from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import tempfile
import tomllib
import platform
import shutil
import sys
import zipfile
from contextlib import contextmanager
from collections import Counter
from typing import Any

from . import __version__
from .engine import ScanEngine
from .integrity import audit_integrity, effect_closure, surface_closure
from .queries import QUERY_SQL, RELEASE_ACCEPTANCE_QUERIES
from .store import Store
from .evidence_graph import (
    export_completeness, export_evidence_catalog, export_evidence_graph, refresh_machine_body_map_projection,
)
from .capabilities import write_nest_capability_map
from .integrity import write_integrity_outputs, write_projection_manifest
from .reconstruction import load_reconstruction_proposal, promote_reconstruction_proposal


def _safe_rel(value: str) -> str:
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe manifest path: {value!r}")
    return p.as_posix()


def _hash_file(path: Path) -> tuple[int, str]:
    h = sha256()
    size = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            size += len(chunk)
            h.update(chunk)
    return size, h.hexdigest()





CERTIFICATION_MANIFEST = "CERTIFICATION_MANIFEST.json"
CERTIFICATION_RECEIPT = "certification_receipt.json"


@contextmanager
def _llm_disabled_environment():
    """Temporarily remove common LLM credentials and advertise mechanical-only execution."""
    names = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "AZURE_OPENAI_API_KEY")
    prior = {name: os.environ.pop(name, None) for name in names}
    prior_disabled = os.environ.get("SCAN_LLM_DISABLED")
    os.environ["SCAN_LLM_DISABLED"] = "1"
    try:
        yield
    finally:
        if prior_disabled is None:
            os.environ.pop("SCAN_LLM_DISABLED", None)
        else:
            os.environ["SCAN_LLM_DISABLED"] = prior_disabled
        for name, value in prior.items():
            if value is not None:
                os.environ[name] = value


def _json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_certification_manifest(certification_root: Path) -> dict[str, Any]:
    """Seal a certification directory without introducing a circular self-hash."""
    root = Path(certification_root).resolve(strict=True)
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == CERTIFICATION_MANIFEST or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        size, digest = _hash_file(path)
        files.append({"path": rel, "bytes": size, "sha256": digest})
    payload = {
        "schema_version": "scan-certification-manifest/0.1",
        "engine_version": __version__,
        "files": files,
    }
    (root / CERTIFICATION_MANIFEST).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload


def verify_certification(certification_root: Path) -> dict[str, Any]:
    root = Path(certification_root).resolve(strict=True)
    issues: list[dict[str, Any]] = []
    manifest_path = root / CERTIFICATION_MANIFEST
    receipt_path = root / CERTIFICATION_RECEIPT
    if not manifest_path.is_file():
        return {"schema_version": "scan-certification-verification/0.1", "state": "FAIL", "issues": [{"kind": "missing_certification_manifest"}]}
    try:
        payload = _json_file(manifest_path)
    except Exception as exc:
        return {"schema_version": "scan-certification-verification/0.1", "state": "FAIL", "issues": [{"kind": "invalid_certification_manifest", "error": str(exc)}]}
    if payload.get("schema_version") != "scan-certification-manifest/0.1":
        issues.append({"kind": "unsupported_certification_manifest_schema", "value": payload.get("schema_version")})
    expected: set[str] = set()
    checked = 0
    for item in payload.get("files", []):
        try:
            rel = _safe_rel(str(item["path"]))
        except Exception as exc:
            issues.append({"kind": "unsafe_path", "item": item, "error": str(exc)})
            continue
        expected.add(rel)
        path = root.joinpath(*PurePosixPath(rel).parts)
        if not path.is_file():
            issues.append({"kind": "missing_file", "path": rel})
            continue
        size, digest = _hash_file(path)
        checked += 1
        if size != int(item.get("bytes", -1)):
            issues.append({"kind": "size_mismatch", "path": rel, "expected": item.get("bytes"), "actual": size})
        if digest != item.get("sha256"):
            issues.append({"kind": "hash_mismatch", "path": rel, "expected": item.get("sha256"), "actual": digest})
    actual = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
        and path.name != CERTIFICATION_MANIFEST and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }
    for rel in sorted(actual - expected):
        issues.append({"kind": "untracked_certification_file", "path": rel})
    if not receipt_path.is_file():
        issues.append({"kind": "missing_certification_receipt"})
        receipt = {}
    else:
        try:
            receipt = _json_file(receipt_path)
            if receipt.get("schema_version") != "scan-specimen-certification/0.1":
                issues.append({"kind": "unsupported_receipt_schema", "value": receipt.get("schema_version")})
        except Exception as exc:
            receipt = {}
            issues.append({"kind": "invalid_certification_receipt", "error": str(exc)})
    scan_root = root / "scan"
    projection = verify_projection_manifest(scan_root) if scan_root.is_dir() else {"state": "FAIL", "issues": [{"kind": "missing_scan_directory"}]}
    if projection.get("state") != "PASS":
        issues.append({"kind": "projection_verification_failed", "details": projection.get("issues", [])})
    return {
        "schema_version": "scan-certification-verification/0.1",
        "state": "PASS" if not issues else "FAIL",
        "engine_version_recorded": payload.get("engine_version"),
        "receipt_state": receipt.get("state"),
        "manifest_file_count": len(payload.get("files", [])),
        "verified_file_count": checked,
        "projection_state": projection.get("state"),
        "issue_count": len(issues),
        "issues": issues,
    }


