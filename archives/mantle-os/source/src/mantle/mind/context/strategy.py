"""Snapshot and rolling-prefix context strategies."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ...core.redact import redact
from .canonical import render_entries, sha256_hex
from .counter import ConservativeByteCounter, TokenCounter
from .ledger import ContextLedger
from .projection import build_delta
from .rollover import build_checkpoint
from .types import (
    CONTEXT_SCHEMA,
    RENDER_FORMAT,
    ROLLING_POLICY,
    ContextBudgetExceeded,
    ContextCapabilityUnavailable,
    ContextIntegrityError,
    ContextKey,
    ModelInfo,
    ModelRequest,
    PreparedContext,
    ProviderCapabilities,
    RollingContextConfig,
    SourceCursor,
)

_USAGE_FIELDS = frozenset({
    "model", "provider", "provider_name", "router", "session_id", "lane",
    "generation_id", "request_hash", "response_cache_status",
    "response_cache_age", "response_cache_ttl", "prompt_tokens",
    "completion_tokens", "total_tokens", "cached_tokens", "cache_write_tokens",
    "cache_discount", "cost", "total_cost", "upstream_inference_cost",
    "context_generation", "context_sequence", "stable_prefix_hash",
    "dynamic_suffix_hash", "context_request_hash",
})


def _safe_usage_receipt(usage: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        key: redact(value)
        for key, value in dict(usage or {}).items()
        if key in _USAGE_FIELDS
    }


def model_info_from_transport(model: Any) -> ModelInfo:
    capabilities = getattr(model, "capabilities", ProviderCapabilities())
    if isinstance(capabilities, dict):
        capabilities = ProviderCapabilities(**{
            name: bool(capabilities.get(name, False))
            for name in ProviderCapabilities.__dataclass_fields__
        })
    if not isinstance(capabilities, ProviderCapabilities):
        capabilities = ProviderCapabilities()
    return ModelInfo(
        provider=getattr(model, "provider", None),
        model=getattr(model, "model_name", getattr(model, "model", None)),
        context_window_tokens=getattr(model, "context_window_tokens", None),
        reserved_output_tokens=getattr(model, "reserved_output_tokens", None),
        capabilities=capabilities,
    )


class SnapshotContextStrategy:
    """The legacy prompt builder.  It intentionally has no durable side effects."""

    def __init__(self, frame: Callable[[Dict[str, Any]], str]) -> None:
        self._frame = frame

    def prepare(self, *, snapshot: Dict[str, Any], intent: Optional[str],
                model_info: ModelInfo) -> PreparedContext:
        del model_info
        frame = self._frame(snapshot)
        prompt = "%s\n\nINTENT:\n%s" % (frame, intent) if intent else frame
        raw = prompt.encode("utf-8")
        digest = sha256_hex(raw)
        return PreparedContext(
            prompt=prompt,
            prompt_bytes=raw,
            generation=0,
            sequence=0,
            request_hash=digest,
            prefix_hash=sha256_hex(b""),
            delta_hash=digest,
            intent_hash=sha256_hex((intent or "").encode("utf-8")),
            estimated_prompt_tokens=0,
            source_cursors_before=SourceCursor().as_dict(),
            source_cursors_after=SourceCursor().as_dict(),
        )

    def commit_success(self, prepared: PreparedContext, *, answer: str,
                       usage: Optional[Dict[str, Any]]) -> None:
        del prepared, answer, usage

    def commit_failure(self, prepared: PreparedContext, *,
                       error: BaseException) -> None:
        del prepared, error


class RollingPrefixContextStrategy:
    """A growing, immutable prefix with Body-owned prepare/commit semantics."""

    def __init__(
        self,
        organism: Any,
        config: RollingContextConfig,
        *,
        token_counter: Optional[TokenCounter] = None,
        key: Optional[ContextKey] = None,
    ) -> None:
        self.organism = organism
        self.config = config
        self.token_counter = token_counter or ConservativeByteCounter()
        self.key = key or ContextKey(
            body_fingerprint=(
                organism.body.key_fingerprint or organism.body.identity_name()
            ),
            lane=config.lane,
            task=config.task,
        )
        self.ledger = ContextLedger(
            organism, self.key, band=config.context_band
        )
        self._session_visible: List[Dict[str, Any]] = []
        self._prepared: Dict[str, PreparedContext] = {}
        self._force_new_session_generation = (
            config.persistence_mode != "durable-exact"
            and self.ledger.latest_open() is not None
        )

    def _open_data(self, snapshot: Dict[str, Any], model_info: ModelInfo,
                   cursor: SourceCursor) -> Dict[str, Any]:
        return {
            "policy": ROLLING_POLICY,
            "render_format": RENDER_FORMAT,
            "model": model_info.model,
            "provider": model_info.provider,
            "context_window_tokens": self.config.context_window_tokens,
            "reserved_output_tokens": self.config.reserved_output_tokens,
            "safety_margin_tokens": self.config.safety_margin_tokens,
            "rollover_threshold": self.config.rollover_threshold,
            "tokenizer": {
                "name": self.token_counter.name,
                "version": self.token_counter.version,
            },
            "source_cursors": cursor.as_dict(),
            "persistence_mode": self.config.persistence_mode,
            "provider_cache": self.config.provider_cache,
            "constitution": redact({
                "primer": snapshot.get("primer"),
                "identity": snapshot.get("identity"),
            }),
        }

    def _open_generation(
        self,
        generation: int,
        snapshot: Dict[str, Any],
        model_info: ModelInfo,
        cursor: SourceCursor,
        *,
        recovery: bool = False,
    ) -> Dict[str, Any]:
        data = self._open_data(snapshot, model_info, cursor)
        if recovery:
            data["recovery_from_corrupt_generation"] = generation - 1
        opened = self.ledger.append(
            "OPEN", generation, data, sequence=0, reset_chain=recovery
        )
        visible = self.ledger.model_visible(opened)
        if self.config.persistence_mode != "durable-exact":
            self._session_visible = [visible]
        return opened

    def _ensure_generation(self, snapshot: Dict[str, Any],
                           model_info: ModelInfo) -> int:
        opened = self.ledger.latest_open()
        if opened is None:
            self._open_generation(1, snapshot, model_info, SourceCursor())
            return 1
        generation = int(opened["generation"])
        if self._force_new_session_generation:
            self._open_generation(
                generation + 1, snapshot, model_info, SourceCursor()
            )
            self._force_new_session_generation = False
            return generation + 1
        try:
            self.ledger.require_active_valid()
        except ContextIntegrityError:
            generation += 1
            self._open_generation(
                generation, snapshot, model_info, SourceCursor(), recovery=True
            )
            return generation
        incompatible = (
            opened.get("render_format") != RENDER_FORMAT
            or opened.get("model") != model_info.model
            or opened.get("provider") != model_info.provider
            or opened.get("tokenizer") != {
                "name": self.token_counter.name,
                "version": self.token_counter.version,
            }
            or opened.get("persistence_mode") != self.config.persistence_mode
            or int(opened.get("context_window_tokens", 0))
            != self.config.context_window_tokens
        )
        if incompatible:
            return self._rollover(
                snapshot, model_info, reason="context_contract_changed"
            )
        return generation

    def _visible(self, generation: int) -> List[Dict[str, Any]]:
        if self.config.persistence_mode == "durable-exact":
            return self.ledger.visible_records(generation)
        return list(self._session_visible)

    def _rollover(self, snapshot: Dict[str, Any], model_info: ModelInfo,
                  *, reason: str) -> int:
        old_generation = self.ledger.active_generation()
        old_records = self.ledger.records()
        terminal_hash = old_records[-1].get("chain_hash", "") if old_records else ""
        cursor = self.ledger.latest_cursor(old_generation)
        self.ledger.append("ROLLOVER", old_generation, {
            "next_generation": old_generation + 1,
            "reason": reason,
            "final_prefix_hash": sha256_hex(
                render_entries(self._visible(old_generation))
            ),
            "ending_cursors": cursor.as_dict(),
        })
        generation = old_generation + 1
        opened = self._open_generation(generation, snapshot, model_info, cursor)
        checkpoint, checkpoint_cursor = build_checkpoint(
            snapshot,
            self.key,
            per_band=self.config.checkpoint_entries_per_band,
            closed_generation_hash=str(terminal_hash),
        )
        record = self.ledger.append("CHECKPOINT", generation, checkpoint)
        if self.config.persistence_mode != "durable-exact":
            self._session_visible = [
                self.ledger.model_visible(opened),
                self.ledger.model_visible(record),
            ]
        # A checkpoint is authoritative for the new generation's source position.
        self.ledger.append("COMMIT", generation, {
            "request_hash": "rollover-checkpoint",
            "source_cursors": checkpoint_cursor.as_dict(),
            "checkpoint_only": True,
        })
        return generation

    def prepare(self, *, snapshot: Dict[str, Any], intent: Optional[str],
                model_info: ModelInfo) -> PreparedContext:
        if (
            self.config.provider_cache == "required"
            and not model_info.capabilities.prefix_cache
        ):
            raise ContextCapabilityUnavailable(
                "provider_cache='required' but the transport reports no prefix cache"
            )
        generation = self._ensure_generation(snapshot, model_info)
        cursor = self.ledger.latest_cursor(generation)
        entries, after, source_range = build_delta(snapshot, cursor)
        request_sequence = self.ledger.next_sequence(generation)
        delta = {
            "context_schema": CONTEXT_SCHEMA,
            "context_key": self.key.as_dict(),
            "generation": generation,
            "kind": "DELTA",
            "source_range": source_range,
            "entries": entries,
        }
        delta["canonical_hash"] = sha256_hex(delta)
        intent_record = {
            "context_schema": CONTEXT_SCHEMA,
            "context_key": self.key.as_dict(),
            "generation": generation,
            "kind": "INTENT",
            "content": redact(intent or ""),
        }
        intent_record["content_hash"] = sha256_hex(intent_record["content"].encode("utf-8"))
        prefix_bytes = render_entries(self._visible(generation))
        delta_bytes = render_entries([delta]) if entries else b""
        intent_bytes = render_entries([intent_record])
        candidate = prefix_bytes + delta_bytes + intent_bytes
        prompt = candidate.decode("utf-8")
        estimated = self.token_counter.count_request(ModelRequest(prompt=prompt))
        delta_tokens = self.token_counter.count_text(delta_bytes.decode("utf-8"))
        if (
            self.config.max_delta_tokens is not None
            and delta_tokens > self.config.max_delta_tokens
        ):
            self.organism.immune_event("context_delta_too_large", {
                "estimated_delta_tokens": delta_tokens,
                "limit": self.config.max_delta_tokens,
            })
            raise ContextBudgetExceeded("rolling context delta exceeds max_delta_tokens")
        if estimated > self.config.rollover_budget:
            generation = self._rollover(
                snapshot, model_info, reason="token_threshold"
            )
            cursor = self.ledger.latest_cursor(generation)
            entries, after, source_range = build_delta(snapshot, cursor)
            request_sequence = self.ledger.next_sequence(generation)
            delta = replace_delta(
                delta, generation, entries, source_range
            )
            intent_record = replace_intent(
                intent_record, generation
            )
            prefix_bytes = render_entries(self._visible(generation))
            delta_bytes = render_entries([delta]) if entries else b""
            intent_bytes = render_entries([intent_record])
            candidate = prefix_bytes + delta_bytes + intent_bytes
            prompt = candidate.decode("utf-8")
            estimated = self.token_counter.count_request(ModelRequest(prompt=prompt))
            if estimated > self.config.rollover_budget:
                self.organism.immune_event("context_budget_exceeded", {
                    "estimated_prompt_tokens": estimated,
                    "rollover_budget": self.config.rollover_budget,
                    "hard_input_budget": self.config.hard_input_budget,
                })
                raise ContextBudgetExceeded(
                    "checkpoint plus active intent exceeds the rollover budget"
                )
        request_hash = sha256_hex(candidate)
        request_data: Dict[str, Any] = {
            "prefix_hash": sha256_hex(prefix_bytes),
            "delta_hash": sha256_hex(delta_bytes),
            "intent_hash": intent_record["content_hash"],
            "request_hash": request_hash,
            "estimated_prompt_tokens": estimated,
            "input_budget": self.config.hard_input_budget,
            "context_entries": len(self._visible(generation)) + bool(entries) + 1,
            "source_cursors_before": cursor.as_dict(),
            "source_cursors_after": after.as_dict(),
        }
        # A REQUEST carries hashes only.  In `durable-exact` the sent bytes are
        # already reproducible by re-rendering this generation's committed
        # visible chain, so storing the whole prompt here would duplicate the
        # entire prefix once per round and grow the ledger quadratically.
        request = self.ledger.append(
            "REQUEST", generation, request_data, sequence=request_sequence
        )
        prepared = PreparedContext(
            prompt=prompt,
            prompt_bytes=candidate,
            generation=generation,
            sequence=int(request["sequence"]),
            request_hash=request_hash,
            prefix_hash=request_data["prefix_hash"],
            delta_hash=request_data["delta_hash"],
            intent_hash=request_data["intent_hash"],
            estimated_prompt_tokens=estimated,
            source_cursors_before=cursor.as_dict(),
            source_cursors_after=after.as_dict(),
            ledger_entry_hashes=(str(request["record_hash"]),),
            delta_record=delta if entries else None,
            intent_record=intent_record,
            request_record_hash=str(request["record_hash"]),
        )
        self._prepared[request_hash] = prepared
        return prepared

    def commit_success(self, prepared: PreparedContext, *, answer: str,
                       usage: Optional[Dict[str, Any]]) -> None:
        if prepared.request_hash not in self._prepared:
            raise ContextIntegrityError("prepared request is unknown or already committed")
        generation = prepared.generation
        exact = self.config.persistence_mode == "durable-exact"
        committed_visible: List[Dict[str, Any]] = []
        if prepared.delta_record is not None:
            data = dict(prepared.delta_record)
            data["request_hash"] = prepared.request_hash
            if exact:
                record = self.ledger.append("DELTA", generation, data)
                committed_visible.append(self.ledger.model_visible(record))
            else:
                # The id range is not content: it is what lets chain verification
                # prove the commit below never advances past an included entry.
                self.ledger.append("DELTA_RECEIPT", generation, {
                    "request_hash": prepared.request_hash,
                    "canonical_hash": prepared.delta_record["canonical_hash"],
                    "source_range": prepared.delta_record["source_range"],
                })
                committed_visible.append({
                    key: value for key, value in data.items()
                    if key != "request_hash"
                })
        intent = dict(prepared.intent_record or {})
        intent["request_hash"] = prepared.request_hash
        if exact:
            record = self.ledger.append("INTENT", generation, intent)
            committed_visible.append(self.ledger.model_visible(record))
        else:
            self.ledger.append("INTENT_RECEIPT", generation, {
                "request_hash": prepared.request_hash,
                "content_hash": prepared.intent_hash,
            })
            committed_visible.append({
                key: value for key, value in intent.items()
                if key != "request_hash"
            })
        redacted_answer = str(redact(answer))
        response = {
            "request_hash": prepared.request_hash,
            "content": redacted_answer,
            "content_hash": sha256_hex(redacted_answer.encode("utf-8")),
            "generation_id": (usage or {}).get("generation_id"),
        }
        if exact:
            record = self.ledger.append("RESPONSE", generation, response)
            committed_visible.append(self.ledger.model_visible(record))
        else:
            self.ledger.append("RESPONSE_RECEIPT", generation, {
                "request_hash": prepared.request_hash,
                "content_hash": response["content_hash"],
                "generation_id": response["generation_id"],
            })
            committed_visible.append({
                "context_schema": CONTEXT_SCHEMA,
                "context_key": self.key.as_dict(),
                "generation": generation,
                "kind": "RESPONSE",
                **{
                    key: value for key, value in response.items()
                    if key != "request_hash"
                },
            })
        receipt = _safe_usage_receipt(usage)
        reported = int(receipt.get("prompt_tokens", 0) or 0)
        receipt.update({
            "request_hash": prepared.request_hash,
            "estimated_prompt_tokens": prepared.estimated_prompt_tokens,
            "reported_prompt_tokens": reported,
            "estimation_error": (
                reported - prepared.estimated_prompt_tokens if reported else None
            ),
            "prefix_hash": prepared.prefix_hash,
            "delta_hash": prepared.delta_hash,
        })
        self.ledger.append("RECEIPT", generation, receipt)
        self.ledger.append("COMMIT", generation, {
            "request_hash": prepared.request_hash,
            "source_cursors": prepared.source_cursors_after,
        })
        if not exact:
            self._session_visible.extend(committed_visible)
        del self._prepared[prepared.request_hash]

    def commit_failure(self, prepared: PreparedContext, *,
                       error: BaseException) -> None:
        self.ledger.append("FAILURE", prepared.generation, {
            "request_hash": prepared.request_hash,
            "error": {
                "type": type(error).__name__,
                "message": redact(str(error)[:512]),
            },
            "source_cursors": prepared.source_cursors_before,
        })
        self._prepared.pop(prepared.request_hash, None)


def replace_delta(record: Dict[str, Any], generation: int,
                  entries: List[Dict[str, Any]],
                  source_range: Dict[str, List[int]]) -> Dict[str, Any]:
    value = dict(record)
    value.update({
        "generation": generation,
        "source_range": source_range,
        "entries": entries,
    })
    value.pop("canonical_hash", None)
    value["canonical_hash"] = sha256_hex(value)
    return value


def replace_intent(record: Dict[str, Any], generation: int) -> Dict[str, Any]:
    value = dict(record)
    value["generation"] = generation
    return value