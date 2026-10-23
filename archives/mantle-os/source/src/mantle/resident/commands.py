#!/usr/bin/env python3
"""Body-owned maintenance commands shared by Mantle residents.

Slash commands are a deterministic control plane.  They never pass through the
MIND: the Body parses them, applies bounded session configuration, and appends a
redacted receipt so a later Context Assembly can show the resident what changed.

Credentials intentionally live only in :class:`ResidentSessionState`.  They are
never included in snapshots, results, Senses signals, Memory events, exceptions,
or object representations.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import re
from typing import Any, Callable, Dict, Iterable, Optional

from ..core.redact import redact, redact_str
from .protocol import resident_vcw_event, sanitize_user_submit


DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL = "openrouter/free"
RESIDENT_PROTOCOL_VERSION = "mantle-resident-v2"
MODEL_ALIASES = {
    "free": DEFAULT_MODEL,
    "auto": "openrouter/auto",
}
COMMAND_ALIASES = {
    "/mind": "/model",
}
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,199}$")
_COMMAND_RE = re.compile(r"^/[a-z][a-z0-9_-]{0,31}$")


class ResidentSessionState:
    """Ephemeral provider configuration with a deliberately secret-safe surface."""

    def __init__(self, *, provider: str = DEFAULT_PROVIDER,
                 model: str = DEFAULT_MODEL) -> None:
        self.provider = str(provider or DEFAULT_PROVIDER)
        self.model = normalize_model(model)
        self.__api_key: Optional[str] = None

    @property
    def key_configured(self) -> bool:
        return bool(self.__api_key)

    def configure_key(self, value: str) -> None:
        candidate = str(value or "").strip()
        if not candidate:
            raise ValueError("API key must not be empty")
        if len(candidate) > 8192:
            raise ValueError("API key exceeds the session limit")
        if any(ch.isspace() for ch in candidate):
            raise ValueError("API key must not contain whitespace")
        self.__api_key = candidate

    def clear_key(self) -> bool:
        changed = self.__api_key is not None
        self.__api_key = None
        return changed

    def credential(self) -> str:
        """Return the credential only to the provider adapter at the call boundary."""
        if self.__api_key is None:
            raise PermissionError("no API key is configured for this session")
        return self.__api_key

    def select_model(self, model: str) -> bool:
        selected = normalize_model(model)
        changed = selected != self.model
        self.model = selected
        return changed

    def build_model(self, **kwargs: Any) -> Callable[[str], str]:
        """Build the configured OpenRouter transport without persisting the key."""
        if self.provider != DEFAULT_PROVIDER:
            raise ValueError("unsupported resident provider: %s" % self.provider)
        from ..mind.transport import openrouter_model
        return openrouter_model(self.credential(), self.model, **kwargs)

    def snapshot(self) -> Dict[str, Any]:
        """Public, persistable state.  The credential value is never part of it."""
        return {
            "provider": self.provider,
            "model": self.model,
            "credential_configured": self.key_configured,
            "credential_storage": "session-memory-only",
        }

    def __repr__(self) -> str:
        return "ResidentSessionState(provider=%r, model=%r, credential_configured=%r)" % (
            self.provider, self.model, self.key_configured,
        )


def normalize_model(model: str) -> str:
    candidate = str(model or "").strip()
    candidate = MODEL_ALIASES.get(candidate.lower(), candidate)
    if not candidate:
        raise ValueError("model must not be empty")
    if not _MODEL_RE.fullmatch(candidate):
        raise ValueError(
            "model must be a bounded provider/model identifier without whitespace"
        )
    return candidate


@dataclass(frozen=True)
class BodyCommandResult:
    """Typed public result from one deterministic Body command."""

    command: str
    ok: bool
    status: str
    message: str
    changed_fields: tuple[str, ...] = ()
    needs_secret: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "ok": self.ok,
            "status": self.status,
            "message": self.message,
            "changed_fields": list(self.changed_fields),
            "needs_secret": self.needs_secret,
            "details": dict(self.details),
        }


BodyCommandHandler = Callable[[str, Optional[str]], BodyCommandResult]


@dataclass(frozen=True)
class BodyCommandSpec:
    name: str
    help: str
    handler: BodyCommandHandler
    accepts_secret: bool = False


class BodyCommandDispatcher:
    """Route slash commands to Body handlers and record every outcome.

    ``organism`` is optional so a terminal can use the dispatcher before a nest
    opens.  When supplied, input crosses Senses once, command receipts enter the
    events band, and successful changes emit ``body_configuration_changed``.
    Host applications can register further deterministic Body commands; ordinary
    non-slash text remains outside this dispatcher and belongs to MIND conversation.
    """

    def __init__(self, organism: Any = None, *,
                 state: Optional[ResidentSessionState] = None) -> None:
        self.organism = organism
        self.state = state or ResidentSessionState()
        self._commands: Dict[str, BodyCommandSpec] = {}
        self._aliases = dict(COMMAND_ALIASES)
        self.register("/help", "list Body maintenance commands", self._help)
        self.register("/key", "configure an API key in session memory", self._key,
                      accepts_secret=True)
        self.register("/model", "show or select the OpenRouter model", self._model)
        self.register("/offline", "clear the session API key", self._offline)
        self.register("/status", "show redacted resident provider state", self._status)
        self.register("/provider-test", "test provider configuration without sending content",
                      self._provider_test)
        self.register("/evidence", "show bounded Body evidence and receipts", self._evidence)
        self.register("/quit", "close the resident terminal", self._quit)
        if organism is not None:
            organism.senses.mark_routine("resident.body_command", "submit")

    def register(self, name: str, help_text: str, handler: BodyCommandHandler,
                 *, accepts_secret: bool = False) -> None:
        command = str(name or "").strip().lower()
        if not _COMMAND_RE.fullmatch(command):
            raise ValueError("Body command names must look like /command")
        if command in self._commands:
            raise ValueError("Body command is already registered: %s" % command)
        self._commands[command] = BodyCommandSpec(
            command, str(help_text or "").strip(), handler, bool(accepts_secret)
        )

    def commands(self) -> Iterable[BodyCommandSpec]:
        return tuple(self._commands[name] for name in sorted(self._commands))

    def aliases(self) -> Dict[str, str]:
        """Return compatibility spellings mapped to canonical Body commands."""
        return dict(self._aliases)

    def dispatch(self, text: str, *, secret_input: Optional[str] = None) -> BodyCommandResult:
        raw = str(text or "")
        stripped = raw.strip()
        if not stripped.startswith("/"):
            raise ValueError("non-slash text belongs to MIND conversation")
        command, _separator, argument = stripped.partition(" ")
        command = command.lower()
        canonical_command = self._aliases.get(command, command)
        sanitized = sanitize_user_submit(raw)
        self._sense(command, sanitized)

        spec = self._commands.get(canonical_command)
        if spec is None:
            result = BodyCommandResult(
                command, False, "refused",
                "Unknown Body command. Use /help to list resident commands.",
                details={"reason_code": "unknown_body_command"},
            )
        elif secret_input is not None and not spec.accepts_secret:
            result = BodyCommandResult(
                command, False, "refused",
                "Secret input is not accepted by this Body command.",
                details={"reason_code": "unexpected_secret_input"},
            )
        else:
            try:
                result = spec.handler(argument.strip(), secret_input)
            except (PermissionError, ValueError) as exc:
                result = BodyCommandResult(
                    command, False, "refused", str(exc),
                    details={"reason_code": type(exc).__name__},
                )
            except Exception as exc:  # fail closed; extensions are untrusted host seams
                result = BodyCommandResult(
                    command, False, "failed",
                    "Body command failed: %s" % type(exc).__name__,
                    details={"reason_code": "body_command_exception",
                             "error_type": type(exc).__name__},
                )

        if command != canonical_command:
            result = replace(
                result,
                command=command,
                details={**result.details, "canonical_command": canonical_command},
            )

        result = self._redact_result(result)
        self._record(result, sanitized)
        return result

    def _sense(self, command: str, sanitized_text: str) -> None:
        if self.organism is None:
            return
        self.organism.senses.inhale({
            "action_id": "resident.body_command",
            "event_type": "submit",
            "command": command,
            "text": sanitized_text,
            "handled_by": "BODY",
        })

    def _record(self, result: BodyCommandResult, sanitized_text: str) -> None:
        if self.organism is None:
            return
        changed = bool(result.changed_fields and result.ok)
        kind = (
            "BODY_CONFIGURATION_CHANGED" if changed else
            "BODY_COMMAND" if result.ok else
            "BODY_COMMAND_REFUSED"
        )
        payload = {
            "command": result.command,
            "status": result.status,
            "changed_fields": list(result.changed_fields),
            "needs_secret": result.needs_secret,
            "handled_by": "BODY",
            "mind_invoked": False,
            "details": redact(result.details),
            "public_state": self.state.snapshot(),
        }
        event = resident_vcw_event(
            kind, payload, text=sanitized_text,
            source="resident-body-command", ok=result.ok,
        )
        self.organism.memory.remember(
            "events", event, opcode=kind, source="resident-body-command"
        )
        if changed:
            self.organism.bus.emit("body_configuration_changed", {
                "command": result.command,
                "changed_fields": list(result.changed_fields),
                "public_state": self.state.snapshot(),
                "event_kind": kind,
            })

    @staticmethod
    def _redact_result(result: BodyCommandResult) -> BodyCommandResult:
        return replace(
            result,
            message=redact_str(result.message),
            details=redact(result.details),
        )

    # -- canonical Body commands ------------------------------------------
    def _help(self, _argument: str, _secret: Optional[str]) -> BodyCommandResult:
        rows = ["%s — %s" % (spec.name, spec.help) for spec in self.commands()]
        rows.extend(
            "%s - compatibility alias for %s" % (alias, canonical)
            for alias, canonical in sorted(self._aliases.items())
        )
        return BodyCommandResult(
            "/help", True, "executed",
            "Body maintenance commands:\n" + "\n".join(rows),
            details={"commands": [spec.name for spec in self.commands()],
                     "aliases": self.aliases()},
        )

    def _key(self, argument: str, secret: Optional[str]) -> BodyCommandResult:
        candidate = secret if secret is not None else argument
        if not candidate:
            return BodyCommandResult(
                "/key", True, "needs_secret",
                "Enter the API key through the terminal's hidden-input prompt.",
                needs_secret=True,
                details={"credential_storage": "session-memory-only"},
            )
        self.state.configure_key(candidate)
        return BodyCommandResult(
            "/key", True, "executed",
            "API key accepted into session memory; it was not written to VCW or disk.",
            changed_fields=("credential",),
            details={"credential_configured": True,
                     "credential_storage": "session-memory-only",
                     "provider": self.state.provider},
        )

    def _model(self, argument: str, _secret: Optional[str]) -> BodyCommandResult:
        if not argument:
            return BodyCommandResult(
                "/model", True, "executed",
                "Current resident model: %s" % self.state.model,
                details={"model": self.state.model,
                         "default_model": DEFAULT_MODEL},
            )
        changed = self.state.select_model(argument)
        return BodyCommandResult(
            "/model", True, "executed",
            "Resident model selected: %s" % self.state.model,
            changed_fields=("model",) if changed else (),
            details={"model": self.state.model,
                     "default_model": DEFAULT_MODEL,
                     "changed": changed},
        )

    def _offline(self, _argument: str, _secret: Optional[str]) -> BodyCommandResult:
        changed = self.state.clear_key()
        return BodyCommandResult(
            "/offline", True, "executed",
            "Resident provider is offline; no API key is configured.",
            changed_fields=("credential",) if changed else (),
            details={"credential_configured": False, "changed": changed},
        )

    def _status(self, _argument: str, _secret: Optional[str]) -> BodyCommandResult:
        state = self.state.snapshot()
        return BodyCommandResult(
            "/status", True, "executed",
            "Provider: %s; model: %s; API key configured: %s" % (
                state["provider"], state["model"],
                "yes" if state["credential_configured"] else "no",
            ),
            details={**state, "resident_protocol": RESIDENT_PROTOCOL_VERSION,
                     "requested_model": state["model"],
                     "resolved_model": None,
                     "model_evidence": "not_requested"},
        )

    def _provider_test(self, _argument: str, _secret: Optional[str]) -> BodyCommandResult:
        """Validate local provider state without making a network request."""
        state = self.state.snapshot()
        if not state["credential_configured"]:
            return BodyCommandResult(
                "/provider-test", True, "offline",
                "Provider configuration is valid but offline until /key is supplied.",
                details={"provider": state["provider"], "model": state["model"],
                         "network_called": False},
            )
        return BodyCommandResult(
            "/provider-test", True, "ready",
            "Provider configuration is locally valid; no network request was made.",
            details={"provider": state["provider"], "model": state["model"],
                     "network_called": False},
        )

    def _evidence(self, _argument: str, _secret: Optional[str]) -> BodyCommandResult:
        """Expose only bounded, redacted Body evidence; never credentials or content."""
        records = []
        if self.organism is not None:
            try:
                records = list(self.organism.memory.recent("events", limit=20))
            except Exception:
                records = []
        safe = redact(records)
        return BodyCommandResult(
            "/evidence", True, "executed",
            "Bounded Body evidence is available below (credentials and raw content redacted).",
            details={"resident_protocol": RESIDENT_PROTOCOL_VERSION,
                     "event_count": len(safe), "events": safe},
        )

    def _quit(self, _argument: str, _secret: Optional[str]) -> BodyCommandResult:
        return BodyCommandResult(
            "/quit", True, "executed", "Resident terminal close requested.",
            details={"exit_requested": True},
        )


__all__ = [
    "COMMAND_ALIASES",
    "DEFAULT_MODEL",
    "DEFAULT_PROVIDER",
    "MODEL_ALIASES",
    "BodyCommandDispatcher",
    "BodyCommandResult",
    "BodyCommandSpec",
    "ResidentSessionState",
    "normalize_model",
]
