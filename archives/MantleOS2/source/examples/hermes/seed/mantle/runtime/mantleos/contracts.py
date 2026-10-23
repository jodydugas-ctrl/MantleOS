"""Substrate-neutral MantleOS 2 contracts.

These records describe an organism without assuming Python, Hermes, or a
particular VCW carrier.  Target-specific code may serialize them differently,
but it must preserve their semantic fields and version identifiers.
"""

from __future__ import annotations

import dataclasses
import enum
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "mantle.contracts.v2"


class TissueState(enum.StrEnum):
    FOUND = "found"
    ACQUIRED = "acquired"
    IDENTIFIED = "identified"
    STAGED = "staged"
    EXERCISED = "exercised"
    VERIFIED = "verified"
    AUTHORIZED = "authorized"
    ADOPTED = "adopted"
    ACTIVE = "active"
    QUARANTINED = "quarantined"
    REVOKED = "revoked"
    RETIRED = "retired"


class Direction(enum.StrEnum):
    AFFERENT = "afferent"
    EFFERENT = "efferent"
    BIDIRECTIONAL = "bidirectional"


class SourceKind(enum.StrEnum):
    GIT_REPOSITORY = "git-repository"
    LOCAL_REPOSITORY = "local-repository"
    INSTALLED_APPLICATION = "installed-application"
    PORTABLE_ARTIFACT = "portable-artifact"
    UNKNOWN = "unknown"


class PhysiologyState(enum.StrEnum):
    CONSTRUCTION = "construction"
    UNBORN = "unborn"
    ACTIVE = "active"
    STASIS = "stasis"
    DEFENSE = "defense"
    STARVED = "starved"
    RECOVERY = "recovery"


class CoverageState(enum.StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not-applicable"


class LoopDisposition(enum.StrEnum):
    DIRECTLY_INNERVATED = "directly-innervated"
    COVERED_BY_ENCLOSING_ARTERY = "covered-by-enclosing-artery"
    LOCAL_UTILITY = "local-utility-no-direct-nerve"
    BLOCKED = "blocked-insufficient-evidence"


@dataclass(frozen=True)
class SourceAnchor:
    path: str
    symbol: str
    anchor_sha256: str
    insertion: str


@dataclass(frozen=True)
class NerveSpec:
    nerve_id: str
    direction: Direction
    semantic_event: str
    anchor: SourceAnchor
    book_id: str | None = None
    capability_id: str | None = None
    payload_schema: str = "mantle.semantic-event.v2"
    redaction_policy: str = "deny-secrets"
    failure_mode: str = "native-no-op"
    tissue_state: TissueState = TissueState.STAGED


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    host_symbol: str
    description: str
    effect: str
    input_schema: str
    verifier: str
    default_authority: str = "denied"
    implementation_status: str = "observed"
    availability_status: str = "not-exercised"
    evidence_status: str = "static"
    transition_owner: str = "BODY"
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class HabitatSpec:
    source_kind: SourceKind
    ecosystem: str
    nest_role: str = "default-body-layer-0"
    host_application: str | None = None
    storage_boundary: str = "nest-local-filesystem"
    permission_boundary: str = "host-owned"
    native_surfaces: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileCoverage:
    path: str
    sha256: str
    bytes: int
    language: str | None
    ownership: str
    artifact_kind: str
    parser: str | None
    state: CoverageState
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoopSpec:
    loop_id: str
    path: str
    line: int
    language: str
    syntax: str
    enclosing_symbol: str | None
    artery_classes: tuple[str, ...]
    disposition: LoopDisposition
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class BodyMap:
    source_uri: str
    source_fingerprint: str
    default_body: str = "NEST"
    logical_layer: int = 0
    habitat: HabitatSpec | None = None
    languages: dict[str, int] = field(default_factory=dict)
    entrypoints: tuple[str, ...] = ()
    build_systems: tuple[str, ...] = ()
    behavior_surfaces: tuple[str, ...] = ()
    capabilities: tuple[CapabilitySpec, ...] = ()
    file_coverage: tuple[FileCoverage, ...] = ()
    loops: tuple[LoopSpec, ...] = ()
    graphs: dict[str, Any] = field(default_factory=dict)
    surfaces: dict[str, Any] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)
    behavior_baseline: dict[str, Any] = field(default_factory=dict)
    unknowns: tuple[str, ...] = ()
    schema: str = "mantle.body-map.v2"


@dataclass(frozen=True)
class BookSpec:
    book_id: str
    name: str
    tome: str
    dialect: str
    record_schema: str
    carrier: str = "encrypted-append-segments"
    capacity_bytes: int = 262_144


@dataclass(frozen=True)
class ActionFrame:
    action_id: str
    capability_id: str
    arguments: dict[str, Any]
    thought_ref: str
    requested_by: str = "MIND"
    schema: str = "mantle.action-frame.v2"


@dataclass(frozen=True)
class ActionReceipt:
    action_id: str
    capability_id: str
    disposition: str
    verifier: str
    result_digest: str | None = None
    reason: str | None = None
    schema: str = "mantle.action-receipt.v2"


@dataclass(frozen=True)
class PrimerCandidate:
    commandments_version: str
    commandments_sha256: str
    personality_sha256: str
    purpose: str
    evidence: tuple[dict[str, str], ...]
    unsupported_claims: tuple[str, ...] = ()
    status: str = "awaiting-user-approval"
    schema: str = "mantle.primer-candidate.v2"


def contract_dict(value: Any) -> dict[str, Any]:
    """Return a stable JSON-ready representation of a contract dataclass."""
    if not dataclasses.is_dataclass(value):
        raise TypeError("value is not a Mantle contract dataclass")

    def convert(item: Any) -> Any:
        if isinstance(item, enum.Enum):
            return item.value
        if dataclasses.is_dataclass(item):
            return {field.name: convert(getattr(item, field.name)) for field in dataclasses.fields(item)}
        if isinstance(item, dict):
            return {str(key): convert(value) for key, value in item.items()}
        if isinstance(item, (tuple, list)):
            return [convert(value) for value in item]
        return item

    return convert(value)
