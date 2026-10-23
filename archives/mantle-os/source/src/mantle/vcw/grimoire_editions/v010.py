"""Grimoire v0.10 VCW software profile."""
from __future__ import annotations

import hashlib
from typing import Any

from .common import GrimoireEditionError
from .. import grimoire as legacy

PROFILE = "grimoire-v0.10"
DOCUMENT_PATH = "documents/grimoire/editions/grimoire-v0.10.md"
BYTE_ORDER = "RGBA"
ROLES = legacy.ROLES
EVIDENCE = legacy.EVIDENCE
FORCE = legacy.FORCE
PARITY = 0x7F
BLEND = 0x40
END = 0x00
HEAD = 0x01
STEP_ROLES = frozenset(range(0x60, 0x70))

SELFTEST_VECTORS = (
    "9a010801 212a0000 13400000 947f5c03",
    "75010804 fc030000 90290000 01400000 c67fa965",
    "4d01080a a9020000 6d400000 90090000 01400000 3f7f4090",
    "9e600000 3d610000 d2620000 af7f2b24",
    "9a01080f 212a0000 13400000 947f5c0d",
)
COMPOSITION_COUNT = 295
STATEMENT_COUNT = 209

ATOM_ADDRESS_PROVENANCE = {
    "profile": PROFILE,
    "source": "GRIMOIRE v0.10 -- VCW SOFTWARE EDITION, section 5",
    "standard": (
        "addresses 1-214 are Kangxi radical canonical numbers from the 1716 "
        "Kangxi Dictionary; addresses 215-254 are Grimoire v0.10 classical particles"
    ),
    "allocation_rule": (
        "external address table; never allocate or resolve addresses from corpus "
        "frequency"
    ),
}


class GrimoireDecodeError(ValueError):
    """A v0.10 Grimoire statement failed the decoder rules."""


def _records(raw: bytes) -> list[tuple[int, int, int, int]]:
    if len(raw) % 4:
        raise GrimoireDecodeError("raw run length is not a multiple of four RGBA bytes")
    return [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]


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


def raw_run_fingerprint(raw: bytes, frame_id: str) -> str:
    h = hashlib.sha256()
    h.update(str(frame_id).encode("utf-8"))
    h.update(b"\0")
    h.update(raw)
    return "sha256:" + h.hexdigest()


def _rotl(value: int, amount: int) -> int:
    amount &= 7
    return ((value << amount) | (value >> (8 - amount))) & 0xFF


