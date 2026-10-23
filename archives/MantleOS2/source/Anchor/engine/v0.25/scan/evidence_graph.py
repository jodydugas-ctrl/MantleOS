from __future__ import annotations

from collections import deque
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Iterable

from .model import stable_id
from .integrity import SEMANTIC_RELATION_KINDS, audit_integrity, effect_closure, surface_closure


# Relations that normally carry justification from evidence/source toward a claim.
PROOF_RELATIONS = {
    "contains_evidence",
    "supports",
    "derived_from",
    "supports_anchor",
}

# Relations that are useful to show during a WHY query but are not positive support.
CONTRADICTION_RELATIONS = {"contradicts"}


def _loads(value: str | None, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _object_row(object_id: str, object_type: str, subtype: str, label: str, *,
                coverage: str = "MAPPED", attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": object_id,
        "object_type": object_type,
        "subtype": subtype,
        "label": label,
        "coverage": coverage,
        "attributes": attributes or {},
    }


def _relation_row(src: str, dst: str, kind: str, *, relation_id: str | None = None,
                  status: str = "MAPPED", attributes: dict[str, Any] | None = None,
                  evidence_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": relation_id or stable_id("semantic-relation", src, kind, dst),
        "src": src,
        "dst": dst,
        "kind": kind,
        "status": status,
        "attributes": attributes or {},
        "evidence_ids": evidence_ids or [],
    }


def build_base_graph(store, specimen: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Project Stage-1 tables into one normalized cross-object semantic/evidence graph.

    The underlying scan tables remain useful for extraction and graph algorithms. This layer gives every
    canonical object a common identity space and makes provenance/dependency relationships traversable.
    """
    files = store.query("SELECT * FROM files ORDER BY path")
    nodes = store.query("SELECT * FROM nodes ORDER BY kind,name,id")
    edges = store.query("SELECT * FROM edges ORDER BY kind,src,dst,id")
    evidence = store.query("SELECT * FROM evidence ORDER BY path,start_line,id")
    findings = store.query("SELECT * FROM findings ORDER BY kind,title,id")
    file_sha = {f["id"]: f.get("sha256") for f in files}

    objects: dict[str, dict[str, Any]] = {}
    relations: dict[str, dict[str, Any]] = {}

    specimen_key = specimen.get("specimen_id") or specimen.get("repository") or specimen.get("root") or "specimen"
    specimen_id = stable_id("specimen", specimen_key, specimen.get("revision") or specimen.get("commit") or specimen.get("tree_sha") or "")
    objects[specimen_id] = _object_row(
        specimen_id, "SPECIMEN", "software-specimen", str(specimen_key),
        attributes={k: v for k, v in specimen.items() if v is not None},
    )

    for f in files:
        attrs = _loads(f.get("attributes_json"), {})
        attrs.update({
            "path": f["path"],
            "size": f["size"],
            "sha256": f.get("sha256"),
            "language": f.get("language"),
            "content_available": bool(f.get("content_available")),
            "acquisition_state": f.get("acquisition_state"),
            "provider": f.get("provider"),
            "provider_object_id": f.get("provider_object_id"),
            "provider_digest_algorithm": f.get("provider_digest_algorithm"),
        })
        objects[f["id"]] = _object_row(f["id"], "FILE", "source-artifact", f["path"], coverage=f["coverage"], attributes=attrs)
        rel = _relation_row(specimen_id, f["id"], "contains")
        relations[rel["id"]] = rel

    for ev in evidence:
        attrs = {
            "path": ev["path"],
            "start_line": ev.get("start_line"),
            "end_line": ev.get("end_line"),
            "evidence_class": ev["evidence_class"],
            "extractor": ev["extractor"],
            "excerpt": ev.get("excerpt"),
            "source_file_id": ev["file_id"],
            "source_sha256": file_sha.get(ev["file_id"]),
        }
        label = f"{ev['evidence_class']} evidence @ {ev['path']}"
        objects[ev["id"]] = _object_row(ev["id"], "EVIDENCE", ev["evidence_class"], label, attributes=attrs)
        rel = _relation_row(ev["file_id"], ev["id"], "contains_evidence")
        relations[rel["id"]] = rel

    for n in nodes:
        attrs = _loads(n.get("attributes_json"), {})
        attrs.update({"path": n.get("path"), "file_id": n.get("file_id")})
        objects[n["id"]] = _object_row(n["id"], "ANATOMICAL_OBJECT", n["kind"], n["name"], coverage=n["coverage"], attributes=attrs)
        if n.get("file_id"):
            rel = _relation_row(n["file_id"], n["id"], "derived_from")
            relations[rel["id"]] = rel
        for ev_id in _loads(n.get("evidence_ids_json"), []):
            rel = _relation_row(ev_id, n["id"], "supports")
            relations[rel["id"]] = rel

    # Each extracted structural edge is itself addressable as a semantic claim object, while the direct
    # src->dst relation remains queryable under the edge's original stable ID.
    for e in edges:
        attrs = _loads(e.get("attributes_json"), {})
        ev_ids = _loads(e.get("evidence_ids_json"), [])
        edge_object_id = stable_id("relation-claim", e["id"])
        objects[edge_object_id] = _object_row(
            edge_object_id, "GRAPH_RELATION", e["kind"], f"{e['src']} --{e['kind']}--> {e['dst']}",
            coverage=e["coverage"], attributes={"edge_id": e["id"], "src": e["src"], "dst": e["dst"], **attrs},
        )
        direct = _relation_row(
            e["src"], e["dst"], e["kind"], relation_id=e["id"], status=e["coverage"],
            attributes={"claim_object_id": edge_object_id, **attrs}, evidence_ids=ev_ids,
        )
        relations[direct["id"]] = direct
        src_rel = _relation_row(e["src"], edge_object_id, "source_of")
        dst_rel = _relation_row(edge_object_id, e["dst"], "targets")
        relations[src_rel["id"]] = src_rel
        relations[dst_rel["id"]] = dst_rel
        for ev_id in ev_ids:
            rel = _relation_row(ev_id, edge_object_id, "supports")
            relations[rel["id"]] = rel

    for f in findings:
        attrs = _loads(f.get("attributes_json"), {})
        ev_ids = _loads(f.get("evidence_ids_json"), [])
        objects[f["id"]] = _object_row(f["id"], "FINDING", f["kind"], f["title"], coverage=f["status"], attributes=attrs)
        for ev_id in ev_ids:
            rel = _relation_row(ev_id, f["id"], "supports")
            relations[rel["id"]] = rel

    return list(objects.values()), list(relations.values())


def compute_completeness(store, audit: dict[str, Any] | None = None, closure: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Create a conservative multidimensional completeness vector.

    These are machine Stage-1 dimensions, not a global completion percentage. Higher stages may add more
    dimensions or refine these states through semantic overlays.
    """
    files = store.query("SELECT * FROM files")
    nodes = store.query("SELECT * FROM nodes")
    edges = store.query("SELECT * FROM edges")
    findings = store.query("SELECT * FROM findings")
    audit = audit or {"state": "UNKNOWN", "severity_counts": {}}
    closure = closure or surface_closure(store)

    file_count = len(files)
    unavailable = sum(1 for f in files if not f.get("content_available"))
    blocked = sum(1 for f in files if f.get("coverage") == "BLOCKED")
    partial = sum(1 for f in files if f.get("coverage") == "PARTIAL")

    cpp_source_suffixes = {".c", ".cc", ".cpp", ".cxx", ".c++", ".m", ".mm"}
    cpp_tus = [f for f in files if f.get("language") in {"C", "C++"} and Path(f.get("path") or "").suffix.lower() in cpp_source_suffixes and f.get("content_available")]
    clang_success_files = {n.get("file_id") for n in nodes if n.get("kind") == "parser_result" and n.get("name") == "clang_ast" and n.get("coverage") == "MAPPED"}
    clang_partial_files = {n.get("file_id") for n in nodes if n.get("kind") == "parser_result" and n.get("name") == "clang_ast" and n.get("coverage") == "PARTIAL"}
    if not cpp_tus:
        clang_state = "UNKNOWN"
    elif len(clang_success_files) == len(cpp_tus):
        clang_state = "MAPPED"
    elif clang_success_files or clang_partial_files:
        clang_state = "PARTIAL"
    else:
        clang_state = "BLOCKED"

    def state_for_acquisition() -> str:
        if file_count == 0:
            return "UNKNOWN"
        if unavailable == 0:
            return "MAPPED"
        if blocked:
            return "BLOCKED"
        return "PARTIAL"

    def has_node(*kinds: str) -> bool:
        return any(n["kind"] in kinds for n in nodes)

    def has_edge(*kinds: str) -> bool:
        return any(e["kind"] in kinds for e in edges)

    dimensions = [
        ("identity", "Specimen identity/fingerprint", "MAPPED" if file_count else "UNKNOWN", None, {}),
        ("acquisition", "Verified specimen byte acquisition", state_for_acquisition(), None,
         {"file_count": file_count, "content_unavailable": unavailable, "blocked": blocked}),
        ("file-census", "Visible file/body census", "MAPPED" if file_count else "UNKNOWN", None,
         {"file_count": file_count}),
        ("parser-coverage", "Parser-eligible content coverage",
         "MAPPED" if file_count and unavailable == 0 and blocked == 0 and partial == 0 else ("BLOCKED" if blocked else "PARTIAL" if file_count else "UNKNOWN"),
         None, {"partial_files": partial, "blocked_files": blocked}),
        ("scan-resource-budget", "Aggregate scan resource/cancellation coverage",
         "PARTIAL" if any(f.get("kind") == "scan_budget" for f in findings) or any(str(f.get("acquisition_state") or "").startswith("RESOURCE_LIMIT_TOTAL") for f in files) else "MAPPED",
         "parser-coverage", {
             "budget_findings": sum(1 for f in findings if f.get("kind") == "scan_budget"),
             "inventory_budget_limited_files": sum(1 for f in files if str(f.get("acquisition_state") or "").startswith("RESOURCE_LIMIT_TOTAL")),
             "meaning": "MAPPED means configured aggregate ceilings did not truncate the scan; PARTIAL preserves explicit bounded coverage",
         }),
        ("cpp-compiler-ast", "Compiler-assisted C/C++ AST coverage", clang_state, "parser-coverage",
         {"translation_units": len(cpp_tus), "compiler_ast_mapped": len(clang_success_files),
          "compiler_ast_partial": len(clang_partial_files),
          "meaning": "BLOCKED/PARTIAL does not suppress conservative fallback extraction"}),
        ("cpp-type-dispatch", "Compiler-assisted type/inheritance/dispatch evidence",
         "PARTIAL" if has_node("type_symbol", "type_reference") else "UNKNOWN", "cpp-compiler-ast",
         {"type_symbols": sum(1 for n in nodes if n.get("kind") == "type_symbol"),
          "virtual_dispatch_candidates": sum(1 for e in edges if e.get("kind") == "virtual_dispatch_candidate")}),
        ("conditional-compilation", "Preprocessor/conditional-compilation provenance",
         "PARTIAL" if has_node("conditional_compilation", "preprocessor_macro") else "UNKNOWN", "parser-coverage",
         {"meaning": "directives recorded; exhaustive branch truth requires full build/config context"}),
        ("qt-generated-code", "Qt generated-code contracts (moc/uic/rcc)",
         "PARTIAL" if has_node("generated_code_receptor", "generated_build_contract", "generated_input") else "UNKNOWN", "parser-coverage",
         {"meaning": "generation contracts mapped without executing specimen build scripts"}),
        ("scintilla-lexilla-coupling", "Scintilla/Lexilla framework capability coupling",
         "PARTIAL" if has_node("framework_capability", "framework_event", "framework_coupling") else "UNKNOWN", "human-surfaces",
         {"framework_capabilities": sum(1 for n in nodes if n.get("kind") == "framework_capability"),
          "framework_events": sum(1 for n in nodes if n.get("kind") == "framework_event")}),
        ("symbols", "Symbol/anatomy extraction", "PARTIAL" if nodes else "UNKNOWN", None,
         {"node_count": len(nodes)}),
        ("structural-graph", "Structural edge graph", "PARTIAL" if edges else "UNKNOWN", None,
         {"edge_count": len(edges)}),
        ("events", "Event/signal/callback pathways", "PARTIAL" if has_edge("dispatches_to", "emits", "connects_to") else "UNKNOWN", "structural-graph", {}),
        ("human-surfaces", "Human interaction surfaces", "PARTIAL" if has_node("human_surface", "surface_reference", "surface_factory_output") else "UNKNOWN", None, {"surface_count": closure.get("surface_count", 0)}),
        ("human-surface-bindings", "Mechanical surface-to-handler/route closure", closure.get("state", "UNKNOWN"), "human-surfaces", {"bound": closure.get("bound_count", 0), "partial": closure.get("partial_count", 0), "unresolved": closure.get("unresolved_count", 0)}),
        ("evidence-integrity", "Canonical evidence-graph referential/provenance integrity", audit.get("state", "UNKNOWN"), None, {"severity_counts": audit.get("severity_counts", {}), "issue_count": audit.get("issue_count", 0)}),
        ("recurrence", "Loop/timer/recurrence coverage", "PARTIAL" if has_node("recurrence_source") else "UNKNOWN", None, {}),
        ("nest-boundaries", "NEST/ecosystem boundaries", "PARTIAL" if has_node("nest_boundary", "nest_condition") else "UNKNOWN", None, {}),
        ("capability-provenance", "Mechanically supported BODY/NEST capability provenance",
         "PARTIAL" if has_node("effect", "nest_boundary", "extension_receptor", "framework_capability") else "UNKNOWN", "nest-boundaries",
         {"typed_effects": sum(1 for n in nodes if n.get("kind") == "effect" and "compiler_typed" in str(n.get("attributes_json") or "")),
          "extension_receptors": sum(1 for n in nodes if n.get("kind") == "extension_receptor")}),
        ("persistence-paths", "Persistence providers and durable-operation pathways",
         "PARTIAL" if has_node("persistence_provider", "persistence_operation") else "UNKNOWN", None,
         {"providers": sum(1 for n in nodes if n.get("kind") == "persistence_provider"),
          "operations": sum(1 for n in nodes if n.get("kind") == "persistence_operation"),
          "state_persistence_candidates": sum(1 for e in edges if e.get("kind") == "persistence_candidate")}),
        ("guard-error-cancel", "Guards, exception/error, cancel and retry pathways",
         "PARTIAL" if has_node("guard", "error_path", "control_exit", "retry_path_candidate") or any(n.get("kind") == "effect" and any(tok in str(n.get("name") or "") for tok in ("cancel", "error", "permission")) for n in nodes) else "UNKNOWN", None,
         {"guards": sum(1 for n in nodes if n.get("kind") == "guard"),
          "error_paths": sum(1 for n in nodes if n.get("kind") == "error_path"),
          "control_exits": sum(1 for n in nodes if n.get("kind") == "control_exit"),
          "retry_candidates": sum(1 for n in nodes if n.get("kind") == "retry_path_candidate")}),
        ("permission-guards", "Permission/availability checks and permission-changing operations",
         "PARTIAL" if any(n.get("kind") == "effect" and "permission" in str(n.get("name") or "") for n in nodes) or any(n.get("kind") == "guard" and "permissions_or_availability" in str(n.get("attributes_json") or "") for n in nodes) else "UNKNOWN", "guard-error-cancel", {}),
        ("extension-receptors", "Extension/add-on/script receptors and capability factories",
         "PARTIAL" if has_node("extension_receptor_candidate", "extension_receptor", "capability_factory") else "UNKNOWN", None,
         {"mapped_receptors": sum(1 for n in nodes if n.get("kind") == "extension_receptor"),
          "candidate_receptors": sum(1 for n in nodes if n.get("kind") == "extension_receptor_candidate"),
          "capability_factories": sum(1 for n in nodes if n.get("kind") == "capability_factory")}),
        ("lifecycle", "Lifecycle state/transition closure", "UNKNOWN", None, {"reason": "requires Stage 2+ synthesis"}),
        ("reconstruction-anchors", "Reconstruction anchor traceability", "UNKNOWN", None, {"reason": "requires derived semantic overlay"}),
    ]

    # Denominator-driven subdimensions make breadth gaps visible without collapsing them into a
    # single human-surface percentage. Surface types are discovered from the specimen itself.
    for surface_type, counts in sorted((closure.get("by_surface_type") or {}).items()):
        total = counts.get("total", 0)
        unresolved_n = counts.get("UNRESOLVED", 0)
        partial_n = counts.get("PARTIAL", 0)
        state = "MAPPED" if total and not unresolved_n and not partial_n else ("PARTIAL" if total else "UNKNOWN")
        key = "human-surfaces/" + str(surface_type).replace(" ", "_").replace("/", "_")
        dimensions.append((
            key, f"Human-surface closure: {surface_type}", state, "human-surfaces",
            {"total": total, "bound": counts.get("BOUND", 0), "partial": partial_n, "unresolved": unresolved_n},
        ))

    out = []
    ids = {key: stable_id("coverage-dimension", key) for key, *_ in dimensions}
    for key, label, state, parent_key, attrs in dimensions:
        out.append({
            "id": ids[key],
            "key": key,
            "label": label,
            "state": state,
            "parent_id": ids.get(parent_key) if parent_key else None,
            "attributes": attrs,
            "evidence_ids": [],
        })
    return out


def persist_base_graph(store, specimen: dict[str, Any]) -> dict[str, int]:
    objects, relations = build_base_graph(store, specimen)
    store.put_semantic_objects(objects)
    store.put_semantic_relations(relations)
    # Audit after the base graph exists so completeness can depend on mechanical integrity/closure.
    audit = audit_integrity(store)
    closure = surface_closure(store)
    deep = effect_closure(store)
    completeness = compute_completeness(store, audit=audit, closure=closure)
    store.put_completeness(completeness)
    return {
        "objects": len(objects),
        "relations": len(relations),
        "completeness_dimensions": len(completeness),
        "integrity_state": audit.get("state"),
        "integrity_issue_count": audit.get("issue_count", 0),
        "surface_closure_state": closure.get("state"),
        "effect_closure_state": deep.get("state"),
    }


def load_overlay(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "scan-semantic-overlay/0.1":
        raise ValueError(f"unsupported semantic overlay schema: {payload.get('schema_version')!r}")
    return payload


def ingest_overlay(store, payload: dict[str, Any]) -> dict[str, int]:
    """Ingest derived interpretations/behaviors/anchors while preserving cross-object references.

    This is intentionally data-only. It does not grant an interpretation the authority of source evidence.
    """
    objects = []
    for x in payload.get("objects", []):
        required = {"id", "object_type", "subtype", "label"}
        missing = required - set(x)
        if missing:
            raise ValueError(f"semantic object missing fields {sorted(missing)}: {x!r}")
        objects.append({
            "id": str(x["id"]),
            "object_type": str(x["object_type"]),
            "subtype": str(x["subtype"]),
            "label": str(x["label"]),
            "coverage": str(x.get("coverage", "UNKNOWN")),
            "attributes": dict(x.get("attributes") or {}),
        })

    relations = []
    for x in payload.get("relations", []):
        required = {"src", "dst", "kind"}
        missing = required - set(x)
        if missing:
            raise ValueError(f"semantic relation missing fields {sorted(missing)}: {x!r}")
        kind = str(x["kind"])
        if kind not in SEMANTIC_RELATION_KINDS:
            raise ValueError(f"unsupported semantic overlay relation kind {kind!r}; use the typed relation vocabulary")
        relations.append(_relation_row(
            str(x["src"]), str(x["dst"]), str(x["kind"]),
            relation_id=str(x.get("id") or stable_id("semantic-relation", x["src"], x["kind"], x["dst"])),
            status=str(x.get("status", "MAPPED")), attributes=dict(x.get("attributes") or {}),
            evidence_ids=[str(v) for v in x.get("evidence_ids", [])],
        ))

    completeness = []
    for x in payload.get("completeness", []):
        required = {"key", "label", "state"}
        missing = required - set(x)
        if missing:
            raise ValueError(f"completeness dimension missing fields {sorted(missing)}: {x!r}")
        completeness.append({
            "id": str(x.get("id") or stable_id("coverage-dimension", x["key"])),
            "key": str(x["key"]), "label": str(x["label"]), "state": str(x["state"]),
            "parent_id": x.get("parent_id"), "attributes": dict(x.get("attributes") or {}),
            "evidence_ids": [str(v) for v in x.get("evidence_ids", [])],
        })

    existing_ids = {r["id"] for r in store.query("SELECT id FROM semantic_objects")}
    incoming_ids = {o["id"] for o in objects}
    valid_ids = existing_ids | incoming_ids
    dangling = sorted({r[side] for r in relations for side in ("src", "dst") if r[side] not in valid_ids})
    if dangling:
        raise ValueError(f"semantic overlay contains dangling object references: {dangling[:20]}")

    store.put_semantic_bundle(objects, relations, completeness)
    return {"objects": len(objects), "relations": len(relations), "completeness_dimensions": len(completeness)}




def refresh_machine_body_map_projection(store, output_path: Path) -> dict[str, Any] | None:
    """Refresh semantic/completeness fields in an existing Machine Body Map after overlays.

    The Stage-1 inventory/extraction tables remain unchanged, but semantic object counts and
    completeness must not silently lag behind the canonical store.
    """
    if not output_path.exists():
        return None
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    sem_objects = store.semantic_objects()
    sem_relations = store.semantic_relations()
    dims = store.completeness_dimensions()
    audit = audit_integrity(store)
    closure = surface_closure(store)
    deep = effect_closure(store)
    sem = dict(payload.get("semantic_graph") or {})
    sem.update({
        "objects": len(sem_objects),
        "relations": len(sem_relations),
        "completeness_dimensions": len(dims),
        "canonical_store": "scan_index.sqlite",
    })
    payload["semantic_graph"] = sem
    payload["completeness_vector"] = dims
    payload["integrity"] = {k: v for k, v in audit.items() if k != "issues"}
    payload["surface_closure"] = {k: v for k, v in closure.items() if k != "records"}
    payload["effect_closure"] = {k: v for k, v in deep.items() if k != "records"}
    payload["semantic_projection_refreshed"] = True
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload

def export_evidence_graph(store, specimen: dict[str, Any], output_path: Path) -> dict[str, Any]:
    objects = store.semantic_objects()
    relations = store.semantic_relations()
    completeness = store.completeness_dimensions()
    payload = {
        "schema_version": "scan-evidence-graph/0.2",
        "specimen": specimen,
        "object_count": len(objects),
        "relation_count": len(relations),
        "objects": objects,
        "relations": relations,
        "completeness_vector": completeness,
        "semantics": {
            "canonical_store": "scan_index.sqlite",
            "this_file": "lossless interchange projection of canonical semantic graph tables",
            "friendly_maps": "projections; not independent authorities",
            "proof_direction": "source/evidence -> supported claim -> interpretation -> reconstruction anchor",
        },
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def export_evidence_catalog(store, output_path: Path) -> dict[str, Any]:
    rows = store.query("""
        SELECT e.*, f.sha256 AS source_sha256, f.provider_object_id AS provider_object_id
        FROM evidence e LEFT JOIN files f ON f.id=e.file_id
        ORDER BY e.path,e.start_line,e.id
    """)
    records = []
    for ev in rows:
        supports = store.query(
            "SELECT id,dst,kind,status FROM semantic_relations WHERE src=? AND kind IN ('supports','supports_anchor') ORDER BY kind,dst",
            (ev["id"],),
        )
        records.append({
            "id": ev["id"], "type": ev["evidence_class"],
            "source": {"file_id": ev["file_id"], "path": ev["path"], "start_line": ev["start_line"], "end_line": ev["end_line"], "sha256": ev.get("source_sha256"), "provider_object_id": ev.get("provider_object_id")},
            "extractor": ev["extractor"], "excerpt": ev["excerpt"], "supports": supports,
        })
    payload = {"schema_version": "scan-evidence-catalog/0.2", "records": records}
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def export_completeness(store, output_path: Path) -> dict[str, Any]:
    dims = store.completeness_dimensions()
    payload = {
        "schema_version": "scan-completeness-vector/0.2",
        "rule": "No single completion percentage replaces anatomical coverage dimensions.",
        "dimensions": dims,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def trace_why(store, object_id: str, max_depth: int = 8) -> dict[str, Any]:
    """Walk backward from a claim toward source/evidence support and show contradictions."""
    obj = store.semantic_object(object_id)
    if obj is None:
        raise KeyError(object_id)

    visited = {object_id}
    queue = deque([(object_id, 0)])
    objects = {object_id: obj}
    relations = []
    contradictions = []

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        incoming = store.incoming_semantic_relations(current)
        for rel in incoming:
            if rel["kind"] in CONTRADICTION_RELATIONS:
                contradictions.append(rel)
                src_obj = store.semantic_object(rel["src"])
                if src_obj:
                    objects[src_obj["id"]] = src_obj
                continue
            if rel["kind"] not in PROOF_RELATIONS:
                continue
            relations.append(rel)
            src = rel["src"]
            src_obj = store.semantic_object(src)
            if src_obj:
                objects[src] = src_obj
            if src not in visited:
                visited.add(src)
                queue.append((src, depth + 1))

    object_values = list(objects.values())
    evidence_reached = sorted(o["id"] for o in object_values if o.get("object_type") == "EVIDENCE")
    source_files_reached = sorted(o["id"] for o in object_values if o.get("object_type") == "FILE")
    return {
        "query": "why", "target": object_id, "max_depth": max_depth,
        "objects": object_values, "proof_relations": relations,
        "contradictions": contradictions,
        "evidence_reached": evidence_reached,
        "source_files_reached": source_files_reached,
        "proof_complete": bool(evidence_reached),
    }


def trace_impact(store, object_id: str, max_depth: int = 8) -> dict[str, Any]:
    """Walk forward from a source/evidence object through dependent semantic claims."""
    obj = store.semantic_object(object_id)
    if obj is None:
        raise KeyError(object_id)

    visited = {object_id}
    queue = deque([(object_id, 0)])
    objects = {object_id: obj}
    relations = []
    allowed = PROOF_RELATIONS | {"contradicts"}

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        outgoing = store.outgoing_semantic_relations(current)
        for rel in outgoing:
            if rel["kind"] not in allowed:
                continue
            relations.append(rel)
            dst = rel["dst"]
            dst_obj = store.semantic_object(dst)
            if dst_obj:
                objects[dst] = dst_obj
            if dst not in visited:
                visited.add(dst)
                queue.append((dst, depth + 1))

    object_values = list(objects.values())
    anchors_reached = sorted(o["id"] for o in object_values if o.get("object_type") == "RECONSTRUCTION_ANCHOR")
    return {
        "query": "impact", "source": object_id, "max_depth": max_depth,
        "objects": object_values, "dependency_relations": relations,
        "reconstruction_anchors_reached": anchors_reached,
    }
