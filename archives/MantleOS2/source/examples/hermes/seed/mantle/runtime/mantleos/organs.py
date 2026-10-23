"""Deterministic organ contracts used by the Body without a MIND."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .contracts import ActionFrame, ActionReceipt, CapabilitySpec, contract_dict

SECRET_KEYS = re.compile(r"(?:secret|token|password|api[_-]?key|authorization)", re.IGNORECASE)
SECRET_VALUES = re.compile(
    r"(?:sk-or-v1-[A-Za-z0-9_-]{16,}|(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{12,})",
    re.IGNORECASE,
)


def redact_semantic_data(value: Any) -> Any:
    """Remove credential-shaped fields before they reach append-only memory."""
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if SECRET_KEYS.search(str(key)) else redact_semantic_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_semantic_data(item) for item in value]
    if isinstance(value, tuple):
        return [redact_semantic_data(item) for item in value]
    if isinstance(value, str) and SECRET_VALUES.search(value):
        return SECRET_VALUES.sub("[REDACTED]", value)
    return value


@dataclass
class RegisteredLimb:
    capability: CapabilitySpec
    function: Callable[[dict[str, Any]], Any]


class LimbAuthority:
    """Body-owned capability admission; a MIND may only propose ActionFrames."""

    def __init__(self, grants: set[str] | None = None):
        self.grants = set(grants or ())
        self._limbs: dict[str, RegisteredLimb] = {}

    def register(self, capability: CapabilitySpec, function: Callable[[dict[str, Any]], Any]) -> None:
        if capability.capability_id in self._limbs:
            raise ValueError(f"Capability is already registered: {capability.capability_id}")
        self._limbs[capability.capability_id] = RegisteredLimb(capability, function)

    def grant(self, capability_id: str) -> None:
        if capability_id not in self._limbs:
            raise ValueError(f"Capability is not registered: {capability_id}")
        self.grants.add(capability_id)

    def execute(self, frame: ActionFrame) -> ActionReceipt:
        limb = self._limbs.get(frame.capability_id)
        if limb is None:
            return ActionReceipt(
                frame.action_id,
                frame.capability_id,
                "refused",
                "capability-registry",
                reason="unknown capability",
            )
        if frame.capability_id not in self.grants:
            return ActionReceipt(
                frame.action_id,
                frame.capability_id,
                "refused",
                limb.capability.verifier,
                reason="authority not granted",
            )
        result = limb.function(dict(frame.arguments))
        safe = redact_semantic_data(result)
        digest = hashlib.sha256(
            json.dumps(safe, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return ActionReceipt(
            frame.action_id,
            frame.capability_id,
            "completed",
            limb.capability.verifier,
            result_digest=digest,
        )

    def describe(self) -> dict[str, Any]:
        return {
            capability_id: {
                "capability": contract_dict(registered.capability),
                "authority": "granted" if capability_id in self.grants else "denied",
            }
            for capability_id, registered in sorted(self._limbs.items())
        }
