"""Filesystem boundary for resident Body state."""

from __future__ import annotations

from pathlib import Path
import os
import re

from .config import ResidentConfig


_PROFILE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class StorageBoundaryError(ValueError):
    """A requested resident path is invalid or escapes the configured root."""


class ResidentStorage:
    def __init__(
        self,
        config: ResidentConfig,
        *,
        hermes_home: str | Path | None = None,
    ) -> None:
        if config.storage_root is not None:
            root = Path(config.storage_root)
        else:
            active_home = hermes_home or os.getenv("HERMES_HOME")
            home = Path(active_home) if active_home else Path.home() / ".hermes"
            root = home / "mantle"
        self.root = root.expanduser().resolve()

    def organism_path(self, profile_id: str) -> Path:
        if not isinstance(profile_id, str) or not _PROFILE_ID.fullmatch(profile_id):
            raise StorageBoundaryError(
                "profile_id must match [A-Za-z0-9][A-Za-z0-9_.-]{0,127}"
            )
        if profile_id in {".", ".."}:
            raise StorageBoundaryError("profile_id cannot be a traversal segment")
        organisms = self.root / "organisms"
        candidate = organisms / profile_id
        if candidate.is_symlink():
            raise StorageBoundaryError("resident profile path cannot be a symbolic link")
        return candidate
