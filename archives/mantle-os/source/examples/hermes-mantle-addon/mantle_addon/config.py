"""Validated immutable configuration for a Hermes Mantle resident."""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


class ConfigError(ValueError):
    """Resident configuration is unknown, unsafe, or internally inconsistent."""


_DNR_VALUES = {"none", "retire_only", "no_reconstruction", "operator_defined"}
_EXPECTED_ADDON_CODES = tuple(f"A-{index:02d}" for index in range(1, 15))


def _utc_timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigError(
            f"{name} must be a timezone-aware ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise ConfigError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ResidentConfig:
    body_enabled: bool = True
    mind_enabled: bool = False
    storage_root: str | None = None
    dnr: str = "none"
    record_raw_prompts: bool = False
    record_raw_tool_args: bool = False
    max_event_chars: int = 4096
    checkpoint_each_turn: bool = True

    def __post_init__(self) -> None:
        for name in (
            "body_enabled",
            "mind_enabled",
            "record_raw_prompts",
            "record_raw_tool_args",
            "checkpoint_each_turn",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ConfigError(f"{name} must be a boolean")
        if self.record_raw_prompts or self.record_raw_tool_args:
            raise ConfigError("raw payload retention is not authorized in Phase 1")
        if self.storage_root is not None and (
            not isinstance(self.storage_root, str) or not self.storage_root.strip()
        ):
            raise ConfigError("storage_root must be null or a non-empty string")
        if self.dnr not in _DNR_VALUES:
            raise ConfigError(
                "dnr must be one of: " + ", ".join(sorted(_DNR_VALUES))
            )
        if (
            isinstance(self.max_event_chars, bool)
            or not isinstance(self.max_event_chars, int)
            or not 1 <= self.max_event_chars <= 1_000_000
        ):
            raise ConfigError("max_event_chars must be an integer from 1 to 1000000")
        if self.mind_enabled:
            raise ConfigError(
                "MIND requires the explicit authorize_phase2 transition"
            )

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, Any],
        *,
        stage1_passed: bool = False,
        fusion_authorized: bool = False,
    ) -> "ResidentConfig":
        if not isinstance(values, Mapping):
            raise ConfigError("resident configuration must be a mapping")
        allowed = {
            name for name, field in cls.__dataclass_fields__.items()
            if field.init and not name.startswith("_")
        }
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ConfigError(f"unknown configuration field: {unknown[0]}")

        merged = cls().to_dict()
        merged.update(values)
        for name in (
            "body_enabled",
            "mind_enabled",
            "record_raw_prompts",
            "record_raw_tool_args",
            "checkpoint_each_turn",
        ):
            if not isinstance(merged[name], bool):
                raise ConfigError(f"{name} must be a boolean")
        if merged["record_raw_prompts"] or merged["record_raw_tool_args"]:
            raise ConfigError("raw payload retention is not authorized in Phase 1")
        storage_root = merged["storage_root"]
        if storage_root is not None and (
            not isinstance(storage_root, str) or not storage_root.strip()
        ):
            raise ConfigError("storage_root must be null or a non-empty string")
        if merged["dnr"] not in _DNR_VALUES:
            raise ConfigError(
                "dnr must be one of: " + ", ".join(sorted(_DNR_VALUES))
            )
        max_event_chars = merged["max_event_chars"]
        if (
            isinstance(max_event_chars, bool)
            or not isinstance(max_event_chars, int)
            or not 1 <= max_event_chars <= 1_000_000
        ):
            raise ConfigError("max_event_chars must be an integer from 1 to 1000000")
        if merged["mind_enabled"] and not stage1_passed:
            raise ConfigError("MIND requires a fresh Stage-1 PASS receipt")
        if merged["mind_enabled"] and not fusion_authorized:
            raise ConfigError("MIND requires separate target-bound operator and guardian fusion authorization")
        if merged["mind_enabled"]:
            raise ConfigError("MIND requires the explicit authorize_phase2 transition")
        return cls(**merged)

    @classmethod
    def authorize_phase2(
        cls,
        base: "ResidentConfig",
        *,
        stage1_receipt: Any,
        readiness_report: Mapping[str, Any],
        authorization: Mapping[str, Any],
        authority_provider: Any | None = None,
        now: datetime | None = None,
        max_receipt_age_seconds: int = 300,
    ) -> dict[str, Any]:
        """Validate evidence and authenticate both target-bound approvals."""
        if not isinstance(base, cls) or not base.body_enabled or base.mind_enabled:
            raise ConfigError("Phase-2 transition requires a live Phase-1 Body config")
        if (
            isinstance(max_receipt_age_seconds, bool)
            or not isinstance(max_receipt_age_seconds, int)
            or max_receipt_age_seconds <= 0
        ):
            raise ConfigError("max_receipt_age_seconds must be a positive integer")

        rows = getattr(stage1_receipt, "rows", None)
        row_codes = tuple(getattr(row, "code", None) for row in rows or ())
        row_results = tuple(getattr(row, "result", None) for row in rows or ())
        if (
            getattr(stage1_receipt, "passed", None) is not True
            or getattr(stage1_receipt, "framework_passed", None) is not True
            or getattr(stage1_receipt, "fails", None) != []
            or getattr(stage1_receipt, "framework_failures", None) != []
            or not isinstance(rows, list)
            or row_codes != _EXPECTED_ADDON_CODES
            or any(result != "PASS" for result in row_results)
            or (getattr(stage1_receipt, "framework_invariants", 0) or 0) <= 0
        ):
            raise ConfigError("Phase-2 transition requires a complete Stage-1 PASS receipt")

        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ConfigError("Phase-2 transition time must include a timezone")
        current = current.astimezone(timezone.utc)
        issued = _utc_timestamp(
            getattr(stage1_receipt, "issued_at", None), "Stage-1 issued_at"
        )
        age = (current - issued).total_seconds()
        if age < 0 or age > max_receipt_age_seconds:
            raise ConfigError("Stage-1 PASS receipt is not fresh")

        resident_identity = getattr(stage1_receipt, "resident_identity", None)
        body_fingerprint = getattr(stage1_receipt, "body_fingerprint", None)
        if not resident_identity or not body_fingerprint:
            raise ConfigError("Stage-1 receipt is not target-bound")
        if not isinstance(readiness_report, MappingABC):
            raise ConfigError("MIND readiness report must be a mapping")
        readiness_target = readiness_report.get("target")
        if (
            readiness_report.get("verdict") != "READY"
            or not isinstance(readiness_target, MappingABC)
            or readiness_target.get("resident_identity") != resident_identity
            or readiness_target.get("body_fingerprint") != body_fingerprint
        ):
            raise ConfigError(
                "Phase-2 transition requires a target-bound READY engineering verdict"
            )
        if readiness_report.get("reproduction_activation_authorized") is not False:
            raise ConfigError("MIND readiness must explicitly deny reproduction")
        readiness_at = _utc_timestamp(
            readiness_report.get("recorded_at"), "readiness recorded_at"
        )
        if readiness_at < issued or readiness_at > current:
            raise ConfigError("readiness report must follow the fresh Stage-1 receipt")
        if not isinstance(authorization, MappingABC):
            raise ConfigError("fusion authorization must be a mapping")
        target = authorization.get("target")
        if (
            not isinstance(target, MappingABC)
            or target.get("resident_identity") != resident_identity
            or target.get("body_fingerprint") != body_fingerprint
        ):
            raise ConfigError("fusion authorization target does not match Stage-1 receipt")

        authorized_at = _utc_timestamp(
            authorization.get("recorded_at"), "fusion authorization recorded_at"
        )
        if authorized_at < issued or authorized_at > current:
            raise ConfigError("fusion authorization must follow the fresh Stage-1 receipt")
        for role in ("operator", "guardian"):
            record = authorization.get(role)
            if (
                not isinstance(record, MappingABC)
                or record.get("fusion_decision") != "APPROVED"
            ):
                raise ConfigError(f"{role} fusion decision must be explicitly APPROVED")
        effective = authorization.get("effective_decision")
        if (
            not isinstance(effective, MappingABC)
            or effective.get("mind_fusion_authorized") is not True
            or effective.get("reproduction_activation_authorized") is not False
        ):
            raise ConfigError(
                "effective decision must authorize MIND and explicitly deny reproduction"
            )

        if authority_provider is None:
            raise ConfigError("authenticated fusion authority provider is unavailable")
        verify = getattr(authority_provider, "verify", None)
        if not callable(verify):
            raise ConfigError("authenticated fusion authority provider is invalid")
        try:
            return verify(authorization)
        except Exception as exc:
            raise ConfigError("authenticated fusion authority rejected approval") from exc

    @classmethod
    def from_hermes_config(
        cls,
        full_config: Mapping[str, Any] | None,
        *,
        plugin_id: str = "mantle-os",
    ) -> "ResidentConfig":
        """Read only ``plugins.entries.<id>.config`` from an active profile config."""
        if full_config is None:
            return cls.from_mapping({})
        if not isinstance(full_config, Mapping):
            raise ConfigError("Hermes configuration must be a mapping")
        plugins = full_config.get("plugins", {})
        if not isinstance(plugins, Mapping):
            raise ConfigError("plugins configuration must be a mapping")
        entries = plugins.get("entries", {})
        if not isinstance(entries, Mapping):
            raise ConfigError("plugins.entries configuration must be a mapping")
        entry = entries.get(plugin_id, {})
        if not isinstance(entry, Mapping):
            raise ConfigError(f"plugins.entries.{plugin_id} must be a mapping")
        values = entry.get("config", {})
        if not isinstance(values, Mapping):
            raise ConfigError(f"plugins.entries.{plugin_id}.config must be a mapping")
        return cls.from_mapping(values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
