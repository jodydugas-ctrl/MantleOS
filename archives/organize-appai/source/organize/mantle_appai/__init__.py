"""Evidence-backed assistance for organize, with an optional MantleOS resident."""

from .containment import ContainmentError, require_contained
from .events import (
    EvaluationEvent,
    JSONLSink,
    MantleSink,
    MemorySink,
    NoOpSink,
    TraceSession,
)

__all__ = [
    "ContainmentError",
    "EvaluationEvent",
    "JSONLSink",
    "MantleSink",
    "MemorySink",
    "NoOpSink",
    "TraceSession",
    "require_contained",
]
