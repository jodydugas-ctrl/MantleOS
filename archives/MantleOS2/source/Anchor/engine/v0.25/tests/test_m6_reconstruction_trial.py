from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scan.engine import ScanEngine
from scan.release import certify_reconstruction_handoff, certify_specimen, write_package_manifest
from scan.store import Store
from scan.reconstruction_trial import (
    CHALLENGE_MANIFEST, EVALUATOR_MANIFEST, SUBMISSION_SCHEMA, TRIAL_MANIFEST,
    prepare_reconstruction_trial, score_reconstruction_trial, verify_reconstruction_trial,
)

UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <action name="actionSave"><property name="text"><string>Save</string></property></action>
 </widget>
</ui>
'''
CPP = '''#include <QAction>
void MainWindow::wire() {
    connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile);
}
void MainWindow::saveFile() {}
'''
MISSING_CPP = '''#include <QAction>
void MainWindow::wire() {}
'''
MISSING_UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0"><class>MainWindow</class><widget class="QMainWindow" name="MainWindow"/></ui>
'''


def proposal(save_id: str):
    return {
        "schema_version": "scan-reconstruction-proposal/0.1",
        "proposal_id": "RP-M6-SAVE",
        "objects": [
            {
                "id": "BEH-M6-SAVE", "object_type": "BEHAVIOR", "subtype": "document-save",
                "label": "Save current document", "coverage": "MAPPED",
                "attributes": {
                    "trigger": "User invokes Save",
                    "observable_response": "The Save route reaches the recovered save handler",
                    "uncertainty": "Only the recovered static route is asserted",
                },
            },
            {
                "id": "RA-M6-SAVE", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior",
                "label": "Preserve Save semantics", "coverage": "MAPPED",
                "attributes": {
                    "property": "A human-facing Save control must reach the save behavior.",
                    "fidelity_test": "Invoke Save and verify the control reaches the save behavior.",
                    "uncertainty": "Runtime persistence details are outside this fixture.",
                },
            },
        ],
        "relations": [
            {"src": save_id, "dst": "BEH-M6-SAVE", "kind": "supports"},
            {"src": "BEH-M6-SAVE", "dst": "RA-M6-SAVE", "kind": "supports_anchor"},
        ],
    }


