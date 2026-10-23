from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mantleos.assimilate import assimilate_source
from mantleos.construction import ConstructionError, approve_foreign_execution


def _source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    (root / "host.py").write_text(
        "def main():\n"
        "    while True:\n"
        "        break\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname='construction-fixture'\nversion='1.0.0'\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "fixture"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return root


def _nest(tmp_path: Path) -> Path:
    destination = tmp_path / "nest"
    assimilate_source(str(_source(tmp_path)), destination=destination)
    return destination


def test_execution_plan_is_shell_free_and_bound_to_map(tmp_path: Path):
    nest = _nest(tmp_path)
    plan = json.loads((nest / "mantle" / "maps" / "EXECUTION_PLAN.json").read_text())
    assert plan["shell"] is False
    assert plan["network"]["default"] == "disabled"
    assert plan["source_commit"] == subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=nest, check=True, capture_output=True, text=True
    ).stdout.strip()
    assert len(plan["plan_sha256"]) == 64


def test_foreign_execution_requires_explicit_approval(tmp_path: Path):
    with pytest.raises(ConstructionError, match="explicit approval"):
        approve_foreign_execution(_nest(tmp_path), approved=False)


def test_changed_plan_is_refused(tmp_path: Path):
    nest = _nest(tmp_path)
    path = nest / "mantle" / "maps" / "EXECUTION_PLAN.json"
    plan = json.loads(path.read_text())
    plan["resources"]["max_command_seconds"] += 1
    path.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(ConstructionError, match="plan changed"):
        approve_foreign_execution(nest, approved=True)


def test_source_revision_drift_is_refused(tmp_path: Path):
    nest = _nest(tmp_path)
    (nest / "drift.txt").write_text("drift", encoding="utf-8")
    subprocess.run(["git", "add", "drift.txt"], cwd=nest, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "drift"],
        cwd=nest,
        check=True,
        capture_output=True,
    )
    with pytest.raises(ConstructionError, match="source revision changed"):
        approve_foreign_execution(nest, approved=True)


def test_approval_receipt_is_private_and_does_not_claim_execution(tmp_path: Path, monkeypatch):
    nest = _nest(tmp_path)
    monkeypatch.setattr("mantleos.construction._sandbox_backend", lambda: None)
    result = approve_foreign_execution(nest, approved=True)
    assert result["status"] == "sandbox-unavailable"
    assert result["executes_foreign_code"] is False
    receipt_path = nest / ".mantle" / "construction" / "foreign-execution-approval.json"
    assert receipt_path.is_file()
    assert ".mantle/" in (nest / ".gitignore").read_text(encoding="utf-8")
