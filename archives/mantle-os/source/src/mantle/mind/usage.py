#!/usr/bin/env python3
"""
mantle.mind.usage  --  normalized MODEL usage receipts (Mantle OS)

Provider usage is transport tissue, not Body doctrine. This module turns the
OpenAI-compatible/OpenRouter-style response shapes into a small redacted receipt
that can be traced, metered, and audited without storing raw prompts, completions,
or credentials.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Mapping, Optional


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v if v is not None else default)
    except (TypeError, ValueError):
        return default


def _float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v if v is not None else default)
    except (TypeError, ValueError):
        return default


def _headers(headers: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not headers:
        return out
    for k, v in dict(headers).items():
        out[str(k).lower()] = str(v)
    return out


def sha16(data: Any) -> str:
    """Short stable hash for receipts."""
    if isinstance(data, bytes):
        raw = data
    else:
        raw = str(data).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def canonical_json_bytes(payload: Dict[str, Any]) -> bytes:
    """Deterministic JSON for repeatable response-cache request bodies."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def stable_session_id(body_fingerprint: str, lane: str, task: str,
                      prefix: str = "mantle") -> str:
    """Build a sticky-routing session id that fits OpenRouter's 256-char limit."""
    def clean(s: str) -> str:
        s = re.sub(r"[^A-Za-z0-9_.:-]+", "-", str(s)).strip("-")
        return s or "unknown"
    base = "%s:%s:%s:%s" % (clean(prefix), clean(body_fingerprint)[:24],
                            clean(lane)[:48], clean(task)[:120])
    if len(base) <= 256:
        return base
    digest = sha16(base)
    return "%s:%s" % (base[:239], digest)


def normalize_usage(response: Optional[Dict[str, Any]] = None, *,
                    headers: Optional[Mapping[str, Any]] = None,
                    generation: Optional[Dict[str, Any]] = None,
                    session_id: Optional[str] = None,
                    request_hash: Optional[str] = None,
                    stable_prefix_hash: Optional[str] = None,
                    dynamic_suffix_hash: Optional[str] = None,
                    lane: Optional[str] = None,
                    model: Optional[str] = None) -> Dict[str, Any]:
    """Return the small receipt Mantle is allowed to remember.

    `response` is a chat-completions response body. `generation` may be either
    the OpenRouter `/generation` body or its inner `data` object.
    """
    response = response or {}
    usage = response.get("usage", {}) or {}
    details = usage.get("prompt_tokens_details", {}) or {}
    cost_details = usage.get("cost_details", {}) or {}
    hdr = _headers(headers)
    gen = (generation or {}).get("data", generation or {}) or {}
    gen_id = (hdr.get("x-generation-id") or response.get("id") or gen.get("id"))
    requested_model = model
    response_model = response.get("model")
    generation_model = gen.get("model")
    resolved_model = response_model or generation_model or requested_model
    model_evidence = (
        "provider_response" if response_model else
        "generation_receipt" if generation_model else
        "requested_only" if requested_model else
        "unknown"
    )

    receipt: Dict[str, Any] = {
        # Keep `model` request-oriented for compatibility, while preserving the
        # provider-reported route result as separate observed evidence.
        "model": requested_model or resolved_model,
        "requested_model": requested_model,
        "response_model": response_model,
        "generation_model": generation_model,
        "resolved_model": resolved_model,
        "model_evidence": model_evidence,
        "provider_name": gen.get("provider_name"),
        "router": gen.get("router"),
        "session_id": session_id or gen.get("session_id"),
        "lane": lane,
        "generation_id": gen_id,
        "request_hash": request_hash,
        "stable_prefix_hash": stable_prefix_hash,
        "dynamic_suffix_hash": dynamic_suffix_hash,
        "response_cache_status": hdr.get("x-openrouter-cache-status"),
        "response_cache_age": _int(hdr.get("x-openrouter-cache-age"), 0),
        "response_cache_ttl": _int(hdr.get("x-openrouter-cache-ttl"), 0),
        "prompt_tokens": _int(usage.get("prompt_tokens", gen.get("tokens_prompt"))),
        "completion_tokens": _int(usage.get("completion_tokens",
                                            gen.get("tokens_completion"))),
        "total_tokens": _int(usage.get("total_tokens")),
        "cached_tokens": _int(details.get("cached_tokens",
                                          gen.get("native_tokens_cached"))),
        "cache_write_tokens": _int(details.get("cache_write_tokens")),
        "cache_discount": _float(response.get("cache_discount",
                                              gen.get("cache_discount")), 0.0),
        "cost": _float(usage.get("cost", gen.get("usage")), 0.0),
        "total_cost": _float(response.get("total_cost", gen.get("total_cost")), 0.0),
        "upstream_inference_cost": _float(
            cost_details.get("upstream_inference_cost",
                             gen.get("upstream_inference_cost")), 0.0),
    }
    if receipt["total_tokens"] == 0:
        receipt["total_tokens"] = receipt["prompt_tokens"] + receipt["completion_tokens"]
    return receipt


def receipt_cost(receipt: Optional[Dict[str, Any]]) -> float:
    """The cost Mantle should charge when a provider receipt is available."""
    receipt = receipt or {}
    return _float(receipt.get("total_cost") or receipt.get("cost"), 0.0)
