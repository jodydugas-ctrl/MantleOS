"""Structured diagnostic events and fail-open trace sinks."""

from __future__ import annotations

import contextlib
import contextvars
import dataclasses
import json
import threading
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Protocol

from .privacy import display_path, redact_text, sanitize

Outcome = Literal[
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
]


@dataclass(frozen=True)
class EvaluationEvent:
    run_id: str
    sequence: int
    timestamp: str
    simulation: bool
    rule_name: str | None
    resource_path: str | None
    stage: str
    component_type: str
    component_name: str
    outcome: Outcome
    reason_code: str
    explanation: str
    evidence: dict[str, object] = field(default_factory=dict)
    inputs: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


class TraceSink(Protocol):
    enabled: bool

    def emit(self, event: EvaluationEvent) -> None: ...


class NoOpSink:
    enabled = False

    def emit(self, event: EvaluationEvent) -> None:
        return None


class MemorySink:
    enabled = True

    def __init__(self) -> None:
        self.events: list[EvaluationEvent] = []

    def emit(self, event: EvaluationEvent) -> None:
        self.events.append(event)


class JSONLSink:
    enabled = True

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def emit(self, event: EvaluationEvent) -> None:
        line = json.dumps(event.to_dict(), ensure_ascii=True, sort_keys=True) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(line)


class CompositeSink:
    enabled = True

    def __init__(self, sinks: Iterable[TraceSink]) -> None:
        self.sinks = tuple(sink for sink in sinks if sink.enabled)
        self.enabled = bool(self.sinks)

    def emit(self, event: EvaluationEvent) -> None:
        for sink in self.sinks:
            try:
                sink.emit(event)
            except Exception:  # noqa: BLE001 - one optional sink must not starve another
                continue


class MantleSink:
    """Optional buffered sink; callers explicitly flush it into a Mantle bridge."""

    enabled = True

    def __init__(
        self,
        bridge: Any,
        *,
        verified_simulation: bool = False,
        max_events: int = 1_000,
    ) -> None:
        self.bridge = bridge
        self.verified_simulation = verified_simulation
        self.max_events = max_events
        self.events: list[EvaluationEvent] = []
        self.dropped = 0

    def emit(self, event: EvaluationEvent) -> None:
        if len(self.events) < self.max_events:
            self.events.append(event)
        else:
            self.dropped += 1

    def flush(self) -> int:
        if not self.events:
            return 0
        count = self.bridge.remember_events(
            self.events,
            verified_simulation=self.verified_simulation,
        )
        self.events.clear()
        return count


_CURRENT: contextvars.ContextVar[TraceSession | None] = contextvars.ContextVar(
    "organize_appai_trace", default=None
)
_COMPONENT: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar(
    "organize_appai_component", default=None
)


