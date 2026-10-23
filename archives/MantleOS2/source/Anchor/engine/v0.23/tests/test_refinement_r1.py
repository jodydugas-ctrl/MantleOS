from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scan.engine import ScanEngine
from scan.evidence_graph import ingest_overlay, trace_why
from scan.integrity import audit_integrity, surface_closure
from scan.store import Store


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


class RefinementR1Tests(unittest.TestCase):
    def _scan(self, td: Path, specimen_id: str = "r1@example"):
        root = td / "specimen"
        root.mkdir()
        (root / "MainWindow.ui").write_text(UI, encoding="utf-8")
        (root / "MainWindow.cpp").write_text(CPP, encoding="utf-8")
        out = td / "out"
        summary = ScanEngine().scan(root, out, specimen_id)
        return root, out, summary

    def test_stable_semantic_and_evidence_ids_repeat_across_clean_runs(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            _, out_a, _ = self._scan(Path(a))
            _, out_b, _ = self._scan(Path(b))
            ga = json.loads((out_a / "evidence_graph.json").read_text())
            gb = json.loads((out_b / "evidence_graph.json").read_text())
            self.assertEqual({o["id"] for o in ga["objects"]}, {o["id"] for o in gb["objects"]})
            self.assertEqual({r["id"] for r in ga["relations"]}, {r["id"] for r in gb["relations"]})

    def test_surface_closure_accounts_for_bound_and_unresolved_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            by_name = {r["name"]: r for r in closure["records"]}
            self.assertEqual(by_name["actionSave"]["closure"], "BOUND")
            self.assertEqual(by_name["actionGhost"]["closure"], "UNRESOLVED")
            self.assertEqual(closure["state"], "PARTIAL")
            self.assertGreaterEqual(closure["unresolved_count"], 1)

    def test_anchor_without_evidence_path_is_integrity_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            ingest_overlay(store, {
                "schema_version": "scan-semantic-overlay/0.1",
                "objects": [{"id": "RA-NOPROOF", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior", "label": "Unsupported anchor"}],
                "relations": [],
            })
            audit = audit_integrity(store)
            store.close()
            matches = [i for i in audit["issues"] if i["code"] == "CLAIM_WITHOUT_EVIDENCE_PATH" and i["attributes"].get("object_id") == "RA-NOPROOF"]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["severity"], "ERROR")
            self.assertEqual(audit["state"], "BLOCKED")

    def test_typed_overlay_relation_vocabulary_rejects_unknown_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            surface = next(o for o in store.semantic_objects() if o["label"] == "actionSave")
            payload = {
                "schema_version": "scan-semantic-overlay/0.1",
                "objects": [{"id": "IN-X", "object_type": "INTERPRETATION", "subtype": "meaning", "label": "x"}],
                "relations": [{"src": surface["id"], "dst": "IN-X", "kind": "sort_of_related_to"}],
            }
            with self.assertRaises(ValueError):
                ingest_overlay(store, payload)
            store.close()

    def test_source_digest_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            ev = next(o for o in store.semantic_objects() if o["object_type"] == "EVIDENCE" and o["attributes"].get("source_sha256"))
            file_id = ev["attributes"]["source_file_id"]
            file_obj = store.semantic_object(file_id)
            file_obj["attributes"]["sha256"] = "0" * 64
            store.put_semantic_objects([file_obj])
            audit = audit_integrity(store)
            store.close()
            self.assertTrue(any(i["code"] == "EVIDENCE_SOURCE_DIGEST_MISMATCH" for i in audit["issues"]))

    def test_positive_proof_cycle_is_reported_without_erasing_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            surface = next(o for o in store.semantic_objects() if o["label"] == "actionSave")
            ingest_overlay(store, {
                "schema_version": "scan-semantic-overlay/0.1",
                "objects": [
                    {"id": "IN-A", "object_type": "INTERPRETATION", "subtype": "meaning", "label": "A"},
                    {"id": "IN-B", "object_type": "INTERPRETATION", "subtype": "meaning", "label": "B"},
                ],
                "relations": [
                    {"src": surface["id"], "dst": "IN-A", "kind": "supports"},
                    {"src": "IN-A", "dst": "IN-B", "kind": "supports"},
                    {"src": "IN-B", "dst": "IN-A", "kind": "supports"},
                ],
            })
            audit = audit_integrity(store)
            why = trace_why(store, "IN-B")
            store.close()
            self.assertTrue(any(i["code"] == "PROOF_CYCLE" for i in audit["issues"]))
            self.assertTrue(any(o["id"] == surface["id"] for o in why["objects"]))


    def test_ingest_knowledge_refreshes_projection_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            _, out, _ = self._scan(td)
            store = Store(out / "scan_index.sqlite")
            surface = next(o for o in store.semantic_objects() if o["label"] == "actionSave")
            store.close()
            overlay = td / "overlay.json"
            overlay.write_text(json.dumps({
                "schema_version": "scan-semantic-overlay/0.1",
                "objects": [
                    {"id": "IN-PROJ", "object_type": "INTERPRETATION", "subtype": "meaning", "label": "save meaning"},
                    {"id": "RA-PROJ", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior", "label": "save anchor"},
                ],
                "relations": [
                    {"src": surface["id"], "dst": "IN-PROJ", "kind": "supports"},
                    {"src": "IN-PROJ", "dst": "RA-PROJ", "kind": "supports_anchor"},
                ],
            }), encoding="utf-8")
            from scan.cli import main
            self.assertEqual(main(["ingest-knowledge", str(out / "scan_index.sqlite"), str(overlay), "--out-dir", str(out)]), 0)
            import hashlib
            body = json.loads((out / "machine_body_map.json").read_text())
            self.assertTrue(body.get("semantic_projection_refreshed"))
            self.assertGreaterEqual(body["semantic_graph"]["objects"], 2)
            dims = {d["key"]: d for d in body["completeness_vector"]}
            self.assertEqual(dims["reconstruction-anchors"]["state"], "MAPPED")
            manifest = json.loads((out / "projection_manifest.json").read_text())
            for rec in manifest["projections"]:
                data = (out / rec["name"]).read_bytes()
                self.assertEqual(len(data), rec["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), rec["sha256"])

    def test_projection_integrity_outputs_are_emitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out, summary = self._scan(Path(tmp))
            self.assertEqual(summary["schema_version"], "scan-machine-body-map/0.9")
            for name in ("integrity_report.json", "surface_closure.json", "projection_manifest.json"):
                self.assertTrue((out / name).exists(), name)
            manifest = json.loads((out / "projection_manifest.json").read_text())
            names = {x["name"] for x in manifest["projections"]}
            self.assertIn("evidence_graph.json", names)
            self.assertIn("integrity_report.json", names)


if __name__ == "__main__":
    unittest.main()
