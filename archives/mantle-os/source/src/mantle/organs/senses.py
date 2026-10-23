#!/usr/bin/env python3
"""
mantle.organs.senses  --  the Senses organ: perception, the ONLY inbound boundary (Mantle OS)

ALL inbound data enters the organism through Senses. It ingests external signals,
REDACTS them at the boundary (a secret must never burn into append-only memory), and
CLASSIFIES their significance deterministically -- with NO LLM -- on the compound key
(action_id, event_type):

  REFLEX       bound to an immediate Body response; handled WITHOUT reaching the brain
  ROUTINE      known-mundane; recorded, no escalation
  SIGNIFICANT  anything unrecognized; recorded and (in Phase 2) surfaced to cognition

Every inbound signal produces EXACTLY ONE senses entry. Senses also owns the afferent
half of the surface: the Human Surface Map (the inventory of every human-visible control;
operating them is efferent and belongs to Limbs).
"""
from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, List, Set, Tuple

from .contract import Organ, OrganContract
from ..vcw.entry import make_entry
from ..core.redact import redact

CONTRACT = OrganContract(
    "senses", "perception (afferent I/O) -- the only inbound boundary",
    reads=["senses", "identity"],
    writes=["senses"],
    reflexes=[
        {"name": "classify", "trigger": "an inbound signal (action_id, event_type)",
         "effect": "tag REFLEX | ROUTINE | SIGNIFICANT (deterministic, no LLM)"},
        {"name": "inhale", "trigger": "an inbound signal",
         "effect": "redact -> exactly one senses entry -> run reflex arc if REFLEX"},
        {"name": "reflex-arc", "trigger": "a signal classified REFLEX",
         "effect": "execute the bound Body response immediately, no MIND, no brain band"},
        {"name": "map-surface", "trigger": "a control registered",
         "effect": "enumerate human-visible controls into the Human Surface Map"},
        {"name": "drain", "trigger": "heartbeat sense-intake step",
         "effect": "inhale every queued signal, in arrival order"},
    ],
    phase1="active",
    phase2_extension="SIGNIFICANT signals are surfaced to the MIND during heartbeat cognition",
    audit=[
        "classifier is deterministic and never calls an LLM",
        "every inbound signal produces exactly one senses entry",
        "REFLEX signals are handled without reaching the brain band",
        "signals are redacted before they become permanent memory",
    ],
)


class Senses(Organ):
    REFLEX = "REFLEX"
    ROUTINE = "ROUTINE"
    SIGNIFICANT = "SIGNIFICANT"

    contract = CONTRACT

    def __init__(self, organism) -> None:
        super().__init__(organism)
        self.reflex_arcs: Dict[Tuple[Any, Any], Callable[[Any, Dict[str, Any]], None]] = {}
        self.routine_keys: Set[Tuple[Any, Any]] = set()
        self.surface_map: Dict[str, Dict[str, Any]] = {}    # the Human Surface Map (afferent)
        self.inbox: deque = deque()                         # queued signals for the next pulse

    # ---- wiring -------------------------------------------------------------
    def bind_reflex(self, action_id: Any, event_type: Any,
                    response: Callable[[Any, Dict[str, Any]], None]) -> None:
        """Bind a deterministic Body response to a signal key (the reflex arc)."""
        self.reflex_arcs[(action_id, event_type)] = response

    def mark_routine(self, action_id: Any, event_type: Any) -> None:
        self.routine_keys.add((action_id, event_type))

    def map_control(self, control_id: str, descriptor: Dict[str, Any]) -> None:
        """Afferent surface perception: a human-visible control enters the Surface Map.
        (Limbs owns the efferent half -- the ControlBridge that operates it.)"""
        self.surface_map[control_id] = descriptor

    # ---- reflexes -------------------------------------------------------------
    def classify(self, action_id: Any, event_type: Any) -> str:
        key = (action_id, event_type)
        if key in self.reflex_arcs:
            return self.REFLEX
        if key in self.routine_keys:
            return self.ROUTINE
        return self.SIGNIFICANT

    def inhale(self, signal: Dict[str, Any]) -> str:
        """Ingest one signal NOW: classify, write EXACTLY ONE redacted senses entry, run
        the bound reflex arc if REFLEX (never touching the brain band), and emit a bus
        signal so other organs can subscribe without reaching into Senses."""
        action_id = signal.get("action_id")
        event_type = signal.get("event_type")
        cls = self.classify(action_id, event_type)
        entry = make_entry(redact({"signal": signal, "class": cls}),
                           opcode="SENSE", author="BODY")
        self.append("senses", entry)
        if cls == self.REFLEX:
            self.reflex_arcs[(action_id, event_type)](self.org, signal)
        self.bus.emit("sense", {"class": cls, "action_id": action_id,
                                "event_type": event_type})
        if cls == self.SIGNIFICANT:
            self.bus.emit("significant", {"action_id": action_id,
                                          "event_type": event_type})
        return cls

    def receive(self, signal: Dict[str, Any]) -> None:
        """Queue a signal for the next heartbeat's sense-intake step (the inbox)."""
        self.inbox.append(signal)

    def drain(self) -> List[str]:
        """The heartbeat's sense-intake step: inhale every queued signal in order."""
        results = []
        while self.inbox:
            results.append(self.inhale(self.inbox.popleft()))
        return results
