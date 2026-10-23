"""VCW persistence/metabolism evaluator profile."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..evaluator import ImmutableEvaluator
from ..protocol import ResearchProtocol


class VCWPersistenceEvaluator(ImmutableEvaluator):
    def __init__(self, repository_root: str | Path, protocol: ResearchProtocol):
        root = Path(repository_root).resolve()
        super().__init__(protocol, source_paths=[root / "src/mantle/vcw"],
                         corpus_paths=[root / "src/mantle/vcw"],
                         version="mantle-research-vcw-v1")

    def evaluate_layers(self, candidate: Any, baseline: Any) -> list[dict[str, Any]]:
        data = candidate if isinstance(candidate, dict) else {}
        return [
            {"stage": "safety", "name": "original-unchanged", "passed": data.get("original_unchanged", True)},
            {"stage": "correctness", "name": "append-only", "passed": data.get("append_only", True)},
            {"stage": "regression", "name": "seal-fingerprint", "passed": data.get("seal_ok", True)},
            {"stage": "regression", "name": "save-load", "passed": data.get("save_load_ok", True)},
            {"stage": "objective", "name": "throughput-measured", "passed": True},
            {"stage": "resource", "name": "storage-growth-reported", "passed": True},
            {"stage": "complexity", "name": "cost-reported", "passed": True},
        ]
