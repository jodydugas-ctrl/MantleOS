#!/usr/bin/env python3
"""The resident cognitive heartbeat -- the Body's own tempo, generalized.

Doctrine (corrections log 90-91): a fused resident Body owns **exactly one** natural
cognitive heartbeat scheduler. Unscheduled wakes -- user submits, Senses `significant`,
reflex events, Immune distress -- ride on top of that cadence so conversation never waits
for the next natural tick, but they **never move the natural deadline**. Every pulse makes
at most one MIND/provider call and writes a `HEARTBEAT_PULSE` receipt into Prime VCW.

This module owns the *rhythm* only. It does not know what a pulse does, how to reach a
provider, or how to write VCW -- the resident injects those:

    hb = ResidentHeartbeat(pulse=my_pulse, marker=my_marker)
    hb.start()
    hb.wake({"reason": "user_submit", "band": "senses"})

`pulse(wake, *, drift_seconds, source, forced)` performs one beat and is responsible for
the single provider call and the `HEARTBEAT_PULSE` write (see
`mantle.resident.protocol.heartbeat_pulse_event` for the receipt shape).
`marker(kind, message, **fields)` records lifecycle and failure events; it is optional and
failures inside it are swallowed -- a broken sidecar must never stop the heart.

A pulse that raises is recorded and dropped. The heart does not stop because one beat
failed; that is an immune concern, not a scheduling one.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

# The natural cadence. Ten minutes. Doctrine, not preference.
NATURAL_INTERVAL_SECONDS = 600

# Stressors are bounded: a storm of events must not become a storm of provider calls.
DEFAULT_QUEUE_LIMIT = 32

PulseFn = Callable[..., Any]
MarkerFn = Callable[..., Any]


class ResidentHeartbeat:
    """One natural cadence, plus a bounded queue of unscheduled wakes."""

    def __init__(self,
                 pulse: PulseFn,
                 *,
                 marker: Optional[MarkerFn] = None,
                 interval_seconds: int = NATURAL_INTERVAL_SECONDS,
                 queue_limit: int = DEFAULT_QUEUE_LIMIT,
                 name: str = "resident-heartbeat",
                 clock: Callable[[], float] = time.monotonic) -> None:
        if interval_seconds <= 0:
            raise ValueError("heartbeat interval must be positive")
        if queue_limit <= 0:
            raise ValueError("stressor queue limit must be positive")
        self._pulse = pulse
        self._marker = marker
        self.interval_seconds = int(interval_seconds)
        self.queue_limit = int(queue_limit)
        self.name = name
        self._clock = clock
        self._lock = threading.RLock()
        self._changed = threading.Event()
        self._wakes: List[Dict[str, Any]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._next_deadline: Optional[float] = None
        self._beats = 0
        self._dropped_wakes = 0
        self.last_error_type = ""

    # -- observation ---------------------------------------------------------
    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def beats(self) -> int:
        """Pulses successfully delivered since start."""
        with self._lock:
            return self._beats

    @property
    def dropped_wakes(self) -> int:
        """Stressors discarded because the bounded queue was full."""
        with self._lock:
            return self._dropped_wakes

    @property
    def seconds_until_next(self) -> Optional[float]:
        with self._lock:
            if self._next_deadline is None:
                return None
            return max(0.0, self._next_deadline - self._clock())

    @property
    def pending_wakes(self) -> int:
        with self._lock:
            return len(self._wakes)

    def status(self) -> Dict[str, Any]:
        """The shape a resident `/heartbeat` command reports. Prime VCW remains truth."""
        with self._lock:
            return {
                "running": self._running,
                "interval_seconds": self.interval_seconds,
                "beats": self._beats,
                "pending_wakes": len(self._wakes),
                "dropped_wakes": self._dropped_wakes,
                "seconds_until_next": (
                    None if self._next_deadline is None
                    else max(0.0, self._next_deadline - self._clock())
                ),
                "last_error_type": self.last_error_type,
                "canonical_source": "prime_vcw",
            }

    # -- lifecycle -----------------------------------------------------------
    def start(self, *, thread: bool = True) -> bool:
        """Begin the cadence. `thread=False` gives a poll-driven heart for tests and
        for hosts that already own an event loop."""
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._next_deadline = self._clock() + self.interval_seconds
            self._changed.clear()
            worker = None
            if thread:
                self._thread = threading.Thread(target=self._run, name=self.name, daemon=True)
                worker = self._thread
        self._record("heartbeat_started", "heartbeat scheduler started",
                     commit_boundary="open", interval_seconds=self.interval_seconds)
        if worker is not None:
            worker.start()
        return True

    def stop(self) -> bool:
        with self._lock:
            if not self._running:
                return False
            self._running = False
            self._wakes.clear()
            self._changed.set()
            worker = self._thread
            self._thread = None
            self._next_deadline = None
        if worker is not None and worker is not threading.current_thread():
            worker.join(2.0)
        self._record("heartbeat_stopped", "heartbeat scheduler stopped", commit_boundary="close")
        return True

    # -- wakes ---------------------------------------------------------------
    def wake(self, stressor: Dict[str, Any]) -> bool:
        """Queue an unscheduled wake. Does NOT move the natural deadline."""
        with self._lock:
            if not self._running:
                return False
            self._wakes.append(dict(stressor))
            if len(self._wakes) > self.queue_limit:
                overflow = len(self._wakes) - self.queue_limit
                self._wakes = self._wakes[-self.queue_limit:]
                self._dropped_wakes += overflow
            self._changed.set()
            return True

    def pulse_now(self, stressor: Optional[Dict[str, Any]] = None) -> Any:
        """An operator-forced beat. Also leaves the natural deadline untouched."""
        return self._pulse(stressor, drift_seconds=None, source="manual-heartbeat", forced=True)

    # -- the beat ------------------------------------------------------------
    def poll(self) -> int:
        """Deliver every due beat. Returns how many pulses were delivered.

        A natural tick that is several intervals overdue produces exactly ONE pulse and
        realigns the deadline -- missed beats do not stack into a provider storm.
        """
        with self._lock:
            if not self._running or self._next_deadline is None:
                return 0
            now = self._clock()
            pending: List[Optional[Dict[str, Any]]] = list(self._wakes)
            self._wakes.clear()
            due_deadline = self._next_deadline
            natural_due = now >= self._next_deadline
            if natural_due:
                pending.append(None)
                skipped = int((now - self._next_deadline) // self.interval_seconds)
                self._next_deadline += (skipped + 1) * self.interval_seconds
        delivered = 0
        for wake in pending:
            natural = wake is None and natural_due
            drift = round(self._clock() - due_deadline, 3) if natural else None
            try:
                self._pulse(wake, drift_seconds=drift,
                            source="scheduler", forced=False)
            except Exception as exc:  # noqa: BLE001 -- a failed beat is recorded, never raised
                self.last_error_type = type(exc).__name__
                self._record("heartbeat_pulse", str(exc), commit_boundary="heartbeat",
                             provider_ok=False, provider_error=str(exc)[:500],
                             wake_type="error")
                continue
            delivered += 1
            with self._lock:
                self._beats += 1
        return delivered

    def _run(self) -> None:
        while True:
            with self._lock:
                if not self._running or self._next_deadline is None:
                    return
                timeout = max(0.0, self._next_deadline - self._clock())
            self._changed.wait(timeout)
            self._changed.clear()
            self.poll()

    # -- sidecar -------------------------------------------------------------
    def _record(self, kind: str, message: str, **fields: Any) -> None:
        if self._marker is None:
            return
        try:
            self._marker(kind, message, **fields)
        except Exception:  # noqa: BLE001 -- sidecar failure must never stop the heart
            pass


__all__ = ["ResidentHeartbeat", "NATURAL_INTERVAL_SECONDS", "DEFAULT_QUEUE_LIMIT"]