def create_certification_bundle(certification_root: Path, bundle_path: Path) -> dict[str, Any]:
    """Create a stable-order ZIP handoff; hashes in CERTIFICATION_MANIFEST remain the authority."""
    root = Path(certification_root).resolve(strict=True)
    bundle = Path(bundle_path).resolve()
    bundle.parent.mkdir(parents=True, exist_ok=True)
    if bundle.exists():
        bundle.unlink()
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, path.read_bytes())
    size, digest = _hash_file(bundle)
    return {"path": str(bundle), "bytes": size, "sha256": digest}


def _coverage_receipt(scan_root: Path, summary: dict[str, Any]) -> dict[str, Any]:
    vector = _json_file(scan_root / "completeness_vector.json")
    state_counts = Counter(str(d.get("state") or "UNKNOWN") for d in vector.get("dimensions", []))
    machine = _json_file(scan_root / "machine_body_map.json")
    findings = machine.get("findings", [])
    parser_failures = [f for f in findings if f.get("kind") == "parser_failure"]
    parser_gaps = [f for f in findings if f.get("kind") == "parser_gap"]
    inventory = summary.get("inventory", {})
    budget = summary.get("budget", {})
    explicit_partial = bool(
        budget.get("triggered")
        or inventory.get("content_unavailable_file_count", 0)
        or parser_failures
    )
    return {
        "execution_state": "PARTIAL" if explicit_partial else "COMPLETE_WITH_EXPLICIT_COVERAGE_VECTOR",
        "completeness_dimension_state_counts": dict(sorted(state_counts.items())),
        "content_unavailable_file_count": inventory.get("content_unavailable_file_count", 0),
        "budget_triggered": bool(budget.get("triggered")),
        "budget_reason": budget.get("reason"),
        "parser_failure_count": len(parser_failures),
        "parser_gap_count": len(parser_gaps),
        "rule": "PASS certifies mechanical integrity of this evidence package, not universal semantic completeness; consult the coverage vector.",
    }


