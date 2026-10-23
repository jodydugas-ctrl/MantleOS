#!/usr/bin/env python3
"""
mantle.organs.heart  --  the Heart organ: clock, heartbeat, circulation (Mantle OS)

The Heart is the only organ whose Phase-1 state is unconditionally ACTIVE: the Body has a
heartbeat with NO brain. Each pulse is a complete moment of awareness, in a fixed,
deterministic order (the organism's native tempo):

    1. tick                 advance the clock; emit `pulse` on the bus
    2. sense intake         Senses drains its inbox (all inbound enters here)
    3. context assembly     the Nervous System materializes the whole-at-once snapshot
    4. reflex execution     bus subscribers fire (registration order, fail-open)
    5. immune scan          the Immune System verifies the cube (every scan_every beats)
    6. checkpoint           circulate: flush dirty state durably (staged atomic commit)

Phase 2 extension: every natural pulse offers the assembled snapshot to the fused Brain
(cognition) -- an extension of the reflex, never a replacement. The natural cadence is
ten minutes (600 seconds). In Phase 1 the Brain slot is empty and the identical loop runs
whole. Nothing here imports a model.

NOCICEPTION (M1): pain, SIGNIFICANT input, distress, and scheduled work add stressor-
anchored wakeups; they never suppress or replace the unconditional natural baseline.
The snapshot is pre-anchored to {reason, band, ref} when a stressor exists.
"""
from __future__ import annotations

import atexit
from typing import Any, Callable, Dict, List, Optional

from .contract import Organ, OrganContract

NATURAL_HEARTBEAT_SECONDS = 600

CONTRACT = OrganContract(
    "heart", "circulation & pulse -- the clock that drives every periodic Body reflex",
    reads=[],
    writes=[],          # the Heart drives; it owns no band (its faults go to Immune)
    reflexes=[
        {"name": "tick", "trigger": "each beat", "effect": "advance the clock; emit `pulse`"},
        {"name": "pulse-check", "trigger": "each beat",
         "effect": "a stalled heartbeat becomes an immune event, never swallowed"},
        {"name": "circulate", "trigger": "each beat / checkpoint / atexit",
         "effect": "flush dirty state durably via the staged-commit sink (fail-open)"},
        {"name": "dual-flush", "trigger": "install",
         "effect": "persist on BOTH explicit checkpoint AND an atexit handler"},
        {"name": "schedule-pulse", "trigger": "the organism plans ahead",
         "effect": "annotate a FUTURE cognition beat (countdown/at); baseline continues"},
        {"name": "schedule-consolidation", "trigger": "the operator requests sleep",
         "effect": "schedule one future Body-governed memory consolidation pulse"},
    ],
    phase1="active",
    phase2_extension="every ten-minute natural pulse offers the snapshot to cognition; "
                     "pain / SIGNIFICANT / distress add stressor-anchored wakeups",
    audit=[
        "heartbeat runs without an LLM (cognition slot empty in Phase 1)",
        "pulse order is fixed: tick, intake, assembly, reflexes, scan, checkpoint",
        "dual-flush persists on checkpoint and atexit",
        "a missed pulse is logged, never swallowed",
        "a calm fused organism calls the MIND on every natural heartbeat",
        "a severe event fires exactly one unscheduled pulse anchored to the stressor",
        "a scheduled pulse wakes cognition on the due beat and not before (one-shot)",
    ],
)


