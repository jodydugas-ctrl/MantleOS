from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mantleos.nutrition import NutritionError, parse_openrouter_food
from mantleos.runtime import (
    VCW,
    BodyCipher,
    Book,
    MantleBody,
    MantleError,
    _load_sealed_json,
    _restrict_identity_key,
    _save_sealed_json,
    canonical_json,
    sha256_bytes,
)


class TestCipher:
    """Deterministic reversible cipher double; production never selects it."""

    def seal(self, value: bytes, *, purpose: str) -> bytes:
        mask = hashlib.sha256(purpose.encode("utf-8")).digest()
        return bytes(byte ^ mask[index % len(mask)] for index, byte in enumerate(value))

    def open(self, value: bytes, *, purpose: str) -> bytes:
        return self.seal(value, purpose=purpose)


class FakeAESGCM:
    """Authenticated test double used only behind a patched dependency gate."""

    def __init__(self, key: bytes):
        self.key = key

    def encrypt(self, nonce: bytes, value: bytes, associated_data: bytes) -> bytes:
        mask = hashlib.sha256(self.key + nonce + associated_data).digest()
        ciphertext = bytes(byte ^ mask[index % len(mask)] for index, byte in enumerate(value))
        tag = hashlib.sha256(self.key + nonce + associated_data + ciphertext).digest()
        return tag + ciphertext

    def decrypt(self, nonce: bytes, value: bytes, associated_data: bytes) -> bytes:
        tag, ciphertext = value[:32], value[32:]
        expected = hashlib.sha256(self.key + nonce + associated_data + ciphertext).digest()
        if tag != expected:
            raise ValueError("authentication failed")
        mask = hashlib.sha256(self.key + nonce + associated_data).digest()
        return bytes(byte ^ mask[index % len(mask)] for index, byte in enumerate(ciphertext))


def prepare_unborn_nest(nest: Path) -> None:
    primer = nest / "mantle" / "primer"
    primer.mkdir(parents=True)
    (primer / "COMMANDMENTS.md").write_text("Protect your VCW.", encoding="utf-8")
    private_construction = nest / ".mantle" / "construction"
    private_construction.mkdir(parents=True)
    personality = private_construction / "PERSONALITY.CANDIDATE.md"
    personality.write_text("Preserve the frame.\n" * 30, encoding="utf-8")
    evidence = private_construction / "personality-evidence.json"
    evidence.write_text('{"source":"test"}\n', encoding="utf-8")
    manifest_path = nest / "mantle" / "ASSIMILATION.json"
    delta_paths = [
        "mantle/ASSIMILATION.json",
        "mantle/primer/COMMANDMENTS.md",
    ]
    checksums = {
        relative: hashlib.sha256((nest / relative).read_bytes()).hexdigest()
        for relative in delta_paths
        if relative != "mantle/ASSIMILATION.json"
    }
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "mantle.assimilation.v2",
                "status": "constructed-not-born",
                "delta": {"paths": delta_paths, "sha256": checksums},
            }
        ),
        encoding="utf-8",
    )
    (nest / ".mantle" / "prebirth.json").write_text(
        json.dumps(
            {
                "schema": "mantle.prebirth.v2",
                "status": "constructed-not-born",
                "public_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                "gates": {"primer": "ready-for-birth-review"},
                "primer_candidate": {
                    "personality_sha256": hashlib.sha256(personality.read_bytes()).hexdigest(),
                    "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                    "status": "ready-for-birth-review",
                },
            }
        ),
        encoding="utf-8",
    )
    (nest / ".gitignore").write_text(
        "/.mantle/\n/COMMUNICATION.TXT\n/Food.txt\n",
        encoding="utf-8",
    )


