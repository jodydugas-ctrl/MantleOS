"""Isolated candidate materialization for Body-owned research.

The Candidate Chamber is deliberately narrower than a deployment or adoption path.  It
copies or validates one proposed mutable surface in a disposable workspace and returns
deterministic hashes.  No adapter can write the original source, calcify a skill, adopt a
genome, or make stored applet data executable.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Protocol, Set


class CandidateChamberError(ValueError):
    """A candidate crossed the chamber's surface, authority, or workspace boundary."""


@dataclass(frozen=True)
class BaselineArtifact:
    source: str
    files: Mapping[str, Mapping[str, Any]]
    tree_hash: str


@dataclass(frozen=True)
class CandidateArtifact:
    workspace: Path
    files: Mapping[str, Mapping[str, Any]]
    tree_hash: str
    source_hash: str
    mutable_surface: str
    original_unchanged: bool = True


@dataclass(frozen=True)
class ArtifactRef:
    path: Path
    tree_hash: str
    policy: str


class CandidateAdapter(Protocol):
    def baseline(self, request: Any = None) -> BaselineArtifact: ...
    def materialize(self, proposal: Any, workspace: Path) -> CandidateArtifact: ...
    def verify_original_unchanged(self) -> bool: ...
    def eligible_artifact(self, result: Mapping[str, Any]) -> Optional[ArtifactRef]: ...


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _safe_rel(path: Any) -> str:
    if not isinstance(path, str) or not path:
        raise CandidateChamberError("candidate path must be a non-empty string")
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or normalized.startswith("/"):
        raise CandidateChamberError("absolute candidate path refused: %r" % path)
    if len(normalized) >= 2 and normalized[1] == ":":
        raise CandidateChamberError("drive-qualified candidate path refused: %r" % path)
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise CandidateChamberError("path traversal or empty component refused: %r" % path)
    return "/".join(parts)


def _snapshot(root: Path, *, skip_git: bool = True) -> Dict[str, Dict[str, Any]]:
    root = root.resolve()
    if not root.is_dir():
        raise CandidateChamberError("candidate source is not a directory: %s" % root)
    result: Dict[str, Dict[str, Any]] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        kept_dirs = []
        for dirname in sorted(dirnames):
            full = current / dirname
            if skip_git and dirname == ".git" and current == root:
                continue
            if full.is_symlink():
                raise CandidateChamberError("symlink in candidate source refused: %s" %
                                             full.relative_to(root))
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            full = current / filename
            rel = full.relative_to(root).as_posix()
            if full.is_symlink():
                raise CandidateChamberError("symlink in candidate source refused: %s" % rel)
            if not full.is_file():
                raise CandidateChamberError("non-file candidate entry refused: %s" % rel)
            data = full.read_bytes()
            result[rel] = {
                "sha256": _sha256(data), "size": len(data),
                "mode": full.stat().st_mode & 0o777,
            }
    return result


def _tree_hash(files: Mapping[str, Mapping[str, Any]]) -> str:
    rows = [{"path": path, **dict(files[path])} for path in sorted(files)]
    return _sha256(_canonical(rows))


def _new_workspace(workspace: Optional[Path], *, forbidden: Iterable[Path] = ()) -> Path:
    if workspace is None:
        return Path(tempfile.mkdtemp(prefix="mantle-research-candidate-"))
    path = Path(workspace).absolute()
    forbidden_real = [Path(item).resolve() for item in forbidden]
    path_real = path.resolve()
    for source in forbidden_real:
        if path_real == source or source in path_real.parents:
            raise CandidateChamberError("candidate workspace overlaps original source")
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise CandidateChamberError("candidate workspace must be new or empty")
    else:
        path.mkdir(parents=True)
    return path


def _copy_source(source: Path, destination: Path) -> None:
    source = source.resolve()
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        current = Path(dirpath)
        relative = current.relative_to(source)
        target = destination / relative
        target.mkdir(parents=True, exist_ok=True)
        for dirname in list(dirnames):
            if dirname == ".git" and current == source:
                dirnames.remove(dirname)
                continue
            if (current / dirname).is_symlink():
                raise CandidateChamberError("symlink in candidate source refused")
        for filename in filenames:
            origin = current / filename
            if origin.is_symlink():
                raise CandidateChamberError("symlink in candidate source refused")
            shutil.copy2(origin, target / filename)


def _write_json(workspace: Path, name: str, payload: Mapping[str, Any]) -> None:
    path = workspace / _safe_rel(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(payload) + b"\n")


class _EligibilityMixin:
    def eligible_artifact(self, result: Mapping[str, Any]) -> Optional[ArtifactRef]:
        if not isinstance(result, Mapping) or str(result.get("status", "")).upper() != "ELIGIBLE":
            return None
        if result.get("artifact_policy") != "preserve":
            return None
        artifact = result.get("candidate_artifact")
        if not isinstance(artifact, CandidateArtifact):
            return None
        return ArtifactRef(artifact.workspace, artifact.tree_hash, "preserve")


