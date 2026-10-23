#!/usr/bin/env python3
"""
mantle.core.status  --  stable organism status adapter (Mantle OS)

Generated certifiers, lifecycle runners, terminals, and CLI commands should not
reach into changing Body/Cube convenience APIs. This module is the small public
surface for status receipts: generation comes from the Prime cube, integrity from
Prime.verify(), and visible/private counts come through Cube.read().
"""
from __future__ import annotations

from typing import Any, Dict, List


def _count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return 1


def organism_status(org: Any) -> Dict[str, Any]:
    """Return an authoritative, JSON-ready status receipt for a loaded organism.

    The adapter intentionally uses the current public VCW API only:
    `org.prime.generation`, `org.prime.bands`, `org.prime.read()`, and
    `org.prime.verify()`. If a band read fails, the failure is reported on that
    band and mirrored in the top-level verification errors instead of crashing a
    long lifecycle audit at the final status step.
    """
    bands: List[Dict[str, Any]] = []
    read_errors: List[str] = []
    for name in sorted(org.prime.bands):
        boot = org.prime.bands[name]
        visible_count = revealed_count = 0
        error = None
        try:
            visible_count = _count(org.prime.read(name))
            revealed_count = _count(org.prime.read(name, reveal_private=True))
        except Exception as exc:  # noqa: BLE001 -- status must report broken bands
            error = "%s: %s" % (type(exc).__name__, exc)
            read_errors.append("band %s read failed: %s" % (name, error))
        bands.append({
            "band": name,
            "head": int(boot.get("head", 0)),
            "span": int(boot.get("span", 1)),
            "encoding": boot.get("encoding"),
            "private": bool(boot.get("private")),
            "layers": len(org.prime.band_layers.get(name, [])),
            "free_layers": len(org.prime.band_free.get(name, [])),
            "visible_entries": visible_count,
            "revealed_entries": revealed_count,
            "read_error": error,
        })

    verify_errors = list(org.prime.verify()) + read_errors
    return {
        "identity": org.body.identity_name(),
        "generation": org.prime.generation,
        "band_count": len(org.prime.bands),
        "bands": bands,
        "verify_ok": verify_errors == [],
        "verify_errors": verify_errors,
        "stage1_certified_runtime": bool(getattr(org, "stage1_certified", False)),
    }
