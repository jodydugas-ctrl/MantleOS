from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.config import ConfigError, ResidentConfig
from mantle_addon.primer import build_primer
from mantle_addon.stage1_gate import GateRow, Stage1Receipt


class ResidentConfigTests(unittest.TestCase):
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)

    def _complete_receipt(self) -> Stage1Receipt:
        issued_at = (self.now - timedelta(seconds=60)).isoformat()
        rows = [GateRow(f"A-{index:02d}", "test", "PASS", "") for index in range(1, 15)]
        return Stage1Receipt(
            passed=True,
            rows=rows,
            fails=[],
            framework_passed=True,
            framework_rows=20,
            framework_invariants=90,
            framework_failures=[],
            summary="complete test receipt",
            issued_at=issued_at,
            resident_identity="Hermes.Mantle.AppAI",
            body_fingerprint="body-fingerprint-1",
        )

    def _approval(self) -> dict:
        return {
            "recorded_at": (self.now - timedelta(seconds=30)).isoformat(),
            "target": {
                "resident_identity": "Hermes.Mantle.AppAI",
                "body_fingerprint": "body-fingerprint-1",
            },
            "operator": {"fusion_decision": "APPROVED"},
            "guardian": {"fusion_decision": "APPROVED"},
            "effective_decision": {
                "mind_fusion_authorized": True,
                "reproduction_activation_authorized": False,
            },
        }

    def _readiness(self) -> dict:
        return {
            "recorded_at": (self.now - timedelta(seconds=45)).isoformat(),
            "verdict": "READY",
            "target": {
                "resident_identity": "Hermes.Mantle.AppAI",
                "body_fingerprint": "body-fingerprint-1",
            },
            "mind_fusion_authorized": False,
            "reproduction_activation_authorized": False,
        }

    def test_defaults_are_body_first_and_observer_only(self):
        config = ResidentConfig.from_mapping({})

        self.assertTrue(config.body_enabled)
        self.assertFalse(config.mind_enabled)
        self.assertIsNone(config.storage_root)
        self.assertEqual("none", config.dnr)
        self.assertFalse(config.record_raw_prompts)
        self.assertFalse(config.record_raw_tool_args)
        self.assertEqual(4096, config.max_event_chars)
        self.assertTrue(config.checkpoint_each_turn)

    def test_config_is_immutable_and_rejects_unknown_fields(self):
        config = ResidentConfig.from_mapping({})

        with self.assertRaises(FrozenInstanceError):
            setattr(config, "body_enabled", False)
        with self.assertRaisesRegex(ConfigError, "unknown configuration field"):
            ResidentConfig.from_mapping({"surprise": True})

    def test_direct_constructor_cannot_bypass_phase1_gates(self):
        with self.assertRaisesRegex(ConfigError, "authorize_phase2"):
            ResidentConfig(mind_enabled=True)
        with self.assertRaises(TypeError):
            ResidentConfig(mind_enabled=True, _phase2_grant=object())
        with self.assertRaisesRegex(ConfigError, "raw payload retention"):
            ResidentConfig(record_raw_prompts=True)

    def test_config_validates_types_ranges_and_dnr(self):
        invalid = [
            {"body_enabled": "yes"},
            {"max_event_chars": 0},
            {"max_event_chars": 1_000_001},
            {"dnr": "rebuild_anyway"},
            {"storage_root": 123},
        ]

        for mapping in invalid:
            with self.subTest(mapping=mapping):
                with self.assertRaises(ConfigError):
                    ResidentConfig.from_mapping(mapping)

    def test_mind_requires_fresh_stage1_and_separate_fusion_authority(self):
        with self.assertRaisesRegex(ConfigError, "Stage-1 PASS"):
            ResidentConfig.from_mapping({"mind_enabled": True})
        with self.assertRaisesRegex(ConfigError, "fusion authorization"):
            ResidentConfig.from_mapping(
                {"mind_enabled": True}, stage1_passed=True
            )

        with self.assertRaisesRegex(ConfigError, "authorize_phase2"):
            ResidentConfig.from_mapping(
                {"mind_enabled": True},
                stage1_passed=True,
                fusion_authorized=True,
            )

    def test_structurally_fabricated_authority_cannot_enable_phase2(self):
        """Unsigned caller-authored JSON is evidence, not independent human authority."""
        with self.assertRaisesRegex(ConfigError, "authenticated.*unavailable"):
            ResidentConfig.authorize_phase2(
                ResidentConfig.from_mapping({}),
                stage1_receipt=self._complete_receipt(),
                readiness_report=self._readiness(),
                authorization=self._approval(),
                now=self.now,
            )

    def test_phase2_transition_rejects_incomplete_stale_or_mismatched_evidence(self):
        base = ResidentConfig.from_mapping({})
        receipt = self._complete_receipt()

        cases = []
        cases.append((
            receipt._replace(framework_passed=False),
            self._readiness(),
            self._approval(),
            "complete",
        ))
        contradictory_rows = [row._replace(result="FAIL") for row in receipt.rows]
        cases.append((
            receipt._replace(rows=contradictory_rows),
            self._readiness(),
            self._approval(),
            "complete",
        ))
        duplicate_codes = list(receipt.rows)
        duplicate_codes[-1] = duplicate_codes[-1]._replace(code="A-01")
        cases.append((
            receipt._replace(rows=duplicate_codes),
            self._readiness(),
            self._approval(),
            "complete",
        ))
        cases.append((
            receipt._replace(issued_at=(self.now - timedelta(seconds=301)).isoformat()),
            self._readiness(),
            self._approval(),
            "fresh",
        ))
        not_ready = self._readiness()
        not_ready["verdict"] = "NOT_READY"
        cases.append((receipt, not_ready, self._approval(), "READY"))
        missing_readiness_time = self._readiness()
        missing_readiness_time.pop("recorded_at")
        cases.append((
            receipt,
            missing_readiness_time,
            self._approval(),
            "readiness recorded_at",
        ))
        early_readiness = self._readiness()
        early_readiness["recorded_at"] = (
            self.now - timedelta(seconds=90)
        ).isoformat()
        cases.append((receipt, early_readiness, self._approval(), "readiness.*follow"))
        wrong_target = self._approval()
        wrong_target["target"]["body_fingerprint"] = "different-body"
        cases.append((receipt, self._readiness(), wrong_target, "target"))
        deferred = self._approval()
        deferred["guardian"]["fusion_decision"] = "DEFERRED"
        cases.append((receipt, self._readiness(), deferred, "guardian"))
        early = self._approval()
        early["recorded_at"] = (self.now - timedelta(seconds=90)).isoformat()
        cases.append((receipt, self._readiness(), early, "follow"))
        reproduction = self._approval()
        reproduction["effective_decision"]["reproduction_activation_authorized"] = True
        cases.append((receipt, self._readiness(), reproduction, "reproduction"))

        for candidate_receipt, candidate_readiness, candidate_authority, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ConfigError, message):
                    ResidentConfig.authorize_phase2(
                        base,
                        stage1_receipt=candidate_receipt,
                        readiness_report=candidate_readiness,
                        authorization=candidate_authority,
                        now=self.now,
                    )

    def test_live_deferred_decisions_cannot_enable_phase2(self):
        decisions = json.loads(
            (PROJECT_ROOT / "docs" / "FUSION_DECISIONS.json").read_text(
                encoding="utf-8"
            )
        )
        with self.assertRaises(ConfigError):
            ResidentConfig.authorize_phase2(
                ResidentConfig.from_mapping({}),
                stage1_receipt=self._complete_receipt(),
                readiness_report=json.loads(
                    (PROJECT_ROOT / "docs" / "MIND_READINESS.json").read_text(
                        encoding="utf-8"
                    )
                ),
                authorization=decisions,
                now=self.now,
            )

    def test_raw_payload_retention_flags_are_present_but_not_authorized(self):
        for field in ("record_raw_prompts", "record_raw_tool_args"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ConfigError, "raw payload retention"):
                    ResidentConfig.from_mapping({field: True})

    def test_defaults_file_matches_runtime_defaults(self):
        defaults = json.loads(
            (PROJECT_ROOT / "config" / "defaults.json").read_text(encoding="utf-8")
        )
        self.assertEqual(defaults, ResidentConfig.from_mapping({}).to_dict())


