import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DECISION_JSON = PROJECT_ROOT / "docs" / "FUSION_DECISIONS.json"
DECISION_MD = PROJECT_ROOT / "docs" / "FUSION_DECISIONS.md"
README = PROJECT_ROOT / "README.md"


class FusionDecisionTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(DECISION_JSON.read_text(encoding="utf-8"))

    def test_release_approval_and_fusion_deferral_are_independent(self):
        self.assertEqual("1.1", self.record["schema_version"])
        for role in ("operator", "guardian"):
            with self.subTest(role=role):
                self.assertEqual("APPROVED", self.record[role]["runtime_decision"])
                self.assertEqual("APPROVED", self.record[role]["release_decision"])
                self.assertEqual("DEFERRED", self.record[role]["fusion_decision"])

    def test_effective_gate_fails_closed(self):
        effective = self.record["effective_decision"]
        self.assertTrue(effective["current_runtime_authorized"])
        self.assertTrue(effective["software_release_authorized"])
        self.assertFalse(effective["mind_fusion_authorized"])
        self.assertFalse(effective["reproduction_activation_authorized"])
        self.assertIn("separate authenticated", effective["fusion_rule"])
        self.assertIn("Silence", effective["fusion_rule"])

    def test_open_evidence_is_operational_not_engineering_debt(self):
        evidence = self.record["evidence_basis"]
        self.assertEqual("READY", evidence["technical_readiness"])
        self.assertGreater(evidence["addon_unit_tests"], 0)
        self.assertGreater(evidence["addon_stage1_rows"], 0)
        self.assertGreater(evidence["containment_rows"], 0)
        open_gates = " ".join(evidence["known_open_gates"]).lower()
        self.assertIn("concrete resident", open_gates)
        self.assertIn("authenticated", open_gates)
        self.assertIn("reproduction", open_gates)

    def test_human_surfaces_match_machine_decisions(self):
        decision_text = DECISION_MD.read_text(encoding="utf-8")
        readme_text = README.read_text(encoding="utf-8")
        self.assertIn("Mantle OS 1.3.0 software release | **APPROVED**", decision_text)
        self.assertIn("Production MIND fusion | **DEFERRED — NOT AUTHORIZED**", decision_text)
        self.assertIn("software release APPROVED", readme_text)
        self.assertIn("production MIND fusion DEFERRED", readme_text)
        self.assertNotIn("Production MIND fusion: APPROVED", decision_text)


if __name__ == "__main__":
    unittest.main()