class TraceSession:
    """Own stable sequence numbers and protect host behavior from sink failures."""

    def __init__(
        self,
        sink: TraceSink | None = None,
        *,
        simulation: bool,
        privacy_root: str | Path | None = None,
        run_id: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.sink = sink or NoOpSink()
        self.simulation = simulation
        self.privacy_root = Path(privacy_root).resolve() if privacy_root else None
        self.run_id = run_id or str(uuid.uuid4())
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.sequence = 0

    @property
    def enabled(self) -> bool:
        return bool(self.sink.enabled)

    @contextlib.contextmanager
    def activate(self) -> Iterator[TraceSession]:
        token = _CURRENT.set(self)
        try:
            yield self
        finally:
            _CURRENT.reset(token)

    @contextlib.contextmanager
    def component(self, component_type: str, component_name: str) -> Iterator[None]:
        token = _COMPONENT.set(
            {"component_type": component_type, "component_name": component_name}
        )
        try:
            yield
        finally:
            _COMPONENT.reset(token)

    def emit(
        self,
        *,
        stage: str,
        component_type: str,
        component_name: str,
        outcome: Outcome,
        reason_code: str,
        explanation: str,
        rule_name: str | None = None,
        resource_path: str | Path | None = None,
        evidence: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
    ) -> EvaluationEvent | None:
        if not self.enabled:
            return None
        self.sequence += 1
        event = EvaluationEvent(
            run_id=self.run_id,
            sequence=self.sequence,
            timestamp=self.clock()
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            simulation=self.simulation,
            rule_name=redact_text(rule_name) if rule_name is not None else None,
            resource_path=(
                display_path(resource_path, self.privacy_root)
                if resource_path is not None
                else None
            ),
            stage=stage,
            component_type=component_type,
            component_name=redact_text(component_name),
            outcome=outcome,
            reason_code=reason_code,
            explanation=redact_text(explanation),
            evidence=sanitize(evidence or {}, root=self.privacy_root),
            inputs=sanitize(inputs or {}, root=self.privacy_root),
            outputs=sanitize(outputs or {}, root=self.privacy_root),
        )
        try:
            self.sink.emit(event)
        except Exception:  # noqa: BLE001 - tracing is explicitly fail-open
            # Instrumentation is fail-open by contract. A sink may be unavailable without
            # changing the host pipeline's result.
            return None
        return event


def current_trace() -> TraceSession | None:
    return _CURRENT.get()


def component_name(component: Any, kind: str) -> str:
    config = getattr(component, f"{kind}_config", None)
    if config is not None and getattr(config, "name", None):
        return str(config.name)
    wrapped = getattr(component, "filter", None)
    if wrapped is not None:
        return "not " + component_name(wrapped, "filter")
    return type(component).__name__.lower()


def component_inputs(component: Any) -> dict[str, Any]:
    wrapped = getattr(component, "filter", None)
    if wrapped is not None:
        return {"negated": True, "filter": component_inputs(wrapped)}
    try:
        if dataclasses.is_dataclass(component):
            return {
                field.name: getattr(component, field.name)
                for field in dataclasses.fields(component)
                if not field.name.startswith("_")
            }
    except (AttributeError, TypeError):
        pass
    model_dump = getattr(component, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return {}


def component_evidence(component: Any, resource_vars: dict[str, Any]) -> dict[str, Any]:
    """Extract bounded facts produced by the real component evaluation."""

    wrapped = getattr(component, "filter", None)
    inspected = wrapped if wrapped is not None else component
    name = component_name(inspected, "filter")
    result: dict[str, Any] = {
        "expected": component_inputs(component),
        "observed": resource_vars.get(name),
    }
    error = getattr(inspected, "_last_error", None)
    if error is not None:
        result["component_error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
    return result


def emit_template_resolution(
    template: Any, rendered: str | None, error: Exception | None
) -> None:
    trace = current_trace()
    if trace is None or not trace.enabled:
        return
    current = _COMPONENT.get() or {
        "component_type": "template",
        "component_name": "template",
    }
    trace.emit(
        stage="template_resolution",
        component_type=current["component_type"],
        component_name=current["component_name"],
        outcome="failed" if error else "executed",
        reason_code="template_render_failed" if error else "template_rendered",
        explanation=(str(error) if error else "Template resolved successfully."),
        inputs={
            "template": template if isinstance(template, str) else "<compiled-template>"
        },
        outputs={"rendered": rendered} if rendered is not None else {},
    )


def emit_conflict(
    *,
    resource_path: Path,
    destination: Path,
    mode: str,
    outcome: Outcome,
    reason_code: str,
    explanation: str,
    use_destination: Path | None = None,
) -> None:
    trace = current_trace()
    if trace is None or not trace.enabled:
        return
    current = _COMPONENT.get() or {
        "component_type": "conflict",
        "component_name": "conflict",
    }
    trace.emit(
        stage="conflict_handling",
        component_type=current["component_type"],
        component_name=current["component_name"],
        outcome=outcome,
        reason_code=reason_code,
        explanation=explanation,
        resource_path=resource_path,
        evidence={"mode": mode, "destination_exists": destination.exists()},
        inputs={"destination": destination},
        outputs={"destination": use_destination} if use_destination else {},
    )
