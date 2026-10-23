#!/usr/bin/env python3
"""
mantle.assimilator.wrappers  --  the fail-open hook runtime (Mantle OS)

Path B, Phase 5+: AFTER the Phase 0 inventory gate is signed, host behavior is threaded
through the organism WITHOUT being changed. The hook runtime wraps host callables --
additively, reversibly, fail-open:

  * the host function runs EXACTLY as before (same args, same return, same exceptions);
  * around it, the organism perceives (Senses), proves (Limbs), mirrors (Memory), or
    redacts (Immune) according to the symbol's organ role;
  * a fault inside a hook degrades to an immune event -- it can NEVER crash the host
    (HF-B32) and never alters the host's result (HF-B40).

`Assimilation.wrap(role, fn)` returns the instrumented callable; the original is kept on
the wrapper (`.mantle_original`) so every hook is reversible (the rewrite-ledger rule).
"""
from __future__ import annotations

import functools
from typing import Any, Callable, Dict, List

from ..vcw.entry import make_entry
from ..core.redact import redact


class Assimilation:
    """The live hook runtime bound to one Organism. Every hook writes through the
    organism's organs; every hook is individually fail-open."""

    def __init__(self, organism: Any) -> None:
        self.org = organism
        self.ledger: List[Dict[str, Any]] = []     # the rewrite ledger (reversibility)

    # ---- the primitive hooks (each individually fail-open) -------------------
    def _safe(self, what: str, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception as e:                     # noqa: BLE001 -- HF-B32
            try:
                self.org.immune_event("hook_fault",
                                      {"hook": what, "error": type(e).__name__})
            except Exception:
                pass                               # immune logging itself is fail-open

    def mantle_sense(self, symbol: str, args: Any) -> None:
        """A SENSOR_EVENT fired: one classified, redacted senses entry."""
        self._safe("sense", lambda: self.org.senses.inhale(
            {"action_id": "host:" + symbol, "event_type": "host_event",
             "payload": redact(_brief(args))}))

    def mantle_external_call(self, symbol: str, ok: bool, reason: str = "ok") -> None:
        """An ARM_ACTION ran: dispatch + Action Execution Proof through Limbs."""
        self._safe("external_call", lambda: self.org.limbs._prove(
            "host:" + symbol, attempted=True, ok=ok, method="host-wrap",
            ref=symbol, reason=reason))

    def mantle_state_write(self, symbol: str, detail: Any) -> None:
        """A STATE_TRANSITION/PERSISTENCE_WRITE ran: mirror into the host_state band
        (or events if the app band is absent)."""
        band = "host_state" if "host_state" in self.org.prime.bands else "events"
        self._safe("state_write", lambda: self.org.prime.append(band, make_entry(
            redact({"symbol": symbol, "detail": _brief(detail)}),
            opcode="HOST_STATE", author="BODY", source="assimilator")))

    def mantle_error(self, symbol: str, exc: BaseException) -> None:
        """A host exception passed through: recorded, NEVER swallowed or re-raised by us."""
        self._safe("error", lambda: self.org.immune_event(
            "host_error", {"symbol": symbol, "error": type(exc).__name__}))

    # ---- the wrapper factory ---------------------------------------------------
    def wrap(self, role: str, fn: Callable, symbol: str = None) -> Callable:
        """Wrap one host callable according to its organ role. The host's behavior is
        preserved EXACTLY: same return value, same exceptions. Reversible via
        `.mantle_original`."""
        name = symbol or getattr(fn, "__qualname__", getattr(fn, "__name__", "host_fn"))

        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            if role in ("SENSOR_EVENT", "REFLEX"):
                self.mantle_sense(name, {"args": len(args), "kwargs": sorted(kwargs)})
            try:
                result = fn(*args, **kwargs)       # the host, unchanged
            except BaseException as e:
                if role in ("ARM_ACTION", "DISPLAY_RENDER"):
                    self.mantle_external_call(name, ok=False, reason=type(e).__name__)
                self.mantle_error(name, e)
                raise                              # host semantics preserved (HF-B40)
            if role in ("ARM_ACTION", "DISPLAY_RENDER"):
                self.mantle_external_call(name, ok=True)
            elif role in ("STATE_TRANSITION", "PERSISTENCE_WRITE"):
                self.mantle_state_write(name, {"args": len(args)})
            return result

        wrapped.mantle_original = fn               # the reversibility handle
        wrapped.mantle_role = role
        self.ledger.append({"symbol": name, "role": role,
                            "marker": "# MANTLE_HOOK_INSERTED", "reversible": True})
        return wrapped

    def unwrap(self, wrapped: Callable) -> Callable:
        """Reverse one hook: hand back the original callable, byte-for-byte behavior."""
        return getattr(wrapped, "mantle_original", wrapped)


def _brief(obj: Any, limit: int = 200) -> Any:
    s = repr(obj)
    return s if len(s) <= limit else s[:limit] + "..."
