#!/usr/bin/env python3
"""
mantle.mind.transport  --  pluggable model transports (Mantle OS)

THE MODEL IS A PLUGGABLE TRANSPORT -- THERE IS NO VENDOR CODE IN THE BODY. The MIND talks
to its model through a single callable `model(prompt) -> text`. The offline deterministic
`stub_mind` is the default: the demo and the Stage-2 audit need no network and no key.
`openai_compatible_model(...)` (pure stdlib urllib, built lazily) reaches ANY
OpenAI-compatible endpoint -- OpenRouter is the reference gateway, a local llama.cpp/vLLM
server works identically. You change providers by changing a STRING, never Body code.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

from .context.types import (
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_GENERATION_URL = "https://openrouter.ai/api/v1/generation"


def stub_mind(prompt: str) -> str:
    """An offline, deterministic stand-in MODEL so demos + the Stage-2 audit need no key
    or network. Mirrors the rest of the framework's 'no network, no LLM' ethos."""
    return ("[offline MIND] The assembled context reads as coherent; I note it and propose "
            "no Body change. (%d chars of context considered.)" % len(prompt))


stub_mind.provider = "offline"  # type: ignore[attr-defined]
stub_mind.model_name = "mantle/stub"  # type: ignore[attr-defined]
stub_mind.capabilities = ProviderCapabilities()  # type: ignore[attr-defined]


def complete_model(model: Any, request: ModelRequest) -> ModelResponse:
    """Use optional structured completion while preserving ``prompt -> text``."""
    complete = getattr(model, "complete", None)
    if callable(complete):
        response = complete(request)
        if isinstance(response, ModelResponse):
            return response
        if isinstance(response, str):
            return ModelResponse(
                text=response,
                usage=getattr(model, "last_usage", None),
                generation_id=getattr(model, "last_generation_id", None),
            )
        if isinstance(response, dict) and isinstance(response.get("text"), str):
            return ModelResponse(
                text=response["text"],
                usage=response.get("usage"),
                generation_id=response.get("generation_id"),
            )
        raise TypeError("structured model transport returned an invalid response")
    text = model(request.prompt)
    if not isinstance(text, str):
        raise TypeError("model transport must return text")
    return ModelResponse(
        text=text,
        usage=getattr(model, "last_usage", None),
        generation_id=getattr(model, "last_generation_id", None),
    )


def load_keyfile(path: str) -> str:
    """Read the single model credential from a keyfile (Phase 2 only). The value is a
    secret boundary: it is redacted everywhere it could surface in senses/immune logs."""
    with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
        return f.read().strip()


