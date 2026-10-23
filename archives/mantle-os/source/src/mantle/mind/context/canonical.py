"""Canonical bytes for immutable model-visible context entries."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_json_bytes(value)
    return hashlib.sha256(raw).hexdigest()


def render_entry(value: Dict[str, Any]) -> bytes:
    payload = canonical_json_bytes(value)
    return (
        b"MANTLE-CONTEXT-ENTRY/1\n"
        + ("length:%d\n" % len(payload)).encode("ascii")
        + ("sha256:%s\n\n" % hashlib.sha256(payload).hexdigest()).encode("ascii")
        + payload
        + b"\n"
    )


def render_entries(values: Iterable[Dict[str, Any]]) -> bytes:
    return b"".join(render_entry(value) for value in values)


def chain_hash(previous_hash: str, value: Dict[str, Any]) -> str:
    previous = bytes.fromhex(previous_hash) if previous_hash else b""
    return hashlib.sha256(previous + canonical_json_bytes(value)).hexdigest()
