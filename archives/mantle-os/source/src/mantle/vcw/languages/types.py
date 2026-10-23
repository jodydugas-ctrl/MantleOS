#!/usr/bin/env python3
"""mantle.vcw.languages.types

Core identity and state types for the VCW Language Forge / Tome / Book
architecture (documents/vcw/languages/VCW_LANGUAGE_FORGE_v0.2.md).

Two axes are kept strictly separate (Forge v0.2 §3):

  * Artifact lifecycle  CANDIDATE -> FROZEN -> SUPERSEDED  (or REFUSED)
  * Record conformance  DECODED -> VALID -> CANONICAL -> VERIFIED ->
                        ADOPTED -> GOVERNING

A Book can be FROZEN while a record written under it is merely DECODED.
A record is never promoted by confidence; only by passing the Book's tests
plus, for ADOPTED/GOVERNING, an explicit Body/operator authority step.

Pure standard library; deterministic; no dependency on mantle.mind.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

# --------------------------------------------------------------------------- #
# Schema + catalogue constants                                                #
# --------------------------------------------------------------------------- #

BOOK_SCHEMA = "vcw-book-v1"
FORGE_SCHEMA = "vcw-forge-v1"

# Forge v0.2 §6 Tome categories.
TOME_CATEGORIES = frozenset({
    "COMPUTATION", "COMMUNICATION", "EPISTEMIC", "TOOLS", "SENSORY",
    "STATE", "AGENT", "SPATIAL", "OPERATIONAL", "MIXED", "OTHER",
})

# Artifact lifecycle (axis a).
LIFECYCLE_STATES = ("CANDIDATE", "FROZEN", "SUPERSEDED", "REFUSED")

# Record conformance ladder (axis b).
CONFORMANCE_STATES = (
    "DECODED", "VALID", "CANONICAL", "VERIFIED", "ADOPTED", "GOVERNING",
)

# Allocation policies (Forge v0.2 §10).
ALLOCATION_POLICIES = (
    "FIXED", "DIALECT-ALLOCATED", "LOCAL-FROZEN", "EXTERNAL-STANDARD",
)

# Framing and integrity library IDs (Forge v0.2 §11, §12).
FRAMING_IDS = frozenset({
    "framed-run-v1", "preorder-tree-v1", "ordered-sequence-v1",
    "referenced-graph-v1", "flat-record-v1",
})
INTEGRITY_IDS = frozenset({
    "rotated-parity-rgba-v1",   # authoritative; covers all four lanes
    "xor-parity-rba-v1",        # legacy/draft; G lane uncovered
    "full-lane-fingerprint-v1", # whole-transport fingerprint
    "none-declared",            # no statement-local integrity
})

# Adoption/policy states in drivers (Forge v0.2 §3, Grimoire S8).
ADOPTION_POLICIES = ("data", "quote", "quarantine", "adopted")


# --------------------------------------------------------------------------- #
# Core identity types                                                         #
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class BookKey:
    """The exact identity of a language: a Book at an edition in a dialect.

    Nothing is ever selected by filename, band name, layer number, color,
    neighbouring layers, or model confidence. Only this explicit key may
    select a language (Forge v0.2 §1.3, §4).
    """
    book_id: str
    book_edition: str
    dialect_id: str
    dialect_edition: str

    def __str__(self) -> str:
        return (f"{self.book_id}@{self.book_edition}/"
                f"{self.dialect_id}@{self.dialect_edition}")


@dataclass(frozen=True)
class BookManifest:
    """Machine-readable identity + contract for a forged Book.

    schema: BOOK_SCHEMA ("vcw-book-v1")
    status: lifecycle state (LIFECYCLE_STATES)
    registry_digest: sha256:<hex> over the Book's lane registries
    codec_digest:    sha256:<hex> over the pinned codec payload
    """
    schema: str = BOOK_SCHEMA
    category: str = "OTHER"
    status: str = "CANDIDATE"
    key: BookKey = field(default_factory=lambda: BookKey("", "", "", ""))
    allocation_policy: str = "FIXED"
    framing_id: str = "framed-run-v1"
    integrity_id: str = "none-declared"
    lane_mapping: str = "identity"
    lane_questions: Dict[str, str] = field(default_factory=dict)
    registry_digest: str = ""
    codec_digest: str = ""
    source_digest: Optional[str] = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.schema != BOOK_SCHEMA:
            raise ValueError("BookManifest schema must be %s" % BOOK_SCHEMA)
        if self.category not in TOME_CATEGORIES:
            raise ValueError("unknown Tome category %r" % (self.category,))
        if self.status not in LIFECYCLE_STATES:
            raise ValueError("unknown lifecycle state %r" % (self.status,))
        if self.allocation_policy not in ALLOCATION_POLICIES:
            raise ValueError("unknown allocation policy %r" %
                             (self.allocation_policy,))
        if self.framing_id not in FRAMING_IDS:
            raise ValueError("unknown framing id %r" % (self.framing_id,))
        if self.integrity_id not in INTEGRITY_IDS:
            raise ValueError("unknown integrity id %r" % (self.integrity_id,))
        lane_keys = set(self.lane_questions)
        if lane_keys != {"R", "G", "B", "A"}:
            raise ValueError("lane_questions must define exactly R, G, B, A")
        for lane, question in self.lane_questions.items():
            if not isinstance(question, str) or not question.strip():
                raise ValueError("lane %s question must be one sentence" % lane)
        if self.status == "FROZEN" and not (self.registry_digest
                                            and self.codec_digest):
            raise ValueError("FROZEN Book requires registry + codec digests")


def manifest_key(manifest: BookManifest) -> BookKey:
    return manifest.key


def key_tuple(key: BookKey) -> tuple:
    return (key.book_id, key.book_edition, key.dialect_id, key.dialect_edition)
