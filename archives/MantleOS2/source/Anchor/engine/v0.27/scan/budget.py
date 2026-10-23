from __future__ import annotations

from dataclasses import dataclass, asdict
from time import monotonic
from typing import Callable


@dataclass(slots=True)
class ScanBudget:
    """Deterministic aggregate scan ceilings checked at safe boundaries.

    A zero value disables that ceiling. Byte/file ceilings are enforced during inventory;
    extraction ceilings are enforced between files/adapters so an adapter result is never
    partially committed to the canonical graph.
    """

    max_total_bytes: int = 0
    max_materialized_files: int = 0
    max_extraction_seconds: float = 0.0
    max_nodes: int = 0
    max_edges: int = 0
    max_evidence: int = 0

    def validate(self) -> None:
        numeric = {
            "max_total_bytes": self.max_total_bytes,
            "max_materialized_files": self.max_materialized_files,
            "max_extraction_seconds": self.max_extraction_seconds,
            "max_nodes": self.max_nodes,
            "max_edges": self.max_edges,
            "max_evidence": self.max_evidence,
        }
        for name, value in numeric.items():
            if value < 0:
                raise ValueError(f"{name} must be >= 0")

    def as_dict(self) -> dict:
        return asdict(self)


class BudgetController:
    def __init__(self, budget: ScanBudget, *, cancel_check: Callable[[], bool] | None = None):
        budget.validate()
        self.budget = budget
        self.cancel_check = cancel_check
        self.started = monotonic()
        self.triggered_reason: str | None = None
        self.triggered_detail: dict = {}

    def _trigger(self, reason: str, **detail) -> str:
        if self.triggered_reason is None:
            self.triggered_reason = reason
            self.triggered_detail = detail
        return self.triggered_reason

    def check_cancel_or_time(self) -> str | None:
        if self.triggered_reason:
            return self.triggered_reason
        if self.cancel_check is not None and self.cancel_check():
            return self._trigger("CANCELLED", meaning="external cancellation requested")
        limit = float(self.budget.max_extraction_seconds)
        elapsed = monotonic() - self.started
        if limit > 0 and elapsed >= limit:
            return self._trigger(
                "RESOURCE_LIMIT_TIME",
                max_extraction_seconds=limit,
                meaning="elapsed-time ceiling reached at a safe file/adapter boundary",
            )
        return None

    def would_exceed_result(self, *, nodes: int, edges: int, evidence: int,
                            add_nodes: int, add_edges: int, add_evidence: int) -> str | None:
        if self.triggered_reason:
            return self.triggered_reason
        checks = (
            ("RESOURCE_LIMIT_NODES", self.budget.max_nodes, nodes, add_nodes, "max_nodes"),
            ("RESOURCE_LIMIT_EDGES", self.budget.max_edges, edges, add_edges, "max_edges"),
            ("RESOURCE_LIMIT_EVIDENCE", self.budget.max_evidence, evidence, add_evidence, "max_evidence"),
        )
        for reason, limit, current, addition, field in checks:
            if limit > 0 and current + addition > limit:
                return self._trigger(reason, current=current, pending=addition, **{field: limit})
        return None

    def status(self) -> dict:
        return {
            "configured": self.budget.as_dict(),
            "triggered": self.triggered_reason is not None,
            "reason": self.triggered_reason,
            "detail": self.triggered_detail,
            "boundary_rule": "inventory byte/file ceilings are hard; extraction time/graph ceilings stop at file/adapter boundaries",
        }
