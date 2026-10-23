from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scan.adapters.clang_cpp import ClangCppAdapter
from scan.engine import ScanEngine
from scan.store import Store


@unittest.skipUnless(shutil.which("clang++") or shutil.which("clang"), "clang is not installed")
class M3B2CompilerTypeTests(unittest.TestCase):
    def test_virtual_override_and_template_specialization_are_explicit(self):
        source = '''
class Base { public: virtual void f(int); virtual ~Base() = default; };
class Derived: public Base { public: void f(int) override; };
template<typename T> T add(T a,T b){ return a+b; }
void Base::f(int){}
void Derived::f(int){}
void call(Base* b){ b->f(1); auto x=add<int>(1,2); (void)x; }
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"; root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3b2-virtual@example")
            attrs = [(n, json.loads(n["attributes_json"])) for n in summary["nodes"]]
            virtual_call = next((n, a) for n, a in attrs if n["kind"] == "call_reference" and a.get("dispatch_kind") == "virtual_possible")
            self.assertEqual(virtual_call[1].get("receiver_static_type"), "Base *")
            self.assertTrue(any(e["kind"] == "overrides" for e in summary["edges"]))
            self.assertTrue(any(e["kind"] == "virtual_dispatch_candidate" for e in summary["edges"]))
            templated = [a for n, a in attrs if n["kind"] == "call_reference" and a.get("dispatch_kind") == "template_specialization"]
            self.assertTrue(any(a.get("template_origin") == "add" for a in templated))
            self.assertTrue(any(n["kind"] == "template_symbol" and n["name"] == "add" for n in summary["nodes"]))
            self.assertTrue(any(n["kind"] == "type_symbol" and n["name"] == "Derived" for n in summary["nodes"]))

    def test_overloaded_calls_keep_compiler_signature_identity(self):
        source = """
int pick(int x){ return x; }
double pick(double x){ return x; }
void use(){ auto a=pick(1); auto b=pick(1.0); (void)a; (void)b; }
"""
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3b2-overload@example")
            call_nodes = [(n, json.loads(n["attributes_json"])) for n in summary["nodes"]
                          if n["kind"] == "call_reference" and n["name"] == "pick"]
            signatures = {a.get("signature") for _, a in call_nodes if a.get("parser") == "clang_ast"}
            self.assertIn("int (int)", signatures)
            self.assertIn("double (double)", signatures)
            call_ids = {n["id"] for n, a in call_nodes if a.get("parser") == "clang_ast"}
            resolved = [e for e in summary["edges"] if e["kind"] == "resolves_to" and e["src"] in call_ids]
            self.assertEqual(len({e["src"] for e in resolved}), 2)

    def test_nested_compile_database_context_changes_cache_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "specimen"; root.mkdir()
            build = root / "build-debug"; build.mkdir()
            source = root / "App.cpp"; source.write_text("int answer(){return VALUE;}\n", encoding="utf-8")
            db = build / "compile_commands.json"
            def write(value: int):
                db.write_text(json.dumps([{
                    "directory": str(root), "file": str(source),
                    "arguments": ["clang++", f"-DVALUE={value}", "-std=c++20", str(source), "-c", "-o", "App.o"]
                }]), encoding="utf-8")
            adapter = ClangCppAdapter()
            record = next(r for r in __import__("scan.inventory", fromlist=["inventory"]).inventory(root) if r.path == "App.cpp")
            write(1)
            adapter._db_cache.clear()
            v1 = adapter.cache_version(root, record)
            context1 = adapter._compile_db_context(root, record)
            self.assertEqual(context1["compile_db"], "build-debug/compile_commands.json")
            self.assertIn("-DVALUE=1", context1["flags"])
            write(2)
            adapter._db_cache.clear()
            v2 = adapter.cache_version(root, record)
            self.assertNotEqual(v1, v2)
            self.assertIn("-DVALUE=2", adapter._compile_db_context(root, record)["flags"])

    def test_compiler_typed_qt_like_effects_create_nest_boundaries(self):
        # Local stubs let Clang prove receiver types without requiring Qt headers in the test environment.
        source = '''
