from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scan.engine import ScanEngine
from scan.integrity import surface_closure
from scan.store import Store


UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <widget class="QPushButton" name="openButton">
   <property name="text"><string>Open</string></property>
  </widget>
  <widget class="QPushButton" name="applyButton">
   <property name="text"><string>Apply</string></property>
  </widget>
  <action name="actionSave">
   <property name="text"><string>Save</string></property>
   <property name="shortcut"><string>Ctrl+S</string></property>
  </action>
 </widget>
 <connections>
  <connection>
   <sender>applyButton</sender><signal>clicked()</signal>
   <receiver>MainWindow</receiver><slot>applyChanges()</slot>
  </connection>
 </connections>
</ui>
'''

CPP = '''#include <QAction>
#include <QPushButton>
#include <QShortcut>
#include <QCommandLineParser>

void MainWindow::wire() {
    connect(ui->openButton, &QPushButton::clicked, this, &MainWindow::openFile);
    connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile);
    auto dynamicAction = new QAction("Dynamic", this);
    connect(dynamicAction, &QAction::triggered, this, &MainWindow::runDynamic);
    auto *quick = new QShortcut(QKeySequence("Ctrl+K"), this);
    connect(quick, &QShortcut::activated, this, &MainWindow::quickFind);
}
void MainWindow::openFile() {}
void MainWindow::saveFile() {}
void MainWindow::runDynamic() {}
void MainWindow::quickFind() {}
void MainWindow::applyChanges() {}
void MainWindow::dropEvent(QDropEvent *event) { Q_UNUSED(event); }
'''

CLI = '''#include <QCommandLineParser>
void parse(QCommandLineParser &parser) {
    parser.addPositionalArgument("files", "Files to open.");
    parser.addOptions({
        {"translation", "Overrides translation.", "translation"},
        {"reset-settings", "Reset settings."}
    });
    if (parser.isSet("reset-settings")) {}
    auto lang = parser.value("translation");
}
'''


class M3SurfaceBreadthTests(unittest.TestCase):
    def _scan(self, td: Path):
        root = td / "specimen"
        root.mkdir()
        (root / "MainWindow.ui").write_text(UI, encoding="utf-8")
        (root / "MainWindow.cpp").write_text(CPP, encoding="utf-8")
        (root / "cli.cpp").write_text(CLI, encoding="utf-8")
        out = td / "out"
        summary = ScanEngine().scan(root, out, "m3-surface@example")
        return out, summary

    def test_unique_ui_object_reference_closes_across_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            open_records = [r for r in closure["records"] if r["name"] == "openButton" and r["surface_type"] == "QPushButton"]
            self.assertEqual(len(open_records), 1)
            self.assertEqual(open_records[0]["closure"], "BOUND")
            self.assertTrue(any(step["kind"] == "resolves_to" for step in open_records[0]["example_route"]))

    def test_ui_connection_and_shortcut_are_first_class_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, summary = self._scan(Path(tmp))
            names = [(n["kind"], n["name"], json.loads(n["attributes_json"])) for n in summary["nodes"]]
            self.assertTrue(any(k == "human_surface" and name == "Ctrl+S" and a.get("surface_type") == "keyboard_shortcut" for k, name, a in names))
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            by_name = [r for r in closure["records"] if r["name"] in {"applyButton", "Ctrl+S"}]
            self.assertTrue(by_name)
            self.assertTrue(all(r["closure"] == "BOUND" for r in by_name))

    def test_dynamic_qaction_and_qshortcut_sender_identity_are_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            by_name = {r["name"]: r for r in closure["records"]}
            self.assertEqual(by_name["dynamicAction"]["closure"], "BOUND")
            self.assertEqual(by_name["quick"]["closure"], "BOUND")

    def test_cli_denominator_includes_declared_options_and_consumers(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, summary = self._scan(Path(tmp))
            surfaces = [(n["name"], json.loads(n["attributes_json"])) for n in summary["nodes"] if n["kind"] in {"human_surface", "surface_reference"}]
            cli_names = {name for name, attrs in surfaces if attrs.get("surface_type") == "cli_option"}
            self.assertIn("--translation", cli_names)
            self.assertIn("--reset-settings", cli_names)
            self.assertTrue(any(name == "files" and attrs.get("surface_type") == "cli_positional" for name, attrs in surfaces))
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            reset = next(r for r in closure["records"] if r["name"] == "--reset-settings")
            translation = next(r for r in closure["records"] if r["name"] == "--translation")
            self.assertEqual(reset["closure"], "BOUND")
            self.assertEqual(translation["closure"], "BOUND")

    def test_event_override_is_explicit_human_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            drop = next(r for r in closure["records"] if r["name"] == "MainWindow::dropEvent")
            self.assertEqual(drop["surface_type"], "drag_drop")
            self.assertEqual(drop["closure"], "BOUND")

    def test_completeness_has_surface_type_subdimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            dims = {d["key"]: d for d in store.completeness_dimensions()}
            store.close()
            self.assertIn("human-surfaces/QPushButton", dims)
            self.assertIn("human-surfaces/cli_option", dims)
            self.assertIn("human-surfaces/keyboard_shortcut", dims)


if __name__ == "__main__":
    unittest.main()

class M3AmbiguityAndMergeTests(unittest.TestCase):
    def test_duplicate_action_identity_merges_declaration_and_reference_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            (root / "Main.ui").write_text(UI, encoding="utf-8")
            (root / "Main.cpp").write_text('''#include <QAction>\nvoid MainWindow::wire(){ connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile); }\nvoid MainWindow::saveFile(){}\n''', encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "merge@example")
            action = [n for n in summary["nodes"] if n["name"] == "actionSave"]
            self.assertEqual(len(action), 1)
            self.assertEqual(action[0]["kind"], "human_surface")
            attrs = json.loads(action[0]["attributes_json"])
            self.assertEqual(attrs.get("text"), "Save")
            self.assertGreaterEqual(len(json.loads(action[0]["evidence_ids_json"])), 2)

    def test_ambiguous_qt_object_names_remain_visible_resolution_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            form = '''<?xml version="1.0"?><ui version="4.0"><class>{cls}</class><widget class="QWidget" name="{cls}"><widget class="QPushButton" name="sharedButton"/></widget></ui>'''
            (root / "A.ui").write_text(form.format(cls="A"), encoding="utf-8")
            (root / "B.ui").write_text(form.format(cls="B"), encoding="utf-8")
            (root / "Use.cpp").write_text('''#include <QPushButton>\nvoid C::wire(){ connect(ui->sharedButton, &QPushButton::clicked, this, &C::go); }\nvoid C::go(){}\n''', encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "ambiguous@example")
            gaps = [f for f in summary["findings"] if f["kind"] == "resolution_gap"]
            self.assertTrue(any("sharedButton" in f["title"] for f in gaps))
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            declarations = [r for r in closure["records"] if r["name"] == "sharedButton" and r["surface_type"] == "QPushButton"]
            self.assertEqual(len(declarations), 2)
            self.assertTrue(all(r["closure"] == "UNRESOLVED" for r in declarations))


