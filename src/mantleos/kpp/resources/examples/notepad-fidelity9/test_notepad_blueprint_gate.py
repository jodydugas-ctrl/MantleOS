"""Round 9: the build-time WhiteHole rejects drift in copied candidates.

The 181 inherited tests remain unchanged. These tests never edit working
source in place: every negative test operates on an isolated temporary copy.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from notepad_blueprint_gate import WhiteHoleBlueprintGate, _suite_is_complete


ROOT = Path(__file__).resolve().parent


class BlueprintGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = WhiteHoleBlueprintGate(ROOT).evaluate()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path in ROOT.glob("*.py"):
            shutil.copy2(path, self.root / path.name)
        for name in ("anchorforge-spec.json", "blueprint-manifest.json"):
            shutil.copy2(ROOT / name, self.root / name)

    def _json(self, filename):
        return json.loads((self.root / filename).read_text(encoding="utf-8"))

    def _write(self, filename, content):
        (self.root / filename).write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")

    def _rejects(self, phrase):
        report = WhiteHoleBlueprintGate(self.root).evaluate()
        self.assertFalse(report.valid, report.as_dict())
        self.assertIn(phrase, "\n".join(report.violations))

    def test_valid_complete_blueprint(self):
        report = self.baseline
        self.assertTrue(report.valid, report.as_dict())
        self.assertEqual(report.anchor_count, 9)
        self.assertEqual(report.obligation_count, 27)
        self.assertEqual(report.preserved_test_count, 181)
        self.assertEqual(report.as_dict()["gate"], "WH-BLUEPRINT-GATE")

    def test_unittest_completed_suite_accepted(self):
        self.assertTrue(_suite_is_complete("Ran 213 tests in 3.2s\n\nOK", 182))

    def test_unittest_skipped_suite_rejected(self):
        self.assertFalse(_suite_is_complete("Ran 213 tests in 3.2s\n\nOK (skipped=30)", 182))

    def test_unittest_missing_summary_rejected(self):
        self.assertFalse(_suite_is_complete("OK", 182))

    def test_unittest_insufficient_count_rejected(self):
        self.assertFalse(_suite_is_complete("Ran 181 tests in 1.2s\n\nOK", 182))

    def test_declared_gate_is_not_a_runtime_command(self):
        spec = self._json("anchorforge-spec.json")
        self.assertEqual([a["id"] for a in spec["responsibilities"]].count("WH-BLUEPRINT-GATE"), 1)
        self.assertNotIn("blueprint-gate", self._json("blueprint-manifest.json")["runtime_actions"])

    def test_does_not_modify_candidate_files(self):
        paths = sorted(self.root.glob("*.py")) + sorted(self.root.glob("*.json"))
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        self.assertTrue(WhiteHoleBlueprintGate(self.root).evaluate().valid)
        after = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        self.assertEqual(before, after)

    def test_missing_anchor_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["responsibilities"].pop(0)
        self._write("anchorforge-spec.json", spec)
        self._rejects("fidelity, manifest fidelity and Anchor count")

    def test_duplicate_anchor_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["responsibilities"].append(spec["responsibilities"][0])
        self._write("anchorforge-spec.json", spec)
        self._rejects("every Anchor must have one distinct ID")

    def test_renamed_source_anchor_rejected(self):
        filename = "notepad_document.py"
        self._write(filename, (self.root / filename).read_text().replace('anchor_id = "N-DOCUMENT"', 'anchor_id = "N-OTHER"'))
        self._rejects("does not declare matching anchor_id")

    def test_missing_source_rejected(self):
        (self.root / "notepad_history.py").unlink()
        self._rejects("unable to parse notepad_history.py")

    def test_changed_state_owner_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["state"][0]["owner"] = "N-EDIT-HISTORY"
        self._write("anchorforge-spec.json", spec)
        self._rejects("state owner drift")

    def test_duplicate_protected_writer_rejected(self):
        filename = "notepad_surface.py"
        self._write(filename, (self.root / filename).read_text() + "\nclass DuplicateDocument:\n    def __init__(self):\n        self._text = 'shadow'\n")
        self._rejects("forbidden writer of _text")

    def test_owner_removed_rejected(self):
        filename = "notepad_document.py"
        self._write(filename, (self.root / filename).read_text().replace("self._baseline_text", "self._renamed_baseline"))
        self._rejects("missing declared owned state attribute _baseline_text")

    def test_effect_guard_change_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["effects"][0]["guard"] = "WH-BLUEPRINT-GATE"
        self._write("anchorforge-spec.json", spec)
        self._rejects("must pass runtime command guard")

    def test_effect_confirmation_removed_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["effects"][0]["confirmation"] = ""
        self._write("anchorforge-spec.json", spec)
        self._rejects("no confirmed success condition")

    def test_effect_executor_changed_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["effects"][2]["executor"] = "N-DOCUMENT"
        self._write("anchorforge-spec.json", spec)
        self._rejects("lost original executor")

    def test_undeclared_network_import_rejected(self):
        filename = "notepad_document.py"
        self._write(filename, (self.root / filename).read_text() + "\nimport socket\n")
        self._rejects("undeclared network module imported")

    def test_unguarded_file_open_rejected(self):
        filename = "notepad_search.py"
        self._write(filename, (self.root / filename).read_text() + "\ndef illicit_read(path):\n    return open(path).read()\n")
        self._rejects("forbidden host call open")

    def test_unguarded_clipboard_call_rejected(self):
        filename = "notepad_document.py"
        self._write(filename, (self.root / filename).read_text() + "\ndef illicit_clip(root):\n    return root.clipboard_get()\n")
        self._rejects("forbidden host call clipboard_get")

    def test_runtime_command_action_added_rejected(self):
        filename = "notepad_guard.py"
        self._write(filename, (self.root / filename).read_text().replace('"replace-all"})', '"replace-all", "network"})'))
        self._rejects("runtime command allowlist drift")

    def test_missing_whitehole_route_rejected(self):
        filename = "notepad_surface.py"
        self._write(filename, (self.root / filename).read_text().replace("self.guard.execute(intent,", "self.guard.not_guarded(intent,"))
        self._rejects("surface no longer sends captured intent through WH guard")

    def test_missing_required_flow_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["flows"] = [f for f in spec["flows"] if f["from"] != "WH-BLUEPRINT-GATE"]
        self._write("anchorforge-spec.json", spec)
        self._rejects("required flow missing")

    def test_unknown_flow_endpoint_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["flows"][0]["to"] = "N-INVENTED"
        self._write("anchorforge-spec.json", spec)
        self._rejects("flow has unknown endpoint")

    def test_removed_prior_obligation_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["obligations"].pop(0)
        self._write("anchorforge-spec.json", spec)
        self._rejects("preserved obligation removed")

    def test_obligation_cycle_rejected(self):
        spec = self._json("anchorforge-spec.json")
        spec["obligations"][0]["depends"] = [spec["obligations"][1]["id"]]
        spec["obligations"][1]["depends"] = [spec["obligations"][0]["id"]]
        self._write("anchorforge-spec.json", spec)
        self._rejects("dependency cycle")

    def test_uncovered_new_anchor_rejected(self):
        spec = self._json("anchorforge-spec.json")
        for obj in spec["obligations"]:
            obj["design_anchors"] = [a for a in obj["design_anchors"] if a != "WH-BLUEPRINT-GATE"]
        self._write("anchorforge-spec.json", spec)
        self._rejects("Anchor WH-BLUEPRINT-GATE is not covered")

    def test_missing_inherited_test_rejected(self):
        filename = "test_notepad_input.py"
        text = (self.root / filename).read_text()
        import re
        match = re.search(r"\bdef (test_\w+)\(", text)
        self.assertIsNotNone(match)
        self._write(filename, text.replace("def " + match.group(1) + "(", "def renamed_" + match.group(1) + "(", 1))
        self._rejects("inherited test method(s) removed or renamed")

    def test_missing_manifest_rejected(self):
        (self.root / "blueprint-manifest.json").unlink()
        self._rejects("cannot read blueprint-manifest.json")

    def test_syntax_invalid_candidate_rejected(self):
        self._write("notepad_document.py", "def this is not valid Python\n")
        self._rejects("unable to parse notepad_document.py")

    def test_cli_fails_closed_on_drift(self):
        spec = self._json("anchorforge-spec.json")
        spec["fidelity"] = 8
        self._write("anchorforge-spec.json", spec)
        output = subprocess.run([sys.executable, str(ROOT / "notepad_blueprint_gate.py"), "--root", str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(output.returncode, 1, output.stdout + output.stderr)
        self.assertIn('"valid": false', output.stdout)

    def test_cli_succeeds_on_valid_candidate(self):
        output = subprocess.run([sys.executable, str(ROOT / "notepad_blueprint_gate.py"), "--root", str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(output.returncode, 0, output.stdout + output.stderr)
        self.assertIn('"valid": true', output.stdout)


if __name__ == "__main__":
    unittest.main()
