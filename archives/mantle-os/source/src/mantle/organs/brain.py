#!/usr/bin/env python3
"""
mantle.organs.brain  --  the Brain organ: the dormant Phase-2 socket (Mantle OS)

The Brain is the only organ that is FULLY DORMANT in Phase 1: the cube has the bands
(`brain`, `thoughts`); nothing writes them. This module is deliberately just the SOCKET --
it holds a fused cognition object and never imports a model, a transport, or anything
from `mantle.mind`. That import direction is the architecture: Phase-1 code cannot reach
an LLM even by accident.

Fusion contract (what `fuse()` accepts): any object with
    cognize(snapshot) -> Optional[str]
The reference implementation is `mantle.mind.Mind`, which is bounded by the Body: it may
write only `thoughts` + `brain`, it proposes while the Body applies, and it cannot
self-promote a skill. Fusion is REFUSED unless the organism's Stage-1 gate has been
certified and separate operator and guardian approvals target this resident.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ..core.authority import validate_fusion_authorization
from .contract import Organ, OrganContract

CONTRACT = OrganContract(
    "brain", "cognition (Phase 2 only) -- the fused MIND's socket; dormant in Phase 1",
    reads=["*"],                       # via the assembled snapshot, never raw layers
    writes=["thoughts", "brain"],      # the ONLY MIND write surface, Body-enforced
    reflexes=[],                       # the Brain is the non-reflex organ; it reasons
    phase1="dormant",
    phase2_extension="receives the assembled context each pulse, thinks into `thoughts`, "
                     "authors INTENTION/DELEGATED dispatches, proposes to the Body",
    audit=[
        "Phase 1: the brain/thoughts bands exist and nothing cognitive writes them",
        "fusion requires Stage-1 evidence plus explicit operator and guardian approval",
        "the fused MIND writes nowhere except thoughts + brain",
        "the fused MIND cannot touch the Genome or self-promote a skill",
    ],
)


class Brain(Organ):
    contract = CONTRACT

    def __init__(self, organism) -> None:
        super().__init__(organism)
        self._mind: Optional[Any] = None
        self._fusion_authorization: Optional[Dict[str, Any]] = None

    @property
    def fused(self) -> bool:
        return self._mind is not None

    @property
    def mind(self) -> Optional[Any]:
        return self._mind

    @property
    def fusion_authorization(self) -> Optional[Dict[str, Any]]:
        """Return the minimized receipt in the validator's external schema."""
        if not self._fusion_authorization:
            return None
        receipt = self._fusion_authorization
        return {
            "target": {"resident_identity": receipt["resident_identity"]},
            "operator": {"fusion_decision": receipt["operator"]},
            "guardian": {"fusion_decision": receipt["guardian"]},
            "effective_decision": {
                "mind_fusion_authorized": receipt["mind_fusion_authorized"]
            },
        }

    def fuse(self, mind: Any, stage1_certified: bool = False,
             authorization: Any = None) -> None:
        """Attach cognition only after technical certification and dual authorization."""
        if not stage1_certified:
            self.org.immune_event("fusion_refused",
                                  {"reason": "Stage-1 gate not certified"})
            raise PermissionError("audit before fusion: certify the Zombie Body "
                                  "(Stage 1) before fusing a MIND")
        try:
            authority = validate_fusion_authorization(self.org, authorization)
        except PermissionError as exc:
            self.org.immune_event("fusion_refused", {"reason": str(exc)})
            raise
        if not callable(getattr(mind, "cognize", None)):
            raise TypeError("a fused MIND must provide cognize(snapshot)")
        self._mind = mind
        self._fusion_authorization = authority
        self.org.immune_event("fusion", {
            "mind": type(mind).__name__,
            "operator": authority["operator"],
            "guardian": authority["guardian"],
        })

    def defuse(self) -> None:
        """Detach cognition. The Body keeps running -- Phase 1 never depended on it."""
        self._mind = None
        self._fusion_authorization = None

    def cognize(self, snapshot: Dict[str, Any]) -> Optional[Any]:
        """The Phase-2 heartbeat extension: offer the assembled snapshot to the fused
        MIND. Fail-open: a sick MIND degrades to an immune event; the pulse completes."""
        if self._mind is None:
            return None
        try:
            return self._mind.cognize(snapshot)
        except Exception as e:                   # noqa: BLE001 -- cognition is fail-open
            self.org.immune_event("cognition_fault",
                                  {"error_type": type(e).__name__})
            return None
