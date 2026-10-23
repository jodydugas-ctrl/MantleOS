"""Interactive AppAI MIND contact through the Hermes host LLM."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.config import ResidentConfig
from mantle_addon.runtime import ResidentRuntime


class _Model:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.last_receipt = {
            "schema_version": "mantle-cognition-v1",
            "outcome": "SUCCESS",
            "attempts": 1,
            "provider": "hermes-host",
            "model": "active",
            "total_tokens": 8,
            "cost_usd": 0.01,
        }

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "I am the AppAI MIND, responding from the resident context."


class _FailingModel:
    last_receipt = {
        "schema_version": "mantle-cognition-v1",
        "outcome": "OUTAGE",
        "attempts": 1,
        "provider": "hermes-host",
        "model": "active",
        "error_class": "HOST_UNAVAILABLE",
        "total_tokens": 0,
        "cost_usd": 0.0,
    }

    def __call__(self, _prompt: str) -> str:
        raise RuntimeError("raw provider failure must not be persisted")


class _EchoModel:
    def __init__(self, answer: str):
        self.answer = answer
        self.last_receipt = {
            "schema_version": "mantle-cognition-v1",
            "outcome": "SUCCESS",
            "attempts": 1,
            "provider": "hermes-host",
            "model": "active",
            "total_tokens": 3,
            "cost_usd": 0.0,
        }

    def __call__(self, _prompt: str) -> str:
        return self.answer


class InteractiveMindTests(unittest.TestCase):
    def test_prompt_runs_one_unscheduled_mind_pulse_and_persists_vcw(self):
        with tempfile.TemporaryDirectory(prefix="mantle-mind-test-") as directory:
            config = ResidentConfig.from_mapping({"storage_root": directory})
            model = _Model()
            runtime = ResidentRuntime(
                config,
                profile_id="default",
                model_factory=lambda: model,
            )
            prompt = "What is your current purpose?"
            beats_before = runtime.organism.heart.beats
            bands_before = {
                band: json.dumps(
                    runtime.organism.prime.read(band, reveal_private=True),
                    default=str,
                    sort_keys=True,
                )
                for band in runtime.organism.prime.bands
            }

            answer = runtime.ask_mind(prompt)

            self.assertEqual(
                "I am the AppAI MIND, responding from the resident context.",
                answer,
            )
            self.assertEqual(1, len(model.prompts))
            self.assertIn(runtime.organism.body.identity_name(), model.prompts[0])
            self.assertIn(prompt, model.prompts[0])
            self.assertEqual(beats_before + 1, runtime.organism.heart.beats)
            self.assertIsNone(runtime._scheduler)
            self.assertFalse(runtime.organism.brain.fused)
            self.assertIsNone(runtime.organism.brain.fusion_authorization)
            bands_after = {
                band: json.dumps(
                    runtime.organism.prime.read(band, reveal_private=True),
                    default=str,
                    sort_keys=True,
                )
                for band in runtime.organism.prime.bands
            }
            self.assertEqual(
                {"brain", "thoughts"},
                {
                    band
                    for band in bands_before
                    if bands_before[band] != bands_after[band]
                },
            )

            reloaded = ResidentRuntime(
                config,
                profile_id="default",
            ).organism
            thoughts = reloaded.prime.read("thoughts", reveal_private=True)
            reflection = thoughts[-1]["content"]["reflection"]
            self.assertNotEqual(answer, reflection)
            self.assertIn("content withheld", reflection)
            brain = reloaded.prime.read("brain", reveal_private=True)
            serialized = json.dumps(brain, sort_keys=True)
            self.assertIn("MODEL.REQUEST", serialized)
            self.assertIn("cognition_receipt", serialized)
            self.assertNotIn(prompt, serialized)

    def test_invalid_prompt_is_refused_before_model_dispatch(self):
        with tempfile.TemporaryDirectory(prefix="mantle-mind-test-") as directory:
            model = _Model()
            runtime = ResidentRuntime(
                ResidentConfig.from_mapping({"storage_root": directory}),
                profile_id="default",
                model_factory=lambda: model,
            )

            for prompt in ("", "   ", "bad\x00prompt", "x" * 4_001):
                with self.subTest(prompt=repr(prompt[:20])):
                    with self.assertRaises(ValueError):
                        runtime.ask_mind(prompt)

            self.assertEqual([], model.prompts)

    def test_host_failure_persists_only_redacted_outage_receipt(self):
        with tempfile.TemporaryDirectory(prefix="mantle-mind-test-") as directory:
            config = ResidentConfig.from_mapping({"storage_root": directory})
            runtime = ResidentRuntime(
                config,
                profile_id="default",
                model_factory=_FailingModel,
            )

            with self.assertRaisesRegex(RuntimeError, "raw provider failure"):
                runtime.ask_mind("Are you available?")

            reloaded = ResidentRuntime(config, profile_id="default").organism
            brain = reloaded.prime.read("brain", reveal_private=True)
            serialized = json.dumps(brain, sort_keys=True)
            self.assertIn('"outcome": "OUTAGE"', serialized)
            self.assertIn('"error_class": "HOST_UNAVAILABLE"', serialized)
            self.assertNotIn("raw provider failure", serialized)
            self.assertNotIn("Are you available?", serialized)

    def test_echoed_prompt_is_returned_but_never_persisted(self):
        prompt = "echo-sensitive-user-prompt-7319"
        with tempfile.TemporaryDirectory(prefix="mantle-mind-test-") as directory:
            config = ResidentConfig.from_mapping({"storage_root": directory})
            runtime = ResidentRuntime(
                config,
                profile_id="default",
                model_factory=lambda: _EchoModel(prompt),
            )

            answer = runtime.ask_mind(prompt)

            self.assertEqual(prompt, answer)
            reloaded = ResidentRuntime(config, profile_id="default").organism
            persisted = json.dumps(
                {
                    band: reloaded.prime.read(band, reveal_private=True)
                    for band in reloaded.prime.bands
                },
                default=str,
                sort_keys=True,
            )
            self.assertNotIn(prompt, persisted)
            self.assertIn("content withheld", persisted)

            resident_root = Path(directory) / "default"
            for artifact in resident_root.rglob("*"):
                if artifact.is_file():
                    self.assertNotIn(prompt.encode("utf-8"), artifact.read_bytes())


if __name__ == "__main__":
    unittest.main()
