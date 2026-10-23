from __future__ import annotations

import json
import hashlib
import time
from pathlib import Path

from .body import Body
from .git_repo import GitRepo
from .mind import ProposalAdmission
from .security import redact


class CrashInjected(RuntimeError):
    pass


class CheckpointUnavailable(RuntimeError):
    pass


class Heart:
    def __init__(self, root: Path, mind=None, checkpoint_guard=None):
        self.root = Path(root)
        self.mind = mind
        self.checkpoint_guard = checkpoint_guard or (lambda: True)

    def beat(self, crash_point: str | None = None, significant: bool = False, beat_id: str | None = None) -> dict:
        repo = GitRepo(self.root)
        parent = repo.head()
        requested_id = beat_id or f"beat-{int(time.time() * 1000000)}"
        existing_receipt = self.root / "receipts" / f"{requested_id}.json"
        if beat_id and existing_receipt.is_file():
            with existing_receipt.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
            if existing.get("status") == "verified":
                return existing
        body = Body.reconstruct(self.root)
        before = body.stack.fingerprint()
        before_layers = body.stack.layer_hashes()
        integrity_before = body.stack.verify()
        if integrity_before:
            raise ValueError("pre-beat integrity failure: " + "; ".join(integrity_before))
        if crash_point == "before_mutation":
            raise CrashInjected("before mutation")

        event = {"event_type": "heartbeat", "beat_id": requested_id,
                 "parent_head": parent}
        body.senses.inhale(event)
        mind_invoked = False
        cognitive = None
        proposal_hash = None
        if self.mind is not None and significant:
            mind_invoked = True
            proposal = redact(self.mind.propose(body.nervous.assemble()),
                              [getattr(self.mind, "_api_key", None)])
            proposal_hash = hashlib.sha256(json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            cognitive = {"provider_id": self.mind.provider_id, "proposal": proposal,
                         "proposal_hash": proposal_hash,
                         "admission": ProposalAdmission(body).admit(proposal)}
        if crash_point == "after_mutation":
            raise CrashInjected("after local mutation")
        problems = body.stack.verify()
        if problems:
            body.immune.event("integrity", {"problems": problems})
            raise ValueError("candidate failed verification: " + "; ".join(problems))
        integrity_after = problems
        if crash_point == "after_verification":
            raise CrashInjected("after verification")

        after = body.stack.fingerprint()
        after_layers = body.stack.layer_hashes()
        changed = [band for band in before_layers if before_layers[band] != after_layers[band]]
        receipt = {"schema_version": 1, "beat_id": event["beat_id"],
                   "created_at": time.time(), "parent_head": parent,
                   "before_stack": before, "after_stack": after,
                   "before_layers": before_layers, "after_layers": after_layers,
                   "changed_layers": changed, "organs": ["heart", "senses", "memory", "nervous", "immune", "limbs"],
                   "mind_invoked": mind_invoked, "cognitive": cognitive,
                   "proposal_hash": proposal_hash, "integrity_before": integrity_before,
                   "integrity_after": integrity_after,
                   "phases": ["load", "pre_verify", "circulate", "mutate", "post_verify", "receipt", "checkpoint", "stop"],
                   "status": "verified"}
        receipt_path = self.root / "receipts" / f"{event['beat_id']}.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if crash_point == "before_commit":
            raise CrashInjected("before commit")
        if not self.checkpoint_guard():
            raise CheckpointUnavailable("repository checkpoint is unavailable")
        paths = ["STACK.json", *[f"vcw/{body.stack.manifest()['bands'][band]['path'].split('/', 1)[1]}" for band in changed],
                 str(receipt_path.relative_to(self.root))]
        child = repo.commit(paths, f"heartbeat: {event['beat_id']}", expected_parent=parent)
        if crash_point == "after_commit":
            raise CrashInjected("after commit")
        return receipt
