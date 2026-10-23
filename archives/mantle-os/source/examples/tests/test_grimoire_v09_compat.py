import pytest

from mantle.vcw.grimoire import (
    GrimoireDecodeError,
    decode_quoted_bytes,
    decode_statement,
    encode_quoted_bytes,
    raw_run_fingerprint,
)
from mantle.vcw.grimoire_editions import decode_statement as decode_profiled


GOLDEN = (
    {
        "raw": "9a010801212a000013400000a87f0801",
        "head_evidence": "STIPULATED",
        "head_force": "LAW",
        "groups": (("HEAD", (("HEAD", 154),)), ("COMPARISON", (("COMPARISON", 33), ("BLEND", 19)))),
    },
    {
        "raw": "75010804fc0300009029000001400000187f0804",
        "head_evidence": "STIPULATED",
        "head_force": "NEVER",
        "groups": (("HEAD", (("HEAD", 117),)), ("PATIENT", (("PATIENT", 252),)), ("SCOPE", (("SCOPE", 144), ("BLEND", 1)))),
    },
    {
        "raw": "a90200006d4000004d01080a9009000001400000187f080a",
        "head_evidence": "STIPULATED",
        "head_force": "POWER",
        "groups": (("AGENT", (("AGENT", 169), ("BLEND", 109))), ("HEAD", (("HEAD", 77),)), ("RECIPIENT", (("RECIPIENT", 144), ("BLEND", 1)))),
    },
)


def _shape(decoded):
    return {
        "profile": decoded["profile"],
        "byte_order": decoded["byte_order"],
        "raw": decoded["raw"],
        "fingerprint_status": decoded["fingerprint_status"],
        "full_lane_integrity": decoded["full_lane_integrity"],
        "parity_status": decoded["parity_status"],
        "head_evidence": decoded["head_evidence"],
        "head_force": decoded["head_force"],
        "groups": tuple((g["role"], tuple((a["role"], a["atom"]["address"]) for a in g["atoms"]))
                       for g in decoded["groups"]),
        "adoption": decoded["adoption"],
    }


def test_v09_golden_selftests_are_byte_and_semantic_stable():
    for index, expected in enumerate(GOLDEN):
        decoded = decode_profiled(bytes.fromhex(expected["raw"]), profile="grimoire-v0.9",
                                  frame_id=f"golden-{index}")
        shape = _shape(decoded)
        assert shape["profile"] == "grimoire-v0.9"
        assert shape["raw"] == expected["raw"]
        assert shape["head_evidence"] == expected["head_evidence"]
        assert shape["head_force"] == expected["head_force"]
        assert shape["groups"] == expected["groups"]
        assert shape["parity_status"] == "ok"
        assert shape["adoption"] == {"status": "data", "governing": False, "authority": "none"}


def test_v09_rejects_the_v010_zero_head_step_vector():
    zero_head = bytes.fromhex("9e6000003d610000d2620000af7f2b24")
    with pytest.raises(GrimoireDecodeError, match="exactly one HEAD"):
        decode_statement(zero_head, frame_id="v010-procedure")


def test_v09_end_and_parity_absence_policies_are_frozen():
    raw = bytes.fromhex(GOLDEN[0]["raw"])
    with_end = raw + b"\x00\x00\x00\x00"
    ended = decode_statement(with_end, frame_id="end")
    assert ended["raw"] == with_end.hex()
    assert ended["parity_status"] == "ok"
    absent = raw[:-4]
    with pytest.raises(GrimoireDecodeError, match="missing PARITY"):
        decode_statement(absent, frame_id="absent")
    allowed = decode_statement(absent, frame_id="absent", allow_parity_absent=True)
    assert allowed["parity_status"] == "absent-carrier-integrity"


def test_v09_fingerprint_and_quoted_bytes_round_trip_are_frozen():
    raw = bytes.fromhex(GOLDEN[0]["raw"])
    frame = "fingerprint"
    decoded = decode_statement(raw, frame_id=frame, fingerprint=raw_run_fingerprint(raw, frame))
    assert decoded["fingerprint_status"] == "ok"
    assert decoded["full_lane_integrity"] == "measured"
    payload = bytes(range(64))
    assert decode_quoted_bytes(encode_quoted_bytes(payload)) == payload


def test_v09_rejection_wall():
    cases = (
        (bytes.fromhex("9a010001212a000013400000a87f0801"), "HEAD must carry", False),
        (bytes.fromhex("9a010801212a000013400000a87f0801"), None, False),
        (bytes.fromhex("9a010801212a000013400000017e0000"), "unknown role", True),
        (bytes.fromhex("9a010801212a000021400101"), "non-HEAD", True),
    )
    for raw, match, allow_absent in cases:
        if match is None:
            decode_statement(raw, frame_id="valid")
        else:
            with pytest.raises(GrimoireDecodeError, match=match):
                decode_statement(raw, frame_id="invalid", allow_parity_absent=allow_absent)
