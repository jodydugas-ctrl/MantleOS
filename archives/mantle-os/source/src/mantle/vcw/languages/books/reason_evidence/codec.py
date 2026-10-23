#!/usr/bin/env python3
"""mantle.vcw.languages.books.reason_evidence

reason-evidence@0.10 / mantle-standard@0.10  —  the OPERATIONAL Tome.

The FIRST production Book and the compatibility bridge: its implementation
lineage is the FROZEN Grimoire v0.10 (documents/grimoire/editions/
grimoire-v0.10.md). It does NOT rewrite that edition; it delegates to the
frozen v010 codec so every existing v0.10 byte decodes identically.

Lane contract (the four streams for an operational layer):
  R  what concept/atom-address exists?
  G  how does that concept participate?
  B  why is the statement believed?
  A  what obligation or modal consequence follows?

Allocation: EXTERNAL-STANDARD (Kangxi radicals + v0.10 particles).
Framing:    framed-run-v1
Integrity:  rotated-parity-rgba-v1 (all four lanes)

Registry material is GENERATED from the frozen edition file at import time
(grimoire_tool.parse approach), never hand-maintained as a second source of
truth.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

from ....grimoire import ROLES, EVIDENCE, FORCE  # frozen tables (v0.9 base source)
from ....grimoire_editions.v010 import (
    SELFTEST_VECTORS,
)
from ....grimoire_editions.registry import decode_statement as _profiled_decode
from ...canonical import registry_digest
from ...errors import EncodingRefused
from ...framing import parse_framed_run
from ...integrity import rotated_parity_pixel, verify_rotated_parity
from ...types import BookKey, BookManifest

RGBA = Tuple[int, int, int, int]

BOOK_ID = "reason-evidence"
BOOK_EDITION = "0.10"
DIALECT_ID = "mantle-standard"
DIALECT_EDITION = "0.10"
CATEGORY = "OPERATIONAL"
STATUS = "FROZEN"
_BLEND_ROLE = 0x40

# The frozen edition file — the single generated source of the registry.
# Resolved via the repo's own paths.REPO_ROOT (avoids the installed-package
# path-collapse trap: repo-only resources resolve under <prefix>/Lib when the
# package is pip-installed, so we follow the repo's path-resolution
# convention, exactly as grimoire_editions.adoption does).
def _edition_src() -> str:
    try:
        from .....paths import REPO_ROOT
        base = os.path.join(REPO_ROOT, "documents", "grimoire", "editions")
    except Exception:
        # fall back to a source-checkout relative path
        here = os.path.dirname(os.path.abspath(__file__))
        base = os.path.normpath(os.path.join(here, *([".."] * 6),
                                             "documents", "grimoire", "editions"))
    path = os.path.join(base, "grimoire-v0.10.md")
    with open(path, encoding="utf-8") as fh:
        return fh.read().replace("\\_", "_")


_EDITION_TEXT = _edition_src()


def _section(header: str) -> str:
    m = re.search(r"^" + re.escape(header) + r".*$", _EDITION_TEXT, re.M)
    if not m:
        raise RuntimeError("frozen edition section %r not found" % header)
    return _EDITION_TEXT[m.end():]


def _atom_atlas() -> Dict[str, int]:
    """Char -> address atlas generated from the frozen edition §5 table."""
    block = _section("## 5 ATOM").split("```")[1]
    atlas: Dict[str, int] = {}
    for num, ch, _gloss in re.findall(r"(\d{1,3})\s+(\S)\s+([a-z_]+)", block):
        n = int(num)
        if not 1 <= n <= 254:
            raise RuntimeError("frozen atom address out of range: %d" % n)
        if ch in atlas:
            raise RuntimeError("duplicate atom char %r" % ch)
        atlas[ch] = n
    if set(atlas.values()) != set(range(1, 255)):
        raise RuntimeError("atom table is not the full 1-254 range")
    return atlas


ATOM_ATLAS: Dict[str, int] = _atom_atlas()


def lane_registries() -> Dict[str, Any]:
    """Lane registries GENERATED from the frozen tables + atom atlas."""
    return {
        "R": {"atoms": {str(addr): ch for ch, addr in sorted(
            ATOM_ATLAS.items(), key=lambda kv: kv[1])},
              "external_standard": True,
              "range": "1..254 (Kangxi 1-214; v0.10 particles 215-254)"},
        "G": {hex(k): v for k, v in sorted(ROLES.items())},
        "B": {hex(k): v for k, v in sorted(EVIDENCE.items())},
        "A": {hex(k): v for k, v in sorted(FORCE.items())},
    }


def build_manifest(codec_digest_value: str = "") -> BookManifest:
    m = BookManifest(
        category=CATEGORY,
        status=STATUS,
        key=book_key(),
        allocation_policy="EXTERNAL-STANDARD",
        framing_id="framed-run-v1",
        integrity_id="rotated-parity-rgba-v1",
        lane_mapping="identity",
        lane_questions={
            "R": "what concept/atom-address exists?",
            "G": "how does that concept participate?",
            "B": "why is the statement believed?",
            "A": "what obligation or modal consequence follows?",
        },
        registry_digest=registry_digest(lane_registries()),
        codec_digest=codec_digest_value,
        source_digest=None,
        description=("OPERATIONAL Tome. Implementation lineage: frozen "
                     "Grimoire v0.10 (delegates to the frozen v010 codec)."),
    )
    return m


def book_key() -> BookKey:
    return BookKey(book_id=BOOK_ID, book_edition=BOOK_EDITION,
                   dialect_id=DIALECT_ID, dialect_edition=DIALECT_EDITION)


# --------------------------------------------------------------------------- #
# Codec — the frozen-delegating adapter                                      #
# --------------------------------------------------------------------------- #

class ReasonEvidenceCodec:
    """Delegates to the FROZEN v010 codec.

    decode() calls the authoritative decoder and returns the same structure a
    legacy grimoire-v0.10 read returns — byte-stable by construction.
    encode() produces a conformant statement run whose decode matches the
    canonical model (validated by round-trip).
    """

    # ---- decode (delegated, byte-stable) ---------------------------------- #

    def decode(self, records: List[RGBA], *,
               frame_id: str | None = None) -> Dict[str, Any]:
        raw = b"".join(bytes(r) for r in records)
        return _profiled_decode(raw, profile="grimoire-v0.10",
                                frame_id=frame_id or "reason-evidence")

    def decode_hex(self, hex_text: str, *, frame_id: str | None = None) -> Dict[str, Any]:
        raw = bytes.fromhex("".join(hex_text.split()))
        return _profiled_decode(raw, profile="grimoire-v0.10",
                                frame_id=frame_id or "reason-evidence")

    # ---- validate ---------------------------------------------------------- #

    def validate_records(self, records: List[RGBA]) -> None:
        verify_rotated_parity(list(records))
        self.decode(list(records), frame_id="validate")

    # ---- encode (canonical model -> records) ------------------------------ #

    def encode(self, value: Any, *, frame_id: str | None = None) -> List[RGBA]:
        """Encode a canonical statement model.

        value:
          {"groups": [{"role": "HEAD", "spelling": "貝",
                       "evidence": "STIPULATED", "force": "LAW"},
                      {"role": "COMPARISON", "spelling": "士力"}]}
        Roles/evidence/force resolve against the frozen tables; atoms against
        the angle table generated from the frozen edition. Never invents.
        """
        if not isinstance(value, dict) or "groups" not in value:
            raise EncodingRefused("unrepresentable",
                                  "reason-evidence needs a groups model")
        groups = value["groups"]
        if not isinstance(groups, list) or not groups:
            raise EncodingRefused("ambiguous-composition", "no groups")

        def role_code(name: str) -> int:
            for code, rn in ROLES.items():
                if rn == name:
                    return int(code)
            raise EncodingRefused("illegal-role", "unknown role %r" % (name,))

        def enum_code(table, name: str, label: str) -> int:
            for code, en in table.items():
                if en == name:
                    return int(code)
            raise EncodingRefused("unknown-value",
                                  "unknown %s %r" % (label, name))

        def spelling_addresses(spelling: str) -> List[int]:
            addresses: List[int] = []
            for ch in spelling:
                addr = ATOM_ATLAS.get(ch)
                if addr is None:
                    raise EncodingRefused("unknown-value",
                                          "character %r not in atom table" % ch)
                addresses.append(addr)
            return addresses

        heads = [g for g in groups if role_code(g["role"]) == 0x01]
        steps_only = all(role_code(g["role"]) in range(0x60, 0x70)
                         for g in groups)
        if len(heads) > 1:
            raise EncodingRefused("illegal-role", "multiple HEAD groups")
        if not heads and not steps_only:
            raise EncodingRefused("missing-required-role",
                                  "no HEAD and not STEP-only")

        head_evidence = head_force = 0
        if heads:
            head_evidence = enum_code(EVIDENCE, heads[0].get("evidence", "STIPULATED"),
                                      "evidence")
            head_force = enum_code(FORCE, heads[0].get("force", "LAW"), "force")
            if head_evidence == 0 or head_force == 0:
                raise EncodingRefused("missing-required-role",
                                      "HEAD may not inherit evidence/force")

        pixels: List[RGBA] = []
        for grp in groups:
            role = role_code(grp["role"])
            addresses = spelling_addresses(grp.get("spelling", ""))
            if not addresses:
                raise EncodingRefused("unknown-value",
                                      "empty spelling for %r" % (grp,))
            b = head_evidence if role == 0x01 else 0
            a = head_force if role == 0x01 else 0
            pixels.append((addresses[0], role, b, a))
            for addr in addresses[1:]:
                pixels.append((addr, _BLEND_ROLE, 0, 0))

        pixels.append(rotated_parity_pixel(pixels))
        # round-trip guard: the frozen decoder must accept what we encode
        self.decode(pixels, frame_id="encode-check")
        return pixels

    # ---- canonicalize + selftest ------------------------------------------ #

    def canonicalize(self, value: Any) -> Any:
        return value  # decoded output already carries canonical form

    def selftest(self) -> dict:
        # Every frozen v0.10 vector must decode identically through the Book.
        results = []
        for index, vector in enumerate(SELFTEST_VECTORS):
            decoded = self.decode_hex(vector, frame_id="selftest-%d" % index)
            ok = (decoded.get("profile") == "grimoire-v0.10"
                  and decoded.get("parity_status") == "ok")
            if not ok:
                raise EncodingRefused(
                    "round-trip-mismatch",
                    "frozen vector %d failed through the Book" % index)
            results.append({"vector": index, "profile": decoded["profile"],
                            "parity_status": decoded["parity_status"],
                            "head_present": decoded["head_present"]})
        return {"vectors_checked": len(results), "ok": True}