class PrimerTests(unittest.TestCase):
    def test_primer_declares_residency_and_all_nine_organs_with_brain_dormant(self):
        primer = build_primer(ResidentConfig.from_mapping({}))

        self.assertEqual("Hermes.Mantle.AppAI", primer.identity["name"])
        self.assertEqual("hospitari", primer.identity["residency_mode"])
        self.assertEqual("dormant", primer.identity["mind_state"])
        self.assertEqual(
            {
                "heart",
                "genome",
                "nervous",
                "senses",
                "immune",
                "limbs",
                "memory",
                "brain",
                "reproduction",
            },
            set(primer.identity["organs"]),
        )
        self.assertIn("Body before MIND", primer.commandments)
        self.assertTrue(any("Action Execution Proof" in item for item in primer.commandments))
        self.assertTrue(any("Hermes approvals" in item for item in primer.truths))

    def test_primer_output_is_deterministic_and_contains_no_runtime_secret(self):
        config = ResidentConfig.from_mapping({"dnr": "no_reconstruction"})

        first = build_primer(config).to_dict()
        second = build_primer(config).to_dict()

        self.assertEqual(first, second)
        serialized = json.dumps(first, sort_keys=True).lower()
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("genesis_key", serialized)
        self.assertEqual("no_reconstruction", first["identity"]["dnr"])


if __name__ == "__main__":
    unittest.main()
