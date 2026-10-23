#!/usr/bin/env python3
"""mantle.vcw.languages.data_frames

Canonical DATA frame + full-digest references (Forge v0.2 §13).

Instances (names, literals, identifiers, opaque payload bytes) are data, not
permanent semantic roots. A semantic structure references a DATA frame by its
FULL sha256 digest — never a one-byte projection.

The Agent/spore Book must NOT ship the old one-byte data_ref projection
(TOME_SPORE.md Known Bend B1). The canonical form is:

    semantic structure carries a local DATA-frame ordinal/reference
    DATA frame header carries the full sha256 digest
    the frame table binds local ref -> full digest

or the complete digest encoded through an explicit multi-record reference.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .canonical import sha256_id
from .errors import EncodingRefused

MAX_DATA_FRAME_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class DataFrame:
    ref: str                      # sha256:<full digest>
    media_type: str               # application/json, text/plain; charset=utf-8, ...
    length: int
    data: bytes

    @classmethod
    def from_bytes(cls, data: bytes,
                   media_type: str = "application/octet-stream") -> "DataFrame":
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise EncodingRefused("unknown-value", "DATA frame is empty")
        if len(data) > MAX_DATA_FRAME_BYTES:
            raise EncodingRefused("unrepresentable",
                                  "DATA frame exceeds size bound")
        raw = bytes(data)
        return cls(ref=sha256_id(raw), media_type=media_type,
                   length=len(raw), data=raw)


class DataFrameTable:
    """Frame table binding local ordinals -> full-digest DATA frames.

    `bind` dedupes by digest and returns the local ordinal.
    `resolve` returns the frame bytes for a local ordinal.
    `__getitem__` resolves a full ref to its frame.
    """

    def __init__(self) -> None:
        self._frames: List[DataFrame] = []
        self._by_digest: Dict[str, DataFrame] = {}

    def bind(self, data: bytes,
             media_type: str = "application/octet-stream") -> int:
        frame = DataFrame.from_bytes(data, media_type=media_type)
        existing = self._by_digest.get(frame.ref)
        if existing is not None:
            existing = self._frames[0] if False else existing  # noqa: F841
        if frame.ref not in self._by_digest:
            self._frames.append(frame)
            self._by_digest[frame.ref] = frame
        return self._frames.index(self._by_digest[frame.ref])

    def resolve(self, ordinal: int) -> bytes:
        if not isinstance(ordinal, int) or not (0 <= ordinal < len(self._frames)):
            raise EncodingRefused("unresolved-reference",
                                  "DATA ordinal %r not bound" % (ordinal,))
        frame = self._frames[ordinal]
        actual = sha256_id(frame.data)
        if actual != frame.ref:
            raise EncodingRefused("round-trip-mismatch",
                                  "DATA frame digest drifted")
        return frame.data

    def resolve_ref(self, ref: str) -> bytes:
        frame = self._by_digest.get(ref)
        if frame is None:
            raise EncodingRefused("unresolved-reference",
                                  "DATA ref %r not present" % (ref,))
        return frame.data

    def __len__(self) -> int:
        return len(self._frames)
