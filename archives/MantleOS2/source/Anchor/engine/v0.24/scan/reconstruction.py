from __future__ import annotations

from collections import defaultdict, deque
import json
from pathlib import Path
from typing import Any

from .evidence_graph import _relation_row, ingest_overlay, trace_impact, trace_why
from .integrity import CLAIM_OBJECT_TYPES, PROOF_RELATION_KINDS, SEMANTIC_RELATION_KINDS, refresh_refinement_completeness
from .model import COVERAGE_STATES, stable_id

PROPOSAL_SCHEMA = "scan-reconstruction-proposal/0.1"
CONTRACT_SCHEMA = "scan-reconstruction-contract/0.1"
PROMOTABLE_OBJECT_TYPES = {
    "INTERPRETATION", "BEHAVIOR", "ARTERY", "NERVE", "CAPABILITY", "RECONSTRUCTION_ANCHOR"
}
ANCHOR_SUPPORT_TYPES = {"BEHAVIOR", "ARTERY", "NERVE", "CAPABILITY"}


def load_reconstruction_proposal(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != PROPOSAL_SCHEMA:
        raise ValueError(f"unsupported reconstruction proposal schema: {payload.get('schema_version')!r}")
    return payload


def _issue(code: str, severity: str, message: str, **attributes) -> dict[str, Any]:
    return {
        "id": stable_id("reconstruction-validation", code, message, json.dumps(attributes, sort_keys=True, default=str)),
        "code": code,
        "severity": severity,
        "message": message,
        "attributes": attributes,
    }


def _normalize_object(x: dict[str, Any]) -> dict[str, Any]:
    required = {"id", "object_type", "subtype", "label"}
    missing = required - set(x)
    if missing:
        raise ValueError(f"reconstruction object missing fields {sorted(missing)}: {x!r}")
    return {
        "id": str(x["id"]),
        "object_type": str(x["object_type"]),
        "subtype": str(x["subtype"]),
        "label": str(x["label"]),
        "coverage": str(x.get("coverage", "UNKNOWN")),
        "attributes": dict(x.get("attributes") or {}),
    }


def _normalize_relation(x: dict[str, Any]) -> dict[str, Any]:
    required = {"src", "dst", "kind"}
    missing = required - set(x)
    if missing:
        raise ValueError(f"reconstruction relation missing fields {sorted(missing)}: {x!r}")
    return _relation_row(
        str(x["src"]), str(x["dst"]), str(x["kind"]),
        relation_id=str(x.get("id") or stable_id("semantic-relation", x["src"], x["kind"], x["dst"])),
        status=str(x.get("status", "MAPPED")),
        attributes=dict(x.get("attributes") or {}),
        evidence_ids=[str(v) for v in x.get("evidence_ids", [])],
    )


def _combined_graph(store, objects: list[dict[str, Any]], relations: list[dict[str, Any]]):
    by_id = {o["id"]: o for o in store.semantic_objects()}
    by_id.update({o["id"]: o for o in objects})
    all_relations = list(store.semantic_relations()) + relations
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rel in all_relations:
        incoming[rel["dst"]].append(rel)
        outgoing[rel["src"]].append(rel)
    return by_id, incoming, outgoing


def _proof_walk(target: str, by_id: dict[str, dict[str, Any]], incoming: dict[str, list[dict[str, Any]]], max_depth: int = 16) -> dict[str, Any]:
    visited = {target}
    queue = deque([(target, 0)])
    object_ids = {target}
    relation_ids: set[str] = set()
    contradictions: list[dict[str, Any]] = []
    evidence: set[str] = set()
    files: set[str] = set()
    while queue:
        current, depth = queue.popleft()
        obj = by_id.get(current)
        if obj:
            if obj.get("object_type") == "EVIDENCE":
                evidence.add(current)
            if obj.get("object_type") == "FILE":
                files.add(current)
        if depth >= max_depth:
            continue
        for rel in incoming.get(current, []):
            if rel["kind"] == "contradicts":
                contradictions.append(rel)
                object_ids.add(rel["src"])
                continue
            if rel["kind"] not in PROOF_RELATION_KINDS:
                continue
            relation_ids.add(rel["id"])
            src = rel["src"]
            object_ids.add(src)
            if src not in visited:
                visited.add(src)
                queue.append((src, depth + 1))
    return {
        "object_ids": sorted(object_ids),
        "relation_ids": sorted(relation_ids),
        "evidence_ids": sorted(evidence),
        "source_file_ids": sorted(files),
        "contradictions": contradictions,
        "proof_complete": bool(evidence),
    }


def validate_reconstruction_proposal(store, payload: dict[str, Any], *, max_depth: int = 16) -> dict[str, Any]:
    """Validate a semantic reconstruction proposal without mutating the canonical store.

    The proposal may be authored by an LLM or human. Promotion authority remains mechanical: every
    promoted claim must have a positive source-evidence path, anchors must be supported by a typed
    behavior/artery/nerve/capability object, and coverage may not be stronger than its proof chain.
    """
    issues: list[dict[str, Any]] = []
    if payload.get("schema_version") != PROPOSAL_SCHEMA:
        issues.append(_issue("UNSUPPORTED_SCHEMA", "ERROR", "Unsupported reconstruction proposal schema",
                             observed=payload.get("schema_version"), expected=PROPOSAL_SCHEMA))
        return {"schema_version": "scan-reconstruction-validation/0.1", "state": "FAIL", "issues": issues,
                "anchor_results": [], "object_count": 0, "relation_count": 0}

    proposal_id = str(payload.get("proposal_id") or stable_id("reconstruction-proposal", json.dumps(payload, sort_keys=True, default=str)))
    objects: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    try:
        objects = [_normalize_object(x) for x in payload.get("objects", [])]
        relations = [_normalize_relation(x) for x in payload.get("relations", [])]
    except ValueError as exc:
        issues.append(_issue("MALFORMED_PROPOSAL", "ERROR", str(exc)))
        return {"schema_version": "scan-reconstruction-validation/0.1", "state": "FAIL", "proposal_id": proposal_id,
                "issues": issues, "anchor_results": [], "object_count": len(objects), "relation_count": len(relations)}

    existing = {o["id"]: o for o in store.semantic_objects()}
    seen: set[str] = set()
    for obj in objects:
        if not obj["id"]:
            issues.append(_issue("EMPTY_OBJECT_ID", "ERROR", "Proposal object ID must be non-empty"))
        if obj["id"] in seen:
            issues.append(_issue("DUPLICATE_OBJECT_ID", "ERROR", f"Duplicate proposal object ID {obj['id']}", object_id=obj["id"]))
        seen.add(obj["id"])
        if obj["id"] in existing:
            issues.append(_issue("OBJECT_ID_COLLISION", "ERROR", f"Proposal may not overwrite existing canonical object {obj['id']}", object_id=obj["id"]))
        if obj["object_type"] not in PROMOTABLE_OBJECT_TYPES:
            issues.append(_issue("NONPROMOTABLE_OBJECT_TYPE", "ERROR", f"Object type {obj['object_type']} is not proposal-promotable",
                                 object_id=obj["id"], object_type=obj["object_type"]))
        if obj["coverage"] not in COVERAGE_STATES:
            issues.append(_issue("INVALID_COVERAGE", "ERROR", f"Invalid coverage state {obj['coverage']}", object_id=obj["id"]))

        attrs = obj.get("attributes") or {}
        if obj["object_type"] == "BEHAVIOR":
            for field in ("trigger", "observable_response", "uncertainty"):
                if field not in attrs or attrs.get(field) in (None, ""):
                    issues.append(_issue("BEHAVIOR_CONTRACT_FIELD_MISSING", "ERROR",
                                         f"Behavior {obj['id']} requires non-empty attribute {field}",
                                         object_id=obj["id"], field=field))
        if obj["object_type"] == "RECONSTRUCTION_ANCHOR":
            for field in ("property", "fidelity_test", "uncertainty"):
                if field not in attrs or attrs.get(field) in (None, ""):
                    issues.append(_issue("ANCHOR_CONTRACT_FIELD_MISSING", "ERROR",
                                         f"Reconstruction anchor {obj['id']} requires non-empty attribute {field}",
                                         object_id=obj["id"], field=field))

    relation_ids: set[str] = set()
    valid_ids = set(existing) | {o["id"] for o in objects}
    for rel in relations:
        if rel["id"] in relation_ids:
            issues.append(_issue("DUPLICATE_RELATION_ID", "ERROR", f"Duplicate proposal relation ID {rel['id']}", relation_id=rel["id"]))
        relation_ids.add(rel["id"])
        if rel["kind"] not in SEMANTIC_RELATION_KINDS:
            issues.append(_issue("INVALID_RELATION_KIND", "ERROR", f"Unsupported semantic relation kind {rel['kind']}", relation_id=rel["id"]))
        for side in ("src", "dst"):
            if rel[side] not in valid_ids:
                issues.append(_issue("DANGLING_RELATION", "ERROR", f"Proposal relation endpoint {rel[side]} does not exist",
                                     relation_id=rel["id"], endpoint=side, object_id=rel[side]))
        for ev_id in rel.get("evidence_ids", []):
            ev = existing.get(ev_id)
            if ev is None or ev.get("object_type") != "EVIDENCE":
                issues.append(_issue("INVALID_RELATION_EVIDENCE", "ERROR", "Relation evidence_ids must reference existing EVIDENCE objects",
                                     relation_id=rel["id"], evidence_id=ev_id))

    if any(i["severity"] == "ERROR" for i in issues):
        return {"schema_version": "scan-reconstruction-validation/0.1", "state": "FAIL", "proposal_id": proposal_id,
                "issues": issues, "anchor_results": [], "object_count": len(objects), "relation_count": len(relations)}

    by_id, incoming, outgoing = _combined_graph(store, objects, relations)
    proposal_ids = {o["id"] for o in objects}

    # Every promoted semantic claim is required to be evidence-backed. Hypotheses can live outside the
    # canonical graph until evidence catches up; promotion is intentionally stricter than brainstorming.
    proof_by_object: dict[str, dict[str, Any]] = {}
    for obj in objects:
        if obj["object_type"] not in CLAIM_OBJECT_TYPES:
            continue
        walk = _proof_walk(obj["id"], by_id, incoming, max_depth=max_depth)
        proof_by_object[obj["id"]] = walk
        if not walk["proof_complete"]:
            issues.append(_issue("CLAIM_WITHOUT_EVIDENCE_PATH", "ERROR",
                                 f"Proposed {obj['object_type']} {obj['id']} has no positive proof path to source evidence",
                                 object_id=obj["id"], object_type=obj["object_type"]))

    anchor_results = []
    for anchor in [o for o in objects if o["object_type"] == "RECONSTRUCTION_ANCHOR"]:
        incoming_anchor = [r for r in incoming.get(anchor["id"], []) if r["kind"] == "supports_anchor"]
        typed_supporters = [by_id.get(r["src"]) for r in incoming_anchor]
        typed_supporters = [o for o in typed_supporters if o and o.get("object_type") in ANCHOR_SUPPORT_TYPES]
        if not typed_supporters:
            issues.append(_issue("ANCHOR_WITHOUT_TYPED_SUPPORT", "ERROR",
                                 f"Reconstruction anchor {anchor['id']} requires supports_anchor from a behavior/artery/nerve/capability",
                                 object_id=anchor["id"]))

        walk = proof_by_object.get(anchor["id"]) or _proof_walk(anchor["id"], by_id, incoming, max_depth=max_depth)
        path_objects = [by_id[x] for x in walk["object_ids"] if x in by_id]
        weaker = [o for o in path_objects if o.get("coverage") in {"PARTIAL", "BLOCKED", "UNKNOWN"}]
        if anchor["coverage"] == "MAPPED" and weaker:
            issues.append(_issue("ANCHOR_COVERAGE_ESCALATION", "ERROR",
                                 f"MAPPED anchor {anchor['id']} depends on weaker coverage",
                                 object_id=anchor["id"], weaker_objects=[{"id": o["id"], "coverage": o.get("coverage")} for o in weaker[:20]]))
        if anchor["coverage"] == "MAPPED" and walk["contradictions"]:
            issues.append(_issue("MAPPED_ANCHOR_HAS_CONTRADICTION", "ERROR",
                                 f"MAPPED anchor {anchor['id']} has visible contradictory evidence/claims",
                                 object_id=anchor["id"], contradiction_relation_ids=[r["id"] for r in walk["contradictions"]]))
        anchor_results.append({
            "id": anchor["id"],
            "coverage": anchor["coverage"],
            "proof_complete": walk["proof_complete"],
            "evidence_ids": walk["evidence_ids"],
            "source_file_ids": walk["source_file_ids"],
            "typed_supporter_ids": sorted(o["id"] for o in typed_supporters),
            "contradiction_relation_ids": sorted(r["id"] for r in walk["contradictions"]),
            "weaker_support_ids": sorted(o["id"] for o in weaker),
        })

    error_count = sum(1 for i in issues if i["severity"] == "ERROR")
    warn_count = sum(1 for i in issues if i["severity"] == "WARN")
    return {
        "schema_version": "scan-reconstruction-validation/0.1",
        "proposal_id": proposal_id,
        "state": "PASS" if error_count == 0 else "FAIL",
        "object_count": len(objects),
        "relation_count": len(relations),
        "anchor_count": len(anchor_results),
        "error_count": error_count,
        "warning_count": warn_count,
        "issues": issues,
        "anchor_results": anchor_results,
        "rule": "Promotion proves evidence traceability and coverage discipline; it does not grant semantic claims more authority than their supporting evidence.",
    }


def _to_overlay(payload: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    proposal_id = validation["proposal_id"]
    objects = []
    for raw in payload.get("objects", []):
        obj = _normalize_object(raw)
        attrs = dict(obj.get("attributes") or {})
        attrs["promotion"] = {
            "proposal_id": proposal_id,
            "validation_schema": validation["schema_version"],
            "validation_state": validation["state"],
        }
        obj["attributes"] = attrs
        objects.append(obj)
    relations = [_normalize_relation(x) for x in payload.get("relations", [])]
    return {
        "schema_version": "scan-semantic-overlay/0.1",
        "objects": objects,
        "relations": relations,
        "completeness": [],
    }


def export_reconstruction_contract(store, output_path: Path) -> dict[str, Any]:
    """Export reconstruction-ready contracts as a projection of the canonical graph."""
    anchors = sorted((o for o in store.semantic_objects() if o["object_type"] == "RECONSTRUCTION_ANCHOR"), key=lambda x: x["id"])
    behaviors = sorted((o for o in store.semantic_objects() if o["object_type"] == "BEHAVIOR"), key=lambda x: x["id"])
    specimen = next((o for o in store.semantic_objects() if o["object_type"] == "SPECIMEN"), None)

    anchor_records = []
    for anchor in anchors:
        why = trace_why(store, anchor["id"], max_depth=16)
        supporting_objects = sorted(
            (o for o in why["objects"] if o["object_type"] in ANCHOR_SUPPORT_TYPES),
            key=lambda x: x["id"],
        )
        anchor_records.append({
            "id": anchor["id"], "subtype": anchor["subtype"], "label": anchor["label"],
            "coverage": anchor["coverage"], "attributes": anchor.get("attributes") or {},
            "proof_complete": why["proof_complete"],
            "supporting_objects": [{"id": o["id"], "object_type": o["object_type"], "label": o["label"], "coverage": o["coverage"]} for o in supporting_objects],
            "evidence_ids": sorted(why["evidence_reached"]),
            "source_file_ids": sorted(why["source_files_reached"]),
            "contradictions": sorted(why["contradictions"], key=lambda r: r["id"]),
        })

    behavior_records = []
    for behavior in behaviors:
        why = trace_why(store, behavior["id"], max_depth=16)
        behavior_records.append({
            "id": behavior["id"], "subtype": behavior["subtype"], "label": behavior["label"],
            "coverage": behavior["coverage"], "attributes": behavior.get("attributes") or {},
            "proof_complete": why["proof_complete"],
            "evidence_ids": sorted(why["evidence_reached"]),
            "source_file_ids": sorted(why["source_files_reached"]),
            "contradictions": sorted(why["contradictions"], key=lambda r: r["id"]),
        })

    payload = {
        "schema_version": CONTRACT_SCHEMA,
        "canonical_store": "scan_index.sqlite",
        "authority": "projection-only; canonical semantic objects/relations and first-class evidence remain authoritative",
        "specimen": specimen.get("attributes") if specimen else {},
        "anchor_count": len(anchor_records),
        "behavior_count": len(behavior_records),
        "anchors": anchor_records,
        "behaviors": behavior_records,
        "completeness_vector": store.completeness_dimensions(),
        "agent_rule": "Treat each anchor only at its declared coverage. Resolve PARTIAL/BLOCKED/UNKNOWN dependencies before relying on them as complete behavior requirements.",
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def promote_reconstruction_proposal(store, payload: dict[str, Any], *, contract_path: Path | None = None) -> dict[str, Any]:
    validation = validate_reconstruction_proposal(store, payload)
    if validation["state"] != "PASS":
        return {"state": "REJECTED", "validation": validation, "promoted": {"objects": 0, "relations": 0}}

    overlay = _to_overlay(payload, validation)
    promoted = ingest_overlay(store, overlay)
    refinement = refresh_refinement_completeness(store)
    # Mechanical postcondition: promotion may not leave canonical integrity ERRORs.
    if refinement["integrity"].get("severity_counts", {}).get("ERROR", 0):
        raise RuntimeError("promoted reconstruction proposal left canonical integrity errors")
    contract = export_reconstruction_contract(store, contract_path) if contract_path is not None else None
    return {
        "state": "PROMOTED",
        "proposal_id": validation["proposal_id"],
        "validation": validation,
        "promoted": promoted,
        "integrity_state": refinement["integrity"].get("state"),
        "contract": {"path": str(contract_path), "anchor_count": contract["anchor_count"], "behavior_count": contract["behavior_count"]} if contract is not None else None,
    }
