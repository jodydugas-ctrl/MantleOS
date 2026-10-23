"""Typed metabolic governance for bounded MIND/provider calls."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import secrets
from typing import Any, Dict, Iterable, Optional, Tuple


class TaskClass(str, Enum):
    CONVERSATION = "conversation"
    HEARTBEAT = "heartbeat"
    ASSIST = "assist"
    ASSIMILATION = "assimilation"
    REBIRTH = "rebirth"
    REPRODUCTION = "reproduction"
    MAINTENANCE = "maintenance"


class ProviderState(str, Enum):
    DISABLED = "disabled"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    LIMITED = "limited"
    FAULTED = "faulted"


class EnergyState(str, Enum):
    FED = "fed"
    HUNGRY = "hungry"
    STARVING = "starving"
    CEILING_REACHED = "ceiling_reached"


@dataclass(frozen=True)
class EnergyPolicy:
    per_call_ceiling: float
    rolling_ceiling: float
    daily_ceiling: float
    rolling_window_seconds: int = 3600
    high_cost_tasks: Tuple[TaskClass, ...] = (
        TaskClass.ASSIMILATION,
        TaskClass.REBIRTH,
        TaskClass.REPRODUCTION,
    )

    def __post_init__(self) -> None:
        values = (self.per_call_ceiling, self.rolling_ceiling, self.daily_ceiling)
        if any(value < 0 for value in values):
            raise ValueError("energy ceilings must be non-negative")
        if self.per_call_ceiling > self.rolling_ceiling:
            raise ValueError("per-call ceiling cannot exceed rolling ceiling")
        if self.rolling_ceiling > self.daily_ceiling:
            raise ValueError("rolling ceiling cannot exceed daily ceiling")
        if self.rolling_window_seconds <= 0:
            raise ValueError("rolling window must be positive")


@dataclass(frozen=True)
class SpendAuthorization:
    schema_version: str
    authorization_id: str
    task_class: TaskClass
    maximum_energy: float
    operator_approved: bool
    issued_at: str

    @classmethod
    def issue(cls, task_class: TaskClass, maximum_energy: float,
              *, operator_approved: bool = False) -> "SpendAuthorization":
        if maximum_energy < 0:
            raise ValueError("maximum energy must be non-negative")
        return cls(
            "mantle-spend-authorization-v1",
            secrets.token_hex(16),
            task_class,
            float(maximum_energy),
            bool(operator_approved),
            datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["task_class"] = self.task_class.value
        return data


def authorize_spend(policy: EnergyPolicy, task_class: TaskClass, requested: float,
                    *, rolling_spend: float = 0.0, daily_spend: float = 0.0,
                    authorization: Optional[SpendAuthorization] = None) -> SpendAuthorization:
    """Return a bounded authorization or fail before a provider call."""
    requested = float(requested)
    if requested < 0:
        raise ValueError("requested energy must be non-negative")
    if requested > policy.per_call_ceiling:
        raise PermissionError("requested energy exceeds the per-call ceiling")
    if rolling_spend + requested > policy.rolling_ceiling:
        raise PermissionError("requested energy exceeds the rolling ceiling")
    if daily_spend + requested > policy.daily_ceiling:
        raise PermissionError("requested energy exceeds the daily ceiling")
    if task_class in policy.high_cost_tasks:
        if authorization is None or not authorization.operator_approved:
            raise PermissionError("high-cost task requires explicit operator authorization")
        if authorization.task_class != task_class:
            raise PermissionError("spend authorization is bound to another task class")
        if requested > authorization.maximum_energy:
            raise PermissionError("requested energy exceeds the authorized maximum")
        return authorization
    return SpendAuthorization.issue(task_class, requested, operator_approved=True)


def reconcile_provider_receipt(authorized: SpendAuthorization,
                               receipt: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reconcile a call; a missing receipt charges the authorized ceiling."""
    if receipt is None:
        return {
            "schema": "mantle-provider-usage-receipt-v1",
            "status": "missing",
            "charged_energy": authorized.maximum_energy,
            "immune_event": "missing_usage_receipt",
            "authorization_id": authorized.authorization_id,
        }
    reported = receipt.get("cost", receipt.get("charged_energy", 0.0))
    try:
        charged = float(reported)
    except (TypeError, ValueError) as exc:
        raise ValueError("provider receipt cost is malformed") from exc
    if charged < 0 or charged > authorized.maximum_energy:
        raise PermissionError("provider receipt exceeds the authorized ceiling")
    return {
        "schema": "mantle-provider-usage-receipt-v1",
        "status": "reconciled",
        "charged_energy": charged,
        "zero_cost": charged == 0,
        "authorization_id": authorized.authorization_id,
        "provider_receipt": dict(receipt),
    }


def spend_totals(receipts: Iterable[Dict[str, Any]]) -> float:
    return sum(float(row.get("charged_energy", 0.0)) for row in receipts)


__all__ = [
    "EnergyPolicy", "EnergyState", "ProviderState", "SpendAuthorization",
    "TaskClass", "authorize_spend", "reconcile_provider_receipt", "spend_totals",
]