def openai_compatible_model(api_key: str, model: str, *, url: str = OPENROUTER_URL,
                            system: Optional[str] = None, max_tokens: int = 1024,
                            context_window_tokens: Optional[int] = None,
                            timeout: int = 60,
                            extra_headers: Optional[Dict[str, str]] = None,
                            session_id: Optional[str] = None,
                            cache_control: Optional[Dict[str, Any]] = None,
                            response_cache: bool = False,
                            response_cache_ttl: Optional[int] = None,
                            response_cache_clear: bool = False,
                            generation_url: Optional[str] = None,
                            audit_generation: bool = False,
                            lane: Optional[str] = None,
                            request_shaper: Optional[
                                Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
                            ) -> Callable[[str], str]:
    """Return a `model(prompt) -> text` callable for ANY OpenAI-compatible chat endpoint.
    Pure standard library (urllib), imported lazily: importing this module never requires
    a network or a key. No vendor SDK, ever.

    The callable contract stays `model(prompt) -> text`. Usage/cache facts are exposed as
    sidecar attributes (`last_usage`, `last_headers`, `last_generation_id`,
    `last_request_hash`, `last_requested_model`, `last_response_model`, and
    `last_resolved_model`) so MIND callers do not need a new interface.
    """
    if session_id is not None and len(session_id) > 256:
        raise ValueError("session_id must be at most 256 characters")
    import urllib.request  # local import: only touched when a real model is wired
    import urllib.parse

    from .usage import canonical_json_bytes, normalize_usage, sha16

    def _fetch_generation(gen_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not (audit_generation and gen_id):
            return None
        gen_url = generation_url or OPENROUTER_GENERATION_URL
        q = urllib.parse.urlencode({"id": gen_id})
        sep = "&" if "?" in gen_url else "?"
        req = urllib.request.Request(gen_url + sep + q,
                                     headers={"Authorization": "Bearer %s" % api_key},
                                     method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _call(prompt: str) -> str:
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload_obj: Dict[str, Any] = {"model": model, "messages": messages,
                                       "max_tokens": max_tokens}
        if session_id:
            payload_obj["session_id"] = session_id
        if cache_control:
            payload_obj["cache_control"] = dict(cache_control)
        if request_shaper:
            payload_obj = request_shaper(payload_obj)
        payload = canonical_json_bytes(payload_obj)
        headers = {"Authorization": "Bearer %s" % api_key,
                   "Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        if session_id:
            headers.setdefault("x-session-id", session_id)
        if response_cache:
            headers["X-OpenRouter-Cache"] = "true"
            if response_cache_ttl is not None:
                headers["X-OpenRouter-Cache-TTL"] = str(int(response_cache_ttl))
            if response_cache_clear:
                headers["X-OpenRouter-Cache-Clear"] = "true"
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_headers = dict(resp.headers.items())
            data = json.loads(resp.read().decode("utf-8"))
        gen_id = resp_headers.get("X-Generation-Id") or resp_headers.get("x-generation-id") \
            or data.get("id")
        generation = _fetch_generation(gen_id)
        receipt = normalize_usage(data, headers=resp_headers, generation=generation,
                                  session_id=session_id,
                                  request_hash=sha16(payload),
                                  stable_prefix_hash=sha16(system or ""),
                                  dynamic_suffix_hash=sha16(prompt),
                                  lane=lane, model=model)
        _call.last_usage = receipt
        _call.last_headers = resp_headers
        _call.last_generation_id = receipt.get("generation_id")
        _call.last_request_hash = receipt.get("request_hash")
        _call.last_requested_model = receipt.get("requested_model")
        _call.last_response_model = receipt.get("response_model")
        _call.last_resolved_model = receipt.get("resolved_model")
        _call.last_model_evidence = receipt.get("model_evidence")
        _call.last_cache = {
            "status": receipt.get("response_cache_status"),
            "cached_tokens": receipt.get("cached_tokens", 0),
            "cache_write_tokens": receipt.get("cache_write_tokens", 0),
        }
        return data["choices"][0]["message"]["content"]

    _call.last_usage = None       # type: ignore[attr-defined]
    _call.last_headers = None     # type: ignore[attr-defined]
    _call.last_generation_id = None   # type: ignore[attr-defined]
    _call.last_request_hash = None    # type: ignore[attr-defined]
    _call.last_requested_model = model  # type: ignore[attr-defined]
    _call.last_response_model = None    # type: ignore[attr-defined]
    _call.last_resolved_model = None    # type: ignore[attr-defined]
    _call.last_model_evidence = "requested_only"  # type: ignore[attr-defined]
    _call.last_cache = None       # type: ignore[attr-defined]
    _call.provider = "openai-compatible"  # type: ignore[attr-defined]
    _call.model_name = model      # type: ignore[attr-defined]
    _call.reserved_output_tokens = max_tokens  # type: ignore[attr-defined]
    _call.context_window_tokens = context_window_tokens  # type: ignore[attr-defined]
    _call.capabilities = ProviderCapabilities(  # type: ignore[attr-defined]
        prefix_cache=bool(cache_control),
        explicit_cache_breakpoints=bool(cache_control),
        response_cache=response_cache,
        reports_cached_tokens=True,
        reports_context_limit=False,
        structured_messages=True,
    )
    return _call


def openrouter_model(api_key: str, model: str, **kwargs: Any) -> Callable[[str], str]:
    """The reference transport: OpenAI-compatible, pointed at OpenRouter. `model` is a
    provider-neutral id string; provider choice is one string, the Body is identical."""
    kwargs.setdefault("url", OPENROUTER_URL)
    return openai_compatible_model(api_key, model, **kwargs)
