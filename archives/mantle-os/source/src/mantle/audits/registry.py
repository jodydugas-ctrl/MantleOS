#!/usr/bin/env python3
"""Typed, validated registry for Mantle's executable invariants."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple


InvariantRunner = Callable[[], Tuple[bool, str]]


@dataclass(frozen=True)
class InvariantSpec:
    code: str
    title: str
    guarantee_id: str
    runner: InvariantRunner
    added: str
    concern: str

    @property
    def name(self) -> str:
        return "%s %s" % (self.code, self.title)


_GUARANTEE_BY_CODE: Dict[str, str] = {
    "EXEC-LIMIT-1": "TM-SKILL-MEMORY-OUTPUT",
    "EXEC-TRUST-1": "TM-FOREIGN-EXECUTION",
    "MIND-PORT-1": "TM-WRAPPER-RAW-HANDLE",
    "STAGE2-PROFILE-1": "TM-REFERENCE-CERT",
    "SUPPLY-1": "TM-FOREIGN-ACQUISITION",
    "CERTIFY-1": "TM-APPLICATION-CERT",
    "DOCTOR-1": "TM-REFERENCE-CERT",
}


def _guarantee(code: str) -> str:
    if code.startswith("CONSOLIDATION-"):
        return "TM-CONSOLIDATION-AUTHORITY"
    if code.startswith("GRIMOIRE-V010-"):
        return "TM-GRIMOIRE-EDITION"
    if code.startswith("GRIMOIRE-ENC-"):
        return "TM-GRIMOIRE-SEMANTIC"
    if code in _GUARANTEE_BY_CODE:
        return _GUARANTEE_BY_CODE[code]
    if code in {"HF-B07", "HF-B45", "HF-B02"}:
        return "TM-GENOME-MUTATION"
    if code == "HF-B08":
        return "TM-PHASE1-MODEL-FREE"
    if code == "HF-B20":
        return "TM-SECRET-BOUNDARY"
    if code in {"GHNEST-1", "GHNEST-2", "GHNEST-12", "GHNEST-15", "GHNEST-16"}:
        return "TM-REMOTE-RESIDENCY"
    if code in {"GHNEST-5", "GHNEST-19", "GHNEST-20"}:
        return "TM-REMOTE-INTEGRITY"
    if code in {"GHNEST-3", "GHNEST-10"}:
        return "TM-REMOTE-SECRET"
    if code in {"GHNEST-4", "GHNEST-6", "GHNEST-7"}:
        return "TM-REMOTE-CAS"
    if code in {"GHNEST-8", "GHNEST-9", "GHNEST-14", "GHNEST-18"}:
        return "TM-REMOTE-EVENTS"
    if code in {"GHNEST-11", "GHNEST-13", "GHNEST-17"}:
        return "TM-REMOTE-ISOLATION"
    if code.startswith("HF-B46"):
        return "TM-ANCESTOR-SEAL"
    if code in {"HF-B47", "HF-B48", "HF-B52"}:
        return "TM-SKILL-INTEGRITY"
    if code == "HF-B50":
        return "TM-FOREIGN-EXECUTION"
    if code == "HF-B51":
        return "TM-AST-KNOWN-REFUSALS"
    if code == "HF-M10":
        return "TM-MIND-BAND-SCOPE"
    if code in {"HF-M12", "HF-M16"}:
        return "TM-MIND-SELF-PROMOTION"
    if code == "HF-M14":
        return "TM-CONTEXT-VEIL"
    if code == "HF-M15":
        return "TM-FUSION-AUTHORITY"
    if code.startswith("CONTEXT-"):
        return "TM-CONTEXT-LEDGER"
    return "TM-REFERENCE-CERT"


def _concern(code: str) -> str:
    if code.startswith("CONSOLIDATION-"):
        return "cognition"
    if code.startswith(("EXEC", "HF-B47", "HF-B48", "HF-B50", "HF-B51", "HF-B52")):
        return "execution"
    if code.startswith(("HF-M", "MIND-", "STAGE2-")):
        return "cognition"
    if code.startswith("CONTEXT-"):
        return "cognition"
    if code.startswith(("APPLET", "SUPPLY", "ASSIM", "APPBAND", "STATUS")):
        return "application"
    if code.startswith(("REPRO", "SPORE", "VAULT", "BOOT", "GRAFT")):
        return "reproduction"
    if code.startswith(("PHENO", "RESID", "NOC", "SCHED", "SYM")):
        return "residency"
    if code.startswith(("MEM", "B-", "HF-B", "PERSIST", "SELF", "GRIMOIRE-ENC-")):
        return "body"
    if code.startswith("GHNEST"):
        return "operations"
    return "operations"


def build_registry(
    definitions: Iterable[Tuple[str, InvariantRunner]],
    *,
    added: str = "pre-registry",
) -> Tuple[InvariantSpec, ...]:
    specs: List[InvariantSpec] = []
    seen_names = set()
    for name, runner in definitions:
        code, separator, title = name.partition(" ")
        if not separator or not code or not title:
            raise ValueError("invalid invariant name %r; expected '<code> <title>'" % name)
        if name in seen_names:
            raise ValueError("duplicate invariant name %s" % name)
        seen_names.add(name)
        specs.append(InvariantSpec(
            code=code,
            title=title,
            guarantee_id=_guarantee(code),
            runner=runner,
            added=added,
            concern=_concern(code),
        ))
    if not specs:
        raise ValueError("invariant registry may not be empty")
    return tuple(specs)


def by_concern(registry: Iterable[InvariantSpec]) -> Dict[str, Tuple[InvariantSpec, ...]]:
    groups: Dict[str, List[InvariantSpec]] = {}
    for spec in registry:
        groups.setdefault(spec.concern, []).append(spec)
    return {name: tuple(specs) for name, specs in sorted(groups.items())}
