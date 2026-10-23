#!/usr/bin/env python3
"""Parity test for the language-agnostic assimilation path.

Asserts the JS organ map (via mantle.assimilator.scanner_ts) equals the Python organ
map (via mantle.assimilator.scanner) for the equivalent notes_app fixture, and that the
record shape matches. Skips cleanly if tree-sitter isn't installed -- the multilang path
is opt-in and Python-only behavior is unaffected either way.
"""
import os
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.join(  # the mantle package (src-layout)
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))

from mantle.assimilator import scanner
from mantle.assimilator import scanner_ts
from mantle.assimilator.organ_map import ROLE_TO_ORGAN

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_app")

EXPECTED_SAMPLE_ROLES = {
    "sanitize_note_text": "ERROR_DEFENSE",
    "validate_note": "ERROR_DEFENSE",
    "check_auth_token": "SECRET_BOUNDARY",
    "set_note": "STATE_TRANSITION",
    "update_note": "STATE_TRANSITION",
    "save_notes": "PERSISTENCE_WRITE",
    "handle_create_note": "SENSOR_EVENT",
    "on_timer_tick": "HEARTBEAT",
    "send_notification": "ARM_ACTION",
    "render_note_list": "DISPLAY_RENDER",
    "summarize_notes": "INTERNAL_UTILITY",
    "suggest_tags_with_llm": "MIND_AFFORDANCE",
    "main_loop": "HEARTBEAT",
}


def _organ_counts(symbols):
    counts = Counter()
    for sym in symbols:
        organ = ROLE_TO_ORGAN.get(sym["role"])
        if organ:
            counts[organ] += 1
    return dict(counts)


class MultiLangParityTest(unittest.TestCase):
    def test_sample_app_role_map_is_the_teaching_contract(self):
        """Keep examples/sample_app aligned with its README role map."""
        py = scanner.scan_file(os.path.join(SAMPLE_DIR, "notes_app.py"), "notes_app.py")
        roles = {sym["symbol"]: sym["role"] for sym in py["symbols"]}
        self.assertEqual(roles, EXPECTED_SAMPLE_ROLES)

    @unittest.skipUnless(scanner_ts.available(), "tree-sitter stack not installed")
    def test_js_organ_map_matches_python(self):
        py = scanner.scan_file(os.path.join(SAMPLE_DIR, "notes_app.py"), "notes_app.py")
        js = scanner_ts.scan_file(os.path.join(SAMPLE_DIR, "notes_app.js"), "notes_app.js")

        self.assertEqual(_organ_counts(py["symbols"]), _organ_counts(js["symbols"]))

        for sym in js["symbols"]:
            self.assertEqual(set(sym.keys()), {"symbol", "kind", "line", "role"})

    @unittest.skipUnless(scanner_ts.available(), "tree-sitter stack not installed")
    def test_read_only(self):
        path = os.path.join(SAMPLE_DIR, "notes_app.js")
        before = Path(path).read_bytes()
        scanner_ts.scan_file(path, "notes_app.js")
        after = Path(path).read_bytes()
        self.assertEqual(before, after)

    def test_scan_project_without_treesitter_is_unchanged(self):
        """Without the optional dependency, scan_project behaves exactly as before."""
        dissection = scanner.scan_project(SAMPLE_DIR)
        self.assertTrue(dissection["read_only"])
        self.assertIn("multilang", dissection)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MultiLangParityTest)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if os.environ.get("MANTLE_REQUIRE_NO_SKIPS") == "1" and result.skipped:
        print("STRICT: %d multi-language test(s) did not execute" % len(result.skipped))
        raise SystemExit(2)
    raise SystemExit(0 if result.wasSuccessful() else 1)
