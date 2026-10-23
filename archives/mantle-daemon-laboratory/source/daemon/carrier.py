from __future__ import annotations

import json
from pathlib import Path

from .stack import Stack
from .constitution import text_hash


def inspect_carrier(root: Path) -> dict:
    """Return inert, read-only carrier facts; never return secrets or executable tissue."""
    root = Path(root)
    identity = json.loads((root / "genome/identity.json").read_text(encoding="utf-8"))
    mission = json.loads((root / "genome/mission.json").read_text(encoding="utf-8"))
    authority = json.loads((root / "genome/authority.json").read_text(encoding="utf-8"))
    special = json.loads((root / "genome/special.json").read_text(encoding="utf-8"))
    mind = json.loads((root / "genome/mind.json").read_text(encoding="utf-8"))
    primer = root / identity["primer_path"]
    return {"inert": True, "stable_id": identity["stable_id"], "mission_id": mission["mission_id"],
            "requested_capabilities": sorted(authority.get("capabilities", {})),
            "authority_default": authority.get("default"), "primer_sha256": text_hash(primer),
            "vcw_format": special.get("vcw_format"),
            "stack_fingerprint": Stack(root).fingerprint(), "mind_enabled": mind.get("enabled", False),
            "execution": "not-permitted"}


def evaluate_arrival(request: dict, grants: dict) -> dict:
    required = {"stable_id", "mission_id", "requested_capabilities", "evidence", "boundaries"}
    missing = required - set(request)
    if missing:
        raise ValueError(f"arrival request missing: {sorted(missing)}")
    granted = sorted(set(request["requested_capabilities"]) & {k for k, v in grants.items() if v == "granted"})
    return {"stable_id": request["stable_id"], "mission_id": request["mission_id"],
            "granted_capabilities": granted, "persist": "write_specimen" in granted,
            "execution": False, "authority_default": "NO"}
