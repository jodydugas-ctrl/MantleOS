"""Measure repeated fresh-incarnation checkpoints without hiding storage cost."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from daemon.git_repo import GitRepo
from daemon.runtime import run_incarnations
from daemon.stack import Stack


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    start = time.perf_counter()
    receipts = run_incarnations(root, args.count)
    elapsed = time.perf_counter() - start
    print(json.dumps({"incarnations": len(receipts), "seconds": elapsed,
                      "head": GitRepo(root).head(), "stack": Stack(root).fingerprint(),
                      "repo_bytes": sum(p.stat().st_size for p in root.rglob("*") if p.is_file())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
