#!/usr/bin/env python3
"""
mantle.organs.nervous  --  the Nervous System organ: routing + Context Assembly (Mantle OS)

Owns the reference resolver (delegated to mantle.core.refs) and the Context Assembly
Protocol: the deterministic act of materializing a fully-resolved context snapshot from
the cube + Body. The doctrine: an AppAI "sees the whole of its experience in perfect
clarity" -- Context Assembly IS that whole-at-once view.

Two guarantees, both Body reflexes (no LLM):
  * NO unresolved reference is ever handed onward; a dangling reference is an immune
    event, never a silent drop.
  * The veil is applied -- the private `thoughts` band is excluded unless lifted.

In Phase 2 the assembled snapshot is exactly what the MIND receives -- already resolved,
already veiled. The MIND never sees a raw reference.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .contract import Organ, OrganContract
from ..core import refs as _refs

_REF_RE = re.compile(r"<[^<>]+>")

CONTRACT = OrganContract(
    "nervous", "signal routing, reference resolution, deterministic Context Assembly",
    reads=["*"],
    writes=[],          # the Nervous System routes and assembles; it owns no band writes
    reflexes=[
        {"name": "resolve", "trigger": "any <reference>",
         "effect": "deterministic resolution; dangling -> immune event"},
        {"name": "assemble", "trigger": "heartbeat context-assembly step / MIND fusion",
         "effect": "fully-resolved, veiled snapshot; `_complete` flags any leftover"},
        {"name": "route", "trigger": "a bus signal", "effect": "deliver between organs"},
    ],
    phase1="active",
    phase2_extension="the assembled snapshot is handed to the MIND (already resolved/veiled)",
    audit=[
        "Context Assembly is deterministic and LLM-free",
        "no unresolved reference ever reaches a provider",
        "every dangling reference is an immune event",
    ],
)


class Nervous(Organ):
    contract = CONTRACT

    # ---- resolve ---------------------------------------------------------------
    def resolve(self, ref: str) -> Any:
        return _refs.resolve(self.org, ref)

    def resolve_all(self, obj: Any) -> Any:
        """Walk a structure, replacing any value that is EXACTLY a reference with its
        resolved value (dangling -> immune event)."""
        if isinstance(obj, str):
            s = obj.strip()
            return self.resolve(s) if _REF_RE.fullmatch(s) else obj
        if isinstance(obj, dict):
            return {k: self.resolve_all(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.resolve_all(v) for v in obj]
        return obj

    def _unresolved(self, obj: Any, out: List[str]) -> None:
        if isinstance(obj, str):
            if _REF_RE.search(obj):
                out.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                self._unresolved(v, out)
        elif isinstance(obj, list):
            for v in obj:
                self._unresolved(v, out)

    # ---- the Context Assembly Protocol -------------------------------------------
    def assemble(self, reveal_private: bool = False) -> Dict[str, Any]:
        """Deterministically assemble a fully-resolved, veiled snapshot. `_complete` is
        True iff no unresolved reference remains (any leftover is an immune event).
        Resolution and the completeness scan run in ONE traversal."""
        leftover: List[str] = []

        def resolve_and_check(obj: Any) -> Any:
            if isinstance(obj, str):
                s = obj.strip()
                val = self.resolve(s) if _REF_RE.fullmatch(s) else obj
                self._unresolved(val, leftover)
                return val
            if isinstance(obj, dict):
                return {k: resolve_and_check(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [resolve_and_check(v) for v in obj]
            return obj

        prime = self.org.prime
        snap: Dict[str, Any] = {
            "primer": self.org.body.boot_order(),                              # identity/boot
            "identity": prime.read("identity"),                                # self-state
            "facts": prime.read("facts"),                                      # truths
            "events": prime.read("events"),                                    # history
            "discoveries": prime.read("discoveries"),                          # learned
            "senses": prime.read("senses"),                                    # perception
            "thoughts": prime.read("thoughts", reveal_private=reveal_private), # the veil
        }
        snap = resolve_and_check(snap)
        if leftover:
            self.org.immune_event("unresolved_ref",
                                  {"count": len(leftover), "sample": leftover[:3]})
        snap["_complete"] = not leftover
        return snap