def _finalize_certification(package_audit: dict[str, Any], summary: dict[str, Any], scan_out: Path,
                            certification_root: Path, specimen_id: str | None, policy: dict[str, Any],
                            bundle_path: Path | None, receipt_extensions: dict[str, Any] | None = None) -> dict[str, Any]:
    out = Path(certification_root).resolve()
    store = Store(scan_out / "scan_index.sqlite", readonly=True)
    integrity = audit_integrity(store)
    closure = surface_closure(store)
    deep = effect_closure(store)
    store.close()
    projections = verify_projection_manifest(scan_out)
    queries = run_query_acceptance(scan_out / "scan_index.sqlite")
    machine = _json_file(scan_out / "machine_body_map.json")
    resolved_specimen_id = specimen_id or machine.get("specimen", {}).get("specimen_id")
    coverage = _coverage_receipt(scan_out, summary)
    health_sections = {"package": package_audit, "projections": projections, "queries": queries}
    mechanical_pass = (
        all(section.get("state") == "PASS" for section in health_sections.values())
        and integrity.get("severity_counts", {}).get("ERROR", 0) == 0
    )
    receipt = {
        "schema_version": "scan-specimen-certification/0.1",
        "engine_version": __version__,
        "state": "PASS" if mechanical_pass else "FAIL",
        "meaning": "PASS means the evidence handoff passed SCAN mechanical integrity gates; it is not a claim of complete understanding.",
        "llm_environment": "DISABLED",
        "specimen": {
            "specimen_id": resolved_specimen_id,
            "fingerprint": machine.get("specimen", {}).get("fingerprint"),
            "acquisition_mode": machine.get("specimen", {}).get("acquisition_mode"),
            "provider": machine.get("specimen", {}).get("provider"),
            "repository": machine.get("specimen", {}).get("repository"),
            "commit_sha": machine.get("specimen", {}).get("commit_sha"),
            "tree_sha": machine.get("specimen", {}).get("tree_sha"),
        },
        "policy": policy,
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "mechanical_health": {
            "package_state": package_audit.get("state"),
            "projection_state": projections.get("state"),
            "query_state": queries.get("state"),
            "queries_passed": queries.get("passed_query_count"),
            "queries_required": queries.get("required_query_count"),
            "integrity_state": integrity.get("state"),
            "integrity_error_count": integrity.get("severity_counts", {}).get("ERROR", 0),
            "surface_closure_state": closure.get("state"),
            "effect_closure_state": deep.get("state"),
        },
        "coverage": coverage,
        "counts": {
            "files": summary.get("inventory", {}).get("file_count"),
            "materialized_files": summary.get("inventory", {}).get("materialized_file_count"),
            "nodes": summary.get("extraction", {}).get("node_count"),
            "edges": summary.get("extraction", {}).get("edge_count"),
            "evidence": summary.get("extraction", {}).get("evidence_count"),
            "semantic_objects": summary.get("semantic_graph", {}).get("objects"),
            "semantic_relations": summary.get("semantic_graph", {}).get("relations"),
        },
    }
    if receipt_extensions:
        for key, value in receipt_extensions.items():
            if key in receipt:
                raise ValueError(f"receipt extension may not overwrite core field {key!r}")
            receipt[key] = value
    (out / CERTIFICATION_RECEIPT).write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = write_certification_manifest(out)
    verification = verify_certification(out)
    receipt["sealed_handoff"] = {
        "manifest_file_count": len(manifest.get("files", [])),
        "verification_state": verification.get("state"),
    }
    (out / CERTIFICATION_RECEIPT).write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = write_certification_manifest(out)
    verification = verify_certification(out)
    bundle = create_certification_bundle(out, bundle_path) if bundle_path is not None else None
    return {
        "schema_version": "scan-certification-run/0.1",
        "state": "PASS" if mechanical_pass and verification.get("state") == "PASS" else "FAIL",
        "receipt": receipt,
        "verification": verification,
        "bundle": bundle,
        "certification_root": str(out),
    }


def _certification_policy(*, max_file_bytes: int, max_total_bytes: int, max_materialized_files: int,
                          max_extraction_seconds: float, max_nodes: int, max_edges: int,
                          max_evidence: int) -> dict[str, Any]:
    return {
        "max_file_bytes": max_file_bytes,
        "max_total_bytes": max_total_bytes,
        "max_materialized_files": max_materialized_files,
        "max_extraction_seconds": max_extraction_seconds,
        "max_nodes": max_nodes,
        "max_edges": max_edges,
        "max_evidence": max_evidence,
    }


