"""PRIMER loading and birth-lock helpers for MantleOS.

A PRIMER is the mandatory COMMANDMENTS + PERSONA pair.  The lock records the
birth hashes.  Runtime code should call ``load_primer`` before constructing any
model/API encounter frame.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

PRIMER_SCHEMA = "mantle.primer-lock/1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(path: Path) -> bytes:
    data = path.read_bytes()
    if not data:
        raise ValueError(f"PRIMER file is empty: {path}")
    return data


def create_lock(root: str | Path, *, persona="PRIMER/PERSONA.md", commandments="PRIMER/COMMANDMENTS.md") -> dict:
    root = Path(root)
    p = root / persona
    c = root / commandments
    value = {
        "schema": PRIMER_SCHEMA,
        "load_order": [commandments, persona],
        "birth_locked": True,
        "drift_policy": "PRIMER changes require explicit rebirth/new lineage; ordinary memory may not rewrite it.",
        "files": {
            commandments: {"sha256": sha256_bytes(_read(c)), "role": "commandments"},
            persona: {"sha256": sha256_bytes(_read(p)), "role": "persona"},
        },
    }
    (root / "PRIMER" / "PRIMER.lock.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return value


def verify_lock(root: str | Path) -> dict:
    root = Path(root)
    lock_path = root / "PRIMER" / "PRIMER.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema") != PRIMER_SCHEMA or lock.get("birth_locked") is not True:
        raise ValueError("Invalid PRIMER lock")
    order = lock.get("load_order")
    if not isinstance(order, list) or len(order) != 2:
        raise ValueError("PRIMER must load exactly COMMANDMENTS then PERSONA")
    roles = []
    for rel in order:
        spec = lock.get("files", {}).get(rel)
        if not isinstance(spec, dict):
            raise ValueError(f"PRIMER lock missing {rel}")
        path = root / rel
        actual = sha256_bytes(_read(path))
        if actual != spec.get("sha256"):
            raise ValueError(f"PRIMER birth lock mismatch: {rel}")
        roles.append(spec.get("role"))
    if roles != ["commandments", "persona"]:
        raise ValueError("PRIMER load order must be commandments then persona")
    return lock


def load_primer(root: str | Path) -> dict:
    """Verify and return the first context that should enter a model encounter."""
    root = Path(root)
    lock = verify_lock(root)
    parts = []
    for rel in lock["load_order"]:
        role = lock["files"][rel]["role"]
        text = (root / rel).read_text(encoding="utf-8")
        parts.append({"role": role, "path": rel, "sha256": lock["files"][rel]["sha256"], "text": text})
    compiled = "\n\n".join(f"# {p['role'].upper()}\n\n{p['text'].strip()}" for p in parts) + "\n"
    return {
        "schema": "mantle.primer/1",
        "birth_locked": True,
        "load_order": list(lock["load_order"]),
        "parts": parts,
        "compiled": compiled,
        "sha256": sha256_bytes(compiled.encode("utf-8")),
    }
