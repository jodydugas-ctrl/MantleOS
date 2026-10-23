from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ActionsContext:
    """Narrow mapping of GitHub Actions facts to the repository seam."""

    repository: str | None
    commit_sha: str | None
    ref: str | None
    write_enabled: bool
    network_required: bool = False

    @classmethod
    def from_environment(cls, environ=None) -> "ActionsContext":
        env = os.environ if environ is None else environ
        permission = str(env.get("MANTLE_CHECKPOINT_WRITE", "false")).lower()
        return cls(repository=env.get("GITHUB_REPOSITORY"), commit_sha=env.get("GITHUB_SHA"),
                   ref=env.get("GITHUB_REF"), write_enabled=permission in {"1", "true", "yes"})