def parity_pixel(records: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    if not records:
        raise GrimoireDecodeError("cannot create PARITY for a blank statement")
    pr = pb = pa = 0
    for i, (r, g, b, a) in enumerate(records):
        w = i & 7
        pr ^= _rotl(r, w)
        pb ^= _rotl(b, w) ^ _rotl(g, w)
        pa ^= _rotl(a, w) ^ _rotl(g, 7 - w)
    return (0xFE if pr == 0 else pr, PARITY, pb, pa)


def encode_quoted_bytes(data: bytes, *, evidence: int = 0x01,
                        force: int = 0x0F) -> bytes:
    """Encode inert bytes as a v0.10 QUOTE frame with v0.10 parity."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise GrimoireDecodeError("quoted-byte statement requires non-empty bytes")
    if evidence not in EVIDENCE or evidence == 0:
        raise GrimoireDecodeError("quoted-byte HEAD needs nonzero known evidence")
    if force not in FORCE or force == 0:
        raise GrimoireDecodeError("quoted-byte HEAD needs nonzero known force")
    nibbles: list[int] = []
    for value in bytes(data):
        nibbles.extend(((value >> 4) + 1, (value & 0x0F) + 1))
    records = [(nibbles[0], HEAD, evidence, force)]
    records.extend((value, BLEND, 0, 0) for value in nibbles[1:])
    records.append(parity_pixel(records))
    return b"".join(bytes(record) for record in records)


def decode_quoted_bytes(raw: Any, *, frame_id: str = "quoted-frame") -> bytes:
    """Validate and decode one v0.10 QUOTE frame."""
    raw_bytes = parse_raw(raw)
    decode_statement(raw_bytes, frame_id=frame_id)
    records = _records(raw_bytes)
    semantic = [rec for rec in records if rec[1] != PARITY]
    if not semantic or semantic[0][1:] != (HEAD, 0x01, 0x0F):
        raise GrimoireDecodeError("quoted-byte frame must start with HEAD/DIRECT/QUOTE")
    if any(rec[1:] != (BLEND, 0, 0) for rec in semantic[1:]):
        raise GrimoireDecodeError("quoted-byte continuation must be BLEND with inherited B/A")
    nibbles = [rec[0] - 1 for rec in semantic]
    if any(value < 0 or value > 15 for value in nibbles) or len(nibbles) % 2:
        raise GrimoireDecodeError("quoted-byte frame has an invalid nibble map")
    return bytes((nibbles[i] << 4) | nibbles[i + 1]
                 for i in range(0, len(nibbles), 2))


def _value(value: Any, table: dict[int, str], label: str, *, nonzero: bool = False) -> int:
    if isinstance(value, str):
        reverse = {name: number for number, name in table.items()}
        if value not in reverse:
            raise GrimoireDecodeError("unknown container %s %r" % (label, value))
        value = reverse[value]
    if not isinstance(value, int) or value not in table:
        raise GrimoireDecodeError("unknown container %s %r" % (label, value))
    if nonzero and value == 0:
        raise GrimoireDecodeError("container %s must be nonzero" % label)
    return value


def atom_provenance(address: int) -> dict[str, Any]:
    if not isinstance(address, int) or not 1 <= address <= 254:
        raise GrimoireDecodeError("unknown atom address %r" % (address,))
    return {
        "address": address,
        "standard": ("Kangxi radical canonical number" if address <= 214
                      else "Grimoire v0.10 particle extension"),
        "source": ATOM_ADDRESS_PROVENANCE["source"],
        "allocation_rule": ATOM_ADDRESS_PROVENANCE["allocation_rule"],
    }


def _morpheme(rec: tuple[int, int, int, int], index: int) -> dict[str, Any]:
    r, g, b, a = rec
    role = ROLES.get(g)
    if role is None or role in ("END", "PARITY"):
        raise GrimoireDecodeError("unknown role 0x%02x at pixel %d" % (g, index))
    if r == 0:
        raise GrimoireDecodeError("unwritten atom at pixel %d" % index)
    if b not in EVIDENCE:
        raise GrimoireDecodeError("unknown evidence 0x%02x at pixel %d" % (b, index))
    if a not in FORCE:
        raise GrimoireDecodeError("unknown force 0x%02x at pixel %d" % (a, index))
    return {
        "index": index, "r": r, "g": g, "b": b, "a": a, "role": role,
        "atom": atom_provenance(r),
    }


def decode_statement(
    raw: Any,
    *,
    frame_id: str,
    profile: str = PROFILE,
    fingerprint: str | None = None,
    claim_tamper_evidence: bool = False,
    allow_parity_absent: bool = False,
    adoption_policy: str = "data",
    container_evidence: int | str | None = None,
    container_force: int | str | None = None,
    container_frame_id: str | None = None,
) -> dict[str, Any]:
    """Decode one v0.10 statement while retaining structural uncertainty."""
    if profile != PROFILE:
        raise GrimoireDecodeError("decoder profile must be %s" % PROFILE)
    raw_bytes = parse_raw(raw)
    records = _records(raw_bytes)
    if records and records[-1][1] == END:
        if records[-1] != (0, 0, 0, 0):
            raise GrimoireDecodeError("END must be 00000000 in this carrier profile")
        records = records[:-1]
    if not records:
        raise GrimoireDecodeError("blank framed statement is invalid")
    if any(rec[1] == END for rec in records):
        raise GrimoireDecodeError("END may only appear as a terminal frame marker")

    parities = [i for i, rec in enumerate(records) if rec[1] == PARITY]
    if len(parities) > 1:
        raise GrimoireDecodeError("statement must contain at most one PARITY")
    if any(records[i][1] == BLEND and i and records[i - 1][1] == PARITY
           for i in range(len(records))):
        raise GrimoireDecodeError("BLEND group was interrupted and resumed")
    if parities and parities[0] != len(records) - 1:
        raise GrimoireDecodeError("PARITY must be the terminal control pixel")
    if not parities and not allow_parity_absent:
        raise GrimoireDecodeError("statement missing PARITY")
    parity_expected = None
    parity_status = "absent-carrier-integrity"
    if parities:
        expected = parity_pixel([rec for rec in records if rec[1] != PARITY])
        actual = records[parities[0]]
        parity_expected = {"r": expected[0], "g": expected[1], "b": expected[2], "a": expected[3]}
        if actual != expected:
            raise GrimoireDecodeError("PARITY mismatch: expected %r got %r" % (expected, actual))
        parity_status = "ok"

    morphemes = [_morpheme(rec, i) for i, rec in enumerate(records) if rec[1] != PARITY]
    for morpheme in morphemes:
        if morpheme["g"] != HEAD and (morpheme["b"], morpheme["a"]) != (0, 0):
            raise GrimoireDecodeError(
                "non-HEAD semantic morpheme must inherit B/A at pixel %d" % morpheme["index"])
    heads = [m for m in morphemes if m["g"] == HEAD]
    if len(heads) > 1:
        raise GrimoireDecodeError("statement must contain exactly one HEAD; got %d" % len(heads))

    procedure = not heads
    lead_roles = [m["g"] for m in morphemes if m["g"] != BLEND]
    if procedure and any(role not in STEP_ROLES for role in lead_roles):
        raise GrimoireDecodeError("zero-HEAD statement requires only STEP lead roles")
    step_roles = [role for role in lead_roles if role in STEP_ROLES]
    if len(step_roles) != len(set(step_roles)):
        raise GrimoireDecodeError("procedure STEP ordinals must not repeat")

    if heads:
        head = heads[0]
        if head["b"] == 0 or head["a"] == 0:
            raise GrimoireDecodeError("HEAD must carry nonzero evidence and force")
        if head["b"] not in EVIDENCE or head["a"] not in FORCE:
            raise GrimoireDecodeError("HEAD evidence or force is unknown")
        effective_evidence = EVIDENCE[head["b"]]
        effective_force = FORCE[head["a"]]
        evidence_source = force_source = "head"
        unknowns: list[str] = []
    else:
        effective_evidence = "INHERIT"
        effective_force = "INHERIT"
        evidence_source = "missing-container"
        force_source = "missing-container"
        unknowns = []
        if container_evidence is not None:
            ev = _value(container_evidence, EVIDENCE, "evidence", nonzero=True)
            effective_evidence = EVIDENCE[ev]
            evidence_source = "container"
        else:
            unknowns.append("container_evidence")
        if container_force is not None:
            fo = _value(container_force, FORCE, "force", nonzero=True)
            effective_force = FORCE[fo]
            force_source = "container"
        else:
            unknowns.append("container_force")

    groups: list[dict[str, Any]] = []
    current = None
    for morpheme in morphemes:
        role = morpheme["role"]
        if role == "BLEND":
            if current is None:
                raise GrimoireDecodeError("BLEND pixel has no preceding atom group")
            current["atoms"].append(morpheme)
            continue
        current = {"role": role, "atoms": [morpheme]}
        groups.append(current)

    for group in groups:
        for atom in group["atoms"]:
            atom["evidence"] = effective_evidence
            atom["force"] = effective_force
            atom["inherited"] = atom["g"] != HEAD

    computed_fp = raw_run_fingerprint(raw_bytes, frame_id)
    if fingerprint is not None:
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

    if adoption_policy not in ("data", "quote", "quarantine", "adopted"):
        raise GrimoireDecodeError("unknown adoption policy %r" % adoption_policy)
    governing = adoption_policy == "adopted" and not unknowns
    adoption = {
        "status": adoption_policy,
        "governing": governing,
        "authority": "boot-policy" if governing else "none",
    }
    return {
        "profile": PROFILE,
        "byte_order": BYTE_ORDER,
        "frame_id": str(frame_id),
        "container_frame_id": container_frame_id,
        "raw": raw_bytes.hex(),
        "original_raw_run": raw_bytes.hex(),
        "raw_fingerprint": computed_fp,
        "fingerprint_status": fingerprint_status,
        "full_lane_integrity": full_lane_integrity,
        "parity_status": parity_status,
        "parity_expected": parity_expected,
        "head_present": bool(heads),
        "effective_evidence": effective_evidence,
        "effective_force": effective_force,
        "evidence_source": evidence_source,
        "force_source": force_source,
        "groups": groups,
        "atom_address_provenance": ATOM_ADDRESS_PROVENANCE,
        "adoption": adoption,
        "governing": governing,
        "unknowns": unknowns,
        "rejection_reason": None,
    }