class CandidateChamber:
    """Route one adapter through an isolated workspace and original-integrity proof."""

    def __init__(self, adapter: CandidateAdapter):
        self.adapter = adapter

    def baseline(self, request: Any = None) -> BaselineArtifact:
        return self.adapter.baseline(request)

    def materialize(self, proposal: Any, workspace: Optional[Path] = None) -> CandidateArtifact:
        original = getattr(self.adapter, "_source_root", None)
        forbidden = [original] if original is not None else []
        target = _new_workspace(workspace, forbidden=forbidden)
        try:
            artifact = self.adapter.materialize(proposal, target)
            if not self.adapter.verify_original_unchanged():
                raise CandidateChamberError("original source changed during materialization")
            return artifact
        except Exception:
            if workspace is None:
                shutil.rmtree(target, ignore_errors=True)
            raise

    def verify_original_unchanged(self) -> bool:
        return self.adapter.verify_original_unchanged()

    @staticmethod
    def discard(artifact: CandidateArtifact) -> None:
        """Discard exactly one chamber artifact; no candidate is made active."""
        path = artifact.workspace.resolve()
        if "mantle-research-candidate-" not in path.name and not path.name.startswith("candidate"):
            raise CandidateChamberError("refusing to discard an unrecognized workspace")
        if path.exists():
            shutil.rmtree(path)


class SourceWorktreeAdapter(_EligibilityMixin):
    """Copy a source tree into a candidate workspace and apply an allowlisted patch."""

    def __init__(self, source: str | Path, *, allowlist: Iterable[str]):
        self._source_root = Path(source).resolve()
        self.allowlist: Set[str] = {_safe_rel(path) for path in allowlist}
        if not self.allowlist:
            raise CandidateChamberError("source candidates require a non-empty path allowlist")
        self._original = _snapshot(self._source_root)

    def baseline(self, request: Any = None) -> BaselineArtifact:
        current = _snapshot(self._source_root)
        if current != self._original:
            raise CandidateChamberError("source changed after adapter baseline")
        return BaselineArtifact(str(self._source_root), dict(current), _tree_hash(current))

    def _patch(self, proposal: Mapping[str, Any], workspace: Path) -> None:
        if not isinstance(proposal, Mapping):
            raise CandidateChamberError("source proposal must be an object")
        surface = proposal.get("mutable_surface")
        if surface is not None and surface != "source-files":
            raise CandidateChamberError("proposal names a different mutable surface")
        files = proposal.get("files", proposal.get("patch", {}))
        if not isinstance(files, Mapping):
            raise CandidateChamberError("source proposal files must be an object")
        for raw_path, data in files.items():
            path = _safe_rel(raw_path)
            if path not in self.allowlist:
                raise CandidateChamberError("candidate path is outside the allowlist: %s" % path)
            if not isinstance(data, (str, bytes)):
                raise CandidateChamberError("candidate file content must be text or bytes")
            target = workspace / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        deletes = proposal.get("delete", [])
        if not isinstance(deletes, list):
            raise CandidateChamberError("source proposal delete must be a list")
        for raw_path in deletes:
            path = _safe_rel(raw_path)
            if path not in self.allowlist:
                raise CandidateChamberError("candidate deletion is outside the allowlist: %s" % path)
            target = workspace / path
            if target.exists():
                target.unlink()

    def materialize(self, proposal: Any, workspace: Path) -> CandidateArtifact:
        self.baseline()
        _copy_source(self._source_root, workspace)
        self._patch(proposal, workspace)
        files = _snapshot(workspace, skip_git=False)
        return CandidateArtifact(workspace, files, _tree_hash(files), _tree_hash(self._original),
                                 "source-files")

    def verify_original_unchanged(self) -> bool:
        return _snapshot(self._source_root) == self._original


class GraftWorkspaceAdapter(_EligibilityMixin):
    """Run the existing non-destructive graft ceremony inside a chamber workspace."""

    def __init__(self, host: str | Path, graft: Optional[Mapping[str, Any]] = None):
        self._source_root = Path(host).resolve()
        self.graft = dict(graft) if graft is not None else None
        self._original = _snapshot(self._source_root)

    def baseline(self, request: Any = None) -> BaselineArtifact:
        current = _snapshot(self._source_root)
        if current != self._original:
            raise CandidateChamberError("graft host changed after adapter baseline")
        return BaselineArtifact(str(self._source_root), dict(current), _tree_hash(current))

    def materialize(self, proposal: Any, workspace: Path) -> CandidateArtifact:
        self.baseline()
        graft = proposal.get("graft") if isinstance(proposal, Mapping) else None
        graft = graft or self.graft
        if graft is None:
            raise CandidateChamberError("graft materialization requires explicit graft data")
        from ..graft import GraftError, GraftDrift, apply
        try:
            result = apply(graft, str(self._source_root), workspace=str(workspace),
                           allow_drift=False)
        except (GraftError, GraftDrift, OSError) as exc:
            raise CandidateChamberError("graft candidate refused: %s" % exc) from exc
        candidate_root = Path(result["workspace"])
        files = _snapshot(candidate_root, skip_git=False)
        return CandidateArtifact(candidate_root, files, _tree_hash(files), _tree_hash(self._original),
                                 "graft-resident")

    def verify_original_unchanged(self) -> bool:
        return _snapshot(self._source_root) == self._original


