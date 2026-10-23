"""Compatibility module for deterministic rolling-context delta construction."""
from .projection import ELIGIBLE_BANDS, build_delta, checkpoint_projection, project_entry

__all__ = [
    "ELIGIBLE_BANDS", "build_delta", "checkpoint_projection", "project_entry",
]
