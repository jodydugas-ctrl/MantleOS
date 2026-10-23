"""Local reference for cloud continuity: verified segments and cold Body restore."""
from pathlib import Path
import os
import shutil
import uuid

from . import cartridge, compiled, continuity, engram, lifecycle, vault_auto
from .transactions import atomic_bytes, body_lock


def sync(body, store):
    body = Path(body)
    with body_lock(body):
        compiled.load(body)
        identity = vault_auto.mounted_identity(body)
        head = store.load_head()
        if head is None:
            store.cas_head(None, continuity.make_head(identity))
            head = store.load_head()
        continuity.verify_head(head)
        continuity.require(head["identity"] == identity, "Continuity identity mismatch")
        records = engram.read(body / "ENGRAM.jsonl")
        remote = continuity.recover(head, {m["blob_id"]: store.get_blob(m["blob_id"]) for m in head["segments"]})
        continuity.require(remote == records[:len(remote)], "Divergent or newer remote history; branch required")
        for record in records[len(remote):]:
            head = continuity.commit(store, record)
        continuity.require(store.load_head() == head, "HEAD readback mismatch")
        return {"result": "VERIFIED", "records": head["seq"], "head": head["sha256"],
                "transport": "local-reference", "cloud_uploaded": False}


def restore(base, store, output):
    """Recover into a new Body; never merge divergent history or mutate the base.

The protocol carries memory, not executable tissue. A base with different admitted
tissue requires its matching full snapshot before continuity restoration.
"""
    base = Path(base).resolve()
    output = lifecycle._destination(output, base)
    with body_lock(base), body_lock(output):
        compiled.load(base)
        head = store.load_head()
        continuity.verify_head(head)
        continuity.require(head["identity"] == vault_auto.mounted_identity(base), "Continuity identity mismatch")
        records = continuity.recover(head, {m["blob_id"]: store.get_blob(m["blob_id"]) for m in head["segments"]})
        current = engram.read(base / "ENGRAM.jsonl")
        continuity.require(current == records[:len(current)], "Divergent or newer base history; branch required")
        # Replaying tissue changes requires a full verified executable snapshot.
        continuity.require(not any(r["type"] in {"tissue-admission", "tissue-rollback", "rebuild", "identity-revision"}
                                   for r in records[len(current):]), "Executable changes require a matching Body snapshot")
        stage = output.parent / ("." + output.name + ".stage-" + uuid.uuid4().hex)
        try:
            shutil.copytree(base, stage, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            # Restore deterministic notebook state from committed execution receipts.
            states = compiled.read_json(stage / "PROGRAM-STATE.json") if (stage / "PROGRAM-STATE.json").exists() else {}
            for record in records[len(current):]:
                if record["type"] == "compiled-run":
                    receipt = record["body"]["receipt"]
                    if receipt["profile"] == "NOTEPAD_LLM/1.3" and receipt["result"]["effect_claim"] == "NONE":
                        states[receipt["program"]] = receipt["result"]["state"]
            if states:
                from .transactions import write_json
                write_json(stage / "PROGRAM-STATE.json", states)
            atomic_bytes(stage / "ENGRAM.jsonl", "".join(engram.canonical(r) + "\n" for r in records).encode())
            lifecycle.finalize(stage)
            cartridge.verify(stage)
            os.rename(stage, output)
            return {"result": "RESTORED", "output": str(output), "records": len(records), "cloud_uploaded": False}
        finally:
            if stage.exists():
                shutil.rmtree(stage)
