#!/usr/bin/env python3
"""mantle.vcw.languages.framing

Composition + framing library (Forge v0.2 §11).

Framing IDs are cited by Books, never reinvented. Each member is a pure,
deterministic validator over a list of RGBA records. The first wave:

  * framed-run-v1        boundary supplied by container or explicit END;
                         empty frame invalid.
  * preorder-tree-v1     first record is root; arity/form in lane A drives
                         child count; children follow in preorder; consume
                         exactly one tree.
  * ordered-sequence-v1  sequence position is semantic; duplicate/regressed
                         ordinals rejected; frame boundary explicit.
  * referenced-graph-v1  generic reference resolver/validator (not claimed
                         measured/frozen until a Book exercises it).

These validators decide STRUCTURE. Lane semantics (what R/G/B/A mean) are the
Book's own lane contract.
"""
from __future__ import annotations

from typing import List, Protocol, Tuple

from .errors import EncodingRefused

RGBA = Tuple[int, int, int, int]
PARITY_ROLE = 0x7F
END_ROLE = 0x00


def _strip_end(pixels: List[RGBA]) -> List[RGBA]:
    """Remove a single terminal END sentinel (framed-run / unframed streams)."""
    if pixels and pixels[-1] == (0, 0, 0, 0):
        return pixels[:-1]
    return pixels


def parse_framed_run(pixels: List[RGBA]) -> List[RGBA]:
    """framed-run-v1: return the semantic body of one framed statement."""
    body = _strip_end(list(pixels))
    if not body:
        raise EncodingRefused("ambiguous-composition", "empty frame")
    return body


class FramingPolicy(Protocol):
    id: str
    def validate(self, pixels: List[RGBA]) -> List[RGBA]:
        ...


def arity_of(record: RGBA) -> int:
    """Read arity from lane A (preorder-tree-v1). 0 = leaf."""
    return record[3]


def validate_preorder_tree(pixels: List[RGBA]) -> List[RGBA]:
    """preorder-tree-v1: consume exactly one arity-driven tree.

    Returns the consumed records; raises EncodingRefused on truncation or
    trailing records.
    """
    body = _strip_end(list(pixels))
    if not body:
        raise EncodingRefused("ambiguous-composition", "empty tree frame")

    consumed: List[RGBA] = []
    # stack of (remaining_children_expected)
    stack: List[int] = []

    def push(record: RGBA) -> None:
        stack.append(arity_of(record))

    # Root
    consumed.append(body[0])
    push(body[0])

    for record in body[1:]:
        # pop completed parents
        while stack and stack[-1] == 0:
            stack.pop()
        if not stack:
            raise EncodingRefused("trailing-records",
                                  "records remain after complete tree")
        consumed.append(record)
        stack[-1] -= 1
        if arity_of(record) > 0:
            push(record)

    # after consumption, all parents must be satisfied
    while stack and stack[-1] == 0:
        stack.pop()
    if stack:
        raise EncodingRefused("truncated-structure",
                              "parent arity not fully consumed")
    return consumed


def validate_ordered_sequence(pixels: List[RGBA],
                              expected_count: int | None = None) -> List[RGBA]:
    """ordered-sequence-v1: sequence position is semantic.

    Each record's lane A carries the ordinal when ordinals are in-band;
    duplicate or regressed ordinals are rejected. A frame without declared
    ordinal-bearing records may instead rely on physical order; the validator
    still rejects regression when ordinals are present.
    """
    body = _strip_end(list(pixels))
    if not body:
        raise EncodingRefused("ambiguous-composition", "empty sequence frame")
    seen = -1
    for index, record in enumerate(body):
        ordinal = record[3]  # lane A ordinal, when used in-band
        if ordinal != 0:
            if ordinal <= seen:
                raise EncodingRefused("ambiguous-composition",
                                      "sequence ordinal %d regressed" % ordinal)
            seen = ordinal
    if expected_count is not None and len(body) != expected_count:
        raise EncodingRefused("ambiguous-composition",
                              "expected %d frames, got %d" %
                              (expected_count, len(body)))
    return body


# ---- generic reference resolver (referenced-graph-v1) --------------------- #

# A reference is an ordinary structured object; the resolver is provided so a
# Book that exercises it has a shared validator. NOT claimed measured/frozen
# until a Book actually exercises and measures it (Forge v0.2 §11).
def validate_reference(ref: dict) -> dict:
    required = {"generation", "layer_id", "book_id", "book_edition",
                "dialect_id", "dialect_edition", "address"}
    missing = required - set(ref)
    if missing:
        raise EncodingRefused("unresolved-reference",
                              "reference missing %s" % sorted(missing))
    for text_key in ("layer_id", "book_id", "book_edition",
                     "dialect_id", "dialect_edition"):
        if not isinstance(ref.get(text_key), str) or not ref[text_key]:
            raise EncodingRefused("unresolved-reference",
                                  "reference field %s must be text" % text_key)
    if not isinstance(ref.get("generation"), int):
        raise EncodingRefused("unresolved-reference", "generation must be int")
    return ref
