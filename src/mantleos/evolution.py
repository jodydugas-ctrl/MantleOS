"""Content-bound tissue proposals; operator admission and append-only rollback.

Trusted Python callers own operator authority. Hashes bind review to bytes; they
are not signatures and this module is not a sandbox for hostile Python callers.
"""
from pathlib import Path
import shutil
import tempfile

from . import tissue as composition, compiled, engram, lifecycle
from . import json_contract as contract
from .transactions import body_lock, ensure_clean, journal_path, publish_body, stage_body, write_json


def revision(body):
    return compiled.load(body)["sha256"]


def _compatible(old, new):
    old = composition.validate_tissue(old)
    new = composition.validate_tissue(new)
    contract.require(old["id"] == new["id"], "Tissue identity cannot change")
    before = {c["id"]: c for c in old["programs"]}
    after = {c["id"]: c for c in new["programs"]}
    contract.require(before.keys() == after.keys(), "Program membership change requires a new construction")
    for name in before:
        for key in ("profile", "dependencies", "capabilities"):
            contract.require(before[name][key] == after[name][key], "Proposal cannot expand privileges or change contracts")


def propose(body, candidate):
    body = Path(body)
    with body_lock(body):
        base = revision(body)
        candidate = composition.validate_tissue(candidate)
        _compatible(compiled.read_json(body / "TISSUE.json"), candidate)
        proposal = {"schema": "mantle.tissue-proposal/1", "base_revision": base,
                    "candidate": candidate}
        proposal["sha256"] = contract.digest(proposal)
        return proposal


def validate(body, proposal):
    contract.shape(proposal, {"schema", "base_revision", "candidate", "sha256"})
    contract.require(proposal["schema"] == "mantle.tissue-proposal/1", "Unsupported proposal version")
    contract.require(proposal["sha256"] == contract.digest({k: v for k, v in proposal.items() if k != "sha256"}),
                     "Proposal digest mismatch")
    contract.require(revision(body) == proposal["base_revision"], "Stale tissue proposal")
    _compatible(compiled.read_json(Path(body) / "TISSUE.json"), proposal["candidate"])
    return {"result": "VALIDATED", "proposal_sha256": proposal["sha256"],
            "scope": "qualified-profiles-and-unchanged-capability-contracts", "authorized": False}


def _replace(stage, tissue):
    with tempfile.TemporaryDirectory(prefix="mantle-tissue-") as work:
        catalog = composition.write_programs(work, tissue)
        # State for unchanged programs survives a bounded tissue update.
        old = compiled.read_json(stage / "TISSUE.json")
        states = compiled.read_json(stage / "PROGRAM-STATE.json") if (stage / "PROGRAM-STATE.json").exists() else {}
        old_programs = {c["id"]: c["sha256"] for c in old["programs"]}
        kept = {c["id"]: states[c["id"]] for c in tissue["programs"]
                if c["id"] in states and old_programs.get(c["id"]) == c["sha256"]}
        lifecycle.install_programs(stage, catalog)
        if kept:
            write_json(stage / "PROGRAM-STATE.json", kept)
    write_json(stage / "TISSUE.json", tissue)
    from .cartridge import write_manifest
    write_manifest(stage)


def apply(body, proposal, *, approval):
    """approval is the exact proposal digest explicitly selected by the operator."""
    body = Path(body).resolve()
    with body_lock(body):
        validate(body, proposal)
        if approval != proposal["sha256"]:
            raise PermissionError("Operator approval must match the exact proposal digest")
        lifecycle._operational(body)
        stage = stage_body(body)
        try:
            old = compiled.read_json(stage / "TISSUE.json")
            _replace(stage, proposal["candidate"])
            engram.append(stage / "ENGRAM.jsonl", "tissue-admission", "operator",
                          {"proposal_sha256": approval, "previous": old,
                           "admitted_sha256": proposal["candidate"]["sha256"]})
            lifecycle.finalize(stage)
            return {**publish_body(stage, body), "proposal_sha256": approval,
                    "revision": revision(body)}
        finally:
            if stage.exists() and not journal_path(body).exists():
                shutil.rmtree(stage)


def rollback(body, *, expected_revision, approval):
    """Restore the latest admitted tissue, retaining all intervening memory."""
    body = Path(body).resolve()
    with body_lock(body):
        ensure_clean(body)
        contract.require(revision(body) == expected_revision, "Stale rollback revision")
        if approval != expected_revision:
            raise PermissionError("Rollback requires explicit current-revision approval")
        lifecycle._operational(body)
        records = engram.read(body / "ENGRAM.jsonl")
        admissions = []
        for record in records:
            if record["type"] == "tissue-admission":
                admissions.append(record)
            elif record["type"] == "tissue-rollback" and admissions:
                contract.require(admissions[-1]["id"] == record["body"]["admission"], "Invalid rollback history")
                admissions.pop()
        contract.require(bool(admissions), "No admitted tissue to roll back")
        latest = admissions[-1]
        current = compiled.read_json(body / "TISSUE.json")
        contract.require(current["sha256"] == latest["body"]["admitted_sha256"], "Tissue drift blocks rollback")
        stage = stage_body(body)
        try:
            _replace(stage, latest["body"]["previous"])
            engram.append(stage / "ENGRAM.jsonl", "tissue-rollback", "operator",
                          {"admission": latest["id"], "previous_revision": expected_revision})
            lifecycle.finalize(stage)
            return {**publish_body(stage, body), "revision": revision(body)}
        finally:
            if stage.exists() and not journal_path(body).exists():
                shutil.rmtree(stage)
