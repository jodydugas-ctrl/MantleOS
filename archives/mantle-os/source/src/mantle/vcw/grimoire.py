#!/usr/bin/env python3
"""
mantle.vcw.grimoire  --  GRIMOIRE v0.9 VCW software profile (Mantle OS)

This module makes the v0.9 Grimoire executable as a VCW carrier/profile without making
it the universal meaning of RGBA. The cube still supplies booted substrate hardware; this
profile supplies one decoder for semantic pixel runs: R=atom, G=role, B=evidence,
A=force.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Tuple


PROFILE = "grimoire-v0.9"
BYTE_ORDER = "RGBA"

ROLES: Dict[int, str] = {
    0x00: "END",
    0x01: "HEAD",
    0x02: "AGENT",
    0x03: "PATIENT",
    0x04: "THEME",
    0x05: "EXPERIENCER",
    0x06: "INSTRUMENT",
    0x07: "SOURCE",
    0x08: "GOAL",
    0x09: "RECIPIENT",
    0x0a: "BENEFICIARY",
    0x20: "LOCATION",
    0x21: "TIME",
    0x22: "MANNER",
    0x23: "PATH",
    0x24: "EXTENT",
    0x25: "CAUSE",
    0x26: "PURPOSE",
    0x27: "CONDITION",
    0x28: "CONCESSION",
    0x29: "SCOPE",
    0x2a: "COMPARISON",
    0x2b: "QUANTITY",
    0x2c: "PREREQUISITE",
    0x40: "BLEND",
    0x41: "QUALIFY",
    0x42: "INTENSIFY",
    0x43: "DIMINISH",
    0x60: "STEP_1",
    0x61: "STEP_2",
    0x62: "STEP_3",
    0x63: "STEP_4",
    0x64: "STEP_5",
    0x65: "STEP_6",
    0x66: "STEP_7",
    0x67: "STEP_8",
    0x68: "STEP_9",
    0x69: "STEP_10",
    0x6a: "STEP_11",
    0x6b: "STEP_12",
    0x6c: "STEP_13",
    0x6d: "STEP_14",
    0x6e: "STEP_15",
    0x6f: "STEP_16",
    0x70: "ALT",
    0x71: "CONJ",
    0x72: "REF",
    0x73: "SUPERSEDE",
    0x74: "VOID",
    0x75: "DENOTES",
    0x7f: "PARITY",
}

EVIDENCE: Dict[int, str] = {
    0x00: "INHERIT",
    0x01: "DIRECT",
    0x02: "MEASURED",
    0x03: "CITED",
    0x04: "INFERRED",
    0x05: "REMEMBERED",
    0x06: "REPORTED",
    0x07: "ASSUMED",
    0x08: "STIPULATED",
    0x09: "UNKNOWN",
}

FORCE: Dict[int, str] = {
    0x00: "INHERIT",
    0x01: "LAW",
    0x02: "MUST",
    0x03: "DUTY",
    0x04: "NEVER",
    0x05: "NEED",
    0x06: "GATE",
    0x07: "BOUND",
    0x08: "RULE",
    0x09: "RIGHT",
    0x0a: "POWER",
    0x0b: "CAN",
    0x0c: "LET",
    0x0d: "MAY",
    0x0e: "WAY",
    0x0f: "QUOTE",
}

SELFTEST_VECTORS = (
    "9a010801 212a0000 13400000 a87f0801",
    "75010804 fc030000 90290000 01400000 187f0804",
    "a9020000 6d400000 4d01080a 90090000 01400000 187f080a",
)

ATOM_ADDRESS_PROVENANCE = {
    "profile": PROFILE,
    "source": "GRIMOIRE v0.9 -- VCW SOFTWARE EDITION, section 5",
    "standard": (
        "addresses 1-214 are Kangxi radical canonical numbers from the 1716 "
        "Kangxi Dictionary; addresses 215-254 are Grimoire v0.9 classical particles"
    ),
    "allocation_rule": (
        "external address table; never allocate or resolve addresses from corpus "
        "frequency"
    ),
    "regeneration_status": (
        "the encoded BOOK is authoritative in v0.9; a higher-level registry compiler is "
        "a future proof path, not a runtime dependency"
    ),
}


class GrimoireDecodeError(ValueError):
    """A v0.9 Grimoire statement failed the decoder rules."""


def _records(raw: bytes) -> List[Tuple[int, int, int, int]]:
    if len(raw) % 4:
        raise GrimoireDecodeError("raw run length is not a multiple of four RGBA bytes")
    return [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]  # type: ignore[list-item]


def _xor(values: Iterable[int]) -> int:
    out = 0
    for value in values:
        out ^= int(value)
    return out


def _parity(records: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int]:
    non_parity = [rec for rec in records if rec[1] != 0x7f]
    r = _xor(rec[0] for rec in non_parity)
    return (
        254 if r == 0 else r,
        _xor(rec[2] for rec in non_parity),
        _xor(rec[3] for rec in non_parity),
    )


def parity_pixel(records: Iterable[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
    """Return the G=PARITY control pixel for non-parity RGBA morphemes."""
    materialized = [tuple(int(v) for v in rec) for rec in records]
    if not materialized:
        raise GrimoireDecodeError("cannot create PARITY for a blank statement")
    if any(len(rec) != 4 for rec in materialized):
        raise GrimoireDecodeError("a morpheme must contain four RGBA bytes")
    if any(rec[1] == 0x7f for rec in materialized):
        raise GrimoireDecodeError("input already contains a PARITY control pixel")
    r, b, a = _parity(materialized)
    return r, 0x7f, b, a


def encode_quoted_bytes(data: bytes, *, evidence: int = 0x01,
                        force: int = 0x0f) -> bytes:
    """Encode inert bytes as one framed Grimoire QUOTE statement.

    Each byte becomes two 1-based nibble atoms in one composed atom spelling. The
    first atom is HEAD; every continuation is BLEND with B=A=0 inheritance. The
    carrier frame ends at the generated G=0x7f PARITY control pixel.
    """
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise GrimoireDecodeError("quoted-byte statement requires non-empty bytes")
    if evidence not in EVIDENCE or evidence == 0:
        raise GrimoireDecodeError("quoted-byte HEAD needs nonzero known evidence")
    if force not in FORCE or force == 0:
        raise GrimoireDecodeError("quoted-byte HEAD needs nonzero known force")
    nibbles: List[int] = []
    for value in bytes(data):
        nibbles.extend(((value >> 4) + 1, (value & 0x0f) + 1))
    records: List[Tuple[int, int, int, int]] = [
        (nibbles[0], 0x01, evidence, force)
    ]
    records.extend((value, 0x40, 0x00, 0x00) for value in nibbles[1:])
    records.append(parity_pixel(records))
    return b"".join(bytes(rec) for rec in records)


def decode_quoted_bytes(raw: Any, *, frame_id: str = "quoted-frame") -> bytes:
    """Validate and decode one statement produced by :func:`encode_quoted_bytes`."""
    raw_bytes = parse_raw(raw)
    decoded = decode_statement(raw_bytes, frame_id=frame_id)
    records = _records(raw_bytes)
    semantic = [rec for rec in records if rec[1] != 0x7f]
    if not semantic or semantic[0][1:] != (0x01, 0x01, 0x0f):
        raise GrimoireDecodeError(
            "quoted-byte frame must start with HEAD/DIRECT/QUOTE")
    if any(rec[1:] != (0x40, 0x00, 0x00) for rec in semantic[1:]):
        raise GrimoireDecodeError(
            "quoted-byte continuation must be BLEND with inherited B/A")
    nibbles = []
    for index, rec in enumerate(semantic):
        if not 1 <= rec[0] <= 16:
            raise GrimoireDecodeError(
                "quoted-byte atom outside nibble map at pixel %d" % index)
        nibbles.append(rec[0] - 1)
    if len(nibbles) % 2:
        raise GrimoireDecodeError("quoted-byte frame has an odd nibble count")
    return bytes((nibbles[i] << 4) | nibbles[i + 1]
                 for i in range(0, len(nibbles), 2))


def raw_run_fingerprint(raw: bytes, frame_id: str) -> str:
    """Fingerprint all four lanes plus the frame boundary, as required by R12."""
    h = hashlib.sha256()
    h.update(str(frame_id).encode("utf-8"))
    h.update(b"\0")
    h.update(raw)
    return "sha256:" + h.hexdigest()


def parse_raw(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return bytes.fromhex("".join(value.split()))
    if isinstance(value, dict):
        raw = value.get("raw") or value.get("hex")
        if isinstance(raw, (bytes, bytearray)):
            return bytes(raw)
        if isinstance(raw, str):
            return bytes.fromhex("".join(raw.split()))
    raise TypeError("Grimoire statement must provide raw bytes or hex")


def atom_provenance(address: int) -> Dict[str, Any]:
    address = int(address)
    if not 1 <= address <= 254:
        raise GrimoireDecodeError("unknown atom address %d" % address)
    if address <= 214:
        standard = "Kangxi radical canonical number"
    else:
        standard = "Grimoire v0.9 particle extension"
    return {
        "address": address,
        "standard": standard,
        "source": ATOM_ADDRESS_PROVENANCE["source"],
        "allocation_rule": ATOM_ADDRESS_PROVENANCE["allocation_rule"],
    }


def _morpheme(rec: Tuple[int, int, int, int], index: int,
              head_evidence: int = 0, head_force: int = 0) -> Dict[str, Any]:
    r, g, b, a = rec
    role = ROLES.get(g)
    if role is None:
        raise GrimoireDecodeError("unknown role 0x%02x at pixel %d" % (g, index))
    if role == "PARITY":
        return {
            "index": index,
            "r": r,
            "g": g,
            "b": b,
            "a": a,
            "role": role,
            "parity": {"r": r, "b": b, "a": a},
        }
    if b not in EVIDENCE:
        raise GrimoireDecodeError("unknown evidence 0x%02x at pixel %d" % (b, index))
    if a not in FORCE:
        raise GrimoireDecodeError("unknown force 0x%02x at pixel %d" % (a, index))
    if role == "HEAD":
        if b == 0 or a == 0:
            raise GrimoireDecodeError("HEAD must carry nonzero evidence and force")
        evidence, force = b, a
    else:
        if b != 0 or a != 0:
            raise GrimoireDecodeError(
                "non-HEAD semantic morpheme must inherit B/A at pixel %d" % index)
        evidence, force = head_evidence, head_force
    return {
        "index": index,
        "r": r,
        "g": g,
        "b": b,
        "a": a,
        "role": role,
        "atom": atom_provenance(r),
        "evidence": EVIDENCE[evidence],
        "force": FORCE[force],
        "inherited": role != "HEAD",
    }


def decode_statement(raw: Any, *, frame_id: str = "frame-0",
                     fingerprint: str = None,
                     claim_tamper_evidence: bool = False,
                     allow_parity_absent: bool = False,
                     adoption_policy: str = "data") -> Dict[str, Any]:
    """Decode one framed v0.9 Grimoire statement.

    `adoption_policy` is Body/boot policy, never payload authority. Supported values are
    data, quote, quarantine, adopted.
    """
    raw_bytes = parse_raw(raw)
    records = _records(raw_bytes)
    if records and records[-1][1] == 0x00:
        if records[-1] != (0, 0, 0, 0):
            raise GrimoireDecodeError("END must be 00000000 in this carrier profile")
        records = records[:-1]
    if not records:
        raise GrimoireDecodeError("blank framed statement is invalid")
    if any(rec[1] == 0x00 for rec in records):
        raise GrimoireDecodeError("END may only appear as a terminal frame marker")

    heads = [i for i, rec in enumerate(records) if rec[1] == 0x01]
    if len(heads) != 1:
        raise GrimoireDecodeError("statement must contain exactly one HEAD")
    parities = [i for i, rec in enumerate(records) if rec[1] == 0x7f]
    if len(parities) > 1:
        raise GrimoireDecodeError("statement must contain at most one PARITY")
    if not parities and not allow_parity_absent:
        raise GrimoireDecodeError("statement missing PARITY")

    head_rec = records[heads[0]]
    if head_rec[2] == 0 or head_rec[3] == 0:
        raise GrimoireDecodeError("HEAD must carry nonzero evidence and force")
    head_evidence, head_force = head_rec[2], head_rec[3]
    if head_evidence not in EVIDENCE:
        raise GrimoireDecodeError("unknown HEAD evidence 0x%02x" % head_evidence)
    if head_force not in FORCE:
        raise GrimoireDecodeError("unknown HEAD force 0x%02x" % head_force)

    parity_status = "absent-carrier-integrity"
    parity_expected = None
    if parities:
        expected = _parity(records)
        parity_expected = {"r": expected[0], "b": expected[1], "a": expected[2]}
        actual_rec = records[parities[0]]
        actual = (actual_rec[0], actual_rec[2], actual_rec[3])
        if actual != expected:
            raise GrimoireDecodeError("PARITY mismatch: expected %r got %r"
                                      % (expected, actual))
        parity_status = "ok"

    computed_fp = raw_run_fingerprint(raw_bytes, frame_id)
    if fingerprint:
        if fingerprint != computed_fp:
            raise GrimoireDecodeError("raw-run fingerprint mismatch")
        fingerprint_status = "ok"
        full_lane_integrity = "measured"
    elif claim_tamper_evidence:
        fingerprint_status = "missing"
        full_lane_integrity = "unmeasured"
    else:
        fingerprint_status = "not-claimed"
        full_lane_integrity = "unmeasured"

    morphemes = [
        _morpheme(rec, i, head_evidence, head_force)
        for i, rec in enumerate(records)
        if rec[1] != 0x7f
    ]
    groups: List[Dict[str, Any]] = []
    current = None
    for morpheme in morphemes:
        if morpheme["role"] == "BLEND":
            if current is None:
                raise GrimoireDecodeError("BLEND pixel has no preceding atom group")
            current["atoms"].append(morpheme)
            continue
        current = {"role": morpheme["role"], "atoms": [morpheme]}
        groups.append(current)

    if adoption_policy not in ("data", "quote", "quarantine", "adopted"):
        raise GrimoireDecodeError("unknown adoption policy %r" % adoption_policy)
    adoption = {
        "status": adoption_policy,
        "governing": adoption_policy == "adopted",
        "authority": "boot-policy" if adoption_policy == "adopted" else "none",
    }

    return {
        "profile": PROFILE,
        "byte_order": BYTE_ORDER,
        "frame_id": str(frame_id),
        "raw": raw_bytes.hex(),
        "raw_fingerprint": computed_fp,
        "fingerprint_status": fingerprint_status,
        "full_lane_integrity": full_lane_integrity,
        "parity_status": parity_status,
        "parity_expected": parity_expected,
        "head_evidence": EVIDENCE[head_evidence],
        "head_force": FORCE[head_force],
        "groups": groups,
        "atom_address_provenance": ATOM_ADDRESS_PROVENANCE,
        "adoption": adoption,
        "unknowns": [],
        "rejection_reason": None,
    }
