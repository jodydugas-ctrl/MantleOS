"""Bounded JSON validation for the current AGENTIC profile."""
import json, re
MAX_SOURCE_BYTES = 32768
MAX_JSON_BYTES = 65536
MAX_HISTORY_BYTES = 262144
NAME = r"[A-Za-z][A-Za-z0-9_]*"
TOOL_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")

class AgenticError(ValueError):
    """Invalid source, model response, tool registration or budget."""


def _json_bytes(value: object, *, limit: int = MAX_JSON_BYTES) -> bytes:
    try:
        blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise AgenticError("NON_JSON_VALUE") from exc
    if len(blob) > limit:
        raise AgenticError("JSON_LIMIT_EXCEEDED")
    return blob


def _decode(raw: str) -> object:
    def no_duplicate(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise AgenticError("DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    def no_constant(_):
        raise AgenticError("NONFINITE_JSON_VALUE")
    try:
        data = json.loads(raw, object_pairs_hook=no_duplicate, parse_constant=no_constant)
    except (ValueError, UnicodeError) as exc:
        raise AgenticError("INVALID_JSON") from exc
    _json_bytes(data)
    return data

