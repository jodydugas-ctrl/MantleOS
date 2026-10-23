"""Explicit, inert Mantle 2 migration and rebind operations."""
from __future__ import annotations

from datetime import datetime, timezone
import copy
import hashlib
import json
import os
import shutil
import tempfile
from typing import Any, Dict

from .core.persist import atomic_write_json


RESIDENT_PROTOCOL = "mantle-resident-v2"


def _new_target(source: str, out: str) -> tuple[str, str]:
    source = os.path.realpath(os.path.abspath(source))
    out = os.path.realpath(os.path.abspath(out))
    if source == out:
        raise ValueError("migration output must differ from its source")
    if os.path.lexists(out):
        raise FileExistsError("migration output already exists; prior artifacts are preserved")
    parent = os.path.dirname(out)
    if not os.path.isdir(parent):
        raise ValueError("migration output parent does not exist")
    return source, out


def _sha256(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _migration_phase(staging: str, kind: str, source: str, out: str,
                     phase: str, result: str = "INTERRUPTED") -> None:
    """Persist a non-activating migration journal before each material stage."""
    atomic_write_json(os.path.join(staging, "migration_journal.json"), {
        "schema": "mantle-migration-journal-v1",
        "kind": kind,
        "source_sha256": _tree_fingerprint(source),
        "target_hash": hashlib.sha256(out.encode("utf-8")).hexdigest(),
        "target_hint": os.path.basename(out),
        "phase": phase,
        "result": result,
        "activated": False,
    })


def migrate_germ(source: str, out: str) -> Dict[str, Any]:
    source, out = _new_target(source, out)
    with open(source, "r", encoding="utf-8") as handle:
        germ = json.load(handle)
    if not isinstance(germ, dict):
        raise ValueError("germ must be a JSON object")
    migrated = copy.deepcopy(germ)
    migrated.pop("germ_format", None)
    migrated.pop("format", None)
    migrated["schema"] = "mantle-germ-v2"
    migrated["migration"] = {
        "source_sha256": _sha256(source),
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "inert": True,
        "activated": False,
    }
    atomic_write_json(out, migrated)
    return {"result": "PASS", "kind": "germ", "out": out, "activated": False}


def migrate_spore(source: str, out: str) -> Dict[str, Any]:
    source, out = _new_target(source, out)
    from . import spore
    info = spore.read_spore(source)
    state = copy.deepcopy(info["state"])
    germ = state.get("germ")
    if isinstance(germ, dict):
        germ.pop("germ_format", None)
        germ.pop("format", None)
        germ["schema"] = "mantle-germ-v2"
        spore.validate_embedded_material(germ)
    state.setdefault("migration", {})["mantle2"] = {
        "source_sha256": _sha256(source), "inert": True, "activated": False,
    }
    spore.render_spore(state, out, status=info["status"])
    return {"result": "PASS", "kind": "spore", "out": out, "activated": False}


def migrate_resident(source: str, out: str) -> Dict[str, Any]:
    source, out = _new_target(source, out)
    if not os.path.isfile(os.path.join(source, "organism.json")):
        raise ValueError("source is not a persisted Mantle resident")
    staging = tempfile.mkdtemp(prefix=".mantle-migrate-resident-", dir=os.path.dirname(out))
    try:
        _migration_phase(staging, "resident", source, out, "staging_created")
        shutil.copytree(source, staging, dirs_exist_ok=True)
        _migration_phase(staging, "resident", source, out, "source_copied")
        atomic_write_json(os.path.join(staging, "resident_protocol.json"), {
            "schema": "mantle-resident-protocol-declaration-v1",
            "protocol": RESIDENT_PROTOCOL,
            "migrated_from_sha256": _tree_fingerprint(source),
            "historical_source_preserved": True,
        })
        _migration_phase(staging, "resident", source, out, "promotion_ready")
        os.replace(staging, out)
        _migration_phase(out, "resident", source, out, "promoted", "PASS")
    except Exception:
        # Preserve the interrupted stage for inspection; do not damage source/out.
        raise
    return {"result": "PASS", "kind": "resident", "out": out,
            "protocol": RESIDENT_PROTOCOL, "source_preserved": True,
            "activated": False}


def rebind(host: str, out: str, *, certify: bool = False) -> Dict[str, Any]:
    """Clone a resident binding into a new preserved target and optionally certify."""
    host = os.path.realpath(os.path.abspath(host))
    source = os.path.join(host, ".mantle") if os.path.isdir(os.path.join(host, ".mantle")) else host
    result = migrate_resident(source, out)
    result["kind"] = "rebind"
    result["host"] = os.path.basename(host)
    if certify:
        from .certify import certify_nest, write_certificate
        receipt = certify_nest(out)
        certificate = write_certificate(receipt, os.path.join(out, "certification.json"))
        result["certification"] = certificate
    return result


def _tree_fingerprint(root: str) -> str:
    digest = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(base, name)
            digest.update(os.path.relpath(path, root).replace("\\", "/").encode("utf-8"))
            with open(path, "rb") as handle:
                digest.update(hashlib.sha256(handle.read()).digest())
    return digest.hexdigest()


__all__ = ["migrate_germ", "migrate_resident", "migrate_spore", "rebind"]
