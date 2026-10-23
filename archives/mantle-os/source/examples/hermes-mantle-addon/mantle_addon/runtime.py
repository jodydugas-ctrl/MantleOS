"""Fail-open observer bridge from documented Hermes hooks into Mantle organs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from threading import RLock
import time
from typing import Any, Callable, Literal, Mapping

from .aep import record_action_execution_proof
from .body import ResidentBodyFactory, save_resident
from .config import ConfigError, ResidentConfig
from .scheduler import CognitiveScheduler
from .vendor import vendored_symbol


def _safe_save(organism: Any, path: Any) -> None:
    """Fail-open save for the atexit handler — never raises on the way down."""
    try:
        save_resident(organism, path)
    except Exception:
        pass


OBSERVER_HOOKS = (
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "pre_llm_call",
    "post_llm_call",
    "pre_tool_call",
    "post_tool_call",
    "pre_approval_request",
    "post_approval_response",
    "subagent_start",
    "subagent_stop",
    "pre_gateway_dispatch",
)

DISCOVERY_CONTROL_ID = "hermes.mantle.record_discovery"
MAX_DISCOVERY_CHARS = 2_000
MAX_MIND_PROMPT_CHARS = 4_000
MAX_MIND_CONTEXT_CHARS = 4_000
INTERACTIVE_MIND_REFLECTION = (
    "Interactive MIND response delivered to the user; content withheld by privacy policy."
)
_DEFUSION_REASONS = {"operator", "guardian", "shutdown", "recovery", "fault", "rollback"}


@dataclass(frozen=True)
class FusionReceipt:
    """Redacted BODY-authored evidence for one fusion lifecycle transition."""

    schema_version: str
    transition: str
    outcome: str
    from_state: str
    to_state: str
    reason_code: str
    resident_identity: str
    body_fingerprint: str
    stage1_certified: bool
    mind_attached: bool
    body_preserved: bool
    reproduction_authorized: Literal[False]
    recorded_at: str
    durable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def body_record(self) -> dict[str, Any]:
        """Return the lifecycle fact without claiming its own durability."""
        record = self.to_dict()
        record.pop("durable")
        return record


class FusionLifecycleError(PermissionError):
    """A fusion request was refused without attaching or invoking a MIND."""

    def __init__(self, receipt: FusionReceipt) -> None:
        super().__init__(f"fusion refused: {receipt.reason_code}")
        self.receipt = receipt


def _validated_discovery(value: Any) -> str:
    """Validate the only model-facing mutation before it reaches Memory."""
    if not isinstance(value, str):
        raise TypeError("discovery must be a string")
    text = value.strip()
    if not text:
        raise ValueError("discovery must not be empty")
    if len(text) > MAX_DISCOVERY_CHARS:
        raise ValueError(
            f"discovery must be at most {MAX_DISCOVERY_CHARS} characters"
        )
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise ValueError("discovery contains unsupported control characters")
    return text


def _validated_mind_prompt(value: Any) -> str:
    """Validate one explicit user-to-AppAI prompt before host dispatch."""
    if not isinstance(value, str):
        raise TypeError("MIND prompt must be a string")
    text = value.strip()
    if not text:
        raise ValueError("MIND prompt must not be empty")
    if len(text) > MAX_MIND_PROMPT_CHARS:
        raise ValueError(
            f"MIND prompt must be at most {MAX_MIND_PROMPT_CHARS} characters"
        )
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise ValueError("MIND prompt contains unsupported control characters")
    return text


class _PrivateMindModel:
    """Persist a privacy marker through MIND while retaining the live answer."""

    def __init__(self, delegate: Callable[[str], str]):
        self._delegate = delegate
        self.answer: str | None = None

    def __call__(self, prompt: str) -> str:
        answer = self._delegate(prompt)
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("AppAI MIND produced no response")
        self.answer = answer.strip()
        return INTERACTIVE_MIND_REFLECTION


class ResidentRuntime:
    """One profile-scoped Body adapter; hook return values never alter Hermes behavior."""

    def __init__(
        self,
        config: ResidentConfig,
        *,
        profile_id: str,
        hermes_home: str | Path | None = None,
        factory: Any | None = None,
        model_factory: Callable[[], Any] | None = None,
        authority_provider_factory: Callable[[], Any] | None = None,
        scheduler_factory: Callable[..., Any] = CognitiveScheduler,
    ) -> None:
        self.config = config
        self.profile_id = profile_id
        self.factory = factory or ResidentBodyFactory(config, hermes_home=hermes_home)
        self._handle: Any | None = None
        self._sequence = 0
        self._lock = RLock()
        self._model_factory = model_factory
        self._authority_provider_factory = authority_provider_factory or (lambda: None)
        self._scheduler_factory = scheduler_factory
        self._scheduler: Any | None = None
        self._model: Any | None = None
        self.diagnostics: list[dict[str, str]] = []

    @property
    def organism(self) -> Any:
        return self._ensure_handle().organism

    @property
    def fusion_state(self) -> Literal["DORMANT", "FUSED"]:
        """Report live attachment state; configuration is never treated as state."""
        with self._lock:
            return "FUSED" if self._ensure_handle().organism.brain.fused else "DORMANT"

    def _ensure_handle(self) -> Any:
        with self._lock:
            if self._handle is None:
                handle = self.factory.get_or_create(self.profile_id)
                organism = handle.organism
                path = handle.path
                if organism.brain.fused:
                    before = self._body_snapshot(organism)
                    organism.brain.defuse()
                    organism.stage1_certified = False
                    receipt = self._new_fusion_receipt(
                        organism,
                        transition="RECOVERED_DORMANT",
                        outcome="COMMITTED",
                        from_state="FUSED",
                        to_state="DORMANT",
                        reason_code="UNEXPECTED_FUSED_STATE",
                        body_preserved=before == self._body_snapshot(organism),
                    )
                    self._persist_fusion_receipt(organism, path, receipt)
                if self.config.checkpoint_each_turn:
                    organism.heart.set_circulate(
                        lambda organism=organism, path=path: save_resident(organism, path)
                    )
                else:
                    organism.heart.set_circulate(None)
                # Dual-flush: persist on BOTH explicit checkpoint AND atexit, so a
                # cube is never lost to an ungraceful shutdown. The atexit handler
                # calls circulate(), which is a no-op when the circulate callback is
                # None (deferred mode) — but in deferred mode we install our own
                # atexit handler below that performs the full save.
                organism.heart.install_dual_flush()
                if not self.config.checkpoint_each_turn:
                    import atexit as _atexit
                    _atexit.register(
                        lambda organism=organism, path=path: _safe_save(organism, path)
                    )
                self._wire_controls(organism)
                self._handle = handle
            return self._handle

    @staticmethod
    def _wire_controls(organism: Any) -> None:
        """Expose the bounded model-facing mutation through Senses + Limbs."""
        def record_discovery(value: Any) -> None:
            text = _validated_discovery(value)
            organism.memory.remember(
                "discoveries",
                {"idea": text},
                opcode="INGESTED",
                source="Hermes mantle_record_discovery",
                verified=False,
                confidence="inferred",
            )

        organism.limbs.register_control(
            DISCOVERY_CONTROL_ID,
            {
                "label": "Record inferred discovery",
                "kind": "bounded_text",
                "band": "discoveries",
                "max_chars": MAX_DISCOVERY_CHARS,
                "verified": False,
            },
            record_discovery,
        )

    @staticmethod
    def _body_snapshot(organism: Any) -> tuple[Any, ...]:
        """Capture the Body properties that defusion must not alter."""
        return (
            id(organism),
            organism.body.identity_name(),
            organism.body.key_fingerprint,
            organism.body.primer_sealed,
            frozenset(organism.organs()),
        )

    @staticmethod
    def _new_fusion_receipt(
        organism: Any,
        *,
        transition: str,
        outcome: str,
        from_state: str,
        to_state: str,
        reason_code: str,
        body_preserved: bool,
    ) -> FusionReceipt:
        return FusionReceipt(
            schema_version="mantle-fusion-lifecycle-v1",
            transition=transition,
            outcome=outcome,
            from_state=from_state,
            to_state=to_state,
            reason_code=reason_code,
            resident_identity=organism.body.identity_name(),
            body_fingerprint=organism.body.key_fingerprint,
            stage1_certified=organism.stage1_certified,
            mind_attached=organism.brain.fused,
            body_preserved=body_preserved,
            reproduction_authorized=False,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            durable=False,
        )

    def _persist_fusion_receipt(
        self,
        organism: Any,
        path: Any,
        receipt: FusionReceipt,
    ) -> FusionReceipt:
        """Append a redacted receipt and report whether the checkpoint succeeded."""
        try:
            make_entry = vendored_symbol("vcw.entry", "make_entry")
            entry = make_entry(
                {"fusion_lifecycle": receipt.body_record()},
                opcode=receipt.transition,
                author="BODY",
                authorship="BODY",
            )
            organism.limbs.append("brain", entry)
            save_resident(organism, path)
        except Exception as exc:
            try:
                organism.immune_event(
                    "fusion_lifecycle_checkpoint_failed",
                    {
                        "transition": receipt.transition,
                        "error_type": type(exc).__name__,
                    },
                )
            except Exception:
                pass
            return receipt
        return replace(receipt, durable=True)

    def request_fusion(
        self,
        *,
        stage1_receipt: Any,
        readiness_report: Mapping[str, Any],
        authorization: Mapping[str, Any],
    ) -> FusionReceipt:
        """Authenticate, attach, and start one cognitive scheduler transactionally."""
        scheduler: Any | None = None
        with self._lock:
            handle = self._ensure_handle()
            organism = handle.organism
            if organism.brain.fused:
                receipt = self._new_fusion_receipt(
                    organism,
                    transition="FUSION_REFUSED",
                    outcome="REFUSED",
                    from_state="FUSED",
                    to_state="FUSED",
                    reason_code="ALREADY_FUSED",
                    body_preserved=True,
                )
                receipt = self._persist_fusion_receipt(organism, handle.path, receipt)
                raise FusionLifecycleError(receipt)

            reason_code: str | None = None
            try:
                verified_authority = ResidentConfig.authorize_phase2(
                    self.config,
                    stage1_receipt=stage1_receipt,
                    readiness_report=readiness_report,
                    authorization=authorization,
                    authority_provider=self._authority_provider_factory(),
                )
            except ConfigError as exc:
                reason_code = (
                    "AUTHORITY_UNAVAILABLE"
                    if str(exc) == "authenticated fusion authority provider is unavailable"
                    else "PREFLIGHT_REFUSED"
                )
            except Exception as exc:
                reason_code = "PREFLIGHT_ERROR"
                organism.immune_event(
                    "fusion_preflight_error",
                    {"error_type": type(exc).__name__},
                )
            if reason_code is None:
                if self._model_factory is None:
                    reason_code = "MODEL_PROVIDER_UNAVAILABLE"
                elif organism.stage1_certified is not True:
                    reason_code = "LIVE_STAGE1_UNCERTIFIED"
            if reason_code is None:
                try:
                    self._model = self._model_factory()
                    fuse = vendored_symbol("mind.mind", "fuse")
                    fuse(organism, self._model, authorization=verified_authority)
                    self._scheduler = self._scheduler_factory(self._cognitive_pulse)
                    if self._scheduler.start() is not True:
                        raise RuntimeError("scheduler did not start")
                    receipt = self._new_fusion_receipt(
                        organism,
                        transition="FUSION",
                        outcome="COMMITTED",
                        from_state="DORMANT",
                        to_state="FUSED",
                        reason_code="AUTHORIZED",
                        body_preserved=True,
                    )
                    receipt = self._persist_fusion_receipt(
                        organism, handle.path, receipt
                    )
                    if receipt.durable:
                        return receipt
                    reason_code = "FUSION_CHECKPOINT_FAILED"
                except Exception as exc:
                    reason_code = "FUSION_COMMIT_FAILED"
                    organism.immune_event(
                        "fusion_commit_failed",
                        {"error_type": type(exc).__name__},
                    )
            scheduler = self._scheduler
            self._scheduler = None
            self._model = None
            if organism.brain.fused:
                organism.brain.defuse()
            organism.stage1_certified = False

        stop_error: Exception | None = None
        if scheduler is not None:
            try:
                scheduler.stop()
            except Exception as exc:
                stop_error = exc
        with self._lock:
            handle = self._ensure_handle()
            organism = handle.organism
            if stop_error is not None:
                detail = {
                    "code": "SCHEDULER_STOP_FAILED",
                    "error_type": type(stop_error).__name__,
                }
                organism.immune_event("scheduler_stop_failed", detail)
                self.diagnostics.append(detail)
                del self.diagnostics[:-100]
            receipt = self._new_fusion_receipt(
                organism,
                transition="FUSION_REFUSED",
                outcome="REFUSED",
                from_state="DORMANT",
                to_state="DORMANT",
                reason_code=reason_code,
                body_preserved=True,
            )
            receipt = self._persist_fusion_receipt(organism, handle.path, receipt)
        raise FusionLifecycleError(receipt)

    def _cognitive_pulse(self, stressor: dict[str, Any] | None) -> None:
        """Run one cognition pulse and persist only its redacted receipt."""
        with self._lock:
            if self._handle is None or not self._handle.organism.brain.fused:
                return
            organism = self._handle.organism
            organism.heart.beat(assemble=True, wake=stressor)
            self._append_cognition_receipt(organism)
            save_resident(organism, self._handle.path)

    def _append_cognition_receipt(self, organism: Any) -> None:
        receipt = getattr(self._model, "last_receipt", None)
        if not isinstance(receipt, Mapping):
            return
        make_entry = vendored_symbol("vcw.entry", "make_entry")
        organism.limbs.append(
            "brain",
            make_entry(
                {"cognition_receipt": dict(receipt)},
                opcode="MODEL.RECEIPT",
                author="BODY",
                authorship="BODY",
            ),
        )

    def _append_interactive_response_digest(
        self,
        organism: Any,
        answer: str,
    ) -> None:
        make_entry = vendored_symbol("vcw.entry", "make_entry")
        organism.limbs.append(
            "brain",
            make_entry(
                {
                    "interactive_response": {
                        "sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
                        "chars": len(answer),
                        "content_persisted": False,
                    }
                },
                opcode="INTERACTIVE.RESPONSE",
                author="BODY",
                authorship="BODY",
            ),
        )

    def ask_mind(self, prompt: Any) -> str:
        """Run one explicit, additive AppAI cognition pulse and persist its VCW trace.

        Interactive contact does not attach the Brain, start a scheduler, or grant
        production fusion authority. It is a bounded user-directed MIND consultation
        through Hermes's active host model.
        """
        question = _validated_mind_prompt(prompt)
        with self._lock:
            handle = self._ensure_handle()
            organism = handle.organism
            if self._model is None:
                if self._model_factory is None:
                    raise RuntimeError("Hermes host LLM is unavailable")
                self._model = self._model_factory()

            organism.heart.body_pulse(assemble=False)
            snapshot = organism.nervous.assemble()
            context = json.dumps(snapshot, default=str, sort_keys=True)[
                :MAX_MIND_CONTEXT_CHARS
            ]
            framed = (
                "You are the interactive MIND of the AppAI named "
                f"{organism.body.identity_name()}. The Body assembled the following "
                "resolved, privacy-veiled VCW context. Answer the user's message "
                "directly and concisely; you may propose changes but cannot apply them."
                f"\n\nCONTEXT:\n{context}\n\nUSER MESSAGE:\n{question}"
            )
            private_model = _PrivateMindModel(self._model)
            Mind = vendored_symbol("mind.mind", "Mind")
            MindPort = vendored_symbol("mind.port", "MindPort")
            mind = Mind(MindPort(organism), private_model, max_thoughts=1)
            try:
                mind.think(snapshot, question=framed)
            except Exception:
                self._append_cognition_receipt(organism)
                _safe_save(organism, handle.path)
                raise
            answer = private_model.answer
            if answer is None:
                raise RuntimeError("AppAI MIND produced no response")
            self._append_interactive_response_digest(organism, answer)
            self._append_cognition_receipt(organism)
            save_resident(organism, handle.path)
            return answer

    def defuse(
        self,
        *,
        reason: Literal[
            "operator", "guardian", "shutdown", "recovery", "fault", "rollback"
        ] = "operator",
    ) -> FusionReceipt:
        """Detach cognition without authority; never reattach on checkpoint failure."""
        if reason not in _DEFUSION_REASONS:
            raise ValueError("unsupported defusion reason")
        with self._lock:
            scheduler = self._scheduler
            self._scheduler = None
        stop_error: Exception | None = None
        if scheduler is not None:
            try:
                scheduler.stop()
            except Exception as exc:
                stop_error = exc
        with self._lock:
            handle = self._ensure_handle()
            organism = handle.organism
            if stop_error is not None:
                detail = {
                    "code": "SCHEDULER_STOP_FAILED",
                    "error_type": type(stop_error).__name__,
                }
                organism.immune_event("scheduler_stop_failed", detail)
                self.diagnostics.append(detail)
                del self.diagnostics[:-100]
            before = self._body_snapshot(organism)
            from_state = "FUSED" if organism.brain.fused else "DORMANT"
            self._model = None
            if organism.brain.fused:
                organism.brain.defuse()
            organism.stage1_certified = False
            body_preserved = before == self._body_snapshot(organism)
            if not body_preserved:
                organism.immune_event(
                    "defusion_body_integrity_failure",
                    {"reason_code": reason.upper()},
                )
            receipt = self._new_fusion_receipt(
                organism,
                transition="DEFUSION",
                outcome="COMMITTED" if from_state == "FUSED" else "NOOP",
                from_state=from_state,
                to_state="DORMANT",
                reason_code=reason.upper(),
                body_preserved=body_preserved,
            )
            return self._persist_fusion_receipt(organism, handle.path, receipt)

    def record_discovery(self, text: Any) -> dict[str, Any]:
        """Record one inferred discovery through Limbs and persist its proof."""
        with self._lock:
            handle = self._ensure_handle()
            organism = handle.organism
            proof = organism.limbs.operate(DISCOVERY_CONTROL_ID, text)
            try:
                save_resident(organism, handle.path)
                durable = True
            except Exception as exc:
                durable = False
                organism.immune_event(
                    "checkpoint_failed",
                    {"event_type": "mantle_record_discovery", "error": type(exc).__name__},
                )
            return {"proof": proof, "durable": durable}

    @staticmethod
    def _hash_text(value: str) -> str:
        return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()

    @classmethod
    def _content_summary(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            return {"chars": len(value), "digest": cls._hash_text(value)}
        if isinstance(value, list):
            text_parts = []
            for item in value:
                if isinstance(item, Mapping):
                    content = item.get("content")
                    if isinstance(content, str):
                        text_parts.append(content)
            text = "\n".join(text_parts)
            return {
                "items": len(value),
                "chars": len(text),
                "digest": cls._hash_text(text),
            }
        return {"type": type(value).__name__}

    def _metadata(self, event_type: str, data: Mapping[str, Any]) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        session_id = data.get("session_id")
        if isinstance(session_id, str) and session_id:
            metadata["session"] = self._hash_text(session_id)[:23]
        if event_type in {"pre_llm_call", "post_llm_call"}:
            model = data.get("model")
            if isinstance(model, str):
                metadata["model"] = model[:256]
            for field in ("user_message", "conversation_history"):
                metadata[field] = self._content_summary(data.get(field))
            if event_type == "post_llm_call":
                metadata["assistant_response"] = self._content_summary(
                    data.get("assistant_response")
                )
            if event_type == "pre_llm_call" and isinstance(
                data.get("is_first_turn"), bool
            ):
                metadata["is_first_turn"] = data["is_first_turn"]
        if event_type in {"pre_tool_call", "post_tool_call"}:
            tool_name = data.get("tool_name")
            if isinstance(tool_name, str):
                metadata["tool_name"] = tool_name[:256]
            args = data.get("args")
            if isinstance(args, Mapping):
                metadata["arg_count"] = len(args)
        if event_type == "post_tool_call":
            metadata["status"] = str(data.get("status") or "unknown")[:64]
            error_type = data.get("error_type")
            if isinstance(error_type, str) and error_type:
                metadata["error_type"] = error_type[:128]
            duration = data.get("duration_ms")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                metadata["duration_ms"] = max(0, int(duration))
        if event_type in {"pre_approval_request", "post_approval_response"}:
            metadata["command"] = self._content_summary(data.get("command"))
            metadata["description"] = self._content_summary(data.get("description"))
            for field in ("surface", "choice", "decided_by"):
                value = data.get(field)
                if isinstance(value, str) and value:
                    metadata[field] = value[:64]
        if event_type in {"subagent_start", "subagent_stop"}:
            if event_type == "subagent_start":
                metadata["goal"] = self._content_summary(data.get("child_goal"))
            else:
                metadata["summary"] = self._content_summary(data.get("child_summary"))
                child_status = data.get("child_status")
                if isinstance(child_status, str) and child_status:
                    metadata["child_status"] = child_status[:64]
                duration = data.get("duration_ms")
                if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                    metadata["duration_ms"] = max(0, int(duration))
            child_role = data.get("child_role")
            if isinstance(child_role, str) and child_role:
                metadata["child_role"] = child_role[:64]
            for field in ("parent_session_id", "child_session_id"):
                value = data.get(field)
                if isinstance(value, str) and value:
                    metadata[field] = self._hash_text(value)[:23]
        if event_type == "pre_gateway_dispatch":
            event = data.get("event")
            metadata["text"] = self._content_summary(getattr(event, "text", None))
            message_type = getattr(event, "message_type", None)
            if message_type is not None:
                metadata["message_type"] = str(
                    getattr(message_type, "value", message_type)
                )[:64]
            media_urls = getattr(event, "media_urls", None)
            if isinstance(media_urls, list):
                metadata["media_count"] = len(media_urls)
            source = getattr(event, "source", None)
            platform = getattr(source, "platform", None)
            if platform is not None:
                metadata["platform"] = str(
                    getattr(platform, "value", platform)
                )[:64]
        encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        if len(encoded) > self.config.max_event_chars:
            return {
                "truncated": True,
                "digest": self._hash_text(encoded),
                "chars": len(encoded),
            }
        return metadata

    def _observe(self, event_type: str, data: Mapping[str, Any]) -> None:
        self._sequence += 1
        organism = self.organism
        tool_call_id = data.get("tool_call_id")
        correlation_ref = (
            self._hash_text(tool_call_id)
            if isinstance(tool_call_id, str) and tool_call_id
            else ""
        )
        action_id = correlation_ref or f"{event_type}:{self._sequence}"
        organism.senses.inhale(
            {
                "action_id": action_id,
                "event_type": event_type,
                "source": "hermes-plugin-hook",
                "metadata": self._metadata(event_type, data),
            }
        )
        if event_type == "post_tool_call":
            status = str(data.get("status") or "unknown")
            attempted = status in {"ok", "error"}
            ok = status == "ok"
            tool_name = str(data.get("tool_name") or "unknown")
            reason = "ok" if ok else str(data.get("error_type") or status)[:128]
            duration = data.get("duration_ms")
            evidence = {
                "source": "post_tool_call",
                "status": status[:64],
                "duration_ms": (
                    max(0, int(duration))
                    if isinstance(duration, (int, float)) and not isinstance(duration, bool)
                    else None
                ),
            }
            record_action_execution_proof(
                organism,
                tool_name,
                action_id=correlation_ref or action_id,
                attempted=attempted,
                ok=ok,
                method="Hermes dispatch" if attempted else None,
                ref=correlation_ref,
                reason=reason,
                actor="Body",
                authorship="BODY",
                timestamp=time.time(),
                evidence=[evidence],
            )
            if status == "blocked":
                organism.immune.event(
                    "host_tool_block",
                    {"tool": tool_name, "error_type": reason},
                )
            elif status == "error":
                organism.immune.event(
                    "host_tool_error",
                    {"tool": tool_name, "error_type": reason},
                )
            elif status != "ok":
                organism.immune.event(
                    "host_tool_status_invalid",
                    {"tool": tool_name, "status": status[:64]},
                )
        pulse = organism.heart.body_pulse(assemble=False)
        if self._scheduler is not None and isinstance(pulse.get("wake"), Mapping):
            self._scheduler.wake(dict(pulse["wake"]))
        if (
            not self.config.checkpoint_each_turn
            and event_type in {"on_session_end", "on_session_finalize"}
            and self._handle is not None
        ):
            save_resident(organism, self._handle.path)

    def _safe_observe(self, event_type: str, data: Mapping[str, Any]) -> None:
        with self._lock:
            try:
                self._observe(event_type, data)
            except Exception as exc:
                detail = {"event_type": event_type, "error_type": type(exc).__name__}
                if self._handle is not None:
                    try:
                        organism = self._handle.organism
                        organism.immune.event("hook_failure", detail)
                        save_resident(organism, self._handle.path)
                    except Exception:
                        pass
                self.diagnostics.append(detail)
                del self.diagnostics[:-100]

    def on_session_start(self, **kwargs: Any) -> None:
        self._safe_observe("on_session_start", kwargs)

    def on_session_end(self, **kwargs: Any) -> None:
        self._safe_observe("on_session_end", kwargs)

    def on_session_finalize(self, **kwargs: Any) -> None:
        self._safe_observe("on_session_finalize", kwargs)

    def pre_llm_call(self, **kwargs: Any) -> None:
        self._safe_observe("pre_llm_call", kwargs)

    def post_llm_call(self, **kwargs: Any) -> None:
        self._safe_observe("post_llm_call", kwargs)

    def pre_tool_call(self, **kwargs: Any) -> None:
        self._safe_observe("pre_tool_call", kwargs)

    def post_tool_call(self, **kwargs: Any) -> None:
        self._safe_observe("post_tool_call", kwargs)

    def pre_approval_request(self, **kwargs: Any) -> None:
        self._safe_observe("pre_approval_request", kwargs)

    def post_approval_response(self, **kwargs: Any) -> None:
        self._safe_observe("post_approval_response", kwargs)

    def subagent_start(self, **kwargs: Any) -> None:
        self._safe_observe("subagent_start", kwargs)

    def subagent_stop(self, **kwargs: Any) -> None:
        self._safe_observe("subagent_stop", kwargs)

    def pre_gateway_dispatch(self, **kwargs: Any) -> None:
        """Observe gateway ingress without rewriting, skipping, or authorizing it."""
        self._safe_observe("pre_gateway_dispatch", kwargs)


class RuntimeRegistry:
    """Resolve one locked resident per active Hermes home/profile at invocation time."""

    def __init__(
        self,
        config: ResidentConfig | None = None,
        *,
        profile_resolver: Callable[[], str],
        home_resolver: Callable[[], str | Path] | None = None,
        config_resolver: Callable[[], ResidentConfig] | None = None,
        model_factory: Callable[[], Any] | None = None,
        authority_provider_factory: Callable[[], Any] | None = None,
    ) -> None:
        if config is None and config_resolver is None:
            raise ValueError("config or config_resolver is required")
        self.config = config
        self._config_resolver = config_resolver or (lambda: config)  # type: ignore[return-value]
        self._profile_resolver = profile_resolver
        self._home_resolver = home_resolver or self._active_hermes_home
        self._model_factory = model_factory
        self._authority_provider_factory = authority_provider_factory
        self._lock = RLock()
        self._runtimes: dict[tuple[str, str], ResidentRuntime] = {}

    @staticmethod
    def _active_hermes_home() -> Path:
        from hermes_constants import get_hermes_home

        return get_hermes_home()

    def current(self) -> ResidentRuntime:
        home = Path(self._home_resolver()).expanduser().resolve()
        profile = self._profile_resolver()
        config = self._config_resolver()
        if not isinstance(config, ResidentConfig):
            raise TypeError("config_resolver must return ResidentConfig")
        key = (str(home), profile)
        with self._lock:
            runtime = self._runtimes.get(key)
            if runtime is None:
                runtime = ResidentRuntime(
                    config,
                    profile_id=profile,
                    hermes_home=home,
                    model_factory=self._model_factory,
                    authority_provider_factory=self._authority_provider_factory,
                )
                self._runtimes[key] = runtime
            return runtime

    def invoke(self, hook_name: str, **kwargs: Any) -> None:
        getattr(self.current(), hook_name)(**kwargs)