class VCWTests(unittest.TestCase):
    def test_append_verify_and_extension_reuse_book(self):
        with tempfile.TemporaryDirectory() as temporary:
            book = Book("app", "Example application", "book:example:v1", capacity=460)
            vcw = VCW(Path(temporary), TestCipher(), [book])
            vcw.initialize()
            for number in range(8):
                vcw.append("app", "example", {"number": number, "text": "x" * 60})
            proof = vcw.verify()
            files = sorted((Path(temporary) / "app").glob("*.jsonl"))
            self.assertGreater(len(files), 1)
            self.assertEqual(8, proof["records"])
            headers = [json.loads(path.read_text(encoding="utf-8").splitlines()[0]) for path in files]
            self.assertEqual({"book:example:v1"}, {header["book_id"] for header in headers})
            self.assertEqual({"STATE_EVENT"}, {header["tome"] for header in headers})
            self.assertEqual({"canonical-json-v2"}, {header["dialect"] for header in headers})
            self.assertEqual(files[0].name, headers[1]["extension_of"])

    def test_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            book = Book("app", "Example application", "book:example:v1")
            vcw = VCW(Path(temporary), TestCipher(), [book])
            vcw.initialize()
            vcw.append("app", "example", {"value": 1})
            path = next((Path(temporary) / "app").glob("*.jsonl"))
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace('"sequence": 1', '"sequence": 2'), encoding="utf-8")
            with self.assertRaises(MantleError):
                vcw.verify()

    def test_mind_frontier_is_bounded_and_advances_only_over_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            book = Book("app", "Example application", "book:example:v1")
            vcw = VCW(Path(temporary), TestCipher(), [book])
            vcw.initialize()
            for number in range(5):
                vcw.append("app", "example", {"number": number})
            first, frontier = vcw.events_after({}, limit=2)
            second, next_frontier = vcw.events_after(frontier, limit=2)
            final, final_frontier = vcw.events_after(next_frontier, limit=2)
            self.assertEqual([0, 1], [event["data"]["number"] for event in first])
            self.assertEqual([2, 3], [event["data"]["number"] for event in second])
            self.assertEqual([4], [event["data"]["number"] for event in final])
            self.assertNotEqual(frontier, next_frontier)
            self.assertNotEqual(next_frontier, final_frontier)