class Heart(Organ):
    contract = CONTRACT

    def __init__(self, organism, circulate: Optional[Callable[[], None]] = None,
                 scan_every: int = 4,
                 natural_interval_seconds: int = NATURAL_HEARTBEAT_SECONDS) -> None:
        super().__init__(organism)
        self._circulate_cb = circulate          # the durable sink (e.g. Organism.save)
        self.scan_every = max(1, int(scan_every))
        self.natural_interval_seconds = max(1, int(natural_interval_seconds))
        self.beats = 0
        self.last_beat = 0
        self.flushes = 0
        self._atexit_installed = False
        self._wake: Optional[Dict[str, Any]] = None   # pending pain coordinates (M1)
        self._schedule: List[Dict[str, Any]] = []     # planned future wakes (scheduling)

    def set_circulate(self, sink: Optional[Callable[[], None]]) -> None:
        self._circulate_cb = sink

    # ---- nociception: what wakes the MIND (M1) ----------------------------
    def on_significant(self, payload: Dict[str, Any]) -> None:
        """A SIGNIFICANT signal (unrecognized input) is a reason to think. Wired to the
        `significant` bus signal Senses emits."""
        self._wake = {"reason": "significant", "band": "senses", "ref": None,
                      "action_id": payload.get("action_id"),
                      "event_type": payload.get("event_type")}

    def on_distress(self, payload: Dict[str, Any]) -> None:
        """A severe immune event is PAIN. Wired to the Immune System's `distress` signal;
        carries the stressor's coordinates so the woken MIND knows where it hurts."""
        self._wake = {"reason": payload.get("reason"), "band": payload.get("band"),
                      "ref": payload.get("ref")}

    def pain(self, reason: str, band: Optional[str] = None,
             ref: Optional[str] = None) -> Dict[str, Any]:
        """The interrupt vector: issue an UNSCHEDULED pulse that wakes the MIND now,
        carrying the pain coordinates. Used when the Body cannot resolve a stressor with
        its own reflexes and must escalate to cognition."""
        return self.beat(assemble=True,
                         wake={"reason": reason, "band": band, "ref": ref})

    # ---- planning ahead: schedule a FUTURE wake (the scheduling command) ----
    def schedule_pulse(self, reason: str = "scheduled", after: Optional[int] = None,
                       at: Optional[int] = None, band: Optional[str] = None,
                       ref: Optional[str] = None) -> int:
        """Plan ahead. Ask the Body to WAKE cognition on a FUTURE beat -- a COUNTDOWN
        (`after=N` beats from now) or a scheduled beat (`at=K`). This is how an AppAI
        CHAINS THOUGHTS: if it must process something later, it schedules a stressor marker
        for that beat. Baseline cognition continues meanwhile. The due beat carries
        `scheduled: True` through the same anchored path as nociception.
        Returns the beat the pulse will fire on. `pain` is the NOW version of this; this is
        the LATER version."""
        if after is not None:
            due = self.beats + max(1, int(after))
        elif at is not None:
            due = max(self.beats + 1, int(at))          # always strictly in the future
        else:
            due = self.beats + 1
        self._schedule.append({"due": due, "reason": reason, "band": band, "ref": ref})
        return due

    def schedule_consolidation(self, after: Optional[int] = None,
                               at: Optional[int] = None) -> int:
        return self.schedule_pulse(reason="memory_consolidation", after=after, at=at,
                                   band="discoveries", ref=None)

    def scheduled(self) -> List[Dict[str, Any]]:
        """The pending planning queue: future wakes not yet fired."""
        return list(self._schedule)

    def cancel_pulse(self, reason: Optional[str] = None) -> int:
        """Cancel pending scheduled wakes -- all of them, or just those matching `reason`.
        Returns how many were removed (plans change)."""
        before = len(self._schedule)
        if reason is None:
            self._schedule = []
        else:
            self._schedule = [s for s in self._schedule if s.get("reason") != reason]
        return before - len(self._schedule)

    def _fire_due_schedules(self) -> Optional[Dict[str, Any]]:
        """Pop any scheduled wakes that have come due (due beat <= now) and return one wake
        dict for them (or None). Deterministic: planning is in beats, the organism's native
        unit of time."""
        if not self._schedule:
            return None
        due = [s for s in self._schedule if s["due"] <= self.beats]
        if not due:
            return None
        self._schedule = [s for s in self._schedule if s["due"] > self.beats]
        s = due[-1]
        return {"reason": s["reason"], "band": s.get("band"), "ref": s.get("ref"),
                "scheduled": True, "fired_at": self.beats}

    # ---- reflexes ---------------------------------------------------------
    def tick(self) -> int:
        self.beats += 1
        return self.beats

    def pulse_check(self) -> bool:
        """A missed pulse is logged as an immune event, never swallowed."""
        if self.beats <= self.last_beat:
            self.org.immune_event("stalled_pulse",
                                  {"beats": self.beats, "last": self.last_beat})
            return False
        self.last_beat = self.beats
        return True

    def circulate(self) -> int:
        """Flush dirty state durably. The injected sink performs the staged commit; a
        missing sink is a no-op (a headless Body still has a heartbeat). Fail-open."""
        try:
            if self._circulate_cb is not None:
                self._circulate_cb()
        except Exception:                        # a sick flush degrades, never crashes
            self.org.immune_event("flush_failed", {"organ": "heart"})
        self.flushes += 1
        return self.flushes

    # ---- the pulse ---------------------------------------------------------
    def body_pulse(self, assemble: bool = False) -> Dict[str, Any]:
        """Run Body circulation for a host event without consuming cognition cadence.

        A fused resident may observe many host events between natural heartbeats. Those
        events keep the autonomic Body current but never invoke the MIND. Any stressor
        discovered here remains pending for the lifecycle-owned scheduler to escalate.
        """
        return self._pulse(assemble=assemble, cognitive=False)

    def beat(self, assemble: bool = False,
             wake: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run one natural or stressor-driven pulse, including fused cognition."""
        return self._pulse(assemble=assemble, wake=wake, cognitive=True)

    def _pulse(self, assemble: bool = False,
               wake: Optional[Dict[str, Any]] = None,
               cognitive: bool = True) -> Dict[str, Any]:
        """Execute the fixed Body order and optionally extend it with cognition."""
        report: Dict[str, Any] = {"beat": self.tick()}
        if wake is not None:
            self._wake = dict(wake)
        if cognitive:
            due = self._fire_due_schedules()    # scheduled cognition comes due naturally
            if due is not None:
                report["scheduled_wake"] = due
                if self._wake is None:          # a live stressor takes precedence
                    self._wake = due
        self.bus.emit("pulse", {"beat": self.beats})                    # 1 tick
        report["ok"] = self.pulse_check()
        report["intake"] = self.org.senses.drain()                      # 2 sense intake
        #                                          (SIGNIFICANT -> on_significant -> _wake)
        snapshot = None
        fused = self.org.brain.fused
        if assemble or (fused and cognitive):
            snapshot = self.org.nervous.assemble()                      # 3 context assembly
            report["assembled"] = snapshot.get("_complete", False)
        # 4 reflex execution: bus subscribers fired during emit (registration order)
        if self.beats % self.scan_every == 0:
            report["scan_problems"] = len(self.org.immune.scan())       # 5 immune scan
            #                                  (integrity etc. -> distress -> on_distress)
        report["flushes"] = self.circulate()                            # 6 checkpoint
        if self._wake is not None:                            # additional wake metadata
            report["wake"] = self._wake          # observable even with no fused Brain
            if snapshot is not None:
                snapshot["_stressor"] = self._wake  # pre-anchor to the pain coordinates
        if fused and cognitive:                               # unconditional P2 baseline
            report["cognition"] = self.org.brain.cognize(snapshot)
        if cognitive:
            self._wake = None                          # cognition consumed the wake
        self.bus.emit("checkpoint", {"beat": self.beats})
        return report

    def run(self, beats: int, assemble: bool = False) -> int:
        for _ in range(beats):
            self.beat(assemble=assemble)
        return self.beats

    # ---- dual-flush (durability) -----------------------------------------
    def install_dual_flush(self) -> bool:
        """Persist on BOTH an explicit checkpoint AND an atexit handler, so a cube is
        never lost to an ungraceful shutdown."""
        if not self._atexit_installed:
            atexit.register(self._safe_flush)
            self._atexit_installed = True
        return self._atexit_installed

    def _safe_flush(self) -> None:
        try:                                     # atexit must never raise on the way down
            self.circulate()
        except Exception:
            pass
