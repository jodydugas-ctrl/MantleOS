"""Read-first, substrate-neutral NEST assimilation for MantleOS 2.

The constructor clones and inventories a host, then writes only Mantle-owned
construction tissue.  It never executes code from the cloned repository and
never performs birth.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .constitution import COMMANDMENTS_VERSION, species_kernel_markdown, species_kernel_sha256
from .construction import create_execution_plan
from .mapping import canonical_file_digest, map_body
from .targets.hermes import HermesInnervationError, innervate, is_hermes

SCHEMA = "mantle.assimilation.v2"
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GITHUB_SSH_REPOSITORY = re.compile(r"^git@github\.com:([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)$")
PRIVATE_NAMES = {".git", ".mantle", "__pycache__", ".pytest_cache", ".venv", "venv"}
GITIGNORE_BLOCK = """# MantleOS private organism state and local communication surfaces.
/.mantle/
/COMMUNICATION.TXT
/Food.txt
"""


class AssimilationError(RuntimeError):
    """A construction or evidence gate could not be satisfied."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    return canonical_file_digest(path)[0]


def normalize_github_source(source: str) -> tuple[str, str]:
    """Return canonical HTTPS URL and repository name for a GitHub source."""
    candidate = source.strip().rstrip("/")
    ssh_match = GITHUB_SSH_REPOSITORY.fullmatch(candidate.removesuffix(".git"))
    if ssh_match:
        raw = ssh_match.group(1)
    else:
        parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
        if (
            parsed.scheme not in {"", "http", "https"}
            or (parsed.hostname or "").lower() != "github.com"
            or parsed.username
            or parsed.password
            or parsed.port
            or parsed.query
            or parsed.fragment
        ):
            raise AssimilationError("The alpha constructor accepts only github.com repositories")
        raw = parsed.path.strip("/")
    raw = raw.removesuffix(".git")
    if not GITHUB_REPOSITORY.fullmatch(raw):
        raise AssimilationError("GitHub source must identify exactly one owner/repository")
    owner, repository = raw.split("/", 1)
    owner = owner.lower()
    repository = repository.lower()
    return f"https://github.com/{owner}/{repository}", repository


def _git(arguments: Iterable[str], *, cwd: Path | None = None) -> str:
    command = ["git", *arguments]
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise AssimilationError("Git is required for GitHub assimilation") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "git operation failed").strip().splitlines()[-1]
        raise AssimilationError(detail) from None
    return completed.stdout.strip()


@dataclass(frozen=True)
class RepositoryCensus:
    file_count: int
    byte_count: int
    source_fingerprint: str
    extensions: dict[str, int]
    sample: list[str]


def _host_files(root: Path) -> Iterable[Path]:
    for current, directories, filenames in os.walk(root):
        directories[:] = sorted(item for item in directories if item not in PRIVATE_NAMES)
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_symlink():
                continue
            yield path


def census_repository(root: Path) -> RepositoryCensus:
    """Fingerprint a host tree without interpreting or executing its contents."""
    root = root.resolve()
    aggregate = hashlib.sha256()
    extensions: dict[str, int] = {}
    byte_count = 0
    sample: list[str] = []
    count = 0
    for path in _host_files(root):
        relative = path.relative_to(root).as_posix()
        digest, size = canonical_file_digest(path)
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        suffix = path.suffix.lower() or "[none]"
        extensions[suffix] = extensions.get(suffix, 0) + 1
        byte_count += size
        count += 1
        if len(sample) < 100:
            sample.append(relative)
    return RepositoryCensus(
        file_count=count,
        byte_count=byte_count,
        source_fingerprint=f"sha256:{aggregate.hexdigest()}",
        extensions=dict(sorted(extensions.items(), key=lambda item: (-item[1], item[0]))),
        sample=sample,
    )


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def _append_gitignore(nest: Path) -> dict[str, str]:
    path = nest / ".gitignore"
    before = sha256_file(path) if path.exists() else hashlib.sha256(b"").hexdigest()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if GITIGNORE_BLOCK not in existing:
        separator = (
            ""
            if not existing or existing.endswith("\n\n")
            else ("\n" if existing.endswith("\n") else "\n\n")
        )
        _atomic_text(path, existing + separator + GITIGNORE_BLOCK)
    return {"path": ".gitignore", "before_sha256": before, "after_sha256": sha256_file(path)}


