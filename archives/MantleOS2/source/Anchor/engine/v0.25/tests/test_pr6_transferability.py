from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scan.engine import ScanEngine
from scan.integrity import effect_closure, surface_closure
from scan.store import Store


LEGACY_CPP = r'''#include <QAction>
#include <QMainWindow>
#include <QTimer>
#include <QSound>

void MainWindow::wire() {
    QAction *pvp = new QAction("PVP", this);
    connect(pvp, SIGNAL(triggered()), this, SLOT(startPvp()));
}
void MainWindow::startPvp() { update(); }
void MainWindow::mouseReleaseEvent(QMouseEvent *event) {
    Q_UNUSED(event);
    QTimer::singleShot(700, this, SLOT(aiMove()));
}
void MainWindow::aiMove() { QSound::play(":/sound/move.wav"); update(); }
'''

QMAKE = r'''QT += core gui multimedia
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets
TARGET = TransferGame
TEMPLATE = app
SOURCES += main.cpp \
           mainwindow.cpp
HEADERS += mainwindow.h
RESOURCES += resources.qrc
'''

QRC = r'''<RCC>
 <qresource prefix="/">
  <file>sound/move.wav</file>
 </qresource>
</RCC>
'''


class PR6TransferabilityTests(unittest.TestCase):
    def _scan(self, td: Path):
        root = td / "specimen"
        (root / "sound").mkdir(parents=True)
        (root / "mainwindow.cpp").write_text(LEGACY_CPP, encoding="utf-8")
        (root / "TransferGame.pro").write_text(QMAKE, encoding="utf-8")
        (root / "resources.qrc").write_text(QRC, encoding="utf-8")
        # It is intentionally binary so the resource adapter must describe the declared resource
        # without pretending to parse its bytes.
        (root / "sound" / "move.wav").write_bytes(b"RIFF\x00\x01\x02\x03")
        out = td / "out"
        summary = ScanEngine().scan(root, out, "pr6-transferability@example")
        return out, summary

    def test_qmake_build_topology_is_first_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, summary = self._scan(Path(tmp))
            rows = [(n["kind"], n["name"], json.loads(n["attributes_json"])) for n in summary["nodes"]]
            self.assertTrue(any(k == "build_target" and name == "TransferGame" for k, name, _ in rows))
            self.assertTrue(any(k == "dependency_registration" and name == "multimedia" for k, name, _ in rows))
            widgets = [a for k, name, a in rows if k == "dependency_registration" and name == "widgets"]
            self.assertTrue(widgets)
            self.assertEqual(widgets[0].get("condition_truth"), "UNKNOWN")
            self.assertTrue(any(k == "generated_input" and name == "resources.qrc" and a.get("generator_family") == "rcc" for k, name, a in rows))
            self.assertTrue(any(k == "conditional_build" and "greaterThan" in name for k, name, _ in rows))

    def test_qrc_resource_declarations_are_mapped_without_executing_rcc(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, summary = self._scan(Path(tmp))
            assets = [n for n in summary["nodes"] if n["kind"] == "resource_asset"]
            self.assertEqual(len(assets), 1)
            attrs = json.loads(assets[0]["attributes_json"])
            self.assertEqual(attrs["resolved_path"], "sound/move.wav")
            self.assertEqual(attrs["resource_url"], ":/sound/move.wav")

    def test_legacy_signal_slot_connect_closes_action_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = self._scan(Path(tmp))
            store = Store(out / "scan_index.sqlite")
            closure = surface_closure(store)
            store.close()
            pvp = next(r for r in closure["records"] if r["name"] == "pvp")
            self.assertEqual(pvp["surface_type"], "QAction")
            self.assertEqual(pvp["closure"], "BOUND")
            self.assertTrue(any(step["kind"] == "dispatches_to" for step in pvp["example_route"]))

    def test_timer_single_shot_and_audio_repaint_feedback_extend_deep_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, summary = self._scan(Path(tmp))
            kinds = [(n["kind"], n["name"], json.loads(n["attributes_json"])) for n in summary["nodes"]]
            self.assertTrue(any(k == "recurrence_source" and name == "QTimer::singleShot" and a.get("single_shot") for k, name, a in kinds))
            self.assertTrue(any(k == "feedback" and name == "audio_feedback" for k, name, _ in kinds))
            self.assertTrue(any(k == "feedback" and name == "repaint_request" for k, name, _ in kinds))
            store = Store(out / "scan_index.sqlite")
            deep = effect_closure(store)
            store.close()
            pvp = next(r for r in deep["records"] if r["name"] == "pvp")
            mouse = next(r for r in deep["records"] if r["name"].endswith("mouseReleaseEvent"))
            self.assertEqual(pvp["effect_closure"], "CLOSED")
            self.assertEqual(mouse["effect_closure"], "CLOSED")


if __name__ == "__main__":
    unittest.main()

class PR6CrossFileReceiverTypeTests(unittest.TestCase):
    def test_fallback_member_static_type_resolves_cross_file_call_to_state_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = td / "specimen"
            root.mkdir()
            (root / "Model.h").write_text(
                "class Model { public: void start(); int state; };\n", encoding="utf-8"
            )
            (root / "Main.h").write_text(
                '#include "Model.h"\nclass Main { Model *model; public: void mouseReleaseEvent(QMouseEvent *event); };\n',
                encoding="utf-8",
            )
            # Deliberately make compiler parsing incomplete for Main.cpp. The fallback layer still has
            # enough direct source evidence to prove Main::model's declared static type.
            (root / "Main.cpp").write_text(
                '#include "Main.h"\n#include <DefinitelyMissingHeader>\n'
                'void Main::mouseReleaseEvent(QMouseEvent *event) { model->start(); }\n',
                encoding="utf-8",
            )
            (root / "Model.cpp").write_text(
                '#include "Model.h"\nvoid Model::start() { this->state = 1; }\n', encoding="utf-8"
            )
            out = td / "out"
            summary = ScanEngine().scan(root, out, "pr6-member-receiver@example")

            member = next(n for n in summary["nodes"] if n["kind"] == "member_symbol" and n["name"] == "Main::model")
            member_attrs = json.loads(member["attributes_json"])
            self.assertEqual(member_attrs.get("declared_type"), "Model")

            resolved = [e for e in summary["edges"] if e["kind"] == "resolves_to"
                        and json.loads(e["attributes_json"]).get("resolution") == "unique_class_member_static_type"]
            self.assertTrue(resolved)
            self.assertTrue(any(json.loads(e["attributes_json"]).get("qualified_name") == "Model::start" for e in resolved))

            store = Store(out / "scan_index.sqlite")
            deep = effect_closure(store)
            store.close()
            mouse = next(r for r in deep["records"] if r["name"].endswith("mouseReleaseEvent"))
            self.assertEqual(mouse["effect_closure"], "CLOSED")
            self.assertTrue(any(t["kind"] == "state_change" for t in mouse["terminals"]))
