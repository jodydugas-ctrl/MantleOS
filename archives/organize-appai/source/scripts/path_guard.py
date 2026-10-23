"""Fail-closed path containment guard for Organize.AppAI operations."""
from __future__ import annotations

import argparse
import os
from pathlib import Path


class ContainmentError(ValueError):
    pass


def require_contained(workspace: str | Path, candidate: str | Path) -> Path:
    root = Path(workspace).expanduser().resolve(strict=True)
    target = Path(candidate).expanduser()
    if not target.is_absolute():
        target = root / target
    resolved = target.resolve(strict=False)
    try:
        common = Path(os.path.commonpath((str(root), str(resolved))))
    except ValueError as exc:
        raise ContainmentError(f"path is on a different volume: {resolved}") from exc
    if common != root:
        raise ContainmentError(f"refusing path outside workspace: {resolved}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    for path in args.paths:
        print(require_contained(args.workspace, path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
