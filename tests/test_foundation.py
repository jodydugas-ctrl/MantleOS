"""Integration boundaries, using synthetic data and no provider calls."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from mantleos import (cartridge, tissue, compiled, continuity, engram, evolution,
                      kernel, lifecycle, organism, replication, single_media,
                      transactions, vault_auto, vault_store)
from mantleos.anchor_engine.tools.anchor_runtime import render_hello_world


class ProgramTests(unittest.TestCase):
    def test_unknown_profile_and_version(self):
        with self.assertRaises(ValueError):
            tissue.program("x", "invented/1", "not executable")
        c = tissue.program("x", "EMIT_TEXT/0.2", render_hello_world())
        c["schema"] = "mantle.program/99"
        with self.assertRaises(ValueError):
            tissue.validate_program(c)

    def test_missing_and_cyclic_dependency(self):
        a = tissue.program("a", "EMIT_TEXT/0.2", render_hello_world(), dependencies=["b"])
        with self.assertRaises(ValueError):
            tissue.tissue("t", [a])
        b = tissue.program("b", "EMIT_TEXT/0.2", render_hello_world(), dependencies=["a"])
        with self.assertRaises(ValueError):
            tissue.tissue("t", [a, b])

    def test_nonportable_and_case_colliding_names(self):
        for name in ("CON", "a.", "../outside"):
            with self.assertRaises(ValueError):
                tissue.program(name, "EMIT_TEXT/0.2", render_hello_world())
        with self.assertRaises(ValueError):
            tissue.tissue("t", [tissue.program(n, "EMIT_TEXT/0.2", render_hello_world()) for n in ("a", "A")])

    def test_content_tamper_and_capability_expansion(self):
        c = tissue.program("a", "EMIT_TEXT/0.2", render_hello_world())
        c["payload"] = render_hello_world(text="tampered")
        with self.assertRaises(ValueError):
            tissue.validate_program(c)
        with self.assertRaises(ValueError):
            tissue.program("a", "EMIT_TEXT/0.2", render_hello_world(), capabilities=["host.execute"])

    def test_systems_have_no_fixed_count(self):
        from mantleos.systems import validate_systems_contract
        value = {"schema": "cell.systems/2", "systems": [{"id": "one", "interfaces": []}]}
        self.assertEqual(validate_systems_contract(value), value)

    def test_cloud_path_traversal_refused(self):
        with tempfile.TemporaryDirectory() as root:
            store = continuity.LocalCASStore(root)
            for name in ("../HEAD.json", "C:/secret", "/etc/passwd"):
                with self.assertRaises(ValueError):
                    store.get_blob(name)

    def test_atomic_create_does_not_replace(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "value"
            transactions.atomic_bytes(path, b"first", replace=False)
            with self.assertRaises(FileExistsError):
                transactions.atomic_bytes(path, b"second", replace=False)
            self.assertEqual(path.read_bytes(), b"first")

    def test_scan_never_executes_specimen(self):
        # A standalone scan has no Body; cwd must not become a protected Body.
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            root = Path(root)
            source = root / "source"; source.mkdir()
            (source / "danger.py").write_text("raise RuntimeError('SPECIMEN_EXECUTED')\n", encoding="utf-8")
            before = (source / "danger.py").read_bytes()
            result = kernel.scan("scan.inspect", {"source": str(source), "workspace": str(root / "scan")}, permit=True)
            self.assertEqual(result["stage"], "VERIFIED")
            self.assertEqual(result["observation"]["result"]["evidence"], "STATIC_ANALYSIS_NOT_BEHAVIORAL_PROOF")
            self.assertEqual((source / "danger.py").read_bytes(), before)


class BodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.base = Path(cls.fixture.name) / "base"
        organism.create(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.body = self.root / "body"
        shutil.copytree(self.base, self.body)

    def edit(self, text="remember", request="edit"):
        return lifecycle.run(self.body, "notepad", {"op": "INSERT", "text": text}, commit=True, request_id=request)

    def test_body_survives_missing_disabled_and_failed_mind(self):
        self.assertEqual(organism.consult(self.body)["status"], "MIND_ABSENT")
        self.assertEqual(organism.consult(self.body, None)["status"], "MIND_ABSENT")
        def fail(_):
            raise ConnectionError("offline")
        self.assertEqual(organism.consult(self.body, fail)["status"], "MIND_FAILED")
        self.assertEqual(self.edit()["result"]["state"]["text"], "remember")

    def test_request_replay_conflict_and_stale_head(self):
        self.edit()
        head = engram.head(self.body / "ENGRAM.jsonl")
        self.assertTrue(self.edit()["replayed"])
        self.assertEqual(engram.head(self.body / "ENGRAM.jsonl"), head)
        with self.assertRaisesRegex(ValueError, "replay conflict"):
            self.edit("different")
        with self.assertRaisesRegex(ValueError, "Stale"):
            lifecycle.run(self.body, "notepad", {"op": "INSERT", "text": "bad"}, commit=True,
                          request_id="new", expected_head=engram.ZERO)

    def test_tissue_admission_rollback_preserves_identity_and_history(self):
        self.edit()
        primer = (self.body / "PRIMER/PERSONA.md").read_bytes()
        proposal = evolution.propose(self.body, organism.notebook_tissue("Improved"))
        before = evolution.revision(self.body)
        self.assertFalse(evolution.validate(self.body, proposal)["authorized"])
        with self.assertRaises(PermissionError):
            evolution.apply(self.body, proposal, approval="not-approved")
        self.assertEqual(evolution.revision(self.body), before)
        evolution.apply(self.body, proposal, approval=proposal["sha256"])
        self.assertEqual(lifecycle.run(self.body, "greeting")["result"]["stdout"], "Improved")
        self.assertEqual(compiled.read_json(self.body / "PROGRAM-STATE.json")["notepad"]["text"], "remember")
        prefix = (self.body / "ENGRAM.jsonl").read_bytes()
        current = evolution.revision(self.body)
        evolution.rollback(self.body, expected_revision=current, approval=current)
        self.assertEqual(lifecycle.run(self.body, "greeting")["result"]["stdout"], "Ready to remember.")
        self.assertTrue((self.body / "ENGRAM.jsonl").read_bytes().startswith(prefix))
        self.assertEqual((self.body / "PRIMER/PERSONA.md").read_bytes(), primer)

    def test_stale_and_tampered_proposals_rejected(self):
        p = evolution.propose(self.body, organism.notebook_tissue("New"))
        tampered = copy.deepcopy(p); tampered["candidate"]["programs"][0]["payload"] += "bad"
        with self.assertRaises(ValueError):
            evolution.apply(self.body, tampered, approval=p["sha256"])
        self.edit()
        before = evolution.revision(self.body)
        with self.assertRaisesRegex(ValueError, "Stale"):
            evolution.apply(self.body, p, approval=p["sha256"])
        self.assertEqual(evolution.revision(self.body), before)

    def test_tissue_manifest_cannot_disagree_with_program(self):
        tissue = organism.notebook_tissue("metadata-only-change")
        transactions.write_json(self.body / "TISSUE.json", tissue)
        cartridge.write_manifest(self.body)
        with self.assertRaisesRegex(ValueError, "payload differs"):
            compiled.load(self.body)

    def test_recover_interruptions_at_both_publication_steps(self):
        for point in ("after-backup", "after-publish"):
            with self.subTest(point=point):
                before = compiled.load(self.body)["sha256"]
                stage = transactions.stage_body(self.body)
                engram.append(stage / "ENGRAM.jsonl", "test", "synthetic", {"point": point})
                lifecycle.finalize(stage)
                with transactions.body_lock(self.body), self.assertRaises(RuntimeError):
                    transactions.publish_body(stage, self.body, interrupt=point)
                with self.assertRaisesRegex(ValueError, "Interrupted"):
                    compiled.load(self.body)
                transactions.recover(self.body)
                self.assertEqual(compiled.load(self.body)["sha256"], before)

    def test_cartridge_and_chroma_round_trip_and_corruption(self):
        self.edit()
        for name, suffix in (("cartridge", ".vcw"), ("chroma", ".png")):
            with self.subTest(format=name):
                snapshot = self.root / (name + suffix)
                lifecycle.save(self.body, snapshot, format=name)
                restored = self.root / (name + "-body")
                lifecycle.restore(snapshot, restored)
                self.assertEqual(compiled.load(restored)["sha256"], compiled.load(self.body)["sha256"])
                if name == "chroma":
                    data = bytearray(snapshot.read_bytes()); data[len(data)//2] ^= 1
                    snapshot.write_bytes(data)
                    with self.assertRaises((ValueError, OSError)):
                        lifecycle.restore(snapshot, self.root / "corrupt")

    def test_unsafe_cartridge_rejected(self):
        path = self.root / "unsafe.vcw"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../outside", "untrusted")
        with self.assertRaises(ValueError):
            cartridge.unpack(path, self.root / "unpacked")
        self.assertFalse((self.root / "outside").exists())

    def test_unknown_carrier_declaration_version(self):
        spec = compiled.read_json(self.body / "CARTRIDGE.json")
        spec["schema"] = "mantle.cartridge/99"
        transactions.write_json(self.body / "CARTRIDGE.json", spec)
        cartridge.write_manifest(self.body)
        with self.assertRaisesRegex(ValueError, "Unsupported cartridge declaration"):
            cartridge.verify(self.body)

    def test_duplicate_manifest_paths_refused(self):
        manifest = compiled.read_json(self.body / "MANIFEST.json")
        manifest["files"].append(manifest["files"][0])
        transactions.write_json(self.body / "MANIFEST.json", manifest)
        with self.assertRaisesRegex(ValueError, "Duplicate manifest"):
            cartridge.verify(self.body)

    def test_cloud_restore_and_divergent_history(self):
        store = continuity.LocalCASStore(self.root / "cloud")
        self.edit()
        replication.sync(self.body, store)
        replication.restore(self.base, store, self.root / "restored")
        self.assertEqual(engram.read(self.root / "restored/ENGRAM.jsonl"), engram.read(self.body / "ENGRAM.jsonl"))
        self.assertEqual(compiled.read_json(self.root / "restored/PROGRAM-STATE.json")["notepad"]["text"], "remember")
        other = self.root / "diverged"; shutil.copytree(self.base, other)
        lifecycle.run(other, "notepad", {"op": "INSERT", "text": "branch"}, commit=True, request_id="branch")
        with self.assertRaisesRegex(ValueError, "Divergent"):
            replication.restore(other, store, self.root / "forbidden")
        self.assertFalse((self.root / "forbidden").exists())

    def test_cloud_rejects_tissue_replay_without_matching_snapshot(self):
        p = evolution.propose(self.body, organism.notebook_tissue("changed"))
        evolution.apply(self.body, p, approval=p["sha256"])
        store = continuity.LocalCASStore(self.root / "cloud")
        replication.sync(self.body, store)
        with self.assertRaisesRegex(ValueError, "matching Body snapshot"):
            replication.restore(self.base, store, self.root / "bad")

    def test_bound_single_file_handoff_and_stale_writer(self):
        identity = vault_auto.mounted_identity(self.body)
        archive = self.body / "ARCHIVE.rvcar"
        head = vault_store.initialize(archive, identity)
        transactions.write_json(self.body / "VAULT-REF.json", {"schema": "raven.vault-binding/1",
            "identity": identity, "file_name": "ARCHIVE.rvcar", "location": "embedded", "root_sha256": head["sha256"]})
        lifecycle.finalize(self.body)
        carrier = self.root / "single.vcw"
        lifecycle.save(self.body, carrier)
        writer_a, writer_b = self.root / "a", self.root / "b"
        cartridge.unpack(carrier, writer_a); cartridge.unpack(carrier, writer_b)
        single_media.bind(writer_a, carrier); single_media.bind(writer_b, carrier)
        lifecycle.admit(writer_a, "note", {"text": "first"}, expected_head=engram.ZERO)
        a = vault_auto.sync_committed(writer_a)
        self.assertTrue(a["publication"]["handoff_updated"])
        lifecycle.admit(writer_b, "note", {"text": "second"}, expected_head=engram.ZERO)
        b = vault_auto.sync_committed(writer_b)
        self.assertEqual(b["status"], "LOCAL_TURN_COMMITTED_VAULT_NOT_SYNCED")
        self.assertIn("STALENESS", b["error"])
        restored = self.root / "single-restored"
        cartridge.unpack(carrier, restored)
        self.assertEqual(engram.read(restored / "ENGRAM.jsonl")[-1]["body"]["text"], "first")


if __name__ == "__main__":
    unittest.main()
