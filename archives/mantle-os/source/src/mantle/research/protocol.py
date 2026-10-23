"""Validated, serializable research protocol contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping


class ResearchProtocolError(ValueError):
    """A research protocol is incomplete or attempts an unsupported surface."""


GATE_ORDER = ("safety", "correctness", "regression", "objective", "resource", "complexity")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class ResearchProtocol:
    protocol_id: str
    profile: str
    version: str
    mutable_surface: Mapping[str, Any]
    immutable_surface: tuple[str, ...] | list[str]
    resource_budget: Mapping[str, Any]
    objective: str
    stop_policy: Mapping[str, Any] = field(default_factory=dict)
    schema: str = "mantle.research.protocol.v1"

    def __post_init__(self) -> None:
        if not self.protocol_id or not self.profile or not self.version:
            raise ResearchProtocolError("protocol_id, profile, and version are required")
        if not isinstance(self.mutable_surface, Mapping) or not self.mutable_surface.get("name"):
            raise ResearchProtocolError("mutable_surface requires a name")
        paths = self.mutable_surface.get("paths", [])
        if not isinstance(paths, (list, tuple)) or not paths:
            raise ResearchProtocolError("mutable_surface requires an allowlisted path list")
        if not isinstance(self.immutable_surface, (list, tuple)) or not self.immutable_surface:
            raise ResearchProtocolError("immutable_surface must be non-empty")
        if not isinstance(self.resource_budget, Mapping) or not self.resource_budget:
            raise ResearchProtocolError("resource_budget is required")
        for key in ("wall_seconds", "max_experiments"):
            if key in self.resource_budget and float(self.resource_budget[key]) <= 0:
                raise ResearchProtocolError("resource budget %s must be positive" % key)
        if self.profile not in {"grimoire-dual-edition", "vcw-persistence", "mind-context", "test"}:
            raise ResearchProtocolError("unknown research profile %r" % self.profile)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "protocol_id": self.protocol_id,
            "profile": self.profile, "version": self.version,
            "mutable_surface": dict(self.mutable_surface),
            "immutable_surface": list(self.immutable_surface),
            "resource_budget": dict(self.resource_budget), "objective": self.objective,
            "stop_policy": dict(self.stop_policy), "gate_order": list(GATE_ORDER),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResearchProtocol":
        if value.get("schema", "mantle.research.protocol.v1") != "mantle.research.protocol.v1":
            raise ResearchProtocolError("unsupported research protocol schema")
        return cls(
            protocol_id=str(value.get("protocol_id", "")), profile=str(value.get("profile", "")),
            version=str(value.get("version", "")),
            mutable_surface=dict(value.get("mutable_surface") or {}),
            immutable_surface=tuple(value.get("immutable_surface") or ()),
            resource_budget=dict(value.get("resource_budget") or {}),
            objective=str(value.get("objective", "")),
            stop_policy=dict(value.get("stop_policy") or {}),
        )

    @property
    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(_canonical(self.to_dict())).hexdigest()


def save_protocol(protocol: ResearchProtocol, path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(protocol.to_dict(), handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def load_protocol(path: str) -> ResearchProtocol:
    with open(path, encoding="utf-8") as handle:
        return ResearchProtocol.from_dict(json.load(handle))