class GateTests(unittest.TestCase):
    def test_windows_identity_key_acl_removes_inherited_general_access(self):
        with tempfile.TemporaryDirectory() as temporary:
            key = Path(temporary) / "body.key"
            key.write_bytes(b"x" * 32)
            identity = mock.Mock(
                returncode=0,
                stdout='"NEST\\Creator","S-1-5-21-123-456-789-1001"\n',
            )
            completed = mock.Mock(returncode=0)
            with mock.patch(
                "mantleos.runtime.subprocess.run",
                side_effect=[identity, completed],
            ) as run:
                _restrict_identity_key(key, platform_name="nt")
            command = run.call_args_list[1].args[0]
            self.assertIn("/inheritance:r", command)
            self.assertIn("*S-1-5-21-123-456-789-1001:(F)", command)
            self.assertIn("*S-1-5-18:(F)", command)
            self.assertIn("*S-1-5-32-544:(F)", command)

    def test_new_identity_key_is_removed_when_permission_hardening_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            body = MantleBody(nest)
            with (
                mock.patch.object(BodyCipher, "require_available", return_value=FakeAESGCM),
                mock.patch(
                    "mantleos.runtime._restrict_identity_key",
                    side_effect=MantleError("private ACL failed"),
                ),
                self.assertRaises(MantleError),
            ):
                body.birth("Candidate", approved=True)
            self.assertFalse((nest / ".mantle" / "keys" / "body.key").exists())

    def test_constructed_body_rejects_heartbeat_and_birth_without_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            body = MantleBody(nest)
            self.assertEqual("constructed-not-born", body.status()["status"])
            self.assertTrue(body.verify()["ok"])
            with self.assertRaises(MantleError):
                body.heartbeat()
            with self.assertRaises(MantleError):
                body.birth("Candidate", approved=False)
            self.assertFalse((nest / ".mantle" / "keys" / "body.key").exists())

    def test_failed_crypto_preflight_creates_no_identity_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            body = MantleBody(nest)
            with (
                mock.patch.object(BodyCipher, "require_available", side_effect=MantleError("unavailable")),
                self.assertRaises(MantleError),
            ):
                body.birth("Candidate", approved=True)
            self.assertFalse((nest / ".mantle" / "keys" / "body.key").exists())

    def test_birth_first_heartbeat_and_no_mind_communication(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            (nest / "host.txt").write_text("native body", encoding="utf-8")

            with mock.patch.object(BodyCipher, "require_available", return_value=FakeAESGCM):
                body = MantleBody(nest)
                identity = body.birth("Candidate", approved=True)
                self.assertTrue(body.is_born)
                self.assertEqual(identity["born_at"], identity["first_heartbeat"]["completed_at"])
                self.assertTrue((nest / "COMMUNICATION.TXT").exists())
                self.assertTrue((nest / ".mantle" / "vcw" / "layer-0").is_dir())
                self.assertEqual("active", body.status()["physiology"]["state"])
                stasis = body.set_physiology("stasis", reason="operator test")
                self.assertEqual("stasis", stasis["state"])
                with self.assertRaises(MantleError):
                    body.set_physiology("unborn", reason="invalid regression")
                body.set_physiology("active", reason="resume test")

                with (nest / "COMMUNICATION.TXT").open("a", encoding="utf-8") as handle:
                    handle.write("USER> hello\n")
                beat = body.heartbeat(reason="communication-file-save")
                self.assertEqual("not-configured", beat["mind"])
                self.assertTrue(beat["communication"]["user_message_recorded"])
                transcript = (nest / "COMMUNICATION.TXT").read_text(encoding="utf-8")
                self.assertIn("APPAI> Received and recorded.", transcript)

                pending_beat = body.begin_host_heartbeat("session-1", "turn-1")
                update = body.prepare_mind_update("session-1", "turn-1")
                self.assertEqual("pending", pending_beat["status"])
                self.assertGreater(update["event_count"], 0)
                acknowledgement = body.acknowledge_mind_update("session-1", "turn-1")
                self.assertEqual("acknowledged", acknowledgement["status"])
                completed = body.complete_host_heartbeat(
                    "session-1", "turn-1", mind_status="responded"
                )
                self.assertEqual("responded", completed["mind"])
                self.assertIn("mind", completed["phases"])

                food_path = nest / "Food.txt"
                food_path.write_text(
                    "sk-or-v1-" + "a" * 40 + "\nopenrouter/free\n",
                    encoding="utf-8",
                )

                def successful_probe(food):
                    return {
                        "ok": True,
                        "requested_model": food.model,
                        "selected_model": "example/free-model",
                        "response_id": "test-response",
                        "response_chars": 14,
                        "usage": {"prompt_tokens": 8, "completion_tokens": 4},
                    }

                digestion = body.digest_food(food_path, probe=successful_probe)
                self.assertEqual("active", digestion["status"])
                receipt = food_path.read_text(encoding="utf-8")
                self.assertTrue(receipt.startswith("MantleOS Food receipt"))
                encrypted_provider = nest / ".mantle" / "providers" / "openrouter.enc"
                self.assertTrue(encrypted_provider.exists())
                self.assertNotIn(b"sk-or-v1-", encrypted_provider.read_bytes())

                with (nest / "COMMUNICATION.TXT").open("a", encoding="utf-8") as handle:
                    handle.write("USER> use the configured mind\n")
                completion = {
                    "content": "MIND response",
                    "selected_model": "example/free-model",
                    "response_id": "mind-response",
                    "usage": {"prompt_tokens": 6, "completion_tokens": 2},
                }
                with mock.patch("mantleos.runtime.openrouter_completion", return_value=completion):
                    mind_beat = body.heartbeat(reason="communication-file-save")
                self.assertEqual("responded", mind_beat["mind"])
                transcript = (nest / "COMMUNICATION.TXT").read_text(encoding="utf-8")
                self.assertIn("APPAI> MIND response", transcript)
                self.assertTrue(body.verify()["ok"])

    def test_primer_has_exact_permanent_components_and_separate_origin(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            personality_path = nest / ".mantle" / "construction" / "PERSONALITY.CANDIDATE.md"
            personality_bytes = personality_path.read_bytes()
            commandments_bytes = (nest / "mantle" / "primer" / "COMMANDMENTS.md").read_bytes()

            with mock.patch.object(BodyCipher, "require_available", return_value=FakeAESGCM):
                body = MantleBody(nest)
                body.birth("Two components", approved=True)
                cipher = body._cipher()
                primer = _load_sealed_json(body.paths.primer, cipher, "primer", {})
                self.assertEqual({"commandments", "personality"}, set(primer))
                self.assertEqual(commandments_bytes, primer["commandments"].encode("utf-8"))
                self.assertEqual(personality_bytes, primer["personality"].encode("utf-8"))
                self.assertNotIn("organism_id", primer)
                self.assertNotIn("name", primer)
                self.assertNotIn("personality_evidence", primer)
                self.assertNotIn("sealed_at", primer)

                origin = _load_sealed_json(
                    body.paths.personality_origin,
                    cipher,
                    "personality-origin",
                    {},
                )
                self.assertEqual("mantle.personality-origin.v2", origin["schema"])
                self.assertEqual(sha256_bytes(personality_bytes), origin["personality_sha256"])
                self.assertEqual(sha256_bytes(commandments_bytes), origin["commandments_sha256"])
                self.assertEqual({"source": "test"}, origin["evidence"])
                self.assertFalse(personality_path.exists())
                self.assertFalse(body.paths.personality_evidence.exists())

                sealed_primer = body.paths.primer.read_bytes()
                body.heartbeat(reason="permanence-test")
                self.assertEqual(sealed_primer, body.paths.primer.read_bytes())
                self.assertEqual("verified", body.verify()["primer"]["origin"])

                context = body.primer_context(
                    [{"logical_layer": "heart", "kind": "test", "data": {"value": 1}}]
                )
                commandments_at = context.index(primer["commandments"])
                personality_at = context.index(primer["personality"])
                continuity_at = context.index("<BODY_CONTINUITY>")
                self.assertLess(commandments_at, personality_at)
                self.assertLess(personality_at, continuity_at)

                _save_sealed_json(
                    body.paths.primer,
                    cipher,
                    "primer",
                    {**primer, "personality": primer["personality"] + "changed"},
                )
                with self.assertRaisesRegex(MantleError, "no longer matches its origin"):
                    body.verify()

    def test_legacy_primer_is_read_without_mutating_born_self(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            with mock.patch.object(BodyCipher, "require_available", return_value=FakeAESGCM):
                body = MantleBody(nest)
                body.birth("Legacy reader", approved=True)
                cipher = body._cipher()
                primer = _load_sealed_json(body.paths.primer, cipher, "primer", {})
                legacy = {
                    "schema": "mantle.primer.v2",
                    "organism_id": "legacy-id",
                    **primer,
                    "personality_evidence": {"source": "legacy"},
                    "sealed_at": "legacy-time",
                }
                _save_sealed_json(body.paths.primer, cipher, "primer", legacy)
                body.paths.personality_origin.unlink()
                sealed_legacy = body.paths.primer.read_bytes()

                context = body.primer_context([])
                self.assertIn(primer["commandments"], context)
                self.assertIn(primer["personality"], context)
                self.assertEqual("legacy-unavailable", body.verify()["primer"]["origin"])
                self.assertEqual(sealed_legacy, body.paths.primer.read_bytes())

    def test_interrupted_legacy_prebirth_primer_is_canonicalized_on_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            with mock.patch.object(BodyCipher, "require_available", return_value=FakeAESGCM):
                body = MantleBody(nest)
                with (
                    mock.patch.object(body, "heartbeat", side_effect=MantleError("interrupted")),
                    self.assertRaisesRegex(MantleError, "interrupted"),
                ):
                    body.birth("Resume", approved=True)

                cipher = body._cipher()
                primer = _load_sealed_json(body.paths.primer, cipher, "primer", {})
                _save_sealed_json(
                    body.paths.primer,
                    cipher,
                    "primer",
                    {"schema": "legacy", **primer, "sealed_at": "before-resume"},
                )
                body.birth("Resume", approved=True)
                resumed = _load_sealed_json(body.paths.primer, body._cipher(), "primer", {})
                self.assertEqual({"commandments", "personality"}, set(resumed))

    def test_resident_watch_recovers_starts_and_wakes_on_committed_message(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            with mock.patch.object(BodyCipher, "require_available", return_value=FakeAESGCM):
                body = MantleBody(nest)
                body.birth("Disposable resident", approved=True)
                reasons = []
                original_heartbeat = body.heartbeat

                def heartbeat(*, reason, **kwargs):
                    reasons.append(reason)
                    return original_heartbeat(reason=reason, **kwargs)

                slept = False

                def commit_message(_interval):
                    nonlocal slept
                    if not slept:
                        slept = True
                        with (nest / "COMMUNICATION.TXT").open("a", encoding="utf-8") as handle:
                            handle.write("USER> resident wake test\n")

                with (
                    mock.patch.object(body, "heartbeat", side_effect=heartbeat),
                    mock.patch.object(
                        body,
                        "recover_host_heartbeats",
                        wraps=body.recover_host_heartbeats,
                    ) as recover,
                    mock.patch("mantleos.runtime.time.sleep", side_effect=commit_message),
                    mock.patch("mantleos.runtime.time.monotonic", side_effect=lambda: float(slept)),
                ):
                    body.watch(
                        interval=0.05,
                        heartbeat_interval=300,
                        stop_requested=lambda: len(reasons) >= 2,
                    )

                recover.assert_called_once_with()
                self.assertEqual(["resident-startup", "communication-file-save"], reasons)
                transcript = (nest / "COMMUNICATION.TXT").read_text(encoding="utf-8")
                self.assertIn("APPAI> Received and recorded.", transcript)

    def test_resident_watch_runs_scheduled_full_heartbeats(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            with mock.patch.object(BodyCipher, "require_available", return_value=FakeAESGCM):
                body = MantleBody(nest)
                body.birth("Disposable schedule", approved=True)
                reasons = []

                def heartbeat(*, reason, **_kwargs):
                    reasons.append(reason)
                    return {"reason": reason}

                with (
                    mock.patch.object(body, "heartbeat", side_effect=heartbeat),
                    mock.patch.object(body, "recover_host_heartbeats", return_value=[]),
                    mock.patch("mantleos.runtime.time.sleep"),
                    mock.patch("mantleos.runtime.time.monotonic", side_effect=[0.0, 2.0, 2.0]),
                ):
                    body.watch(
                        interval=0.05,
                        heartbeat_interval=1.0,
                        stop_requested=lambda: len(reasons) >= 2,
                    )

                self.assertEqual(["resident-startup", "resident-scheduled"], reasons)

    def test_changed_or_undeclared_prebirth_tissue_stops_before_key_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            personality = nest / ".mantle" / "construction" / "PERSONALITY.CANDIDATE.md"
            personality.write_text("A silently changed personality.", encoding="utf-8")
            body = MantleBody(nest)
            self.assertEqual("construction-invalid", body.status()["status"])
            with self.assertRaisesRegex(MantleError, "changed after construction"):
                body.verify()
            with self.assertRaisesRegex(MantleError, "changed after construction"):
                body.birth("Candidate", approved=True)
            self.assertFalse((nest / ".mantle" / "keys" / "body.key").exists())

        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            (nest / "mantle" / "unreviewed.py").write_text("pass\n", encoding="utf-8")
            with self.assertRaisesRegex(MantleError, "Undeclared public candidate tissue"):
                MantleBody(nest).verify()

        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            (nest / ".gitignore").write_text("/.mantle/\n", encoding="utf-8")
            with self.assertRaisesRegex(MantleError, "no longer excludes"):
                MantleBody(nest).verify()

        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            prepare_unborn_nest(nest)
            (nest / ".mantle" / "prebirth.json").write_text("not-json", encoding="utf-8")
            status = MantleBody(nest).status()
            self.assertEqual("construction-invalid", status["status"])
            self.assertFalse(status["construction_integrity"]["ok"])

    def test_canonical_json_is_stable(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))

    def test_food_parser_rejects_ambiguous_or_malformed_deliveries(self):
        with self.assertRaises(NutritionError):
            parse_openrouter_food(b"not-a-key\nopenrouter/free\n")
        with self.assertRaises(NutritionError):
            parse_openrouter_food(
                b"sk-or-v1-" + b"a" * 40 + b"\nopenrouter/free\nthird-line\n"
            )


if __name__ == "__main__":
    unittest.main()
