from pathlib import Path
import sys

from mantle.core.body import Body
from mantle.research import (
    BoundedProcessRunner,
    CandidateChamber,
    ProcessBudget,
    ResearchGanglion,
    ResearchLedger,
    ResearchProtocol,
    SourceWorktreeAdapter,
)
from mantle.research.evaluator import ImmutableEvaluator


class DemoEvaluator(ImmutableEvaluator):
    def evaluate_layers(self, candidate, baseline):
        return [{"stage": "safety", "name": "demo", "passed": True}]


class DemoHeart:
    def __init__(self):
        self.requests = []

    def schedule_pulse(self, **kwargs):
        self.requests.append(kwargs)
        return len(self.requests)


def _ganglion(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "candidate.txt").write_text("baseline", encoding="utf-8")
    evaluator_file = tmp_path / "evaluator.txt"
    evaluator_file.write_text("evaluator", encoding="utf-8")
    protocol = ResearchProtocol(
        protocol_id="demo", profile="test", version="1",
        mutable_surface={"name": "source", "paths": ["candidate.txt"]},
        immutable_surface=["evaluator.txt"],
        resource_budget={"wall_seconds": 2, "cpu_seconds": 1, "memory_bytes": 64 * 1024 * 1024,
                         "output_bytes": 4096, "max_experiments": 2}, objective="demo",
    )
    evaluator = DemoEvaluator(protocol, source_paths=[evaluator_file], corpus_paths=[evaluator_file])
    body = Body()
    ledger = ResearchLedger.new(body)
    heart = DemoHeart()
    runner = BoundedProcessRunner()
    budget = ProcessBudget(2, 1, 64 * 1024 * 1024, 4096, 16)
    ganglion = ResearchGanglion(
        body=body, ledger=ledger, protocol=protocol, evaluator=evaluator,
        chamber=CandidateChamber(SourceWorktreeAdapter(source, allowlist={"candidate.txt"})),
        runner=runner, budget=budget, energy=lambda: 10.0, heart=heart,
    )
    return ganglion, ledger, heart


def test_serial_pulse_writes_complete_sequence_and_schedules_once(tmp_path: Path):
    ganglion, ledger, heart = _ganglion(tmp_path)
    result = ganglion.pulse({
        "experiment_id": "demo-1", "operator_authorized": True,
        "candidate": {"files": {"candidate.txt": "candidate"}},
        "argv": [sys.executable, "-c", "print('trial')"], "env": {},
        "artifact_policy": "preserve",
    })
    statuses = [event.get("status") for event in ledger.history()
                if event.get("event") == "transition"]
    assert statuses == ["PROPOSED", "MATERIALIZED", "RUNNING", "MEASURED", "ELIGIBLE"]
    assert result["status"] == "ELIGIBLE"
    assert len(heart.requests) == 1
    assert result["adopted"] is False


def test_restart_does_not_repeat_completed_transition(tmp_path: Path):
    ganglion, ledger, _heart = _ganglion(tmp_path)
    proposal = {"experiment_id": "demo-2", "operator_authorized": True,
                "candidate": {"files": {"candidate.txt": "candidate"}},
                "argv": [sys.executable, "-c", "pass"], "env": {}}
    first = ganglion.pulse(proposal)
    second = ganglion.pulse(proposal)
    assert first["status"] == "ELIGIBLE"
    assert second["status"] == "ALREADY-COMPLETE"
    assert len([e for e in ledger.history() if e.get("experiment_id") == "demo-2"
                and e.get("event") == "transition" and e.get("status") == "PROPOSED"]) == 1


def test_unauthorized_or_budget_failure_is_receipted_and_never_adopted(tmp_path: Path):
    ganglion, ledger, _heart = _ganglion(tmp_path)
    refused = ganglion.pulse({"experiment_id": "demo-3", "operator_authorized": False,
                              "candidate": {"files": {"candidate.txt": "no"}}})
    assert refused["status"] == "REFUSED"
    assert refused["adopted"] is False
    assert any(e.get("status") == "REFUSED" for e in ledger.history())
