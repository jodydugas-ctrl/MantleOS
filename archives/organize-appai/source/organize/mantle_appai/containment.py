"""Fail-closed path containment used by assist, demos, and guarded tests."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path


class ContainmentError(ValueError):
    """A requested path cannot be proven to remain under the approved root."""


def require_contained(root: str | Path, candidate: str | Path) -> Path:
    approved = Path(root).expanduser().resolve(strict=True)
    target = Path(candidate).expanduser()
    if not target.is_absolute():
        target = approved / target
    # Resolve only the parent (a real directory) and then append the leaf name,
    # which is a pure string operation. This never raises NotADirectoryError for a
    # symlink escape with a non-existent trailing component (which Path.resolve /
    # realpath of the full path can do on some platforms) and still resolves the
    # parent through the symlink so a link pointing outside the approved root is
    # detected as a refusal.
    parent_resolved = Path(os.path.realpath(os.fspath(target.parent)))
    resolved = parent_resolved / target.name
    try:
        common = Path(os.path.commonpath((str(approved), str(resolved))))
    except ValueError as exc:
        raise ContainmentError(f"path is on a different volume: {resolved}") from exc
    if common != approved:
        raise ContainmentError(
            f"refusing path outside approved root: {resolved} (root: {approved})"
        )
    return resolved


def require_all_contained(
    root: str | Path, candidates: Iterable[str | Path]
) -> list[Path]:
    return [require_contained(root, candidate) for candidate in candidates]
