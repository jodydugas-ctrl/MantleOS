from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scan.engine import ScanEngine


CPP = r'''#include <QtConcurrent>
#include <QFutureWatcher>

void Loader::start() {
    auto future = QtConcurrent::run(loadImage, path);
    watcher.setFuture(future);
    connect(&watcher, &QFutureWatcher<QImage>::finished, this, &Loader::finish);
}

void Loader::finish() {
    imageLabel->setPixmap(resultPixmap);
}
'''

UNBOUND = r'''#include <QtConcurrent>
void Loader::start() {
    QtConcurrent::run(loadImage, path);
}
'''

EXTERNAL_FUTURE = r'''#include <QFutureWatcher>
void Loader::attach(QFuture<QImage> future) {
    watcher.setFuture(future);
    connect(&watcher, &QFutureWatcher<QImage>::finished, this, &Loader::finish);
}
void Loader::finish() {}
'''


class PR6DAsyncClosureTests(unittest.TestCase):
    def _scan(self, source: str):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name) / "specimen"
        root.mkdir()
        (root / "Loader.cpp").write_text(source, encoding="utf-8")
        out = Path(td.name) / "out"
        summary = ScanEngine().scan(root, out, "pr6d-async@example")
        return td, summary

    def test_qtconcurrent_future_watcher_chain_is_first_class(self):
        td, summary = self._scan(CPP)
        try:
            tasks = [n for n in summary["nodes"] if n["kind"] == "async_task"]
            self.assertEqual(len(tasks), 1)
            attrs = json.loads(tasks[0]["attributes_json"])
            self.assertEqual(attrs["mechanism"], "QtConcurrent::run")
            self.assertEqual(attrs["future_variable"], "future")

            async_edges = [e for e in summary["edges"] if e["kind"] == "delivers_async_to"]
            self.assertEqual(len(async_edges), 1)
            watcher_id = async_edges[0]["dst"]

            finished_events = [n for n in summary["nodes"]
                               if n["kind"] == "event" and "finished" in n["name"]]
            self.assertEqual(len(finished_events), 1)
            self.assertTrue(any(e["src"] == watcher_id and e["dst"] == finished_events[0]["id"]
                                and e["kind"] == "emits" for e in summary["edges"]))
            self.assertTrue(any(e["src"] == finished_events[0]["id"] and e["kind"] == "dispatches_to"
                                for e in summary["edges"]))
        finally:
            td.cleanup()

    def test_unassigned_qtconcurrent_launch_stays_partial_not_dropped(self):
        td, summary = self._scan(UNBOUND)
        try:
            task = next(n for n in summary["nodes"] if n["kind"] == "async_task")
            self.assertEqual(task["coverage"], "PARTIAL")
            attrs = json.loads(task["attributes_json"])
            self.assertFalse(attrs["continuation_known"])
        finally:
            td.cleanup()

    def test_external_future_attachment_preserves_unknown_launch_site(self):
        td, summary = self._scan(EXTERNAL_FUTURE)
        try:
            ref = next(n for n in summary["nodes"] if n["kind"] == "async_task_reference")
            self.assertEqual(ref["coverage"], "PARTIAL")
            attrs = json.loads(ref["attributes_json"])
            self.assertFalse(attrs["launch_site_observed"])
            edge = next(e for e in summary["edges"] if e["kind"] == "delivers_async_to")
            self.assertEqual(edge["coverage"], "PARTIAL")
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()

class PR6DAsyncDeepClosureTests(unittest.TestCase):
    def test_surface_effect_closure_traverses_async_continuation(self):
        source = r'''#include <QAction>
#include <QtConcurrent>
#include <QFutureWatcher>
#include <QFile>

void Loader::wire() {
    auto *runAction = new QAction("Run");
    connect(runAction, &QAction::triggered, this, &Loader::start);
}
void Loader::start() {
    auto future = QtConcurrent::run(loadImage, path);
    watcher.setFuture(future);
    connect(&watcher, &QFutureWatcher<QImage>::finished, this, &Loader::finish);
}
void Loader::finish() {
    QFile::remove(tempPath);
}
'''
        td = tempfile.TemporaryDirectory()
        try:
            root = Path(td.name) / "specimen"
            root.mkdir()
            (root / "Loader.cpp").write_text(source, encoding="utf-8")
            out = Path(td.name) / "out"
            ScanEngine().scan(root, out, "pr6d-deep-closure@example")
            deep = json.loads((out / "effect_closure.json").read_text(encoding="utf-8"))
            run = next(r for r in deep["records"] if r["name"] == "runAction")
            self.assertEqual(run["effect_closure"], "CLOSED")
            self.assertTrue(any(t["name"] == "filesystem_write" for t in run["terminals"]))
            route_kinds = [step["kind"] for t in run["terminals"] for step in t.get("example_route", [])]
            self.assertIn("triggers_async", route_kinds)
            self.assertIn("delivers_async_to", route_kinds)
        finally:
            td.cleanup()
