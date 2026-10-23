"""Focused tests for Mantle's optional rolling-prefix context policy."""
from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest

from mantle import Organism
from mantle.mind import Mind, MindPort
from mantle.mind.context import (
    ContextCapabilityUnavailable,
    ModelInfo,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    RollingContextConfig,
    RollingPrefixContextStrategy,
    SourceCursor,
    canonical_json_bytes,
    install_context_band,
    render_entries,
    render_entry,
)
from mantle.primer import appai_commandments, appai_truths


def born():
    org = Organism.birth(
        identity={"name": "Rolling.Context.Test"},
        truths=appai_truths(),
        commandments=appai_commandments(),
    )
    install_context_band(org, authorized=True)
    return org


class CountingModel:
    provider = "test"
    model_name = "test/model"
    capabilities = ProviderCapabilities(
        prefix_cache=True,
        reports_cached_tokens=True,
    )

    def __init__(self):
        self.prompts = []
        self.last_usage = None

    def __call__(self, prompt):
        self.prompts.append(prompt)
        self.last_usage = {
            "prompt_tokens": math.ceil(len(prompt.encode("utf-8")) / 3),
            "completion_tokens": 3,
            "cached_tokens": 10 if len(self.prompts) > 1 else 0,
            "cache_write_tokens": 10 if len(self.prompts) == 1 else 2,
            "generation_id": "g-%d" % len(self.prompts),
        }
        return "answer-%d" % len(self.prompts)


