"""Run the local evidence suite, including isolated endurance measurement."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from daemon.constitution import validate
from daemon.git_repo import GitRepo
from daemon.receipt import verify_receipts
from daemon.runtime import run_incarnations
from daemon.stack import Stack
from crash_matrix import run as run_crash_matrix


def main() -> int:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--endurance", type=int, default=100)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    started = time.perf_counter()
    local_problems = Stack(root).verify() + validate(root) + verify_receipts(root)
    if local_problems:
        print(json.dumps({"status": "failed", "problems": local_problems}, indent=2))
        return 1
    test = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=root, text=True, capture_output=True)
    if test.returncode:
        print(test.stdout + test.stderr)
        return test.returncode
    for _ in range(3):
        result = run_crash_matrix(root)
        if set(result.values()) != {"pass"}:
            raise AssertionError(result)
    source_head = GitRepo(root).head()
    with tempfile.TemporaryDirectory(prefix="mantle-endurance-") as temp:
        clone = Path(temp) / "specimen"
        GitRepo(root)._run("clone", "-q", str(root), str(clone))
        endurance_start = time.perf_counter()
        receipts = run_incarnations(clone, args.endurance)
        endurance_seconds = time.perf_counter() - endurance_start
        problems = Stack(clone).verify() + validate(clone) + verify_receipts(clone)
        if problems or len(receipts) != args.endurance:
            raise AssertionError({"problems": problems, "receipts": len(receipts)})
        summary = {"status": "pass", "source_head": source_head, "endurance": args.endurance,
                   "endurance_seconds": endurance_seconds, "events": len(Stack(clone).read("events")),
                   "stack_fingerprint": Stack(clone).fingerprint(),
                   "repo_bytes": sum(p.stat().st_size for p in clone.rglob("*") if p.is_file()),
                   "elapsed_seconds": time.perf_counter() - started}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

