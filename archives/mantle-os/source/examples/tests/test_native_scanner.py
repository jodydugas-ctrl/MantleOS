#!/usr/bin/env python3
"""Native/Qt/Rust fallback scanner regression coverage."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mantle.assimilator import scanner, scanner_native, scanner_rust


class NativeScannerTest(unittest.TestCase):
    def test_cpp_constructor_connect_and_multirole(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "window.cpp"
            path.write_text(
                "#include <QMainWindow>\n"
                "Window::Window(QWidget *parent)\n"
                "  : QMainWindow(parent), ready_(false)\n"
                "{\n"
                "  connect(actionOpen, &QAction::triggered, this, [this](bool checked) {\n"
                "    if (checked) { openFile(); }\n"
                "  });\n"
                "}\n"
                "void Window::saveSettings() { QSettings s; s.setValue(\"ready\", ready_); }\n",
                encoding="utf-8",
            )
            result = scanner_native.scan_file(str(path), "src/window.cpp")
            by_name = {item["symbol"]: item for item in result["symbols"]}
            self.assertIn("Window::Window", by_name)
            if "tree-sitter" in result["parser"]:
                self.assertTrue(by_name["Window::Window"]["structured"])
            self.assertEqual(by_name["Window::Window"]["qt_edges"][0]["kind"], "qt-connect")
            self.assertEqual(len(by_name["Window::Window"]["qt_edges"][0]["args"]), 4)
            self.assertIn("PERSISTENCE_WRITE",
                          {role["role"] for role in by_name["Window::saveSettings"]["roles"]})

    def test_ui_qrc_and_cmake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.ui").write_text(
                '<ui><class>Main</class><widget class="QMainWindow" name="Main">'
                '<widget class="QMenu" name="menuFile"><addaction name="actionOpen"/></widget>'
                '<action name="actionOpen"><property name="text"><string>&amp;Open</string></property></action>'
                '</widget><connections><connection><sender>actionOpen</sender><signal>triggered()</signal>'
                '<receiver>Main</receiver><slot>open()</slot></connection></connections></ui>',
                encoding="utf-8",
            )
            (root / "icon.svg").write_text("<svg/>", encoding="utf-8")
            (root / "app.qrc").write_text(
                "<RCC><qresource prefix='/icons'><file alias='app'>icon.svg</file></qresource></RCC>",
                encoding="utf-8",
            )
            (root / "CMakeLists.txt").write_text(
                "add_executable(app main.cpp window.cpp)\ntarget_sources(app PRIVATE extra.cpp)\n",
                encoding="utf-8",
            )
            ui = scanner_native.scan_file(str(root / "main.ui"), "main.ui")
            qrc = scanner_native.scan_file(str(root / "app.qrc"), "app.qrc")
            cmake = scanner_native.scan_file(str(root / "CMakeLists.txt"), "CMakeLists.txt")
            self.assertTrue(any(item["kind"] == "ui-action" for item in ui["symbols"]))
            self.assertTrue(any(item["kind"] == "ui-connection" for item in ui["symbols"]))
            self.assertEqual(qrc["coverage"], "complete")
            self.assertEqual(cmake["symbols"][0]["symbol"], "app")

    def test_rust_fallback_and_project_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rust = root / "main.rs"
            rust.write_text(
                "use std::process::Command;\nfn main() { let _ = Command::new(\"echo\").status(); }\n",
                encoding="utf-8",
            )
            fallback = scanner_rust.scan_file(str(rust), "main.rs")
            self.assertEqual(fallback["symbols"][0]["role"], "HEARTBEAT")
            project = scanner.scan_project(str(root))
            self.assertEqual(project["schema"], "mantle-host-evidence-v3")
            self.assertIn(project["coverage_state"], {"complete", "partial"})


if __name__ == "__main__":
    unittest.main()