PUBLIC_README = """# MantleOS 2 tissue

This directory is the public, reproducible tissue added during assimilation.
The surrounding NEST is Layer 0 and remains the Default Body. Native behavior
must remain available when the organism is unborn, in stasis, lacks a MIND, or
cannot load Mantle.

`ASSIMILATION.json` binds the Body Map, direct nerve map, source provenance,
candidate Primer state, and every declared public file. Private identity, VCW,
provider state, and Heart receipts live under ignored `.mantle/` storage.
"""

NERVE_PROXY = '''"""NEST-local direct nerve surface.

This is embedded organism tissue, not a host extension or plugin. The Body
remains native if the organism runtime cannot be loaded.
"""
try:
    from .runtime.mantleos.nerves import (
        after_mind,
        authorize_tool,
        before_mind,
        session_ended,
        session_started,
        tool_completed,
        turn_ended,
    )
except Exception:
    def _noop(*args, **kwargs):
        return {"direct": False, "context": "", "message": kwargs.get("user_message", "")}
    after_mind = authorize_tool = before_mind = session_ended = session_started = _noop
    tool_completed = turn_ended = _noop

__all__ = [
    "after_mind", "authorize_tool", "before_mind", "session_ended", "session_started",
    "tool_completed", "turn_ended",
]
'''


def _runtime_payloads() -> dict[str, str]:
    """Return the versioned constructor runtime as NEST-local organ tissue."""
    package = Path(__file__).resolve().parent
    payloads = {"runtime/__init__.py": '"""NEST-local MantleOS organ runtime."""\n'}
    for source in sorted(package.rglob("*.py")):
        if "__pycache__" in source.parts:
            continue
        relative = source.relative_to(package).as_posix()
        payloads[f"runtime/mantleos/{relative}"] = source.read_text(encoding="utf-8")
    return payloads


def _compressed_json(value: Any) -> bytes:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    target = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=target, compresslevel=9, mtime=0) as handle:
        handle.write(raw)
    return target.getvalue()


def _body_map_summary(body_map: dict[str, Any]) -> dict[str, Any]:
    omitted = {"file_coverage", "loops", "graphs", "surfaces"}
    summary = {key: value for key, value in body_map.items() if key not in omitted}
    summary["evidence_files"] = {
        "file_coverage": "maps/FILE_COVERAGE.json.gz",
        "arteries": "maps/ARTERY_MAP.json.gz",
        "symbols": "maps/SYMBOL_GRAPH.json.gz",
        "calls": "maps/CALL_GRAPH.json.gz",
        "events": "maps/EVENT_GRAPH.json.gz",
        "seams": "maps/SEAM_MAP.json.gz",
    }
    return summary