def certify_specimen(package_root: Path, specimen_root: Path, certification_root: Path, *,
                     specimen_id: str | None = None, max_file_bytes: int = 64 * 1024 * 1024,
                     max_total_bytes: int = 0, max_materialized_files: int = 0,
                     max_extraction_seconds: float = 0.0, max_nodes: int = 0,
                     max_edges: int = 0, max_evidence: int = 0, bundle_path: Path | None = None) -> dict[str, Any]:
    """Run one bounded, LLM-disabled local scan and seal an agent-verifiable evidence handoff."""
    package = Path(package_root).resolve(strict=True)
    specimen = Path(specimen_root)
    if specimen.is_symlink():
        raise ValueError(f"specimen root must not be a symlink: {specimen}")
    specimen = specimen.resolve(strict=True)
    out = Path(certification_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    scan_out = out / "scan"
    package_audit = verify_package(package)
    policy = _certification_policy(
        max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes,
        max_materialized_files=max_materialized_files, max_extraction_seconds=max_extraction_seconds,
        max_nodes=max_nodes, max_edges=max_edges, max_evidence=max_evidence,
    )
    with _llm_disabled_environment():
        summary = ScanEngine(**policy).scan(specimen, scan_out, specimen_id)
        return _finalize_certification(package_audit, summary, scan_out, out, specimen_id, policy, bundle_path)


def certify_manifest(package_root: Path, manifest_path: Path, certification_root: Path, *,
                     content_root: Path | None = None, specimen_id: str | None = None,
                     max_file_bytes: int = 64 * 1024 * 1024, max_total_bytes: int = 0,
                     max_materialized_files: int = 0, max_extraction_seconds: float = 0.0,
                     max_nodes: int = 0, max_edges: int = 0, max_evidence: int = 0,
                     bundle_path: Path | None = None) -> dict[str, Any]:
    """Certify a provider/source-manifest specimen without discarding acquisition provenance."""
    package = Path(package_root).resolve(strict=True)
    manifest = Path(manifest_path).resolve(strict=True)
    content = Path(content_root).resolve(strict=True) if content_root is not None else None
    if content is not None and content.is_symlink():
        raise ValueError(f"content root must not be a symlink: {content}")
    out = Path(certification_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    scan_out = out / "scan"
    package_audit = verify_package(package)
    policy = _certification_policy(
        max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes,
        max_materialized_files=max_materialized_files, max_extraction_seconds=max_extraction_seconds,
        max_nodes=max_nodes, max_edges=max_edges, max_evidence=max_evidence,
    )
    with _llm_disabled_environment():
        summary = ScanEngine(**policy).scan_manifest(manifest, scan_out, content, specimen_id)
        return _finalize_certification(package_audit, summary, scan_out, out, specimen_id, policy, bundle_path)

def certify_reconstruction_handoff(package_root: Path, source_certification_root: Path,
                                    proposal_path: Path, certification_root: Path, *,
                                    bundle_path: Path | None = None) -> dict[str, Any]:
    """Create a new sealed handoff lineage from a verified mechanical certification + M5 proposal.

    The source certification is never modified. Semantic generation may be external (human/LLM); only
    promotion is mechanical. The derived receipt records its parent so evidence integrity and semantic
    interpretation remain separable.
    """
    package = Path(package_root).resolve(strict=True)
    source = Path(source_certification_root).resolve(strict=True)
    proposal_path = Path(proposal_path).resolve(strict=True)
    source_verification = verify_certification(source)
    if source_verification.get("state") != "PASS":
        return {
            "schema_version": "scan-reconstruction-certification-run/0.1",
            "state": "REJECTED",
            "reason": "SOURCE_CERTIFICATION_INVALID",
            "source_verification": source_verification,
        }
    source_receipt = _json_file(source / CERTIFICATION_RECEIPT)
    source_manifest_size, source_manifest_sha = _hash_file(source / CERTIFICATION_MANIFEST)
    source_receipt_size, source_receipt_sha = _hash_file(source / CERTIFICATION_RECEIPT)

    out = Path(certification_root).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"derived certification output must be empty or absent: {out}")
    out.mkdir(parents=True, exist_ok=True)
    scan_out = out / "scan"
    shutil.copytree(source / "scan", scan_out)

    store = Store(scan_out / "scan_index.sqlite")
    try:
        payload = load_reconstruction_proposal(proposal_path)
        promotion = promote_reconstruction_proposal(
            store, payload, contract_path=scan_out / "reconstruction_contract.json"
        )
        if promotion.get("state") != "PROMOTED":
            store.close()
            shutil.rmtree(out, ignore_errors=True)
            return {
                "schema_version": "scan-reconstruction-certification-run/0.1",
                "state": "REJECTED",
                "reason": "RECONSTRUCTION_PROPOSAL_REJECTED",
                "promotion": promotion,
                "source_verification": source_verification,
            }

        specimen_objects = [x for x in store.semantic_objects() if x["object_type"] == "SPECIMEN"]
        specimen = specimen_objects[0]["attributes"] if specimen_objects else {}
        export_evidence_graph(store, specimen, scan_out / "evidence_graph.json")
        export_evidence_catalog(store, scan_out / "evidence_catalog.json")
        export_completeness(store, scan_out / "completeness_vector.json")
        write_integrity_outputs(store, scan_out)
        write_nest_capability_map(store, scan_out / "nest_capability_map.json")
        refresh_machine_body_map_projection(store, scan_out / "machine_body_map.json")
        write_projection_manifest(scan_out, [
            "machine_body_map.json", "evidence_graph.json", "evidence_catalog.json",
            "completeness_vector.json", "integrity_report.json", "surface_closure.json",
            "effect_closure.json", "nest_capability_map.json", "reconstruction_contract.json",
            "stage1_summary.md",
        ])
    finally:
        # close is idempotent enough for the normal path; rejected path closes before deleting on Windows.
        try:
            store.close()
        except Exception:
            pass

    summary = _json_file(scan_out / "machine_body_map.json")
    package_audit = verify_package(package)
    proposal_origin = payload.get("origin") or "EXTERNAL_PROPOSAL"
    lineage = {
        "kind": "semantic-promotion",
        "parent_certification_manifest": {"bytes": source_manifest_size, "sha256": source_manifest_sha},
        "parent_certification_receipt": {"bytes": source_receipt_size, "sha256": source_receipt_sha},
        "parent_engine_version": source_receipt.get("engine_version"),
        "rule": "The parent mechanical evidence handoff remains immutable; this derived handoff adds only mechanically validated semantic promotion.",
    }
    semantic_promotion = {
        "proposal_id": promotion.get("proposal_id"),
        "proposal_origin": proposal_origin,
        "promotion_state": promotion.get("state"),
        "validation_state": promotion.get("validation", {}).get("state"),
        "anchor_count": promotion.get("contract", {}).get("anchor_count"),
        "behavior_count": promotion.get("contract", {}).get("behavior_count"),
        "authority_rule": "External semantic generation does not become DIRECT evidence; SCAN certifies only the promotion gate, proof paths, coverage discipline, and sealed bytes.",
    }
    policy = dict(source_receipt.get("policy") or {})
    policy["semantic_promotion"] = "M5_GATED"
    result = _finalize_certification(
        package_audit, summary, scan_out, out,
        summary.get("specimen", {}).get("specimen_id"), policy, bundle_path,
        receipt_extensions={"lineage": lineage, "semantic_promotion": semantic_promotion},
    )
    result["schema_version"] = "scan-reconstruction-certification-run/0.1"
    result["promotion"] = promotion
    return result


def write_package_manifest(package_root: Path) -> dict[str, Any]:
    root = Path(package_root).resolve(strict=True)
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == "PACKAGE_MANIFEST.json" or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        size, digest = _hash_file(path)
        files.append({"path": rel, "bytes": size, "sha256": digest})
    payload = {"schema_version": "scan-package-manifest/0.1", "engine_version": __version__, "files": files}
    (root / "PACKAGE_MANIFEST.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload

def verify_package(package_root: Path) -> dict[str, Any]:
    root = Path(package_root).resolve(strict=True)
    manifest_path = root / "PACKAGE_MANIFEST.json"
    issues: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        return {"schema_version": "scan-package-self-audit/0.1", "state": "FAIL", "issues": [{"kind": "missing_manifest"}]}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema_version": "scan-package-self-audit/0.1", "state": "FAIL", "issues": [{"kind": "invalid_manifest", "error": str(exc)}]}
    if payload.get("schema_version") != "scan-package-manifest/0.1":
        issues.append({"kind": "unsupported_manifest_schema", "value": payload.get("schema_version")})
    if payload.get("engine_version") != __version__:
        issues.append({"kind": "engine_version_mismatch", "manifest": payload.get("engine_version"), "runtime": __version__})

    expected: set[str] = set()
    checked = 0
    for item in payload.get("files", []):
        try:
            rel = _safe_rel(str(item["path"]))
        except Exception as exc:
            issues.append({"kind": "unsafe_path", "item": item, "error": str(exc)})
            continue
        expected.add(rel)
        path = root.joinpath(*PurePosixPath(rel).parts)
        if not path.is_file():
            issues.append({"kind": "missing_file", "path": rel})
            continue
        size, digest = _hash_file(path)
        checked += 1
        if size != int(item.get("bytes", -1)):
            issues.append({"kind": "size_mismatch", "path": rel, "expected": item.get("bytes"), "actual": size})
        if digest != item.get("sha256"):
            issues.append({"kind": "hash_mismatch", "path": rel, "expected": item.get("sha256"), "actual": digest})

    actual = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == "PACKAGE_MANIFEST.json" or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        actual.add(rel)
    for rel in sorted(actual - expected):
        issues.append({"kind": "untracked_package_file", "path": rel})
    for rel in sorted(expected - actual):
        # Missing files were already reported above; retain this only for a manifest bookkeeping view.
        if not (root / rel).exists():
            continue

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            project_version = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
            if project_version != __version__:
                issues.append({"kind": "pyproject_version_mismatch", "pyproject": project_version, "runtime": __version__})
        except Exception as exc:
            issues.append({"kind": "invalid_pyproject", "error": str(exc)})
    else:
        issues.append({"kind": "missing_pyproject"})

    return {
        "schema_version": "scan-package-self-audit/0.1",
        "state": "PASS" if not issues else "FAIL",
        "engine_version": __version__,
        "manifest_file_count": len(payload.get("files", [])),
        "verified_file_count": checked,
        "issue_count": len(issues),
        "issues": issues,
    }


def verify_projection_manifest(output_root: Path) -> dict[str, Any]:
    root = Path(output_root).resolve(strict=True)
    manifest_path = root / "projection_manifest.json"
    issues = []
    if not manifest_path.is_file():
        return {"schema_version": "scan-projection-self-audit/0.1", "state": "FAIL", "issues": [{"kind": "missing_projection_manifest"}]}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema_version": "scan-projection-self-audit/0.1", "state": "FAIL", "issues": [{"kind": "invalid_projection_manifest", "error": str(exc)}]}
    if payload.get("schema_version") != "scan-projection-manifest/0.1":
        issues.append({"kind": "unsupported_projection_schema", "value": payload.get("schema_version")})
    for item in payload.get("projections", []):
        name = item.get("name")
        try:
            rel = _safe_rel(str(name))
        except Exception as exc:
            issues.append({"kind": "unsafe_projection_path", "name": name, "error": str(exc)})
            continue
        path = root.joinpath(*PurePosixPath(rel).parts)
        if not path.is_file():
            issues.append({"kind": "missing_projection", "name": rel})
            continue
        size, digest = _hash_file(path)
        if size != int(item.get("bytes", -1)):
            issues.append({"kind": "projection_size_mismatch", "name": rel, "expected": item.get("bytes"), "actual": size})
        if digest != item.get("sha256"):
            issues.append({"kind": "projection_hash_mismatch", "name": rel, "expected": item.get("sha256"), "actual": digest})
    db = root / str(payload.get("canonical_store") or "scan_index.sqlite")
    if not db.is_file():
        issues.append({"kind": "missing_canonical_store", "path": db.name})
    else:
        conn = None
        try:
            conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
            quick = conn.execute("PRAGMA quick_check").fetchone()[0]
            if quick != "ok":
                issues.append({"kind": "database_quick_check", "result": quick})
        except sqlite3.DatabaseError as exc:
            issues.append({"kind": "database_corrupt", "error": str(exc)})
        finally:
            if conn is not None:
                conn.close()
    return {
        "schema_version": "scan-projection-self-audit/0.1",
        "state": "PASS" if not issues else "FAIL",
        "projection_count": len(payload.get("projections", [])),
        "issue_count": len(issues),
        "issues": issues,
    }


def run_query_acceptance(db_path: Path, *, limit: int = 100) -> dict[str, Any]:
    path = Path(db_path).resolve(strict=True)
    db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    db.row_factory = sqlite3.Row
    results = []
    for name in RELEASE_ACCEPTANCE_QUERIES:
        try:
            rows = [dict(r) for r in db.execute(QUERY_SQL[name] + " LIMIT ?", (limit,)).fetchall()]
            results.append({"query": name, "state": "PASS", "row_count": len(rows), "sample_ids": [r.get("id") for r in rows[:5] if r.get("id")]})
        except Exception as exc:
            results.append({"query": name, "state": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    db.close()
    return {
        "schema_version": "scan-query-acceptance/0.1",
        "state": "PASS" if all(r["state"] == "PASS" for r in results) else "FAIL",
        "required_query_count": len(RELEASE_ACCEPTANCE_QUERIES),
        "passed_query_count": sum(1 for r in results if r["state"] == "PASS"),
        "results": results,
    }


def qualify_release(package_root: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(package_root).resolve(strict=True)
    package_audit = verify_package(root)
    fixture = root / "tests" / "fixtures" / "qualification_sample"
    if not fixture.is_dir():
        fixture = root / "tests" / "fixtures" / "qt_sample"
    with _llm_disabled_environment():
        with tempfile.TemporaryDirectory(prefix="scan-qualification-") as tmp:
            scan_out = Path(tmp) / "scan"
            summary = ScanEngine().scan(fixture, scan_out, "scan-release-qualification")
            store = Store(scan_out / "scan_index.sqlite", readonly=True)
            integrity = audit_integrity(store)
            closure = surface_closure(store)
            deep = effect_closure(store)
            store.close()
            projections = verify_projection_manifest(scan_out)
            queries = run_query_acceptance(scan_out / "scan_index.sqlite")
            required_outputs = [
                "scan_index.sqlite", "machine_body_map.json", "evidence_graph.json", "evidence_catalog.json",
                "completeness_vector.json", "integrity_report.json", "surface_closure.json", "effect_closure.json",
                "nest_capability_map.json", "projection_manifest.json", "stage1_summary.md",
            ]
            missing_outputs = [name for name in required_outputs if not (scan_out / name).is_file()]
            mechanical = {
                "state": "PASS" if not missing_outputs and integrity.get("severity_counts", {}).get("ERROR", 0) == 0 else "FAIL",
                "llm_environment": "DISABLED",
                "required_outputs": required_outputs,
                "missing_outputs": missing_outputs,
                "integrity_state": integrity.get("state"),
                "integrity_error_count": integrity.get("severity_counts", {}).get("ERROR", 0),
                "surface_closure_state": closure.get("state"),
                "effect_closure_state": deep.get("state"),
                "files": summary["inventory"]["file_count"],
                "nodes": summary["extraction"]["node_count"],
                "edges": summary["extraction"]["edge_count"],
                "evidence": summary["extraction"]["evidence_count"],
            }

    sections = {"package": package_audit, "mechanical_independence": mechanical, "projections": projections, "queries": queries}
    state = "PASS" if all(x.get("state") == "PASS" for x in sections.values()) else "FAIL"
    result = {"schema_version": "scan-release-qualification/0.1", "engine_version": __version__, "state": state, **sections}
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
