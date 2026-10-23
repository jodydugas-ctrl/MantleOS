from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from typing import Any

from .adapters import DEFAULT_ADAPTERS
from .adapters.base import Adapter
from .engine import ScanEngine


_CANONICAL_PROJECTIONS = [
    "machine_body_map.json", "evidence_graph.json", "evidence_catalog.json",
    "completeness_vector.json", "integrity_report.json", "surface_closure.json",
    "effect_closure.json", "nest_capability_map.json", "stage1_summary.md",
    "projection_manifest.json",
]


def _load_json(root: Path, name: str) -> dict[str, Any]:
    return json.loads((root / name).read_text(encoding="utf-8"))


def _fresh(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _load_candidate(path: Path) -> Adapter:
    path = path.resolve(strict=True)
    module_name = f"scan_assimilation_candidate_{sha256(path.read_bytes()).hexdigest()[:16]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load candidate adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    # Candidate-local parse helpers may live beside candidate_adapter.py. This is explicitly authorized
    # scanner code loading; ordinary scan never performs this step and never imports specimen modules.
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(path.parent))
        except ValueError:
            pass

    candidate_class = getattr(module, "CandidateAssimilationAdapter", None)
    if not isinstance(candidate_class, type) or not issubclass(candidate_class, Adapter):
        raise TypeError("candidate_adapter.py must expose CandidateAssimilationAdapter(Adapter)")
    candidate = candidate_class()
    trusted_names = {adapter.name for adapter in DEFAULT_ADAPTERS}
    if candidate.name in trusted_names:
        raise ValueError(f"candidate adapter name collides with trusted adapter: {candidate.name}")
    return candidate


def _candidate_adapter_order(candidate: Adapter) -> list[Adapter]:
    # Keep generic text last so a candidate structural parser can emit anatomy before the generic evidence
    # sweep. Both still run where accepted; ordering does not grant the candidate semantic authority.
    generic = [a for a in DEFAULT_ADAPTERS if a.name == "generic_text"]
    structural = [a for a in DEFAULT_ADAPTERS if a.name != "generic_text"]
    return [*structural, candidate, *generic]


def _run_summary(root: Path) -> dict[str, Any]:
    body = _load_json(root, "machine_body_map.json")
    surface = _load_json(root, "surface_closure.json")
    effect = _load_json(root, "effect_closure.json")
    integrity = _load_json(root, "integrity_report.json")
    nest = _load_json(root, "nest_capability_map.json")
    return {
        "fingerprint": (body.get("specimen") or {}).get("fingerprint"),
        "files": (body.get("inventory") or {}).get("file_count"),
        "nodes": (body.get("extraction") or {}).get("node_count"),
        "edges": (body.get("extraction") or {}).get("edge_count"),
        "evidence": (body.get("extraction") or {}).get("evidence_count"),
        "findings": (body.get("extraction") or {}).get("finding_count"),
        "surface_closure": {k: surface.get(k) for k in (
            "state", "surface_count", "bound_count", "partial_count", "unresolved_count", "closure_ratio"
        )},
        "effect_closure": {k: effect.get(k) for k in (
            "state", "surface_count", "closed_count", "partial_count", "unresolved_count", "closure_ratio"
        )},
        "integrity": {k: integrity.get(k) for k in ("state", "issue_count", "severity_counts")},
        "nest": {k: nest.get(k) for k in (
            "state", "capability_count", "effect_count", "boundary_count", "persistence_object_count"
        )},
    }


def validate_assimilation_candidate(*, specimen_root: Path, candidate_path: Path, output: Path,
                                    specimen_id: str | None = None) -> dict[str, Any]:
    """Evaluate candidate scanner code without promoting it into the trusted adapter set.

    Loading candidate code is an explicit engineering action. It is not ordinary scanning and the candidate
    is responsible for obeying the no-specimen-execution contract. The validator supplies no API that executes,
    imports, builds, instruments, or stimulates the specimen.
    """
    specimen_root = Path(specimen_root).resolve(strict=True)
    candidate_path = Path(candidate_path).resolve(strict=True)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    candidate = _load_candidate(candidate_path)

    baseline_dir = output / "baseline"
    adapted_a_dir = output / "candidate-a"
    adapted_b_dir = output / "candidate-b"
    for path in (baseline_dir, adapted_a_dir, adapted_b_dir):
        _fresh(path)

    ScanEngine().scan(specimen_root, baseline_dir, specimen_id=specimen_id)
    adapters = _candidate_adapter_order(candidate)
    ScanEngine(adapters=adapters).scan(specimen_root, adapted_a_dir, specimen_id=specimen_id)
    ScanEngine(adapters=adapters).scan(specimen_root, adapted_b_dir, specimen_id=specimen_id)

    deterministic_files: list[str] = []
    mismatches: list[str] = []
    for name in _CANONICAL_PROJECTIONS:
        left = adapted_a_dir / name
        right = adapted_b_dir / name
        if not left.exists() or not right.exists():
            mismatches.append(name)
            continue
        if left.read_bytes() == right.read_bytes():
            deterministic_files.append(name)
        else:
            mismatches.append(name)

    baseline = _run_summary(baseline_dir)
    candidate_summary = _run_summary(adapted_a_dir)
    fingerprint_match = baseline.get("fingerprint") == candidate_summary.get("fingerprint")
    baseline_errors = int((baseline.get("integrity") or {}).get("severity_counts", {}).get("ERROR", 0) or 0)
    candidate_errors = int((candidate_summary.get("integrity") or {}).get("severity_counts", {}).get("ERROR", 0) or 0)

    def delta(path: tuple[str, ...]) -> float | int | None:
        def get(obj):
            cur: Any = obj
            for part in path:
                if not isinstance(cur, dict):
                    return None
                cur = cur.get(part)
            return cur
        a = get(candidate_summary)
        b = get(baseline)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a - b
        return None

    candidate_hash = sha256(candidate_path.read_bytes()).hexdigest()
    report = {
        "schema_version": "scan-assimilation-candidate-validation/0.1",
        "candidate": {
            "path": str(candidate_path), "sha256": candidate_hash,
            "adapter_name": candidate.name, "adapter_version": str(candidate.version),
        },
        "specimen": {
            "root": str(specimen_root), "specimen_id": specimen_id,
            "fingerprint_match": fingerprint_match,
        },
        "baseline": baseline,
        "candidate_run": candidate_summary,
        "delta": {
            "nodes": delta(("nodes",)), "edges": delta(("edges",)), "evidence": delta(("evidence",)),
            "human_surfaces": delta(("surface_closure", "surface_count")),
            "bound_surfaces": delta(("surface_closure", "bound_count")),
            "closed_effect_routes": delta(("effect_closure", "closed_count")),
            "nest_effects": delta(("nest", "effect_count")),
            "nest_boundaries": delta(("nest", "boundary_count")),
        },
        "determinism": {
            "state": "PASS" if not mismatches else "FAIL",
            "matched_projection_count": len(deterministic_files),
            "matched_projections": deterministic_files,
            "mismatched_projections": mismatches,
        },
        "integrity_gate": {
            "baseline_error_count": baseline_errors,
            "candidate_error_count": candidate_errors,
            "state": "PASS" if candidate_errors <= baseline_errors else "FAIL",
        },
        "promotion": {
            "state": "BLOCKED_PENDING_REVIEW",
            "reason": "mechanical candidate validation never promotes scanner code; regression, anti-overfit and newly-closed-route review remain required",
        },
    }
    report["mechanical_gate"] = "PASS" if (
        fingerprint_match and not mismatches and candidate_errors <= baseline_errors
    ) else "FAIL"
    (output / "candidate_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
