"""Focused, evidence-backed diagnosis for one resource."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

from organize.config import Config, should_execute
from organize.output import SavingOutput
from organize.rule import filter_pipeline

from .containment import ContainmentError, require_contained
from .events import (
    EvaluationEvent,
    MemorySink,
    TraceSession,
    component_inputs,
    component_name,
)

SCHEMA_VERSION = "organize-appai.why.v1"
DANGEROUS_ACTIONS = {"delete", "trash", "shell", "python"}
MAX_TRACE_BYTES = 10 * 1024 * 1024
MAX_TRACE_EVENTS = 10_000
EVENT_FIELDS = set(EvaluationEvent.__dataclass_fields__)
VALID_OUTCOMES = {
    "entered",
    "matched",
    "not_matched",
    "skipped",
    "planned",
    "executed",
    "failed",
    "refused",
    "conflict",
    "redacted",
}


def diagnose_path(
    config: Config,
    candidate: str | Path,
    *,
    approved_root: str | Path,
    tags: Iterable[str] = (),
    skip_tags: Iterable[str] = (),
) -> dict[str, object]:
    """Evaluate rule selection and real filters, but never execute an action."""

    root = Path(approved_root).resolve(strict=True)
    sink = MemorySink()
    trace = TraceSession(sink, simulation=True, privacy_root=root)
    selected_tags = set(tags)
    excluded_tags = set(skip_tags)

    try:
        resource_path = require_contained(root, candidate)
    except ContainmentError as error:
        trace.emit(
            stage="path_safety",
            component_type="guard",
            component_name="containment",
            outcome="refused",
            reason_code="path_outside_approved_root",
            explanation=str(error),
            resource_path=Path(candidate),
        )
        return _report(trace, sink.events, candidate)

    if not resource_path.exists():
        trace.emit(
            stage="target_selection",
            component_type="resource",
            component_name="existence",
            outcome="failed",
            reason_code="resource_missing",
            explanation="The requested resource does not exist.",
            resource_path=resource_path,
        )
        return _report(trace, sink.events, resource_path)

    previous_dir = Path.cwd()
    os.chdir(root)
    try:
        with trace.activate():
            for rule_nr, rule in enumerate(config.rules):
                rule_name = rule.name or f"rule {rule_nr + 1}"
                eligible = should_execute(rule.tags, selected_tags, excluded_tags)
                if not rule.enabled:
                    trace.emit(
                        stage="rule_selection",
                        component_type="rule",
                        component_name=rule_name,
                        outcome="skipped",
                        reason_code="rule_disabled",
                        explanation=f'Rule "{rule_name}" is disabled.',
                        rule_name=rule_name,
                        resource_path=resource_path,
                    )
                    continue
                if not eligible:
                    trace.emit(
                        stage="rule_selection",
                        component_type="rule",
                        component_name=rule_name,
                        outcome="skipped",
                        reason_code="rule_excluded_by_tags",
                        explanation=f'Rule "{rule_name}" was excluded by tag selection.',
                        rule_name=rule_name,
                        resource_path=resource_path,
                        evidence={
                            "rule_tags": sorted(rule.tags),
                            "included_tags": sorted(selected_tags),
                            "skipped_tags": sorted(excluded_tags),
                        },
                    )
                    continue

                trace.emit(
                    stage="rule_selection",
                    component_type="rule",
                    component_name=rule_name,
                    outcome="entered",
                    reason_code="rule_selected",
                    explanation=f'Rule "{rule_name}" is eligible.',
                    rule_name=rule_name,
                    resource_path=resource_path,
                )

                if not rule.locations:
                    trace.emit(
                        stage="target_selection",
                        component_type="rule",
                        component_name=rule_name,
                        outcome="skipped",
                        reason_code="standalone_rule_has_no_resource",
                        explanation="This standalone rule does not evaluate file resources.",
                        rule_name=rule_name,
                        resource_path=resource_path,
                    )
                    continue

                unsafe_location = False
                for location in rule.locations:
                    for configured in location.path:
                        from organize.template import render

                        expanded = Path(render(configured))
                        try:
                            require_contained(root, expanded)
                        except ContainmentError as error:
                            unsafe_location = True
                            trace.emit(
                                stage="location_expansion",
                                component_type="location",
                                component_name="path",
                                outcome="refused",
                                reason_code="location_outside_approved_root",
                                explanation=str(error),
                                rule_name=rule_name,
                                resource_path=resource_path,
                                inputs={"configured_path": configured},
                            )
                        else:
                            trace.emit(
                                stage="location_expansion",
                                component_type="location",
                                component_name="path",
                                outcome="entered" if expanded.exists() else "failed",
                                reason_code=(
                                    "location_expanded"
                                    if expanded.exists()
                                    else "location_missing"
                                ),
                                explanation=(
                                    "The location exists inside the approved root."
                                    if expanded.exists()
                                    else "The location is safe but does not exist."
                                ),
                                rule_name=rule_name,
                                resource_path=expanded,
                            )
                if unsafe_location:
                    continue

                actual_type = (
                    "files"
                    if resource_path.is_file()
                    else "dirs"
                    if resource_path.is_dir()
                    else "other"
                )
                if actual_type != rule.targets:
                    trace.emit(
                        stage="target_selection",
                        component_type="target",
                        component_name=rule.targets,
                        outcome="not_matched",
                        reason_code="wrong_target_type",
                        explanation=f"Rule targets {rule.targets}, but the resource is {actual_type}.",
                        rule_name=rule_name,
                        resource_path=resource_path,
                        evidence={"expected": rule.targets, "observed": actual_type},
                    )
                    continue

                matched_resource = next(
                    (
                        item
                        for item in rule.walk(rule_nr=rule_nr)
                        if item.path is not None
                        and item.path.resolve(strict=False) == resource_path
                    ),
                    None,
                )
                if matched_resource is None:
                    trace.emit(
                        stage="target_selection",
                        component_type="target",
                        component_name=rule.targets,
                        outcome="not_matched",
                        reason_code="resource_not_selected_by_location",
                        explanation="The location depth, include, or exclude rules did not select this resource.",
                        rule_name=rule_name,
                        resource_path=resource_path,
                    )
                    continue

                trace.emit(
                    stage="target_selection",
                    component_type="target",
                    component_name=rule.targets,
                    outcome="entered",
                    reason_code="target_selected",
                    explanation="The resource was selected by the configured location and target type.",
                    rule_name=rule_name,
                    resource_path=resource_path,
                )
                output = SavingOutput()
                passed = filter_pipeline(
                    rule.filters,
                    rule.filter_mode,
                    matched_resource,
                    output,
                    trace,
                )
                if not passed:
                    trace.emit(
                        stage="action_planning",
                        component_type="pipeline",
                        component_name="actions",
                        outcome="skipped",
                        reason_code="actions_skipped_after_filter_rejection",
                        explanation="Actions were not planned because the filter pipeline rejected the resource.",
                        rule_name=rule_name,
                        resource_path=resource_path,
                    )
                    continue

                for action in rule.actions:
                    name = component_name(action, "action")
                    dangerous = name in DANGEROUS_ACTIONS
                    trace.emit(
                        stage="action_planning",
                        component_type="action",
                        component_name=name,
                        outcome="refused" if dangerous else "planned",
                        reason_code=(
                            "dangerous_action_not_executed_by_why"
                            if dangerous
                            else "action_would_run"
                        ),
                        explanation=(
                            f'Dangerous action "{name}" was not executed by diagnosis.'
                            if dangerous
                            else f'Action "{name}" would run; diagnosis never executes actions.'
                        ),
                        rule_name=rule_name,
                        resource_path=resource_path,
                        inputs=component_inputs(action),
                    )
    finally:
        os.chdir(previous_dir)

    return _report(trace, sink.events, resource_path)


def diagnose_trace(
    trace_file: str | Path,
    candidate: str | Path,
    *,
    approved_root: str | Path,
    run_id: str | None = None,
) -> dict[str, object]:
    """Load a bounded prior JSONL trace and select evidence for one resource."""

    root = Path(approved_root).resolve(strict=True)
    path = require_contained(root, trace_file)
    if not path.is_file():
        raise ValueError(f"trace file does not exist: {path}")
    if path.stat().st_size > MAX_TRACE_BYTES:
        raise ValueError(f"trace file exceeds {MAX_TRACE_BYTES} bytes")
    resource = require_contained(root, candidate)
    resource_ref = resource.relative_to(root).as_posix()

    events: list[EvaluationEvent] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if line_number > MAX_TRACE_EVENTS:
                raise ValueError(f"trace contains more than {MAX_TRACE_EVENTS} events")
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid JSONL at line {line_number}: {error.msg}"
                ) from error
            if not isinstance(raw, dict) or set(raw) != EVENT_FIELDS:
                raise ValueError(f"invalid event schema at line {line_number}")
            if (
                not isinstance(raw["run_id"], str)
                or not raw["run_id"]
                or not isinstance(raw["sequence"], int)
                or raw["sequence"] < 1
                or raw["outcome"] not in VALID_OUTCOMES
                or not all(
                    isinstance(raw[field], dict)
                    for field in ("evidence", "inputs", "outputs")
                )
            ):
                raise ValueError(f"invalid event values at line {line_number}")
            try:
                events.append(EvaluationEvent(**raw))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"invalid event at line {line_number}: {error}"
                ) from error

    matching_runs: list[str] = []
    for event in events:
        if (
            _same_resource(event.resource_path, resource_ref, resource.name)
            and event.run_id not in matching_runs
        ):
            matching_runs.append(event.run_id)
    selected_run = run_id or (matching_runs[-1] if matching_runs else None)
    if selected_run is None:
        return {
            "schema": SCHEMA_VERSION,
            "run_id": "not-found",
            "resource": resource_ref,
            "source_trace": path.relative_to(root).as_posix(),
            "events": [],
            "diagnostic": "No event in the trace refers to this resource.",
        }
    if selected_run not in {event.run_id for event in events}:
        raise ValueError(f"run id not present in trace: {selected_run}")

    run_events = sorted(
        (event for event in events if event.run_id == selected_run),
        key=lambda event: event.sequence,
    )
    relevant_rules = {
        event.rule_name
        for event in run_events
        if event.rule_name
        and _same_resource(event.resource_path, resource_ref, resource.name)
    }
    windows: dict[str, tuple[int, int]] = {}
    for rule_name in relevant_rules:
        start = min(
            event.sequence
            for event in run_events
            if event.rule_name == rule_name
            and _same_resource(event.resource_path, resource_ref, resource.name)
        )
        end = next(
            (
                event.sequence
                for event in run_events
                if event.sequence > start
                and event.rule_name == rule_name
                and event.stage == "target_selection"
                and event.resource_path is not None
                and not _same_resource(event.resource_path, resource_ref, resource.name)
            ),
            MAX_TRACE_EVENTS + 1,
        )
        windows[rule_name] = (start, end)

    selected: list[EvaluationEvent] = []
    for event in run_events:
        if (
            _same_resource(event.resource_path, resource_ref, resource.name)
            or event.resource_path is None
            and event.stage
            in {
                "configuration_selection",
                "rule_selection",
                "exception",
            }
        ) or (
            event.rule_name in windows
            and windows[event.rule_name][0]
            <= event.sequence
            < windows[event.rule_name][1]
            and event.stage
            in {
                "action_planning",
                "action_execution",
                "conflict_handling",
                "template_resolution",
                "exception",
            }
        ):
            selected.append(event)
    selected.sort(key=lambda event: event.sequence)
    return {
        "schema": SCHEMA_VERSION,
        "run_id": selected_run,
        "resource": resource_ref,
        "source_trace": path.relative_to(root).as_posix(),
        "events": [event.to_dict() for event in selected],
    }


def _same_resource(recorded: str | None, relative: str, name: str) -> bool:
    if recorded is None or recorded.startswith("<outside-root>"):
        return False
    normalized = recorded.replace("\\", "/").lstrip("./")
    return normalized == relative.lstrip("./") or normalized == name


def _report(
    trace: TraceSession, events: list[EvaluationEvent], candidate: str | Path
) -> dict[str, object]:
    return {
        "schema": SCHEMA_VERSION,
        "run_id": trace.run_id,
        "resource": str(candidate),
        "events": [event.to_dict() for event in events],
    }


def why_json(report: dict[str, object]) -> str:
    return json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True)


def report_events(report: dict[str, object]) -> list[dict[str, object]]:
    events = report.get("events")
    if not isinstance(events, list):
        return []
    return [e for e in events if isinstance(e, dict)]


def why_human(report: dict[str, object]) -> str:
    events = report["events"]
    assert isinstance(events, list)
    lines = [f"Trace {report['run_id']} for {report['resource']}"]
    if report.get("source_trace"):
        lines.append(f"Source: {report['source_trace']}")
    if report.get("diagnostic"):
        lines.append(str(report["diagnostic"]))
    for event in events:
        assert isinstance(event, dict)
        if event["stage"] == "rule_selection":
            lines.append(
                f"\n{event['outcome'].upper()} rule {event['component_name']}: {event['explanation']}"
            )
        elif event["stage"] == "filter_evaluation":
            label = "PASS" if event["outcome"] == "matched" else "FAIL"
            lines.append(f"  {label} {event['component_name']}: {event['explanation']}")
            evidence = event.get("evidence", {})
            if isinstance(evidence, dict):
                if evidence.get("expected"):
                    lines.append(f"    Expected: {evidence['expected']}")
                if evidence.get("observed") is not None:
                    lines.append(f"    Observed: {evidence['observed']}")
                if evidence.get("component_error"):
                    lines.append(f"    Evidence: {evidence['component_error']}")
        elif event["stage"] in {
            "action_planning",
            "action_execution",
            "conflict_handling",
            "template_resolution",
            "exception",
        } or event["outcome"] in {"failed", "refused", "skipped", "planned"}:
            lines.append(
                f"  {str(event['outcome']).upper()} {event['component_name']} "
                f"[{event['reason_code']}]: {event['explanation']}"
            )
    return "\n".join(lines)
