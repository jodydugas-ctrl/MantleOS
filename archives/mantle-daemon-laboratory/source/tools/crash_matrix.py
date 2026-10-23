"""Run the deterministic crash points against fresh clones of a specimen."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from daemon.git_repo import GitRepo
from daemon.heart import CrashInjected, Heart
from daemon.stack import Stack


def run(root: Path) -> dict[str, str]:
    root = Path(root)
    source_head = GitRepo(root).head()
    results = {}
    for point in ("before_mutation", "after_mutation", "after_verification", "before_commit", "after_commit"):
        with tempfile.TemporaryDirectory(prefix="mantle-crash-") as temp:
            clone = Path(temp) / "specimen"
            GitRepo(root)._run("clone", "-q", str(root), str(clone))
            try:
                Heart(clone).beat(point)
            except CrashInjected:
                pass
            head = GitRepo(clone).head()
            if point == "after_commit":
                assert head != source_head
            else:
                assert head == source_head
            # The committed checkout is always the source of truth.
            clean = Path(temp) / "clean"
            GitRepo(root)._run("clone", "-q", str(root), str(clean))
            assert Stack(clean).verify() == []
            results[point] = "pass"
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    print(run(Path(parser.parse_args().root).resolve()))
