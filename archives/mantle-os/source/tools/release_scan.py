"""Scan tracked/release text for credentials and machine-private paths."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BINARY = {".png", ".jpg", ".jpeg", ".pdf", ".docx", ".whl", ".gz", ".zip", ".vcw"}
PATTERNS = (
    ("openrouter_key", re.compile(r"sk-or-v1-[A-Za-z0-9_-]{12,}")),
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._~-]{20,}", re.I)),
    ("private_workspace", re.compile(
        r"(?:mantle-" r"workspaces|Claude[\\/]" r"Projects|"
        r"AppData[\\/]Local[\\/]" r"Temp)", re.I)),
)


def _tracked() -> list[Path]:
    rows = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    return [ROOT / row for row in rows]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include", action="append", default=[])
    args = parser.parse_args(argv)
    paths = _tracked()
    for name in args.include:
        target = (ROOT / name).resolve()
        if target.is_file():
            paths.append(target)
        elif target.is_dir():
            paths.extend(target.rglob("*"))
    problems = []
    for path in paths:
        if not path.is_file() or path.suffix.lower() in BINARY:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PATTERNS:
            if pattern.search(text):
                problems.append("%s:%s" % (path.relative_to(ROOT).as_posix(), label))
    if problems:
        raise SystemExit("release scan refused:\n" + "\n".join(sorted(set(problems))))
    print("release scan PASS (%d files)" % len(set(paths)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
