from __future__ import annotations

from collections import deque
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any
import zipfile

from . import __version__
from .engine import ScanEngine
from .integrity import PROOF_RELATION_KINDS, audit_integrity, effect_closure, surface_closure
from .release import verify_certification, verify_package, verify_projection_manifest
from .store import Store

CHALLENGE_SCHEMA = "scan-reconstruction-challenge/0.1"
EVALUATOR_SCHEMA = "scan-reconstruction-evaluator/0.1"
SUBMISSION_SCHEMA = "scan-reconstruction-submission/0.1"
SCORECARD_SCHEMA = "scan-reconstruction-scorecard/0.1"
TRIAL_RECEIPT_SCHEMA = "scan-reconstruction-trial/0.1"
CHALLENGE_MANIFEST = "CHALLENGE_MANIFEST.json"
EVALUATOR_MANIFEST = "EVALUATOR_MANIFEST.json"
TRIAL_MANIFEST = "TRIAL_MANIFEST.json"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hash_file(path: Path) -> tuple[int, str]:
    h = sha256()
    size = 0
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            size += len(chunk)
            h.update(chunk)
    return size, h.hexdigest()


def _safe_rel(value: str) -> str:
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe manifest path: {value!r}")
    return p.as_posix()


def _write_manifest(root: Path, name: str, schema: str) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == name or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        size, digest = _hash_file(path)
        records.append({"path": rel, "bytes": size, "sha256": digest})
    payload = {"schema_version": schema, "engine_version": __version__, "files": records}
    (root / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def _verify_manifest(root: Path, name: str, schema: str) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    manifest_path = root / name
    issues: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        return {"state": "FAIL", "issues": [{"kind": "missing_manifest", "path": name}]}
    try:
        payload = _json(manifest_path)
    except Exception as exc:
        return {"state": "FAIL", "issues": [{"kind": "invalid_manifest", "error": str(exc)}]}
    if payload.get("schema_version") != schema:
        issues.append({"kind": "unsupported_manifest_schema", "expected": schema, "actual": payload.get("schema_version")})
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
            issues.append({"kind": "size_mismatch", "path": rel})
        if digest != item.get("sha256"):
            issues.append({"kind": "hash_mismatch", "path": rel})
    actual = {
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
        and p.name != name and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}
    }
    for rel in sorted(actual - expected):
        issues.append({"kind": "untracked_file", "path": rel})
    return {
        "state": "PASS" if not issues else "FAIL",
        "manifest_file_count": len(payload.get("files", [])),
        "verified_file_count": checked,
        "issue_count": len(issues),
        "issues": issues,
    }


def _zip_dir(root: Path, output: Path) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, path.read_bytes())
    size, digest = _hash_file(output)
    return {"path": str(output), "bytes": size, "sha256": digest}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _sanitize_contract(contract: dict[str, Any], challenge_id: str) -> dict[str, Any]:
    anchors = []
    for anchor in contract.get("anchors", []):
        attrs = dict(anchor.get("attributes") or {})
        attrs.pop("promotion", None)
        anchors.append({
            "id": anchor.get("id"),
            "subtype": anchor.get("subtype"),
            "label": anchor.get("label"),
            "coverage": anchor.get("coverage"),
            "property": attrs.get("property"),
            "fidelity_test": attrs.get("fidelity_test"),
            "uncertainty": attrs.get("uncertainty"),
            "contradiction_count": len(anchor.get("contradictions") or []),
            "supporting_semantic_objects": [
                {"id": x.get("id"), "object_type": x.get("object_type"), "label": x.get("label"), "coverage": x.get("coverage")}
                for x in anchor.get("supporting_objects", [])
            ],
        })
    behaviors = []
    for behavior in contract.get("behaviors", []):
        attrs = dict(behavior.get("attributes") or {})
        attrs.pop("promotion", None)
        behaviors.append({
            "id": behavior.get("id"),
            "subtype": behavior.get("subtype"),
            "label": behavior.get("label"),
            "coverage": behavior.get("coverage"),
            "trigger": attrs.get("trigger"),
            "preconditions": attrs.get("preconditions"),
            "observable_response": attrs.get("observable_response"),
            "state_transition": attrs.get("state_transition"),
            "persistence_effect": attrs.get("persistence_effect"),
            "error_behavior": attrs.get("error_behavior"),
            "uncertainty": attrs.get("uncertainty"),
            "contradiction_count": len(behavior.get("contradictions") or []),
        })
    completeness = [
        {"key": d.get("key"), "label": d.get("label"), "state": d.get("state"), "parent_id": d.get("parent_id")}
        for d in contract.get("completeness_vector", [])
    ]
    return {
        "schema_version": "scan-public-reconstruction-contract/0.1",
        "challenge_id": challenge_id,
        "authority": "derived challenge projection; no original source bytes or source evidence excerpts are included",
        "anchors": anchors,
        "behaviors": behaviors,
        "completeness_vector": completeness,
    }


