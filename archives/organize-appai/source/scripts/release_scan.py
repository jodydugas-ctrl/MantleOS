"""Refuse credential patterns and local private paths in publishable evidence."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ROOTS = ("organize", "docs", "tests", "artifacts", "README.md")
BINARY = {".png", ".pdf", ".docx", ".jpg", ".jpeg", ".vcw"}
PATTERNS = (
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]{12,}"),
    re.compile(
        r"(?:mantle-" r"workspaces|Claude[\\/]" r"Projects|"
        r"AppData[\\/]Local[\\/]" r"Temp)",
        re.I,
    ),
)


def main() -> int:
    problems = []
    tracked = subprocess.run(
        ["git", "ls-files", "--", *ROOTS], cwd=ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    artifact_paths = (
        list((ROOT / "artifacts").rglob("*"))
        if (ROOT / "artifacts").exists() else []
    )
    for path in [ROOT / item for item in tracked] + artifact_paths:
        if not path.is_file() or path.suffix.lower() in BINARY:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in PATTERNS):
            problems.append(path.relative_to(ROOT).as_posix())
    if problems:
        raise SystemExit("private material found: " + ", ".join(sorted(problems)))
    print("release scan PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
