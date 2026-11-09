import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from mantleos import heart, heart_trial as trial
from mantleos.heart_trial_checks import Clock


class HeartTrialTests(unittest.TestCase):
    def test_owned_accepts_ordinary_path_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work).resolve()
            self.assertEqual(trial.owned(root / "notes"), root / "notes")
            with self.assertRaisesRegex(ValueError, "Traversal"):
                trial.owned(root / ".." / "notes")

    @unittest.skipUnless(os.name == "nt", "Windows DOS short names")
    def test_owned_accepts_windows_short_name_for_same_directory(self):
        import ctypes

        with tempfile.TemporaryDirectory() as work:
            root = Path(work).resolve() / "Heart trial specimen folder"
            root.mkdir()
            short_name = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
            buffer = ctypes.create_unicode_buffer(32768)
            size = short_name(str(root), buffer, len(buffer))
            if not 0 < size < len(buffer) or Path(buffer.value) == root:
                self.skipTest("DOS short names unavailable for this volume")
            self.assertEqual(trial.owned(Path(buffer.value) / "notes"), root / "notes")

    def test_owned_rejects_linked_specimen_and_descendant(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work).resolve()
            target = root / "target"
            target.mkdir()
            link = root / "linked"
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Directory symlink creation unavailable")
            for path in (link, link / "notes"):
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "Linked specimen"):
                    trial.owned(path)

    @unittest.skipUnless(os.name == "nt", "Windows junctions")
    def test_owned_rejects_junction_and_missing_descendant(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work).resolve()
            target = root / "target"
            target.mkdir()
            link = root / "junction"
            result = subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(link), str(target)],
                                    capture_output=True)
            if result.returncode:
                self.skipTest("Directory junction creation unavailable")
            for path in (link, link / "notes"):
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "Linked specimen"):
                    trial.owned(path)

    def test_checked_candidate_rollback_and_synthetic_birth(self):
        with tempfile.TemporaryDirectory() as work:
            nest = Path(work) / "notes"
            clock = Clock()
            plant = heart.plant
            with patch.object(heart, "plant", side_effect=lambda root, primer, binding:
                              plant(root, primer, binding, wall=clock.wall)):
                trial.plant(nest)
            root = nest / ".heart"
            rhythm = heart.Rhythm(root, clock=clock.monotonic, wall=clock.wall)
            clock.tick = 600
            self.assertEqual(rhythm.poll()["kind"], "natural")
            seed_db = nest / "notes.sqlite"
            seed = seed_db.read_bytes()
            with self.assertRaisesRegex(ValueError, "review"):
                trial.stage(nest)
            with self.assertRaisesRegex(ValueError, "qualification"):
                trial.birth(nest, "invalid", "Synthetic")
            review = trial.stage(nest, reviewed=True)["review"]
            self.assertEqual(trial.status(nest)["status"], "AWAITING_EXPORT_APPROVAL")
            with self.assertRaisesRegex(ValueError, "does not match"):
                trial.edit_export(nest, "stale")
            candidate = root / "construction/candidate/notes_export.py"
            raw = candidate.read_bytes()
            candidate.write_bytes(raw + b"\n# drift\n")
            with self.assertRaisesRegex(ValueError, "stale"):
                trial.edit_export(nest, review)
            candidate.write_bytes(raw)

            # A write can complete before its outcome is published. Recovery
            # inspects bytes and never replays the write.
            append = heart.append

            def interrupt(root, kind, body, history):
                if kind == "heart.export-state":
                    raise OSError("simulated power interruption")
                return append(root, kind, body, history)

            with patch.object(heart, "append", side_effect=interrupt):
                with self.assertRaisesRegex(OSError, "interruption"):
                    trial.edit_export(nest, review)
            self.assertEqual(trial.status(nest)["status"], "BLOCKED")
            recovered = trial.recover(nest)
            self.assertTrue(recovered["enabled"])
            self.assertEqual(seed_db.read_bytes(), seed)
            self.assertTrue(trial.notes(nest / "notes.py", seed_db, "export").startswith("1: "))
            trial.edit_export(nest, recovered["change"], remove=True)
            self.assertFalse((nest / "notes_export.py").exists())
            self.assertEqual(seed_db.read_bytes(), seed)
            self.assertEqual(candidate.read_bytes(), raw)
            trial.edit_export(nest, review)
            qualified = trial.qualify(nest, reviewed=True)
            self.assertEqual(len(qualified["obligations"]), 13)
            self.assertEqual(trial.status(nest)["status"], "READY_FOR_BIRTH")
            with self.assertRaisesRegex(ValueError, "does not match"):
                trial.birth(nest, review, "Synthetic")
            primer = root / "PRIMER.md"
            founding = primer.read_bytes()
            primer.unlink()
            with self.assertRaises(FileNotFoundError):
                trial.birth(nest, qualified["review"], "Synthetic")
            primer.write_bytes(founding)
            self.assertEqual(trial.birth(nest, qualified["review"], "Synthetic")["status"], "BORN")
            self.assertEqual(trial.status(nest)["status"], "BORN")
            self.assertEqual(json.loads(trial.notes(nest / "notes.py", seed_db, "read", "1")),
                             trial.SEED + " Updated.")

    def test_failed_candidate_retained_without_review(self):
        with tempfile.TemporaryDirectory() as work:
            nest = Path(work) / "notes"
            trial.plant(nest)
            run_checks = trial.run_checks

            def break_candidate(work, candidate, contract, cases):
                (candidate / "notes_export.py").write_text("def render(rows): return 'broken'\n")
                return run_checks(work, candidate, contract, cases)

            with patch.object(trial, "run_checks", side_effect=break_candidate):
                with self.assertRaisesRegex(ValueError, "checks failed"):
                    trial.stage(nest, reviewed=True)
            self.assertEqual(trial.status(nest)["status"], "BLOCKED")
            with self.assertRaisesRegex(ValueError, "No reviewed candidate"):
                trial.edit_export(nest, "anything")
            recovered = trial.recover(nest)
            self.assertTrue((nest / ".heart" / recovered["retained"]).is_dir())
            self.assertFalse((nest / "notes_export.py").exists())
