"""One lifecycle-owned cognitive cadence per fused resident."""

from __future__ import annotations

from collections import deque
from threading import Event, RLock, Thread
import time
from typing import Any, Callable

NATURAL_HEARTBEAT_SECONDS = 600


class CognitiveScheduler:
    """Drive cognition every ten minutes plus queued stressor wakeups."""

    def __init__(
        self,
        pulse: Callable[[dict[str, Any] | None], None],
        *,
        clock: Callable[[], float] = time.monotonic,
        thread_factory: Callable[..., Any] = Thread,
    ) -> None:
        self._pulse = pulse
        self._clock = clock
        self._thread_factory = thread_factory
        self._lock = RLock()
        self._changed = Event()
        self._wakes: deque[dict[str, Any]] = deque(maxlen=16)
        self._thread: Any | None = None
        self._running = False
        self._next_deadline: float | None = None
        self.last_error_type = ""

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def next_deadline(self) -> float | None:
        with self._lock:
            return self._next_deadline

    def start(self) -> bool:
        """Start once; duplicate starts leave the existing cadence untouched."""
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._next_deadline = self._clock() + NATURAL_HEARTBEAT_SECONDS
            self._thread = self._thread_factory(
                target=self._run,
                name="mantle-cognitive-heartbeat",
                daemon=True,
            )
            thread = self._thread
        thread.start()
        return True

    def stop(self) -> bool:
        """Stop idempotently without executing a final cognitive pulse."""
        with self._lock:
            if not self._running:
                return False
            self._running = False
            thread = self._thread
            self._thread = None
            self._next_deadline = None
            self._wakes.clear()
            self._changed.set()
        if thread is not None:
            thread.join(2.0)
            is_alive = getattr(thread, "is_alive", None)
            if callable(is_alive) and is_alive():
                raise RuntimeError("cognitive scheduler thread did not stop")
        return True

    def wake(self, stressor: dict[str, Any]) -> bool:
        """Queue one additional wake; never alter the natural deadline."""
        if not isinstance(stressor, dict):
            raise TypeError("stressor must be a mapping")
        with self._lock:
            if not self._running:
                return False
            self._wakes.append(dict(stressor))
            self._changed.set()
            return True

    def poll(self) -> int:
        """Run currently due work once. Public for deterministic supervision/tests."""
        with self._lock:
            if not self._running or self._next_deadline is None:
                return 0
            now = self._clock()
            pending = list(self._wakes)
            self._wakes.clear()
            if now >= self._next_deadline:
                pending.append(None)
                skipped = int((now - self._next_deadline) // NATURAL_HEARTBEAT_SECONDS)
                self._next_deadline += (skipped + 1) * NATURAL_HEARTBEAT_SECONDS
        for stressor in pending:
            try:
                self._pulse(stressor)
            except Exception as exc:
                self.last_error_type = type(exc).__name__
        return len(pending)

    def _run(self) -> None:
        while True:
            with self._lock:
                if not self._running or self._next_deadline is None:
                    return
                timeout = max(0.0, self._next_deadline - self._clock())
            self._changed.wait(timeout)
            self._changed.clear()
            self.poll()
