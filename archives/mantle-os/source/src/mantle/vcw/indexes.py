#!/usr/bin/env python3
"""
mantle.vcw.indexes  --  compact per-band read indexes (Mantle OS)

The VCW's logical address for an entry is its index into the band's concatenated VISIBLE
stream (so physical layer reuse never breaks a reference). v2 resolved that address by
re-reading and re-filtering every layer on every retrieve. Mantle keeps a small per-band index:

    band -> [ (physical_layer, position_in_layer), ... ]   one slot per VISIBLE entry
    band -> { entry_id -> visible_index }                  reverse lookup for marks

The index is a pure memo, invalidated on any mutation (append, tombstone, quarantine,
compaction) and rebuilt lazily on the next read. Dropping it only makes the next read
slower, never wrong.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class BandIndexes:
    def __init__(self) -> None:
        self._positions: Dict[str, List[Tuple[int, int]]] = {}   # band -> [(layer, pos)]
        self._by_id: Dict[str, Dict[int, int]] = {}              # band -> {id -> visible idx}

    # ---- invalidation ------------------------------------------------------
    def invalidate(self, band: Optional[str] = None) -> None:
        if band is None:
            self._positions.clear()
            self._by_id.clear()
        else:
            self._positions.pop(band, None)
            self._by_id.pop(band, None)

    # ---- (re)build ---------------------------------------------------------
    def build(self, band: str, layer_indices: List[int], content_of) -> None:
        """Rebuild the index for one band. `content_of(idx)` returns a layer's entry list."""
        positions: List[Tuple[int, int]] = []
        by_id: Dict[int, int] = {}
        for layer in layer_indices:
            entries = content_of(layer)
            for pos, e in enumerate(entries):
                if not e.get("tombstone") and not e.get("quarantined"):
                    if e.get("id") is not None:
                        by_id[e["id"]] = len(positions)
                    positions.append((layer, pos))
        self._positions[band] = positions
        self._by_id[band] = by_id

    def has(self, band: str) -> bool:
        return band in self._positions

    # ---- queries -----------------------------------------------------------
    def visible_count(self, band: str) -> int:
        return len(self._positions[band])

    def locate(self, band: str, visible_index: int) -> Optional[Tuple[int, int]]:
        """Map a logical visible index -> (physical layer, position in layer)."""
        slots = self._positions[band]
        return slots[visible_index] if 0 <= visible_index < len(slots) else None

    def locate_id(self, band: str, entry_id: int) -> Optional[Tuple[int, int]]:
        vi = self._by_id[band].get(entry_id)
        return None if vi is None else self.locate(band, vi)
