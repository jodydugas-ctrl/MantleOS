from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mantle.ancestry import query_ancestor
from mantle.assimilator.artifact_validation import validate_artifact
from mantle.assimilator.report import dry_run
from mantle.certify import CertificationError, certify_nest
from mantle.contracts import ClaimStatus, HostAdapter, ResidentRuntime
from mantle.core.organism import Organism
from mantle.governance import (
    EnergyPolicy,
    SpendAuthorization,
    TaskClass,
    authorize_spend,
    reconcile_provider_receipt,
)
from mantle.lifecycle import (
    LifecycleAction,
    LifecycleAuthorization,
    begin_transaction,
    canonical_target,
    resume_transaction,
)
from mantle.phenotype import express, phenotype_bands, wear
from mantle.primer import appai_commandments, appai_truths
from mantle.proofs import ActionExecutionProof, MutationClass
from mantle.resident.commands import BodyCommandDispatcher
from mantle.resources import (
    FakeResourceOfferAdapter,
    ResourceOfferError,
    ResourceOfferInbox,
)


def born(genome=None):
    return Organism.birth(
        {"name": "Mantle2Test"}, appai_truths(), appai_commandments(), genome=genome
    )


def test_claim_and_resident_evidence_firewall_and_proof_lane():
    assert ResidentRuntime.classify_claim("unsupported", ClaimStatus.VERIFIED).status == ClaimStatus.REFUSED

    class Provider:
        last_usage = {"cost": 0.0, "resolved_model": "fake/model"}

        def __call__(self, _prompt):
            return "Done\x1b[31m <APPAI_BODY>{\"action\":\"save\",\"surface\":\"doc\"}</APPAI_BODY>"

    class Adapter(HostAdapter):
        def execute(self, request):
            return ActionExecutionProof(
                request["action"], request["surface"], "window-1", "low",
                MutationClass.REVERSIBLE, {"text": "before"}, {"called": True},
                {"text": "after"}, "fixture-readback", True, "vcw-1",
            )

    org = born()
    result = ResidentRuntime(BodyCommandDispatcher(org), Adapter(), Provider()).turn("save it")
    assert result.route == "mind"
    assert "APPAI_BODY" not in result.visible_output and "\x1b" not in result.visible_output
    assert result.body_proofs[0]["verified"] is True
    assert result.answer.claims[0].status == ClaimStatus.INFERRED
    assert result.provider_receipt["resolved_model"] == "fake/model"
    assert any(row["opcode"] == "USER_MESSAGE" for row in org.memory.recall("events"))


def test_metabolic_policy_ceiling_approval_and_receipt_reconciliation():
    policy = EnergyPolicy(2, 4, 8)
    with pytest.raises(PermissionError):
        authorize_spend(policy, TaskClass.REPRODUCTION, 1)
    approval = SpendAuthorization.issue(TaskClass.REPRODUCTION, 1, operator_approved=True)
    assert authorize_spend(policy, TaskClass.REPRODUCTION, 1, authorization=approval) == approval
    missing = reconcile_provider_receipt(approval, None)
    assert missing["charged_energy"] == 1 and missing["immune_event"] == "missing_usage_receipt"
    free = reconcile_provider_receipt(approval, {"cost": 0, "model": "free"})
    assert free["zero_cost"] is True and free["charged_energy"] == 0
    with pytest.raises(PermissionError):
        authorize_spend(policy, TaskClass.CONVERSATION, 1, daily_spend=8)


