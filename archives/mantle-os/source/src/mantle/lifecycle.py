"""Target-bound lifecycle authorization and journal primitives.

The primitives are intentionally independent of hatch/graft storage so callers can
validate an authorization before creating a target directory.  SELF-vault recovery
can bypass this external activation gate; external artifacts cannot.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple


class LifecycleAction(str, Enum):
    HATCH = "hatch"
    GRAFT = "graft"


class LifecycleResult(str, Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    REFUSED = "refused"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class LineageAttestation:
    schema_version: str
    artifact_sha256: str
    issuer: Optional[str]
    parent_fingerprint: Optional[str]
    signature: Optional[str]
    status: str

    @classmethod
    def unattested(cls, artifact_sha256: str) -> "LineageAttestation":
        return cls("mantle-lineage-attestation-v1", artifact_sha256,
                   None, None, None, "UNATTESTED")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SporeInspection:
    schema_version: str
    carrier_integrity: bool
    artifact_sha256: str
    germ_schema: str
    inert: bool
    conversation_count: int
    conversation_sha256: str
    lineage: LineageAttestation
    declared_controls: Tuple[Any, ...] = ()
    declared_instincts: Tuple[Any, ...] = ()
    declared_capabilities: Tuple[Any, ...] = ()
    task: Optional[str] = None
    target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["lineage"] = self.lineage.to_dict()
        return data


@dataclass(frozen=True)
class LifecycleAuthorization:
    schema_version: str
    action: LifecycleAction
    artifact_sha256: str
    target_id: str
    operator_approved: bool
    issued_at: str
    expires_at: str
    nonce: str

    @classmethod
    def issue(cls, action: LifecycleAction, artifact: str, target_id: str,
              *, expires_at: Optional[str] = None) -> "LifecycleAuthorization":
        with open(artifact, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        default_expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        return cls("mantle-lifecycle-authorization-v1", action, digest,
                   canonical_target(target_id),
                   True, now, expires_at or default_expiry, secrets.token_hex(16))

    def redacted(self) -> Dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        data["target_id"] = hashlib.sha256(self.target_id.encode("utf-8")).hexdigest()[:16]
        return data


class LifecycleAuthorizationError(PermissionError):
    pass


def validate_authorization(auth: LifecycleAuthorization, action: LifecycleAction,
                           artifact: str, target_id: str,
                           *, used_nonces: Optional[set] = None) -> None:
    """Fail closed before target creation for missing, stale, replayed or mismatched auth."""
    if auth.schema_version != "mantle-lifecycle-authorization-v1":
        raise LifecycleAuthorizationError("unsupported lifecycle authorization schema")
    if auth.action != action or not auth.operator_approved:
        raise LifecycleAuthorizationError("operator authorization does not approve this action")
    with open(artifact, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    if digest != auth.artifact_sha256:
        raise LifecycleAuthorizationError("artifact fingerprint does not match authorization")
    if canonical_target(target_id) != auth.target_id:
        raise LifecycleAuthorizationError("resolved target does not match authorization")
    if used_nonces is not None and auth.nonce in used_nonces:
        raise LifecycleAuthorizationError("authorization nonce has already been used")
    try:
        expires = datetime.fromisoformat(auth.expires_at.replace("Z", "+00:00"))
        if expires < datetime.now(timezone.utc):
            raise LifecycleAuthorizationError("lifecycle authorization has expired")
    except ValueError:
        raise LifecycleAuthorizationError("authorization expiry is invalid")


def canonical_target(target_id: str) -> str:
    """Stable exact target identifier used only in memory and authorization files."""
    return os.path.normcase(os.path.realpath(os.path.abspath(str(target_id))))


def authorization_from_dict(data: Dict[str, Any]) -> LifecycleAuthorization:
    try:
        return LifecycleAuthorization(
            schema_version=str(data["schema_version"]),
            action=LifecycleAction(str(data["action"])),
            artifact_sha256=str(data["artifact_sha256"]),
            target_id=str(data["target_id"]),
            operator_approved=bool(data["operator_approved"]),
            issued_at=str(data["issued_at"]),
            expires_at=str(data["expires_at"]),
            nonce=str(data["nonce"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise LifecycleAuthorizationError("malformed lifecycle authorization") from exc


@dataclass
class LifecycleJournal:
    path: str
    action: LifecycleAction
    target_hash: str
    target_hint: str
    result: LifecycleResult = LifecycleResult.INTERRUPTED
    phase: str = "created"

    def write(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        payload = {"schema": "mantle-lifecycle-journal-v1", **asdict(self)}
        payload["action"] = self.action.value
        payload["result"] = self.result.name
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)


@dataclass
class LifecycleTransaction:
    """Unique same-parent staging tree promoted atomically after verification."""

    action: LifecycleAction
    target: str
    staging: str
    journal: LifecycleJournal

    def phase(self, name: str, result: LifecycleResult = LifecycleResult.INTERRUPTED) -> None:
        self.journal.phase = str(name)
        self.journal.result = result
        self.journal.write()

    def promote(self) -> str:
        if os.path.lexists(self.target):
            raise FileExistsError("lifecycle target already exists; historical targets are preserved")
        # The staging tree is not complete until the atomic rename succeeds.  Recording
        # PASS before os.replace made a filesystem interruption look certified and also
        # made the surviving stage ineligible for resume.
        self.phase("promotion_ready", LifecycleResult.INTERRUPTED)
        os.replace(self.staging, self.target)
        self.journal.path = os.path.join(self.target, "lifecycle_journal.json")
        self.phase("promoted", LifecycleResult.PASS)
        return self.target

    def interrupt(self, reason: str) -> None:
        previous = self.journal.phase
        self.journal.phase = "interrupted:%s:%s" % (previous, str(reason)[:120])
        self.journal.result = LifecycleResult.INTERRUPTED
        self.journal.write()


def load_journal(stage: str) -> LifecycleJournal:
    """Load and validate a journal belonging to an interrupted Mantle stage."""
    stage = canonical_target(stage)
    if not os.path.basename(stage).startswith(".mantle-stage-"):
        raise LifecycleAuthorizationError("resume requires a Mantle staging directory")
    path = os.path.join(stage, "lifecycle_journal.json")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema") != "mantle-lifecycle-journal-v1":
        raise LifecycleAuthorizationError("unsupported lifecycle journal schema")
    try:
        journal = LifecycleJournal(
            path=path,
            action=LifecycleAction(data["action"]),
            target_hash=str(data["target_hash"]),
            target_hint=str(data["target_hint"]),
            result=LifecycleResult(str(data["result"]).lower()),
            phase=str(data["phase"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LifecycleAuthorizationError("malformed lifecycle journal") from exc
    if journal.result != LifecycleResult.INTERRUPTED:
        raise LifecycleAuthorizationError("only an interrupted lifecycle can resume")
    return journal


def resume_transaction(stage: str) -> LifecycleTransaction:
    """Re-open an interrupted verified stage without replaying authorization.

    Resume is intentionally narrow: only a stage that reached ``artifact_verified``
    may be promoted. Earlier phases require quarantine and a fresh authorization,
    because arbitrary build steps are not safely replayable from a journal alone.
    """
    stage = canonical_target(stage)
    journal = load_journal(stage)
    resumable = (
        journal.phase in ("artifact_verified", "promotion_ready") or
        journal.phase.startswith("interrupted:artifact_verified:") or
        journal.phase.startswith("interrupted:promotion_ready:")
    )
    if not resumable:
        raise LifecycleAuthorizationError(
            "stage is not safely resumable; quarantine it and start with fresh authorization"
        )
    target = canonical_target(os.path.join(os.path.dirname(stage), journal.target_hint))
    if hashlib.sha256(target.encode("utf-8")).hexdigest() != journal.target_hash:
        raise LifecycleAuthorizationError("journal target binding is missing or invalid")
    if os.path.lexists(target):
        raise FileExistsError("prior completed target is preserved; resume will not overwrite it")
    return LifecycleTransaction(journal.action, target, stage, journal)


def _target_receipt(target: str) -> Dict[str, str]:
    canonical = canonical_target(target)
    return {
        "target_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "target_hint": os.path.basename(canonical) or "target",
    }


def begin_transaction(auth: LifecycleAuthorization, action: LifecycleAction,
                      artifact: str, target: str) -> LifecycleTransaction:
    """Validate/consume authorization before creating the unique staging tree."""
    canonical = canonical_target(target)
    validate_authorization(auth, action, artifact, canonical)
    parent = os.path.dirname(canonical)
    if not os.path.isdir(parent):
        raise LifecycleAuthorizationError("authorized target parent does not exist")
    if os.path.lexists(canonical):
        raise FileExistsError("lifecycle target already exists; use a new preserved target")

    # Durable one-shot nonce consumption. The raw target is intentionally omitted.
    registry = os.path.join(parent, ".mantle-lifecycle-authorizations")
    os.makedirs(registry, exist_ok=True)
    nonce_name = hashlib.sha256(auth.nonce.encode("utf-8")).hexdigest() + ".json"
    nonce_path = os.path.join(registry, nonce_name)
    try:
        with open(nonce_path, "x", encoding="utf-8") as handle:
            json.dump({"authorization": auth.redacted(), **_target_receipt(canonical)},
                      handle, indent=2, sort_keys=True)
    except FileExistsError as exc:
        raise LifecycleAuthorizationError("authorization nonce has already been used") from exc

    staging = tempfile.mkdtemp(prefix=".mantle-stage-%s-" % action.value, dir=parent)
    receipt = _target_receipt(canonical)
    journal = LifecycleJournal(
        os.path.join(staging, "lifecycle_journal.json"), action,
        receipt["target_hash"], receipt["target_hint"],
        LifecycleResult.INTERRUPTED, "authorized",
    )
    journal.write()
    return LifecycleTransaction(action, canonical, staging, journal)


def load_authorization(path: str) -> LifecycleAuthorization:
    with open(path, "r", encoding="utf-8") as handle:
        return authorization_from_dict(json.load(handle))


def write_authorization(auth: LifecycleAuthorization, path: str) -> str:
    payload = asdict(auth)
    payload["action"] = auth.action.value
    with open(path, "x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    return path
