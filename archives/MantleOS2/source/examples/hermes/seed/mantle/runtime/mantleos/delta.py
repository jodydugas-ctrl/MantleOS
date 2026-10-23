"""Build, apply, verify, and reverse public Mantle delta seeds."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class DeltaError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(value: bytes) -> str:
    """Hash Git text as LF-normalized content while leaving binary data exact."""
    if b"\0" not in value:
        value = value.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(path: Path) -> str:
    return _canonical_digest(path.read_bytes())


def _git(root: Path, *arguments: str, binary: bool = False) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=not binary,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None) or getattr(exc, "stdout", None) or str(exc)
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        raise DeltaError(str(detail).strip()) from None
    return result.stdout


def _manifest(root: Path) -> dict[str, Any]:
    path = root / "mantle" / "ASSIMILATION.json"
    if not path.is_file():
        raise DeltaError(f"Missing assimilation manifest: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeltaError("Assimilation manifest is unreadable") from exc
    if value.get("schema") != "mantle.assimilation.v2":
        raise DeltaError("Assimilation manifest has an unsupported schema")
    return value


def _files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    )


def build_seed(nest: str | Path, destination: str | Path) -> dict[str, Any]:
    nest = Path(nest).resolve()
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise DeltaError(f"Seed destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(nest)
    patch = _git(
        nest,
        "diff",
        "--binary",
        "--full-index",
        "--",
        ":(exclude)mantle/**",
        binary=True,
    )
    if not isinstance(patch, bytes) or not patch:
        raise DeltaError("The host-edge patch is empty")
    (destination / "host-edge.patch").write_bytes(patch)
    shutil.copytree(nest / "mantle", destination / "mantle")
    changed_paths = [
        line.strip()
        for line in str(_git(nest, "diff", "--name-only", "--", ":(exclude)mantle/**")).splitlines()
        if line.strip()
    ]
    host_edges = []
    for relative in changed_paths:
        pristine = _git(nest, "show", f"HEAD:{relative}", binary=True)
        if not isinstance(pristine, bytes):
            raise DeltaError(f"Could not read upstream edge bytes: {relative}")
        host_edges.append(
            {
                "path": relative,
                "before_sha256": _canonical_digest(pristine),
                "after_sha256": _canonical_sha256(nest / relative),
                "hash_mode": "lf-normalized-text-or-exact-binary",
            }
        )
    lock = {
        "schema": "mantle.delta-seed.v2",
        "source": manifest["source"],
        "target": manifest.get("target"),
        "host_edge_sha256": hashlib.sha256(patch).hexdigest(),
        "host_edges": host_edges,
        "private_state_included": False,
        "apply": "mantle delta apply <seed> --destination <clean-nest>",
        "verify": "mantle delta verify <seed> --destination <candidate-nest>",
        "reverse": "mantle delta reverse <seed> --destination <candidate-nest> --approve-reverse",
    }
    (destination / "SEED.json").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    checksums = [
        f"{_sha256(path)}  {path.relative_to(destination).as_posix()}"
        for path in _files(destination)
    ]
    (destination / "SHA256SUMS").write_text(
        "\n".join(checksums) + "\n", encoding="utf-8", newline="\n"
    )
    return {"ok": True, "destination": str(destination), "files": len(checksums) + 1}


def _load_seed(seed: Path) -> dict[str, Any]:
    try:
        value = json.loads((seed / "SEED.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeltaError("Seed metadata is unreadable") from exc
    if value.get("schema") != "mantle.delta-seed.v2":
        raise DeltaError("Seed metadata has an unsupported schema")
    return value


def verify_seed(seed: str | Path, destination: str | Path) -> dict[str, Any]:
    seed = Path(seed).resolve()
    destination = Path(destination).resolve()
    metadata = _load_seed(seed)
    commit = str(_git(destination, "rev-parse", "HEAD")).strip()
    if commit != metadata["source"]["commit"]:
        raise DeltaError("NEST does not match the seed's pinned upstream commit")
    if hashlib.sha256((seed / "host-edge.patch").read_bytes()).hexdigest() != metadata[
        "host_edge_sha256"
    ]:
        raise DeltaError("Host-edge patch checksum failed")
    for line in (seed / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = seed / relative
        if not path.is_file() or _sha256(path) != expected:
            raise DeltaError(f"Seed checksum failed: {relative}")
    seed_manifest = (seed / "mantle" / "ASSIMILATION.json").read_bytes()
    applied_manifest = destination / "mantle" / "ASSIMILATION.json"
    if not applied_manifest.is_file() or applied_manifest.read_bytes() != seed_manifest:
        raise DeltaError("Applied Mantle tissue does not match the seed")
    final_by_path = {
        edge["path"]: edge["after_sha256"] for edge in metadata.get("host_edges", [])
    }
    changed = {
        line[3:].replace("\\", "/")
        for line in str(_git(destination, "status", "--short")).splitlines()
    }
    expected_changed = {*final_by_path, "mantle/"}
    if changed != expected_changed:
        raise DeltaError("Applied changed-path set does not match the seed")
    for relative, expected in final_by_path.items():
        path = destination / relative
        if not path.is_file() or _canonical_sha256(path) != expected:
            raise DeltaError(f"Applied host tissue hash failed: {relative}")
    return {"ok": True, "commit": commit, "private_state_included": False}


def apply_seed(seed: str | Path, destination: str | Path) -> dict[str, Any]:
    seed = Path(seed).resolve()
    destination = Path(destination).resolve()
    metadata = _load_seed(seed)
    if (destination / "mantle").exists() or (destination / ".mantle").exists():
        raise DeltaError("Destination already contains Mantle tissue")
    if str(_git(destination, "rev-parse", "HEAD")).strip() != metadata["source"]["commit"]:
        raise DeltaError("Destination is not the seed's pinned upstream commit")
    if str(_git(destination, "status", "--porcelain")).strip():
        raise DeltaError("Destination must be a clean checkout")
    baseline_by_path = {
        edge["path"]: edge["before_sha256"] for edge in metadata.get("host_edges", [])
    }
    for relative, expected in baseline_by_path.items():
        path = destination / relative
        # Re-materialize only declared edge files from their exact Git blobs.
        # This removes checkout-level CRLF conversion without touching the rest
        # of the Body and makes the reviewed patch byte-reproducible.
        pristine = _git(destination, "show", f"HEAD:{relative}", binary=True)
        if not isinstance(pristine, bytes):
            raise DeltaError(f"Could not materialize clean source bytes: {relative}")
        path.write_bytes(pristine)
        if not path.is_file() or _canonical_sha256(path) != expected:
            raise DeltaError(
                f"Clean source bytes do not match the seed: {relative}; "
                "the pinned Git object may not match"
            )
    patch = seed / "host-edge.patch"
    _git(destination, "-c", "core.autocrlf=false", "apply", "--check", str(patch))
    _git(destination, "-c", "core.autocrlf=false", "apply", str(patch))
    try:
        shutil.copytree(seed / "mantle", destination / "mantle")
    except Exception:
        _git(destination, "-c", "core.autocrlf=false", "apply", "-R", str(patch))
        raise
    return verify_seed(seed, destination)


def reverse_seed(seed: str | Path, destination: str | Path, *, approved: bool) -> dict[str, Any]:
    if not approved:
        raise DeltaError("Reversing a delta requires --approve-reverse")
    seed = Path(seed).resolve()
    destination = Path(destination).resolve()
    verify_seed(seed, destination)
    if (destination / ".mantle").exists() or (destination / "COMMUNICATION.TXT").exists():
        raise DeltaError("Refusing to reverse a delta that has organism state")
    patch = seed / "host-edge.patch"
    _git(destination, "-c", "core.autocrlf=false", "apply", "-R", "--check", str(patch))
    _git(destination, "-c", "core.autocrlf=false", "apply", "-R", str(patch))
    edge_paths = [edge["path"] for edge in _load_seed(seed).get("host_edges", [])]
    if edge_paths:
        # Restore the checkout's configured representation (for example CRLF)
        # after proving and reversing the exact canonical patch.
        _git(destination, "checkout-index", "--force", "--", *edge_paths)
        _git(destination, "add", "--", *edge_paths)
    public = (destination / "mantle").resolve()
    public.relative_to(destination)
    shutil.rmtree(public)
    return {"ok": True, "commit": str(_git(destination, "rev-parse", "HEAD")).strip()}
