import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.config import ResidentConfig
from mantle_addon.runtime import OBSERVER_HOOKS, ResidentRuntime, RuntimeRegistry


class ResidentRuntimeTests(unittest.TestCase):
    runtime_root = PROJECT_ROOT / ".runtime" / "test-runtime"

    def setUp(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)
        self.runtime_root.mkdir(parents=True)
        config = ResidentConfig.from_mapping(
            {"storage_root": str(self.runtime_root)}
        )
        self.runtime = ResidentRuntime(config, profile_id="default")

    def tearDown(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)

    def test_observer_hooks_route_signals_through_senses_without_raw_payloads(self):
        self.runtime.on_session_start(session_id="session-1")
        self.runtime.pre_llm_call(
            session_id="session-1",
            model="provider/model",
            user_message="sk-private-user",
            conversation_history=[
                {"role": "user", "content": "sk-private-history"}
            ],
            is_first_turn=False,
        )
        self.runtime.post_llm_call(
            session_id="session-1",
            model="provider/model",
            user_message="sk-private-user",
            assistant_response="sk-private-assistant",
            conversation_history=[],
        )
        self.runtime.pre_tool_call(
            session_id="session-1",
            tool_name="terminal",
            args={"command": "printf sk-secret-value", "sk-secret-value": "ignored"},
            tool_call_id="call-1",
        )
        self.runtime.post_tool_call(
            session_id="session-1",
            tool_name="terminal",
            args={"command": "printf sk-secret-value", "sk-secret-value": "ignored"},
            result="sk-secret-value",
            tool_call_id="call-1",
            status="ok",
            duration_ms=4,
        )

        organism = self.runtime.organism
        entries = organism.prime.read("senses")
        serialized = json.dumps(entries, sort_keys=True)
        self.assertEqual(5, len(entries))
        for forbidden in (
            "sk-private-user",
            "sk-private-history",
            "sk-private-assistant",
            "sk-secret-value",
            "call-1",
        ):
            self.assertNotIn(forbidden, serialized)
        pre_signal = next(
            entry["content"]["signal"]
            for entry in entries
            if entry["content"]["signal"]["event_type"] == "pre_llm_call"
        )
        post_signal = next(
            entry["content"]["signal"]
            for entry in entries
            if entry["content"]["signal"]["event_type"] == "post_llm_call"
        )
        self.assertEqual(15, pre_signal["metadata"]["user_message"]["chars"])
        self.assertEqual(1, pre_signal["metadata"]["conversation_history"]["items"])
        self.assertEqual(20, post_signal["metadata"]["assistant_response"]["chars"])
        self.assertIn("post_tool_call", serialized)
        self.assertGreaterEqual(organism.heart.beats, 5)

    def test_post_tool_records_action_execution_proof_and_failure_immune_event(self):
        self.runtime.on_session_start(session_id="session-1")

        with patch.object(
            self.runtime.organism.limbs,
            "_prove",
            side_effect=AssertionError("private API must not be called"),
        ):
            self.runtime.post_tool_call(
                session_id="session-1",
                tool_name="write_file",
                args={"path": "/tmp/x", "content": "secret"},
                result="failed",
                tool_call_id="call-2",
                status="error",
                error_type="PermissionError",
                error_message="private detail",
                duration_ms=2,
            )

        brain = self.runtime.organism.prime.read("brain")
        proofs = [
            item["content"]["action_proof"]
            for item in brain
            if "action_proof" in item.get("content", {})
        ]
        self.assertEqual(1, len(proofs))
        self.assertTrue(proofs[0]["attempted"])
        self.assertFalse(proofs[0]["ok"])
        self.assertEqual("Hermes dispatch", proofs[0]["method"])
        self.assertTrue(proofs[0]["ref"].startswith("sha256:"))
        self.assertNotIn("call-2", json.dumps(proofs[0]))
        self.assertTrue(
            {
                "action_id",
                "attempted",
                "ok",
                "method",
                "ref",
                "reason",
                "actor",
                "authorship",
                "timestamp",
                "evidence",
            }.issubset(proofs[0])
        )
        self.assertEqual("BODY", proofs[0]["authorship"])
        self.assertEqual("post_tool_call", proofs[0]["evidence"][0]["source"])
        self.assertTrue(
            any(event["kind"] == "host_tool_error" for event in self.runtime.organism.immune.log)
        )

    def test_blocked_tool_proof_never_claims_dispatch_attempt(self):
        self.runtime.post_tool_call(
            session_id="session-1",
            tool_name="write_file",
            args={"path": "/tmp/x"},
            result="blocked",
            tool_call_id="call-blocked",
            status="blocked",
            error_type="plugin_block",
        )

        proofs = [
            item["content"]["action_proof"]
            for item in self.runtime.organism.prime.read("brain")
            if "action_proof" in item.get("content", {})
        ]
        self.assertEqual(1, len(proofs))
        self.assertFalse(proofs[0]["attempted"])
        self.assertFalse(proofs[0]["ok"])
        self.assertIsNone(proofs[0]["method"])
        self.assertTrue(
            any(
                event["kind"] == "host_tool_block"
                for event in self.runtime.organism.immune.log
            )
        )

    def test_malformed_tool_status_does_not_claim_an_attempt(self):
        self.runtime.post_tool_call(tool_name="terminal", status="surprise")

        proof = self.runtime.organism.prime.read("brain")[-1]["content"]["action_proof"]
        self.assertFalse(proof["attempted"])
        self.assertFalse(proof["ok"])
        self.assertIsNone(proof["method"])

    def test_checkpoint_each_turn_false_defers_persistence_to_session_end(self):
        deferred_root = self.runtime_root / "deferred"
        runtime = ResidentRuntime(
            ResidentConfig.from_mapping(
                {
                    "storage_root": str(deferred_root),
                    "checkpoint_each_turn": False,
                }
            ),
            profile_id="default",
        )
        runtime.organism

        with patch("mantle_addon.runtime.save_resident") as persist:
            runtime.pre_llm_call(
                user_message="private",
                conversation_history=[],
                model="provider/model",
            )
            self.assertEqual(0, persist.call_count)
            runtime.on_session_end(session_id="session-1")
            self.assertEqual(1, persist.call_count)

    def test_checkpoint_failure_is_fail_open_and_becomes_immune_event(self):
        self.runtime.organism
        with patch(
            "mantle_addon.runtime.save_resident",
            side_effect=OSError("private filesystem detail"),
        ):
            result = self.runtime.pre_llm_call(
                user_message="private",
                conversation_history=[],
            )

        self.assertIsNone(result)
        failures = [
            event
            for event in self.runtime.organism.immune.log
            if event["kind"] == "flush_failed"
        ]
        self.assertEqual(1, len(failures))
        self.assertNotIn("private filesystem detail", json.dumps(failures))

    def test_callbacks_are_fail_open_when_body_initialization_fails(self):
        class BrokenFactory:
            def get_or_create(self, profile_id):
                raise RuntimeError("broken resident")

        runtime = ResidentRuntime(
            ResidentConfig.from_mapping({}),
            profile_id="default",
            factory=BrokenFactory(),
        )

        result = runtime.pre_llm_call(messages=[])

        self.assertIsNone(result)
        self.assertEqual("RuntimeError", runtime.diagnostics[-1]["error_type"])
        self.assertNotIn("broken resident", json.dumps(runtime.diagnostics))

        for _ in range(150):
            runtime.pre_llm_call(messages=[])
        self.assertEqual(100, len(runtime.diagnostics))

    def test_hook_failure_after_body_birth_becomes_redacted_immune_event(self):
        self.runtime.on_session_start(session_id="session-1")
        organism = self.runtime.organism

        with patch.object(organism.senses, "inhale", side_effect=ValueError("secret detail")):
            result = self.runtime.pre_llm_call(
                messages=[{"role": "user", "content": "private"}]
            )

        self.assertIsNone(result)
        failures = [
            event for event in organism.immune.log if event["kind"] == "hook_failure"
        ]
        self.assertEqual(1, len(failures))
        self.assertEqual("pre_llm_call", failures[0]["detail"]["event_type"])
        self.assertEqual("ValueError", failures[0]["detail"]["error_type"])
        self.assertNotIn("secret detail", json.dumps(failures))

    def test_declared_hooks_are_observers_and_callbacks_return_none(self):
        self.assertEqual(
            {
                "on_session_start",
                "on_session_end",
                "on_session_finalize",
                "pre_llm_call",
                "post_llm_call",
                "pre_tool_call",
                "post_tool_call",
                "pre_approval_request",
                "post_approval_response",
                "subagent_start",
                "subagent_stop",
                "pre_gateway_dispatch",
            },
            set(OBSERVER_HOOKS),
        )
        for hook_name in OBSERVER_HOOKS:
            with self.subTest(hook=hook_name):
                self.assertIsNone(getattr(self.runtime, hook_name)())

    def test_runtime_installs_dual_flush_on_handle_creation(self):
        """The runtime should install dual-flush (atexit) when the handle is created."""
        _ = self.runtime.organism  # triggers _ensure_handle
        self.assertTrue(self.runtime.organism.heart._atexit_installed)

    def test_runtime_deferred_mode_installs_atexit_save_handler(self):
        """In deferred checkpoint mode, an atexit save handler should be registered."""
        deferred_root = self.runtime_root / "deferred-atexit"
        config = ResidentConfig.from_mapping(
            {"storage_root": str(deferred_root), "checkpoint_each_turn": False}
        )
        runtime = ResidentRuntime(config, profile_id="default")
        _ = runtime.organism  # triggers _ensure_handle

        # The heart should have dual-flush installed
        self.assertTrue(runtime.organism.heart._atexit_installed)
        # The circulate callback should be None (deferred mode)
        self.assertIsNone(runtime.organism.heart._circulate_cb)

    def test_participant_hooks_route_redacted_signals_through_senses(self):
        """The five host-surface hooks should record derived, non-raw metadata."""
        secret_command = "rm -rf /"
        secret_goal = "analyze customer secret"
        secret_message = "gateway secret payload"
        event = SimpleNamespace(
            text=secret_message,
            message_type=SimpleNamespace(value="text"),
            media_urls=["/tmp/image.png"],
            source=SimpleNamespace(platform=SimpleNamespace(value="telegram")),
        )

        self.runtime.pre_approval_request(
            command=secret_command,
            description="dangerous",
            pattern_key="destructive",
            surface="cli",
        )
        self.runtime.post_approval_response(
            command=secret_command,
            description="dangerous",
            choice="deny",
            pattern_key="destructive",
            surface="cli",
        )
        self.runtime.subagent_start(
            child_goal=secret_goal,
            child_role="leaf",
            parent_session_id="parent-1",
            child_session_id="child-1",
        )
        self.runtime.subagent_stop(
            child_summary=secret_goal,
            child_status="completed",
            child_role="leaf",
            parent_session_id="parent-1",
            child_session_id="child-1",
        )
        self.runtime.pre_gateway_dispatch(event=event)

        entries = self.runtime.organism.prime.read("senses")
        serialized = json.dumps(entries, sort_keys=True)
        event_types = {
            e["content"]["signal"]["event_type"]
            for e in entries
            if isinstance(e.get("content"), dict)
            and isinstance(e["content"].get("signal"), dict)
        }
        self.assertTrue(
            {
                "pre_approval_request",
                "post_approval_response",
                "subagent_start",
                "subagent_stop",
                "pre_gateway_dispatch",
            }.issubset(event_types)
        )
        self.assertIn('"choice": "deny"', serialized)
        self.assertIn('"child_status": "completed"', serialized)
        self.assertIn('"summary": {"chars": 23', serialized)
        self.assertIn('"platform": "telegram"', serialized)
        self.assertIn('"media_count": 1', serialized)
        self.assertNotIn(secret_command, serialized)
        self.assertNotIn(secret_goal, serialized)
        self.assertNotIn(secret_message, serialized)
        self.assertNotIn("parent-1", serialized)
        self.assertNotIn("child-1", serialized)

    def test_participant_hooks_return_none(self):
        """All five callbacks are observer-only and cannot alter host behavior."""
        self.assertIsNone(self.runtime.pre_approval_request())
        self.assertIsNone(self.runtime.post_approval_response())
        self.assertIsNone(self.runtime.subagent_start())
        self.assertIsNone(self.runtime.subagent_stop())
        self.assertIsNone(self.runtime.pre_gateway_dispatch())

    def test_observer_hooks_never_cognize_between_natural_heartbeats(self):
        """Hermes activity drives the Body, not the fused MIND cadence."""
        organism = self.runtime.organism
        mind = SimpleNamespace(cognize=lambda _snapshot: "thought")
        organism.brain._mind = mind

        with patch.object(mind, "cognize", wraps=mind.cognize) as cognize:
            self.runtime.pre_llm_call(user_message="private")
            cognize.assert_not_called()
            organism.heart.beat()
            cognize.assert_called_once()

    def test_registry_does_not_fork_a_resident_when_config_changes(self):
        configs = [self.runtime.config]
        registry = RuntimeRegistry(
            profile_resolver=lambda: "default",
            home_resolver=lambda: self.runtime_root,
            config_resolver=lambda: configs[0],
        )
        first = registry.current()
        first.organism.brain._mind = SimpleNamespace(cognize=lambda _snapshot: "thought")
        configs[0] = ResidentConfig.from_mapping(
            {
                "storage_root": str(self.runtime_root),
                "max_event_chars": 8192,
            }
        )

        second = registry.current()

        self.assertIs(first, second)
        self.assertTrue(second.organism.brain.fused)


if __name__ == "__main__":
    unittest.main()
