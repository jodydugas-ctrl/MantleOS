from pathlib import Path

import pytest

from mantle.research import ImmutableEvaluator, ResearchProtocol
from mantle.research.profiles.grimoire import GrimoireDualEditionEvaluator


class SyntheticEvaluator(ImmutableEvaluator):
    def evaluate_layers(self, candidate, baseline):
        return [{"name": "safety", "passed": True, "detail": "synthetic"}]


def test_protocol_identity_baseline_and_mutation_abort(tmp_path: Path):
    source = tmp_path / "evaluator.py"
    corpus = tmp_path / "corpus.json"
    source.write_text("immutable", encoding="utf-8")
    corpus.write_text("corpus", encoding="utf-8")
    protocol = ResearchProtocol(
        protocol_id="synthetic", profile="test", version="1",
        mutable_surface={"name": "candidate", "paths": ["candidate.py"]},
        immutable_surface=["evaluator.py", "corpus.json"],
        resource_budget={"wall_seconds": 1}, objective="test",
    )
    evaluator = SyntheticEvaluator(protocol, source_paths=[source], corpus_paths=[corpus])
    baseline = evaluator.baseline({"tree_hash": "baseline"})
    result = evaluator.evaluate({"tree_hash": "candidate"}, baseline)
    assert result.status == "PASS"
    corpus.write_text("changed", encoding="utf-8")
    aborted = evaluator.evaluate({"tree_hash": "candidate"}, baseline)
    assert aborted.status == "ABORTED"
    assert "changed" in aborted.reason


def test_grimoire_profile_dry_run_has_immutable_identity():
    root = Path(__file__).resolve().parents[2]
    evaluator = GrimoireDualEditionEvaluator(root)
    baseline = evaluator.baseline({"mode": "dry-run"})
    result = evaluator.evaluate({"tree_hash": "dry-run", "original_unchanged": True}, baseline)
    assert result.status == "PASS"
    assert result.metrics["v09_vectors"] > 0
    assert result.metrics["v010_vectors"] > 0
    assert result.metrics["independent_verifier"] == "PASS"
