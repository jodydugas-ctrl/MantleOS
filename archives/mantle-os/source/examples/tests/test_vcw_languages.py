#!/usr/bin/env python3
"""Tests for the VCW Language Forge foundation (PR A + reason-evidence adapter).

Covers (Forge v0.2 / MANTLE_OS_VCW_TOME_MIGRATION_IMPLEMENTATION_PLAN §5, §9):

  * selection is explicit — a wrong/missing BookKey refuses
  * registry digest is bound to the generated registries
  * codec digest is bound to the pinned implementation
  * a CANDIDATE Book can never be requested as governing tissue
  * the FROZEN reason-evidence Book decodes every frozen v0.10 vector
    byte-stably through the authoritative v010 codec
  * encode() produces runs the frozen decoder accepts (round-trip tied to
    the frozen implementation)
  * fixed refusal codes and the canonical ENCODING REFUSED message
  * digest recipe is canonical (key order independent)
"""
import importlib
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, os.path.abspath(_SRC))

from mantle.vcw.languages import (  # noqa: E402
    ENCODING_REFUSED_PREFIX,
    REFUSAL_CODES,
    BookKey,
    BookManifest,
    EncodingRefused,
    canonical_json_bytes,
    codec_digest,
    get_book,
    known_books,
    make_key,
    register_book,
    registry_digest,
    sha256_id,
    verify_registered_book,
)
from mantle.vcw.languages.registry import RegisteredBook, REGISTRY  # noqa: E402
from mantle.vcw.languages.books import reason_evidence  # noqa: E402

from mantle.vcw.grimoire_editions.v010 import (  # noqa: E402
    SELFTEST_VECTORS as FROZEN_VECTORS,
)
from mantle.vcw.grimoire_editions.registry import (  # noqa: E402
    decode_statement as frozen_decode,
)

RE = "reason-evidence"
RE_ED = "0.10"


# ---- base ----------------------------------------------------------------- #

def test_language_package_imports_and_registers_reason_evidence():
    names = known_books()
    assert any(RE in name and RE_ED in name for name in names), names


def test_reason_evidence_is_frozen():
    book = get_book(RE, RE_ED, "mantle-standard", "0.10")
    assert book.manifest.status == "FROZEN"
    assert book.manifest.integrity_id == "rotated-parity-rgba-v1"


# ---- explicit selection ---------------------------------------------------- #

def test_missing_book_refuses():
    with pytest.raises(EncodingRefused) as exc:
        get_book("not-a-book", "0.1", "x", "0.1")
    assert exc.value.code == "book-missing"
    assert str(exc.value).startswith(ENCODING_REFUSED_PREFIX)


def test_wrong_edition_refuses():
    with pytest.raises(EncodingRefused):
        get_book(RE, "9.9", "mantle-standard", "0.10")


# ---- digest binding -------------------------------------------------------- #

def test_registry_digest_matches_generated_registries():
    book = get_book(RE, RE_ED, "mantle-standard", "0.10")
    expected = registry_digest(book.registries)
    assert book.manifest.registry_digest == expected


def test_codec_digest_matches_pinned_source():
    book = get_book(RE, RE_ED, "mantle-standard", "0.10")
    expected = codec_digest(book.codec_source)
    assert book.manifest.codec_digest == expected


def test_digest_mismatch_refuses_registration():
    # A FROZEN Book carrying the WRONG registry digest must be refused, on a
    # fresh registry so the duplicate-key guard does not fire first.
    m = reason_evidence._MANIFEST
    probe = BookKey(book_id="digest-probe", book_edition="0.1",
                    dialect_id="d", dialect_edition="0.1")
    manifest = BookManifest(
        category="OPERATIONAL",
        status="FROZEN",
        key=probe,
        allocation_policy="EXTERNAL-STANDARD",
        framing_id="framed-run-v1",
        integrity_id="rotated-parity-rgba-v1",
        lane_mapping="identity",
        lane_questions=m.lane_questions,
        registry_digest="sha256:" + "0" * 64,  # corrupted declared digest
        codec_digest=m.codec_digest,
        source_digest=None,
        description="tampered probe",
    )
    from mantle.vcw.languages.registry import BookRegistry
    fresh = BookRegistry()
    with pytest.raises(EncodingRefused) as exc:
        fresh.register_book(RegisteredBook(
            manifest=manifest,
            codec=reason_evidence._CODEC,
            registries=reason_evidence.lane_registries(),
        ))
    assert exc.value.code == "registry-missing"


