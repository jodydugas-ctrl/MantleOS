"""Typed substrate coverage and insertion-state contracts for Mantle 2."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CoverageState(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class InsertionState(str, Enum):
    OBSERVED_CAUSAL_GRAPH = "observed_causal_graph"
    RENDERED_NATIVE_SCAFFOLD = "rendered_native_scaffold"
    COMPILE_READY_PATCH = "compile_ready_patch"
    APPLIED_HOST_HOOK = "applied_host_hook"


@dataclass(frozen=True)
class ParserCapability:
    language: str
    available: bool
    parser: str
    limitations: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SymbolEvidence:
    name: str
    path: str
    language: str
    primary_role: str
    candidate_roles: Tuple[str, ...] = ()
    ownership: str = "first_party"
    artifact_kind: str = "source"
    evidence: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateRole:
    role: str
    confidence: float
    evidence: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SubstrateCoverage:
    language: str
    first_party_files: int
    first_party_bytes: int
    parsed_files: int
    total_first_party_files: int = 0
    total_first_party_bytes: int = 0
    material_gaps: Tuple[str, ...] = ()
    parser: Optional[ParserCapability] = None

    @property
    def state(self) -> CoverageState:
        total_files = self.total_first_party_files or self.first_party_files
        total_bytes = self.total_first_party_bytes or self.first_party_bytes
        dominant = self.parsed_files == 0 and (
            self.first_party_files > total_files / 2 or self.first_party_bytes > total_bytes / 2
        )
        if dominant and (not self.parser or not self.parser.available):
            return CoverageState.BLOCKED
        if self.material_gaps or self.parsed_files < self.first_party_files:
            return CoverageState.PARTIAL
        return CoverageState.COMPLETE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "first_party_files": self.first_party_files,
            "first_party_bytes": self.first_party_bytes,
            "parsed_files": self.parsed_files,
            "material_gaps": list(self.material_gaps),
            "state": self.state.value,
            "parser": self.parser.__dict__ if self.parser else None,
        }
