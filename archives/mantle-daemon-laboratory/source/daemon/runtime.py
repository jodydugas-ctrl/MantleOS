from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .git_repo import GitRepo
from .heart import Heart


def fresh_incarnation(root: Path, mind=None, significant: bool = False) -> dict:
    root = Path(root)
    parent = GitRepo(root).head()
    with tempfile.TemporaryDirectory(prefix="mantle-daemon-runtime-") as temp:
        runtime = Path(temp) / "specimen"
        # Each incarnation is disposable and stays on the same local filesystem as
        # its durable parent.  Share immutable Git objects for this ephemeral clone;
        # new runtime commits are still written to the runtime repository, while the
        # source specimen remains the only durable checkpoint target.
        GitRepo(root)._run("clone", "-q", "--shared", str(root), str(runtime))
        receipt = Heart(runtime, mind=mind).beat(significant=significant)
        if receipt["parent_head"] != parent:
            raise RuntimeError("runtime did not start at durable parent")
        # Only validated durable outputs cross the runtime boundary.  Existing
        # receipts are immutable, so transfer the new receipt rather than recopying
        # the entire growing receipt history on every incarnation.
        shutil.copy2(runtime / "STACK.json", root / "STACK.json")
        target_vcw = root / "vcw"
        if target_vcw.exists():
            shutil.rmtree(target_vcw)
        shutil.copytree(runtime / "vcw", target_vcw)
        target_receipts = root / "receipts"
        target_receipts.mkdir(parents=True, exist_ok=True)
        shutil.copy2(runtime / "receipts" / f"{receipt['beat_id']}.json",
                     target_receipts / f"{receipt['beat_id']}.json")
        paths = ["STACK.json", "vcw", f"receipts/{receipt['beat_id']}.json"]
        GitRepo(root).commit(paths, f"incarnation: {receipt['beat_id']}", expected_parent=parent)
        return receipt


def run_incarnations(root: Path, count: int) -> list[dict]:
    if count < 1:
        raise ValueError("count must be positive")
    return [fresh_incarnation(root) for _ in range(count)]
