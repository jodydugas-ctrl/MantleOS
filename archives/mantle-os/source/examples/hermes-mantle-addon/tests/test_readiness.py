import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
READINESS_JSON = PROJECT_ROOT / "docs" / "MIND_READINESS.json"
READINESS_MD = PROJECT_ROOT / "docs" / "MIND_READINESS.md"
DECISIONS_JSON = PROJECT_ROOT / "docs" / "FUSION_DECISIONS.json"
README = PROJECT_ROOT / "README.md"


class MindReadinessTests(unittest.TestCase):
    def setUp(self):
        self.readiness = json.loads(READINESS_JSON.read_text(encoding="utf-8"))
        self.decisions = json.loads(DECISIONS_JSON.read_text(encoding="utf-8"))

    def test_ready_for_release_does_not_authorize_activation(self):
        self.assertEqual("READY", self.readiness["verdict"])
        self.assertFalse(self.readiness["mind_fusion_authorized"])
        self.assertFalse(self.readiness["reproduction_activation_authorized"])
        self.assertEqual("DEFERRED", self.readiness["evidence"]["operator_fusion_decision"])
        self.assertEqual("DEFERRED", self.readiness["evidence"]["guardian_fusion_decision"])

    def test_complete_gate_evidence_is_self_consistent(self):
        evidence = self.readiness["evidence"]
        addon = evidence["addon_stage1"]
        framework = evidence["framework_stage1"]
        self.assertEqual(addon["passed_rows"], addon["total_rows"])
        self.assertGreater(addon["total_rows"], 0)
        self.assertTrue(addon["passed"])
        self.assertEqual(
            framework["security_invariants_passed"],
            framework["security_invariants_total"],
        )
        self.assertGreater(framework["security_invariants_total"], 0)
        self.assertTrue(framework["passed"])
        self.assertIsNone(framework["failed_invariant"])
        self.assertGreater(evidence["addon_unit_tests"], 0)
        self.assertIn("advisory", framework["root_cause"])

    def test_engineering_blockers_are_resolved_and_activation_stays_separate(self):
        self.assertEqual([], self.readiness["blocking_requirements"])
        self.assertEqual(
            [f"B-{i:02d}" for i in range(1, 9)],
            [row["id"] for row in self.readiness["resolved_requirements"]],
        )
        operational = self.readiness["operational_activation_requirements"]
        self.assertEqual(["A-01", "A-02", "A-03"], [row["id"] for row in operational])
        self.assertTrue(all(row["requirement"] for row in operational))

    def test_decision_authority_matches_report(self):
        effective = self.decisions["effective_decision"]
        self.assertTrue(effective["software_release_authorized"])
        self.assertFalse(effective["mind_fusion_authorized"])
        self.assertFalse(effective["reproduction_activation_authorized"])
        for role in ("operator", "guardian"):
            self.assertEqual("APPROVED", self.decisions[role]["release_decision"])
            self.assertEqual("DEFERRED", self.decisions[role]["fusion_decision"])

    def test_human_surfaces_keep_release_and_fusion_authority_distinct(self):
        report = READINESS_MD.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        self.assertIn("**Software engineering verdict:** **READY**", report)
        self.assertIn("production MIND fusion", readme)
        self.assertIn("caller-authored JSON alone has no authority", readme)
        self.assertNotIn("Production MIND fusion: APPROVED", report)
        self.assertNotIn("production MIND fusion APPROVED", readme)


if __name__ == "__main__":
    unittest.main()
