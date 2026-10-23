#!/usr/bin/env python3
"""mantle.vcw.languages.manifest

Book manifest construction + structural validation.

A manifest is the machine-readable identity contract of a forged Book.
The digest fields are computed over the canonical serialization
(languages.canonical). A FROZEN Book must carry registry + codec digests.

This module implements manifest *validation* and *digest computation*; the
actual Book registry (register_book / get_book) lives in languages.registry.
"""
from __future__ import annotations

from typing import Any, Dict

from .canonical import canonical_json_bytes, codec_digest, registry_digest
from .errors import EncodingRefused
from .types import (
    ALLOCATION_POLICIES,
    BOOK_SCHEMA,
    FRAMING_IDS,
    INTEGRITY_IDS,
    LIFECYCLE_STATES,
    TOME_CATEGORIES,
    BookKey,
    BookManifest,
)

REQUIRED_MANIFEST_KEYS = {
    "schema", "category", "status", "book_id", "book_edition",
    "dialect_id", "dialect_edition", "allocation_policy",
    "framing_id", "integrity_id", "lane_mapping",
    "lanes",        # {"R": {"question": ..., "registry": {...}}, ...}
    "registry_digest", "codec_digest",
}


def manifest_from_dict(data: Dict[str, Any]) -> BookManifest:
    """Validate a manifest mapping and return an immutable BookManifest.

    Refuses on: wrong schema, unknown category/state/policy/framing/integrity,
    missing lane questions, FROZEN without digests.
    """
    if not isinstance(data, dict):
        raise EncodingRefused("book-missing", "manifest must be a mapping")
    missing = REQUIRED_MANIFEST_KEYS - set(data)
    if missing:
        raise EncodingRefused("book-missing",
                              "manifest missing keys: %s" % sorted(missing))
    if data["schema"] != BOOK_SCHEMA:
        raise EncodingRefused("book-missing",
                              "manifest schema must be %s" % BOOK_SCHEMA)
    if data["category"] not in TOME_CATEGORIES:
        raise EncodingRefused("unknown-value",
                              "unknown category %r" % (data["category"],))
    if data["status"] not in LIFECYCLE_STATES:
        raise EncodingRefused("unknown-value",
                              "unknown lifecycle %r" % (data["status"],))
    if data["allocation_policy"] not in ALLOCATION_POLICIES:
        raise EncodingRefused("unknown-value",
                              "unknown allocation policy %r" %
                              (data["allocation_policy"],))
    if data["framing_id"] not in FRAMING_IDS:
        raise EncodingRefused("unknown-value",
                              "unknown framing id %r" % (data["framing_id"],))
    if data["integrity_id"] not in INTEGRITY_IDS:
        raise EncodingRefused("unknown-value",
                              "unknown integrity id %r" % (data["integrity_id"],))

    lanes = data.get("lanes")
    if not isinstance(lanes, dict) or set(lanes) != {"R", "G", "B", "A"}:
        raise EncodingRefused("registry-missing",
                              "lanes must define exactly R, G, B, A")
    for lane, spec in lanes.items():
        if not isinstance(spec, dict) or "question" not in spec:
            raise EncodingRefused("registry-missing",
                                  "lane %s missing its question" % lane)
        if not isinstance(spec["question"], str) or not spec["question"].strip():
            raise EncodingRefused("registry-missing",
                                  "lane %s question must be one sentence" % lane)

    key = BookKey(
        book_id=str(data["book_id"]),
        book_edition=str(data["book_edition"]),
        dialect_id=str(data["dialect_id"]),
        dialect_edition=str(data["dialect_edition"]),
    )
    return BookManifest(
        schema=BOOK_SCHEMA,
        category=data["category"],
        status=data["status"],
        key=key,
        allocation_policy=data["allocation_policy"],
        framing_id=data["framing_id"],
        integrity_id=data["integrity_id"],
        lane_mapping=str(data.get("lane_mapping", "identity")),
        lane_questions={lane: lanes[lane]["question"] for lane in ("R", "G", "B", "A")},
        registry_digest=str(data.get("registry_digest", "")),
        codec_digest=str(data.get("codec_digest", "")),
        source_digest=data.get("source_digest"),
        description=str(data.get("description", "")),
    )


def compute_manifest_digests(manifest_dict: Dict[str, Any],
                             codec_source: bytes | None = None,
                             registries: Dict[str, Any] | None = None) -> Dict[str, str]:
    """Compute the manifest's digest fields over canonical serializations."""
    payload = {k: v for k, v in manifest_dict.items()
               if k not in ("registry_digest", "codec_digest",
                            "source_digest", "description")}
    from .canonical import manifest_digest as _manifest_digest
    digests: Dict[str, str] = {
        "registry_digest": (registry_digest(registries)
                            if registries is not None else ""),
        "codec_digest": (codec_digest(codec_source)
                         if codec_source is not None else ""),
        "source_digest": _manifest_digest(payload),
    }
    return digests


def validate_frozen_completeness(manifest: BookManifest) -> None:
    """A FROZEN Book must have complete digests and not claim more than verified."""
    if manifest.status == "FROZEN":
        from .canonical import is_valid_digest
        if not (is_valid_digest(manifest.registry_digest)
                and is_valid_digest(manifest.codec_digest)):
            raise EncodingRefused(
                "registry-missing",
                "FROZEN Book requires valid registry + codec digests")