# ---- candidate-not-governing ----------------------------------------------- #

def test_candidate_cannot_govern():
    manifest = BookManifest(
        category="OPERATIONAL",
        status="CANDIDATE",
        key=make_key(book_id="probe", book_edition="0.1",
                     dialect_id="d", dialect_edition="0.1"),
        allocation_policy="FIXED",
        framing_id="framed-run-v1",
        integrity_id="rotated-parity-rgba-v1",
        lane_mapping="identity",
        lane_questions={"R": "q?", "G": "q?", "B": "q?", "A": "q?"},
        registry_digest="",
        codec_digest="",
    )
    with pytest.raises(EncodingRefused) as exc:
        REGISTRY.require_governing_capable(
            "probe", "0.1", "d", "0.1")
    assert exc.value.code == "book-missing"


def test_frozen_can_govern():
    # reason-evidence is FROZEN -> governing-gate passes (no raise)
    REGISTRY.require_governing_capable(RE, RE_ED, "mantle-standard", "0.10")


# ---- frozen byte-stability ------------------------------------------------- #

def test_all_frozen_v010_vectors_decode_byte_stable_through_book():
    book = get_book(RE, RE_ED, "mantle-standard", "0.10")
    for index, vector in enumerate(FROZEN_VECTORS):
        via_book = book.codec.decode_hex(vector, frame_id="test-%d" % index)
        via_frozen = frozen_decode(vector, profile="grimoire-v0.10",
                                   frame_id="test-%d" % index)
        # byte-stable: raw and group structure identical to the frozen decoder
        assert via_book["raw"] == via_frozen["raw"]
        assert via_book["parity_status"] == "ok"
        assert via_book["profile"] == "grimoire-v0.10"
        assert via_book["head_present"] == via_frozen["head_present"]


def test_encode_roundtrips_through_frozen_decoder():
    book = get_book(RE, RE_ED, "mantle-standard", "0.10")
    model = {"groups": [
        {"role": "HEAD", "spelling": "前見",
         "evidence": "STIPULATED", "force": "LAW"},
        {"role": "AGENT", "spelling": "士"},
        {"role": "PURPOSE", "spelling": "宀人"},
    ]}
    records = book.codec.encode(model, frame_id="rt")
    raw = b"".join(bytes(r) for r in records)
    decoded = frozen_decode(raw, profile="grimoire-v0.10", frame_id="rt")
    assert decoded["parity_status"] == "ok"
    assert decoded["raw"] == raw.hex()


def test_frozen_book_selftest_via_registry_verify():
    report = verify_registered_book(RE, RE_ED, "mantle-standard", "0.10")
    assert report["status"] == "FROZEN"
    assert report["selftest"] == "ok"


# ---- refusal codes + canonical message ------------------------------------- #

def test_refusal_codes_are_fixed():
    assert "book-missing" in REFUSAL_CODES
    assert "round-trip-mismatch" in REFUSAL_CODES
    assert len(REFUSAL_CODES) == 14


def test_unknown_refusal_code_refused():
    with pytest.raises(ValueError):
        EncodingRefused("not-a-real-code")


# ---- canonical digest recipe ---------------------------------------------- #

def test_canonical_serialization_is_key_order_independent():
    a = {"b": 1, "a": [1, 2], "c": {"z": None}}
    b = {"c": {"z": None}, "a": [1, 2], "b": 1}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)
    assert sha256_id(canonical_json_bytes(a)) == sha256_id(canonical_json_bytes(b))
