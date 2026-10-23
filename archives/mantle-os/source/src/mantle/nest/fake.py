"""Deterministic in-memory fake GitHub NEST transport for hermetic tests.

Implements the git data model behind the REST surface the real transport uses:
an object store with repository identity and a branch ref that advances ONLY as
a non-force fast-forward under an expected-parent compare-and-swap.

No invariant or unit test may need the network; this fake is the seam that makes
that true. It can also be rigged (visibility flips, wrong repo IDs, racing
writers, tampered manifests) to exercise the red cases.
"""
from __future__ import annotations

import copy
import hashlib
import os
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .manifest import canonical_json, read_json, sha256_bytes
from .target import NestTarget
from .transport import (
    MaterializationReceipt,
    NestConflict,
    PublishReceipt,
    ReconcileReceipt,
    RemoteNestStatus,
)


@dataclass
class _Repo:
    repo_id: int
    full_name: str
    visibility: str = "private"
    state_branch: str = "mantle-state"
    head: str = ""  # commit sha
    # commit_sha -> {"tree": sha, "parent": sha, "tx": str, "manifest_hash": str}
    commits: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # path -> bytes for the tree at head
    files: Dict[str, bytes] = field(default_factory=dict)
    enable_cas: bool = True


class FakeGithubTransport:
    """A real-behaviour fake: git object repo + CAS fast-forward ref update."""

    def __init__(self) -> None:
        self._repos: Dict[int, _Repo] = {}
        self._next_commit = 0
        # rigging switches (red-case drivers)
        self.force_visibility: Optional[str] = None
        self.tamper_manifest: Optional[bool] = None
        self.partial_upload = False  # if true, publish writes half the files then it would fail
        self.cancel_after_save = False
        # GitHub-footprint instrumentation: remote WRITE operations and
        # per-file writes. A compliant publisher must use a CONSTANT number of
        # write ops per checkpoint no matter how many files (fewer, larger
        # updates) -- never N individual file writes.
        self.write_ops = 0
        self.per_file_writes = 0

    # ---- repo discovery / rigging ------------------------------------------
    def resolve_target(self, target: NestTarget) -> NestTarget:
        repo = self._repo_for(target)
        return target.with_repo_id(repo.repo_id)

    def _repo_for(self, target: NestTarget) -> _Repo:
        if target.kind != "github":
            raise ValueError("fake transport supports github targets only")
        if target.repo_id:
            # An EXPLICIT numeric id is primary identity: resolve ONLY by id.
            # A name alone may resolve only when the id is unspecified (0).
            repo = self._repos.get(target.repo_id)
            if repo is None:
                raise KeyError("unknown repository id %s" % target.repo_id)
            if repo.full_name != target.full_name:
                raise ValueError(
                    "repository id %s resolves to %r, not %r"
                    % (target.repo_id, repo.full_name, target.full_name)
                )
            return repo
        for r in self._repos.values():
            if r.full_name == target.full_name:
                return r
        raise KeyError("unknown repository %s" % target.full_name)

    def seed_repo(
        self, *, repo_id: int, full_name: str, visibility: str = "private",
        state_branch: str = "mantle-state", head: str = "", files: Optional[Dict[str, bytes]] = None,
    ) -> None:
        self._repos[repo_id] = _Repo(
            repo_id=repo_id, full_name=full_name, visibility=visibility,
            state_branch=state_branch, head=head, files=dict(files or {}),
        )

    def set_head(self, repo_id: int, files: Dict[str, bytes]) -> str:
        repo = self._repos[repo_id]
        sha = self._commit(repo, files, parent=repo.head, tx="seed")
        repo.head = sha
        repo.files = dict(files)
        return sha

    def _commit(self, repo: _Repo, files: Dict[str, bytes], parent: str, tx: str) -> str:
        self._next_commit += 1
        tree_obj = {"files": {k: sha256_bytes(v) for k, v in files.items()}}
        tree = sha256_bytes(canonical_json(tree_obj))
        manifest_hash = sha256_bytes(canonical_json({"tx": tx, "parent": parent, "tree": tree}))
        sha = sha256_bytes(
            canonical_json({"n": self._next_commit, "tree": tree, "parent": parent, "tx": tx})
        )
        repo.commits[sha] = {"tree": tree, "parent": parent, "tx": tx, "manifest_hash": manifest_hash}
        return sha

    # ---- NestTransport -----------------------------------------------------
    def inspect(self, target: NestTarget) -> RemoteNestStatus:
        repo = self._repo_for(target)
        vis = self.force_visibility if self.force_visibility else repo.visibility
        manifests = [p for p in repo.files if p.endswith("/nest.json")]
        return RemoteNestStatus(
            exists=True,
            repo_id=repo.repo_id,
            full_name=repo.full_name,
            visibility=vis,
            state_branch=repo.state_branch,
            head_commit=repo.head,
            manifest_present=bool(manifests),
            manifest_hash=sha256_bytes(repo.files.get(manifests[0], b"")) if manifests else "",
        )

    def _checked_out_files(self, target: NestTarget) -> Dict[str, bytes]:
        return dict(self._repo_for(target).files)

    def materialize(self, target: NestTarget, destination: str) -> MaterializationReceipt:
        repo = self._repo_for(target)
        os.makedirs(destination, exist_ok=True)
        files = dict(repo.files)
        manifest = files.get("mantle-nest/nest.json", b"{}")
        for rel, data in files.items():
            full = os.path.join(destination, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(data)
        return MaterializationReceipt(
            transaction_id=repo.commits.get(repo.head, {}).get("tx", ""),
            repo_id=repo.repo_id,
            head_commit=repo.head,
            manifest_hash=sha256_bytes(manifest),
            destination=destination,
            opened_envelope=False,
            file_count=len(files),
        )

    def publish(
        self, target: NestTarget, source: str, expected_parent: str
    ) -> PublishReceipt:
        repo = self._repo_for(target)
        # compare-and-swap: branch head must equal the remembered expected parent
        if repo.enable_cas and repo.head and expected_parent and repo.head != expected_parent:
            raise NestConflict(
                "state-branch head moved (expected %s, got %s)"
                % (expected_parent[:12], repo.head[:12]),
                expected_parent=expected_parent,
                actual_head=repo.head,
            )
        files: Dict[str, bytes] = {}
        for dirpath, _dirs, filenames in os.walk(source):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, source).replace(os.sep, "/")
                with open(full, "rb") as f:
                    files[rel] = f.read()
        if self.partial_upload:
            # simulate an interrupted upload: only half the tree lands
            keys = sorted(files)
            files = {k: files[k] for k in keys[: max(1, len(keys) // 2)]}
        tx = "tx-%s" % hashlib.sha1(repr(sorted(files)).encode("utf-8")).hexdigest()[:16]
        tree_obj = {"files": {k: sha256_bytes(v) for k, v in files.items()}}
        tree = sha256_bytes(canonical_json(tree_obj))
        parent = repo.head if repo.head else ""
        commit_sha = self._commit(repo, files, parent=parent, tx=tx)
        # advance ref non-force fast-forward (ONE atomic remote write op)
        repo.head = commit_sha
        repo.files = files
        self.write_ops += 1  # one O(1) remote write, regardless of file count
        manifest_hash = sha256_bytes(files.get("mantle-nest/nest.json", b""))
        return PublishReceipt(
            transaction_id=tx,
            repo_id=repo.repo_id,
            parent_commit=parent,
            commit=commit_sha,
            tree_hash=tree,
            manifest_hash=manifest_hash,
        )

    def reconcile(self, target: NestTarget, transaction_id: str) -> ReconcileReceipt:
        repo = self._repo_for(target)
        head_commit = repo.head
        info = repo.commits.get(head_commit, {})
        request_verified = bool(info) and info.get("tx") == transaction_id
        # tree match requires files present for the recorded inventory
        tree_matches = bool(info)
        return ReconcileReceipt(
            transaction_id=transaction_id,
            repo_id=repo.repo_id,
            head_commit=head_commit,
            request_verified=request_verified,
            tree_matches=tree_matches,
            completed=request_verified and tree_matches,
        )
