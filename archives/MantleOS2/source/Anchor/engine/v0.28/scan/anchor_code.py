from __future__ import annotations

"""Deterministic Anchor Code 0.9 projection for SCAN.

SCAN mechanically inspects source and configuration evidence without executing the
target project. Anchor Code is a deterministic LLM-oriented semantic projection of
that evidence. Static evidence remains distinct from observed runtime behavior.
"""

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ANCHOR_SCHEMA = "AnchorCode/0.9"
ANCHOR_LANGUAGE_VERSION = "0.9"

TYPE_ORDER = [
    "EVIDENCE", "ENTITY", "RESOURCE", "IDENTITY", "HOST", "EXECUTION", "CAPABILITY",
    "BINDING", "LINEAGE", "REL", "BEHAVIOR", "STATE", "UNKNOWN", "GOAL",
    "REQUIREMENT", "OPTION", "DECISION", "PROCEDURE", "ACTION", "TEST", "RESULT",
    "ANCHOR", "LINK", "GATE", "DELTA", "PATTERN", "REFLEX", "RECEIPT",
]

PROVENANCE_RELATIONS = {
    "contains", "contains_evidence", "supports", "derived_from", "supports_anchor",
    "source_of", "targets", "contradicts",
}

RUNTIME_RELATIONS = {
    "CALLS", "RETURNS", "RAISES", "TRIGGERS", "FLOWS_TO", "WRITES", "READS",
    "PERSISTS_TO", "RECOVERS_FROM", "REQUIRES_CAPABILITY",
}


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return sha256(data).hexdigest()


def _derived_evidence_id(relation: dict[str, Any]) -> str:
    key = "|".join([
        str(relation.get("id") or ""), str(relation.get("src") or ""),
        str(relation.get("kind") or ""), str(relation.get("dst") or ""),
    ])
    return f"evidence:static:{_sha(key)[:20]}"


def _unknown_id(subject: str, question: str) -> str:
    return f"unknown:{_sha(subject + '|' + question)[:20]}"


def _record(record_type: str, record_id: str, **body: Any) -> dict[str, Any]:
    return {
        "type": record_type,
        "id": record_id,
        "body": {key: value for key, value in body.items() if value is not None},
    }


def _merge_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge exact identities conservatively; conflicting claims fail closed."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in records:
        key = (rec["type"], rec["id"])
        old = merged.get(key)
        if old is None:
            merged[key] = {"type": rec["type"], "id": rec["id"], "body": dict(rec["body"])}
            continue
        left = old["body"]
        right = rec["body"]
        for field in set(left) | set(right):
            if field in {"evidence", "evidence_refs", "source_evidence"}:
                a = left.get(field) or []
                b = right.get(field) or []
                if not isinstance(a, list) or not isinstance(b, list):
                    raise ValueError(f"Anchor list-field collision for {rec['id']} field {field}")
                left[field] = sorted(set(a + b))
                continue
            if field not in left:
                left[field] = right[field]
                continue
            if field not in right:
                continue
            if left[field] != right[field]:
                raise ValueError(f"Anchor deterministic ID collision for {rec['id']} field {field}")
    return list(merged.values())


def to_anchor_code(blueprint: dict[str, Any]) -> str:
    header = {
        "schema": ANCHOR_SCHEMA,
        "language": "Anchor Code",
        "version": ANCHOR_LANGUAGE_VERSION,
        "specimen": blueprint.get("specimen", {}),
        "contract": {
            "scan_mode": "READ_ONLY_STATIC",
            "specimen_execution": "FORBIDDEN_BY_DEFAULT",
            "unknown_survives": True,
            "static_runtime_firewall": True,
        },
    }
    rank = {name: index for index, name in enumerate(TYPE_ORDER)}
    records = [(rec, _canon(rec["body"])) for rec in blueprint.get("records", [])]
    records.sort(
        key=lambda item: (
            rank.get(item[0]["type"], 999), item[0]["type"], item[0]["id"], item[1]
        )
    )
    lines = [f"ANCHORCODE\t{ANCHOR_LANGUAGE_VERSION}\t" + _canon(header)]
    lines.extend(rec["type"] + "\t" + rec["id"] + "\t" + body for rec, body in records)
    return "\n".join(lines) + "\n"