def test_resource_offer_is_other_bounded_one_shot_and_plaintext_secret_refused(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    good = inbox / "offer.json"
    good.write_text(json.dumps({"classification": "OTHER", "type": "fixture", "name": "demo"}))
    body = ResourceOfferInbox(str(inbox), FakeResourceOfferAdapter())
    receipt = body.process(str(good))
    assert receipt["offer"]["classification"] == "OTHER"
    assert receipt["raw_secret_stored"] is False
    with pytest.raises(ResourceOfferError):
        body.process(str(good))
    bad = inbox / "bad.json"
    bad.write_text(json.dumps({"classification": "OTHER", "nested": {"api_key": "sentinel"}}))
    with pytest.raises(ResourceOfferError, match="plaintext"):
        body.inspect(str(bad))


def test_face_attestation_and_ancestor_query_are_explicit_and_read_only():
    from mantle.vcw.bands import standard_genome
    genome = standard_genome() + phenotype_bands()
    org = born(genome)
    org.senses.surface_map = {"editor": {}}
    express(org, "plain", "html", "<p>x</p>", controls=[{"id": "editor"}],
            capabilities={"save": True})
    result = wear(org, "plain")
    attestation = result["face_attestation"]
    assert attestation["appai_identity"] == "Mantle2Test"
    assert attestation["verified_socket_capabilities"] == ["editor"]
    assert attestation["wear_event_id"] != "unavailable"
    org.memory.remember("facts", {"fact": "old"}, opcode="OBSERVED", verified=True)
    org.rebirth(reason="fixture")
    rows = query_ancestor(org, 0)
    assert rows[0].generation == 0 and rows[0].evidence_status == "verified"
    assert org.ancestral[0].sealed is True


def test_lifecycle_resume_only_promotes_verified_stage(tmp_path: Path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}")
    target = tmp_path / "new-target"
    auth = LifecycleAuthorization.issue(LifecycleAction.HATCH, str(artifact), str(target))
    tx = begin_transaction(auth, LifecycleAction.HATCH, str(artifact), str(target))
    (Path(tx.staging) / "proof.txt").write_text("verified")
    tx.phase("artifact_verified")
    tx.interrupt("promote")
    resumed = resume_transaction(tx.staging)
    assert resumed.promote() == canonical_target(str(target))
    assert (target / "proof.txt").read_text() == "verified"
    journal = json.loads((target / "lifecycle_journal.json").read_text())
    assert journal["result"] == "PASS" and journal["phase"] == "promoted"


def test_resident_migration_is_journaled_and_preserves_source(tmp_path: Path):
    from mantle.migration import migrate_resident
    source = tmp_path / "source"
    born().save(str(source))
    original = (source / "organism.json").read_bytes()
    out = tmp_path / "migrated"
    result = migrate_resident(str(source), str(out))
    assert result["result"] == "PASS" and result["activated"] is False
    assert (source / "organism.json").read_bytes() == original
    journal = json.loads((out / "migration_journal.json").read_text())
    assert journal["result"] == "PASS" and journal["phase"] == "promoted"


def test_artifact_grammars_and_assimilation_report_emit_actual_state(tmp_path: Path):
    (tmp_path / "main.cpp").write_text("int main() { return 0; }")
    report = dry_run(str(tmp_path))["map"]
    assert report["insertion_state"] == "observed_causal_graph"
    assert report["runtime_hook_verified"] is False
    assert validate_artifact("cpp", "int main() { return 0; }").valid
    assert validate_artifact("qt-ui", "<ui><widget/></ui>").valid
    assert validate_artifact("qrc", "<RCC><qresource/></RCC>").valid
    assert validate_artifact("cmake", "add_executable(app main.cpp)").valid
    assert validate_artifact("rust", "fn main() {}").valid
    assert not validate_artifact("rust", "fn main( {").valid


def test_resident_protocol_declaration_is_required_for_certification(tmp_path: Path):
    nest = tmp_path / "nest"
    org = born()
    org.save(str(nest))
    assert certify_nest(str(nest), include_invariants=False)["stage1"]["passed"]
    (nest / "resident_protocol.json").unlink()
    with pytest.raises(CertificationError, match="protocol drift"):
        certify_nest(str(nest), include_invariants=False)


def test_application_certification_names_failed_repository_invariant(tmp_path: Path, monkeypatch):
    import mantle.certify as certification
    nest = tmp_path / "nest"
    born().save(str(nest))
    monkeypatch.setattr(certification._inv, "run_all", lambda: [{
        "name": "SPORE-2 sporeagent-lifecycle-receipt", "ok": False,
        "detail": "Pillow missing",
    }])
    with pytest.raises(CertificationError, match="SPORE-2.*Pillow missing"):
        certification.certify_nest(str(nest))


def test_top_level_help_is_a_successful_read_only_command(capsys):
    from mantle.cli import main
    assert main(["--help"]) == 0
    assert "usage: python -m mantle" in capsys.readouterr().out
    assert main(["definitely-not-a-command"]) == 1
