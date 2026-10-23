#!/usr/bin/env python3
"""
mantle.organs.immune  --  the Immune System organ: defense & repair (Mantle OS)

The Immune System is EXISTENTIAL, not janitorial: the VCW is the organism's reality, so
protecting it is protecting the self. It is also the organism's ONLY failure boundary --
every dangling reference, integrity fault, organ overreach, stalled pulse, capacity
pressure, refused MIND write, or policy violation becomes an immune event here. Nothing
fails silently.

Reflexes (all deterministic, no LLM):
  event       record an immune event (REDACTED at the boundary) to the immune band + log
  scan        verify cube integrity (hashes, coherence, seals) on a heartbeat
  quarantine  isolate a suspect entry      tombstone   retire an obsolete entry
  redact      strip secrets from anything crossing a secret boundary
  is_self     SELF/OTHER recognition (M2): an artifact this Body can verify is SELF
  nociception (M1): a severe event emits a `distress` signal carrying the pain
              coordinates {reason, band, ref} -- the Heart turns it into an additional
              unscheduled pulse without replacing the natural cognitive baseline
"""
from __future__ import annotations

from typing import Any, Dict, List

from .contract import Organ, OrganContract
from ..vcw.entry import make_entry
from ..core.redact import redact

CONTRACT = OrganContract(
    "immune", "defense & repair -- the only failure boundary; protects the VCW (the self)",
    reads=["immune", "*"],
    writes=["immune"],
    reflexes=[
        {"name": "event", "trigger": "any violation/fault anywhere in the organism",
         "effect": "redact, append one immune entry, emit `immune` signal"},
        {"name": "scan", "trigger": "heartbeat (every scan_every beats)",
         "effect": "cube verify(): hashes, coherence, active/free overlap, seals"},
        {"name": "quarantine", "trigger": "a suspect entry", "effect": "isolate from reads"},
        {"name": "tombstone", "trigger": "an obsolete entry", "effect": "retire from reads"},
        {"name": "redact", "trigger": "any string crossing a secret boundary",
         "effect": "secrets are masked BEFORE they can burn into append-only memory"},
        {"name": "is_self", "trigger": "an artifact is checked for provenance",
         "effect": "SELF iff this Body's genesis key verifies it; else OTHER (rejected)"},
        {"name": "nociception", "trigger": "an event of autonomic severity",
         "effect": "emit a `distress` signal {reason, band, ref}: the pain coordinates"},
    ],
    phase1="active",
    phase2_extension="the MIND may PROPOSE immune actions; enforcement stays in the Body",
    audit=[
        "integrity scan runs on the heartbeat",
        "secrets never appear in senses/immune logs",
        "quarantined/tombstoned entries are hidden from normal reads",
        "every violation class becomes an immune event (no silent failure)",
        "SELF/OTHER: only artifacts this Body can sign verify as SELF; OTHER is rejected",
        "severe events emit distress (the unscheduled-pulse trigger), never silent",
    ],
)

# Events severe enough to add an unscheduled MIND pulse: nociception fires a `distress`
# signal for these. Routine/economic events (e.g. `starvation`, capacity pressure) are not
# autonomic interrupts; they do not add pulses or suppress the natural fused baseline.
AUTONOMIC_KINDS = frozenset({
    "integrity", "organ_overreach", "mind_write_refused", "foreign_rejected",
    "autoimmune_risk", "unresolved_ref", "ancestor_tamper", "flush_failed",
})


class Immune(Organ):
    contract = CONTRACT

    def __init__(self, organism) -> None:
        super().__init__(organism)
        self.log: List[Dict[str, Any]] = []     # the in-memory mirror (fast audit access)
        self.scans = 0

    # ---- the failure boundary ---------------------------------------------
    def event(self, kind: str, detail: Any) -> Dict[str, Any]:
        """Record one immune event. Redacts at the boundary; fail-open (immune logging
        must never crash the organism); emits an `immune` signal for subscribed reflexes."""
        evt = {"kind": kind, "detail": redact(detail)}
        self.log.append(evt)
        try:
            self.append("immune", make_entry(evt, opcode="IMMUNE", author="BODY"))
        except Exception:
            pass  # fail-open: a full/sick immune band degrades, never crashes
        try:
            self.bus.emit("immune", dict(evt))
        except Exception:
            pass
        # nociception (M1): a severe event is PAIN -- emit a localized distress signal so
        # the Heart can issue an unscheduled pulse with the stressor's coordinates. The
        # detail is already redacted; band/ref are extracted from it when present.
        if kind in AUTONOMIC_KINDS:
            self._nociceptor(kind, evt["detail"])
        return evt

    def _nociceptor(self, reason: str, detail: Any) -> None:
        """Translate a severe event into pain coordinates {reason, band, ref} and emit a
        `distress` signal. Fail-open: pain signalling never crashes the organism."""
        band = detail.get("band") if isinstance(detail, dict) else None
        ref = None
        if isinstance(detail, dict):
            ref = detail.get("ref")
            if ref is None and band is not None and detail.get("id") is not None:
                ref = "<%s.%s>" % (band, detail["id"])
        try:
            self.bus.emit("distress", {"reason": reason, "band": band, "ref": ref})
        except Exception:
            pass

    # ---- scan (the heartbeat integrity reflex) -----------------------------
    def scan(self) -> List[str]:
        """Verify the Prime cube; every problem becomes an immune event."""
        self.scans += 1
        problems = self.org.prime.verify()
        for p in problems:
            self.event("integrity", {"problem": p})
        return problems

    # ---- marks --------------------------------------------------------------
    def quarantine(self, band: str, entry_id: int) -> bool:
        ok = self.org.prime.quarantine(band, entry_id)
        self.event("quarantine", {"band": band, "id": entry_id, "ok": ok})
        return ok

    def tombstone(self, band: str, entry_id: int) -> bool:
        ok = self.org.prime.tombstone(band, entry_id)
        return ok

    # ---- the secret boundary -------------------------------------------------
    @staticmethod
    def redact(obj: Any) -> Any:
        return redact(obj)

    # ---- SELF / OTHER recognition (M2) --------------------------------------
    def is_self(self, data: bytes, mac: str) -> bool:
        """SELF iff this Body's genesis key verifies `mac` over `data`. An artifact made
        by another body (or forged) produces a different mac -> OTHER. This is the immune
        recognition boundary: only SELF is trusted; OTHER is quarantined, never executed."""
        return self.org.body.verify(data, mac)

    def reject_foreign(self, label: str, detail: Any = None) -> Dict[str, Any]:
        """Record that an OTHER artifact was refused. Severe by design (autonomic): a
        foreign artifact in the nest is a stressor the MIND should learn about."""
        return self.event("foreign_rejected", {"artifact": label, "detail": detail})