def _proof_anatomy(store: Store, start_id: str, max_depth: int = 16) -> list[dict[str, Any]]:
    """Collect non-semantic mechanical objects in the positive proof ancestry of a promoted claim."""
    seen = {start_id}
    q = deque([(start_id, 0)])
    found: dict[str, dict[str, Any]] = {}
    while q:
        current, depth = q.popleft()
        if depth >= max_depth:
            continue
        for rel in store.incoming_semantic_relations(current):
            if rel.get("kind") not in PROOF_RELATION_KINDS:
                continue
            src = str(rel["src"])
            obj = store.semantic_object(src)
            if obj is None:
                continue
            if obj.get("object_type") == "ANATOMICAL_OBJECT":
                found[src] = obj
            if src not in seen:
                seen.add(src)
                q.append((src, depth + 1))
    return [found[k] for k in sorted(found)]


def _surface_public_key(obj: dict[str, Any]) -> dict[str, Any]:
    attrs = obj.get("attributes") or {}
    text = attrs.get("text") or attrs.get("title") or attrs.get("label")
    return {
        "surface_type": attrs.get("surface_type") or obj.get("subtype"),
        "surface_role": attrs.get("surface_role"),
        "human_text": text,
        "fallback_name": obj.get("label"),
        "coverage": obj.get("coverage"),
    }


def _terminal_signature(item: dict[str, Any]) -> dict[str, Any]:
    attrs = item.get("attributes") or {}
    return {
        "kind": item.get("kind"),
        "name": item.get("name"),
        "coverage": item.get("coverage"),
        "effect_type": attrs.get("effect_type"),
        "capability": attrs.get("capability"),
        "direction": attrs.get("direction"),
        "boundary_type": attrs.get("boundary_type"),
        "feedback_type": attrs.get("feedback_type"),
    }


def _derive_evaluator(cert_root: Path, challenge_id: str, challenge_manifest_sha: str = "") -> dict[str, Any]:
    scan = cert_root / "scan"
    contract = _json(scan / "reconstruction_contract.json")
    surface_payload = _json(scan / "surface_closure.json")
    effect_payload = _json(scan / "effect_closure.json")
    surfaces = {str(r.get("surface_id")): r for r in surface_payload.get("records", [])}
    effects = {str(r.get("surface_id")): r for r in effect_payload.get("records", [])}
    store = Store(scan / "scan_index.sqlite", readonly=True)
    anchor_expectations = []
    try:
        for anchor in contract.get("anchors", []):
            anatomy: dict[str, dict[str, Any]] = {}
            support_ids = [str(x.get("id")) for x in anchor.get("supporting_objects", []) if x.get("id")]
            for support_id in support_ids:
                for obj in _proof_anatomy(store, support_id):
                    anatomy[obj["id"]] = obj
            surface_expectations = []
            for obj in anatomy.values():
                attrs = obj.get("attributes") or {}
                if obj.get("subtype") not in {"human_surface", "surface_factory_output"} and attrs.get("surface_role") != "input":
                    continue
                sid = str(obj["id"])
                srec = surfaces.get(sid, {})
                erec = effects.get(sid, {})
                surface_expectations.append({
                    **_surface_public_key(obj),
                    "source_surface_id": sid,
                    "binding_closure": srec.get("closure", "UNRESOLVED"),
                    "effect_closure": erec.get("effect_closure", "UNRESOLVED"),
                    "terminal_signatures": [_terminal_signature(x) for x in erec.get("terminals", [])],
                    "feedback_signatures": [_terminal_signature(x) for x in erec.get("feedback", [])],
                })
            anchor_expectations.append({
                "anchor_id": anchor.get("id"),
                "anchor_label": anchor.get("label"),
                "source_coverage": anchor.get("coverage"),
                "source_uncertainty": (anchor.get("attributes") or {}).get("uncertainty"),
                "source_contradiction_count": len(anchor.get("contradictions") or []),
                "surface_expectations": surface_expectations,
                "scorable": bool(surface_expectations),
                "unscorable_reason": None if surface_expectations else "no mechanically recoverable human-input surface in the promoted proof ancestry",
            })
    finally:
        store.close()
    return {
        "schema_version": EVALUATOR_SCHEMA,
        "engine_version": __version__,
        "challenge_id": challenge_id,
        "challenge_manifest_sha256": challenge_manifest_sha,
        "scoring_policy": {
            "source_code_comparison": False,
            "candidate_execution": False,
            "comparison_basis": "SCAN-recovered surface/binding/effect signatures only",
            "mapped_missing_rule": "strong source evidence + adequate candidate scan + missing signature => RECONSTRUCTION_AGENT",
            "weak_source_rule": "PARTIAL/BLOCKED/UNKNOWN source support remains UNRESOLVED_SOURCE_UNCERTAINTY",
            "candidate_gap_rule": "candidate scanner gaps that prevent adjudication => SCANNER_CANDIDATE_COVERAGE",
            "unscorable_rule": "promoted anchor with no mechanical reconstruction signature => SEMANTIC_IR",
        },
        "anchor_expectations": anchor_expectations,
    }


