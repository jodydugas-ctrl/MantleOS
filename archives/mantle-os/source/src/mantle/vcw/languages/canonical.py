#!/usr/bin/env python3
"""mantle.vcw.languages.canonical

The ONE canonical serialization + digest recipe (Forge v0.2 §16).

Two honest generators of the same registry/Manifest/codec MUST produce the
same digest. No Book may invent its own serialization.

Rules:
  * JSON: UTF-8, LF newlines, sort_keys=True, separators=(",", ":"),
    ensure_ascii=False, no insignificant whitespace.
  * Text artifacts: normalize CRLF/CR to LF before hashing.
  * Digests: "sha256:<64 lowercase hex>".
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

DIGEST_PREFIX = "sha256:"
_SHA256_HEX = re.compile(r"^sha256:[0-9a-f]{64}$")


def canonical_json_bytes(value: Any) -> bytes:
    """The fixed canonical JSON serialization for hashing."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def normalize_text(value: str) -> str:
    """LF newlines for text artifacts targeted by a digest."""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def sha256_id(data: bytes) -> str:
    return DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def text_digest(text: str) -> str:
    return sha256_id(normalize_text(text).encode("utf-8"))


def manifest_digest(manifest_without_self_digest: Any) -> str:
    """Digest of a manifest payload (self-referential digest excluded)."""
    return sha256_id(canonical_json_bytes(manifest_without_self_digest))


def registry_digest(registries: Any) -> str:
    """Digest of a Book's lane registries in canonical form."""
    return sha256_id(canonical_json_bytes(registries))


def codec_digest(source_bytes: bytes) -> str:
    """Digest of the pinned codec implementation (source bytes or pinned payload)."""
    return sha256_id(source_bytes)


def is_valid_digest(value) -> bool:
    return isinstance(value, str) and bool(_SHA256_HEX.match(value))
