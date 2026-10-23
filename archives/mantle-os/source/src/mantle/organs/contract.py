#!/usr/bin/env python3
"""
mantle.organs.contract  --  the organ contract (Mantle OS)

Every organ declares itself with a machine-readable contract: its role, the bands it may
read and write, its reflex surface, its Phase-1 state, its Phase-2 extension, its audit
obligations, and its fail mode. The contract is DATA -- validated when the organism is
wired, enforced when the organ writes (a write outside the declared bands is refused and
becomes an immune event), and inspectable by the audits and by an agent operating the
AppAI runtime.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class OrganContract:
    def __init__(self, organ: str, role: str, *,
                 reads: Optional[List[str]] = None,
                 writes: Optional[List[str]] = None,
                 reflexes: Optional[List[Dict[str, str]]] = None,
                 phase1: str = "active",
                 phase2_extension: str = "none",
                 audit: Optional[List[str]] = None,
                 fail_mode: str = "fail-open") -> None:
        if phase1 not in ("active", "dormant", "dormant->active"):
            raise ValueError("phase1 must be active | dormant | dormant->active")
        if fail_mode != "fail-open":
            raise ValueError("every Mantle organ is fail-open: a sick organ degrades, "
                             "it never crashes the host or hides faults")
        self.organ = organ
        self.role = role
        self.reads = list(reads or [])
        self.writes = list(writes or [])
        self.reflexes = list(reflexes or [])
        self.phase1 = phase1
        self.phase2_extension = phase2_extension
        self.audit = list(audit or [])
        self.fail_mode = fail_mode

    def may_write(self, band: str) -> bool:
        return band in self.writes or "*" in self.writes

    def to_dict(self) -> Dict[str, Any]:
        return {"organ": self.organ, "role": self.role, "reads": self.reads,
                "writes": self.writes, "reflexes": self.reflexes, "phase1": self.phase1,
                "phase2_extension": self.phase2_extension, "audit": self.audit,
                "fail_mode": self.fail_mode}


class Organ:
    """Base organ: holds the organism, exposes its contract, and provides the ONE write
    path -- `self.append(band, entry)` -- which enforces the contract's band permissions.
    An out-of-contract write is refused AND becomes an immune event (overreach)."""

    contract: OrganContract = None  # subclasses set this

    def __init__(self, organism: Any) -> None:
        self.org = organism

    @property
    def bus(self):
        return self.org.bus

    def append(self, band: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        if not self.contract.may_write(band):
            self.org.immune_event("organ_overreach", {
                "organ": self.contract.organ, "band": band,
                "declared_writes": self.contract.writes})
            raise PermissionError("organ %r may not write band %r (declared: %s)"
                                  % (self.contract.organ, band, self.contract.writes))
        return self.org.prime.append(band, entry)

    def manifest(self) -> Dict[str, Any]:
        return self.contract.to_dict()