def _write_public_delta(
    nest: Path,
    manifest: dict[str, Any],
    evidence_body_map: dict[str, Any],
) -> list[str]:
    public = nest / "mantle"
    payloads = {
        "__init__.py": (
            '"""Self-contained MantleOS 2 NEST controls."""\n'
            "from .runtime.mantleos.runtime import VCW, Book, MantleBody, MantleError\n"
            "\n"
            '__all__ = ["Book", "MantleBody", "MantleError", "VCW"]\n'
        ),
        "__main__.py": "from .runtime.mantleos.cli import main\n\nraise SystemExit(main())\n",
        "README.md": PUBLIC_README,
        "nerves.py": NERVE_PROXY,
        "primer/COMMANDMENTS.md": species_kernel_markdown(),
        "maps/BODY_MAP.json": json.dumps(manifest["body_map"], indent=2, ensure_ascii=False) + "\n",
        "maps/NERVE_MAP.json": json.dumps(manifest["nerve_map"], indent=2, ensure_ascii=False) + "\n",
    }
    payloads.update(_runtime_payloads())
    body_map = evidence_body_map
    payloads.update(
        {
            "maps/FILE_COVERAGE.json.gz": _compressed_json(body_map["file_coverage"]),
            "maps/ARTERY_MAP.json.gz": _compressed_json(body_map["loops"]),
            "maps/SYMBOL_GRAPH.json.gz": _compressed_json(body_map["graphs"]["symbols"]),
            "maps/CALL_GRAPH.json.gz": _compressed_json(body_map["graphs"]["calls"]),
            "maps/EVENT_GRAPH.json.gz": _compressed_json(body_map["graphs"]["events"]),
            "maps/COVERAGE.json": json.dumps(
                body_map["coverage"], indent=2, ensure_ascii=False
            )
            + "\n",
            "maps/CAPABILITY_MAP.json": json.dumps(
                body_map["capabilities"], indent=2, ensure_ascii=False
            )
            + "\n",
            "maps/SEAM_MAP.json.gz": _compressed_json(body_map["surfaces"]),
            "maps/BEHAVIOR_BASELINE.json": json.dumps(
                body_map["behavior_baseline"], indent=2, ensure_ascii=False
            )
            + "\n",
            "maps/EXECUTION_PLAN.json": json.dumps(
                manifest["execution_plan"], indent=2, ensure_ascii=False
            )
            + "\n",
        }
    )
    written: list[str] = []
    for relative, value in payloads.items():
        target = public / relative
        if target.exists():
            raise AssimilationError(f"Refusing to overwrite existing candidate tissue: {target}")
        if isinstance(value, bytes):
            _atomic_bytes(target, value)
        else:
            _atomic_text(target, value)
        written.append(target.relative_to(nest).as_posix())
    _atomic_text(public / "ASSIMILATION.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    written.append("mantle/ASSIMILATION.json")
    return sorted(written)


def construct_nest(
    nest: Path,
    *,
    source_url: str,
    command: str,
    identity_suggestion: str = "The Compiler",
    purpose: str = "Create an AppAI while preserving native Body behavior",
) -> dict[str, Any]:
    """Construct an un-born Mantle delta in an already-cloned Git NEST."""
    nest = nest.resolve()
    if not (nest / ".git").is_dir():
        raise AssimilationError("The NEST must be a Git checkout")
    if (nest / "mantle").exists() or (nest / ".mantle").exists():
        raise AssimilationError("The NEST already contains Mantle construction tissue")

    commit = _git(["rev-parse", "HEAD"], cwd=nest)
    tree = _git(["rev-parse", "HEAD^{tree}"], cwd=nest)
    branch = _git(["branch", "--show-current"], cwd=nest) or None
    before = census_repository(nest)
    body_map = map_body(
        nest,
        source_uri=source_url,
        source_fingerprint=before.source_fingerprint,
    )
    license_path = next(
        (
            path
            for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
            if (path := nest / name).is_file()
        ),
        None,
    )
    host_edge = _append_gitignore(nest)
    try:
        nerve_map = innervate(nest) if is_hermes(nest) else []
    except HermesInnervationError as exc:
        raise AssimilationError(str(exc)) from exc
    target_kind = "reference-candidate" if nerve_map else "generic"
    coverage_tier = body_map["coverage"]["tier"]
    innervation_gate = (
        "staged-requires-coverage-reconciliation"
        if nerve_map
        else (
            "awaiting-nerve-synthesis"
            if coverage_tier == "mapping-complete"
            else "blocked-by-mapping-coverage"
        )
    )
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "constructed-not-born",
        "constructed_at": utc_now(),
        "source": {
            "canonical_url": source_url,
            "branch": branch,
            "commit": commit,
            "tree": tree,
            "license": {
                "path": license_path.name if license_path else None,
                "sha256": sha256_file(license_path) if license_path else None,
                "evidence": "observed" if license_path else "unknown",
            },
            "census": asdict(before),
        },
        "default_body": {
            "logical_layer": 0,
            "name": "Default Body",
            "substrate": "native-nest",
            "self_boundary": "The NEST is Layer 0 substrate and remains OTHER; it is not SELF.",
            "compatibility_rule": "The host must retain ordinary behavior without the AppAI MIND.",
        },
        "identity_suggestion": identity_suggestion,
        "declared_purpose": purpose,
        "body_map": _body_map_summary(body_map),
        "nerve_map": nerve_map,
        "target": {
            "kind": target_kind,
            "mapping": coverage_tier,
            "traditional_plugin": False,
        },
        "primer_candidate": {
            "status": "awaiting-developmental-mind",
            "commandments": "primer/COMMANDMENTS.md",
            "commandments_version": COMMANDMENTS_VERSION,
            "commandments_sha256": species_kernel_sha256(),
            "personality": "private construction candidate; never part of the public delta",
            "developmental_mind": "external construction process; not the organism MIND",
            "provenance": ["Body Map", "declared purpose", "user-approved construction evidence"],
        },
        "host_edges": [host_edge],
        "activation": {
            "automatic": False,
            "birth_requires_separate_approval": True,
            "direct_nerves": bool(nerve_map),
            "traditional_plugin": False,
        },
        "gates": {
            "source_identified": "verified",
            "read_only_census": "verified",
            "innervation": innervation_gate,
            "host_behavior": "awaiting-explicit-sandbox-tests",
            "primer": "awaiting-developmental-mind",
            "public_delta": "verified-at-construction",
            "birth": "not-authorized",
        },
    }
    manifest["execution_plan"] = create_execution_plan(manifest)
    delta_paths = _write_public_delta(nest, manifest, body_map)
    manifest["delta"] = {
        "paths": delta_paths,
        "sha256": {
            path: sha256_file(nest / path)
            for path in delta_paths
            if path != "mantle/ASSIMILATION.json"
        },
    }
    _atomic_text(
        nest / "mantle" / "ASSIMILATION.json",
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    )
    manifest_sha256 = sha256_file(nest / "mantle" / "ASSIMILATION.json")

    prebirth = {
        "schema": "mantle.prebirth.v2",
        "status": "constructed-not-born",
        "command": command,
        "source": manifest["source"],
        "public_delta": "mantle/",
        "public_manifest_sha256": manifest_sha256,
        "default_body": "Layer 0 / NEST",
        "identity_suggestion": identity_suggestion,
        "approvals": {"assimilation_construction": True, "foreign_code_execution": False, "birth": False},
        "gates": {
            "source_identified": "verified",
            "read_only_census": "verified",
            "host_behavior": "requires-runtime-verification",
            "innervation": innervation_gate,
            "primer": "awaiting-developmental-mind",
            "public_delta": "verified-at-construction",
            "birth": "not-authorized",
        },
        "execution_plan": {
            "path": "mantle/maps/EXECUTION_PLAN.json",
            "sha256": manifest["execution_plan"]["plan_sha256"],
        },
        "constraints": [
            "Host-native behavior remains available without a MIND.",
            "No live VCW, identity key, or communication file exists before birth.",
            "Direct nerves are inserted at mapped host seams; no traditional plugin is used.",
        ],
    }
    _atomic_text(
        nest / ".mantle" / "prebirth.json",
        json.dumps(prebirth, indent=2, ensure_ascii=False) + "\n",
    )
    return manifest


