"""Types for Body-owned, rolling model context.

The context ledger is a transport projection of VCW memory, not another source
of truth.  These types deliberately contain no provider SDK concepts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Protocol, Tuple


CONTEXT_SCHEMA = "mantle-context-v1"
RENDER_FORMAT = "mantle-prefix-v1"
ROLLING_POLICY = "rolling-prefix"
SNAPSHOT_POLICY = "snapshot"


class ContextError(RuntimeError):
    """Base error for context preparation and persistence."""


class ContextBudgetExceeded(ContextError):
    """The candidate context cannot safely fit in the configured input budget."""


class ContextCapabilityUnavailable(ContextError):
    """A required provider capability is absent from the configured transport."""


class ContextIntegrityError(ContextError):
    """The durable context chain is corrupt or internally inconsistent."""


class ContextMigrationRequired(ContextError):
    """Rolling context was requested for a cube without a context band."""


@dataclass(frozen=True)
class SourceCursor:
    facts: int = 0
    events: int = 0
    discoveries: int = 0
    senses: int = 0
    conversation: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "facts": self.facts,
            "events": self.events,
            "discoveries": self.discoveries,
            "senses": self.senses,
            "conversation": self.conversation,
        }

    @classmethod
    def from_mapping(cls, value: Optional[Mapping[str, Any]]) -> "SourceCursor":
        value = value or {}
        return cls(**{
            name: max(0, int(value.get(name, 0)))
            for name in cls.__dataclass_fields__
        })


@dataclass(frozen=True)
class ContextKey:
    body_fingerprint: str
    lane: str = "interactive"
    task: str = "primary"

    def __post_init__(self) -> None:
        if not self.body_fingerprint:
            raise ValueError("body_fingerprint is required")
        if not self.lane or not self.task:
            raise ValueError("context lane and task must be non-empty")

    def as_dict(self) -> Dict[str, str]:
        return {
            "body_fingerprint": self.body_fingerprint,
            "lane": self.lane,
            "task": self.task,
        }


@dataclass(frozen=True)
class ProviderCapabilities:
    prefix_cache: bool = False
    explicit_cache_breakpoints: bool = False
    response_cache: bool = False
    reports_cached_tokens: bool = False
    reports_context_limit: bool = False
    structured_messages: bool = False


@dataclass(frozen=True)
class ModelInfo:
    provider: Optional[str] = None
    model: Optional[str] = None
    context_window_tokens: Optional[int] = None
    reserved_output_tokens: Optional[int] = None
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    messages: Optional[Tuple[Dict[str, str], ...]] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    text: str
    usage: Optional[Mapping[str, Any]] = None
    generation_id: Optional[str] = None


class ModelTransport(Protocol):
    def __call__(self, prompt: str) -> str:
        ...

    def complete(self, request: ModelRequest) -> ModelResponse:
        ...


@dataclass(frozen=True)
class RollingContextConfig:
    context_window_tokens: int
    reserved_output_tokens: int = 4096
    safety_margin_tokens: int = 2048
    rollover_threshold: float = 0.90
    minimum_cache_prefix_tokens: int = 0
    max_delta_tokens: Optional[int] = None
    exact_context_persistence: bool = True
    persistence_mode: str = "durable-exact"
    resume_after_restart: bool = True
    context_band: str = "context"
    lane: str = "interactive"
    task: str = "primary"
    checkpoint_entries_per_band: int = 32
    provider_cache: str = "auto"

    def __post_init__(self) -> None:
        if self.context_window_tokens <= 0:
            raise ValueError("context_window_tokens must be positive")
        if self.reserved_output_tokens < 0 or self.safety_margin_tokens < 0:
            raise ValueError("token reserves and margins may not be negative")
        if not 0.5 <= self.rollover_threshold < 1.0:
            raise ValueError("rollover_threshold must be in [0.5, 1.0)")
        if self.hard_input_budget <= 0:
            raise ValueError("output reserve and safety margin exhaust the context window")
        if self.max_delta_tokens is not None and self.max_delta_tokens <= 0:
            raise ValueError("max_delta_tokens must be positive when supplied")
        if not self.context_band:
            raise ValueError("rolling context requires a context band")
        if self.persistence_mode not in {
            "durable-exact", "session-exact", "receipt-only",
        }:
            raise ValueError("unknown context persistence mode")
        if self.persistence_mode != "durable-exact" and self.resume_after_restart:
            raise ValueError(
                "%s cannot resume after restart without exact durable content"
                % self.persistence_mode
            )
        if self.persistence_mode == "durable-exact" and not self.exact_context_persistence:
            raise ValueError("durable-exact requires exact_context_persistence")
        if self.provider_cache not in {
            "disabled", "auto", "required", "response-cache",
        }:
            raise ValueError("unknown provider_cache policy")
        if self.checkpoint_entries_per_band < 1:
            raise ValueError("checkpoint_entries_per_band must be positive")

    @property
    def hard_input_budget(self) -> int:
        return (
            self.context_window_tokens
            - self.reserved_output_tokens
            - self.safety_margin_tokens
        )

    @property
    def rollover_budget(self) -> int:
        return int(self.hard_input_budget * self.rollover_threshold)


@dataclass(frozen=True)
class PreparedContext:
    prompt: str
    prompt_bytes: bytes
    generation: int
    sequence: int
    request_hash: str
    prefix_hash: str
    delta_hash: str
    intent_hash: str
    estimated_prompt_tokens: int
    source_cursors_before: Dict[str, int]
    source_cursors_after: Dict[str, int]
    ledger_entry_hashes: Tuple[str, ...] = ()
    delta_record: Optional[Dict[str, Any]] = None
    intent_record: Optional[Dict[str, Any]] = None
    request_record_hash: Optional[str] = None


class ContextStrategy(Protocol):
    def prepare(
        self,
        *,
        snapshot: Dict[str, Any],
        intent: Optional[str],
        model_info: ModelInfo,
    ) -> PreparedContext:
        ...

    def commit_success(
        self,
        prepared: PreparedContext,
        *,
        answer: str,
        usage: Optional[Dict[str, Any]],
    ) -> None:
        ...

    def commit_failure(
        self,
        prepared: PreparedContext,
        *,
        error: BaseException,
    ) -> None:
        ...
