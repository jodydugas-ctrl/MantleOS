"""Notepad — Round 1, BH-EDITOR-INPUT.

This module implements exactly one Anchor application. It captures raw editor
intent without validating, applying, persisting, or otherwise interpreting it.
Those operations belong to future WhiteHole and Neutral applications.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EditorIntent:
    """An input observation. Not an approved or executed command."""
    action: Any
    payload: Any = None


class BlackHoleEditorInput:
    """BlackHole BH-EDITOR-INPUT: receive a user/editor input event."""

    anchor_id = "BH-EDITOR-INPUT"
    canonical_type = "BlackHole"

    @staticmethod
    def receive(action: Any, payload: Any = None) -> EditorIntent:
        """Capture inputs as supplied; do not interpret, guard, or mutate them."""
        return EditorIntent(action=action, payload=payload)
