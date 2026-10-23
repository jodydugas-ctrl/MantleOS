import pytest

from mantle.vcw.grimoire_editions import decode_statement as _decode_statement
from mantle.vcw.grimoire_editions.v010 import GrimoireDecodeError, SELFTEST_VECTORS, raw_run_fingerprint


def decode_statement(raw, **context):
    return _decode_statement(raw, profile="grimoire-v0.10", **context)


def test_all_v010_selftest_vectors_decode():
    for index, vector in enumerate(SELFTEST_VECTORS):
        decoded = decode_statement(vector, frame_id=f"v010-{index}")
        assert decoded["profile"] == "grimoire-v0.10"
        assert decoded["byte_order"] == "RGBA"
        assert decoded["parity_status"] == "ok"
        assert decoded["rejection_reason"] is None


def test_zero_head_step_procedure_is_structural_but_unresolved_without_container():
    decoded = decode_statement(SELFTEST_VECTORS[3], frame_id="procedure")
    assert decoded["head_present"] is False
    assert decoded["effective_evidence"] == "INHERIT"
    assert decoded["effective_force"] == "INHERIT"
    assert decoded["evidence_source"] == "missing-container"
    assert decoded["force_source"] == "missing-container"
    assert decoded["unknowns"] == ["container_evidence", "container_force"]
    assert decoded["governing"] is False


def test_zero_head_step_procedure_inherits_explicit_container_metadata():
    decoded = decode_statement(
        SELFTEST_VECTORS[3], frame_id="procedure", adoption_policy="adopted",
        container_evidence="STIPULATED", container_force="WAY", container_frame_id="book-1",
    )
    assert decoded["effective_evidence"] == "STIPULATED"
    assert decoded["effective_force"] == "WAY"
    assert decoded["evidence_source"] == "container"
    assert decoded["force_source"] == "container"
    assert decoded["container_frame_id"] == "book-1"
    assert decoded["governing"] is True


def test_procedure_requires_step_leads_and_unique_ordinals():
    with pytest.raises(GrimoireDecodeError, match="only STEP"):
        decode_statement("9e600000 212a0000", frame_id="bad-procedure", allow_parity_absent=True)
    with pytest.raises(GrimoireDecodeError, match="must not repeat"):
        decode_statement("9e600000 3d600000", frame_id="repeat", allow_parity_absent=True)


def test_heads_and_inheritance_are_strict():
    with pytest.raises(GrimoireDecodeError, match="exactly one HEAD"):
        decode_statement("9a010801 75010804", frame_id="two-heads", allow_parity_absent=True)
    with pytest.raises(GrimoireDecodeError, match="HEAD must carry"):
        decode_statement("9a010001 212a0000", frame_id="zero-evidence", allow_parity_absent=True)
    with pytest.raises(GrimoireDecodeError, match="non-HEAD"):
        decode_statement("9a010801 21400101", frame_id="non-inherit", allow_parity_absent=True)


def test_control_and_domain_errors_are_refused():
    with pytest.raises(GrimoireDecodeError, match="BLEND"):
        decode_statement("01400000", frame_id="leading-blend", allow_parity_absent=True)
    with pytest.raises(GrimoireDecodeError, match="PARITY must"):
        decode_statement("9a010801 947f5c03 212a0000", frame_id="interrupted", allow_parity_absent=True)
    with pytest.raises(GrimoireDecodeError, match="interrupted and resumed"):
        decode_statement("9a010801 947f5c03 13400000", frame_id="resumed", allow_parity_absent=True)
    with pytest.raises(GrimoireDecodeError, match="unknown role"):
        decode_statement("9a010801 217e0000", frame_id="unknown-role", allow_parity_absent=True)
    with pytest.raises(GrimoireDecodeError, match="unknown evidence"):
        decode_statement("9a010801 210a0a00", frame_id="unknown-evidence", allow_parity_absent=True)
    with pytest.raises(GrimoireDecodeError, match="unknown force"):
        decode_statement("9a010801 210a0010", frame_id="unknown-force", allow_parity_absent=True)


def test_parity_fingerprint_and_authority_boundaries():
    vector = SELFTEST_VECTORS[0]
    with pytest.raises(GrimoireDecodeError, match="PARITY mismatch"):
        decode_statement(vector[:-1] + "4", frame_id="bad-parity")
    decoded = decode_statement(vector, frame_id="fp", claim_tamper_evidence=True)
    assert decoded["fingerprint_status"] == "missing"
    assert decoded["full_lane_integrity"] == "unmeasured"
    checked = decode_statement(vector, frame_id="fp", fingerprint=raw_run_fingerprint(bytes.fromhex(vector.replace(" ", "")), "fp"))
    assert checked["fingerprint_status"] == "ok"
    assert checked["full_lane_integrity"] == "measured"
    inert = decode_statement(vector, frame_id="quoted", adoption_policy="quote")
    assert inert["governing"] is False
