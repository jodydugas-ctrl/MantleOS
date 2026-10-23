"""Foreign Food parsing and the minimal OpenRouter MIND transport."""

from __future__ import annotations

import hashlib
import http.client
import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_FOOD_BYTES = 8_192
MAX_PROVIDER_OUTPUT_TOKENS = 8_192
MAX_PROVIDER_RESPONSE_BYTES = 1_048_576
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._~:/-]+$")


class NutritionError(RuntimeError):
    """Food could not be safely parsed, stored, or tested."""


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Credentials and private context are authorized for one endpoint only.
        raise NutritionError("OpenRouter redirect refused")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _refuse_constant(value: str) -> None:
    raise ValueError("non-finite JSON constant")


def _completion_from_bytes(raw: bytes) -> dict[str, Any]:
    """Validate the text-only adapter result before any Body admission.

    Optional provider envelope metadata is not an instruction or a receipt.
    Only the declared fields below cross this boundary; no returned tools run.
    """
    if not raw or len(raw) > MAX_PROVIDER_RESPONSE_BYTES:
        raise NutritionError("OpenRouter response exceeds the bounded text profile")
    try:
        result = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_refuse_constant
        )
        if not isinstance(result, dict) or result.get("error") is not None:
            raise ValueError("provider error or invalid envelope")
        choices = result["choices"]
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError("one completion required")
        choice = choices[0]
        if (
            not isinstance(choice, dict)
            or choice.get("finish_reason") != "stop"
            or choice.get("error") is not None
        ):
            raise ValueError("incomplete completion")
        message = choice["message"]
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise ValueError("unexpected message role")
        if message.get("tool_calls") or message.get("function_call") or message.get("refusal"):
            raise ValueError("unsupported tools or refusal")
        content = message["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty completion")
        content.encode("utf-8")  # Reject escaped lone surrogates; preserve valid text exactly.
        model, response_id = result["model"], result["id"]
        for identifier in (model, response_id):
            if not isinstance(identifier, str) or not 1 <= len(identifier) <= 256:
                raise ValueError("missing or oversized provider identity")
            if not MODEL_PATTERN.fullmatch(identifier):
                raise ValueError("invalid provider identity")
            if identifier.startswith(("sk-", "ghp_", "github_pat_")):
                raise ValueError("credential-shaped provider identity")
        usage = result.get("usage")
        safe_usage = {}
        if isinstance(usage, dict):
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = usage.get(key)
                if type(value) is int and 0 <= value <= 2**63 - 1:
                    safe_usage[key] = value
            cost = usage.get("cost")
            if type(cost) in (int, float) and 0 <= cost <= 2**63 - 1 and math.isfinite(cost):
                safe_usage["cost"] = cost
    except (UnicodeError, ValueError, KeyError, IndexError, TypeError, RecursionError):
        # Never include provider bytes, error messages, or duplicate key names.
        raise NutritionError("OpenRouter returned an invalid or incomplete text completion") from None
    return {
        "content": content,
        "selected_model": model,
        "response_id": response_id,
        "usage": safe_usage,
    }


@dataclass(frozen=True)
class OpenRouterFood:
    api_key: str
    model: str
    source_sha256: str
    key_fingerprint: str


def parse_openrouter_food(raw: bytes) -> OpenRouterFood:
    if not raw or len(raw) > MAX_FOOD_BYTES:
        raise NutritionError("Food must contain between 1 and 8192 bytes")
    source_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        lines = [line.strip() for line in raw.decode("utf-8-sig").splitlines() if line.strip()]
    except UnicodeDecodeError as exc:
        raise NutritionError("Food is not UTF-8 text") from exc
    if len(lines) != 2:
        raise NutritionError("OpenRouter Food must contain exactly a key line and a model line")
    api_key, model = lines
    if not api_key.startswith("sk-or-v1-") or len(api_key) < 32:
        raise NutritionError("The first Food line is not an OpenRouter key")
    if not MODEL_PATTERN.fullmatch(model):
        raise NutritionError("The second Food line is not a safe OpenRouter model identifier")
    return OpenRouterFood(
        api_key=api_key,
        model=model,
        source_sha256=source_sha256,
        key_fingerprint=hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16],
    )


def openrouter_completion(
    api_key: str,
    model: str,
    message: str,
    *,
    max_tokens: int = 256,
    timeout: float = 45.0,
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": max(1, min(max_tokens, MAX_PROVIDER_OUTPUT_TOKENS)),
            "temperature": 0,
            "stream": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENROUTER_CHAT_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MantleOS/2",
            "X-OpenRouter-Title": "MantleOS",
        },
    )
    try:
        opener = urllib.request.build_opener(_RefuseRedirect())
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise NutritionError(f"OpenRouter rejected the request with HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        raise NutritionError(f"OpenRouter could not be reached ({type(exc).__name__})") from None
    return _completion_from_bytes(raw)


def verify_openrouter_food(food: OpenRouterFood) -> dict[str, Any]:
    result = openrouter_completion(
        food.api_key,
        food.model,
        "Credential verification only. Reply with the exact text MANTLE_BODY_OK.",
        # The free router may select a reasoning model. Leave enough room for
        # hidden reasoning plus the short visible verification response.
        max_tokens=256,
    )
    return {
        "ok": True,
        "requested_model": food.model,
        "selected_model": result["selected_model"],
        "response_id": result["response_id"],
        "response_chars": len(result["content"]),
        "usage": result["usage"],
    }
