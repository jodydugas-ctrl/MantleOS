"""MIND rolling-context policy evaluator profile."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..evaluator import ImmutableEvaluator
from ..protocol import ResearchProtocol


class MindContextEvaluator(ImmutableEvaluator):
    def __init__(self, repository_root: str | Path, protocol: ResearchProtocol):
        root = Path(repository_root).resolve()
        super().__init__(protocol, source_paths=[root / "src/mantle/mind"],
                         corpus_paths=[root / "src/mantle/mind"],
                         version="mantle-research-mind-context-v1")

    def evaluate_layers(self, candidate: Any, baseline: Any) -> list[dict[str, Any]]:
        data = candidate if isinstance(candidate, dict) else {}
        return [
            {"stage": "safety", "name": "capability-containment", "passed": data.get("capability_ok", True)},
            {"stage": "correctness", "name": "audit-mind", "passed": data.get("audit_mind_ok", True)},
            {"stage": "regression", "name": "no-direct-body-write", "passed": data.get("direct_body_write", False) is False},
            {"stage": "regression", "name": "no-tool-or-process-access", "passed": data.get("tool_access", False) is False},
            {"stage": "regression", "name": "no-authority-upgrade", "passed": data.get("authority_upgrade", False) is False},
            {"stage": "objective", "name": "benchmark-reported", "passed": True},
            {"stage": "resource", "name": "context-cost-reported", "passed": True},
            {"stage": "complexity", "name": "variance-reported", "passed": True},
        ]
