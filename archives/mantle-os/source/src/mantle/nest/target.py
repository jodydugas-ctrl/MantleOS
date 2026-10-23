"""Typed NEST target and locator parsing.

A ``NestTarget`` is a typed value, never a raw URL string threaded through the
runtime. The canonical locator grammar is::

    local:<absolute-path>
    github:<owner>/<repository>

For a resolved GitHub target, the NUMERIC repository ID is the primary identity.
``owner/name`` is display and drift-detection data (repositories can be renamed or
transferred); a rename/transfer keeps the same repo ID.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Optional

DEFAULT_API_BASE = "https://api.github.com"
DEFAULT_STATE_BRANCH = "mantle-state"

# GitHub owner slug: alphanumerics, hyphens, dots (runs, not leading/trailing hyphen).
_OWNER_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")
# GitHub repository name: letters, digits, '_', '-', '.'
_REPO_RE = re.compile(r"[A-Za-z0-9_.-]+")
_LOCAL_RE = re.compile(r"^local:(.+)$")
_GITHUB_RE = re.compile(r"^github:([^/]+)/([^/]+)$")

_HEX_40 = re.compile(r"^[0-9a-fA-F]{40}$")


def _normalize_abs(path: str) -> str:
    import os

    p = os.path.abspath(os.path.expanduser(path))
    if os.sep != "/":
        p = p.replace("/", os.sep)
    return p


@dataclass(frozen=True)
class NestTarget:
    kind: str  # "local" | "github"
    # local
    path: str = ""
    # github
    owner: str = ""
    repository: str = ""
    repo_id: int = 0
    api_base: str = DEFAULT_API_BASE
    private: bool = True
    state_branch: str = DEFAULT_STATE_BRANCH
    expected_head: str = ""  # 40-hex expected head SHA of the state branch ("" = unspecified)
    installation_id: str = ""
    credential_provider: str = ""
    # optional host-repository binding (host repo is NOT the nest)
    host_repo_id: int = 0
    host_commit: str = ""

    @property
    def full_name(self) -> str:
        return "%s/%s" % (self.owner, self.repository) if self.kind == "github" else self.path

    @property
    def display(self) -> str:
        if self.kind == "local":
            return "local:%s" % self.path
        return "github:%s/%s" % (self.owner, self.repository)

    def resolved(self) -> bool:
        """A GitHub target is only usable once it carries a numeric repo ID."""
        if self.kind == "local":
            return bool(self.path)
        return bool(self.repo_id)

    def to_dict(self) -> Dict[str, object]:
        return {
            "kind": self.kind,
            "path": self.path,
            "owner": self.owner,
            "repository": self.repository,
            "repo_id": self.repo_id,
            "api_base": self.api_base,
            "private": self.private,
            "state_branch": self.state_branch,
            "expected_head": self.expected_head,
            "installation_id": self.installation_id,
            "credential_provider": self.credential_provider,
            "host_repo_id": self.host_repo_id,
            "host_commit": self.host_commit,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, object]) -> "NestTarget":
        return cls(
            kind=str(d.get("kind", "")),
            path=str(d.get("path", "")),
            owner=str(d.get("owner", "")),
            repository=str(d.get("repository", "")),
            repo_id=int(d.get("repo_id", 0) or 0),
            api_base=str(d.get("api_base", DEFAULT_API_BASE)),
            private=bool(d.get("private", True)),
            state_branch=str(d.get("state_branch", DEFAULT_STATE_BRANCH)),
            expected_head=str(d.get("expected_head", "")),
            installation_id=str(d.get("installation_id", "")),
            credential_provider=str(d.get("credential_provider", "")),
            host_repo_id=int(d.get("host_repo_id", 0) or 0),
            host_commit=str(d.get("host_commit", "")),
        )

    def with_repo_id(self, repo_id: int) -> "NestTarget":
        if self.kind != "github":
            raise ValueError("repo_id applies to github targets only")
        return NestTarget(
            kind=self.kind, path=self.path, owner=self.owner, repository=self.repository,
            repo_id=int(repo_id), api_base=self.api_base, private=self.private,
            state_branch=self.state_branch, expected_head=self.expected_head,
            installation_id=self.installation_id, credential_provider=self.credential_provider,
            host_repo_id=self.host_repo_id, host_commit=self.host_commit,
        )


def parse_location(text: str) -> NestTarget:
    """Parse a ``local:`` or ``github:`` locator into a :class:`NestTarget`.

    Raises ValueError on malformed or un-resolvable-syntactically locations.
    A ``github:`` target is returned UNSOLVED (repo_id may be 0); callers or the
    transport must resolve the numeric ID before use.
    """
    t = text.strip()
    m = _LOCAL_RE.match(t)
    if m:
        return NestTarget(kind="local", path=_normalize_abs(m.group(1)))
    m = _GITHUB_RE.match(t)
    if m:
        owner = m.group(1)
        repo = m.group(2)
        if not _OWNER_RE.fullmatch(owner):
            raise ValueError("invalid GitHub owner slug: %r" % owner)
        if not _REPO_RE.fullmatch(repo):
            raise ValueError("invalid GitHub repository name: %r" % repo)
        if owner in (".", "..") or "/" in owner:
            raise ValueError("owner must be a single slug")
        return NestTarget(kind="github", owner=owner, repository=repo)
    raise ValueError(
        "unknown NEST locator %r (expected 'local:<abs-path>' or 'github:<owner>/<repo>')" % text
    )


def validate_expected_head(sha: str) -> None:
    if sha and not _HEX_40.match(sha):
        raise ValueError("expected_head must be a 40-hex commit SHA, got %r" % sha)


def expected_head_or(target: NestTarget, fallback: str) -> str:
    return target.expected_head or fallback
