from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import json

from scan.adapters.base import Adapter
from scan.engine import ScanEngine
from scan.inventory import FileRecord
from scan.model import ExtractionResult, Evidence, Node, stable_id


class CrashAdapter(Adapter):
    name = "crash_adapter"
    version = "1"

    def accepts(self, record: FileRecord) -> bool:
        return record.path.endswith(".cpp")

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        if "CRASH_ME" in text:
            raise RuntimeError("synthetic parser failure")
        out = ExtractionResult()
        eid = stable_id("evidence", record.id, self.name, "ok")
        nid = stable_id("node", self.name, record.id)
        out.evidence.append(Evidence(eid, record.id, record.path, 1, 1, "MEASURED", self.name, "parsed"))
        out.nodes.append(Node(nid, "synthetic_symbol", record.path, record.id, record.path, "MAPPED", {}, [eid]))
        return out


class MemoryCrashAdapter(CrashAdapter):
    name = "memory_crash_adapter"

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        raise MemoryError("synthetic exhaustion")


class ParserIsolationTests(unittest.TestCase):
    def test_adapter_failure_is_explicit_and_other_files_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            (specimen / "bad.cpp").write_text("CRASH_ME\n", encoding="utf-8")
            (specimen / "good.cpp").write_text("int good = 1;\n", encoding="utf-8")
            out = td / "out"
            summary = ScanEngine(adapters=[CrashAdapter()]).scan(specimen, out, "parser-isolation")

            failures = [f for f in summary["findings"] if f["kind"] == "parser_failure"]
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["status"], "PARTIAL")
            self.assertEqual(json.loads(failures[0]["attributes_json"])["adapter"], "crash_adapter")
            bad = next(f for f in summary["files"] if f["path"] == "bad.cpp")
            good = next(f for f in summary["files"] if f["path"] == "good.cpp")
            self.assertEqual(bad["coverage"], "PARTIAL")
            self.assertTrue(json.loads(bad["attributes_json"])["adapter_failures"])
            self.assertEqual(good["coverage"], "MAPPED")
            self.assertEqual(summary["extraction"]["node_count"], 1)
            self.assertEqual(summary["extraction"]["adapter_runs"]["crash_adapter:FAILED"], 1)
            self.assertTrue((out / "projection_manifest.json").is_file())

    def test_one_adapter_can_fail_while_another_still_extracts_same_file(self):
        class SurvivorAdapter(CrashAdapter):
            name = "survivor"
            def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
                out = ExtractionResult()
                eid = stable_id("evidence", record.id, self.name, "survived")
                nid = stable_id("node", self.name, record.id)
                out.evidence.append(Evidence(eid, record.id, record.path, 1, 1, "MEASURED", self.name, "survived"))
                out.nodes.append(Node(nid, "survivor", record.path, record.id, record.path, "MAPPED", {}, [eid]))
                return out

        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            (specimen / "bad.cpp").write_text("CRASH_ME\n", encoding="utf-8")
            summary = ScanEngine(adapters=[CrashAdapter(), SurvivorAdapter()]).scan(specimen, td / "out", "multi-adapter")
            self.assertEqual(summary["extraction"]["node_count"], 1)
            self.assertEqual(summary["files"][0]["coverage"], "PARTIAL")
            self.assertEqual(sum(1 for f in summary["findings"] if f["kind"] == "parser_failure"), 1)

    def test_memory_error_is_not_downgraded_to_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            (specimen / "x.cpp").write_text("int x;\n", encoding="utf-8")
            with self.assertRaises(MemoryError):
                ScanEngine(adapters=[MemoryCrashAdapter()]).scan(specimen, td / "out", "fatal-memory")

    def test_malformed_qt_ui_stays_explicit_without_crashing_scan(self):
        from scan.adapters.qt_ui import QtUiAdapter
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            (specimen / "broken.ui").write_text("<ui><widget>", encoding="utf-8")
            summary = ScanEngine(adapters=[QtUiAdapter()]).scan(specimen, td / "out", "malformed-ui")
            gaps = [f for f in summary["findings"] if f["kind"] == "parser_gap"]
            self.assertEqual(len(gaps), 1)
            self.assertEqual(gaps[0]["status"], "BLOCKED")
            self.assertEqual(summary["integrity"]["issue_count"], 0)


if __name__ == "__main__":
    unittest.main()
