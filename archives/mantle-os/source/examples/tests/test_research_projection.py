from mantle.research import project_receipt, project_procedure


def test_projection_is_derived_and_missing_container_is_non_governing():
    receipt = {"kind": "mind_hypothesis", "experiment_id": "p-1", "hypothesis": "faster"}
    projection = project_receipt(receipt, frame_id="research-p-1")
    assert projection["canonical_record_hash"].startswith("sha256:")
    assert projection["semantic_projection_status"] == "ok"
    assert projection["decoded"]["effective_evidence"] == "INHERIT"
    assert projection["decoded"]["governing"] is False
    assert "container_evidence" in projection["decoded"]["unknowns"]
    assert projection["canonical_record"] == receipt


def test_procedure_round_trip_preserves_container_labels_and_authority_boundary():
    projection = project_procedure(
        ["establish baseline", "propose one candidate", "measure"],
        frame_id="research-procedure-1", container_evidence="STIPULATED",
        container_force="WAY",
    )
    decoded = projection["decoded"]
    assert decoded["effective_evidence"] == "STIPULATED"
    assert decoded["effective_force"] == "WAY"
    assert decoded["evidence_source"] == "container"
    assert decoded["force_source"] == "container"
    assert decoded["governing"] is False
    assert projection["adoption"]["governing"] is False


def test_projection_failure_keeps_canonical_record():
    receipt = {"kind": "measured_result", "experiment_id": "bad"}
    projection = project_receipt(receipt, frame_id="bad", procedure_steps=[])
    assert projection["semantic_projection_status"] == "failed"
    assert projection["canonical_record"] == receipt
