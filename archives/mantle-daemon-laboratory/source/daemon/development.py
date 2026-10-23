from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


MIN_PYTHON = (3, 9)
RUNTIME_CONTRACT = "python >=3.9"


def file_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_candidate(root: Path, relative: str, expected_hash: str) -> bool:
    path = Path(root) / relative
    return path.is_file() and file_hash(path) == expected_hash


def validate_registry(root: Path) -> list[str]:
    root = Path(root)
    path = root / "genome/organ_registry.json"
    if not path.is_file():
        return ["organ registry is missing"]
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"organ registry: {exc}"]
    problems: list[str] = []
    if registry.get("schema_version") != 1:
        problems.append("organ registry schema is unsupported")
    if registry.get("runtime") != RUNTIME_CONTRACT:
        problems.append("organ registry runtime is incompatible")
    if sys.version_info[:2] < MIN_PYTHON:
        problems.append("running Python version is below the supported minimum")
    for name, record in registry.get("organs", {}).items():
        if not isinstance(record, dict) or not verify_candidate(root, record.get("path", ""), record.get("sha256", "")):
            problems.append(f"{name}: candidate hash or path mismatch")
        if not record.get("tests"):
            problems.append(f"{name}: proving tests are missing")
    return problems
