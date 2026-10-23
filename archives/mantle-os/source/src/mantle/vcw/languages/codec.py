#!/usr/bin/env python3
"""mantle.vcw.languages.codec

The codec interface every forged Book must provide (Forge v0.2 §15).

A codec transforms between a canonical structured value and RGBA records,
performing the Book's lane contract. Books implement the methods; the
registry and drivers call them through this protocol.

Required API (stdlib-only; deterministic):
    encode(value, *, frame_id=None) -> list[RGBA]
    decode(records, *, frame_id=None) -> canonical value
    validate_records(records) -> None        (raise on any violation)
    canonicalize(value) -> value
    encode_entries(value) -> list[RGBA]      (optional; entry_stream drivers)
    selftest() -> report dict

A codec never invents meaning while decoding. It raises EncodingRefused
(ENCODING REFUSED: <code>) rather than guessing.
"""
from __future__ import annotations

from typing import Any, List, Protocol, Tuple, runtime_checkable

RGBA = Tuple[int, int, int, int]


@runtime_checkable
class BookCodec(Protocol):
    """The deterministic, stdlib-only codec contract for a forged Book."""

    def encode(self, value: Any, *, frame_id: str | None = None) -> List[RGBA]:
        ...

    def decode(self, records: List[RGBA], *, frame_id: str | None = None) -> Any:
        ...

    def validate_records(self, records: List[RGBA]) -> None:
        ...

    def canonicalize(self, value: Any) -> Any:
        ...

    def selftest(self) -> dict:
        ...

    def encode_entries(self, value: Any, *, frame_id: str | None = None) -> List[RGBA]:
        ...
