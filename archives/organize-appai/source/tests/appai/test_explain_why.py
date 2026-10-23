from __future__ import annotations

from pathlib import Path

from organize import Config
from organize.mantle_appai.events import JSONLSink, MemorySink, TraceSession
from organize.mantle_appai.explain import explain_config
from organize.mantle_appai.why import diagnose_path, diagnose_trace, report_events
from organize.output import SavingOutput


def _reasons(report):
    return [event["reason_code"] for event in report_events(report)]


def test_explain_is_deterministic_and_marks_risk(tmp_path: Path):
    config = Config.from_string(
        f"""
        rules:
          - name: risky
            locations: [{tmp_path.as_posix()}]
            subfolders: true
            filters:
              - extension: pdf
            actions:
              - move: {{dest: archive/, on_conflict: overwrite}}
              - shell: echo unsafe
        """
    )
    first = explain_config(config, tags={"b", "a"})
    second = explain_config(config, tags={"a", "b"})
    assert first == second
    assert first["schema"] == "organize-appai.explain.v1"
    assert first["rules"][0]["filters"][0]["order"] == 1
    assert "high-risk action" in first["rules"][0]["actions"][1]["risks"]
    assert "destructive conflict policy: overwrite" in first["risk_summary"]


def test_why_matched_and_later_filter_failed(tmp_path: Path):
    file = tmp_path / "invoice.txt"
    file.write_text("synthetic", encoding="utf-8")
    config = Config.from_string(
        f"""
        rules:
          - name: candidate
            locations: [{tmp_path.as_posix()}]
            filters:
              - extension: txt
              - name: {{contains: receipt}}
            actions:
              - echo: "no"
        """
    )
    report = diagnose_path(config, file, approved_root=tmp_path)
    assert _reasons(report).count("filter_matched") == 1
    assert "filter_not_matched" in _reasons(report)
    assert "actions_skipped_after_filter_rejection" in _reasons(report)


def test_why_first_filter_failure_short_circuits(tmp_path: Path):
    file = tmp_path / "invoice.pdf"
    file.write_text("synthetic", encoding="utf-8")
    config = Config.from_string(
        f"""
        rules:
          - locations: [{tmp_path.as_posix()}]
            filters:
              - extension: txt
              - name: {{contains: invoice}}
            actions: [echo]
        """
    )
    report = diagnose_path(config, file, approved_root=tmp_path)
    filters = [
        event for event in report_events(report) if event["stage"] == "filter_evaluation"
    ]
    assert len(filters) == 1
    assert filters[0]["component_name"] == "extension"


def test_why_excluded_tag_wrong_target_and_missing_location(tmp_path: Path):
    folder = tmp_path / "folder"
    folder.mkdir()
    config = Config.from_string(
        f"""
        rules:
          - name: tagged
            tags: [only]
            locations: [{tmp_path.as_posix()}]
            actions: [echo]
          - name: wrong-type
            locations: [{tmp_path.as_posix()}]
            actions: [echo]
          - name: missing
            locations: [{(tmp_path / "missing").as_posix()}]
            targets: dirs
            actions: [echo]
        """
    )
    report = diagnose_path(config, folder, approved_root=tmp_path, tags={"different"})
    reasons = _reasons(report)
    assert reasons.count("rule_excluded_by_tags") >= 2

    report = diagnose_path(config, folder, approved_root=tmp_path)
    reasons = _reasons(report)
    assert "wrong_target_type" in reasons
    assert "location_missing" in reasons


def test_template_failure_action_exception_and_simulation(tmp_path: Path):
    file = tmp_path / "item.txt"
    file.write_text("synthetic", encoding="utf-8")
    config = Config.from_string(
        f"""
        rules:
          - locations: [{tmp_path.as_posix()}]
            actions:
              - rename: "{{missing_value}}.txt"
        """
    )
    sink = MemorySink()
    trace = TraceSession(sink, simulation=True, privacy_root=tmp_path)
    config.execute(
        simulate=True, output=SavingOutput(), working_dir=tmp_path, trace=trace
    )
    assert "template_render_failed" in [event.reason_code for event in sink.events]
    assert "action_exception" in [event.reason_code for event in sink.events]
    assert file.exists()


def test_conflict_and_dangerous_execution_refusal(tmp_path: Path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    file = source / "item.txt"
    file.write_text("one", encoding="utf-8")
    (destination / "item.txt").write_text("two", encoding="utf-8")
    config = Config.from_string(
        f"""
        rules:
          - locations: [{source.as_posix()}]
            actions:
              - move: {{dest: {destination.as_posix()}/, on_conflict: skip}}
              - delete
        """
    )
    sink = MemorySink()
    trace = TraceSession(sink, simulation=True, privacy_root=tmp_path)
    config.execute(
        simulate=True, output=SavingOutput(), working_dir=tmp_path, trace=trace
    )
    assert "conflict_skipped" in [event.reason_code for event in sink.events]
    assert "action_suppressed_by_simulation" in [
        event.reason_code for event in sink.events
    ]
    assert file.exists()

    report = diagnose_path(config, file, approved_root=tmp_path)
    assert "dangerous_action_not_executed_by_why" in _reasons(report)


def test_why_reads_actual_prior_simulation_trace(tmp_path: Path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    file = source / "invoice.txt"
    file.write_text("synthetic", encoding="utf-8")
    trace_path = tmp_path / "artifacts" / "simulation.jsonl"
    config = Config.from_string(
        f"""
        rules:
          - name: traced
            locations: [{source.as_posix()}]
            filters:
              - extension: txt
            actions:
              - move: {{dest: {destination.as_posix()}/, on_conflict: skip}}
        """
    )
    session = TraceSession(
        JSONLSink(trace_path), simulation=True, privacy_root=tmp_path
    )
    config.execute(
        simulate=True, output=SavingOutput(), working_dir=tmp_path, trace=session
    )

    report = diagnose_trace(trace_path, file, approved_root=tmp_path)
    reasons = _reasons(report)
    assert report["run_id"] == session.run_id
    assert "filter_matched" in reasons
    assert "action_suppressed_by_simulation" in reasons
    assert file.exists()
