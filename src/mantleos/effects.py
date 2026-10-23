"""Checked-effect lifecycle for MantleOS capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any
import hashlib
import json

from . import engram


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Capability:
    name: str
    effect: str
    authority: str | None
    provider_id: str
    provider: Callable[[dict], Any]
    verifier: Callable[[Any], bool]


class CapabilityRegistry:
    def __init__(self):
        self._items: dict[str, Capability] = {}

    def register(self, capability: Capability):
        if capability.name in self._items:
            raise ValueError("Duplicate capability")
        self._items[capability.name] = capability

    def get(self, name: str) -> Capability:
        try:
            return self._items[name]
        except KeyError as exc:
            raise ValueError("Unknown capability") from exc

    def catalog(self):
        return [
            {"name": c.name, "effect": c.effect, "authority": c.authority, "provider_id": c.provider_id}
            for c in sorted(self._items.values(), key=lambda x: x.name)
        ]


class CheckedActionExecutor:
    """Separate visibility, authority, execution, observation, and verification.

    When a ledger is bound, callers may provide ``expected_head``.  Every emitted
    lifecycle record advances from the preceding observed head, which makes a
    checked action usable inside a stale-state-protected hosted transaction.
    """

    def __init__(self, registry: CapabilityRegistry, broker: Callable[[str, str | None], bool], ledger=None):
        self.registry = registry
        self.broker = broker
        self.ledger = ledger

    def _record(self, stage, body, *, expected_head=None):
        payload = {"schema": "mantle.effect-stage/1", "stage": stage, **body}
        if self.ledger:
            rec = engram.append(self.ledger, "effect", "checked-action", payload, expected_head=expected_head)
            return payload, rec["sha256"]
        return payload, expected_head

    def execute(self, name: str, arguments: dict, *, request_id: str, expected_head: str | None = None):
        cap = self.registry.get(name)
        if not isinstance(arguments, dict):
            raise ValueError("Capability arguments must be an object")
        binding = {
            "request_id": request_id,
            "capability": name,
            "provider_id": cap.provider_id,
            "effect": cap.effect,
            "arguments": arguments,
        }
        binding_sha = digest(binding)
        current = expected_head
        intended, current = self._record("INTENDED", {**binding, "binding_sha256": binding_sha}, expected_head=current)
        trace = [intended]
        if cap.authority and not self.broker(cap.authority, name):
            failed, current = self._record(
                "FAILED", {"binding_sha256": binding_sha, "reason": "authority_denied"}, expected_head=current
            )
            trace.append(failed)
            return {"schema": "mantle.checked-action/1", "stage": "FAILED", "binding_sha256": binding_sha, "trace": trace, "ledger_head": current}
        attempted, current = self._record("ATTEMPTED", {"binding_sha256": binding_sha}, expected_head=current)
        trace.append(attempted)
        try:
            result = cap.provider(arguments)
        except Exception as exc:  # evidence, not a hidden retry
            unknown, current = self._record(
                "UNKNOWN",
                {"binding_sha256": binding_sha, "error": type(exc).__name__ + ": " + str(exc)},
                expected_head=current,
            )
            trace.append(unknown)
            return {"schema": "mantle.checked-action/1", "stage": "UNKNOWN", "binding_sha256": binding_sha, "trace": trace, "ledger_head": current}
        if name in {'memory.engram','body.compile','body.rebuild'} and self.ledger:
            current = engram.head(self.ledger)
        observation = {"binding_sha256": binding_sha, "result": result, "result_sha256": digest(result)}
        observed, current = self._record("OBSERVED", observation, expected_head=current)
        trace.append(observed)
        try:
            verified = bool(cap.verifier(result))
        except Exception:
            verified = False
        final = "VERIFIED" if verified else "FAILED"
        final_payload, current = self._record(
            final, {"binding_sha256": binding_sha, "result_sha256": observation["result_sha256"]}, expected_head=current
        )
        trace.append(final_payload)
        return {
            "schema": "mantle.checked-action/1",
            "stage": final,
            "binding_sha256": binding_sha,
            "observation": observation,
            "trace": trace,
            "ledger_head": current,
        }
