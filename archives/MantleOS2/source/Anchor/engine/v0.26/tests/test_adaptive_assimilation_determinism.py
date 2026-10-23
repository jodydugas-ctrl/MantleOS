from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from scan.adaptive_cli import _post_scan_assimilation
from scan.assimilation import prepare_assimilation_workbench


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def _closures(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    (output / "surface_closure.json").write_text(json.dumps({
        "state": "PARTIAL", "surface_count": 2, "bound_count": 1,
        "partial_count": 0, "unresolved_count": 1, "closure_ratio": 0.5, "records": [],
    }), encoding="utf-8")
    (output / "effect_closure.json").write_text(json.dumps({
        "state": "PARTIAL", "surface_count": 2, "closed_count": 0,
        "partial_count": 1, "unresolved_count": 1, "closure_ratio": 0.0, "records": [],
    }), encoding="utf-8")


def test_workbench_bytes_are_deterministic(tmp_path: Path):
    output = tmp_path / "scan"
    root = tmp_path / "specimen"
    root.mkdir()
    (root / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
    _closures(output)
    kwargs = dict(
        output=output,
        specimen={"specimen_id": "fixture", "fingerprint": {"value": "frozen-tree"}},
        files=[{"path": "main.rs", "language": "Rust", "is_binary": 0}],
        nodes=[], findings=[], evidence=[], adapter_runs={"generic_text": 1}, content_root=root,
    )

    first = prepare_assimilation_workbench(**kwargs)
    first_hashes = _hash_tree(output / "assimilation")
    second = prepare_assimilation_workbench(**kwargs)
    second_hashes = _hash_tree(output / "assimilation")

    assert first == second
    assert first_hashes == second_hashes


def test_post_scan_wrapper_creates_secondary_status_only(tmp_path: Path, monkeypatch):
    output = tmp_path / "scan"
    root = tmp_path / "specimen"
    root.mkdir()
    (root / "app.py").write_text("value = 1\n", encoding="utf-8")
    _closures(output)
    body = {
        "specimen": {"specimen_id": "fixture", "fingerprint": {"value": "frozen-tree"}},
        "files": [{"path": "app.py", "language": "Python", "is_binary": 0}],
        "nodes": [], "findings": [], "evidence": [],
        "extraction": {"adapter_runs": {"generic_text": 1}},
    }
    original = json.dumps(body, indent=2)
    (output / "machine_body_map.json").write_text(original, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    status = _post_scan_assimilation(["scan", str(root), "--out", str(output)])

    assert status and status["required"] is True
    assert (output / "assimilation_status.json").exists()
    assert (output / "machine_body_map.json").read_text(encoding="utf-8") == original
