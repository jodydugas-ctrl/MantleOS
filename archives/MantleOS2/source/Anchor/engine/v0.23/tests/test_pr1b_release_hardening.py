from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scan import __version__
from scan.engine import ScanEngine
from scan.queries import RELEASE_ACCEPTANCE_QUERIES
from scan.release import run_query_acceptance, verify_package, verify_projection_manifest, write_package_manifest
from scan.store import Store


class AggregateBudgetTests(unittest.TestCase):
    def test_total_byte_budget_preserves_census_and_blocks_excess_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            (specimen / "a.cpp").write_text("void a(){}\n", encoding="utf-8")
            (specimen / "b.cpp").write_text("void b(){}\n", encoding="utf-8")
            first_size = (specimen / "a.cpp").stat().st_size
            summary = ScanEngine(max_total_bytes=first_size).scan(specimen, td / "out", "budget-bytes")
            self.assertEqual(summary["inventory"]["file_count"], 2)
            self.assertEqual(summary["inventory"]["materialized_file_count"], 1)
            blocked = [f for f in summary["files"] if f["acquisition_state"] == "RESOURCE_LIMIT_TOTAL_BYTES"]
            self.assertEqual(len(blocked), 1)
            self.assertTrue(summary["budget"]["triggered"])
            self.assertEqual(summary["budget"]["inventory_limit_states"]["RESOURCE_LIMIT_TOTAL_BYTES"], 1)

    def test_materialized_file_budget_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            for name in ("a.cpp", "b.cpp", "c.cpp"):
                (specimen / name).write_text(f"void {name[0]}(){{}}\n", encoding="utf-8")
            summary = ScanEngine(max_materialized_files=1).scan(specimen, td / "out", "budget-files")
            self.assertEqual(summary["inventory"]["file_count"], 3)
            self.assertEqual(summary["inventory"]["materialized_file_count"], 1)
            self.assertEqual(summary["inventory"]["acquisition_counts"]["RESOURCE_LIMIT_TOTAL_FILES"], 2)

    def test_graph_budget_stops_at_adapter_boundary_and_marks_partial(self):
        fixture = Path(__file__).parent / "fixtures" / "qualification_sample"
        with tempfile.TemporaryDirectory() as tmp:
            summary = ScanEngine(max_nodes=1).scan(fixture, Path(tmp) / "out", "budget-nodes")
            self.assertTrue(summary["budget"]["triggered"])
            self.assertEqual(summary["budget"]["reason"], "RESOURCE_LIMIT_NODES")
            self.assertLessEqual(summary["extraction"]["node_count"], 1)
            self.assertGreater(summary["budget"]["parser_eligible_files_not_fully_processed"], 0)
            self.assertTrue(any(f["kind"] == "scan_budget" for f in summary["findings"]))
            self.assertTrue(any(f["coverage"] == "PARTIAL" and f["content_available"] for f in summary["files"]))

    def test_external_cancellation_finishes_with_partial_outputs(self):
        fixture = Path(__file__).parent / "fixtures" / "qualification_sample"
        with tempfile.TemporaryDirectory() as tmp:
            summary = ScanEngine(cancel_check=lambda: True).scan(fixture, Path(tmp) / "out", "cancel")
            self.assertEqual(summary["budget"]["reason"], "CANCELLED")
            self.assertTrue((Path(tmp) / "out" / "projection_manifest.json").is_file())
            self.assertGreater(summary["budget"]["parser_eligible_files_not_fully_processed"], 0)


class ResumeAfterBudgetTests(unittest.TestCase):
    def test_budget_limited_run_can_resume_with_cache_and_complete(self):
        fixture = Path(__file__).parent / "fixtures" / "qualification_sample"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "scan"
            partial = ScanEngine(max_nodes=20).scan(fixture, out, "resume-budget")
            self.assertTrue(partial["budget"]["triggered"])
            full = ScanEngine().scan(fixture, out, "resume-budget")
            self.assertFalse(full["budget"]["triggered"])
            self.assertGreater(full["extraction"]["node_count"], partial["extraction"]["node_count"])
            self.assertGreater(full["extraction"]["cache_hits"], 0)
            self.assertEqual(full["integrity"]["issue_count"], 0)


class StoreRecoveryTests(unittest.TestCase):
    def test_corrupt_derived_database_is_quarantined_and_cleanly_rebuilt_on_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            (specimen / "x.cpp").write_text("void f(){}\n", encoding="utf-8")
            out = td / "out"
            out.mkdir()
            (out / "scan_index.sqlite").write_bytes(b"not a sqlite database")
            summary = ScanEngine().scan(specimen, out, "corrupt-rebuild")
            self.assertEqual(summary["store_recovery"]["state"], "CLEAN_REBUILD")
            self.assertEqual(summary["store_recovery"]["reason"], "DATABASE_CORRUPT")
            quarantined = Path(summary["store_recovery"]["quarantined_path"])
            self.assertTrue(quarantined.is_file())
            conn = sqlite3.connect(out / "scan_index.sqlite")
            self.assertEqual(conn.execute("PRAGMA quick_check").fetchone()[0], "ok")
            conn.close()

    def test_corrupt_database_is_not_silently_rebuilt_for_read_only_consumer(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "bad.sqlite"
            db.write_bytes(b"corrupt")
            with self.assertRaises(sqlite3.DatabaseError):
                Store(db)


class ReleaseQualificationTests(unittest.TestCase):
    def test_release_query_acceptance_surface_executes_all_required_queries(self):
        fixture = Path(__file__).parent / "fixtures" / "qualification_sample"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "scan"
            ScanEngine().scan(fixture, out, "query-acceptance")
            result = run_query_acceptance(out / "scan_index.sqlite")
            self.assertEqual(result["state"], "PASS")
            self.assertEqual(result["required_query_count"], len(RELEASE_ACCEPTANCE_QUERIES))
            self.assertEqual(result["passed_query_count"], len(RELEASE_ACCEPTANCE_QUERIES))
            counts = {x["query"]: x["row_count"] for x in result["results"]}
            self.assertGreater(counts["surface-without-handler"], 0)
            self.assertGreater(counts["hidden-surface-candidates"], 0)
            self.assertGreater(counts["unknown-routes"], 0)

    def test_projection_self_audit_detects_tampering(self):
        fixture = Path(__file__).parent / "fixtures" / "qualification_sample"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "scan"
            ScanEngine().scan(fixture, out, "projection-audit")
            self.assertEqual(verify_projection_manifest(out)["state"], "PASS")
            (out / "stage1_summary.md").write_text("tampered\n", encoding="utf-8")
            result = verify_projection_manifest(out)
            self.assertEqual(result["state"], "FAIL")
            self.assertTrue(any(x["kind"] == "projection_hash_mismatch" for x in result["issues"]))

    def test_package_manifest_generation_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scan").mkdir()
            (root / "scan" / "__init__.py").write_text(f'__version__ = "{__version__}"\n', encoding="utf-8")
            (root / "pyproject.toml").write_text(f'[project]\nname="x"\nversion="{__version__}"\n', encoding="utf-8")
            (root / "payload.txt").write_text("hello\n", encoding="utf-8")
            write_package_manifest(root)
            # verify_package compares against the executing SCAN runtime version.
            self.assertEqual(verify_package(root)["state"], "PASS")
            (root / "payload.txt").write_text("changed\n", encoding="utf-8")
            self.assertEqual(verify_package(root)["state"], "FAIL")


if __name__ == "__main__":
    unittest.main()
