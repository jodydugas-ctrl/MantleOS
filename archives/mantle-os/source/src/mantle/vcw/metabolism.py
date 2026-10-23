#!/usr/bin/env python3
"""
mantle.vcw.metabolism  --  the memory metabolism (Mantle OS)

"Failure is not the end; waste is." Metabolism is how the organism keeps its working set
lean WITHOUT ever losing identity or being forced into a lossy reset:

  compact      drop tombstoned/quarantined entries; an emptied non-tail layer returns to
               the band's free pool for reuse (safe-reuse: only entry-addressed layers)
  dedupe       tombstone entries whose (opcode, content) duplicates an earlier live entry
  reclaim      compact + dedupe in one pass (the standard pressure response)
  pressure     fraction of a band's reserved span currently allocated
  coherence    structural sanity: duplicate ids, active/free overlap

CAPACITY DOCTRINE: crossing OVERFLOW (0.75) or EMERGENCY (0.90) triggers metabolism --
NEVER rebirth. Rebirth stays a separate, chosen reformat (`Organism.rebirth`); reaching
capacity may *motivate* the choice but may never force it.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .bands import OVERFLOW_THRESHOLD, EMERGENCY_THRESHOLD, get_driver
from .entry import content_hash

# the reclaimable, entry-addressed encodings (spatial/exec layers are never recycled)
ENTRY_ENCODINGS = ("log-json", "keyvalue", "grimoire-v0.10-entry")


def _entry_stream(boot) -> bool:
    """True when the band's driver declares entry-shaped, hashed records (log-json and
    the semantic entry driver). Capability-based: adding a new entry-stream driver
    requires no hardcoded name changes here or in the cube."""
    enc = boot.get("encoding", "")
    if enc == "log-json":
        return True
    return bool(getattr(get_driver(enc), "entry_stream", False))


def pressure(cube, band: str) -> float:
    """Allocated fraction of the band's reserved span: (active + freed-but-held) / span.
    A freed layer still occupies its slot until reused, so it counts toward pressure of the
    RANGE; the free pool is what relieves it."""
    boot = cube.bands[band]
    used = len(set(cube.band_layers[band]))           # active physical layers
    return used / float(boot["span"])


def classify_pressure(p: float) -> str:
    if p >= EMERGENCY_THRESHOLD:
        return "emergency"
    if p >= OVERFLOW_THRESHOLD:
        return "overflow"
    return "normal"


def compact(cube, band: str) -> Dict[str, Any]:
    """Drop tombstoned/quarantined entries; reclaim any non-tail layer that becomes empty
    into the free pool. Only entry-addressed bands are reclaimable (safe-reuse rule)."""
    boot = cube.bands[band]
    if not _entry_stream(boot):
        return {"band": band, "reclaimed": 0, "dropped": 0,
                "note": "spatial/exec/keyvalue layers are not reclaimed"}
    reclaimed = dropped = 0
    keep: List[int] = []
    for idx in list(cube.band_layers[band]):
        entries = cube.layer_content(idx)
        live = [e for e in entries if not e.get("tombstone") and not e.get("quarantined")]
        dropped += len(entries) - len(live)
        cube.set_layer_content(idx, live)
        is_last_remaining = (len(cube.band_layers[band]) - reclaimed) <= 1
        if not live and not is_last_remaining:
            cube.release_layer(band, idx)
            reclaimed += 1
        else:
            keep.append(idx)
    cube.band_layers[band] = keep or [cube.band_layers[band][0]]
    cube.indexes.invalidate(band)
    return {"band": band, "reclaimed": reclaimed, "dropped": dropped,
            "active": len(cube.band_layers[band]), "free": len(cube.band_free[band])}


def dedupe(cube, band: str) -> Dict[str, Any]:
    """Tombstone every live entry whose (opcode, content) repeats an earlier live entry in
    the same band. The duplicate is tombstoned -- append-only history is preserved; the
    visible stream becomes coherent. Returns a report with the duplicate ids."""
    boot = cube.bands[band]
    if not _entry_stream(boot):
        return {"band": band, "duplicates": 0,
                "note": "only entry-stream bands deduplicate"}
    seen = set()
    duplicates = []
    for idx in cube.band_layers[band]:
        for e in cube.layer_content(idx):
            if e.get("tombstone") or e.get("quarantined"):
                continue
            key = (e.get("opcode"), content_hash(e.get("content")))
            sem = e.get("semantic")
            if isinstance(sem, dict):
                # semantic records: evidence and force are part of what a duplicate
                # IS -- a MEASURED fact and an INFERRED reflection with the same
                # content are NOT duplicates. Never drop distinct evidence/force.
                key = key + (sem.get("evidence"), sem.get("force"))
            if key in seen:
                e["tombstone"] = True
                duplicates.append(e.get("id"))
            else:
                seen.add(key)
    if duplicates:
        cube.indexes.invalidate(band)
    return {"band": band, "duplicates": len(duplicates), "ids": duplicates}


def reclaim(cube, band: str, aggressive: bool = False) -> Dict[str, Any]:
    """The standard pressure response: dedupe (when aggressive) then compact. Pure Body
    reflex -- deterministic, no judgment, no rebirth."""
    report: Dict[str, Any] = {"band": band, "pressure_before": pressure(cube, band)}
    if aggressive:
        report["dedupe"] = dedupe(cube, band)
    report["compact"] = compact(cube, band)
    report["pressure_after"] = pressure(cube, band)
    return report


def coherence(cube, band: str) -> List[str]:
    """Structural coherence problems for one band (beyond entry hashes, which verify()
    recomputes): duplicate entry ids in the visible stream; active/free overlap."""
    problems: List[str] = []
    boot = cube.bands[band]
    if set(cube.band_layers.get(band, [])) & set(cube.band_free.get(band, [])):
        problems.append("band %s has a layer both active and free" % band)
    if _entry_stream(boot):
        seen = set()
        for idx in cube.band_layers.get(band, []):
            for e in cube.layer_content(idx):
                eid = e.get("id")
                if eid is None:
                    continue
                if eid in seen:
                    problems.append("band %s has duplicate entry id %s" % (band, eid))
                seen.add(eid)
    return problems
