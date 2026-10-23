from __future__ import annotations

import json
from pathlib import Path

from scan.assimilation import prepare_assimilation_workbench


def _write_closure(output: Path, *, surface_count=0, bound=0, partial=0, unresolved=0,
                   closed=0, effect_partial=0, effect_unresolved=0):
    output.mkdir(parents=True, exist_ok=True)
    (output / "surface_closure.json").write_text(json.dumps({
        "state": "MAPPED" if surface_count and not partial and not unresolved else "UNKNOWN" if not surface_count else "PARTIAL",
        "surface_count": surface_count,
        "bound_count": bound,
        "partial_count": partial,
        "unresolved_count": unresolved,
        "closure_ratio": (bound / surface_count) if surface_count else None,
        "records": [],
    }), encoding="utf-8")
    (output / "effect_closure.json").write_text(json.dumps({
        "state": "MAPPED" if surface_count and not effect_partial and not effect_unresolved else "UNKNOWN" if not surface_count else "PARTIAL",
        "surface_count": surface_count,
        "closed_count": closed,
        "partial_count": effect_partial,
        "unresolved_count": effect_unresolved,
        "closure_ratio": (closed / surface_count) if surface_count else None,
        "records": [],
    }), encoding="utf-8")


def _specimen():
    return {"specimen_id": "fixture", "fingerprint": {"kind": "test", "value": "abc123"}}


def test_unknown_runtime_language_opens_inert_workbench(tmp_path: Path):
    output = tmp_path / "scan"
    root = tmp_path / "specimen"
    root.mkdir()
    (root / "app.py").write_text("print('not executed')\n", encoding="utf-8")
    _write_closure(output)

    status = prepare_assimilation_workbench(
        output=output,
        specimen=_specimen(),
        files=[{"path": "app.py", "language": "Python", "is_binary": 0}],
        nodes=[], findings=[], evidence=[], adapter_runs={"generic_text": 1}, content_root=root,
    )

    assert status["required"] is True
    assert status["unknown_runtime_languages"] == ["Python"]
    request = json.loads((output / "assimilation" / "assimilation_request.json").read_text(encoding="utf-8"))
    assert request["authority"]["generated_candidate_code_auto_executed"] is False
    assert any(r["kind"] == "unsupported_runtime_language" for r in request["reasons"])
    candidate = (output / "assimilation" / "candidate_adapter.py").read_text(encoding="utf-8")
    assert "app.py" not in candidate
    assert "return ExtractionResult()" in candidate
    assert (output / "assimilation" / "LLM_ASSIMILATION_TASK.md").exists()
    assert (output / "assimilation" / "promotion_gate.json").exists()


def test_known_but_incomplete_substrate_opens_refinement_workbench(tmp_path: Path):
    output = tmp_path / "scan"
    root = tmp_path / "specimen"
    root.mkdir()
    (root / "app.tsx").write_text("export const App = () => null\n", encoding="utf-8")
    _write_closure(output, surface_count=10, bound=8, partial=1, unresolved=1,
                   closed=4, effect_partial=4, effect_unresolved=2)

    status = prepare_assimilation_workbench(
        output=output,
        specimen=_specimen(),
        files=[{"path": "app.tsx", "language": "TypeScript", "is_binary": 0}],
        nodes=[], findings=[], evidence=[], adapter_runs={"typescript-electron": 1}, content_root=root,
    )

    assert status["required"] is True
    assert status["unknown_runtime_languages"] == []
    request = json.loads((output / "assimilation" / "assimilation_request.json").read_text(encoding="utf-8"))
    kinds = {r["kind"] for r in request["reasons"]}
    assert {"human_surface_closure", "effect_closure"} <= kinds


def test_known_complete_substrate_does_not_create_workbench(tmp_path: Path):
    output = tmp_path / "scan"
    root = tmp_path / "specimen"
    root.mkdir()
    (root / "app.tsx").write_text("export const App = () => null\n", encoding="utf-8")
    _write_closure(output, surface_count=5, bound=5, closed=5)

    status = prepare_assimilation_workbench(
        output=output,
        specimen=_specimen(),
        files=[{"path": "app.tsx", "language": "TypeScript", "is_binary": 0}],
        nodes=[], findings=[], evidence=[], adapter_runs={"typescript-electron": 1}, content_root=root,
    )

    assert status == {
        "state": "NOT_REQUIRED", "required": False, "workbench": None,
        "unknown_runtime_languages": [], "reason_count": 0,
    }
    assert not (output / "assimilation").exists()
