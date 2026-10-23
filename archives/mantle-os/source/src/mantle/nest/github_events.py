"""GitHub event normalization for the Senses boundary.

Every accepted signal is normalized into a bounded, redacted record carrying:
repository ID and expected installation ID, a delivery GUID / run ID as the
idempotency key, event + action type, actor ID and type, commit/ref coordinates,
a redacted bounded payload summary, a hash of the original verified payload,
and receipt + source timestamps.

Rules:
- verify webhook HMAC before normalization;
- reject wrong repository or installation IDs;
- deduplicate delivery GUIDs;
- assume events can be late or out of order;
- treat comments, issue/PR text, branch names, filenames, workflow output, and
  provider output as UNTRUSTED data; never execute text that resembles a command;
- route through Senses.inhale(...) exactly once; verification/parsing failures
  route through Immune.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass, field
from typing import Dict, Optional

from .manifest import sha256_bytes, canonical_json

_WEBHOOK_SIGNATURE = "sha256="
_COMMAND_LIKE = re.compile(
    r"(?i)\b(execute|run|python|sudo|curl|wget|bash|sh|rm|eval|import|subprocess|os\.system)\b"
)


class EventRejected(Exception):
    pass


@dataclass(frozen=True)
class NormalizedGithubEvent:
    delivery_guid: str
    event: str
    action: str
    repo_id: int
    installation_id: str
    actor_id: str
    actor_type: str
    ref: str
    commit: str
    payload_summary_redacted: str
    payload_hash: str
    received_at: str
    source_timestamp: str

    def to_sense_entry(self) -> Dict[str, object]:
        """Shape for Mantle Senses intake (one entry, opcode preserved)."""
        return {
            "opcode": "GITHUB_EVENT",
            "content": {
                "delivery_guid": self.delivery_guid,
                "event": self.event,
                "action": self.action,
                "repo_id": self.repo_id,
                "installation_id": self.installation_id,
                "actor_id": self.actor_id,
                "actor_type": self.actor_type,
                "ref": _redact_ref(self.ref),
                "commit": self.commit,
                "payload": self.payload_summary_redacted,
                "payload_hash": self.payload_hash,
                "received_at": self.received_at,
                "source_timestamp": self.source_timestamp,
            },
            "provenance": "github-webhook",
            "trust": "OTHER",
        }


def _redact_ref(ref: str) -> str:
    # refs may carry leading "refs/heads/"; strip to reduce noise, keep identity
    return re.sub(r"^refs/(heads|tags)/", "", ref)


def verify_hmac(payload: bytes, signature: str, secret: str) -> bool:
    """Constant-time webhook HMAC verification."""
    if not signature.startswith(_WEBHOOK_SIGNATURE):
        return False
    provided = signature[len(_WEBHOOK_SIGNATURE):]
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)


def _bounded_summary(obj: object, cap: int = 400) -> str:
    import json as _json

    try:
        text = _json.dumps(obj, sort_keys=True, default=str)
    except TypeError:
        text = repr(obj)
    if len(text) > cap:
        text = text[:cap] + "..."
    return text


def _redact_command_like(text: str) -> str:
    # Harden untrusted text before it enters Senses: leave no command-shaped text
    # that could be mistaken for an instruction to execute.
    return _COMMAND_LIKE.sub("[redacted:command-like]", text)


def normalize_webhook(
    *,
    payload_bytes: bytes,
    signature: str,
    secret: str,
    delivery_guid: str,
    repo_id: int,
    installation_id: str,
    event: str,
    received_at: str,
) -> NormalizedGithubEvent:
    """Verify + normalize a webhook delivery. Raises EventRejected on any rule."""
    if not verify_hmac(payload_bytes, signature or "", secret):
        raise EventRejected("webhook HMAC verification failed")
    import json as _json

    try:
        payload = _json.loads(payload_bytes.decode("utf-8"))
    except ValueError as e:
        raise EventRejected("webhook payload not valid JSON: %s" % e)

    payload_repo_id = ((payload.get("repository") or {}).get("id")) or 0
    if payload_repo_id and payload_repo_id != repo_id:
        raise EventRejected(
            "webhook repository id %s does not match expected %s"
            % (payload_repo_id, repo_id)
        )
    inst = payload.get("installation") or {}
    payload_inst = inst.get("id")
    if payload_inst is not None and str(payload_inst) != str(installation_id):
        raise EventRejected(
            "webhook installation id %s does not match expected %s"
            % (payload_inst, installation_id)
        )

    sender = payload.get("sender") or {}
    action = payload.get("action", "")
    ref = payload.get("ref", "")
    head = payload.get("head", "")
    if head == "":
        head = ((payload.get("check_run") or {}).get("head_sha")) or ""
    redacted_summary = _redact_command_like(
        _bounded_summary(_pick_summary(payload))
    )
    return NormalizedGithubEvent(
        delivery_guid=delivery_guid,
        event=event,
        action=str(action),
        repo_id=int(repo_id),
        installation_id=str(installation_id),
        actor_id=str(sender.get("id", "")),
        actor_type=str(sender.get("type", "")),
        ref=str(ref),
        commit=str(head),
        payload_summary_redacted=redacted_summary,
        payload_hash=sha256_bytes(payload_bytes),
        received_at=received_at,
        source_timestamp=str(payload.get("timestamp", "")),
    )


def _pick_summary(payload: Dict[str, object]) -> object:
    """A bounded, non-secret slice of the payload for the sense entry."""
    keys = ("action", "ref", "head", "before", "after", "workflow_run", "check_run",
            "number", "title", "state", "conclusion")
    out: Dict[str, object] = {}
    for k in keys:
        if k in payload:
            v = payload[k]
            if isinstance(v, str) and len(v) > 200:
                v = v[:200] + "..."
            out[k] = v
    if not out:
        out = {"shape": _bounded_summary(payload, 80)}
    return out
