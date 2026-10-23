"""Offline, synthetic organism loop. All output is disposable and caller-owned."""
from pathlib import Path
import shutil

from . import compiled, continuity, engram, evolution, lifecycle, organism, replication, vault_auto, vault_store


def run(output):
    root = Path(output).resolve()
    if root.exists():
        raise ValueError("Demo output already exists; choose a new directory")
    root.mkdir(parents=True)
    body = root / "notebook"
    organism.create(body)
    base = root / "base"
    shutil.copytree(body, base)
    checks = {}

    def check(name, success):
        if not success:
            raise AssertionError(name)
        checks[name] = "PASS"

    check("mind_absent", organism.consult(body)["status"] == "MIND_ABSENT")
    check("mind_disabled", organism.consult(body, None)["status"] == "MIND_ABSENT")

    def failing_mind(context):
        raise ConnectionError("synthetic provider unavailable")

    check("mind_failure", organism.consult(body, failing_mind)["status"] == "MIND_FAILED")
    receipt = lifecycle.run(body, "notepad", {"op": "INSERT", "text": "Observe, remember, improve."},
                            commit=True, request_id="demo-edit")
    check("body_edits_without_mind", receipt["result"]["state"]["text"] == "Observe, remember, improve.")
    replay = lifecycle.run(body, "notepad", {"op": "INSERT", "text": "Observe, remember, improve."},
                           commit=True, request_id="demo-edit")
    check("idempotent_request", replay.get("replayed") is True)
    check("recall", bool(compiled.query(body, "Observe")))
    store = continuity.LocalCASStore(root / "simulated-cloud")
    replication.sync(body, store)
    replica = root / "cloud-restored"
    replication.restore(base, store, replica)
    check("cloud_memory_recovery", engram.read(replica / "ENGRAM.jsonl") == engram.read(body / "ENGRAM.jsonl"))
    check("cloud_program_state_recovery", (replica / "PROGRAM-STATE.json").read_bytes() == (body / "PROGRAM-STATE.json").read_bytes())

    archive = root / "cold.rvcar"
    anchor = vault_store.initialize(archive, vault_auto.mounted_identity(body))
    vault_store.commit(archive, [("notes/observation.txt", b"An older synthetic observation.",
                                 "text/plain", "note", ["demo"], "Cold reference")], expected=anchor["sha256"])
    check("cold_retrieval", vault_store.retrieve(archive, "notes/observation.txt") == b"An older synthetic observation.")

    fake = lambda context: organism.notebook_tissue("Ready to remember and reconsider.")
    candidate = organism.consult(body, fake)
    check("mind_proposes_only", candidate["authorized"] is False)
    proposal = evolution.propose(body, candidate["candidate"])
    check("validated_not_authorized", evolution.validate(body, proposal)["authorized"] is False)
    before = evolution.revision(body)
    try:
        evolution.apply(body, proposal, approval=None)
    except PermissionError:
        check("unauthorized_change_rejected", evolution.revision(body) == before)
    else:
        raise AssertionError("Unauthorized evolution succeeded")
    evolution.apply(body, proposal, approval=proposal["sha256"])
    check("admitted_change_works", lifecycle.run(body, "greeting")["result"]["stdout"] == "Ready to remember and reconsider.")
    history = (body / "ENGRAM.jsonl").read_bytes()
    current = evolution.revision(body)
    evolution.rollback(body, expected_revision=current, approval=current)
    check("rollback_keeps_history", (body / "ENGRAM.jsonl").read_bytes().startswith(history))
    check("rollback_restores_tissue", lifecycle.run(body, "greeting")["result"]["stdout"] == "Ready to remember.")
    for name, suffix in (("cartridge", ".vcw"), ("chroma", ".png")):
        snapshot = root / ("notebook" + suffix)
        saved = lifecycle.save(body, snapshot, format=name)
        restored = root / (name + "-restored")
        lifecycle.restore(snapshot, restored)
        check(name + "_round_trip", saved["restored_verify"] == "PASS" and
              compiled.load(restored)["sha256"] == compiled.load(body)["sha256"])
    report = {"result": "PASS", "checks": checks, "output": str(root), "model_calls": 0,
              "network_calls": 0, "identity": "synthetic", "cloud": "local simulation"}
    from .transactions import write_json
    write_json(root / "report.json", report)
    return report
