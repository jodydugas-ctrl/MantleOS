"""Immutable evaluator base for bounded research trials."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Iterable, Mapping

from .chamber import CandidateArtifact
from .protocol import GATE_ORDER, ResearchProtocol


class EvaluatorError(RuntimeError):
    """Evaluation could not establish an immutable measurement surface."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(path: Path) -> str:
    if path.is_dir():
        rows = []
        for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
            current = Path(dirpath)
            for filename in sorted(filenames):
                item = current / filename
                if item.is_symlink():
                    raise EvaluatorError("symlink in immutable surface: %s" % item)
                data = item.read_bytes()
                rows.append({"path": item.relative_to(path).as_posix(),
                             "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
        payload = _canonical(rows)
    elif path.is_file() and not path.is_symlink():
        payload = path.read_bytes()
    else:
        raise EvaluatorError("immutable surface path is absent or unsafe: %s" % path)
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _paths_digest(paths: Iterable[str | Path]) -> str:
    rows = []
    for raw in paths:
        path = Path(raw).resolve()
        rows.append({"path": str(path), "digest": _digest(path)})
    return "sha256:" + hashlib.sha256(_canonical(rows)).hexdigest()


def _target_hash(target: Any) -> str:
    if isinstance(target, CandidateArtifact):
        return target.tree_hash
    if isinstance(target, Mapping):
        for key in ("tree_hash", "candidate_hash", "target_hash"):
            if target.get(key):
                return str(target[key])
    return "sha256:" + hashlib.sha256(_canonical(target)).hexdigest()


@dataclass(frozen=True)
class Evaluation:
    status: str
    evaluator_identity: Mapping[str, Any]
    baseline_hash: str
    candidate_hash: str
    gates: tuple[Mapping[str, Any], ...] = ()
    metrics: Mapping[str, Any] = field(default_factory=dict)
    score: float | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "evaluator_identity": dict(self.evaluator_identity),
                "baseline_hash": self.baseline_hash, "candidate_hash": self.candidate_hash,
                "gates": [dict(gate) for gate in self.gates], "metrics": dict(self.metrics),
                "score": self.score, "reason": self.reason}


class ImmutableEvaluator:
    """Evaluate candidates only while the evaluator and corpus remain byte-identical."""

    evaluator_version = "mantle-research-evaluator-v1"

    def __init__(self, protocol: ResearchProtocol, *, source_paths: Iterable[str | Path],
                 corpus_paths: Iterable[str | Path], version: str | None = None):
        self.protocol = protocol
        self.source_paths = tuple(Path(path).resolve() for path in source_paths)
        self.corpus_paths = tuple(Path(path).resolve() for path in corpus_paths)
        if not self.source_paths or not self.corpus_paths:
            raise EvaluatorError("source and corpus surfaces are mandatory")
        self.version = version or self.evaluator_version

    def environment_receipt(self) -> dict[str, str]:
        return {"python": platform.python_version(), "implementation": platform.python_implementation(),
                "platform": platform.platform(), "os": os.name}

    def identity(self) -> dict[str, Any]:
        return {
            "evaluator": self.__class__.__module__ + "." + self.__class__.__qualname__,
            "version": self.version, "protocol_hash": self.protocol.digest,
            "source_hash": _paths_digest(self.source_paths),
            "corpus_hash": _paths_digest(self.corpus_paths),
            "environment": self.environment_receipt(),
        }

    def baseline(self, target: Any) -> Evaluation:
        if target is None:
            raise EvaluatorError("baseline target is mandatory")
        identity = self.identity()
        target_hash = _target_hash(target)
        return Evaluation("BASELINE", identity, target_hash, target_hash,
                          metrics={"baseline": True}, reason="baseline established")

    def evaluate_layers(self, candidate: Any, baseline: Evaluation) -> list[dict[str, Any]]:
        unchanged = not isinstance(candidate, Mapping) or candidate.get("original_unchanged", True)
        return [{"stage": "safety", "name": "original_unchanged", "passed": unchanged,
                 "detail": "candidate did not alter original" if unchanged else "original changed"}]

    def measure_metrics(self, candidate: Any, baseline: Evaluation) -> Mapping[str, Any]:
        return {"candidate_hash": _target_hash(candidate), "complexity": "unmeasured"}

    def evaluate(self, candidate: Any, baseline: Evaluation) -> Evaluation:
        candidate_hash = _target_hash(candidate)
        try:
            before = self.identity()
            if baseline.status != "BASELINE":
                raise EvaluatorError("evaluation requires a BASELINE result")
            if dict(baseline.evaluator_identity) != before:
                raise EvaluatorError("baseline evaluator or corpus identity changed")
            gates = []
            for index, gate in enumerate(self.evaluate_layers(candidate, baseline)):
                stage = str(gate.get("stage") or (GATE_ORDER[index] if index < len(GATE_ORDER) else "complexity"))
                row = {"stage": stage, "name": str(gate.get("name", stage)),
                       "passed": bool(gate.get("passed")),
                       "detail": str(gate.get("detail", ""))}
                gates.append(row)
                if not row["passed"]:
                    after = self.identity()
                    if after != before:
                        return Evaluation("ABORTED", after, baseline.baseline_hash, candidate_hash,
                                           tuple(gates), reason="evaluator or corpus changed during evaluation")
                    return Evaluation("FAIL", before, baseline.baseline_hash, candidate_hash,
                                       tuple(gates), reason="gate failed: " + row["name"])
            metrics = dict(self.measure_metrics(candidate, baseline))
            after = self.identity()
            if after != before:
                return Evaluation("ABORTED", after, baseline.baseline_hash, candidate_hash,
                                  tuple(gates), metrics, reason="evaluator or corpus changed during evaluation")
            return Evaluation("PASS", before, baseline.baseline_hash, candidate_hash,
                              tuple(gates), metrics, score=float(metrics.get("score", 1.0)))
        except (EvaluatorError, OSError, ValueError, TypeError) as exc:
            try:
                identity = self.identity()
            except Exception:  # noqa: BLE001
                identity = dict(getattr(baseline, "evaluator_identity", {}))
            return Evaluation("ABORTED", identity, baseline.baseline_hash, candidate_hash,
                              reason=str(exc))
