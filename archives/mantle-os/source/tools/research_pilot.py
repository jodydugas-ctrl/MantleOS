"""Run the mandatory serial Grimoire dual-edition research pilot."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mantle.core.body import Body
from mantle.research import (BoundedProcessRunner, CandidateChamber, ProcessBudget,
                             ResearchGanglion, ResearchLedger, ResearchProtocol,
                             SourceWorktreeAdapter, save_protocol)
from mantle.research.profiles.grimoire import GrimoireDualEditionEvaluator, _default_protocol


class ForcedDiscardEvaluator(GrimoireDualEditionEvaluator):
    """Control fixture for proving a failed hard gate reaches DISCARDED."""

    def evaluate_layers(self, candidate, baseline):
        return [{"stage": "correctness", "name": "pilot-discard-control", "passed": False,
                 "detail": "intentional control failure; no candidate authority"}]


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items() if key != "artifact"}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _protocol():
    base = _default_protocol().to_dict()
    base["resource_budget"] = dict(base["resource_budget"], max_experiments=4)
    base["stop_policy"] = dict(base["stop_policy"], max_experiments=4)
    return ResearchProtocol.from_dict(base)


def _ganglion(body, ledger, protocol, evaluator, root, *, runner):
    return ResearchGanglion(
        body=body, ledger=ledger, protocol=protocol, evaluator=evaluator,
        chamber=CandidateChamber(SourceWorktreeAdapter(
            root, allowlist=protocol.mutable_surface["paths"])),
        runner=runner,
        budget=ProcessBudget(1, 1, 256 * 1024 * 1024, 64 * 1024, 256),
        energy=lambda: float("inf"),
    )


def _experiment_summaries(history):
    ids = sorted({event.get("experiment_id") for event in history if event.get("experiment_id")})
    summaries = []
    for experiment_id in ids:
        events = [event for event in history if event.get("experiment_id") == experiment_id]
        transitions = [event for event in events if event.get("event") == "transition"]
        measured = next((event for event in transitions if event.get("status") == "MEASURED"), {})
        materialized = next((event for event in transitions if event.get("status") == "MATERIALIZED"), {})
        process = next((event.get("process") for event in transitions if event.get("process") is not None), None)
        summaries.append({
            "experiment_id": experiment_id,
            "statuses": [event.get("status") for event in transitions],
            "receipt_hashes": [event.get("receipt_hash") for event in events],
            "protocol_hash": next((event.get("protocol_hash") for event in events), None),
            "candidate_hash": materialized.get("candidate_hash"),
            "evaluation": measured.get("evaluation"),
            "process": process,
            "adopted": any(event.get("status") == "ADOPTED" for event in transitions),
        })
    return summaries


def main():
    output = ROOT / ".artifacts" / "research-pilot"
    output.mkdir(parents=True, exist_ok=True)
    protocol = _protocol()
    save_protocol(protocol, str(output / "protocol.json"))
    body = Body()
    ledger = ResearchLedger.new(body)
    runner = BoundedProcessRunner()
    evaluator = GrimoireDualEditionEvaluator(ROOT, protocol=protocol)
    baseline = evaluator.baseline({"tree_hash": "pilot-baseline"})
    actual = _ganglion(body, ledger, protocol, evaluator, ROOT, runner=runner)
    eligible = actual.pulse({
        "experiment_id": "pilot-eligible", "operator_authorized": True,
        "candidate": {}, "artifact_policy": "discard",
    })
    crashed = actual.pulse({
        "experiment_id": "pilot-crashed", "operator_authorized": True,
        "candidate": {}, "argv": [sys.executable, "-c", "import time; time.sleep(5)"],
        "env": {}, "artifact_policy": "discard",
    })
    discard = _ganglion(body, ledger, protocol,
                        ForcedDiscardEvaluator(ROOT, protocol=protocol), ROOT, runner=runner).pulse({
        "experiment_id": "pilot-discarded", "operator_authorized": True,
        "candidate": {}, "artifact_policy": "discard",
    })

    fixture_body = Body()
    fixture_ledger = ResearchLedger.new(fixture_body)
    fixture_ledger.propose({"experiment_id": "authority-fixture", "kind": "pilot-fixture"})
    fixture_ledger.transition("authority-fixture", "MATERIALIZED")
    fixture_ledger.transition("authority-fixture", "RUNNING")
    fixture_ledger.transition("authority-fixture", "MEASURED")
    fixture_ledger.transition("authority-fixture", "ELIGIBLE")
    operator_receipt = {"kind": "pilot-operator-fixture", "operator_authorized": True}
    authorized = fixture_ledger.authorize("authority-fixture", operator_receipt)
    adopted = fixture_ledger.adopt("authority-fixture", operator_receipt)

    history = ledger.history()
    report = {
        "schema": "mantle.research.pilot-report.v1",
        "profile": protocol.profile,
        "protocol": protocol.to_dict(),
        "protocol_hash": protocol.digest,
        "baseline": baseline.to_dict(),
        "experiments": _experiment_summaries(history),
        "results": [_jsonable(eligible), _jsonable(crashed), _jsonable(discard)],
        "stop_reason": "serial pilot completed; no parallel wave authorized",
        "production_adoption": {"occurred": False, "reason": "eligibility is not adoption"},
        "authority_fixture": {"authorized_status": authorized["status"],
                               "adopted_status": adopted["status"], "automatic": False},
        "ledger_tail_hash": ledger.snapshot()["tail_hash"],
        "ledger": ledger.snapshot(),
    }
    (output / "grimoire-dual-edition-report.json").write_text(
        json.dumps(_jsonable(report), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "report": str(output / "grimoire-dual-edition-report.json"),
                      "experiments": [item["statuses"] for item in report["experiments"]],
                      "production_adoption": False}, sort_keys=True))


if __name__ == "__main__":
    main()
