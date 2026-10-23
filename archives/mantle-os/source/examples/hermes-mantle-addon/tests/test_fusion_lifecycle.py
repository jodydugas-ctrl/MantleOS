import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sys
from threading import Thread
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.authority import Ed25519AuthorityProvider, _canonical_payload
from mantle_addon.config import ResidentConfig
from mantle_addon.runtime import FusionLifecycleError, ResidentRuntime
from mantle_addon.stage1_gate import GateRow, Stage1Receipt, run_gate
from mantle_addon.vendor import vendored_symbol


def _framework_invariant_count() -> int:
    """The live invariant count, derived from the loaded runtime (never hardcoded)."""
    return len(vendored_symbol("audits.invariants", "TESTS"))


class _Mind:
    def cognize(self, _snapshot):
        raise AssertionError("unexpected cognition")


class _Factory:
    def __init__(self, handle):
        self.handle = handle

    def get_or_create(self, _profile_id):
        return self.handle


class _Model:
    def __init__(self):
        self.calls = 0
        self.last_receipt = {}

    def __call__(self, _prompt):
        self.calls += 1
        self.last_receipt = {
            "schema_version": "mantle-cognition-v1",
            "outcome": "SUCCESS",
            "attempts": 1,
            "error_type": "",
            "provider": "host",
            "model": "active",
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
            "cost_usd": 0.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        return "reflection"


class _Scheduler:
    def __init__(self, pulse):
        self.pulse = pulse
        self.running = False

    def start(self):
        self.running = True
        return True

    def stop(self):
        was_running = self.running
        self.running = False
        return was_running

    def wake(self, stressor):
        if not self.running:
            return False
        self.pulse(stressor)
        return True


class FusionLifecycleTests(unittest.TestCase):
    runtime_root = PROJECT_ROOT / ".runtime" / "test-fusion-lifecycle"

    def setUp(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)
        self.runtime_root.mkdir(parents=True)
        self.config = ResidentConfig.from_mapping(
            {"storage_root": str(self.runtime_root)}
        )
        self.runtime = ResidentRuntime(self.config, profile_id="default")

    def tearDown(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)

    def _evidence(self):
        now = datetime.now(timezone.utc)
        organism = self.runtime.organism
        identity = organism.body.identity_name()
        fingerprint = organism.body.key_fingerprint
        receipt = Stage1Receipt(
            passed=True,
            rows=[
                GateRow(f"A-{index:02d}", "test", "PASS", "")
                for index in range(1, 15)
            ],
            fails=[],
            framework_passed=True,
            framework_rows=20,
            framework_invariants=_framework_invariant_count(),
            framework_failures=[],
            summary="complete test receipt",
            issued_at=(now - timedelta(seconds=60)).isoformat(),
            resident_identity=identity,
            body_fingerprint=fingerprint,
        )
        readiness = {
            "recorded_at": (now - timedelta(seconds=45)).isoformat(),
            "verdict": "READY",
            "target": {
                "resident_identity": identity,
                "body_fingerprint": fingerprint,
            },
            "mind_fusion_authorized": False,
            "reproduction_activation_authorized": False,
        }
        authorization = {
            "recorded_at": (now - timedelta(seconds=30)).isoformat(),
            "target": {
                "resident_identity": identity,
                "body_fingerprint": fingerprint,
            },
            "operator": {"fusion_decision": "APPROVED"},
            "guardian": {"fusion_decision": "APPROVED"},
            "effective_decision": {
                "mind_fusion_authorized": True,
                "reproduction_activation_authorized": False,
            },
        }
        return receipt, readiness, authorization

    @staticmethod
    def _authenticate(authorization):
        private_keys = {
            "operator": Ed25519PrivateKey.from_private_bytes(b"o" * 32),
            "guardian": Ed25519PrivateKey.from_private_bytes(b"g" * 32),
        }
        provider = Ed25519AuthorityProvider(
            operator_key_id="operator-test",
            operator_public_key=private_keys["operator"].public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            ),
            guardian_key_id="guardian-test",
            guardian_public_key=private_keys["guardian"].public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            ),
        )
        for role, key in private_keys.items():
            key_id = f"{role}-test"
            authorization[role]["key_id"] = key_id
            authorization[role]["signature"] = base64.b64encode(
                key.sign(_canonical_payload(role, authorization, key_id))
            ).decode()
        return provider

    @staticmethod
    def _lifecycle_records(organism):
        return [
            entry["content"]["fusion_lifecycle"]
            for entry in organism.prime.read("brain")
            if "fusion_lifecycle" in entry.get("content", {})
        ]

    def test_default_state_is_dormant(self):
        self.assertEqual("DORMANT", self.runtime.fusion_state)
        self.assertFalse(self.runtime.organism.brain.fused)

    def test_structurally_valid_caller_authority_is_refused_before_fusion(self):
        receipt, readiness, authorization = self._evidence()

        from mantle_addon.vendor import vendored_symbol as real_vendored_symbol
        with patch(
            "mantle_addon.runtime.vendored_symbol",
            wraps=real_vendored_symbol,
        ) as resolve:
            with self.assertRaises(FusionLifecycleError) as raised:
                self.runtime.request_fusion(
                    stage1_receipt=receipt,
                    readiness_report=readiness,
                    authorization=authorization,
                )

        refusal = raised.exception.receipt
        self.assertEqual("FUSION_REFUSED", refusal.transition)
        self.assertEqual("AUTHORITY_UNAVAILABLE", refusal.reason_code)
        self.assertEqual("DORMANT", refusal.to_state)
        self.assertTrue(refusal.durable)
        self.assertFalse(self.runtime.organism.brain.fused)
        self.assertFalse(
            any(
                call.args[:2] == ("mind.mind", "fuse")
                for call in resolve.call_args_list
            )
        )
        serialized = json.dumps(self._lifecycle_records(self.runtime.organism))
        self.assertNotIn("APPROVED", serialized)
        self.assertNotIn(authorization["recorded_at"], serialized)

    def test_live_incomplete_evidence_is_refused_and_recorded(self):
        with self.assertRaises(FusionLifecycleError) as raised:
            self.runtime.request_fusion(
                stage1_receipt=None,
                readiness_report={},
                authorization={},
            )

        self.assertEqual("PREFLIGHT_REFUSED", raised.exception.receipt.reason_code)
        self.assertEqual(1, len(self._lifecycle_records(self.runtime.organism)))
        self.assertFalse(self.runtime.organism.brain.fused)

    def test_authenticated_fusion_pulse_and_defusion_are_reversible(self):
        receipt, readiness, authorization = self._evidence()
        provider = self._authenticate(authorization)
        model = _Model()
        runtime = ResidentRuntime(
            self.config,
            profile_id="default",
            model_factory=lambda: model,
            authority_provider_factory=lambda: provider,
            scheduler_factory=_Scheduler,
        )
        runtime.organism.stage1_certified = True

        fused = runtime.request_fusion(
            stage1_receipt=receipt,
            readiness_report=readiness,
            authorization=authorization,
        )

        self.assertEqual("FUSION", fused.transition)
        self.assertTrue(fused.durable)
        self.assertEqual("FUSED", runtime.fusion_state)
        self.assertTrue(runtime._scheduler.running)

        runtime._scheduler.pulse(None)
        self.assertEqual(1, model.calls)
        self.assertIn(
            "cognition_receipt",
            json.dumps(runtime.organism.prime.read("brain")),
        )

        defused = runtime.defuse(reason="operator")
        self.assertEqual("COMMITTED", defused.outcome)
        self.assertEqual("DORMANT", runtime.fusion_state)
        self.assertFalse(runtime.organism.stage1_certified)

        post_defusion = run_gate(
            runtime.organism,
            runtime.config,
            runtime._handle.path,
            runtime=runtime,
            include_framework=True,
        )
        self.assertTrue(
            post_defusion.passed,
            f"{post_defusion.summary}; failures={post_defusion.fails}",
        )
        self.assertEqual(_framework_invariant_count(),
                         post_defusion.framework_invariants)

    def test_defusion_stops_scheduler_without_holding_runtime_lock(self):
        receipt, readiness, authorization = self._evidence()
        provider = self._authenticate(authorization)
        runtime = None

        class LockProbeScheduler(_Scheduler):
            def stop(self):
                acquired = []

                def probe():
                    locked = runtime._lock.acquire(timeout=0.2)
                    acquired.append(locked)
                    if locked:
                        runtime._lock.release()

                probe_thread = Thread(target=probe)
                probe_thread.start()
                probe_thread.join()
                if acquired != [True]:
                    raise AssertionError("runtime lock held while scheduler stopped")
                return super().stop()

        runtime = ResidentRuntime(
            self.config,
            profile_id="default",
            model_factory=_Model,
            authority_provider_factory=lambda: provider,
            scheduler_factory=LockProbeScheduler,
        )
        runtime.organism.stage1_certified = True
        runtime.request_fusion(
            stage1_receipt=receipt,
            readiness_report=readiness,
            authorization=authorization,
        )

        defused = runtime.defuse(reason="operator")

        self.assertEqual("COMMITTED", defused.outcome)
        self.assertEqual("DORMANT", runtime.fusion_state)

    def test_defusion_remains_fail_safe_when_scheduler_stop_reports_timeout(self):
        class StuckScheduler:
            def stop(self):
                raise RuntimeError("scheduler thread did not stop")

        organism = self.runtime.organism
        organism.brain._mind = _Mind()
        self.runtime._scheduler = StuckScheduler()

        defused = self.runtime.defuse(reason="shutdown")

        self.assertEqual("COMMITTED", defused.outcome)
        self.assertFalse(organism.brain.fused)
        self.assertTrue(
            any(
                row.get("code") == "SCHEDULER_STOP_FAILED"
                for row in self.runtime.diagnostics
            )
        )

    def test_failed_fusion_checkpoint_stops_scheduler_without_runtime_lock(self):
        receipt, readiness, authorization = self._evidence()
        provider = self._authenticate(authorization)
        runtime = None

        class LockProbeScheduler(_Scheduler):
            def stop(self):
                acquired = []

                def probe():
                    locked = runtime._lock.acquire(timeout=0.2)
                    acquired.append(locked)
                    if locked:
                        runtime._lock.release()

                probe_thread = Thread(target=probe)
                probe_thread.start()
                probe_thread.join()
                if acquired != [True]:
                    raise AssertionError("runtime lock held during fusion rollback")
                return super().stop()

        runtime = ResidentRuntime(
            self.config,
            profile_id="default",
            model_factory=_Model,
            authority_provider_factory=lambda: provider,
            scheduler_factory=LockProbeScheduler,
        )
        runtime.organism.stage1_certified = True
        nondurable = runtime._new_fusion_receipt(
            runtime.organism,
            transition="FUSION",
            outcome="COMMITTED",
            from_state="DORMANT",
            to_state="FUSED",
            reason_code="AUTHORIZED",
            body_preserved=True,
        )
        def persist(_organism, _path, candidate):
            if candidate.transition == "FUSION":
                return nondurable
            return replace(candidate, durable=True)

        with patch.object(runtime, "_persist_fusion_receipt", side_effect=persist):
            with self.assertRaises(FusionLifecycleError) as raised:
                runtime.request_fusion(
                    stage1_receipt=receipt,
                    readiness_report=readiness,
                    authorization=authorization,
                )

        self.assertEqual("FUSION_CHECKPOINT_FAILED", raised.exception.receipt.reason_code)
        self.assertEqual("DORMANT", runtime.fusion_state)

    def test_already_fused_mind_is_not_replaced(self):
        organism = self.runtime.organism
        existing = _Mind()
        organism.brain._mind = existing
        receipt, readiness, authorization = self._evidence()

        with self.assertRaises(FusionLifecycleError) as raised:
            self.runtime.request_fusion(
                stage1_receipt=receipt,
                readiness_report=readiness,
                authorization=authorization,
            )

        self.assertEqual("ALREADY_FUSED", raised.exception.receipt.reason_code)
        self.assertIs(existing, organism.brain.mind)

    def test_defusion_is_authority_free_idempotent_and_preserves_body(self):
        organism = self.runtime.organism
        existing = _Mind()
        organism.brain._mind = existing
        organism.brain._fusion_authorization = {"test": True}
        organism.stage1_certified = True
        before = (
            id(organism),
            organism.body.identity_name(),
            organism.body.key_fingerprint,
            organism.body.primer_sealed,
            frozenset(organism.organs()),
        )

        receipt = self.runtime.defuse(reason="operator")
        after = (
            id(organism),
            organism.body.identity_name(),
            organism.body.key_fingerprint,
            organism.body.primer_sealed,
            frozenset(organism.organs()),
        )

        self.assertEqual("DEFUSION", receipt.transition)
        self.assertEqual("COMMITTED", receipt.outcome)
        self.assertEqual(before, after)
        self.assertFalse(organism.brain.fused)
        self.assertIsNone(organism.brain.mind)
        self.assertIsNone(organism.brain.fusion_authorization)
        self.assertFalse(organism.stage1_certified)
        self.assertTrue(receipt.body_preserved)
        self.assertTrue(receipt.durable)

        noop = self.runtime.defuse(reason="operator")
        self.assertEqual("NOOP", noop.outcome)
        self.assertEqual("DORMANT", noop.to_state)

    def test_persistence_failure_never_reattaches_mind(self):
        organism = self.runtime.organism
        organism.brain._mind = _Mind()
        organism.stage1_certified = True

        with patch(
            "mantle_addon.runtime.save_resident",
            side_effect=OSError("private filesystem detail"),
        ):
            receipt = self.runtime.defuse(reason="fault")

        self.assertFalse(receipt.durable)
        self.assertFalse(organism.brain.fused)
        self.assertFalse(organism.stage1_certified)
        self.assertNotIn("private filesystem detail", json.dumps(receipt.to_dict()))

    def test_unexpected_fused_handle_recovers_before_first_hook(self):
        handle = self.runtime._ensure_handle()
        organism = handle.organism
        organism.brain._mind = _Mind()
        organism.brain._fusion_authorization = {"test": True}
        organism.stage1_certified = True
        recovered = ResidentRuntime(
            self.config,
            profile_id="default",
            factory=_Factory(SimpleNamespace(
                organism=organism,
                path=handle.path,
                created=False,
            )),
        )

        with patch.object(organism.brain, "cognize") as cognize:
            recovered.on_session_start(session_id="session")

        self.assertFalse(organism.brain.fused)
        self.assertFalse(organism.stage1_certified)
        cognize.assert_not_called()
        records = self._lifecycle_records(organism)
        self.assertEqual("RECOVERED_DORMANT", records[-1]["transition"])


if __name__ == "__main__":
    unittest.main()
