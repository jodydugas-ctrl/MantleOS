from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from organize import Config
from organize.mantle_appai.events import (
    CompositeSink,
    JSONLSink,
    MantleSink,
    MemorySink,
    NoOpSink,
    TraceSession,
)
from organize.output import SavingOutput


def test_event_schema_ordering_and_redaction(tmp_path: Path):
    sink = MemorySink()
    trace = TraceSession(
        sink,
        simulation=True,
        privacy_root=tmp_path,
        run_id="run-1",
        clock=lambda: datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    trace.emit(
        stage="filter_evaluation",
        component_type="filter",
        component_name="name",
        outcome="matched",
        reason_code="filter_matched",
        explanation="token=super-secret-value",
        resource_path=tmp_path / "inbox" / "item.txt",
        evidence={
            "api_key": "never-store-this",
            "filecontent": {"invoice": "private extracted text"},
            "absolute_path_string": str(tmp_path / "inbox" / "item.txt"),
            "value": "safe",
        },
    )
    trace.emit(
        stage="action_planning",
        component_type="action",
        component_name="echo",
        outcome="planned",
        reason_code="action_planned",
        explanation="safe",
    )

    assert [event.sequence for event in sink.events] == [1, 2]
    assert sink.events[0].resource_path == "inbox/item.txt"
    assert sink.events[0].evidence["api_key"] == "<redacted>"
    assert sink.events[0].evidence["filecontent"] == "<redacted:file-content>"
    assert sink.events[0].evidence["absolute_path_string"] == "inbox/item.txt"
    assert "super-secret-value" not in sink.events[0].explanation
    assert sink.events[0].timestamp == "2025-01-01T00:00:00Z"


def test_disabled_tracing_does_not_build_events():
    trace = TraceSession(NoOpSink(), simulation=True)
    assert (
        trace.emit(
            stage="x",
            component_type="x",
            component_name="x",
            outcome="entered",
            reason_code="x",
            explanation="x",
        )
        is None
    )
    assert trace.sequence == 0


def test_jsonl_sink(tmp_path: Path):
    path = tmp_path / "trace.jsonl"
    trace = TraceSession(JSONLSink(path), simulation=True, run_id="jsonl")
    trace.emit(
        stage="configuration",
        component_type="config",
        component_name="config",
        outcome="entered",
        reason_code="loaded",
        explanation="loaded",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "jsonl"
    assert payload["sequence"] == 1


def test_host_pipeline_event_order(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "invoice.txt").write_text("synthetic", encoding="utf-8")
    config = Config.from_string(
        f"""
        rules:
          - name: invoices
            locations: [{inbox.as_posix()}]
            filters:
              - extension: txt
              - name: {{contains: invoice}}
            actions:
              - echo: matched
        """
    )
    sink = MemorySink()
    trace = TraceSession(sink, simulation=True, privacy_root=tmp_path)
    config.execute(
        simulate=True, output=SavingOutput(), working_dir=tmp_path, trace=trace
    )
    stages = [event.stage for event in sink.events]
    assert stages.index("rule_selection") < stages.index("target_selection")
    assert stages.index("target_selection") < stages.index("filter_evaluation")
    assert stages.index("filter_pipeline") < stages.index("action_planning")
    assert [event.sequence for event in sink.events] == list(
        range(1, len(sink.events) + 1)
    )


def test_sink_failure_is_fail_open(tmp_path: Path):
    class BrokenSink:
        enabled = True

        def emit(self, event):
            raise OSError("unavailable")

    config = Config.from_string("rules:\n  - actions:\n      - echo: ok\n")
    trace = TraceSession(BrokenSink(), simulation=True, privacy_root=tmp_path)
    config.execute(
        simulate=True, output=SavingOutput(), working_dir=tmp_path, trace=trace
    )


def test_composite_sink_failure_does_not_starve_later_sink():
    class BrokenSink:
        enabled = True

        def emit(self, event):
            raise OSError("unavailable")

    memory = MemorySink()
    trace = TraceSession(CompositeSink([BrokenSink(), memory]), simulation=True)
    trace.emit(
        stage="configuration",
        component_type="config",
        component_name="config",
        outcome="entered",
        reason_code="loaded",
        explanation="loaded",
    )
    assert len(memory.events) == 1


def test_mantle_sink_buffers_until_explicit_flush():
    class Bridge:
        def __init__(self):
            self.calls = []

        def remember_events(self, events, *, verified_simulation):
            batch = list(events)
            self.calls.append((batch, verified_simulation))
            return len(batch)

    bridge = Bridge()
    sink = MantleSink(bridge, verified_simulation=True)
    trace = TraceSession(sink, simulation=True, run_id="mantle-buffer")
    trace.emit(
        stage="action_execution",
        component_type="action",
        component_name="echo",
        outcome="executed",
        reason_code="action_executed",
        explanation="done",
    )
    assert bridge.calls == []
    assert sink.flush() == 1
    assert bridge.calls[0][1] is True
    assert sink.events == []
