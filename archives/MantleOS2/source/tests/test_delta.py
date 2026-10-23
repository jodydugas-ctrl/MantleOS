from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mantleos.delta import DeltaError, apply_seed, build_seed, reverse_seed, verify_seed


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_delta_seed_round_trip_is_exact_and_refuses_unapproved_reverse(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init")
    git(source, "config", "user.email", "test@example.invalid")
    git(source, "config", "user.name", "Mantle test")
    (source / ".gitignore").write_text("\n", encoding="utf-8", newline="\n")
    (source / "body.py").write_text("print('native')\n", encoding="utf-8", newline="\n")
    git(source, "add", ".gitignore", "body.py")
    git(source, "commit", "-m", "native body")
    commit = git(source, "rev-parse", "HEAD")

    clean = tmp_path / "clean"
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", "clone", str(source), str(clean)],
        check=True,
        capture_output=True,
    )

    (source / ".gitignore").write_text(
        "/.mantle/\n/COMMUNICATION.TXT\n/Food.txt\n", encoding="utf-8", newline="\n"
    )
    (source / "body.py").write_text(
        "print('native')\nobserve('semantic event')\n", encoding="utf-8", newline="\n"
    )
    mantle = source / "mantle"
    mantle.mkdir()
    (mantle / "ASSIMILATION.json").write_text(
        json.dumps(
            {
                "schema": "mantle.assimilation.v2",
                "status": "constructed-not-born",
                "source": {"commit": commit, "tree": "test"},
                "target": {"traditional_plugin": False},
            }
        ),
        encoding="utf-8",
    )
    (mantle / "nerves.py").write_text("# direct nerve\n", encoding="utf-8")

    seed = tmp_path / "seed"
    assert build_seed(source, seed)["ok"]
    assert apply_seed(seed, clean)["ok"]
    assert verify_seed(seed, clean)["ok"]
    with pytest.raises(DeltaError, match="approve-reverse"):
        reverse_seed(seed, clean, approved=False)
    assert reverse_seed(seed, clean, approved=True)["ok"]
    assert not (clean / "mantle").exists()
    assert git(clean, "status", "--porcelain") == ""
