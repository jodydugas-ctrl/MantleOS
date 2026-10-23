#!/usr/bin/env python3
"""mantle.vcw.languages.errors

Fixed refusal codes (Forge v0.2 §18) and the canonical EncodingRefused error.

The user-facing canonical message is always:

    ENCODING REFUSED: <code>

A decoder/encoder NEVER substitutes a guessed value. Refusal preserves the
VCW better than plausible semantic corruption (Forge v0.2 §1.5, §18).
"""
from __future__ import annotations

# The fixed registry of refusal codes (Forge v0.2 §18).
REFUSAL_CODES = frozenset({
    "book-missing",
    "edition-missing",
    "registry-missing",
    "unknown-value",
    "ambiguous-composition",
    "illegal-role",
    "truncated-structure",
    "trailing-records",
    "arity-mismatch",
    "missing-required-role",
    "duplicate-forbidden-role",
    "unresolved-reference",
    "unrepresentable",
    "round-trip-mismatch",
})

ENCODING_REFUSED_PREFIX = "ENCODING REFUSED:"


class EncodingRefused(ValueError):
    """The canonical refusal. Never catches and guesses around it."""

    def __init__(self, code: str, detail: str = ""):
        if code not in REFUSAL_CODES:
            # Structural invariant: a program must not mint new refusal codes.
            raise ValueError("unknown refusal code %r" % (code,))
        self.code = code
        self.detail = detail
        message = "%s %s" % (ENCODING_REFUSED_PREFIX, code)
        if detail:
            message += "  (%s)" % detail
        super().__init__(message)
