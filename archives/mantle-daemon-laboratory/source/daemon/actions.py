from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .heart import CheckpointUnavailable, Heart


@dataclass
class ActionsResult:
    persisted: bool
    reason: str


class ActionsEmulator:
    """Exercise the same Heart entry point under Actions-like write modes."""

    def run(self, root: Path, write_enabled: bool = True, lose_write_mid_run: bool = False) -> ActionsResult:
        state = {"enabled": bool(write_enabled)}

        def guard() -> bool:
            if lose_write_mid_run:
                state["enabled"] = False
            return state["enabled"]

        try:
            Heart(Path(root), checkpoint_guard=guard).beat()
        except CheckpointUnavailable as exc:
            return ActionsResult(False, str(exc))
        return ActionsResult(True, "checkpoint committed")

