from __future__ import annotations

from pathlib import Path


def scan(root: Path, secret_values=()) -> list[str]:
    """Find supplied secret values in durable text/binary artifacts."""
    root = Path(root)
    needles = [str(value).encode() for value in secret_values if value]
    if not needles:
        return []
    problems: list[str] = []
    excluded = {".git", "__pycache__"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if any(needle in data for needle in needles):
            problems.append(str(path.relative_to(root)))
    return problems

