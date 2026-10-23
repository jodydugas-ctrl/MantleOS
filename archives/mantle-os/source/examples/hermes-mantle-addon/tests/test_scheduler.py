"""Deterministic tests for the fused-resident cognitive scheduler."""

from __future__ import annotations

from pathlib import Path
import sys
from threading import Event
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.scheduler import CognitiveScheduler, NATURAL_HEARTBEAT_SECONDS


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class _Thread:
    def __init__(self, target, **_kwargs) -> None:
        self.target = target
        self.started = 0
        self.joined = 0

    def start(self) -> None:
        self.started += 1

    def join(self, _timeout=None) -> None:
        self.joined += 1

    def is_alive(self) -> bool:
        return False


class _StuckThread(_Thread):
    def is_alive(self) -> bool:
        return True


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = _Clock()
        self.pulses = []
        self.threads = []

        def thread_factory(**kwargs):
            thread = _Thread(**kwargs)
            self.threads.append(thread)
            return thread

        self.scheduler = CognitiveScheduler(
            self.pulses.append,
            clock=self.clock,
            thread_factory=thread_factory,
        )

    def tearDown(self) -> None:
        self.scheduler.stop()

    def test_exactly_one_scheduler_and_fixed_natural_deadline(self):
        self.assertEqual(600, NATURAL_HEARTBEAT_SECONDS)
        self.assertTrue(self.scheduler.start())
        self.assertFalse(self.scheduler.start())
        self.assertEqual(1, len(self.threads))
        self.assertEqual(1, self.threads[0].started)
        self.assertEqual(700.0, self.scheduler.next_deadline)

    def test_unscheduled_wake_does_not_replace_natural_baseline(self):
        self.scheduler.start()
        self.clock.now = 200.0
        self.assertTrue(self.scheduler.wake({"reason": "distress", "band": "immune"}))
        self.scheduler.poll()
        self.assertEqual([{"reason": "distress", "band": "immune"}], self.pulses)
        self.assertEqual(700.0, self.scheduler.next_deadline)

        self.clock.now = 700.0
        self.scheduler.poll()
        self.assertEqual(
            [{"reason": "distress", "band": "immune"}, None],
            self.pulses,
        )
        self.assertEqual(1300.0, self.scheduler.next_deadline)

    def test_unfused_scheduler_is_inert_and_stop_is_idempotent(self):
        self.assertFalse(self.scheduler.wake({"reason": "pain"}))
        self.clock.now = 10_000.0
        self.scheduler.poll()
        self.assertEqual([], self.pulses)
        self.assertFalse(self.scheduler.stop())

        self.scheduler.start()
        self.assertTrue(self.scheduler.stop())
        self.assertFalse(self.scheduler.stop())
        self.assertEqual(1, self.threads[0].joined)

    def test_stressor_queue_is_bounded_and_keeps_the_freshest_wakeups(self):
        self.scheduler.start()
        for index in range(20):
            self.assertTrue(self.scheduler.wake({"reason": str(index)}))

        self.assertEqual(16, self.scheduler.poll())
        self.assertEqual(
            [{"reason": str(index)} for index in range(4, 20)],
            self.pulses,
        )

    def test_stop_reports_a_thread_that_did_not_quiesce(self):
        scheduler = CognitiveScheduler(
            self.pulses.append,
            clock=self.clock,
            thread_factory=lambda **kwargs: _StuckThread(**kwargs),
        )
        scheduler.start()

        with self.assertRaisesRegex(RuntimeError, "did not stop"):
            scheduler.stop()

    def test_real_worker_processes_wake_and_quiesces(self):
        pulsed = Event()
        scheduler = CognitiveScheduler(lambda _stressor: pulsed.set())
        scheduler.start()

        self.assertTrue(scheduler.wake({"reason": "distress"}))
        self.assertTrue(pulsed.wait(1.0))
        self.assertTrue(scheduler.stop())
        self.assertFalse(scheduler.running)


if __name__ == "__main__":
    unittest.main()
