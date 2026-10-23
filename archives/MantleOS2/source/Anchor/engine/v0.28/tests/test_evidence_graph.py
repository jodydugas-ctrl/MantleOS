from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scan.engine import ScanEngine
from scan.evidence_graph import ingest_overlay, trace_impact, trace_why
from scan.store import Store


UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <action name="actionSave">
   <property name="text"><string>Save</string></property>
  </action>
 </widget>
</ui>
'''
CPP = '''#include <QAction>
void MainWindow::wire() {
    connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile);
}
void MainWindow::saveFile() {}
'''


class EvidenceGraphTests(unittest.TestCase):
    def _scan(self, td: Path):
        specimen = td / "specimen"
        specimen.mkdir()
        (specimen / "MainWindow.ui").write_text(UI)
        (specimen / "MainWindow.cpp").write_text(CPP)
        out = td / "scan"
        summary = ScanEngine().scan(specimen, out, "fixture@example")
        return out, summary

    def test_scan_exports_normalized_evidence_graph_and_completeness_vector(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, summary = self._scan(Path(tmp))
            self.assertEqual(summary["schema_version"], "scan-machine-body-map/0.9")
            self.assertTrue((out / "scan_index.sqlite").exists())
            self.assertTrue((out / "evidence_graph.json").exists())
            self.assertTrue((out / "evidence_catalog.json").exists())
            self.assertTrue((out / "completeness_vector.json").exists())

            graph = json.loads((out / "evidence_graph.json").read_text())
            self.assertEqual(graph["schema_version"], "scan-evidence-graph/0.2")
            kinds = {x["object_type"] for x in graph["objects"]}
            self.assertTrue({"SPECIMEN", "FILE", "EVIDENCE", "ANATOMICAL_OBJECT", "GRAPH_RELATION"}.issubset(kinds))
            relation_kinds = {x["kind"] for x in graph["relations"]}
            self.assertIn("contains_evidence", relation_kinds)
            self.assertIn("supports", relation_kinds)

            cv = json.loads((out / "completeness_vector.json").read_text())
            self.assertEqual(cv["schema_version"], "scan-completeness-vector/0.2")
            self.assertNotIn("completion_percentage", cv)
            keys = {x["key"] for x in cv["dimensions"]}
            self.assertIn("human-surfaces", keys)
            self.assertIn("reconstruction-anchors", keys)

    def test_anchor_can_be_traced_to_exact_evidence_and_impact_reversed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, summary = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            save_nodes = [x for x in store.semantic_objects() if x["label"] == "actionSave"]
            self.assertTrue(save_nodes)
            save_id = save_nodes[0]["id"]
            incoming = store.incoming_semantic_relations(save_id)
            support = [r for r in incoming if r["kind"] == "supports"]
            self.assertTrue(support)
            evidence_id = support[0]["src"]

            overlay = {
                "schema_version": "scan-semantic-overlay/0.1",
                "objects": [
                    {"id": "IN-TEST-SAVE", "object_type": "INTERPRETATION", "subtype": "behavior-meaning", "label": "Save action reaches document save behavior", "coverage": "MAPPED"},
                    {"id": "RA-TEST-SAVE", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior", "label": "A Save control must preserve current-document save semantics", "coverage": "MAPPED"},
                ],
                "relations": [
                    {"src": save_id, "dst": "IN-TEST-SAVE", "kind": "supports"},
                    {"src": "IN-TEST-SAVE", "dst": "RA-TEST-SAVE", "kind": "supports_anchor"},
                ],
                "completeness": [
                    {"key": "reconstruction-anchors", "label": "Reconstruction anchor traceability", "state": "PARTIAL", "attributes": {"fixture": True}}
                ],
            }
            ingest_overlay(store, overlay)

            why = trace_why(store, "RA-TEST-SAVE")
            why_ids = {o["id"] for o in why["objects"]}
            self.assertIn("IN-TEST-SAVE", why_ids)
            self.assertIn(save_id, why_ids)
            self.assertIn(evidence_id, why_ids)
            self.assertTrue(why["proof_complete"])
            self.assertIn(evidence_id, why["evidence_reached"])
            evidence_objects = [o for o in why["objects"] if o["id"] == evidence_id]
            self.assertEqual(evidence_objects[0]["object_type"], "EVIDENCE")
            self.assertEqual(evidence_objects[0]["attributes"]["path"], "MainWindow.ui")
            self.assertIsNotNone(evidence_objects[0]["attributes"]["start_line"])

            impact = trace_impact(store, evidence_id)
            impact_ids = {o["id"] for o in impact["objects"]}
            self.assertIn(save_id, impact_ids)
            self.assertIn("IN-TEST-SAVE", impact_ids)
            self.assertIn("RA-TEST-SAVE", impact_ids)
            self.assertIn("RA-TEST-SAVE", impact["reconstruction_anchors_reached"])
            store.close()

    def test_overlay_rejects_dangling_claim_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            overlay = {
                "schema_version": "scan-semantic-overlay/0.1",
                "objects": [{"id": "RA-X", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior", "label": "x"}],
                "relations": [{"src": "MISSING", "dst": "RA-X", "kind": "supports_anchor"}],
            }
            with self.assertRaises(ValueError):
                ingest_overlay(store, overlay)
            store.close()


if __name__ == "__main__":
    unittest.main()