class ProgrammaticQtSurfaceTests(unittest.TestCase):
    def test_programmatic_widget_is_surface_and_connect_sender_reuses_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            cpp = '''#include <QApplication>
#include <QMainWindow>
#include <QTextEdit>
#include <QListWidget>

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    QMainWindow window;
    QTextEdit *editor = new QTextEdit();
    QListWidget* navigation = new QListWidget();
    QObject::connect(navigation, &QListWidget::currentTextChanged,
                     &window, [editor](const QString &text) {
        editor->setText(text);
    });
    window.show();
    return app.exec();
}
'''
            (root / "main.cpp").write_text(cpp, encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "programmatic-surfaces@example")

            surfaces = {
                (n["name"], json.loads(n["attributes_json"]).get("surface_type")): n
                for n in summary["nodes"] if n["kind"] == "human_surface"
            }
            self.assertIn(("navigation", "QListWidget"), surfaces)
            self.assertIn(("editor", "QTextEdit"), surfaces)

            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            nav = next(r for r in closure["records"] if r["name"] == "navigation")
            self.assertEqual(nav["surface_type"], "QListWidget")
            self.assertEqual(nav["closure"], "BOUND")
            self.assertTrue(any(step["kind"] == "emits" for step in nav["example_route"]))
            self.assertTrue(any(step["kind"] == "dispatches_to" for step in nav["example_route"]))


    def test_read_only_programmatic_text_edit_is_presented_not_entry_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            cpp = '''#include <QTextEdit>
void build() {
    QTextEdit *log = new QTextEdit();
    log->setReadOnly(true);
}
'''
            (root / "main.cpp").write_text(cpp, encoding="utf-8")
            out = td / "out"
            summary = ScanEngine().scan(root, out, "readonly-surface@example")
            node = next(n for n in summary["nodes"] if n["kind"] == "human_surface" and n["name"] == "log")
            attrs = json.loads(node["attributes_json"])
            self.assertEqual(attrs["surface_role"], "presented")
            self.assertTrue(attrs["read_only"])
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            self.assertEqual(closure["surface_count"], 0)
            self.assertEqual(closure["presented_surface_count"], 1)