def parse_anchor_code(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines:
        raise ValueError("empty Anchor Code")
    header_parts = lines[0].split("\t", 2)
    if len(header_parts) != 3 or header_parts[0] != "ANCHORCODE" or header_parts[1] != ANCHOR_LANGUAGE_VERSION:
        raise ValueError("bad Anchor Code header")
    header = json.loads(header_parts[2])
    if header.get("schema") != ANCHOR_SCHEMA:
        raise ValueError("bad Anchor Code schema")
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for line_no, line in enumerate(lines[1:], 2):
        if not line:
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3 or not parts[0] or not parts[1]:
            raise ValueError(f"bad Anchor statement at line {line_no}")
        body = json.loads(parts[2])
        if not isinstance(body, dict):
            raise ValueError(f"Anchor body must be object at line {line_no}")
        identity = (parts[0], parts[1])
        if identity in seen:
            raise ValueError(f"duplicate Anchor statement id at line {line_no}: {parts[1]}")
        seen.add(identity)
        records.append({"type": parts[0], "id": parts[1], "body": body})
    return {"header": header, "records": records}


def _evidence_kind(evidence_class: str) -> str:
    value = str(evidence_class or "UNKNOWN").upper()
    if value == "INFERRED":
        return "STATICALLY_DERIVED"
    if value in {
        "DIRECT", "STATICALLY_DERIVED", "OBSERVED_RUNTIME", "MEASURED", "REPORTED",
        "CITED", "ASSUMED", "UNKNOWN",
    }:
        return value
    return "UNKNOWN"


def _object_record_type(obj: dict[str, Any]) -> str:
    object_type = str(obj.get("object_type") or "").upper()
    subtype = str(obj.get("subtype") or "").lower()
    coverage = str(obj.get("coverage") or "UNKNOWN").upper()

    if object_type == "EVIDENCE":
        return "EVIDENCE"
    if object_type in TYPE_ORDER:
        return object_type
    if "anchor" in object_type.lower() or "anchor" in subtype:
        return "ANCHOR"
    if "behavior" in object_type.lower() or "behavior" in subtype:
        return "BEHAVIOR"
    if "capability" in subtype or object_type == "CAPABILITY":
        return "CAPABILITY"
    if any(token in subtype for token in ("resource", "persistence", "database", "filesystem", "boundary")):
        return "RESOURCE"
    if any(token in subtype for token in ("state", "lifecycle", "coverage")):
        return "STATE"
    if object_type == "FINDING" and coverage in {"UNKNOWN", "PARTIAL", "BLOCKED"}:
        return "UNKNOWN"
    if object_type == "FINDING":
        return "RESULT"
    return "ENTITY"


def _project_object(obj: dict[str, Any]) -> dict[str, Any]:
    record_type = _object_record_type(obj)
    attributes = dict(obj.get("attributes") or {})
    body: dict[str, Any] = {
        "kind": obj.get("subtype") or obj.get("object_type"),
        "name": obj.get("label"),
        "coverage": obj.get("coverage"),
        "source_object_type": obj.get("object_type"),
        "attributes": attributes or None,
    }
    if record_type == "EVIDENCE":
        body = {
            "kind": _evidence_kind(str(obj.get("subtype") or attributes.get("evidence_class") or "UNKNOWN")),
            "source": attributes.get("path") or attributes.get("source_file_id"),
            "claim": obj.get("label"),
            "extractor": attributes.get("extractor"),
            "excerpt": attributes.get("excerpt"),
            "source_sha256": attributes.get("source_sha256"),
            "line_start": attributes.get("start_line"),
            "line_end": attributes.get("end_line"),
        }
    elif record_type == "UNKNOWN":
        body.update({
            "subject": obj.get("id"),
            "question": obj.get("label"),
            "status": "UNKNOWN" if str(obj.get("coverage")).upper() == "UNKNOWN" else str(obj.get("coverage") or "UNKNOWN").upper(),
        })
    return _record(record_type, str(obj["id"]), **body)


def _relation_type(kind: str) -> str:
    return str(kind or "RELATES_TO").strip().replace("-", "_").replace(" ", "_").upper()


def _build_anchor_blueprint_and_code(
    store, specimen: dict[str, Any], *, engine_version: str, snapshot=None,
) -> tuple[dict[str, Any], str]:
    objects = list(snapshot.objects) if snapshot is not None else store.semantic_objects()
    relations = list(snapshot.relations) if snapshot is not None else store.semantic_relations()
    completeness = list(snapshot.completeness) if snapshot is not None else store.completeness_dimensions()
    records: list[dict[str, Any]] = []

    evidence_ids = {str(obj["id"]) for obj in objects if str(obj.get("object_type")).upper() == "EVIDENCE"}

    for obj in objects:
        if str(obj.get("object_type")).upper() == "GRAPH_RELATION":
            continue
        records.append(_project_object(obj))

    for relation in relations:
        relation_kind_raw = str(relation.get("kind") or "relates_to")
        relation_kind = _relation_type(relation_kind_raw)
        original_evidence = sorted(set(str(x) for x in relation.get("evidence_ids") or [] if str(x) in evidence_ids))
        relation_evidence = list(original_evidence)
        if relation_kind_raw not in PROVENANCE_RELATIONS:
            derived_id = _derived_evidence_id(relation)
            records.append(_record(
                "EVIDENCE", derived_id,
                kind="STATICALLY_DERIVED",
                source=relation.get("id"),
                claim=f"{relation.get('src')} --{relation_kind}--> {relation.get('dst')}",
                source_evidence=original_evidence,
                coverage=relation.get("status"),
                method="SCAN_CANONICAL_GRAPH_PROJECTION",
            ))
            relation_evidence.append(derived_id)

        body: dict[str, Any] = {
            "type": relation_kind,
            "from": relation.get("src"),
            "to": relation.get("dst"),
            "status": relation.get("status"),
            "evidence": sorted(set(relation_evidence)),
            "attributes": relation.get("attributes") or None,
        }
        if relation_kind_raw not in PROVENANCE_RELATIONS or relation_kind in RUNTIME_RELATIONS:
            body["runtime_execution"] = "UNKNOWN"
        records.append(_record("REL", str(relation["id"]), **body))

    for dim in completeness:
        state_id = f"anchor:coverage:{_sha(str(dim.get('id')) + '|' + str(dim.get('state')))[:20]}"
        records.append(_record(
            "STATE", state_id,
            subject=dim.get("id"), name=dim.get("key"), value=dim.get("state"),
            label=dim.get("label"), evidence=dim.get("evidence_ids") or [],
            attributes=dim.get("attributes") or None,
        ))
        if str(dim.get("state") or "UNKNOWN").upper() in {"UNKNOWN", "PARTIAL", "BLOCKED"}:
            question = f"coverage dimension {dim.get('key')} is not fully mapped"
            records.append(_record(
                "UNKNOWN", _unknown_id(str(dim.get("id")), question),
                subject=dim.get("id"), question=question,
                status=str(dim.get("state") or "UNKNOWN").upper(), evidence=dim.get("evidence_ids") or [],
            ))

    records = _merge_records(records)
    specimen_payload = {
        **specimen,
        "scan_mode": "READ_ONLY_STATIC",
        "execution": "FORBIDDEN_BY_DEFAULT",
        "scanner": f"scan-software-body/{engine_version}",
    }
    blueprint = {
        "anchor_version": ANCHOR_LANGUAGE_VERSION,
        "specimen": specimen_payload,
        "records": records,
        "integrity": {
            "semantic_objects_seen": len(objects),
            "semantic_relations_seen": len(relations),
            "completeness_dimensions_seen": len(completeness),
            "record_count": len(records),
            "unknown_count": sum(1 for rec in records if rec["type"] == "UNKNOWN"),
            "static_derived_evidence_count": sum(
                1 for rec in records
                if rec["type"] == "EVIDENCE" and rec["body"].get("kind") == "STATICALLY_DERIVED"
            ),
        },
    }
    anchor_code = to_anchor_code(blueprint)
    parsed = parse_anchor_code(anchor_code)
    if len(parsed["records"]) != len(records):
        raise ValueError("Anchor Code self-validation record count mismatch")
    blueprint["anchor_code_sha256"] = _sha(anchor_code)
    return blueprint, anchor_code


def build_anchor_blueprint(
    store, specimen: dict[str, Any], *, engine_version: str, snapshot=None,
) -> dict[str, Any]:
    blueprint, _ = _build_anchor_blueprint_and_code(
        store, specimen, engine_version=engine_version, snapshot=snapshot,
    )
    return blueprint


def export_anchor_code(
    store, specimen: dict[str, Any], anchor_path: Path, blueprint_path: Path, *, engine_version: str,
    body_map_path: Path | None = None, snapshot=None,
) -> dict[str, Any]:
    blueprint, anchor_code = _build_anchor_blueprint_and_code(
        store, specimen, engine_version=engine_version, snapshot=snapshot,
    )
    anchor_path.write_text(anchor_code, encoding="utf-8")
    blueprint_path.write_text(json.dumps(blueprint, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = {
        "schema": ANCHOR_SCHEMA,
        "version": ANCHOR_LANGUAGE_VERSION,
        "record_count": blueprint["integrity"]["record_count"],
        "unknown_count": blueprint["integrity"]["unknown_count"],
        "static_derived_evidence_count": blueprint["integrity"]["static_derived_evidence_count"],
        "sha256": blueprint["anchor_code_sha256"],
        "file": anchor_path.name,
        "blueprint": blueprint_path.name,
        "runtime_observation_claimed": False,
    }
    if body_map_path is not None and body_map_path.exists():
        payload = json.loads(body_map_path.read_text(encoding="utf-8"))
        payload["anchor_code"] = summary
        semantic = dict(payload.get("semantic_graph") or {})
        projections = list(semantic.get("projections") or [])
        for name in (anchor_path.name, blueprint_path.name):
            if name not in projections:
                projections.append(name)
        semantic["projections"] = projections
        payload["semantic_graph"] = semantic
        body_map_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
