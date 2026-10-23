from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from daemon.body import Body
from daemon.git_repo import GitRepo
from daemon.heart import Heart
from daemon.runtime import run_incarnations
from daemon.stack import Stack
from daemon.png import pack_layer, unpack_layer


PROJECT = Path(__file__).resolve().parents[1]


class DaemonTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "specimen"
        shutil.copytree(PROJECT / "genome", self.root / "genome")
        Stack.bootstrap(self.root)
        GitRepo(self.root).init_birth()

    def tearDown(self):
        self.temp.cleanup()

    def test_body_reconstructs_without_mind(self):
        body = Body.reconstruct(self.root)
        self.assertEqual(body.identity["stable_id"], "daemon-lab-0001")
        self.assertEqual(body.stack.read("events"), [])

    def test_self_bootstrap_constitution_is_explicit(self):
        identity = json.loads((self.root / "genome/identity.json").read_text(encoding="utf-8"))
        self.assertEqual(identity["self_components"], ["PRIMER", "IMMUNE", "SPECIAL"])

    def test_empty_layer_round_trip_is_byte_stable(self):
        path = self.root / "vcw/100_identity.png"
        original = path.read_bytes()
        boot, payload = unpack_layer(original)
        self.assertEqual(original, pack_layer(boot, payload))

    def test_history_keeps_birth_state_inspectable(self):
        birth = GitRepo(self.root).head()
        Heart(self.root).beat()
        child = GitRepo(self.root).head()
        self.assertNotEqual(birth, child)
        old = Path(self.temp.name) / "old"
        GitRepo(self.root)._run("clone", "-q", str(self.root), str(old))
        GitRepo(old)._run("checkout", "-q", birth)
        self.assertEqual(Stack(old).verify(), [])
        self.assertEqual(Stack(old).read("events"), [])

    def test_replaying_a_completed_beat_id_is_idempotent(self):
        first = Heart(self.root).beat(beat_id="beat-fixed")
        second = Heart(self.root).beat(beat_id="beat-fixed")
        self.assertEqual(first["after_stack"], second["after_stack"])
        self.assertEqual(len(Stack(self.root).read("events")), 1)

    def test_png_stack_round_trip_and_heartbeat(self):
        birth = GitRepo(self.root).head()
        before = Stack(self.root).fingerprint()
        receipt = Heart(self.root).beat()
        self.assertFalse(receipt["mind_invoked"])
        self.assertNotEqual(before, receipt["after_stack"])
        self.assertEqual(Stack(self.root).verify(), [])
        self.assertEqual(len(Stack(self.root).read("events")), 1)
        self.assertEqual(GitRepo(self.root).status(), [])
        self.assertEqual(set(GitRepo(self.root).changed_paths(birth)), {"STACK.json", "vcw/200_events.png", f"receipts/{receipt['beat_id']}.json"})

    def test_five_destroy_reconstruct_cycles(self):
        receipts = run_incarnations(self.root, 5)
        self.assertEqual(len(receipts), 5)
        self.assertEqual(len(Stack(self.root).read("events")), 5)
        self.assertEqual(len(list((self.root / "receipts").glob("*.json"))), 5)
        self.assertEqual(Stack(self.root).verify(), [])
