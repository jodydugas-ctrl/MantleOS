from __future__ import annotations

import hashlib
import json
from pathlib import Path


def text_hash(path: Path) -> str:
    """Hash constitutional text canonically across Git checkout line endings."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_json(root: Path, relative: str) -> dict:
    path = Path(root) / relative
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{relative} must be an object")
    return value


def validate(root: Path) -> list[str]:
    problems: list[str] = []
    required = {"schema_version", "name", "stable_id", "birth_time", "lifecycle_class", "primer_path", "self_components"}
    try:
        identity = load_json(root, "genome/identity.json")
        missing = required - set(identity)
        if missing:
            problems.append(f"identity missing: {sorted(missing)}")
        if not isinstance(identity.get("stable_id"), str) or not identity.get("stable_id"):
            problems.append("identity stable_id must be non-empty")
        if identity.get("primer_path") != "genome/primer.md":
            problems.append("identity primer path is not constitutional")
        primer_path = Path(root) / identity.get("primer_path", "")
        if primer_path.is_file() and text_hash(primer_path) != identity.get("primer_sha256"):
            problems.append("primer hash mismatch: constitutional tissue was modified")
        if identity.get("self_components") != ["PRIMER", "IMMUNE", "SPECIAL"]:
            problems.append("SELF must bootstrap as PRIMER + IMMUNE + SPECIAL")
    except Exception as exc:
        problems.append(f"identity: {exc}")
    for rel in ("genome/mission.json", "genome/authority.json", "genome/developmental.json", "genome/immune.json", "genome/special.json", "genome/mind.json"):
        try:
            value = load_json(root, rel)
            if value.get("schema_version") != 1:
                problems.append(f"{rel}: unsupported schema")
        except Exception as exc:
            problems.append(f"{rel}: {exc}")
    try:
        special = load_json(root, "genome/special.json")
        if special.get("self_component") != "SPECIAL" or special.get("vcw_format") != "vcw-cube-png-v2":
            problems.append("special: invalid VCW boot declaration")
        if special.get("dimensions") != [800, 800]:
            problems.append("special: wrong VCW dimensions")
        for band, spec in special.get("bands", {}).items():
            if not isinstance(spec, dict) or not isinstance(spec.get("layer"), int) or not spec.get("path"):
                problems.append(f"special: malformed band {band}")
    except Exception:
        pass
    primer = Path(root) / "genome/primer.md"
    if not primer.is_file() or not primer.read_text(encoding="utf-8").strip():
        problems.append("primer missing or empty")
    return problems
