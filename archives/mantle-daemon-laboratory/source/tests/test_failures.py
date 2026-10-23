from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from daemon.git_repo import GitRepo, StaleCheckpoint
from daemon.heart import CrashInjected, Heart
from daemon.actions import ActionsEmulator
from daemon.stack import Stack


PROJECT = Path(__file__).resolve().parents[1]


class FailureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "specimen"
        shutil.copytree(PROJECT / "genome", self.root / "genome")
        Stack.bootstrap(self.root)
        GitRepo(self.root).init_birth()

    def tearDown(self):
        self.temp.cleanup()

    def test_crash_before_commit_is_not_durable(self):
        parent = GitRepo(self.root).head()
        with self.assertRaises(CrashInjected):
            Heart(self.root).beat("before_commit")
        self.assertEqual(GitRepo(self.root).head(), parent)
        self.assertEqual(len(Stack(self.root).read("events")), 1)  # local candidate only
        # A clean checkout from the parent has no candidate event.
        checkout = Path(self.temp.name) / "clean"
        GitRepo(self.root)._run("clone", "-q", f"--branch", "master", str(self.root), str(checkout))
        self.assertEqual(len(Stack(checkout).read("events")), 0)

    def test_corruption_is_detected(self):
        path = self.root / "vcw/200_events.png"
        data = bytearray(path.read_bytes())
        data[-20] ^= 1
        path.write_bytes(data)
        self.assertTrue(Stack(self.root).verify())

    def test_stale_checkpoint_is_refused(self):
        repo = GitRepo(self.root)
        parent = repo.head()
        Heart(self.root).beat()
        with self.assertRaises(StaleCheckpoint):
            repo.commit(["STACK.json"], "stale checkpoint", expected_parent=parent)

    def test_manifest_mapping_and_missing_layer_are_detected(self):
        manifest = Stack(self.root).manifest()
        manifest["bands"]["events"]["path"] = "vcw/100_identity.png"
        (self.root / "STACK.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
        self.assertTrue(Stack(self.root).verify())

    def test_wrong_manifest_hash_is_detected(self):
        manifest = Stack(self.root).manifest()
        manifest["bands"]["events"]["sha256"] = "0" * 64
        (self.root / "STACK.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
        self.assertTrue(any("hash mismatch" in p for p in Stack(self.root).verify()))

    def test_primer_is_constitutional_and_receipt_is_validated(self):
        primer = self.root / "genome/primer.md"
        original = primer.read_bytes()
        primer.write_bytes(original + b"\nunauthorized")
        with self.assertRaises(ValueError):
            from daemon.body import Body
            Body.reconstruct(self.root)
        self.assertNotEqual(primer.read_bytes(), original)
        primer.write_bytes(original)
        receipt = Heart(self.root).beat()
        from daemon.receipt import validate_receipt
        self.assertEqual(validate_receipt(self.root / "receipts" / f"{receipt['beat_id']}.json"), [])

    def test_actions_read_only_and_write_loss_report_non_persistence(self):
        parent = GitRepo(self.root).head()
        result = ActionsEmulator().run(self.root, write_enabled=False)
        self.assertFalse(result.persisted)
        self.assertEqual(GitRepo(self.root).head(), parent)
        result = ActionsEmulator().run(self.root, write_enabled=True, lose_write_mid_run=True)
        self.assertFalse(result.persisted)
        self.assertEqual(GitRepo(self.root).head(), parent)

    def test_immune_evidence_redacts_credential_fields(self):
        from daemon.security import redact
        self.assertEqual(redact({"api_key": "dummy", "nested": {"token": "secret"}, "normal": "kept"}),
                         {"api_key": "[REDACTED]", "nested": {"token": "[REDACTED]"}, "normal": "kept"})

    def test_forked_stale_incarnation_cannot_overwrite_newer_checkpoint(self):
        import shutil
        parent = GitRepo(self.root).head()
        first = Path(self.temp.name) / "first"
        second = Path(self.temp.name) / "second"
        GitRepo(self.root)._run("clone", "-q", str(self.root), str(first))
        GitRepo(self.root)._run("clone", "-q", str(self.root), str(second))
        Heart(first).beat()
        Heart(second).beat()
        for rel in ("STACK.json", "vcw", "receipts"):
            source, target = first / rel, self.root / rel
            if source.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
        GitRepo(self.root).commit(["STACK.json", "vcw", "receipts"], "first fork checkpoint", expected_parent=parent)
        for rel in ("STACK.json", "vcw", "receipts"):
            source, target = second / rel, self.root / rel
            if source.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
        with self.assertRaises(StaleCheckpoint):
            GitRepo(self.root).commit(["STACK.json", "vcw", "receipts"], "stale fork", expected_parent=parent)
        self.assertNotEqual(GitRepo(self.root).head(), parent)
