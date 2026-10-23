import json
from pathlib import Path

from mantle.cli import main


def _json(capsys):
    return json.loads(capsys.readouterr().out)


def test_cli_serial_workflow_and_separate_authority_commands(tmp_path: Path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("MANTLE_RESEARCH_ROOT", str(root))
    protocol_path = tmp_path / "protocol.json"
    assert main(["research-init", "grimoire-dual-edition", "--out=" + str(protocol_path)]) == 0
    protocol = _json(capsys)
    assert protocol["profile"] == "grimoire-dual-edition"

    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps({
        "experiment_id": "cli-1", "operator_authorized": True,
        "candidate": {}, "artifact_policy": "discard",
    }), encoding="utf-8")
    assert main(["research-propose", str(protocol_path), str(proposal_path)]) == 0
    proposed = _json(capsys)
    assert proposed["status"] == "PROPOSED"

    assert main(["research-trial", str(protocol_path), proposed["proposal_id"]]) == 0
    trial = _json(capsys)
    assert trial["status"] == "ELIGIBLE"

    receipt_path = tmp_path / "operator.json"
    receipt_path.write_text(json.dumps({
        "protocol": str(protocol_path), "experiment_id": "cli-1",
        "operator_authorized": True, "kind": "operator-research-authority",
    }), encoding="utf-8")
    assert main(["research-authorize", "cli-1", "--operator-receipt=" + str(receipt_path)]) == 0
    assert _json(capsys)["status"] == "AUTHORIZED"
    assert main(["research-adopt", "cli-1", "--operator-receipt=" + str(receipt_path)]) == 0
    adopted = _json(capsys)
    assert adopted["status"] == "ADOPTED"
    assert adopted["automatic"] is False


def test_research_cli_help_disclaims_self_adoption(capsys):
    assert main(["research-trial"]) != 0
    assert "does not self-adopt" in capsys.readouterr().out.lower()
