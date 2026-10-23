from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scan.adapters.clang_cpp import ClangCppAdapter
from scan.engine import ScanEngine


CPP = '''class App { public: void save(); void helper(); int state; };\nvoid App::helper(){ state = 1; }\nvoid App::save(){ helper(); }\n'''


@unittest.skipUnless(shutil.which("clang++") or shutil.which("clang"), "clang is not installed")
class ClangCppAdapterTests(unittest.TestCase):
    def test_compiler_ast_enriches_symbols_calls_and_member_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            (root / "App.cpp").write_text(CPP, encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "clang-fixture@example")
            app_save = [n for n in summary["nodes"] if n["kind"] == "symbol" and n["name"] == "App::save"]
            self.assertEqual(len(app_save), 1)
            attrs = json.loads(app_save[0]["attributes_json"])
            self.assertEqual(attrs.get("parser"), "clang_ast")
            self.assertEqual(app_save[0]["coverage"], "MAPPED")
            self.assertTrue(any(n["kind"] == "call_reference" and json.loads(n["attributes_json"]).get("parser") == "clang_ast" for n in summary["nodes"]))
            self.assertTrue(any(n["kind"] == "state_change" and json.loads(n["attributes_json"]).get("parser") == "clang_ast" for n in summary["nodes"]))
            self.assertTrue(any(e["kind"] == "resolves_to" and json.loads(e["attributes_json"]).get("resolution") == "clang_decl_identity" for e in summary["edges"]))
            dims = {d["key"]: d for d in summary["completeness_vector"]}
            self.assertEqual(dims["cpp-compiler-ast"]["state"], "MAPPED")

    def test_compiler_and_fallback_merge_same_function_identity_across_blank_lines(self):
        source = "class App { public: void save(); };\n\nvoid App::save() { }\n"
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "clang-merge@example")
            matches = [n for n in summary["nodes"] if n["kind"] == "symbol" and n["name"] == "App::save"]
            self.assertEqual(len(matches), 1)
            attrs = json.loads(matches[0]["attributes_json"])
            self.assertEqual(attrs.get("line"), 3)
            self.assertEqual(attrs.get("parser"), "clang_ast")
            evidence_ids = json.loads(matches[0]["evidence_ids_json"])
            self.assertGreaterEqual(len(evidence_ids), 2)


    def test_compiler_projection_excludes_system_header_declaration_noise(self):
        source = '#include <utility>\nint main(){ std::pair<int,int> p{1,2}; return p.first; }\n'
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "clang-main-file-filter@example")
            compiler_decl_kinds = {"symbol", "type_symbol", "template_symbol"}
            external = [n for n in summary["nodes"] if n["kind"] in compiler_decl_kinds and n["name"].startswith("std::")]
            self.assertEqual(external, [])
            # Calls made by main() may still point at external providers; declarations from those headers
            # must not be mis-attributed to App.cpp as specimen anatomy.
            self.assertLess(len(summary["nodes"]), 80)


    def test_state_changes_only_follow_lhs_members_rooted_in_this(self):
        source = '''class PairLike { public: int first; };
class App { public: int state; PairLike nested; void run(); };
void App::run(){
    PairLike local;
    local.first = 2;
    int x = local.first;
    state = x;
    nested.first = 3;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "clang-state-target@example")
            state_nodes = [n for n in summary["nodes"] if n["kind"] == "state_change"
                           and json.loads(n["attributes_json"]).get("parser") == "clang_ast"]
            names = [n["name"] for n in state_nodes]
            self.assertIn("state", names)
            self.assertIn("first", names)  # nested.first is specimen-rooted through this->nested.
            # The local.first write and RHS local.first read must not create extra state records.
            first_nodes = [n for n in state_nodes if n["name"] == "first"]
            self.assertEqual(len(first_nodes), 1)
            local_line = 5
            nested_line = 8
            self.assertFalse(any(json.loads(n["attributes_json"]).get("line") == local_line and n["name"] == "first" for n in state_nodes))
            self.assertTrue(any(json.loads(n["attributes_json"]).get("line") == nested_line and n["name"] == "first" for n in state_nodes))

    def test_compile_database_flags_are_whitelisted(self):
        flags = ClangCppAdapter._safe_flags([
            "-I", "include", "-DDEBUG=1", "-std=c++20", "-Xclang", "-load", "evil.so",
            "@args.rsp", "-o", "owned-output.o", "-fplugin=bad.so", "-include", "side_effect.h",
        ], Path("/tmp/project"))
        joined = " ".join(flags)
        self.assertIn("-DDEBUG=1", flags)
        self.assertIn("-std=c++20", flags)
        self.assertIn("-I", flags)
        self.assertNotIn("evil.so", joined)
        self.assertNotIn("args.rsp", joined)
        self.assertNotIn("owned-output.o", joined)
        self.assertNotIn("side_effect.h", joined)

    def test_valid_ast_is_retained_as_partial_when_clang_reports_missing_dependency(self):
        source = '''#include "dependency_that_does_not_exist_7f6416.hpp"
class App { public: void save(); int state; };
void App::save(){ state = 1; }
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "clang-partial-ast@example")

            parser_results = [
                n for n in summary["nodes"]
                if n["kind"] == "parser_result" and n["name"] == "clang_ast"
            ]
            self.assertEqual(len(parser_results), 1)
            self.assertEqual(parser_results[0]["coverage"], "PARTIAL")
            attrs = json.loads(parser_results[0]["attributes_json"])
            self.assertTrue(attrs.get("recovered_after_diagnostics"))
            self.assertNotEqual(attrs.get("returncode"), 0)

            self.assertTrue(any(
                n["kind"] == "symbol" and n["name"] == "App::save"
                and json.loads(n["attributes_json"]).get("parser") == "clang_ast"
                for n in summary["nodes"]
            ))
            gaps = [f for f in summary["findings"] if f["kind"] == "parser_gap"]
            self.assertTrue(any(
                json.loads(f["attributes_json"]).get("recovered_valid_ast")
                for f in gaps
            ))
            dims = {d["key"]: d for d in summary["completeness_vector"]}
            compiler = dims["cpp-compiler-ast"]
            self.assertEqual(compiler["state"], "PARTIAL")
            compiler_attrs = compiler["attributes"]
            self.assertEqual(compiler_attrs["compiler_ast_mapped"], 0)
            self.assertEqual(compiler_attrs["compiler_ast_partial"], 1)

    def test_oversized_clang_json_remains_an_explicit_partial_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            (root / "App.cpp").write_text("void f(){}\n", encoding="utf-8")
            out = td / "out"
            summary = ScanEngine(adapters=[ClangCppAdapter(max_ast_json_bytes=1)]).scan(
                root, out, "clang-ast-limit@example"
            )
            self.assertFalse(any(
                n["kind"] == "parser_result" and n["name"] == "clang_ast"
                for n in summary["nodes"]
            ))
            gaps = [f for f in summary["findings"] if f["kind"] == "parser_gap"]
            self.assertEqual(len(gaps), 1)
            attrs = json.loads(gaps[0]["attributes_json"])
            self.assertGreater(attrs["ast_json_bytes"], attrs["max_ast_json_bytes"])
            self.assertEqual(gaps[0]["status"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
