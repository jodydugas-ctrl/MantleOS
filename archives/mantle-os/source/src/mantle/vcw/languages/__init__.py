#!/usr/bin/env python3
"""mantle.vcw.languages

The VCW Language Forge / Tome / Book subsystem (Forge v0.2).

A generic, deterministic, stdlib-only language layer beside — never inside —
the frozen Grimoire implementation. Modules:

  types       BookKey / BookManifest / lifecycle + conformance axes
  errors      fixed refusal codes + EncodingRefused
  canonical   one canonical serialization + digest recipe
  codec       the Book codec protocol
  manifest    manifest construction + validation
  registry    the Body-approved Book registry (selection by exact key)
  framing     framing library (framed-run / preorder-tree / sequence / graph)
  integrity   rotated (authoritative) + xor (legacy) parity, full-lane digest
  data_frames canonical DATA frames + full-digest references
  adoption    Body/operator adoption receipts

Books (immutable language artifacts) live under languages.books.

Presence is not authority. Decoding is not adoption. Force is not
authorization. No model promotes a Book, record, rule, or carrier by
confidence or by wording.
"""
from __future__ import annotations

from . import adoption  # noqa: F401
from .canonical import (
    canonical_json_bytes,
    codec_digest,
    is_valid_digest,
    manifest_digest,
    normalize_text,
    registry_digest,
    sha256_id,
    text_digest,
)
from .codec import BookCodec  # noqa: F401
from .errors import ENCODING_REFUSED_PREFIX, REFUSAL_CODES, EncodingRefused
from .registry import (
    REGISTRY,
    BookRegistry,
    RegisteredBook,
    get_book,
    known_books,
    make_key,
    register_book,
    verify_registered_book,
)
from .types import (
    ADOPTION_POLICIES,
    ALLOCATION_POLICIES,
    BOOK_SCHEMA,
    CONFORMANCE_STATES,
    FRAMING_IDS,
    FORGE_SCHEMA,
    INTEGRITY_IDS,
    LIFECYCLE_STATES,
    TOME_CATEGORIES,
    BookKey,
    BookManifest,
)

__all__ = [
    "canonical_json_bytes", "codec_digest", "is_valid_digest",
    "manifest_digest", "normalize_text", "registry_digest", "sha256_id",
    "text_digest",
    "ENCODING_REFUSED_PREFIX", "REFUSAL_CODES", "EncodingRefused",
    "REGISTRY", "BookRegistry", "RegisteredBook", "get_book", "known_books",
    "make_key", "register_book", "verify_registered_book",
    "ADOPTION_POLICIES", "ALLOCATION_POLICIES", "BOOK_SCHEMA",
    "CONFORMANCE_STATES", "FRAMING_IDS", "FORGE_SCHEMA", "INTEGRITY_IDS",
    "LIFECYCLE_STATES", "TOME_CATEGORIES", "BookKey", "BookManifest",
]
