from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any


COVERAGE_STATES = {"MAPPED", "PARTIAL", "BLOCKED", "NOT_APPLICABLE", "UNKNOWN"}
EVIDENCE_CLASSES = {"DIRECT", "MEASURED", "REPORTED", "INFERRED", "ASSUMED", "UNKNOWN"}


def stable_id(namespace: str, *parts: object) -> str:
    payload = "\x1f".join([namespace, *[str(p) for p in parts]])
    return f"{namespace}:{sha256(payload.encode('utf-8', 'surrogatepass')).hexdigest()[:20]}"


@dataclass(slots=True)
class Evidence:
    id: str
    file_id: str
    path: str
    start_line: int | None
    end_line: int | None
    evidence_class: str = "DIRECT"
    extractor: str = ""
    excerpt: str | None = None


@dataclass(slots=True)
class Node:
    id: str
    kind: str
    name: str
    file_id: str | None = None
    path: str | None = None
    coverage: str = "MAPPED"
    attributes: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Edge:
    id: str
    src: str
    dst: str
    kind: str
    coverage: str = "MAPPED"
    attributes: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Finding:
    id: str
    kind: str
    title: str
    status: str
    attributes: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)




@dataclass(slots=True)
class SemanticObject:
    id: str
    object_type: str
    subtype: str
    label: str
    coverage: str = "UNKNOWN"
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SemanticRelation:
    id: str
    src: str
    dst: str
    kind: str
    status: str = "MAPPED"
    attributes: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CoverageDimension:
    id: str
    key: str
    label: str
    state: str
    parent_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExtractionResult:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def merge(self, other: "ExtractionResult") -> None:
        self.nodes.extend(other.nodes)
        self.edges.extend(other.edges)
        self.evidence.extend(other.evidence)
        self.findings.extend(other.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [asdict(x) for x in self.nodes],
            "edges": [asdict(x) for x in self.edges],
            "evidence": [asdict(x) for x in self.evidence],
            "findings": [asdict(x) for x in self.findings],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExtractionResult":
        return cls(
            nodes=[Node(**x) for x in payload.get("nodes", [])],
            edges=[Edge(**x) for x in payload.get("edges", [])],
            evidence=[Evidence(**x) for x in payload.get("evidence", [])],
            findings=[Finding(**x) for x in payload.get("findings", [])],
        )
