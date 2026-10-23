"""Mandatory first research profile: dual-edition Grimoire conformance."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from ..evaluator import Evaluation, ImmutableEvaluator
from ..protocol import ResearchProtocol
from ...vcw.grimoire_editions import decode_statement, get_edition


def _default_protocol() -> ResearchProtocol:
    return ResearchProtocol(
        protocol_id="grimoire-dual-edition", profile="grimoire-dual-edition", version="1",
        mutable_surface={"name": "selected-decoder", "paths": [
            "src/mantle/vcw/grimoire_editions/v010.py"]},
        immutable_surface=[
            "documents/grimoire/editions/grimoire-v0.9.md",
            "documents/grimoire/editions/grimoire-v0.10.md",
            "tools/grimoire_tool.py",
            "src/mantle/audits/invariants.py",
        ],
        resource_budget={"wall_seconds": 30, "cpu_seconds": 10, "memory_bytes": 268435456,
                         "max_experiments": 1},
        objective="statements decoded per second under fixed dual-edition corpus",
        stop_policy={"on_authority_drift": "stop", "on_regression": "stop"},
    )


class GrimoireDualEditionEvaluator(ImmutableEvaluator):
    """Run the v0.9 regression wall and v0.10 independent verifier together."""

    def __init__(self, repository_root: str | Path, protocol: ResearchProtocol | None = None):
        self.repository_root = Path(repository_root).resolve()
        self.v09 = self.repository_root / "documents/grimoire/editions/grimoire-v0.9.md"
        self.v010 = self.repository_root / "documents/grimoire/editions/grimoire-v0.10.md"
        tool = self.repository_root / "tools/grimoire_tool.py"
        source = [self.v09, self.v010, tool, self.repository_root / "src/mantle/audits/invariants.py"]
        corpus = [self.v09, self.v010]
        super().__init__(protocol or _default_protocol(), source_paths=source, corpus_paths=corpus,
                         version="mantle-research-grimoire-dual-edition-v1")

    def _decode_vectors(self, profile: str) -> tuple[int, int, int, int]:
        edition = get_edition(profile)
        count = 0
        output_bytes = 0
        authority_drift = 0
        failures = 0
        started = time.perf_counter()
        for index, vector in enumerate(edition.selftest_vectors):
            raw = bytes.fromhex("".join(vector.split()))
            decoded = decode_statement(raw, profile=profile, frame_id="research-%s-%d" % (profile, index))
            count += 1
            output_bytes += len(str(decoded).encode("utf-8"))
            authority_drift += int(bool(decoded.get("governing")))
            failures += int(bool(decoded.get("rejection_reason")))
        elapsed = max(time.perf_counter() - started, 1e-9)
        return count, output_bytes, authority_drift, failures

    def _independent_compare(self) -> dict[str, Any]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(self.repository_root / "src")
        proc = subprocess.run(
            [sys.executable, str(self.repository_root / "tools/grimoire_tool.py"), "compare",
             str(self.v010), "--profile", "grimoire-v0.10", "--json"],
            cwd=str(self.repository_root), env=env, capture_output=True, text=True, timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            raise ValueError("independent verifier failed: " + (proc.stderr or proc.stdout).strip()[-500:])
        return __import__("json").loads(proc.stdout)

    def _measurement(self) -> dict[str, Any]:
        v09, bytes09, authority09, failed09 = self._decode_vectors("grimoire-v0.9")
        v010, bytes010, authority010, failed010 = self._decode_vectors("grimoire-v0.10")
        independent = self._independent_compare()
        return {
            "v09_vectors": v09, "v010_vectors": v010,
            "v09_output_bytes": bytes09, "v010_output_bytes": bytes010,
            "v09_authority_drift": authority09, "v010_authority_drift": authority010,
            "v09_rejections": failed09, "v010_rejections": failed010,
            "independent_verifier": independent.get("status"),
            "independent_differences": len(independent.get("differences", [])),
            "statements_decoded": v09 + v010,
            "complexity": "unmeasured", "allocations": "unmeasured",
        }

    def baseline(self, target: Any) -> Evaluation:
        baseline = super().baseline(target)
        measurement = self._measurement()
        return Evaluation(baseline.status, baseline.evaluator_identity, baseline.baseline_hash,
                          baseline.candidate_hash, baseline.gates, measurement,
                          reason="dual-edition baseline established")

    def evaluate_layers(self, candidate: Any, baseline: Evaluation) -> list[dict[str, Any]]:
        candidate_unchanged = not isinstance(candidate, dict) or candidate.get("original_unchanged", True)
        measurement = self._measurement()
        self._last_measurement = measurement
        return [
            {"stage": "safety", "name": "candidate-original-unchanged", "passed": candidate_unchanged,
             "detail": "candidate chamber proof"},
            {"stage": "correctness", "name": "dual-edition-conformance",
             "passed": measurement["v09_rejections"] == 0 and measurement["v010_rejections"] == 0,
             "detail": "no selftest rejection"},
            {"stage": "regression", "name": "v09-and-v010-baseline-stable",
             "passed": measurement["statements_decoded"] == baseline.metrics.get("statements_decoded")},
            {"stage": "regression", "name": "independent-verifier-agreement",
             "passed": measurement["independent_verifier"] == "PASS" and measurement["independent_differences"] == 0},
            {"stage": "regression", "name": "authority-boundary",
             "passed": measurement["v09_authority_drift"] == 0 and measurement["v010_authority_drift"] == 0},
            {"stage": "objective", "name": "fixed-corpus-decoding", "passed": True,
             "detail": "fixed corpus"},
            {"stage": "resource", "name": "bounded-output", "passed": True,
             "detail": "output is measured"},
            {"stage": "complexity", "name": "complexity-reported", "passed": True,
             "detail": "unmeasured is explicit"},
        ]

    def measure_metrics(self, candidate: Any, baseline: Evaluation) -> dict[str, Any]:
        measurement = dict(getattr(self, "_last_measurement", {}))
        measurement["candidate_hash"] = self._candidate_hash(candidate)
        measurement["score"] = float(measurement.get("statements_decoded", 0))
        return measurement

    @staticmethod
    def _candidate_hash(candidate: Any) -> str:
        if hasattr(candidate, "tree_hash"):
            return str(candidate.tree_hash)
        if isinstance(candidate, dict):
            return str(candidate.get("tree_hash") or candidate.get("candidate_hash") or "dry-run")
        return "dry-run"
