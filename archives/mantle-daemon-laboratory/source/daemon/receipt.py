from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def validate_receipt(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"receipt: {exc}"]
    required = {"schema_version", "beat_id", "parent_head", "before_stack", "after_stack",
                "before_layers", "after_layers", "changed_layers", "organs", "mind_invoked", "status"}
    missing = required - set(value)
    if missing:
        problems.append(f"receipt missing: {sorted(missing)}")
    for key in ("before_stack", "after_stack"):
        if key in value and not HEX64.fullmatch(str(value[key])):
            problems.append(f"receipt {key} is not a SHA-256 fingerprint")
    if not isinstance(value.get("changed_layers"), list):
        problems.append("receipt changed_layers must be a list")
    if not isinstance(value.get("mind_invoked"), bool):
        problems.append("receipt mind_invoked must be boolean")
    if value.get("mind_invoked"):
        cognitive = value.get("cognitive")
        if not isinstance(cognitive, dict) or not cognitive.get("provider_id") or not cognitive.get("proposal_hash"):
            problems.append("cognitive receipt is incomplete")
        elif not HEX64.fullmatch(str(cognitive["proposal_hash"])):
            problems.append("cognitive proposal hash is malformed")
        elif hashlib.sha256(json.dumps(cognitive.get("proposal"), sort_keys=True, separators=(",", ":")).encode()).hexdigest() != cognitive["proposal_hash"]:
            problems.append("cognitive proposal hash does not match proposal")
        if isinstance(cognitive, dict) and value.get("proposal_hash") != cognitive.get("proposal_hash"):
            problems.append("receipt proposal hash disagrees with cognitive record")
    elif value.get("cognitive") is not None:
        problems.append("non-cognitive receipt contains cognitive data")
    if not value.get("mind_invoked") and value.get("proposal_hash") is not None:
        problems.append("non-cognitive receipt contains proposal hash")
    for key in ("before_layers", "after_layers"):
        layers = value.get(key)
        if not isinstance(layers, dict):
            problems.append(f"receipt {key} must be an object")
        else:
            for band, layer_hash in layers.items():
                if not HEX64.fullmatch(str(layer_hash)):
                    problems.append(f"receipt {key}.{band} is not a SHA-256 hash")
    if isinstance(value.get("changed_layers"), list) and isinstance(value.get("after_layers"), dict):
        unknown = set(value["changed_layers"]) - set(value["after_layers"])
        if unknown:
            problems.append(f"receipt changed_layers has unknown bands: {sorted(unknown)}")
    if value.get("schema_version") != 1:
        problems.append("receipt schema is unsupported")
    return problems


def verify_receipts(root: Path) -> list[str]:
    problems: list[str] = []
    receipt_dir = Path(root) / "receipts"
    if not receipt_dir.is_dir():
        return ["receipts directory is missing"]
    for path in sorted(receipt_dir.glob("*.json")):
        problems.extend(f"{path.name}: {p}" for p in validate_receipt(path))
    return problems