class M6ReconstructionTrialTests(unittest.TestCase):
    def _source_cert(self, td: Path):
        root = Path(__file__).resolve().parents[1]
        write_package_manifest(root)
        specimen = td / "original_secret_specimen"
        specimen.mkdir()
        (specimen / "MainWindow.ui").write_text(UI, encoding="utf-8")
        (specimen / "MainWindow.cpp").write_text(CPP, encoding="utf-8")
        mechanical = td / "mechanical"
        self.assertEqual(certify_specimen(root, specimen, mechanical, specimen_id="m6-hidden")["state"], "PASS")
        store = Store(mechanical / "scan" / "scan_index.sqlite", readonly=True)
        save = next(o for o in store.semantic_objects() if o["label"] == "actionSave")
        store.close()
        p = td / "proposal.json"
        p.write_text(json.dumps(proposal(save["id"])), encoding="utf-8")
        semantic = td / "semantic"
        self.assertEqual(certify_reconstruction_handoff(root, mechanical, p, semantic)["state"], "PASS")
        return root, specimen, semantic

    def _submission(self, td: Path, challenge_id: str, *, network=False, challenge_override=None):
        path = td / "submission.json"
        path.write_text(json.dumps({
            "schema_version": SUBMISSION_SCHEMA,
            "challenge_id": challenge_override or challenge_id,
            "agent": {"name": "test-coding-agent", "version": "1", "provider": "fixture"},
            "source_isolation": {
                "original_source_accessed": False,
                "parent_certification_accessed": False,
                "evaluator_bundle_accessed": False,
                "network_source_lookup_used": network,
                "enforcement_level": "TEST_HARNESS",
            },
            "notes": "source-blind synthetic regression",
        }), encoding="utf-8")
        return path

    def _candidate(self, td: Path, *, good=True):
        c = td / ("candidate_good" if good else "candidate_bad")
        c.mkdir()
        (c / "MainWindow.ui").write_text(UI if good else MISSING_UI, encoding="utf-8")
        (c / "MainWindow.cpp").write_text(CPP if good else MISSING_CPP, encoding="utf-8")
        return c

    def test_prepare_trial_splits_source_free_challenge_from_private_evaluator(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            _, specimen, semantic = self._source_cert(td)
            challenge, evaluator = td / "challenge", td / "evaluator"
            result = prepare_reconstruction_trial(semantic, challenge, evaluator)
            self.assertEqual(result["state"], "PASS")
            self.assertTrue((challenge / CHALLENGE_MANIFEST).is_file())
            self.assertTrue((evaluator / EVALUATOR_MANIFEST).is_file())
            self.assertFalse((challenge / "scan_index.sqlite").exists())
            self.assertFalse((challenge / "evidence_catalog.json").exists())
            combined = "\n".join(p.read_text(encoding="utf-8") for p in challenge.iterdir() if p.is_file())
            self.assertNotIn(str(specimen), combined)
            self.assertNotIn("connect(ui->actionSave", combined)
            self.assertNotIn("source_file_ids", combined)
            self.assertIn("Save", combined)
            ev = json.loads((evaluator / "evaluator.json").read_text(encoding="utf-8"))
            self.assertEqual(ev["challenge_id"], result["challenge_id"])
            self.assertEqual(len(ev["anchor_expectations"]), 1)
            self.assertTrue(ev["anchor_expectations"][0]["scorable"])

    def test_source_blind_matching_candidate_scores_pass_and_trial_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, _, semantic = self._source_cert(td)
            result = prepare_reconstruction_trial(semantic, td / "challenge", td / "evaluator")
            submission = self._submission(td, result["challenge_id"])
            trial = td / "trial"
            scored = score_reconstruction_trial(root, td / "evaluator", self._candidate(td, good=True), submission, trial)
            self.assertEqual(scored["state"], "PASS")
            self.assertEqual(scored["scorecard"]["anchor_counts"]["PASS"], 1)
            self.assertEqual(scored["scorecard"]["fidelity_score"], 1.0)
            self.assertEqual(verify_reconstruction_trial(trial)["state"], "PASS")
            self.assertTrue((trial / TRIAL_MANIFEST).is_file())
            receipt = json.loads((trial / "trial_receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["blindness"]["challenge_packaging"], "MECHANICALLY_SOURCE_FREE")
            self.assertEqual(receipt["agent"]["name"], "test-coding-agent")

    def test_missing_strongly_evidenced_surface_is_attributed_to_reconstruction_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, _, semantic = self._source_cert(td)
            prepared = prepare_reconstruction_trial(semantic, td / "challenge", td / "evaluator")
            submission = self._submission(td, prepared["challenge_id"])
            scored = score_reconstruction_trial(root, td / "evaluator", self._candidate(td, good=False), submission, td / "trial")
            self.assertEqual(scored["state"], "FAIL")
            anchor = scored["scorecard"]["anchor_results"][0]
            self.assertEqual(anchor["state"], "FAIL")
            self.assertEqual(anchor["attribution"], "RECONSTRUCTION_AGENT")

    def test_submission_that_admits_source_lookup_is_rejected_before_candidate_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, _, semantic = self._source_cert(td)
            prepared = prepare_reconstruction_trial(semantic, td / "challenge", td / "evaluator")
            submission = self._submission(td, prepared["challenge_id"], network=True)
            scored = score_reconstruction_trial(root, td / "evaluator", self._candidate(td), submission, td / "trial")
            self.assertEqual(scored["state"], "INVALID")
            self.assertEqual(scored["reason"], "SOURCE_ISOLATION_OR_SUBMISSION_INVALID")
            self.assertFalse((td / "trial").exists())

    def test_wrong_challenge_submission_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, _, semantic = self._source_cert(td)
            prepared = prepare_reconstruction_trial(semantic, td / "challenge", td / "evaluator")
            submission = self._submission(td, prepared["challenge_id"], challenge_override="challenge:wrong")
            scored = score_reconstruction_trial(root, td / "evaluator", self._candidate(td), submission, td / "trial")
            self.assertEqual(scored["state"], "INVALID")
            self.assertIn("challenge_id_mismatch", scored["submission"]["issues"])

    def test_private_evaluator_tamper_is_detected_before_scoring(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, _, semantic = self._source_cert(td)
            prepared = prepare_reconstruction_trial(semantic, td / "challenge", td / "evaluator")
            (td / "evaluator" / "evaluator.json").write_text("{}", encoding="utf-8")
            submission = self._submission(td, prepared["challenge_id"])
            scored = score_reconstruction_trial(root, td / "evaluator", self._candidate(td), submission, td / "trial")
            self.assertEqual(scored["state"], "INVALID")
            self.assertEqual(scored["reason"], "EVALUATOR_INVALID")

    def test_trial_tamper_is_detected_after_scoring(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, _, semantic = self._source_cert(td)
            prepared = prepare_reconstruction_trial(semantic, td / "challenge", td / "evaluator")
            submission = self._submission(td, prepared["challenge_id"])
            trial = td / "trial"
            self.assertEqual(score_reconstruction_trial(root, td / "evaluator", self._candidate(td), submission, trial)["state"], "PASS")
            (trial / "scorecard.json").write_text("{}", encoding="utf-8")
            verify = verify_reconstruction_trial(trial)
            self.assertEqual(verify["state"], "FAIL")
            self.assertGreater(verify["issue_count"], 0)

    def test_public_challenge_bundle_is_deterministic_for_same_certification(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            _, _, semantic = self._source_cert(td)
            b1, b2 = td / "challenge1.zip", td / "challenge2.zip"
            r1 = prepare_reconstruction_trial(semantic, td / "c1", td / "e1", challenge_bundle=b1)
            r2 = prepare_reconstruction_trial(semantic, td / "c2", td / "e2", challenge_bundle=b2)
            self.assertEqual(r1["challenge_id"], r2["challenge_id"])
            self.assertEqual(hashlib.sha256(b1.read_bytes()).hexdigest(), hashlib.sha256(b2.read_bytes()).hexdigest())

    def test_partial_source_terminals_are_advisory_when_all_mapped_requirements_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = Path(__file__).resolve().parents[1]
            write_package_manifest(root)
            specimen = td / "source_with_mixed_effects"
            specimen.mkdir()
            (specimen / "MainWindow.ui").write_text(UI, encoding="utf-8")
            (specimen / "MainWindow.cpp").write_text('''#include <QAction>
#include <QProcess>
#include <QFile>
void MainWindow::wire(){ connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile); }
void MainWindow::saveFile(){ QProcess::startDetached("echo", {"x"}); QFile output("x"); output.write("x"); }
''', encoding="utf-8")
            mechanical = td / "mechanical"
            self.assertEqual(certify_specimen(root, specimen, mechanical, specimen_id="m6-mixed")["state"], "PASS")
            store = Store(mechanical / "scan" / "scan_index.sqlite", readonly=True)
            save = next(o for o in store.semantic_objects() if o["label"] == "actionSave")
            store.close()
            pth = td / "proposal.json"
            pth.write_text(json.dumps(proposal(save["id"])), encoding="utf-8")
            semantic = td / "semantic"
            self.assertEqual(certify_reconstruction_handoff(root, mechanical, pth, semantic)["state"], "PASS")
            prepared = prepare_reconstruction_trial(semantic, td / "challenge", td / "evaluator")
            public = json.loads((td / "challenge" / "challenge.json").read_text(encoding="utf-8"))
            terms = public["reconstruction_requirements"][0]["surface_requirements"][0]
            self.assertTrue(any(t.get("effect_type") == "subprocess_launch" for t in terms["required_mapped_terminals"]))
            self.assertTrue(terms["uncertain_terminals_not_required_for_binary_failure"])
            candidate = td / "candidate"
            candidate.mkdir()
            (candidate / "MainWindow.ui").write_text(UI, encoding="utf-8")
            (candidate / "MainWindow.cpp").write_text('''#include <QAction>
#include <QProcess>
void MainWindow::wire(){ connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile); }
void MainWindow::saveFile(){ QProcess::startDetached("echo", {"x"}); }
''', encoding="utf-8")
            submission = self._submission(td, prepared["challenge_id"])
            scored = score_reconstruction_trial(root, td / "evaluator", candidate, submission, td / "trial")
            self.assertEqual(scored["state"], "PASS")
            self.assertEqual(scored["scorecard"]["anchor_results"][0]["state"], "PASS")


if __name__ == "__main__":
    unittest.main()
