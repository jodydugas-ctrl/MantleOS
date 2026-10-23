#!/usr/bin/env python3
"""
mantle.ganglia  --  parallel limbs that think into the VCW (Mantle OS · M7)

The octopus runs much of its cognition in its ARMS: each arm's ganglion acts semi-
independently and reports back. A Ganglion here is a bounded limb that runs a task and
writes its PROGRESS into a reserved VCW band. The parent does not talk to the sub-task
directly -- it reads the progress *as memory*. The sub-task's thoughts are the organism's
thoughts (they are in the VCW), so the parent observes them with ZERO model calls:
zero-token telemetry.

Fail-open like every limb: a crashed ganglion becomes an immune event, never a parent
crash. The progress band obeys the veil and the contracts like any other band.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List

from .vcw.bands import make_band_boot
from .vcw.entry import make_entry
from .core.redact import redact


def ganglion_band(name: str, head: int, span: int = 4, private: bool = False) -> Dict[str, Any]:
    """A reserved band for one ganglion's progress telemetry."""
    return make_band_boot(name, head, "log-json", span=span, private=private,
                          purpose="ganglion progress (zero-token telemetry)")


class Ganglion:
    """A bounded parallel limb. `run(task)` executes `task(report, *args)` -- where the
    task calls `report(payload)` to write progress into the reserved band -- in its own
    thread, then joins. A fault inside the task is an immune event; the parent never sees
    the exception. The parent reads `progress()` with no model call."""

    def __init__(self, organism: Any, band: str) -> None:
        self.org = organism
        self.band = band
        self._thread: Any = None

    def _report(self, payload: Any) -> None:
        """The task's hand into the VCW: one redacted progress entry. Fail-open."""
        try:
            self.org.prime.append(self.band, make_entry(
                redact(payload), opcode="PROGRESS", author="BODY", source="ganglion"))
        except Exception:
            pass                                   # telemetry must never crash the task

    def run(self, task: Callable[..., Any], *args: Any, parallel: bool = True) -> "Ganglion":
        """Start the task. With `parallel=True` it runs in a thread the parent can join;
        either way a fault degrades to an immune event (fail-open)."""
        def _body():
            try:
                task(self._report, *args)
            except Exception as e:                 # noqa: BLE001 -- a ganglion is fail-open
                self.org.immune_event("ganglion_fault",
                                      {"band": self.band, "error": type(e).__name__})

        if parallel:
            self._thread = threading.Thread(target=_body, daemon=True)
            self._thread.start()
        else:
            _body()
        return self

    def join(self, timeout: float = 5.0) -> "Ganglion":
        if self._thread is not None:
            self._thread.join(timeout)
        return self

    def progress(self) -> List[Dict[str, Any]]:
        """The parent's view of the sub-task -- read as memory, no model call."""
        return self.org.prime.read(self.band, reveal_private=True)
