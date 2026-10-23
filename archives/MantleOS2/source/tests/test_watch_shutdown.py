"""Deterministic scheduling and shutdown boundaries, without a live MIND."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mantleos.runtime import MantleBody, MantleError


@pytest.fixture
def clock(monkeypatch):
    state = SimpleNamespace(now=0.0, stopped=False, sleeps=0, on_sleep=lambda: None)

    def sleep(duration):
        assert 0 < duration <= 0.1
        state.now += duration
        state.sleeps += 1
        assert state.sleeps < 1000, "watch failed to stop"
        state.on_sleep()

    monkeypatch.setattr("mantleos.runtime.time.monotonic", lambda: state.now)
    monkeypatch.setattr("mantleos.runtime.time.sleep", sleep)
    return state


def body_fixture():
    path = Mock()
    path.stat.return_value = SimpleNamespace(st_mtime_ns=1, st_size=10)
    return SimpleNamespace(
        is_born=True, paths=SimpleNamespace(communication=path),
        heartbeat=Mock(), recover_host_heartbeats=Mock(), _ensure_communication_file=Mock(),
    )


def reasons(body):
    return [call.kwargs["reason"] for call in body.heartbeat.call_args_list]


def test_stop_before_start_does_not_recover_or_start_heartbeat(clock):
    body = body_fixture()
    MantleBody.watch(body, stop_requested=lambda: True)
    body.heartbeat.assert_not_called()
    body.recover_host_heartbeats.assert_not_called()
    body._ensure_communication_file.assert_not_called()


def test_stop_while_idle_does_not_start_pending_message_or_scheduled_beat(clock):
    body = body_fixture()

    def stop():
        clock.stopped = True
        body.paths.communication.stat.return_value = SimpleNamespace(st_mtime_ns=2, st_size=20)

    clock.on_sleep = stop
    MantleBody.watch(body, interval=0.05, heartbeat_interval=0.05, stop_requested=lambda: clock.stopped)
    assert reasons(body) == ["resident-startup"]
    assert clock.sleeps == 1
    assert body.paths.communication.stat.call_count == 1


def test_long_observation_cadence_does_not_delay_idle_stop(clock):
    body = body_fixture()
    clock.on_sleep = lambda: setattr(clock, "stopped", True)
    MantleBody.watch(body, interval=3600, heartbeat_interval=3600, stop_requested=lambda: clock.stopped)
    assert clock.now == pytest.approx(0.1)
    assert reasons(body) == ["resident-startup"]


def test_stop_during_full_beat_allows_completion_but_no_followup(clock):
    body = body_fixture()
    stages = []

    def heartbeat(*, reason):
        stages.append((reason, "started"))
        clock.stopped = True
        stages.append((reason, "completed"))

    body.heartbeat.side_effect = heartbeat
    MantleBody.watch(body, stop_requested=lambda: clock.stopped)
    assert stages == [("resident-startup", "started"), ("resident-startup", "completed")]
    assert clock.sleeps == 0


def test_signal_does_not_turn_failed_beat_into_clean_completion(clock):
    body = body_fixture()

    def failed(**_kwargs):
        clock.stopped = True
        raise MantleError("checkpoint failed")

    body.heartbeat.side_effect = failed
    with pytest.raises(MantleError, match="checkpoint failed"):
        MantleBody.watch(body, stop_requested=lambda: clock.stopped)
    assert reasons(body) == ["resident-startup"]


@pytest.mark.parametrize("unavailable", [FileNotFoundError(), PermissionError()])
def test_missing_or_unreadable_communication_does_not_starve_schedule(clock, unavailable):
    body = body_fixture()
    initial = body.paths.communication.stat.return_value
    body.paths.communication.stat.side_effect = [initial, unavailable, unavailable]
    body.heartbeat.side_effect = lambda **kw: setattr(clock, "stopped", kw["reason"] == "resident-scheduled")
    MantleBody.watch(body, interval=0.1, heartbeat_interval=0.1, stop_requested=lambda: clock.stopped)
    assert reasons(body) == ["resident-startup", "resident-scheduled"]


def test_communication_response_is_not_echoed_as_new_wake(clock):
    body = body_fixture()
    changed = SimpleNamespace(st_mtime_ns=2, st_size=20)
    response = SimpleNamespace(st_mtime_ns=3, st_size=30)

    def event():
        if clock.sleeps == 1:
            body.paths.communication.stat.return_value = changed
        if clock.sleeps == 3:
            clock.stopped = True

    def heartbeat(**kw):
        if kw["reason"] == "communication-file-save":
            body.paths.communication.stat.return_value = response

    clock.on_sleep = event
    body.heartbeat.side_effect = heartbeat
    MantleBody.watch(body, interval=0.05, heartbeat_interval=0.1, stop_requested=lambda: clock.stopped)
    assert reasons(body) == ["resident-startup", "communication-file-save"]


def test_due_schedule_wins_simultaneous_file_change(clock):
    body = body_fixture()
    clock.on_sleep = lambda: setattr(
        body.paths.communication.stat, "return_value", SimpleNamespace(st_mtime_ns=2, st_size=20)
    )
    body.heartbeat.side_effect = lambda **kw: setattr(clock, "stopped", kw["reason"] != "resident-startup")
    MantleBody.watch(body, interval=0.1, heartbeat_interval=0.1, stop_requested=lambda: clock.stopped)
    assert reasons(body) == ["resident-startup", "resident-scheduled"]


def test_short_idle_slices_preserve_file_observation_cadence(clock):
    body = body_fixture()
    clock.on_sleep = lambda: setattr(clock, "stopped", clock.sleeps >= 6)
    MantleBody.watch(body, interval=10, heartbeat_interval=20, stop_requested=lambda: clock.stopped)
    assert body.paths.communication.stat.call_count == 1


def test_startup_response_does_not_cause_a_second_wake(clock):
    body = body_fixture()
    body.heartbeat.side_effect = lambda **_kw: setattr(
        body.paths.communication.stat, "return_value", SimpleNamespace(st_mtime_ns=2, st_size=20)
    )
    clock.on_sleep = lambda: setattr(clock, "stopped", clock.sleeps >= 3)
    MantleBody.watch(body, interval=0.05, heartbeat_interval=300, stop_requested=lambda: clock.stopped)
    assert reasons(body) == ["resident-startup"]


@pytest.mark.parametrize("invalid", [0, -1, float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["interval", "heartbeat_interval"])
def test_invalid_cadences_refuse_before_any_heartbeat(clock, field, invalid):
    body = body_fixture()
    with pytest.raises(MantleError, match="finite and positive"):
        MantleBody.watch(body, **{field: invalid})
    body.heartbeat.assert_not_called()