class QSettings { public: void setValue(const char*, int); int value(const char*); };
class QClipboard { public: void setText(const char*); const char* text(); };
void save(QSettings* settings, QClipboard* clipboard) {
  settings->setValue("n", 3);
  clipboard->setText("hello");
  auto x = settings->value("n"); (void)x;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3b2-effects@example")
            effects = {(n["name"], json.loads(n["attributes_json"]).get("classification")) for n in summary["nodes"] if n["kind"] == "effect"}
            self.assertIn(("settings_write", "compiler_typed_api"), effects)
            self.assertIn(("settings_read", "compiler_typed_api"), effects)
            self.assertIn(("clipboard_write", "compiler_typed_api"), effects)
            boundaries = {(n["name"], n["coverage"]) for n in summary["nodes"] if n["kind"] == "nest_boundary"}
            self.assertIn(("settings", "MAPPED"), boundaries)
            self.assertIn(("clipboard", "MAPPED"), boundaries)


class M3B2FrameworkTests(unittest.TestCase):
    def test_scintilla_lexilla_messages_are_framework_capabilities_not_fake_human_surfaces(self):
        source = '''
void edit() {
  int a = SCI_UNDO;
  int b = SCI_COPY;
  int c = SCN_MODIFIED;
  auto lexer = Lexilla::MakeLexer("cpp");
  (void)a; (void)b; (void)c; (void)lexer;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "Editor.cpp").write_text(source, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3b2-scintilla@example")
            caps = [n for n in summary["nodes"] if n["kind"] == "framework_capability"]
            events = [n for n in summary["nodes"] if n["kind"] == "framework_event"]
            self.assertTrue(any(n["name"] == "SCI_UNDO" for n in caps))
            self.assertTrue(any(n["name"] == "SCI_COPY" for n in caps))
            self.assertTrue(any(n["name"] == "SCN_MODIFIED" for n in events))
            self.assertTrue(any(n["kind"] == "extension_receptor_candidate" and "Lexilla" in n["name"] for n in summary["nodes"]))
            self.assertFalse(any(n["kind"] == "human_surface" and n["name"] == "SCI_UNDO" for n in summary["nodes"]))
            dims = {d["key"]: d for d in summary["completeness_vector"]}
            self.assertEqual(dims["scintilla-lexilla-coupling"]["state"], "PARTIAL")

    def test_preprocessor_and_qt_codegen_contracts_remain_explicit(self):
        header = '''
#define FEATURE_X 1
#if defined(_WIN32)
class App { Q_OBJECT };
#else
class App {};
#endif
'''
        cmake = '''
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)
add_executable(app main.cpp MainWindow.ui resources.qrc)
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "App.h").write_text(header, encoding="utf-8")
            (root / "CMakeLists.txt").write_text(cmake, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3b2-codegen@example")
            self.assertTrue(any(n["kind"] == "preprocessor_macro" and n["name"] == "FEATURE_X" for n in summary["nodes"]))
            self.assertTrue(any(n["kind"] == "conditional_compilation" for n in summary["nodes"]))
            self.assertTrue(any(n["kind"] == "generated_code_receptor" and n["name"] == "Q_OBJECT" for n in summary["nodes"]))
            generators = {n["name"] for n in summary["nodes"] if n["kind"] == "generated_build_contract"}
            self.assertTrue({"AUTOMOC", "AUTOUIC", "AUTORCC"}.issubset(generators))
            self.assertTrue(any(n["kind"] == "generated_input" and n["name"].endswith(".ui") for n in summary["nodes"]))
            self.assertTrue(any(n["kind"] == "generated_input" and n["name"].endswith(".qrc") for n in summary["nodes"]))
            dims = {d["key"]: d for d in summary["completeness_vector"]}
            self.assertEqual(dims["conditional-compilation"]["state"], "PARTIAL")
            self.assertEqual(dims["qt-generated-code"]["state"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