def _public_requirements(evaluator: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose enough source-free mechanical signature for a blind agent to reconstruct what will be scored."""
    result = []
    for anchor in evaluator.get("anchor_expectations", []):
        surfaces = []
        for surface in anchor.get("surface_expectations", []):
            required_terminals = []
            uncertain_terminals = []
            for terminal in surface.get("terminal_signatures", []):
                public = {k: terminal.get(k) for k in ("kind", "name", "coverage", "effect_type", "capability", "direction", "boundary_type", "feedback_type")}
                (required_terminals if terminal.get("coverage") == "MAPPED" else uncertain_terminals).append(public)
            surfaces.append({
                "surface_type": surface.get("surface_type"),
                "surface_role": surface.get("surface_role"),
                "human_text": surface.get("human_text"),
                "fallback_name": surface.get("fallback_name") if not surface.get("human_text") else None,
                "binding_closure": surface.get("binding_closure"),
                "effect_closure": surface.get("effect_closure"),
                "required_mapped_terminals": required_terminals,
                "uncertain_terminals_not_required_for_binary_failure": uncertain_terminals,
            })
        result.append({
            "anchor_id": anchor.get("anchor_id"),
            "source_coverage": anchor.get("source_coverage"),
            "scorable": anchor.get("scorable"),
            "surface_requirements": surfaces,
        })
    return result


def _agent_brief(challenge: dict[str, Any]) -> str:
    contract = challenge["reconstruction_contract"]
    lines = [
        "# SCAN Blind Reconstruction Challenge",
        "",
        f"Challenge ID: `{challenge['challenge_id']}`",
        "",
        "Reconstruct the target application from this public SCAN challenge only.",
        "",
        "## Blindness boundary",
        "",
        "Do not obtain or inspect the original specimen source, the parent SCAN certification, or the private evaluator package.",
        "Do not use repository/network lookup to retrieve the original source. The challenge intentionally contains no source bytes, SQLite database, source evidence excerpts, or original source paths.",
        "",
        "You may choose any internal implementation. Fidelity is judged against the evidence-supported behavior/control contracts below, not source similarity.",
        "",
        "## Reconstruction anchors",
        "",
    ]
    for a in contract.get("anchors", []):
        lines += [f"### {a.get('id')} — {a.get('label')}", f"- Coverage: `{a.get('coverage')}`", f"- Property: {a.get('property')}", f"- Fidelity test: {a.get('fidelity_test')}", f"- Uncertainty: {a.get('uncertainty')}", ""]
    lines += ["## Mechanically scored reconstruction signatures", ""]
    for req in challenge.get("reconstruction_requirements", []):
        lines.append(f"### {req.get('anchor_id')}")
        for surface in req.get("surface_requirements", []):
            lines.append(f"- Surface: type={surface.get('surface_type')}, text={surface.get('human_text') or surface.get('fallback_name')}, binding={surface.get('binding_closure')}, effect={surface.get('effect_closure')}")
            for terminal in surface.get("required_mapped_terminals", []):
                lines.append(f"  - Required terminal: kind={terminal.get('kind')}, effect={terminal.get('effect_type') or terminal.get('name')}, capability={terminal.get('capability')}, direction={terminal.get('direction')}")
        lines.append("")
    lines += [
        "## Submission",
        "",
        "Place the reconstructed implementation in its own directory. Fill in `SUBMISSION_TEMPLATE.json` outside that directory and pass it separately to the SCAN scorer.",
        "The source-isolation declaration is an attestation unless the surrounding execution environment independently enforces isolation.",
        "",
    ]
    return "\n".join(lines)


def prepare_reconstruction_trial(source_certification_root: Path, challenge_out: Path, evaluator_out: Path, *,
                                 challenge_bundle: Path | None = None, evaluator_bundle: Path | None = None) -> dict[str, Any]:
    source = Path(source_certification_root).resolve(strict=True)
    verification = verify_certification(source)
    if verification.get("state") != "PASS":
        return {"schema_version": "scan-reconstruction-trial-preparation/0.1", "state": "FAIL", "reason": "SOURCE_CERTIFICATION_INVALID", "verification": verification}
    contract_path = source / "scan" / "reconstruction_contract.json"
    if not contract_path.is_file():
        return {"schema_version": "scan-reconstruction-trial-preparation/0.1", "state": "FAIL", "reason": "RECONSTRUCTION_CONTRACT_MISSING"}
    contract = _json(contract_path)
    if not contract.get("anchors"):
        return {"schema_version": "scan-reconstruction-trial-preparation/0.1", "state": "FAIL", "reason": "NO_RECONSTRUCTION_ANCHORS"}

    parent_manifest = source / "CERTIFICATION_MANIFEST.json"
    _, parent_manifest_sha = _hash_file(parent_manifest)
    _, contract_sha = _hash_file(contract_path)
    challenge_id = "challenge:" + sha256(f"{parent_manifest_sha}:{contract_sha}".encode()).hexdigest()[:24]

    challenge_root = Path(challenge_out).resolve()
    evaluator_root = Path(evaluator_out).resolve()
    for root in (challenge_root, evaluator_root):
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)

    evaluator = _derive_evaluator(source, challenge_id)
    public_contract = _sanitize_contract(contract, challenge_id)
    challenge = {
        "schema_version": CHALLENGE_SCHEMA,
        "engine_version": __version__,
        "challenge_id": challenge_id,
        "purpose": "source-blind reconstruction from evidence-supported SCAN contracts",
        "source_isolation": {
            "original_source_bytes_included": False,
            "canonical_database_included": False,
            "source_evidence_excerpts_included": False,
            "original_source_paths_included": False,
            "private_evaluator_included": False,
            "agent_policy": "original source, parent certification, private evaluator, and repository/network source lookup are forbidden",
            "enforcement": "challenge packaging is mechanically enforced; external agent network/filesystem isolation must be enforced by the trial harness or declared by the agent",
        },
        "reconstruction_contract": public_contract,
        "reconstruction_requirements": _public_requirements(evaluator),
        "required_submission_schema": SUBMISSION_SCHEMA,
    }
    (challenge_root / "challenge.json").write_text(json.dumps(challenge, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (challenge_root / "AGENT_BRIEF.md").write_text(_agent_brief(challenge) + "\n", encoding="utf-8")
    submission_template = {
        "schema_version": SUBMISSION_SCHEMA,
        "challenge_id": challenge_id,
        "agent": {"name": "", "version": "", "provider": ""},
        "source_isolation": {
            "original_source_accessed": False,
            "parent_certification_accessed": False,
            "evaluator_bundle_accessed": False,
            "network_source_lookup_used": False,
            "enforcement_level": "DECLARED_ONLY",
        },
        "notes": "",
    }
    (challenge_root / "SUBMISSION_TEMPLATE.json").write_text(json.dumps(submission_template, indent=2) + "\n", encoding="utf-8")
    challenge_manifest = _write_manifest(challenge_root, CHALLENGE_MANIFEST, "scan-reconstruction-challenge-manifest/0.1")
    _, challenge_manifest_sha = _hash_file(challenge_root / CHALLENGE_MANIFEST)

    evaluator["challenge_manifest_sha256"] = challenge_manifest_sha
    evaluator["lineage"] = {
        "parent_certification_manifest_sha256": parent_manifest_sha,
        "parent_reconstruction_contract_sha256": contract_sha,
    }
    (evaluator_root / "evaluator.json").write_text(json.dumps(evaluator, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    evaluator_manifest = _write_manifest(evaluator_root, EVALUATOR_MANIFEST, "scan-reconstruction-evaluator-manifest/0.1")

    public_forbidden = ["scan_index.sqlite", "evidence_catalog.json", "evidence_graph.json", "machine_body_map.json"]
    leaked = [p.name for p in challenge_root.rglob("*") if p.is_file() and p.name in public_forbidden]
    if leaked:
        raise RuntimeError(f"public challenge leaked forbidden evidence artifacts: {leaked}")

    return {
        "schema_version": "scan-reconstruction-trial-preparation/0.1",
        "state": "PASS",
        "challenge_id": challenge_id,
        "source_certification_verification": verification.get("state"),
        "challenge": {
            "root": str(challenge_root),
            "manifest_files": len(challenge_manifest.get("files", [])),
            "verification": _verify_manifest(challenge_root, CHALLENGE_MANIFEST, "scan-reconstruction-challenge-manifest/0.1"),
            "bundle": _zip_dir(challenge_root, challenge_bundle) if challenge_bundle else None,
        },
        "evaluator": {
            "root": str(evaluator_root),
            "manifest_files": len(evaluator_manifest.get("files", [])),
            "verification": _verify_manifest(evaluator_root, EVALUATOR_MANIFEST, "scan-reconstruction-evaluator-manifest/0.1"),
            "bundle": _zip_dir(evaluator_root, evaluator_bundle) if evaluator_bundle else None,
            "scorable_anchor_count": sum(1 for x in evaluator.get("anchor_expectations", []) if x.get("scorable")),
            "unscorable_anchor_count": sum(1 for x in evaluator.get("anchor_expectations", []) if not x.get("scorable")),
        },
    }


def _submission_check(path: Path, challenge_id: str) -> dict[str, Any]:
    try:
        data = _json(path)
    except Exception as exc:
        return {"state": "FAIL", "reason": "INVALID_SUBMISSION", "error": str(exc)}
    issues = []
    if data.get("schema_version") != SUBMISSION_SCHEMA:
        issues.append("unsupported_submission_schema")
    if data.get("challenge_id") != challenge_id:
        issues.append("challenge_id_mismatch")
    isolation = data.get("source_isolation") or {}
    for key in ("original_source_accessed", "parent_certification_accessed", "evaluator_bundle_accessed", "network_source_lookup_used"):
        if isolation.get(key) is not False:
            issues.append(f"source_isolation_{key}_not_false")
    if not isolation.get("enforcement_level"):
        issues.append("missing_enforcement_level")
    return {
        "state": "PASS" if not issues else "FAIL",
        "issues": issues,
        "agent": data.get("agent") or {},
        "source_isolation": isolation,
        "notes": data.get("notes"),
    }


def _candidate_surface_matches(expected: dict[str, Any], candidate_records: list[dict[str, Any]], candidate_objects: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    e_type = _normalize_text(expected.get("surface_type"))
    e_text = _normalize_text(expected.get("human_text"))
    e_name = _normalize_text(expected.get("fallback_name"))
    matches = []
    for rec in candidate_records:
        if e_type and _normalize_text(rec.get("surface_type")) != e_type:
            continue
        obj = candidate_objects.get(str(rec.get("surface_id")), {})
        attrs = obj.get("attributes") or {}
        c_text = _normalize_text(attrs.get("text") or attrs.get("title") or attrs.get("label"))
        c_name = _normalize_text(rec.get("name"))
        if e_text:
            if c_text != e_text and c_name != e_text:
                continue
        elif e_name and c_name != e_name:
            continue
        matches.append(rec)
    return matches


def _closure_rank(value: str) -> int:
    return {"UNRESOLVED": 0, "PARTIAL": 1, "BOUND": 2, "CLOSED": 2}.get(str(value or "UNRESOLVED"), 0)


def _terminal_matches(expected: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if expected.get("kind") and candidate.get("kind") != expected.get("kind"):
        return False
    ea, ca = expected, candidate.get("attributes") or {}
    fields = {
        "effect_type": ca.get("effect_type"),
        "capability": ca.get("capability"),
        "direction": ca.get("direction"),
        "boundary_type": ca.get("boundary_type"),
        "feedback_type": ca.get("feedback_type"),
    }
    discriminators = [k for k in fields if ea.get(k)]
    if discriminators:
        return all(_normalize_text(ea.get(k)) == _normalize_text(fields[k]) for k in discriminators)
    return _normalize_text(ea.get("name")) == _normalize_text(candidate.get("name"))


def _score_anchor(expectation: dict[str, Any], candidate_surface: list[dict[str, Any]], candidate_effect: dict[str, dict[str, Any]], candidate_objects: dict[str, dict[str, Any]], candidate_scan_partial: bool) -> dict[str, Any]:
    anchor_id = expectation.get("anchor_id")
    if not expectation.get("scorable"):
        return {"anchor_id": anchor_id, "state": "UNSCORABLE", "score": None, "attribution": "SEMANTIC_IR", "reason": expectation.get("unscorable_reason")}
    source_weak = expectation.get("source_coverage") != "MAPPED" or expectation.get("source_contradiction_count", 0) > 0
    checks = []
    any_fail = False
    any_partial = False
    for surface in expectation.get("surface_expectations", []):
        matches = _candidate_surface_matches(surface, candidate_surface, candidate_objects)
        if not matches:
            if source_weak:
                checks.append({"kind": "surface", "state": "PARTIAL", "expected": surface, "reason": "source evidence is not fully mapped/contradiction-free"})
                any_partial = True
            elif candidate_scan_partial:
                checks.append({"kind": "surface", "state": "PARTIAL", "expected": surface, "reason": "candidate scan coverage prevents a strong absence claim"})
                any_partial = True
            else:
                checks.append({"kind": "surface", "state": "FAIL", "expected": surface, "reason": "strongly evidenced source surface not recovered in candidate"})
                any_fail = True
            continue
        best = max(matches, key=lambda x: _closure_rank(x.get("closure")))
        binding_ok = _closure_rank(best.get("closure")) >= _closure_rank(surface.get("binding_closure"))
        effect = candidate_effect.get(str(best.get("surface_id")), {})
        effect_ok = _closure_rank(effect.get("effect_closure")) >= _closure_rank(surface.get("effect_closure"))
        terminal_results = []
        for terminal in surface.get("terminal_signatures", []):
            if terminal.get("coverage") != "MAPPED":
                terminal_results.append({"expected": terminal, "state": "SOURCE_UNCERTAINTY", "reason": "source terminal is not MAPPED and is advisory rather than a binary reconstruction requirement"})
                continue
            matched = any(_terminal_matches(terminal, c) for c in effect.get("terminals", []))
            terminal_results.append({"expected": terminal, "state": "PASS" if matched else "FAIL"})
            if not matched:
                any_fail = True
        if not binding_ok or not effect_ok:
            if candidate_scan_partial:
                any_partial = True
            else:
                any_fail = True
        checks.append({
            "kind": "surface",
            "state": "PASS" if binding_ok and effect_ok and not any(x.get("state") == "FAIL" for x in terminal_results) else ("PARTIAL" if candidate_scan_partial else "FAIL"),
            "expected": surface,
            "candidate_surface_id": best.get("surface_id"),
            "candidate_name": best.get("name"),
            "binding_ok": binding_ok,
            "effect_ok": effect_ok,
            "terminal_results": terminal_results,
        })
    if any_fail:
        attribution = "SCANNER_CANDIDATE_COVERAGE" if candidate_scan_partial else "RECONSTRUCTION_AGENT"
        return {"anchor_id": anchor_id, "state": "FAIL" if not candidate_scan_partial else "PARTIAL", "score": 0.0 if not candidate_scan_partial else 0.5, "attribution": attribution, "checks": checks}
    if any_partial or source_weak:
        return {"anchor_id": anchor_id, "state": "PARTIAL", "score": 0.5, "attribution": "UNRESOLVED_SOURCE_UNCERTAINTY" if source_weak else "SCANNER_CANDIDATE_COVERAGE", "checks": checks}
    return {"anchor_id": anchor_id, "state": "PASS", "score": 1.0, "attribution": "PASS", "checks": checks}


def _copy_candidate(candidate_root: Path, target: Path) -> None:
    root = Path(candidate_root)
    if root.is_symlink():
        raise ValueError("candidate root must not be a symlink")
    root = root.resolve(strict=True)
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"candidate tree contains symlink: {path.relative_to(root)}")
    shutil.copytree(root, target)


def score_reconstruction_trial(package_root: Path, evaluator_root: Path, candidate_root: Path, submission_path: Path,
                               trial_out: Path, *, bundle_path: Path | None = None) -> dict[str, Any]:
    package = Path(package_root).resolve(strict=True)
    package_audit = verify_package(package)
    if package_audit.get("state") != "PASS":
        return {"schema_version": TRIAL_RECEIPT_SCHEMA, "state": "INVALID", "reason": "PACKAGE_AUDIT_FAILED", "package_audit": package_audit}
    evaluator_root = Path(evaluator_root).resolve(strict=True)
    evaluator_verification = _verify_manifest(evaluator_root, EVALUATOR_MANIFEST, "scan-reconstruction-evaluator-manifest/0.1")
    if evaluator_verification.get("state") != "PASS":
        return {"schema_version": TRIAL_RECEIPT_SCHEMA, "state": "INVALID", "reason": "EVALUATOR_INVALID", "verification": evaluator_verification}
    evaluator = _json(evaluator_root / "evaluator.json")
    if evaluator.get("schema_version") != EVALUATOR_SCHEMA:
        return {"schema_version": TRIAL_RECEIPT_SCHEMA, "state": "INVALID", "reason": "EVALUATOR_SCHEMA_UNSUPPORTED"}
    submission = _submission_check(Path(submission_path), str(evaluator.get("challenge_id")))
    if submission.get("state") != "PASS":
        return {"schema_version": TRIAL_RECEIPT_SCHEMA, "state": "INVALID", "reason": "SOURCE_ISOLATION_OR_SUBMISSION_INVALID", "submission": submission}

    out = Path(trial_out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    candidate_copy = out / "candidate"
    _copy_candidate(candidate_root, candidate_copy)
    shutil.copy2(submission_path, out / "submission.json")
    scan_out = out / "candidate_scan"
    summary = ScanEngine().scan(candidate_copy, scan_out, specimen_id=f"reconstruction:{evaluator.get('challenge_id')}")
    projection_verification = verify_projection_manifest(scan_out)
    store = Store(scan_out / "scan_index.sqlite", readonly=True)
    integrity = audit_integrity(store)
    surface = surface_closure(store)
    effects = effect_closure(store)
    objects = {o["id"]: o for o in store.semantic_objects()}
    store.close()
    candidate_partial = bool(
        summary.get("budget", {}).get("triggered")
        or summary.get("inventory", {}).get("content_unavailable_file_count", 0)
        or integrity.get("severity_counts", {}).get("ERROR", 0)
        or projection_verification.get("state") != "PASS"
    )
    candidate_surfaces = list(surface.get("records", []))
    candidate_effects = {str(r.get("surface_id")): r for r in effects.get("records", [])}
    anchor_results = [
        _score_anchor(exp, candidate_surfaces, candidate_effects, objects, candidate_partial)
        for exp in evaluator.get("anchor_expectations", [])
    ]
    counts = {state: sum(1 for x in anchor_results if x.get("state") == state) for state in ("PASS", "PARTIAL", "FAIL", "UNSCORABLE")}
    numeric = [x["score"] for x in anchor_results if isinstance(x.get("score"), (int, float))]
    fidelity = sum(numeric) / len(numeric) if numeric else None
    if counts["FAIL"]:
        score_state = "FAIL"
    elif counts["PARTIAL"] or counts["UNSCORABLE"]:
        score_state = "PARTIAL"
    else:
        score_state = "PASS"
    scorecard = {
        "schema_version": SCORECARD_SCHEMA,
        "challenge_id": evaluator.get("challenge_id"),
        "state": score_state,
        "fidelity_score": fidelity,
        "authoritative_result": "anchor states and attributions; fidelity_score is convenience only",
        "anchor_counts": counts,
        "candidate_scan": {
            "integrity_state": integrity.get("state"),
            "integrity_errors": integrity.get("severity_counts", {}).get("ERROR", 0),
            "projection_state": projection_verification.get("state"),
            "surface_closure_state": surface.get("state"),
            "effect_closure_state": effects.get("state"),
            "coverage_partial": candidate_partial,
        },
        "anchor_results": anchor_results,
        "attribution_categories": ["RECONSTRUCTION_AGENT", "SEMANTIC_IR", "SCANNER_CANDIDATE_COVERAGE", "UNRESOLVED_SOURCE_UNCERTAINTY", "PASS"],
        "limits": [
            "This M6A scorer is static and does not execute the reconstructed candidate.",
            "Source isolation outside the generated challenge package is declared unless an external harness enforces filesystem/network isolation.",
            "A PASS demonstrates recovery of mechanically scorable signatures, not universal behavioral equivalence.",
        ],
    }
    (out / "scorecard.json").write_text(json.dumps(scorecard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _, evaluator_manifest_sha = _hash_file(evaluator_root / EVALUATOR_MANIFEST)
    receipt = {
        "schema_version": TRIAL_RECEIPT_SCHEMA,
        "engine_version": __version__,
        "state": score_state,
        "challenge_id": evaluator.get("challenge_id"),
        "blindness": {
            "challenge_packaging": "MECHANICALLY_SOURCE_FREE",
            "agent_isolation": submission.get("source_isolation", {}).get("enforcement_level"),
            "agent_attestation_state": submission.get("state"),
        },
        "agent": submission.get("agent"),
        "lineage": {
            "challenge_manifest_sha256": evaluator.get("challenge_manifest_sha256"),
            "evaluator_manifest_sha256": evaluator_manifest_sha,
            **(evaluator.get("lineage") or {}),
        },
        "score": {"state": score_state, "fidelity_score": fidelity, "anchor_counts": counts},
        "candidate_scan": scorecard["candidate_scan"],
    }
    (out / "trial_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = _write_manifest(out, TRIAL_MANIFEST, "scan-reconstruction-trial-manifest/0.1")
    verification = verify_reconstruction_trial(out)
    bundle = _zip_dir(out, bundle_path) if bundle_path else None
    return {
        "schema_version": "scan-reconstruction-trial-run/0.1",
        "state": score_state if verification.get("state") == "PASS" else "INVALID",
        "challenge_id": evaluator.get("challenge_id"),
        "scorecard": scorecard,
        "trial_verification": verification,
        "manifest_file_count": len(manifest.get("files", [])),
        "bundle": bundle,
        "trial_root": str(out),
    }


def verify_reconstruction_trial(trial_root: Path) -> dict[str, Any]:
    root = Path(trial_root).resolve(strict=True)
    verification = _verify_manifest(root, TRIAL_MANIFEST, "scan-reconstruction-trial-manifest/0.1")
    issues = list(verification.get("issues", []))
    try:
        receipt = _json(root / "trial_receipt.json")
        scorecard = _json(root / "scorecard.json")
    except Exception as exc:
        issues.append({"kind": "invalid_trial_metadata", "error": str(exc)})
        receipt, scorecard = {}, {}
    if receipt.get("schema_version") != TRIAL_RECEIPT_SCHEMA:
        issues.append({"kind": "unsupported_trial_receipt_schema", "actual": receipt.get("schema_version")})
    if scorecard.get("schema_version") != SCORECARD_SCHEMA:
        issues.append({"kind": "unsupported_scorecard_schema", "actual": scorecard.get("schema_version")})
    if receipt.get("challenge_id") != scorecard.get("challenge_id"):
        issues.append({"kind": "challenge_id_mismatch"})
    scan_root = root / "candidate_scan"
    projections = verify_projection_manifest(scan_root) if scan_root.is_dir() else {"state": "FAIL", "issues": [{"kind": "missing_candidate_scan"}]}
    if projections.get("state") != "PASS":
        issues.append({"kind": "candidate_projection_verification_failed", "details": projections.get("issues")})
    return {
        "schema_version": "scan-reconstruction-trial-verification/0.1",
        "state": "PASS" if not issues else "FAIL",
        "receipt_state": receipt.get("state"),
        "scorecard_state": scorecard.get("state"),
        "manifest_file_count": verification.get("manifest_file_count", 0),
        "verified_file_count": verification.get("verified_file_count", 0),
        "projection_state": projections.get("state"),
        "issue_count": len(issues),
        "issues": issues,
    }