def assimilate_source(
    source: str,
    *,
    destination: str | Path | None = None,
    ref: str | None = None,
    purpose: str = "Create an AppAI while preserving native Body behavior",
    canonical_source: str | None = None,
) -> dict[str, Any]:
    local_source = Path(source).resolve()
    if local_source.is_dir():
        if not (local_source / ".git").exists():
            raise AssimilationError("A local Body source must be a Git checkout")
        clone_source = str(local_source)
        repository = local_source.name
        canonical_url = (
            normalize_github_source(canonical_source)[0]
            if canonical_source
            else local_source.as_uri()
        )
    else:
        canonical_url, repository = normalize_github_source(source)
        clone_source = canonical_url
    target = Path(destination or repository).resolve()
    if target.exists() and any(target.iterdir()):
        raise AssimilationError(f"Destination is not empty: {target}")
    if target.exists() and not target.is_dir():
        raise AssimilationError(f"Destination is not a directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="mantle-git-hooks-") as hook_dir:
        clone = [
            "-c",
            f"core.hooksPath={hook_dir}",
            "-c",
            "core.autocrlf=false",
            "-c",
            "filter.lfs.smudge=",
            "-c",
            "filter.lfs.required=false",
            "clone",
            "--no-recurse-submodules",
        ]
        clone.extend([clone_source, str(target)])
        _git(clone)
    if ref:
        _git(["fetch", "--depth", "1", "origin", ref], cwd=target)
        _git(["checkout", "--detach", "FETCH_HEAD"], cwd=target)

    command = f"mantle assimilate {source}"
    if ref:
        command += f" --ref {ref}"
    if destination:
        command += f" --destination {destination}"
    return construct_nest(target, source_url=canonical_url, command=command, purpose=purpose)


def assimilate_github(
    source: str,
    *,
    destination: str | Path | None = None,
    ref: str | None = None,
    purpose: str = "Create an AppAI while preserving native Body behavior",
) -> dict[str, Any]:
    """Compatibility entry point restricted to GitHub sources."""
    normalize_github_source(source)
    return assimilate_source(source, destination=destination, ref=ref, purpose=purpose)
