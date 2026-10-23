#!/usr/bin/env python3
"""
mantle.core.events  --  the SignalBus: the organism's reflex/event bus (Mantle OS)

Organs do not reach into each other. They publish SIGNALS onto one deterministic,
synchronous bus and subscribe REFLEXES to the signal kinds they care about. The bus is the
nervous tissue between organs; the cube is the durable record. Properties:

  deterministic   handlers run synchronously, in registration order -- no threads, no
                  reordering, no LLM. A Phase-1 organism's whole behavior is replayable.
  fail-open       a faulting reflex is caught, degraded, and escalated as an IMMUNE event;
                  it never crashes the host and never fails silently (HF-B32).
  bounded         re-entrant emits are queued and drained in order (no recursion blowups);
                  the immune escalation path never re-enters itself.
  inspectable     the bus keeps a small trace ring of the last signals for audit/debug.

Well-known signal kinds (organs may add app-specific ones):
  pulse, sense, significant, reflex, dispatch, immune, pressure, checkpoint, cognition
"""
from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, List, Optional

Handler = Callable[[Dict[str, Any]], None]

TRACE_LIMIT = 256


class SignalBus:
    def __init__(self, immune_sink: Optional[Callable[[str, Any], None]] = None) -> None:
        # immune_sink(kind, detail): where reflex faults and policy violations go.
        # Wired to the Immune organ by the Organism; a missing sink collects locally.
        self._subs: Dict[str, List[Handler]] = {}
        self._immune_sink = immune_sink
        self._queue: deque = deque()
        self._draining = False
        self.trace: deque = deque(maxlen=TRACE_LIMIT)
        self.pending_immune: List[Dict[str, Any]] = []   # collected before a sink is wired
        self._handler_organs: Dict[int, str] = {}

    # ---- wiring -------------------------------------------------------------
    def set_immune_sink(self, sink: Callable[[str, Any], None]) -> None:
        self._immune_sink = sink
        for evt in self.pending_immune:                  # deliver anything held back
            sink(evt["kind"], evt["detail"])
        self.pending_immune = []

    def subscribe(self, kind: str, handler: Handler, *, organ: str = "?") -> None:
        """Register a reflex for a signal kind. Order of registration = order of firing."""
        self._subs.setdefault(kind, []).append(handler)
        self._handler_organs[id(handler)] = organ
        try:
            setattr(handler, "_mantle_organ", organ)
        except (AttributeError, TypeError):
            pass

    def _organ_for(self, handler: Handler) -> str:
        return getattr(handler, "_mantle_organ", self._handler_organs.get(id(handler), "?"))

    def reflex_surface(self) -> Dict[str, List[str]]:
        """The inspectable reflex surface: signal kind -> the organs subscribed to it."""
        return {kind: [self._organ_for(h) for h in handlers]
                for kind, handlers in sorted(self._subs.items())}

    # ---- emission -------------------------------------------------------------
    def emit(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Publish a signal. Re-entrant emits queue behind the current one (breadth-first,
        deterministic). Handler faults degrade to immune events, never propagate."""
        self._queue.append((kind, payload or {}))
        if self._draining:
            return
        self._draining = True
        try:
            while self._queue:
                k, p = self._queue.popleft()
                self.trace.append({"kind": k, "payload_keys": sorted(p.keys())})
                for handler in list(self._subs.get(k, [])):
                    try:
                        handler(p)
                    except Exception as e:               # noqa: BLE001 -- fail-open
                        self._escalate("reflex_fault", {
                            "signal": k,
                            "organ": self._organ_for(handler),
                            "error": "%s: %s" % (type(e).__name__, e)})
        finally:
            self._draining = False

    def _escalate(self, kind: str, detail: Any) -> None:
        if self._immune_sink is None:
            self.pending_immune.append({"kind": kind, "detail": detail})
            return
        try:
            self._immune_sink(kind, detail)
        except Exception:                                # the immune path must never recurse
            self.pending_immune.append({"kind": kind, "detail": detail})
