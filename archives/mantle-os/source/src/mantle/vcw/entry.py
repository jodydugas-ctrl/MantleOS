#!/usr/bin/env python3
"""
mantle.vcw.entry  --  the one entry hasher + the one entry maker (Mantle OS)

The rule is simple and total: the hash covers EVERY field of an entry EXCEPT the four
volatile ones the Body is allowed to flip after the fact -- `id` (assigned on append),
`tombstone`, `quarantined` (immune flags), and `hash` itself. So `authorship` and any other
content-bearing extra field are hash-protected by construction: "what your organ does, you
have done" is true in code, not just in prose.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict

# Fields the Body may set/flip after an entry is born; everything else is inside the hash.
VOLATILE_FIELDS = ("id", "tombstone", "quarantined", "hash")


def entry_hash(entry: Dict[str, Any]) -> str:
    """SHA-256 (first 16 hex chars) over every non-volatile field. Deterministic across
    processes and save/reload: keys sorted, separators fixed."""
    h = {k: v for k, v in entry.items() if k not in VOLATILE_FIELDS}
    blob = json.dumps(h, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def content_hash(content: Any) -> str:
    """A canonical hash of an entry's CONTENT alone -- the deduplication key used by
    metabolism (two entries with the same opcode + content hash are duplicates)."""
    blob = json.dumps(content, separators=(",", ":"), sort_keys=True,
                      default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def make_entry(content: Any, opcode: str = "WRITE", author: str = "BODY",
               source: str = "", **extra) -> Dict[str, Any]:
    """Create one immutable band entry record. Extra fields (e.g. `authorship`, `verified`,
    `confidence`) are INSIDE the hash."""
    e = {"id": None, "ts": time.time(), "opcode": opcode, "author": author,
         "source": source, "content": content, "tombstone": False, "quarantined": False}
    e.update(extra)
    e["hash"] = entry_hash(e)
    return e


def visible(entries) -> list:
    """The base visibility filter: tombstoned and quarantined entries never surface."""
    return [e for e in entries if not e.get("tombstone") and not e.get("quarantined")]


# ---- graded memory: weight / deweighting / behavioral ghosts (M3) ----------
# A weight is NOT a mutable field on an entry (that would break the immutable hash). It is
# an OVERLAY computed from append-only DEWEIGHT events: each event records {target, weight},
# and the latest event targeting an entry wins. An entry with no event has weight 1.0. An
# entry whose effective weight drops to/under the ghost threshold vanishes from the default
# read stream but stays physically present -- a recoverable "behavioral ghost". Long-term
# depression, not deletion; nothing is ever overwritten.
DEWEIGHT_OPCODE = "DEWEIGHT"
GHOST_THRESHOLD = 0.0       # effective weight <= this is a ghost (hidden from default reads)


def effective_weights(entries) -> dict:
    """id -> effective weight, read from the append-only DEWEIGHT events (last wins)."""
    w: dict = {}
    for e in entries:
        if e.get("opcode") == DEWEIGHT_OPCODE:
            c = e.get("content") or {}
            tid, wt = c.get("target"), c.get("weight")
            if tid is not None and isinstance(wt, (int, float)) and not isinstance(wt, bool):
                w[tid] = float(wt)
    return w


def weight_overlay(entries, ghosts: bool = False) -> list:
    """Apply the graded-memory overlay to a base-visible stream (tombstone/quarantine
    already filtered). DEWEIGHT bookkeeping entries are dropped from the output; remaining
    entries are ordered by DESCENDING effective weight (stable). Default (`ghosts=False`)
    hides suppressed entries (weight <= GHOST_THRESHOLD); `ghosts=True` returns ONLY those
    suppressed ghosts, in stream order. A cube with no deweight activity is unchanged."""
    has_event = any(e.get("opcode") == DEWEIGHT_OPCODE for e in entries)
    if not has_event:
        return [] if ghosts else list(entries)
    wmap = effective_weights(entries)
    live, ghost = [], []
    for e in entries:
        if e.get("opcode") == DEWEIGHT_OPCODE:
            continue                              # bookkeeping never surfaces as content
        ew = wmap.get(e.get("id"), 1.0)
        (ghost if ew <= GHOST_THRESHOLD else live).append((ew, e))
    if ghosts:
        return [e for _w, e in ghost]
    live.sort(key=lambda t: -t[0])               # stable: equal weights keep stream order
    return [e for _w, e in live]
