"""Transport-segment reconstruction (correctness before optimization).

The default remote NEST carries ONE complete content-addressed VCW checkpoint
per commit (a single, self-contained recovery unit). Segments are an OPTIONAL
transport optimization -- they are never a second memory model, and they may
only be adopted once exact reconstruction equivalence is proven.

This module provides the equivalence gate GHNEST-20 enforces: a split payload
must reconstruct to the exact canonical bytes (or a matching fingerprint), and a
tampered segment must be detected. Segments are not yet used as the canonical
carrier; the gate is proven now so that adopting them later cannot regress
reconstruction.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Optional

from .manifest import sha256_bytes


class SegmentError(Exception):
    pass


@dataclass(frozen=True)
class SegmentHeader:
    total: int
    index: int
    payload_sha256: str


def _split_n(data: bytes, n: int) -> List[bytes]:
    if n <= 0:
        raise SegmentError("segment count must be positive")
    if n == 1:
        return [data]
    size = max(1, (len(data) + n - 1) // n)
    return [data[i:i + size] for i in range(0, len(data), size)]


def slice_segments(data: bytes, n: int) -> List[SegmentHeader]:
    """Split ``data`` into ``n`` ordered segment headers (content+index)."""
    parts = _split_n(data, n)
    return [SegmentHeader(total=n, index=i, payload_sha256=sha256_bytes(p))
            for i, p in enumerate(parts)]


def segment_payload(h: SegmentHeader) -> bytes:
    """Serialize a header's bindings without the payload (for integrity)."""
    return json.dumps(
        {"total": h.total, "index": h.index, "payload_sha256": h.payload_sha256},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def reconstruct(parts: List[SegmentHeader], get_payload) -> bytes:
    """Reassemble ordered segments into the exact canonical bytes.

    ``get_payload(header)`` returns that segment's raw bytes. Reconstruction is
    accepted only if every segment's digest matches and the assembly equals the
    full canonical payload (fingerprint equivalence). A tampered or reordered
    segment raises :class:`SegmentError`.
    """
    if not parts:
        raise SegmentError("no segments to reconstruct")
    ordered = sorted(parts, key=lambda h: h.index)
    if [h.index for h in ordered] != list(range(len(ordered))):
        raise SegmentError("segment index set is not contiguous/labelled")
    if any(h.total != ordered[0].total for h in ordered):
        raise SegmentError("inconsistent segment total count")
    chunks = []
    for h in ordered:
        payload = get_payload(h)
        if sha256_bytes(payload) != h.payload_sha256:
            raise SegmentError("segment %d payload digest mismatch (tampered)" % h.index)
        chunks.append(payload)
    return b"".join(chunks)


def fingerprint_equal(assembled: bytes, canonical_sha256: str) -> bool:
    return bool(canonical_sha256) and sha256_bytes(assembled) == canonical_sha256
