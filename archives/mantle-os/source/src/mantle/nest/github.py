"""GitHub NEST transport (real implementation).

Uses ONLY the Python standard library (``urllib``), imported lazily so importing
this module never opens a socket (mirrors ``mantle.ghost_http``). It drives
GitHub's git-database REST API to materialize and to publish ONE atomic
multi-file commit whose ref advances only as a non-force fast-forward under an
expected-parent compare-and-swap.

This module is never imported by Phase-1 core. Tests use
:mod:`mantle.nest.fake` instead of the network. The live path requires an
injected credential (GitHub App installation token or a short-lived PAT); it is
exercised only by an explicit, consent-gated smoke test.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

from .target import NestTarget
from .transport import (
    MaterializationReceipt,
    NestConflict,
    PublishReceipt,
    ReconcileReceipt,
    RemoteNestStatus,
)

_STATE_BRANCH_REF = "refs/heads/{branch}"


class GithubAuth:
    """A short-lived bearer credential holder. Never logged, never persisted."""

    def __init__(self, token: str, *, token_type: str = "token"):
        self.token = token
        self.token_type = token_type

    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": "%s %s" % (self.token_type, self.token),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mantle-os-nest",
        }


def _http_json(method: str, url: str, auth: GithubAuth, payload: Optional[object] = None):
    # Lazy stdlib-only HTTP client: importing this module never opens a socket.
    import urllib.request
    import urllib.error

    data = None
    headers = auth.headers()
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        if e.code in (409, 422) and "cannot be fast-forwarded" in body.lower():
            raise NestConflict("state-branch ref update refused (not fast-forward)")
        raise RemoteHttpError("GitHub %s %s -> HTTP %s: %s"
                              % (method, url, e.code, body[:300]))
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


class RemoteHttpError(Exception):
    pass


class GithubNestTransport:
    """GitHub transport bound to an injected, short-lived credential."""

    def __init__(self, auth: GithubAuth):
        self._auth = auth

    # ---- resolution --------------------------------------------------------
    def _base(self, target: NestTarget) -> str:
        return "%s/repos/%s/%s" % (target.api_base, target.owner, target.repository)

    def resolve_target(self, target: NestTarget) -> NestTarget:
        """Resolve/verify the numeric repo ID and private visibility via the API."""
        meta = _http_json("GET", self._base(target), self._auth)
        repo_id = int(meta["id"])
        is_private = bool(meta.get("private"))
        if not is_private:
            raise RemoteHttpError(
                "repository %s/%s is not private; refusing to treat it as a NEST"
                % (target.owner, target.repository)
            )
        if target.repo_id and target.repo_id != repo_id:
            raise RemoteHttpError(
                "resolved repo id %s does not match adopted target id %s"
                % (repo_id, target.repo_id)
            )
        return target.with_repo_id(repo_id)

    # ---- NestTransport -----------------------------------------------------
    def inspect(self, target: NestTarget) -> RemoteNestStatus:
        rt = self.resolve_target(target)
        branch = rt.state_branch
        ref = None
        try:
            ref = _http_json(
                "GET",
                "%s/git/ref/%s" % (self._base(rt), _STATE_BRANCH_REF.format(branch=branch)),
                self._auth,
            )
        except RemoteHttpError:
            ref = None
        head = (ref or {}).get("object", {}).get("sha", "") if ref else ""
        return RemoteNestStatus(
            exists=ref is not None,
            repo_id=rt.repo_id,
            full_name=rt.full_name,
            visibility=rt.private and "private" or "public",
            state_branch=rt.state_branch,
            head_commit=head,
        )

    def materialize(self, target: NestTarget, destination: str) -> MaterializationReceipt:
        rt = self.resolve_target(target)
        head = self._head_sha(rt)
        tree = self._tree_at(rt, head)
        os.makedirs(destination, exist_ok=True)
        entries = tree.get("tree", [])
        manifest_hash = ""
        count = 0
        for entry in entries:
            if entry.get("type") != "blob":
                continue
            path = entry.get("path", "")
            sha = entry["sha"]
            blob = _http_json(
                "GET", "%s/git/blobs/%s" % (self._base(rt), sha), self._auth
            )
            import base64 as _b64

            data = _b64.b64decode(blob["content"])
            full = os.path.join(destination, *path.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(data)
            if path == "mantle-nest/nest.json":
                from .manifest import sha256_bytes

                manifest_hash = sha256_bytes(data)
            count += 1
        return MaterializationReceipt(
            transaction_id="",
            repo_id=rt.repo_id,
            head_commit=head,
            manifest_hash=manifest_hash,
            destination=destination,
            opened_envelope=False,
            file_count=count,
        )

    def publish(
        self, target: NestTarget, source: str, expected_parent: str
    ) -> PublishReceipt:
        rt = self.resolve_target(target)
        head = self._head_sha(rt)
        if head != expected_parent:
            raise NestConflict(
                "state-branch head moved (expected %s, got %s)"
                % (expected_parent[:12], head[:12]),
                expected_parent=expected_parent,
                actual_head=head,
            )
        # Build the ENTIRE tree in ONE request (blobs inline as base64 content) so
        # the number of outbound WIRE writes is constant (3 per checkpoint:
        # tree + commit + ref) regardless of how many files the NEST has. This
        # keeps the publisher inside GitHub's write limits: fewer, larger updates,
        # never N per-file blob calls. All content is prepared locally first.
        tree_sha = self._create_tree_inline(rt, source)
        commit_sha = self._create_commit(rt, tree_sha, head)
        self._update_ref(rt, commit_sha, expected_parent=head)
        from .manifest import file_inventory, sha256_bytes as _s
        inv = file_inventory(source)
        mh = ""
        for i in inv:
            if i["path"] == "mantle-nest/nest.json":
                mh = i["sha256"]
        return PublishReceipt(
            transaction_id="",
            repo_id=rt.repo_id,
            parent_commit=head,
            commit=commit_sha,
            tree_hash=tree_sha,
            manifest_hash=mh,
        )

    def reconcile(self, target: NestTarget, transaction_id: str) -> ReconcileReceipt:
        rt = self.resolve_target(target)
        head = self._head_sha(rt)
        commit = _http_json(
            "GET", "%s/git/commits/%s" % (self._base(rt), head), self._auth
        )
        message = commit.get("message", "")
        request_verified = transaction_id in message
        return ReconcileReceipt(
            transaction_id=transaction_id,
            repo_id=rt.repo_id,
            head_commit=head,
            request_verified=request_verified,
            tree_matches=True,
            completed=request_verified,
        )

    # ---- git-database helpers ---------------------------------------------
    def _head_sha(self, rt: NestTarget) -> str:
        ref = _http_json(
            "GET",
            "%s/git/ref/%s" % (self._base(rt), _STATE_BRANCH_REF.format(branch=rt.state_branch)),
            self._auth,
        )
        return ref["object"]["sha"]

    def _tree_at(self, rt: NestTarget, sha: str):
        return _http_json("GET", "%s/git/trees/%s?recursive=1" % (self._base(rt), sha), self._auth)

    def _create_tree_inline(self, rt: NestTarget, source: str) -> str:
        """Create a tree with ALL blobs inline in ONE request (see publish)."""
        import base64 as _b64

        entries = []
        for dirpath, _dirs, filenames in os.walk(source):
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, source).replace(os.sep, "/")
                with open(full, "rb") as f:
                    content = _b64.b64encode(f.read()).decode("ascii")
                entries.append(
                    {"path": rel, "mode": "100644", "type": "blob", "content": content}
                )
        tree = _http_json(
            "POST",
            "%s/git/trees" % self._base(rt),
            self._auth,
            {"tree": entries},
        )
        return tree["sha"]

    def _create_commit(self, rt: NestTarget, tree_sha: str, parent: str) -> str:
        commit = _http_json(
            "POST",
            "%s/git/commits" % self._base(rt),
            self._auth,
            {
                "message": "mantle-nest checkpoint (CAS fast-forward)",
                "tree": tree_sha,
                "parents": [parent] if parent else [],
            },
        )
        return commit["sha"]

    def _update_ref(self, rt: NestTarget, commit_sha: str, *, expected_parent: str) -> None:
        _http_json(
            "PATCH",
            "%s/git/refs/%s" % (self._base(rt), _STATE_BRANCH_REF.format(branch=rt.state_branch)),
            self._auth,
            {"sha": commit_sha, "force": False},
        )
