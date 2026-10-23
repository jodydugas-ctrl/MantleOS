#!/usr/bin/env python3
"""
mantle.core.refs  --  the unified reference resolver (Mantle OS)

One grammar addresses everything the organism can remember:

    <TARGET . SELECTOR . ADDRESS>

    TARGET    cube              -> the current PRIME cube              (default if omitted)
    .         gen2 / shard2     -> a specific retained generation      (shard = legacy alias)
    .         body              -> the Body's mutable store
    SELECTOR  a band/layer name (facts, immune, calendar) or a Body category (primer, immune)
    ADDRESS   11                -> visible entry #11
    .         23x33             -> coordinate (x=23, y=33)
    .         (omitted)         -> the whole band/category

Examples:
    <facts.11>         Prime, facts band, visible entry 11
    <gen2.boot.23x33>  generation 2, that layer, pixel (23,33)
    <body.immune.11>   Body, immunization store, entry 11

A reference that resolves to nothing is a DANGLING reference: it becomes an immune event,
never a silent drop. Resolution is deterministic -- same organism state, same answer.
"""
from __future__ import annotations

import re
from typing import Any, Optional, Tuple

_GEN_RE = re.compile(r"^(?:gen|shard)(\d+)$", re.IGNORECASE)
_COORD_RE = re.compile(r"^(\d+)x(\d+)$", re.IGNORECASE)
_INT_RE = re.compile(r"^\d+$")
_TARGETS = ("cube", "prime", "body")


def parse(ref: str) -> Tuple[str, str, Optional[Any]]:
    """Return (target, selector, address). target is 'cube', 'body', or 'genN'."""
    s = ref.strip().lstrip("<").rstrip(">").strip()
    parts = [p for p in s.split(".") if p != ""]
    if not parts:
        raise ValueError("empty reference")

    first = parts[0].lower()
    if first in _TARGETS or _GEN_RE.match(first):
        target = "cube" if first in ("cube", "prime") else first
        rest = parts[1:]
    else:
        target = "cube"
        rest = parts

    if not rest:
        raise ValueError("reference %r has no selector" % ref)
    selector = rest[0]
    address: Optional[Any] = None
    if len(rest) >= 2:
        addr = rest[1]
        m = _COORD_RE.match(addr)
        if m:
            address = (int(m.group(1)), int(m.group(2)))
        elif _INT_RE.match(addr):
            address = int(addr)
        else:
            address = addr
    return target, selector, address


def resolve(organism, ref: str) -> Any:
    """Resolve a reference against an Organism. Dangling -> immune event, returns None."""
    try:
        target, selector, address = parse(ref)
    except ValueError as e:
        organism.immune_event("malformed_ref", {"ref": ref, "error": str(e)})
        return None

    # ---- the Body, addressed like a layer --------------------------------
    if target == "body":
        try:
            if address is None:
                return organism.body.category(selector)
            return organism.body.get(selector, int(address))
        except (KeyError, TypeError, ValueError):
            organism.immune_event("dangling_ref", {"ref": ref, "where": "body"})
            return None

    # ---- a cube (prime or a specific generation) -------------------------
    if target == "cube":
        cube = organism.prime
    else:
        gen = int(_GEN_RE.match(target).group(1))
        cube = organism.cube_for_generation(gen)
        if cube is None:
            organism.immune_event("dangling_ref", {"ref": ref, "missing_generation": gen})
            return None

    if selector not in cube.bands:
        organism.immune_event("dangling_ref", {"ref": ref, "missing_band": selector})
        return None

    if address is None:
        return cube.read(selector)
    if cube.encoding(selector) == "log-json":
        try:
            int(address)
        except (TypeError, ValueError):
            organism.immune_event("malformed_ref", {
                "ref": ref, "band": selector, "address": address,
                "error": "log-json addresses must be integer entry ids"})
            return None
    try:
        result = cube.retrieve(selector, address)
    except (TypeError, ValueError) as e:
        organism.immune_event("malformed_ref", {"ref": ref, "error": str(e)})
        return None
    if result is None:
        organism.immune_event("dangling_ref", {"ref": ref, "address": address})
    return result
