#!/usr/bin/env python3
"""mantle.vcw.languages.adoption

Body/operator adoption receipts (Forge v0.2 §3 axis b, §14).

Decoded/valid/canonical/verified are computed metadata. ADOPTED means the
Body has explicitly authorized this exact Book/dialect for this layer scope.
GOVERNING additionally requires the relevant Body authority policy.

Only operator/Body code may create an adoption receipt. The MIND has no
adoption capability. A CANDIDATE Book may be authorized only for
quarantine/test, never governing.

Functions here are the registry-sided helpers; the Body owns the durable
receipt store (core.body body.language_adoptions).
"""
from __future__ import annotations

from typing import Dict, List

from .errors import EncodingRefused
from .types import LIFECYCLE_STATES, BookKey, key_tuple

ADOPTION_KINDS = (
    "vcw_language_forge_adoption",
    "vcw_book_adoption",
    "vcw_genome_profile_adoption",
    "spore_agent_book_adoption",
)


def make_book_adoption(*, key: BookKey, status: str,
                       registry_sha256: str, codec_sha256: str,
                       selftest_sha256: str = "",
                       measurement_sha256: str = "",
                       operator_authorized: bool = True,
                       default_scope: str = "new-tissue-only",
                       legacy_reinterpretation: bool = False,
                       commit: str = "") -> Dict[str, object]:
    """Build a vcw_book_adoption receipt (validated shape)."""
    if status not in LIFECYCLE_STATES:
        raise EncodingRefused("book-missing",
                              "adoption status must be a lifecycle state")
    if status != "FROZEN":
        # CANDIDATE may be authorized only for quarantine/test — encode that
        # in default_scope; the governing gate separately refuses non-FROZEN.
        pass
    if default_scope not in ("new-tissue-only", "quarantine-test", "governing"):
        raise EncodingRefused("book-missing",
                              "unknown adoption scope %r" % (default_scope,))
    return {
        "kind": "vcw_book_adoption",
        "book": key_tuple(key),
        "status": status,
        "registry_sha256": registry_sha256,
        "codec_sha256": codec_sha256,
        "selftest_sha256": selftest_sha256,
        "measurement_sha256": measurement_sha256,
        "operator_authorized": bool(operator_authorized),
        "default_scope": default_scope,
        "legacy_reinterpretation": bool(legacy_reinterpretation),
        "commit": commit,
    }


def requires_frozen_for_governing(status: str) -> None:
    """Governing scope requires FROZEN; nothing less may govern."""
    if status != "FROZEN":
        raise EncodingRefused(
            "book-missing",
            "Book status %s cannot govern; only FROZEN may" % status)


def policy_from_receipts(receipts: List[Dict[str, object]], *,
                         book_id: str, book_edition: str,
                         dialect_id: str, dialect_edition: str) -> str:
    """Return the highest authority scope a receipt grants: governing >
    quarantine-test > none. Presence of a receipt is not governing unless the
    receipt explicitly says governing scope."""
    target = (book_id, book_edition, dialect_id, dialect_edition)
    result = "none"
    for receipt in receipts:
        if receipt.get("kind") != "vcw_book_adoption":
            continue
        if tuple(receipt.get("book", ())) != target:
            continue
        scope = receipt.get("default_scope", "new-tissue-only")
        if scope == "governing":
            return "governing"
        if scope in ("quarantine-test", "new-tissue-only"):
            result = scope
    return result
