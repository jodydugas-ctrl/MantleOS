"""Canonical remote NEST manifest and content hashing.

The remote form is a versioned root manifest plus a SELF-sealed transport seal
that binds the manifest to a specific repository ID, state branch, expected
parent revision, full file inventory, Prime generation/fingerprint, and
transaction ID -- never to a mutable repository NAME.

Canonical JSON: sorted keys, UTF-8, compact separators, bounded fields, and no
non-finite values. All content digests use the ``sha256:<hex>`` form.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

SCHEMA = "mantle-github-nest-v1"

_HEX_40 = "0123456789abcdef" * 40  # note: not used; kept for clarity


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def canonical_json(obj: object) -> bytes:
    """Serialize to canonical JSON bytes (sorted keys, compact, UTF-8)."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_json_str(obj: object) -> str:
    return canonical_json(obj).decode("utf-8")


class NonFiniteError(ValueError):
    pass


def _assert_no_nan(obj: object) -> None:
    import math

    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise NonFiniteError("non-finite float in canonical manifest")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_nan(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _assert_no_nan(v)


def file_inventory(root: str, base: str = "") -> List[Dict[str, object]]:
    """Compute a canonical, ordered inventory of the files under ``root``.

    Paths are POSIX-relative to ``base`` (default: the ``mantle-nest`` remote
    root is produced by callers passing base="mantle-nest"). Returns a list of
    ``{"path", "bytes", "sha256"}`` sorted by path.
    """
    items: List[Dict[str, object]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            rel = rel.replace(os.sep, "/")
            if base:
                rel = base.rstrip("/") + "/" + rel
            with open(full, "rb") as f:
                raw = f.read()
            items.append(
                {"path": rel, "bytes": len(raw), "sha256": sha256_bytes(raw)}
            )
    items.sort(key=lambda i: i["path"])
    return items


def build_nest_manifest(
    *,
    repo_id: int,
    full_name: str,
    visibility: str,
    state_branch: str,
    parent_commit: str,
    transaction_id: str,
    key_fingerprint: str,
    prime_generation: int,
    prime_fingerprint: str,
    files: Iterable[Dict[str, object]],
    schema: str = SCHEMA,
) -> Dict[str, object]:
    manifest = {
        "schema": schema,
        "authority": {
            "github_is_self": False,
            "technical_evidence_only": True,
        },
        "repository": {
            "id": int(repo_id),
            "full_name": str(full_name),
            "visibility": str(visibility),
            "state_branch": str(state_branch),
        },
        "revision": {
            "parent_commit": str(parent_commit),
            "transaction_id": str(transaction_id),
        },
        "organism": {
            "key_fingerprint": str(key_fingerprint),
            "prime_generation": int(prime_generation),
            "prime_fingerprint": str(prime_fingerprint),
        },
        "files": sorted(files, key=lambda i: i["path"]),
    }
    _assert_no_nan(manifest)
    return manifest


def manifest_hash(manifest: Dict[str, object]) -> str:
    return sha256_bytes(canonical_json(manifest))


def build_transport_seal(
    *,
    manifest: Dict[str, object],
    repo_id: int,
    state_branch: str,
    expected_parent: str,
    transaction_id: str,
    prime_generation: int,
    prime_fingerprint: str,
    files_inventory: List[Dict[str, object]],
) -> Dict[str, object]:
    """The Body-auth binding object (sealed separately by the envelope signer)."""
    return {
        "schema": "mantle-github-transport-seal-v1",
        "manifest_hash": manifest_hash(manifest),
        "repository": {"id": int(repo_id), "state_branch": str(state_branch)},
        "revision": {
            "expected_parent": str(expected_parent),
            "transaction_id": str(transaction_id),
        },
        "organism": {
            "prime_generation": int(prime_generation),
            "prime_fingerprint": str(prime_fingerprint),
        },
        "files": sorted(files_inventory, key=lambda i: i["path"]),
    }


def write_json(path: str, obj: object) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(canonical_json(obj))


def read_json(path: str) -> object:
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))
