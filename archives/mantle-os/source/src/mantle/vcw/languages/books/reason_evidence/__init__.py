#!/usr/bin/env python3
"""mantle.vcw.languages.books.reason_evidence

reason-evidence@0.10 / mantle-standard@0.10 — the OPERATIONAL Tome, FROZEN,
implementation lineage grimoire-v0.10.

Importing this package registers the Book with the module-level registry
(languages.registry.REGISTRY). Selection is by exact BookKey only; the codec
delegates to the frozen Grimoire v0.10 implementation so every existing v0.10
byte decodes identically.

The User Language, Computational Thought and Agent Instruction Tomes are
CANDIDATE and deliberately NOT registered here yet (Forge §23 freeze gate).
"""
from __future__ import annotations

import os

from ...canonical import codec_digest
from ...registry import RegisteredBook, register_book
from .codec import ReasonEvidenceCodec, build_manifest, lane_registries

_CODEC = ReasonEvidenceCodec()

# Pin the codec digest to THIS implementation's file bytes so the registry
# refuses if the implementation drifts (checkout-stable: the same file bytes
# always yield the same digest).
_CODEC_SOURCE = open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "codec.py"),
    "rb",
).read()
_MANIFEST = build_manifest(codec_digest(_CODEC_SOURCE))

register_book(RegisteredBook(
    manifest=_MANIFEST,
    codec=_CODEC,
    registries=lane_registries(),
    codec_source=_CODEC_SOURCE,
))

Book = _MANIFEST

__all__ = ["_MANIFEST", "_CODEC", "_CODEC_SOURCE", "Book", "build_manifest",
           "lane_registries", "ReasonEvidenceCodec"]
