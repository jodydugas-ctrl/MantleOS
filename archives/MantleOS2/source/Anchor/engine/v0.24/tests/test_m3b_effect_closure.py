from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scan.engine import ScanEngine
from scan.integrity import effect_closure
from scan.store import Store


UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <action name="actionSave"><property name="text"><string>Save</string></property></action>
  <action name="actionInfo"><property name="text"><string>Info</string></property></action>
  <action name="actionGhost"><property name="text"><string>Ghost</string></property></action>
 </widget>
</ui>
'''

CPP = r'''#include <QAction>
#include <QFile>
#include <QMessageBox>

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent) {
    connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile);
    connect(ui->actionInfo, &QAction::triggered, this, &MainWindow::showInfo);
}

void MainWindow::saveFile() {
    persistDocument();
    statusBar()->showMessage("Saved");
}

void MainWindow::persistDocument() {
    QFile::rename("draft.tmp", "document.txt");
    this->dirty = false;
}

void MainWindow::showInfo() {
    QMessageBox::information(this, "Info", "Ready");
}
'''


class M3BEffectClosureTests(unittest.TestCase):
    def _scan(self, td: Path):
        root = td / "specimen"
        root.mkdir()
        (root / "MainWindow.ui").write_text(UI, encoding="utf-8")
        (root / "MainWindow.cpp").write_text(CPP, encoding="utf-8")
        out = td / "out"
        summary = ScanEngine().scan(root, out, "m3b-effect@example")
        return out, summary

    def test_custom_call_chain_reaches_filesystem_effect_and_state_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, summary = self._scan(Path(tmp))
            nodes = summary["nodes"]
            self.assertTrue(any(n["kind"] == "call_reference" and "persistDocument" in n["name"] for n in nodes))
            self.assertTrue(any(n["kind"] == "effect" and n["name"] == "filesystem_write" for n in nodes))
            self.assertTrue(any(n["kind"] == "state_change" and n["name"] == "this->dirty" for n in nodes))

            store = Store(out / "scan_index.sqlite")
            deep = effect_closure(store)
            store.close()
            save = next(r for r in deep["records"] if r["name"] == "actionSave")
            self.assertEqual(save["effect_closure"], "CLOSED")
            terminal_kinds = {x["kind"] for x in save["terminals"]}
            self.assertIn("effect", terminal_kinds)
            self.assertIn("state_change", terminal_kinds)
            fs_effect = next(x for x in save["terminals"] if x["kind"] == "effect" and x["name"] == "filesystem_write")
            route_kinds = {s["kind"] for s in fs_effect["example_route"]}
            self.assertIn("calls", route_kinds)
            self.assertIn("resolves_to", route_kinds)

    def test_feedback_is_traced_through_handler(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            deep = effect_closure(store)
            store.close()
            save = next(r for r in deep["records"] if r["name"] == "actionSave")
            info = next(r for r in deep["records"] if r["name"] == "actionInfo")
            self.assertGreaterEqual(save["feedback_count"], 1)
            self.assertGreaterEqual(info["feedback_count"], 1)
            self.assertEqual(info["effect_closure"], "CLOSED")

    def test_presented_dialog_is_feedback_terminal_not_entry_binding_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            binding = __import__("scan.integrity", fromlist=["surface_closure"]).surface_closure(store)
            store.close()
            self.assertEqual(binding["schema_version"], "scan-surface-closure/0.3")
            self.assertEqual(binding["surface_count"], 3)
            self.assertEqual(binding["presented_surface_count"], 1)
            self.assertFalse(any(r["surface_type"] == "dialog" for r in binding["records"]))

    def test_sender_scoped_qt_events_do_not_cross_wire_unrelated_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            deep = effect_closure(store)
            store.close()
            save = next(r for r in deep["records"] if r["name"] == "actionSave")
            info = next(r for r in deep["records"] if r["name"] == "actionInfo")
            save_terminal_names = {(x["kind"], x["name"]) for x in save["terminals"]}
            info_terminal_names = {(x["kind"], x["name"]) for x in info["terminals"]}
            self.assertIn(("effect", "filesystem_write"), save_terminal_names)
            self.assertNotIn(("effect", "filesystem_write"), info_terminal_names)
            self.assertIn(("feedback", "modal_message"), info_terminal_names)
            self.assertNotIn(("feedback", "modal_message"), save_terminal_names)

    def test_unbound_surface_stays_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            deep = effect_closure(store)
            store.close()
            ghost = next(r for r in deep["records"] if r["name"] == "actionGhost")
            self.assertEqual(ghost["binding_closure"], "UNRESOLVED")
            self.assertEqual(ghost["effect_closure"], "UNRESOLVED")

    def test_effect_projection_and_completeness_dimension_are_emitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, summary = self._scan(Path(tmp))
            self.assertEqual(summary["schema_version"], "scan-machine-body-map/0.9")
            self.assertTrue((out / "effect_closure.json").exists())
            payload = json.loads((out / "effect_closure.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "scan-effect-closure/0.1")
            dims = {d["key"]: d for d in summary["completeness_vector"]}
            self.assertIn("human-surface-effect-closure", dims)
            self.assertEqual(dims["human-surface-effect-closure"]["state"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()


class ProgrammaticLambdaEffectClosureTests(unittest.TestCase):
    def test_programmatic_surface_lambda_reaches_feedback_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            cpp = '''#include <QApplication>
#include <QMainWindow>
#include <QListWidget>
#include <QStatusBar>

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    QMainWindow window;
    QListWidget *navigation = new QListWidget();
    QStatusBar *status = window.statusBar();
    QObject::connect(navigation, &QListWidget::currentTextChanged,
                     &window, [status](const QString &text) {
        status->showMessage(text, 1000);
    });
    window.show();
    return app.exec();
}
'''
            (root / "main.cpp").write_text(cpp, encoding="utf-8")
            out = td / "out"
            ScanEngine().scan(root, out, "lambda-deep@example")
            store = Store(out / "scan_index.sqlite")
            deep = effect_closure(store)
            store.close()
            navigation = next(r for r in deep["records"] if r["name"] == "navigation")
            self.assertEqual(navigation["binding_closure"], "BOUND")
            self.assertEqual(navigation["effect_closure"], "CLOSED")
            self.assertGreaterEqual(navigation["feedback_count"], 1)
            self.assertTrue(any(x["name"] == "status_message" for x in navigation["feedback"]))
