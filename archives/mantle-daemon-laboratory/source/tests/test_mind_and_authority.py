from __future__ import annotations

import shutil
import tempfile
import unittest
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from pathlib import Path

from daemon.git_repo import GitRepo
from daemon.heart import Heart
from daemon.mind import AlternateFakeMind, FakeMind
from daemon.stack import Stack
from daemon.carrier import evaluate_arrival, inspect_carrier
from daemon.security import confined_path, may_write_specimen
from daemon.receipt import validate_receipt
from daemon.github_actions import ActionsContext
from daemon.provider import HttpJsonMind
from daemon.secret_audit import scan


PROJECT = Path(__file__).resolve().parents[1]


class MindBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "specimen"
        shutil.copytree(PROJECT / "genome", self.root / "genome")
        Stack.bootstrap(self.root)
        GitRepo(self.root).init_birth()

    def tearDown(self):
        self.temp.cleanup()

    def test_fake_mind_is_replaceable_and_admitted_by_body(self):
        receipt = Heart(self.root, mind=FakeMind()).beat(significant=True)
        self.assertTrue(receipt["mind_invoked"])
        self.assertTrue(receipt["cognitive"]["admission"]["admitted"])
        self.assertEqual(Stack(self.root).verify(), [])
        self.assertEqual(validate_receipt(self.root / "receipts" / f"{receipt['beat_id']}.json"), [])

    def test_second_provider_shape_preserves_body_admission(self):
        first = Heart(self.root, mind=FakeMind()).beat(significant=True)
        second = Heart(self.root, mind=AlternateFakeMind()).beat(significant=True)
        self.assertNotEqual(first["cognitive"]["provider_id"], second["cognitive"]["provider_id"])
        self.assertTrue(first["cognitive"]["admission"]["admitted"])
        self.assertTrue(second["cognitive"]["admission"]["admitted"])
        self.assertEqual(Stack(self.root).verify(), [])

    def test_live_adapter_requires_explicit_endpoint_and_secret_stays_out_of_receipt(self):
        with self.assertRaises(ValueError):
            HttpJsonMind()
        class SecretMind:
            provider_id = "secret-test"
            def propose(self, context):
                return {"opcode": "MIND_NOTE", "content": {"message": "ok", "api_key": "do-not-persist"}}
        receipt = Heart(self.root, mind=SecretMind()).beat(significant=True)
        serialized = (self.root / "receipts" / f"{receipt['beat_id']}.json").read_text(encoding="utf-8")
        self.assertNotIn("do-not-persist", serialized)
        self.assertEqual(Stack(self.root).verify(), [])
        self.assertEqual(scan(self.root, ["do-not-persist"]), [])

    def test_provider_neutral_http_adapter_contract(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"proposal": {"opcode": "MIND_NOTE", "content": {"ok": True}}}).encode())
            def log_message(self, *args):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        Thread(target=server.handle_request, daemon=True).start()
        try:
            proposal = HttpJsonMind(f"http://127.0.0.1:{server.server_port}").propose({"events": []})
            self.assertEqual(proposal["opcode"], "MIND_NOTE")
        finally:
            server.server_close()

    def test_invalid_proposal_is_refused_without_stack_corruption(self):
        class InvalidMind:
            provider_id = "invalid-test"
            def propose(self, context):
                return {"opcode": "EXECUTE_FOREIGN_CODE", "content": "no"}
        receipt = Heart(self.root, mind=InvalidMind()).beat(significant=True)
        self.assertFalse(receipt["cognitive"]["admission"]["admitted"])
        self.assertEqual(Stack(self.root).verify(), [])

    def test_routine_beat_does_not_wake_mind(self):
        receipt = Heart(self.root, mind=FakeMind()).beat(significant=False)
        self.assertFalse(receipt["mind_invoked"])

    def test_carrier_is_inert_and_partial_grant_stays_bounded(self):
        carrier = inspect_carrier(self.root)
        self.assertTrue(carrier["inert"])
        self.assertEqual(carrier["execution"], "not-permitted")
        request = {"stable_id": carrier["stable_id"], "mission_id": carrier["mission_id"],
                   "requested_capabilities": ["write_specimen", "network"], "evidence": {}, "boundaries": {"scope": "lab"}}
        result = evaluate_arrival(request, {"write_specimen": "granted"})
        self.assertEqual(result["granted_capabilities"], ["write_specimen"])
        self.assertTrue(result["persist"])
        refused = evaluate_arrival(request, {})
        self.assertFalse(refused["persist"])

    def test_authority_and_path_confinement(self):
        self.assertTrue(may_write_specimen(self.root))
        with self.assertRaises(PermissionError):
            confined_path(self.root, "../outside")

    def test_actions_context_maps_permission_explicitly(self):
        context = ActionsContext.from_environment({"GITHUB_REPOSITORY": "lab/specimen",
                                                   "GITHUB_SHA": "abc", "GITHUB_REF": "refs/heads/main",
                                                   "MANTLE_CHECKPOINT_WRITE": "true"})
        self.assertTrue(context.write_enabled)
        self.assertEqual(context.commit_sha, "abc")
        denied = ActionsContext.from_environment({"GITHUB_SHA": "abc"})
        self.assertFalse(denied.write_enabled)
