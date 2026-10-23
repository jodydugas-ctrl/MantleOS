from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scan.cpp_structure import mask_cpp as real_mask_cpp
from scan.engine import ScanEngine


class Pr5CalibrationRefinementTests(unittest.TestCase):
    def test_documentation_and_workflow_urls_are_not_runtime_nest_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "specimen"
            (root / "docs").mkdir(parents=True)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / "docs" / "README.md").write_text(
                "Plugin guide: https://example.invalid/docs\n", encoding="utf-8"
            )
            (root / ".github" / "workflows" / "build.yml").write_text(
                "source: https://example.invalid/toolchain\n", encoding="utf-8"
            )

            summary = ScanEngine().scan(root, Path(tmp) / "out", "metadata-context@example")
            metadata_nodes = [n for n in summary["nodes"] if n["kind"] == "repository_reference"]
            runtime_boundaries = [n for n in summary["nodes"] if n["kind"] == "nest_boundary"]

            self.assertGreaterEqual(len(metadata_nodes), 3)
            self.assertFalse(runtime_boundaries)

    def test_runtime_source_url_remains_explicit_nest_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "specimen"
            root.mkdir()
            (root / "Update.cpp").write_text(
                'const char *endpoint = "https://example.invalid/update";\n', encoding="utf-8"
            )

            summary = ScanEngine().scan(root, Path(tmp) / "out", "runtime-context@example")
            boundaries = [
                n for n in summary["nodes"]
                if n["kind"] == "nest_boundary"
                and json.loads(n["attributes_json"]).get("generic_kind") == "url"
            ]

            self.assertEqual(len(boundaries), 1)
            self.assertIn("https://example.invalid/update", boundaries[0]["name"])

    def test_vendored_source_root_license_and_test_urls_are_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "specimen"
            (root / "thirdparty" / "lib").mkdir(parents=True)
            (root / "tests").mkdir()
            (root / "LICENSE").write_text("https://example.invalid/license\n", encoding="utf-8")
            (root / "thirdparty" / "lib" / "code.cpp").write_text(
                'const char *upstream = "https://example.invalid/upstream";\n', encoding="utf-8"
            )
            (root / "tests" / "fixture.cpp").write_text(
                'const char *fixture = "https://example.invalid/fixture";\n', encoding="utf-8"
            )

            summary = ScanEngine().scan(root, Path(tmp) / "out", "reference-paths@example")
            references = [n for n in summary["nodes"] if n["kind"] == "repository_reference"]
            boundaries = [n for n in summary["nodes"] if n["kind"] == "nest_boundary"]

            self.assertEqual(len(references), 3)
            self.assertFalse(boundaries)

    def test_source_comment_url_is_reference_but_string_url_is_runtime_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "specimen"
            root.mkdir()
            (root / "Update.cpp").write_text(
                "// https://example.invalid/comment\n"
                "/* https://example.invalid/block */\n"
                'const char *endpoint = "https://example.invalid/runtime";\n',
                encoding="utf-8",
            )

            summary = ScanEngine().scan(root, Path(tmp) / "out", "comment-context@example")
            references = [
                n for n in summary["nodes"]
                if n["kind"] == "repository_reference"
                and json.loads(n["attributes_json"]).get("generic_kind") == "url"
            ]
            boundaries = [
                n for n in summary["nodes"]
                if n["kind"] == "nest_boundary"
                and json.loads(n["attributes_json"]).get("generic_kind") == "url"
            ]

            self.assertEqual({n["name"] for n in references}, {
                "https://example.invalid/comment",
                "https://example.invalid/block",
            })
            self.assertEqual([n["name"] for n in boundaries], ["https://example.invalid/runtime"])

    def test_cpp_fallback_masks_each_translation_unit_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "specimen"
            root.mkdir()
            (root / "Worker.cpp").write_text(
                "class Worker { QSettings *settings; void first(); void second(); };\n"
                "void Worker::first() { settings->value(\"one\"); }\n"
                "void Worker::second() { settings->setValue(\"two\", 2); }\n",
                encoding="utf-8",
            )

            with patch("scan.adapters.cpp_qt.mask_cpp", wraps=real_mask_cpp) as mask:
                ScanEngine().scan(root, Path(tmp) / "out", "single-mask@example")

            self.assertEqual(mask.call_count, 1)

    def test_repeated_cpp_boundary_and_extension_tokens_aggregate_without_losing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "specimen"
            root.mkdir()
            (root / "Worker.cpp").write_text(
                "void first() { QSettings one; one.value(\"a\"); lua_State *left; }\n"
                "void second() { QSettings two; two.setValue(\"b\", 2); lua_State *right; }\n",
                encoding="utf-8",
            )

            summary = ScanEngine().scan(root, Path(tmp) / "out", "aggregate-capability@example")
            boundaries = [
                n for n in summary["nodes"]
                if n["kind"] == "nest_boundary"
                and json.loads(n["attributes_json"]).get("aggregation") == "translation_unit_capability"
                and n["name"] == "settings"
            ]
            extensions = [
                n for n in summary["nodes"]
                if n["kind"] == "extension_receptor_candidate"
                and json.loads(n["attributes_json"]).get("aggregation") == "translation_unit_capability"
                and n["name"] == "script_engine"
            ]

            self.assertEqual(len(boundaries), 1)
            self.assertEqual(len(extensions), 1)
            self.assertGreaterEqual(json.loads(boundaries[0]["attributes_json"])["occurrence_count"], 2)
            self.assertEqual(json.loads(extensions[0]["attributes_json"])["occurrence_count"], 2)
            self.assertGreaterEqual(len(json.loads(boundaries[0]["evidence_ids_json"])), 2)
            self.assertEqual(len(json.loads(extensions[0]["evidence_ids_json"])), 2)

    def test_case_variant_capability_tokens_have_total_deterministic_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "specimen"
            root.mkdir()
            (root / "Worker.cpp").write_text(
                "void probe() { int plugin = 0; int Plugin = 0; int PLUGIN = 0; }\n",
                encoding="utf-8",
            )

            summary = ScanEngine().scan(root, Path(tmp) / "out", "token-order@example")
            extension = next(
                n for n in summary["nodes"]
                if n["kind"] == "extension_receptor_candidate" and n["name"] == "plugin"
                and json.loads(n["attributes_json"]).get("aggregation") == "translation_unit_capability"
            )
            self.assertEqual(
                json.loads(extension["attributes_json"])["tokens"],
                ["PLUGIN", "Plugin", "plugin"],
            )
