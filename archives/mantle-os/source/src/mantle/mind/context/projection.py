"""Deterministic, privacy-veiled projection from resolved VCW snapshots."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from ...core.redact import redact
from .types import SourceCursor


ELIGIBLE_BANDS: Tuple[str, ...] = (
    "facts", "events", "discoveries", "senses", "conversation",
)
EXCLUDED_BANDS = frozenset({"thoughts", "brain", "immune", "context", "context_ledger"})


def project_entry(band: str, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if band in EXCLUDED_BANDS:
        return None
    if entry.get("tombstone") or entry.get("quarantined"):
        return None
    entry_id = entry.get("id")
    if not isinstance(entry_id, int) or isinstance(entry_id, bool):
        return None
    projected = {
        "source_band": band,
        "source_id": entry_id,
        "opcode": entry.get("opcode"),
        "content": redact(entry.get("content")),
        "verified": entry.get("verified"),
        "confidence": entry.get("confidence"),
    }
    return projected


def build_delta(
    snapshot: Dict[str, Any],
    cursor: SourceCursor,
) -> Tuple[List[Dict[str, Any]], SourceCursor, Dict[str, List[int]]]:
    entries: List[Dict[str, Any]] = []
    after = cursor.as_dict()
    ranges: Dict[str, List[int]] = {}
    before = cursor.as_dict()
    for band in ELIGIBLE_BANDS:
        source: Sequence[Any] = snapshot.get(band, []) or []
        projected_band: List[Dict[str, Any]] = []
        for raw in source:
            if not isinstance(raw, dict):
                continue
            entry = project_entry(band, raw)
            if entry is None or entry["source_id"] < before[band]:
                continue
            projected_band.append(entry)
        projected_band.sort(key=lambda item: item["source_id"])
        if projected_band:
            ids = [item["source_id"] for item in projected_band]
            ranges[band] = [ids[0], ids[-1]]
            after[band] = ids[-1] + 1
            entries.extend(projected_band)
    entries.sort(key=lambda item: (ELIGIBLE_BANDS.index(item["source_band"]),
                                   item["source_id"]))
    return entries, SourceCursor.from_mapping(after), ranges


def checkpoint_projection(
    snapshot: Dict[str, Any],
    *,
    per_band: int,
) -> Tuple[List[Dict[str, Any]], SourceCursor]:
    selected: List[Dict[str, Any]] = []
    cursors = SourceCursor().as_dict()
    for band in ELIGIBLE_BANDS:
        projected = [
            item for item in (
                project_entry(band, raw)
                for raw in (snapshot.get(band, []) or [])
                if isinstance(raw, dict)
            )
            if item is not None
        ]
        projected.sort(key=lambda item: item["source_id"])
        if projected:
            cursors[band] = projected[-1]["source_id"] + 1
            selected.extend(projected[-per_band:])
    return selected, SourceCursor.from_mapping(cursors)