class RollingContextTests(unittest.TestCase):
    def strategy(self, org, **overrides):
        values = {"context_window_tokens": 16_000}
        values.update(overrides)
        return RollingPrefixContextStrategy(org, RollingContextConfig(**values))

    def test_canonical_json_and_envelope_are_stable(self):
        left = {"z": "é", "a": {"y": 2, "x": 1}}
        right = {"a": {"x": 1, "y": 2}, "z": "é"}
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))
        self.assertEqual(render_entry(left), render_entry(right))
        with self.assertRaises(ValueError):
            canonical_json_bytes({"bad": float("nan")})

    def test_snapshot_strategy_preserves_legacy_prompt_bytes(self):
        org = born()
        model = CountingModel()
        mind = Mind(MindPort(org), model)
        snapshot = org.nervous.assemble()
        expected = mind._frame(snapshot)
        mind.think(snapshot)
        self.assertEqual(model.prompts, [expected])

    def test_snapshot_strategy_keeps_context_when_intent_is_supplied(self):
        org = born()
        model = CountingModel()
        mind = Mind(MindPort(org), model)
        snapshot = org.nervous.assemble()
        expected = "%s\n\nINTENT:\nhello" % mind._frame(snapshot)
        mind.think(snapshot, "hello")
        self.assertEqual(model.prompts, [expected])

    def test_prefix_is_immutable_and_delta_advances_once(self):
        org = born()
        org.memory.remember("facts", {"name": "alpha"})
        model = CountingModel()
        strategy = self.strategy(org)
        mind = Mind(MindPort(org), model, context_strategy=strategy)
        mind.think(org.nervous.assemble(), "first")
        first_prompt = model.prompts[-1].encode("utf-8")
        mind.think(org.nervous.assemble(), "second")
        second_prompt = model.prompts[-1].encode("utf-8")
        self.assertTrue(second_prompt.startswith(first_prompt))
        self.assertEqual(strategy.ledger.latest_cursor().facts, 1)
        deltas = [r for r in strategy.ledger.records() if r["kind"] == "DELTA"]
        source_ids = [
            (entry["source_band"], entry["source_id"])
            for delta in deltas for entry in delta["entries"]
        ]
        self.assertEqual(source_ids.count(("facts", 0)), 1)
        self.assertNotEqual(first_prompt, second_prompt)
        self.assertEqual(strategy.ledger.verify(), [])

    def test_failure_does_not_advance_cursor_and_retry_bytes_match(self):
        org = born()
        org.memory.remember("events", {"event": "pending"})
        strategy = self.strategy(org)
        model_info = ModelInfo(provider="test", model="test/model")
        first = strategy.prepare(
            snapshot=org.nervous.assemble(),
            intent="retry me",
            model_info=model_info,
        )
        strategy.commit_failure(first, error=TimeoutError("provider timeout"))
        self.assertEqual(strategy.ledger.latest_cursor(), SourceCursor())
        second = strategy.prepare(
            snapshot=org.nervous.assemble(),
            intent="retry me",
            model_info=model_info,
        )
        self.assertEqual(first.prompt_bytes, second.prompt_bytes)
        self.assertEqual(first.request_hash, second.request_hash)

    def test_model_change_rolls_generation_before_send(self):
        org = born()
        strategy = self.strategy(org)
        snapshot = org.nervous.assemble()
        first = strategy.prepare(
            snapshot=snapshot,
            intent="one",
            model_info=ModelInfo(provider="p", model="large"),
        )
        strategy.commit_success(first, answer="ok", usage={})
        second = strategy.prepare(
            snapshot=snapshot,
            intent="two",
            model_info=ModelInfo(provider="p", model="small"),
        )
        self.assertEqual(second.generation, 2)
        self.assertTrue(any(
            record["kind"] == "ROLLOVER"
            for record in strategy.ledger.records()
        ))

    def test_private_context_is_not_in_snapshot_or_mind_write_surface(self):
        org = born()
        strategy = self.strategy(org)
        prepared = strategy.prepare(
            snapshot=org.nervous.assemble(),
            intent="api_key=sk-ABCDEFGHIJKLMNOPQRST",
            model_info=ModelInfo(model="test"),
        )
        self.assertNotIn("sk-ABCDEFGHIJKLMNOPQRST", prepared.prompt)
        self.assertNotIn("context", org.nervous.assemble())
        mind = Mind(MindPort(org), CountingModel(), context_strategy=strategy)
        with self.assertRaises(PermissionError):
            mind._guarded_write("context", {"forbidden": True})

    def test_request_hash_and_usage_receipt_are_exact(self):
        org = born()
        model = CountingModel()
        strategy = self.strategy(org)
        mind = Mind(MindPort(org), model, context_strategy=strategy)
        mind.think(org.nervous.assemble(), "account")
        request = next(r for r in strategy.ledger.records() if r["kind"] == "REQUEST")
        # The durable hash covers the bytes the transport actually received, and
        # the ledger stores the hash rather than another copy of the prompt.
        self.assertEqual(
            request["request_hash"],
            hashlib.sha256(model.prompts[-1].encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("request_prompt", request)
        receipt = next(r for r in strategy.ledger.records() if r["kind"] == "RECEIPT")
        self.assertEqual(receipt["generation_id"], "g-1")
        self.assertIn("estimation_error", receipt)

    def test_ledger_grows_linearly_not_with_the_resent_prefix(self):
        """The ledger stores each byte once, so a round costs the same at any depth."""
        org = born()
        model = CountingModel()
        strategy = self.strategy(org, context_window_tokens=200_000)
        mind = Mind(MindPort(org), model, context_strategy=strategy)
        sizes = []
        for index in range(12):
            org.memory.remember("facts", {"index": index, "text": "z" * 200})
            mind.think(org.nervous.assemble(), "round %d" % index)
            sizes.append(len(json.dumps(
                org.prime.read("context", reveal_private=True)
            )))
        growth = [later - earlier for earlier, later in zip(sizes, sizes[1:])]
        # Each round re-sends the whole prefix. Storing a copy of the prompt per
        # request would make the ledger grow quadratically, so a late round would
        # cost far more than an early one.
        self.assertLess(growth[-1], 1.5 * growth[0])
        self.assertEqual(strategy.ledger.verify(), [])

    def test_exact_sent_bytes_are_reconstructible_from_the_committed_chain(self):
        org = born()
        model = CountingModel()
        strategy = self.strategy(org)
        mind = Mind(MindPort(org), model, context_strategy=strategy)
        org.memory.remember("facts", {"name": "alpha"})
        mind.think(org.nervous.assemble(), "first")
        # Re-rendering the committed visible chain reproduces the prefix the
        # next round builds on, without any stored prompt copy.
        rebuilt = render_entries(strategy.ledger.visible_records())
        mind.think(org.nervous.assemble(), "second")
        self.assertTrue(model.prompts[-1].encode("utf-8").startswith(rebuilt))

    def test_corruption_is_detected_and_next_generation_recovers(self):
        org = born()
        strategy = self.strategy(org)
        prepared = strategy.prepare(
            snapshot=org.nervous.assemble(),
            intent="one",
            model_info=ModelInfo(model="test"),
        )
        strategy.commit_success(prepared, answer="ok", usage={})
        physical = org.prime.read("context", reveal_private=True)
        target = next(entry for entry in physical
                      if entry["content"]["kind"] == "RESPONSE")
        target["content"]["content"] = "tampered"
        self.assertTrue(strategy.ledger.verify())
        recovered = strategy.prepare(
            snapshot=org.nervous.assemble(),
            intent="two",
            model_info=ModelInfo(model="test"),
        )
        self.assertEqual(recovered.generation, 2)
        self.assertEqual(strategy.ledger.verify_generation(2), [])

    def test_durable_exact_resumes_after_save_and_reload(self):
        org = born()
        strategy = self.strategy(org)
        info = ModelInfo(provider="test", model="test/model")
        first = strategy.prepare(
            snapshot=org.nervous.assemble(),
            intent="persist",
            model_info=info,
        )
        strategy.commit_success(first, answer="remembered answer", usage={})
        with tempfile.TemporaryDirectory() as directory:
            org.save(directory)
            loaded = Organism.load(directory)
            resumed = self.strategy(loaded)
            second = resumed.prepare(
                snapshot=loaded.nervous.assemble(),
                intent="continue",
                model_info=info,
            )
        self.assertEqual(second.generation, 1)
        self.assertIn("remembered answer", second.prompt)
        self.assertEqual(resumed.ledger.verify(), [])

    def test_every_persistence_mode_keeps_one_stable_generation(self):
        for mode in ("durable-exact", "session-exact", "receipt-only"):
            with self.subTest(mode=mode):
                org = born()
                strategy = self.strategy(
                    org,
                    persistence_mode=mode,
                    resume_after_restart=(mode == "durable-exact"),
                )
                info = ModelInfo(provider="test", model="test/model")
                prompts = []
                for index in range(4):
                    org.memory.remember("facts", {"index": index})
                    prepared = strategy.prepare(
                        snapshot=org.nervous.assemble(),
                        intent="round %d" % index,
                        model_info=info,
                    )
                    prompts.append(prepared.prompt_bytes)
                    self.assertEqual(prepared.generation, 1)
                    strategy.commit_success(
                        prepared, answer="answer %d" % index, usage={},
                    )
                for earlier, later in zip(prompts, prompts[1:]):
                    self.assertTrue(later.startswith(earlier))
                self.assertEqual(strategy.ledger.verify(), [])
                self.assertEqual(
                    [event for event in org.prime.read("immune")
                     if (event.get("content") or {}).get("kind")
                     == "context_corruption"],
                    [],
                )

    def test_receipt_only_delta_still_bounds_cursor_commits(self):
        org = born()
        org.memory.remember("facts", {"name": "alpha"})
        strategy = self.strategy(
            org, persistence_mode="receipt-only", resume_after_restart=False,
        )
        prepared = strategy.prepare(
            snapshot=org.nervous.assemble(),
            intent="one",
            model_info=ModelInfo(model="test"),
        )
        strategy.commit_success(prepared, answer="ok", usage={})
        self.assertEqual(strategy.ledger.verify(), [])
        commit = next(entry for entry in org.prime.read("context", reveal_private=True)
                      if entry["content"]["kind"] == "COMMIT")
        commit["content"]["source_cursors"]["facts"] = 999
        self.assertTrue(any("beyond committed" in problem
                            for problem in strategy.ledger.verify()))

    def test_required_provider_cache_refuses_an_incapable_transport(self):
        org = born()
        strategy = self.strategy(org, provider_cache="required")
        with self.assertRaises(ContextCapabilityUnavailable):
            strategy.prepare(
                snapshot=org.nervous.assemble(),
                intent="cache me",
                model_info=ModelInfo(model="test"),
            )

    def test_structured_transport_remains_optional(self):
        class Structured:
            provider = "test"
            model_name = "structured"
            capabilities = ProviderCapabilities(structured_messages=True)

            def __call__(self, prompt):
                raise AssertionError("legacy path should not be used")

            def complete(self, request: ModelRequest):
                self.request = request
                return ModelResponse(text="structured-answer", usage={"prompt_tokens": 1})

        org = born()
        model = Structured()
        mind = Mind(MindPort(org), model)
        snapshot = org.nervous.assemble()
        self.assertEqual(mind.think(snapshot, "hello"), "structured-answer")
        self.assertEqual(
            model.request.prompt,
            "%s\n\nINTENT:\nhello" % mind._frame(snapshot),
        )


if __name__ == "__main__":
    unittest.main()
