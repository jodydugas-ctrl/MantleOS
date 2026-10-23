from pathlib import Path

import pytest

from mantle.core.body import Body
from mantle.research import ResearchLedger, ResearchLedgerError


def test_research_ledger_transitions_refusals_and_round_trip(tmp_path: Path):
    body = Body()
    ledger = ResearchLedger.new(body)
    proposal = ledger.propose({
        "schema": "mantle.research.receipt.v1",
        "experiment_id": "exp-1",
        "target_kind": "grimoire",
        "grimoire_profile": "grimoire-v0.10",
    })
    ledger.transition("exp-1", "MATERIALIZED")
    ledger.transition("exp-1", "RUNNING")
    ledger.transition("exp-1", "CRASHED", error="candidate crashed")
    with pytest.raises(ResearchLedgerError):
        ledger.transition("exp-1", "ELIGIBLE")
    history = ledger.history()
    assert history[0]["receipt_hash"].startswith("sha256:")
    assert history[-1]["status"] == "REFUSED"
    assert history[-1]["event"] == "transition_attempt"
    assert all(event["author"] == "BODY" for event in history)

    path = tmp_path / "cube"
    ledger.cube.save(str(path))
    restored = ResearchLedger(body, ledger.cube.load(str(path)))
    assert restored.snapshot()["events"] == history
    assert restored.snapshot()["tail_hash"] == history[-1]["receipt_hash"]
    assert proposal["previous_hash"] is None
