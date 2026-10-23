#!/usr/bin/env python3
"""mantle.vcw.languages.integrity

Integrity members (Forge v0.2 §12).

The modern, mandatory member is `rotated-parity-rgba-v1`:
  * It is the adopted Grimoire v0.10 parity algorithm.
  * It covers ALL FOUR lanes (R, G, B, A) via position-weighted rotation.
  * It is DELEGATED to the frozen v010 implementation (grimoire_editions),
    never independently reimplemented with subtly different behavior.

`xor-parity-rba-v1` is kept ONLY for decoding legacy/draft material that
declares it; it leaves the G lane uncovered and must not be used for newly
frozen safety-bearing Books.

`full-lane-fingerprint-v1` is whole-transport integrity: a SHA-256 over raw
semantic frame bytes + frame index + frame boundary. It is separate from
statement-local parity.

Integrity is detection, not prevention. Anything not covered is UNMEASURED.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable, List, Tuple

from ..grimoire_editions.v010 import (
    parity_pixel as _v010_parity_pixel,
    raw_run_fingerprint as _v010_raw_run_fingerprint,
)

RGBA = Tuple[int, int, int, int]
PARITY_ROLE = 0x7F


def rotated_parity_pixel(records: List[RGBA]) -> RGBA:
    """rotated-parity-rgba-v1: the adopted v0.10 algorithm (all four lanes).

    Delegated to the FROZEN implementation so behavior is byte-for-byte
    identical to every existing v0.10 vector.
    """
    return _v010_parity_pixel(records)


def verify_rotated_parity(records: List[RGBA], *, label: str = "statement") -> None:
    """Verify the terminal PARITY record of a statement (rotated member).

    Raises ValueError on mismatch, exactly as the frozen codec does.
    """
    if not records:
        raise ValueError("%s: blank statement" % label)
    if records[-1][1] != PARITY_ROLE:
        raise ValueError("%s: missing terminal PARITY" % label)
    expected = rotated_parity_pixel(records[:-1])
    if expected != records[-1]:
        raise ValueError("%s: PARITY mismatch" % label)


def xor_parity_pixel(records: List[RGBA]) -> RGBA:
    """xor-parity-rba-v1 (legacy/draft only): lane-wise XOR of R, B, A.

    G is NOT covered. Retained for decoding legacy material that declares it;
    new safety-bearing Books must use rotated-parity-rgba-v1.
    """
    xr = xb = xa = 0
    for index, (r, g, b, a) in enumerate(records):
        if g == PARITY_ROLE:
            continue
        xr ^= r
        xb ^= b
        xa ^= a
    return (0xFE if xr == 0 else xr, PARITY_ROLE, xb, xa)


def verify_xor_parity(records: List[RGBA], *, label: str = "statement") -> None:
    if not records:
        raise ValueError("%s: blank statement" % label)
    if records[-1][1] != PARITY_ROLE:
        raise ValueError("%s: missing terminal PARITY" % label)
    expected = xor_parity_pixel(records[:-1])
    if expected != records[-1]:
        raise ValueError("%s: PARITY mismatch" % label)


def full_lane_fingerprint(raw: bytes, frame_id: str, *,
                          include_data_frames: bool = False,
                          data_bytes: Iterable[bytes] = ()) -> str:
    """full-lane-fingerprint-v1: whole-transport SHA-256.

    Covers: frame_id, raw semantic RGBA frame bytes, and optionally DATA
    frames when the carrier claims those frames are covered.
    Delegates to the frozen v0.10 fingerprint for the raw frame portion so the
    result byte-matches existing carriers.
    """
    h = hashlib.sha256()
    base = _v010_raw_run_fingerprint(raw, frame_id)
    h.update(base.encode("utf-8"))
    if include_data_frames:
        for data in data_bytes:
            h.update(b"\x00")
            h.update(data)
    return "sha256:" + h.hexdigest()
