from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from scan.engine import ScanEngine
from scan.inventory import git_blob_sha1


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "qt_sample"


class Stage1Tests(unittest.TestCase):
    def test_mechanical_surface_and_nest_extraction(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            summary = ScanEngine().scan(FIXTURE, out, "fixture@1")
            self.assertEqual(summary["inventory"]["file_count"], 4)
            names = {(n["kind"], n["name"]) for n in summary["nodes"]}
            self.assertIn(("human_surface", "actionSave"), names)
            self.assertIn(("human_surface", "actionGhost"), names)
            self.assertTrue(any(k == "surface_factory_output" for k, _ in names))
            self.assertTrue(any(n["kind"] == "nest_boundary" and n["name"] == "subprocess" for n in summary["nodes"]))
            self.assertTrue(any(e["kind"] == "dispatches_to" for e in summary["edges"]))
            self.assertTrue(any(n["kind"] == "handler_reference" and n["name"] == "App::checkpoint" for n in summary["nodes"]))
            timer = [n for n in summary["nodes"] if n["kind"] == "recurrence_source" and n["name"] == "checkpointTimer"]
            self.assertTrue(timer)
            self.assertEqual(json.loads(timer[-1]["attributes_json"])["interval_expression"], "60 * 1000")
            self.assertTrue(any(n["kind"] == "handler_reference" and n["name"].startswith("lambda@") for n in summary["nodes"]))
            self.assertTrue((out / "machine_body_map.json").exists())
            self.assertTrue((out / "scan_index.sqlite").exists())
            db = sqlite3.connect(out / "scan_index.sqlite")
            ghost = db.execute("""
                SELECT n.name FROM nodes n
                WHERE n.kind='human_surface' AND n.name='actionGhost'
                AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.src=n.id AND e.kind IN ('dispatches_to','emits'))
            """).fetchone()
            save = db.execute("""
                SELECT n.name FROM nodes n
                WHERE n.kind='human_surface' AND n.name='actionSave'
                AND EXISTS (SELECT 1 FROM edges e WHERE e.src=n.id AND e.kind IN ('dispatches_to','emits'))
            """).fetchone()
            self.assertEqual(ghost[0], "actionGhost")
            self.assertEqual(save[0], "actionSave")
            db.close()

    def test_second_scan_uses_cache(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            ScanEngine().scan(FIXTURE, out, "fixture@1")
            second = ScanEngine().scan(FIXTURE, out, "fixture@1")
            self.assertGreater(second["extraction"]["cache_hits"], 0)


class ManifestAcquisitionTests(unittest.TestCase):
    def test_metadata_only_manifest_is_accounted_but_not_parsed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            manifest = td / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "scan-source-manifest/0.1",
                "specimen": {
                    "specimen_id": "owner/repo@abc",
                    "provider": "github",
                    "repository": "owner/repo",
                    "revision": "abc",
                    "tree_sha": "tree123",
                },
                "files": [
                    {"path": "src/main.cpp", "size": 42, "sha": "blob1", "type": "blob", "mode": "100644"},
                    {"path": "ui/Main.ui", "size": 99, "sha": "blob2", "type": "blob", "mode": "100644"},
                ],
            }), encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan_manifest(manifest, out)
            self.assertEqual(summary["inventory"]["file_count"], 2)
            self.assertEqual(summary["inventory"]["metadata_only_file_count"], 2)
            self.assertEqual(summary["inventory"]["materialized_file_count"], 0)
            self.assertEqual(summary["extraction"]["node_count"], 0)
            self.assertEqual(summary["specimen"]["fingerprint"]["value"], "tree123")
            self.assertTrue(any(f["kind"] == "acquisition_gap" for f in summary["findings"]))
            db = sqlite3.connect(out / "scan_index.sqlite")
            row = db.execute("SELECT COUNT(*) FROM files WHERE content_available=0 AND coverage='PARTIAL'").fetchone()
            db.close()
            self.assertEqual(row[0], 2)

    def test_manifest_materializes_only_present_files(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            content = td / "content"
            (content / "ui").mkdir(parents=True)
            ui_text = '''<?xml version="1.0"?><ui version="4.0"><widget class="QMainWindow" name="Main"><action name="actionSave"><property name="text"><string>Save</string></property></action></widget></ui>'''
            (content / "ui" / "Main.ui").write_text(ui_text, encoding="utf-8")
            ui_git_sha = git_blob_sha1(ui_text.encode("utf-8"))
            manifest = td / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "scan-source-manifest/0.1",
                "specimen": {"specimen_id": "owner/repo@abc", "provider": "github", "tree_sha": "tree123"},
                "files": [
                    {"path": "ui/Main.ui", "size": len(ui_text.encode("utf-8")), "sha": ui_git_sha, "type": "blob"},
                    {"path": "src/missing.cpp", "size": 42, "sha": "0" * 40, "type": "blob"},
                ],
            }), encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan_manifest(manifest, out, content)
            self.assertEqual(summary["inventory"]["materialized_file_count"], 1)
            self.assertEqual(summary["inventory"]["metadata_only_file_count"], 1)
            self.assertTrue(any(n["kind"] == "human_surface" and n["name"] == "actionSave" for n in summary["nodes"]))
            missing = [f for f in summary["files"] if f["path"] == "src/missing.cpp"][0]
            self.assertEqual(missing["coverage"], "PARTIAL")
            self.assertEqual(missing["content_available"], 0)


if __name__ == "__main__":
    unittest.main()
