from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scan.cli import main
from scan.engine import ScanEngine
from scan.reconstruction import (
    export_reconstruction_contract,
    promote_reconstruction_proposal,
    validate_reconstruction_proposal,
)
from scan.store import Store
from scan.release import (
    CERTIFICATION_MANIFEST, certify_reconstruction_handoff, certify_specimen, verify_certification,
    write_package_manifest,
)


UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <action name="actionSave"><property name="text"><string>Save</string></property></action>
  <action name="actionGhost"><property name="text"><string>Ghost</string></property></action>
 </widget>
</ui>
'''
CPP = '''#include <QAction>
void MainWindow::wire() {
    connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile);
}
void MainWindow::saveFile() {}
'''


def proposal(save_id: str, *, behavior_coverage: str = "MAPPED", anchor_coverage: str = "MAPPED"):
    return {
        "schema_version": "scan-reconstruction-proposal/0.1",
        "proposal_id": "RP-SAVE-001",
        "objects": [
            {
                "id": "BEH-SAVE-001", "object_type": "BEHAVIOR", "subtype": "document-save",
                "label": "Save the current document", "coverage": behavior_coverage,
                "attributes": {
                    "trigger": "User invokes the Save action",
                    "preconditions": "A current document exists",
                    "observable_response": "The current document is passed into the application's save pathway",
                    "state_transition": "Document may transition from modified to persisted",
                    "persistence_effect": "Document bytes are intended for durable storage",
                    "error_behavior": "Preserve source-observed save failure semantics where known",
                    "uncertainty": "Native/framework details remain limited to evidence recovered by the scan",
                },
            },
            {
                "id": "RA-SAVE-001", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior",
                "label": "A Save control preserves current-document save semantics", "coverage": anchor_coverage,
                "attributes": {
                    "property": "A human-accessible Save route must invoke the reconstructed current-document save behavior.",
                    "fidelity_test": "Invoke Save on a modified document and verify the reconstructed route reaches the save behavior and preserves supported feedback/error semantics.",
                    "uncertainty": "Do not infer framework-native details absent from the evidence graph.",
                },
            },
        ],
        "relations": [
            {"src": save_id, "dst": "BEH-SAVE-001", "kind": "supports"},
            {"src": "BEH-SAVE-001", "dst": "RA-SAVE-001", "kind": "supports_anchor"},
        ],
    }


class M5ReconstructionPromotionTests(unittest.TestCase):
    def _scan(self, td: Path):
        specimen = td / "specimen"
        specimen.mkdir()
        (specimen / "MainWindow.ui").write_text(UI, encoding="utf-8")
        (specimen / "MainWindow.cpp").write_text(CPP, encoding="utf-8")
        out = td / "scan"
        ScanEngine().scan(specimen, out, "m5@example")
        store = Store(out / "scan_index.sqlite")
        save = next(o for o in store.semantic_objects() if o["label"] == "actionSave")
        ghost = next(o for o in store.semantic_objects() if o["label"] == "actionGhost")
        return out, store, save, ghost

    def test_valid_proposal_promotes_evidence_backed_behavior_and_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, store, save, _ = self._scan(Path(tmp))
            contract = out / "reconstruction_contract.json"
            result = promote_reconstruction_proposal(store, proposal(save["id"]), contract_path=contract)
            self.assertEqual(result["state"], "PROMOTED")
            self.assertEqual(result["validation"]["state"], "PASS")
            self.assertEqual(result["integrity_state"], "MAPPED")
            self.assertIsNotNone(store.semantic_object("RA-SAVE-001"))
            payload = json.loads(contract.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "scan-reconstruction-contract/0.1")
            self.assertEqual(payload["anchor_count"], 1)
            self.assertEqual(payload["behavior_count"], 1)
            anchor = payload["anchors"][0]
            self.assertTrue(anchor["proof_complete"])
            self.assertTrue(anchor["evidence_ids"])
            self.assertTrue(anchor["source_file_ids"])
            self.assertEqual(anchor["attributes"]["property"], proposal(save["id"])["objects"][1]["attributes"]["property"])
            store.close()

    def test_unsupported_anchor_is_rejected_without_mutating_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, store, _, _ = self._scan(Path(tmp))
            before = {o["id"] for o in store.semantic_objects()}
            bad = {
                "schema_version": "scan-reconstruction-proposal/0.1",
                "proposal_id": "RP-BAD",
                "objects": [{
                    "id": "RA-BAD", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior",
                    "label": "Unsupported", "coverage": "PARTIAL",
                    "attributes": {"property": "x", "fidelity_test": "test x", "uncertainty": "unknown"},
                }],
                "relations": [],
            }
            result = promote_reconstruction_proposal(store, bad)
            after = {o["id"] for o in store.semantic_objects()}
            self.assertEqual(result["state"], "REJECTED")
            self.assertEqual(before, after)
            codes = {i["code"] for i in result["validation"]["issues"]}
            self.assertIn("CLAIM_WITHOUT_EVIDENCE_PATH", codes)
            self.assertIn("ANCHOR_WITHOUT_TYPED_SUPPORT", codes)
            store.close()

    def test_mapped_anchor_cannot_escalate_partial_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, store, save, _ = self._scan(Path(tmp))
            result = validate_reconstruction_proposal(store, proposal(save["id"], behavior_coverage="PARTIAL", anchor_coverage="MAPPED"))
            self.assertEqual(result["state"], "FAIL")
            self.assertIn("ANCHOR_COVERAGE_ESCALATION", {i["code"] for i in result["issues"]})
            self.assertIsNone(store.semantic_object("RA-SAVE-001"))
            store.close()

    def test_partial_anchor_preserves_visible_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, store, save, ghost = self._scan(Path(tmp))
            p = proposal(save["id"], behavior_coverage="PARTIAL", anchor_coverage="PARTIAL")
            p["relations"].append({"src": ghost["id"], "dst": "BEH-SAVE-001", "kind": "contradicts"})
            result = promote_reconstruction_proposal(store, p, contract_path=out / "reconstruction_contract.json")
            self.assertEqual(result["state"], "PROMOTED")
            contract = json.loads((out / "reconstruction_contract.json").read_text(encoding="utf-8"))
            self.assertTrue(contract["anchors"][0]["contradictions"])
            self.assertEqual(contract["anchors"][0]["coverage"], "PARTIAL")
            store.close()

    def test_behavior_contract_fields_are_required_before_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, store, save, _ = self._scan(Path(tmp))
            p = proposal(save["id"])
            del p["objects"][0]["attributes"]["observable_response"]
            result = validate_reconstruction_proposal(store, p)
            self.assertEqual(result["state"], "FAIL")
            matches = [i for i in result["issues"] if i["code"] == "BEHAVIOR_CONTRACT_FIELD_MISSING"]
            self.assertTrue(any(i["attributes"].get("field") == "observable_response" for i in matches))
            store.close()

    def test_cli_promotion_refreshes_contract_and_projection_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            out, store, save, _ = self._scan(td)
            store.close()
            proposal_path = td / "proposal.json"
            proposal_path.write_text(json.dumps(proposal(save["id"])), encoding="utf-8")
            rc = main(["promote-reconstruction", str(out / "scan_index.sqlite"), str(proposal_path), "--out-dir", str(out)])
            self.assertEqual(rc, 0)
            contract = json.loads((out / "reconstruction_contract.json").read_text(encoding="utf-8"))
            self.assertEqual(contract["anchor_count"], 1)
            manifest = json.loads((out / "projection_manifest.json").read_text(encoding="utf-8"))
            rec = next(x for x in manifest["projections"] if x["name"] == "reconstruction_contract.json")
            data = (out / rec["name"]).read_bytes()
            self.assertEqual(rec["bytes"], len(data))
            self.assertEqual(rec["sha256"], hashlib.sha256(data).hexdigest())
            store = Store(out / "scan_index.sqlite")
            dims = {d["key"]: d for d in store.completeness_dimensions()}
            self.assertEqual(dims["reconstruction-anchors"]["state"], "MAPPED")
            store.close()

    def test_derived_reconstruction_certification_preserves_parent_and_seals_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = Path(__file__).resolve().parents[1]
            write_package_manifest(root)
            source = td / "source_cert"
            source_result = certify_specimen(root, root / "tests" / "fixtures" / "qualification_sample", source, specimen_id="m5-cert")
            self.assertEqual(source_result["state"], "PASS")
            parent_manifest_hash = hashlib.sha256((source / CERTIFICATION_MANIFEST).read_bytes()).hexdigest()
            store = Store(source / "scan" / "scan_index.sqlite", readonly=True)
            save = next(o for o in store.semantic_objects() if o["label"] == "actionSave")
            store.close()
            pth = td / "proposal.json"
            pth.write_text(json.dumps(proposal(save["id"])), encoding="utf-8")
            derived = td / "derived_cert"
            bundle = td / "derived.zip"
            result = certify_reconstruction_handoff(root, source, pth, derived, bundle_path=bundle)
            self.assertEqual(result["state"], "PASS")
            self.assertEqual(verify_certification(derived)["state"], "PASS")
            self.assertTrue((derived / "scan" / "reconstruction_contract.json").is_file())
            receipt = json.loads((derived / "certification_receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["semantic_promotion"]["promotion_state"], "PROMOTED")
            self.assertEqual(receipt["semantic_promotion"]["anchor_count"], 1)
            self.assertEqual(receipt["lineage"]["parent_certification_manifest"]["sha256"], parent_manifest_hash)
            self.assertEqual(hashlib.sha256((source / CERTIFICATION_MANIFEST).read_bytes()).hexdigest(), parent_manifest_hash)
            self.assertTrue(bundle.is_file())

    def test_derived_certification_rejects_bad_proposal_without_touching_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = Path(__file__).resolve().parents[1]
            write_package_manifest(root)
            source = td / "source_cert"
            self.assertEqual(certify_specimen(root, root / "tests" / "fixtures" / "qualification_sample", source, specimen_id="m5-reject")["state"], "PASS")
            parent_manifest_hash = hashlib.sha256((source / CERTIFICATION_MANIFEST).read_bytes()).hexdigest()
            bad = {
                "schema_version": "scan-reconstruction-proposal/0.1",
                "proposal_id": "RP-REJECT",
                "objects": [{
                    "id": "RA-REJECT", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior",
                    "label": "No proof", "coverage": "PARTIAL",
                    "attributes": {"property": "x", "fidelity_test": "x", "uncertainty": "unknown"},
                }],
                "relations": [],
            }
            pth = td / "bad.json"
            pth.write_text(json.dumps(bad), encoding="utf-8")
            derived = td / "derived_bad"
            result = certify_reconstruction_handoff(root, source, pth, derived)
            self.assertEqual(result["state"], "REJECTED")
            self.assertEqual(result["reason"], "RECONSTRUCTION_PROPOSAL_REJECTED")
            self.assertFalse(derived.exists())
            self.assertEqual(hashlib.sha256((source / CERTIFICATION_MANIFEST).read_bytes()).hexdigest(), parent_manifest_hash)
            self.assertEqual(verify_certification(source)["state"], "PASS")


if __name__ == "__main__":
    unittest.main()
