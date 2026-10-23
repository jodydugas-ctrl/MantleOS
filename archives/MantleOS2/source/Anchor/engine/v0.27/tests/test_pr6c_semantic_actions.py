from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scan.engine import ScanEngine


CPP = r'''#include <QAction>
#include <QMenu>

void ActionManager::initializeActionLibrary() {
    auto *openAction = new QAction("Open");
    actionLibrary.insert("open", openAction);
    auto *ghostAction = new QAction("Ghost");
    actionLibrary.insert("ghost", ghostAction);
}

void ActionManager::build(QMenu *menu) {
    addCloneOfAction(menu, "open");
}

void ActionManager::actionTriggered(QAction *triggeredAction, MainWindow *relevantWindow) {
    auto key = triggeredAction->data().toStringList().first();
    if (key == "open") {
        relevantWindow->openFile();
    }
}

void ActionManager::buildRecents(QMenu *menu) {
    for (int i = 0; i < recentsListMaxLength; i++) {
        auto action = new QAction("Empty", menu);
        action->setData("recent" + QString::number(i));
        menu->addAction(action);
    }
}

void ActionManager::dispatchRecent(QAction *triggeredAction) {
    auto key = triggeredAction->data().toStringList().first();
    if (key.startsWith("recent")) {
        openRecent();
    }
}
'''

CMAKE_CONTRADICTION = r'''cmake_minimum_required(VERSION 3.16)
project(Test)
option(DISABLE_NET "Disable network" OFF)
if(NOT DISABLE_NET)
    list(APPEND PROJECT_SOURCES update.cpp)
    target_compile_definitions(Test PRIVATE DISABLE_NET)
endif()
'''

CMAKE_NORMAL = r'''cmake_minimum_required(VERSION 3.16)
project(Test)
option(DISABLE_NET "Disable network" OFF)
if(DISABLE_NET)
    target_compile_definitions(Test PRIVATE DISABLE_NET)
endif()
'''


class PR6CSemanticActionTests(unittest.TestCase):
    def _scan_cpp(self, source: str):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name) / "specimen"
        root.mkdir()
        (root / "ActionManager.cpp").write_text(source, encoding="utf-8")
        out = Path(td.name) / "out"
        summary = ScanEngine().scan(root, out, "pr6c-semantic-action@example")
        return td, summary

    def test_registry_actions_are_semantic_identities_and_clones_are_route_instances(self):
        td, summary = self._scan_cpp(CPP)
        try:
            actions = {
                n["name"]: json.loads(n["attributes_json"])
                for n in summary["nodes"] if n["kind"] == "semantic_action"
            }
            self.assertIn("open", actions)
            self.assertIn("ghost", actions)
            self.assertEqual(actions["open"].get("semantic_key"), "open")

            instances = [
                n for n in summary["nodes"]
                if n["kind"] == "surface_instance" and n["name"] == "open"
            ]
            self.assertEqual(len(instances), 1)
            edges = [e for e in summary["edges"] if e["kind"] == "has_surface_instance"]
            self.assertEqual(len(edges), 1)
        finally:
            td.cleanup()

    def test_payload_dispatch_and_dynamic_family_are_first_class(self):
        td, summary = self._scan_cpp(CPP)
        try:
            cases = [
                (n["name"], json.loads(n["attributes_json"]))
                for n in summary["nodes"] if n["kind"] == "dispatch_case"
            ]
            self.assertTrue(any(name == "open" and a.get("dispatch_kind") == "payload_key_equality"
                                for name, a in cases))
            self.assertTrue(any(name == "recent*" and a.get("dispatch_kind") == "payload_key_prefix"
                                for name, a in cases))

            family = next(n for n in summary["nodes"]
                          if n["kind"] == "dynamic_surface_family" and n["name"] == "recent")
            attrs = json.loads(family["attributes_json"])
            self.assertEqual(attrs.get("bound_expression"), "recentsListMaxLength")
        finally:
            td.cleanup()


    def test_duplicate_payload_dispatch_case_is_preserved_as_anomaly(self):
        source = CPP.replace(
            'if (key == "open") {\n        relevantWindow->openFile();\n    }',
            'if (key == "open") {\n        relevantWindow->openFile();\n    } else if (key == "open") {\n        relevantWindow->openFile();\n    }'
        )
        td, summary = self._scan_cpp(source)
        try:
            findings = [f for f in summary["findings"] if f["kind"] == "duplicate_dispatch_case"]
            self.assertEqual(len(findings), 1)
            self.assertIn("open", findings[0]["title"])
        finally:
            td.cleanup()

    def test_registry_action_without_payload_dispatch_is_preserved_as_candidate_gap(self):
        td, summary = self._scan_cpp(CPP)
        try:
            gaps = [f for f in summary["findings"]
                    if f["kind"] == "semantic_action_dispatch_gap"]
            titles = {f["title"] for f in gaps}
            self.assertIn("No payload dispatch case observed for semantic action: ghost", titles)
            self.assertNotIn("No payload dispatch case observed for semantic action: open", titles)
        finally:
            td.cleanup()


class PR6CBuildContradictionTests(unittest.TestCase):
    def _scan_cmake(self, source: str):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name) / "specimen"
        root.mkdir()
        (root / "CMakeLists.txt").write_text(source, encoding="utf-8")
        out = Path(td.name) / "out"
        summary = ScanEngine().scan(root, out, "pr6c-cmake@example")
        return td, summary

    def test_compile_definition_inside_if_not_same_symbol_is_preserved(self):
        td, summary = self._scan_cmake(CMAKE_CONTRADICTION)
        try:
            findings = [f for f in summary["findings"]
                        if f["kind"] == "build_condition_contradiction"]
            self.assertEqual(len(findings), 1)
            self.assertIn("DISABLE_NET", findings[0]["title"])
        finally:
            td.cleanup()

    def test_normal_positive_guard_is_not_reported_as_contradiction(self):
        td, summary = self._scan_cmake(CMAKE_NORMAL)
        try:
            findings = [f for f in summary["findings"]
                        if f["kind"] == "build_condition_contradiction"]
            self.assertEqual(findings, [])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
