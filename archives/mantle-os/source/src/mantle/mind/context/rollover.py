"""Deterministic context-generation checkpoint construction."""
from __future__ import annotations

from typing import Any, Dict, Tuple

from ...core.redact import redact
from .canonical import sha256_hex
from .projection import checkpoint_projection
from .types import ContextKey, SourceCursor


def build_checkpoint(
    snapshot: Dict[str, Any],
    key: ContextKey,
    *,
    per_band: int,
    closed_generation_hash: str,
) -> Tuple[Dict[str, Any], SourceCursor]:
    entries, cursor = checkpoint_projection(snapshot, per_band=per_band)
    checkpoint = {
        "checkpoint_schema": "mantle-context-checkpoint-v1",
        "context_key": key.as_dict(),
        "constitution": {
            "primer": redact(snapshot.get("primer")),
            "identity": redact(snapshot.get("identity")),
        },
        "entries": entries,
        "source_cursors": cursor.as_dict(),
        "closed_generation_hash": closed_generation_hash,
    }
    checkpoint["checkpoint_hash"] = sha256_hex(checkpoint)
    return checkpoint, cursor