class _DescriptorAdapter(_EligibilityMixin):
    mutable_surface = "descriptor"

    def _descriptor_baseline(self) -> BaselineArtifact:
        blob = _canonical(self._descriptor)
        files = {"candidate.json": {"sha256": _sha256(blob), "size": len(blob), "mode": 0o644}}
        return BaselineArtifact("memory", files, _tree_hash(files))

    def baseline(self, request: Any = None) -> BaselineArtifact:
        return self._descriptor_baseline()

    def verify_original_unchanged(self) -> bool:
        return _canonical(self._descriptor) == self._original_blob

    def _materialize_descriptor(self, payload: Mapping[str, Any], workspace: Path) -> CandidateArtifact:
        _write_json(workspace, "candidate.json", payload)
        files = _snapshot(workspace, skip_git=False)
        return CandidateArtifact(workspace, files, _tree_hash(files),
                                 self._descriptor_baseline().tree_hash, self.mutable_surface)


class SkillTrialAdapter(_DescriptorAdapter):
    """Prepare a skill trial descriptor; only the existing trial gate may execute it."""

    def __init__(self, code: str, entry: str, cases: Iterable[Any]):
        if not isinstance(code, str) or not isinstance(entry, str):
            raise CandidateChamberError("skill baseline requires code and entry strings")
        self._descriptor = {"kind": "skill-trial", "code": code, "entry": entry,
                            "cases": list(cases)}
        self._original_blob = _canonical(self._descriptor)

    def materialize(self, proposal: Any, workspace: Path) -> CandidateArtifact:
        payload = dict(self._descriptor)
        if proposal:
            if not isinstance(proposal, Mapping) or set(proposal) - {"code", "entry", "cases"}:
                raise CandidateChamberError("skill proposal may change only code, entry, and cases")
            payload.update(proposal)
        from ..vcw.drivers import validate_skill_code
        try:
            validate_skill_code(payload["code"])
        except Exception as exc:
            raise CandidateChamberError("skill static gate refused candidate: %s" % exc) from exc
        payload.update({"trial_only": True, "calcify": False, "adopt": False})
        return self._materialize_descriptor(payload, workspace)


class GenomeProposalAdapter(_DescriptorAdapter):
    """Validate a genome proposal without applying it to an organism."""

    def __init__(self, specs: Iterable[Mapping[str, Any]]):
        self._descriptor = {"kind": "genome-proposal", "specs": [dict(item) for item in specs]}
        self._original_blob = _canonical(self._descriptor)

    def materialize(self, proposal: Any, workspace: Path) -> CandidateArtifact:
        specs = self._descriptor["specs"]
        if proposal:
            if not isinstance(proposal, Mapping) or set(proposal) != {"specs"}:
                raise CandidateChamberError("genome proposal may change only specs")
            specs = proposal["specs"]
        if not isinstance(specs, list):
            raise CandidateChamberError("genome specs must be a list")
        from ..compiler import GenomeError, validate_genome
        try:
            boots = validate_genome([dict(item) for item in specs])
        except (GenomeError, TypeError, ValueError) as exc:
            raise CandidateChamberError("genome validation refused candidate: %s" % exc) from exc
        payload = {"kind": "genome-proposal", "specs": specs,
                   "validated": boots, "adopt": False, "authority": "BODY-rebirth"}
        return self._materialize_descriptor(payload, workspace)


class AppletBodyAdapter(_EligibilityMixin):
    """Store source as an inert foreign capsule; storage never grants execution authority."""

    def __init__(self, source: str | Path):
        self._source_root = Path(source).resolve()
        self._original = _snapshot(self._source_root)

    def baseline(self, request: Any = None) -> BaselineArtifact:
        current = _snapshot(self._source_root)
        if current != self._original:
            raise CandidateChamberError("applet source changed after adapter baseline")
        return BaselineArtifact(str(self._source_root), dict(current), _tree_hash(current))

    def materialize(self, proposal: Any, workspace: Path) -> CandidateArtifact:
        if proposal not in ({}, None):
            raise CandidateChamberError("applet capsule has no executable proposal surface")
        self.baseline()
        files = []
        for rel in sorted(self._original):
            source = self._source_root / rel
            data = source.read_bytes()
            if len(data) > 1_000_000:
                raise CandidateChamberError("applet capsule file exceeds bounded size: %s" % rel)
            files.append({"path": rel, **self._original[rel],
                          "data_b64": base64.b64encode(data).decode("ascii")})
        payload = {"kind": "APPLET-BODY-CAPSULE", "status": "capsule",
                   "foreign": True, "execution_authority": False,
                   "source_tree_hash": _tree_hash(self._original), "files": files}
        _write_json(workspace, "capsule.json", payload)
        candidate_files = _snapshot(workspace, skip_git=False)
        return CandidateArtifact(workspace, candidate_files, _tree_hash(candidate_files),
                                 _tree_hash(self._original), "inert-applet-capsule")

    def verify_original_unchanged(self) -> bool:
        return _snapshot(self._source_root) == self._original
