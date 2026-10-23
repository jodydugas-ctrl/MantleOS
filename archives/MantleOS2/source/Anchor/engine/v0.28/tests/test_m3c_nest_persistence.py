from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scan.engine import ScanEngine
from scan.integrity import effect_closure
from scan.store import Store


@unittest.skipUnless(shutil.which("clang++") or shutil.which("clang"), "clang is not installed")
class M3CTypedNestTests(unittest.TestCase):
    def test_permission_environment_and_cancel_effects_are_typed(self):
        source = r'''
class QFileInfo { public: bool isWritable() const; };
class QSaveFile { public: void cancelWriting(); };
class QProcess { public: void terminate(); };
class QNetworkReply { public: void abort(); int error() const; };
const char* qEnvironmentVariable(const char*);
bool check(QFileInfo* info, QSaveFile* file, QProcess* proc, QNetworkReply* reply) {
  auto home = qEnvironmentVariable("HOME"); (void)home;
  if (!info->isWritable()) return false;
  if (reply->error()) { reply->abort(); file->cancelWriting(); proc->terminate(); return false; }
  return true;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3c-typed@example")
            effects = {n["name"] for n in summary["nodes"] if n["kind"] == "effect"}
            self.assertTrue({"environment_read", "permission_check", "network_error_state", "network_cancel", "persistence_cancel", "subprocess_cancel"}.issubset(effects))
            guards = [(n, json.loads(n["attributes_json"])) for n in summary["nodes"] if n["kind"] == "guard"]
            self.assertTrue(any(a.get("guard_domain_candidate") == "permissions_or_availability" for _, a in guards))
            dims = {d["key"]: d for d in summary["completeness_vector"]}
            self.assertEqual(dims["permission-guards"]["state"], "PARTIAL")
            self.assertEqual(dims["guard-error-cancel"]["state"], "PARTIAL")

    def test_typed_plugin_and_script_receptors_create_capability_factories(self):
        source = r'''
class QObject {};
class QPluginLoader { public: bool load(); QObject* instance(); };
class QJSEngine { public: int evaluate(const char*); };
int luaL_loadfile(void*, const char*);
void use(QPluginLoader* loader, QJSEngine* js, void* L) {
  loader->load(); auto p = loader->instance();
  auto x = js->evaluate("1+1");
  luaL_loadfile(L, "plugin.lua");
  (void)p; (void)x;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "Plugins.cpp").write_text(source, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3c-ext@example")
            receptors = [n for n in summary["nodes"] if n["kind"] == "extension_receptor"]
            factories = [n for n in summary["nodes"] if n["kind"] == "capability_factory"]
            self.assertTrue(any("qt_plugin:load" == n["name"] for n in receptors))
            self.assertTrue(any("qt_plugin:instance" == n["name"] for n in receptors))
            self.assertTrue(any("javascript:evaluate" == n["name"] for n in receptors))
            self.assertTrue(any("lua:" in n["name"] for n in receptors))
            self.assertGreaterEqual(len(factories), 3)
            dims = {d["key"]: d for d in summary["completeness_vector"]}
            self.assertEqual(dims["extension-receptors"]["state"], "PARTIAL")

    def test_state_change_can_be_linked_to_typed_persistence_candidate(self):
        source = r'''
class QSettings { public: void setValue(const char*, int); };
class App {
  int dirty;
public:
  void save(QSettings* settings) { this->dirty = 0; settings->setValue("dirty", dirty); }
};
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "App.cpp").write_text(source, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3c-persistence@example")
            self.assertTrue(any(n["kind"] == "persistence_operation" and n["name"] == "settings_write" for n in summary["nodes"]))
            self.assertTrue(any(e["kind"] == "persistence_candidate" and e["coverage"] == "PARTIAL" for e in summary["edges"]))
            dims = {d["key"]: d for d in summary["completeness_vector"]}
            self.assertEqual(dims["persistence-paths"]["state"], "PARTIAL")


class M3CControlFlowTests(unittest.TestCase):
    def test_guards_exits_exception_and_retry_candidates_are_explicit(self):
        source = r'''
bool ok(); void risky();
bool run() {
  int retryCount = 3;
  while (retryCount-- > 0) {
    if (!ok()) return false;
  }
  try { risky(); }
  catch (...) { throw; }
  return true;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "Flow.cpp").write_text(source, encoding="utf-8")
            summary = ScanEngine().scan(root, td / "out", "m3c-flow@example")
            kinds = [n["kind"] for n in summary["nodes"]]
            self.assertIn("guard", kinds)
            self.assertIn("control_loop", kinds)
            self.assertIn("control_exit", kinds)
            self.assertIn("error_path", kinds)
            self.assertIn("retry_path_candidate", kinds)
            self.assertTrue(any(e["kind"] == "guards_exit" for e in summary["edges"]))

    def test_deep_closure_treats_persistence_and_error_paths_as_consequences(self):
        ui = '''<?xml version="1.0"?><ui version="4.0"><class>MainWindow</class><widget class="QMainWindow" name="MainWindow"><action name="actionSave"/><action name="actionGhost"/></widget></ui>'''
        cpp = r'''
class QAction { public: void triggered(); };
class QSettings { public: void setValue(const char*, int); };
void MainWindow::wire(){ connect(ui->actionSave, &QAction::triggered, this, &MainWindow::save); }
void MainWindow::save(){ QSettings s; s.setValue("x", 1); if (false) throw 1; }
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "Main.ui").write_text(ui, encoding="utf-8")
            (root / "Main.cpp").write_text(cpp, encoding="utf-8")
            out = td / "out"; ScanEngine().scan(root, out, "m3c-deep@example")
            store = Store(out / "scan_index.sqlite")
            deep = effect_closure(store)
            store.close()
            by_name = {r["name"]: r for r in deep["records"]}
            self.assertEqual(by_name["actionSave"]["effect_closure"], "CLOSED")
            self.assertEqual(by_name["actionGhost"]["effect_closure"], "UNRESOLVED")
            terminal_kinds = {x["kind"] for x in by_name["actionSave"]["terminals"]}
            self.assertTrue("persistence_operation" in terminal_kinds or "effect" in terminal_kinds)


    def test_nest_capability_projection_is_emitted_and_preserves_potential_factories(self):
        source = r'''
class QPluginLoader { public: void* instance(); };
class QSettings { public: void setValue(const char*, int); };
void use(QPluginLoader* loader, QSettings* settings) {
  auto p = loader->instance(); settings->setValue("x", 1); (void)p;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp); root = td / "specimen"; root.mkdir()
            (root / "Map.cpp").write_text(source, encoding="utf-8")
            out = td / "out"; summary = ScanEngine().scan(root, out, "m3c-map@example")
            path = out / "nest_capability_map.json"
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "scan-nest-capability-map/0.1")
            self.assertTrue(any(x.get("capability_provenance") == "POTENTIAL" for x in payload["extensions"] if x["kind"] == "capability_factory"))
            self.assertIn("nest_capability_map.json", summary["semantic_graph"]["projections"])

    def test_new_m3c_queries_are_registered(self):
        from scan.cli import QUERY_SQL
        self.assertIn("persistence", QUERY_SQL)
        self.assertIn("guards", QUERY_SQL)
        self.assertIn("permissions", QUERY_SQL)


if __name__ == "__main__":
    unittest.main()
