from __future__ import annotations

from collections import defaultdict, deque
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .model import stable_id

# Overlay-facing relation vocabulary. Extraction-specific structural relations remain open because
# substrate adapters may introduce additional mechanically named edge kinds.
SEMANTIC_RELATION_KINDS = {
    "supports",
    "derived_from",
    "contradicts",
    "enters",
    "observed_by",
    "requires",
    "supports_anchor",
    "contains",
    "contains_evidence",
    "source_of",
    "targets",
    "alternate_route_to",
    "implements",
    "produces_feedback",
    "changes_state",
    "crosses_boundary",
}

PROOF_RELATION_KINDS = {"contains_evidence", "supports", "derived_from", "supports_anchor"}
CLAIM_OBJECT_TYPES = {
    "INTERPRETATION",
    "BEHAVIOR",
    "ARTERY",
    "NERVE",
    "CAPABILITY",
    "RECONSTRUCTION_ANCHOR",
}


def _decode_json(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _has_evidence_path(store, object_id: str, max_depth: int = 12) -> bool:
    """Return True when a positive proof walk reaches a first-class evidence object."""
    visited = {object_id}
    queue = deque([(object_id, 0)])
    while queue:
        current, depth = queue.popleft()
        obj = store.semantic_object(current)
        if obj and obj["object_type"] == "EVIDENCE":
            return True
        if depth >= max_depth:
            continue
        for rel in store.incoming_semantic_relations(current):
            if rel["kind"] not in PROOF_RELATION_KINDS:
                continue
            src = rel["src"]
            if src not in visited:
                visited.add(src)
                queue.append((src, depth + 1))
    return False


def _proof_cycles(objects: set[str], relations: list[dict[str, Any]]) -> list[list[str]]:
    """Find cycles in the positive proof subgraph using DFS.

    Cycles are not automatically corrupt, but they are suspicious because proof should normally flow
    from source/evidence toward increasingly derived claims.
    """
    graph: dict[str, list[str]] = defaultdict(list)
    for rel in relations:
        if rel["kind"] in PROOF_RELATION_KINDS and rel["src"] in objects and rel["dst"] in objects:
            graph[rel["src"]].append(rel["dst"])

    state: dict[str, int] = {}
    stack: list[str] = []
    index: dict[str, int] = {}
    cycles: list[list[str]] = []
    seen_cycle_keys: set[tuple[str, ...]] = set()

    def visit(node: str):
        state[node] = 1
        index[node] = len(stack)
        stack.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt, 0) == 0:
                visit(nxt)
            elif state.get(nxt) == 1:
                cyc = stack[index[nxt]:] + [nxt]
                # canonicalize by object set so repeated traversal does not duplicate the same cycle
                key = tuple(sorted(set(cyc)))
                if key not in seen_cycle_keys:
                    seen_cycle_keys.add(key)
                    cycles.append(cyc)
        stack.pop()
        index.pop(node, None)
        state[node] = 2

    for node in sorted(objects):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def surface_closure(store) -> dict[str, Any]:
    """Measure denominator-driven human-surface route closure.

    v0.2 walks a small deterministic routing graph instead of assuming every binding is at most two
    edges away. This lets declarations resolve through cross-file UI references, shortcut aliases,
    signals, helper dispatch and handler references without turning unresolved framework behavior into
    a fabricated route.
    """
    surfaces = store.query(
        "SELECT id,kind,name,path,coverage,attributes_json FROM nodes "
        "WHERE kind IN ('human_surface','surface_reference','surface_factory_output') ORDER BY path,name,id"
    )
    nodes = {r["id"]: r for r in store.query("SELECT id,kind,name,coverage,attributes_json FROM nodes")}
    edges = store.query("SELECT id,src,dst,kind,coverage,attributes_json,evidence_ids_json FROM edges ORDER BY src,kind,dst,id")
    by_src: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        by_src[edge["src"]].append(edge)

    routing_kinds = {
        "resolves_to", "alternate_route_to", "emits", "dispatches_to", "invokes",
        "triggers", "routes_to", "opens_surface",
    }
    actionable_kinds = {"handler_reference", "symbol", "input_consumer"}
    max_depth = 6
    records = []
    bound = unresolved = partial = 0
    presented_surface_count = 0
    by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "BOUND": 0, "PARTIAL": 0, "UNRESOLVED": 0})

    for row in surfaces:
        attrs = _decode_json(row.get("attributes_json"), {})
        # Binding closure measures actionable entrance surfaces. Presented/output surfaces (for example
        # a message dialog opened by a handler) are effect/feedback terminals, not independent entry
        # controls unless a deeper adapter explicitly models their internal controls.
        if attrs.get("surface_role") == "presented":
            presented_surface_count += 1
            continue
        queue = deque([(row["id"], 0, [])])
        visited = {row["id"]}
        route_edges: list[dict[str, Any]] = []
        reachable_handlers: list[dict[str, Any]] = []
        best_paths: list[list[dict[str, Any]]] = []

        while queue:
            current, depth, path = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in by_src.get(current, []):
                if edge["kind"] not in routing_kinds:
                    continue
                route_edges.append(edge)
                step = {"edge_id": edge["id"], "kind": edge["kind"], "src": edge["src"], "dst": edge["dst"], "coverage": edge["coverage"]}
                new_path = path + [step]
                dst = nodes.get(edge["dst"])
                if dst and dst["kind"] in actionable_kinds:
                    reachable_handlers.append({"id": dst["id"], "kind": dst["kind"], "name": dst["name"], "coverage": dst["coverage"]})
                    best_paths.append(new_path)
                if edge["dst"] not in visited:
                    visited.add(edge["dst"])
                    queue.append((edge["dst"], depth + 1, new_path))

        if reachable_handlers:
            status = "BOUND"
            bound += 1
        elif route_edges:
            status = "PARTIAL"
            partial += 1
        else:
            status = "UNRESOLVED"
            unresolved += 1
        surface_type = attrs.get("surface_type") or row["kind"]
        by_type[str(surface_type)]["total"] += 1
        by_type[str(surface_type)][status] += 1
        records.append({
            "surface_id": row["id"],
            "name": row["name"],
            "kind": row["kind"],
            "path": row["path"],
            "coverage": row["coverage"],
            "surface_type": surface_type,
            "surface_role": attrs.get("surface_role", "input"),
            "closure": status,
            "route_edge_count": len({e["id"] for e in route_edges}),
            "reachable_handlers": sorted({h["id"]: h for h in reachable_handlers}.values(), key=lambda x: (x["name"], x["id"])),
            "example_route": min(best_paths, key=len) if best_paths else [],
        })
    total = len(records)
    state = "UNKNOWN" if total == 0 else "MAPPED" if unresolved == 0 and partial == 0 else "PARTIAL"
    return {
        "schema_version": "scan-surface-closure/0.3",
        "state": state,
        "surface_count": total,
        "presented_surface_count": presented_surface_count,
        "bound_count": bound,
        "partial_count": partial,
        "unresolved_count": unresolved,
        "closure_ratio": (bound / total) if total else None,
        "by_surface_type": dict(sorted(by_type.items())),
        "records": records,
    }


def audit_integrity(store, *, proof_depth: int = 12) -> dict[str, Any]:
    """Audit the canonical evidence graph for R1 integrity failures.

    The audit never repairs data silently. It reports concrete issues that can be turned into scanner
    findings, tests, or deeper extraction work.
    """
    objects_list = store.semantic_objects()
    relations = store.semantic_relations()
    objects = {o["id"]: o for o in objects_list}
    ids = set(objects)
    issues: list[dict[str, Any]] = []

    def add(code: str, severity: str, message: str, **attrs):
        issues.append({"id": stable_id("integrity-issue", code, message, json.dumps(attrs, sort_keys=True, default=str)),
                       "code": code, "severity": severity, "message": message, "attributes": attrs})

    # Referential integrity for semantic relations and their direct evidence references.
    for rel in relations:
        if rel["src"] not in ids:
            add("DANGLING_RELATION_SOURCE", "ERROR", f"Relation {rel['id']} source is missing", relation_id=rel["id"], object_id=rel["src"])
        if rel["dst"] not in ids:
            add("DANGLING_RELATION_TARGET", "ERROR", f"Relation {rel['id']} target is missing", relation_id=rel["id"], object_id=rel["dst"])
        for ev_id in rel.get("evidence_ids", []):
            ev = objects.get(ev_id)
            if ev is None:
                add("DANGLING_RELATION_EVIDENCE", "ERROR", f"Relation {rel['id']} references missing evidence", relation_id=rel["id"], evidence_id=ev_id)
            elif ev.get("object_type") != "EVIDENCE":
                add("NON_EVIDENCE_REFERENCE", "ERROR", f"Relation {rel['id']} evidence_ids contains a non-evidence object", relation_id=rel["id"], evidence_id=ev_id, object_type=ev.get("object_type"))

    # Evidence provenance must terminate in an extant FILE object and retain the source digest that
    # was current when the graph projection was constructed.
    for obj in objects_list:
        if obj["object_type"] != "EVIDENCE":
            continue
        attrs = obj.get("attributes") or {}
        file_id = attrs.get("source_file_id")
        file_obj = objects.get(file_id) if file_id else None
        if file_obj is None or file_obj.get("object_type") != "FILE":
            add("EVIDENCE_SOURCE_MISSING", "ERROR", f"Evidence {obj['id']} has no valid source file object", evidence_id=obj["id"], source_file_id=file_id)
        else:
            expected = attrs.get("source_sha256")
            actual = (file_obj.get("attributes") or {}).get("sha256")
            if expected and actual and expected != actual:
                add("EVIDENCE_SOURCE_DIGEST_MISMATCH", "ERROR", f"Evidence {obj['id']} source digest no longer matches FILE object", evidence_id=obj["id"], expected=expected, actual=actual, source_file_id=file_id)

        downstream = [r for r in store.outgoing_semantic_relations(obj["id"]) if r["kind"] in {"supports", "supports_anchor", "derived_from"}]
        if not downstream:
            add("ORPHAN_EVIDENCE", "WARN", f"Evidence {obj['id']} supports no extracted or semantic claim", evidence_id=obj["id"])

    # Claim-bearing objects should have a positive proof path to source evidence. The audit makes this
    # a mechanical property instead of relying on a well-written label.
    for obj in objects_list:
        if obj["object_type"] not in CLAIM_OBJECT_TYPES:
            continue
        if not _has_evidence_path(store, obj["id"], max_depth=proof_depth):
            severity = "ERROR" if obj["object_type"] == "RECONSTRUCTION_ANCHOR" else "WARN"
            add("CLAIM_WITHOUT_EVIDENCE_PATH", severity,
                f"{obj['object_type']} {obj['id']} has no positive proof path to EVIDENCE",
                object_id=obj["id"], object_type=obj["object_type"], proof_depth=proof_depth)

    # Completeness hierarchy must itself be referentially valid.
    completeness = store.completeness_dimensions()
    dim_ids = {d["id"] for d in completeness}
    for dim in completeness:
        if dim.get("parent_id") and dim["parent_id"] not in dim_ids:
            add("DANGLING_COMPLETENESS_PARENT", "ERROR", f"Completeness dimension {dim['key']} references missing parent", dimension_id=dim["id"], parent_id=dim["parent_id"])
        for ev_id in dim.get("evidence_ids", []):
            if ev_id not in ids:
                add("DANGLING_COMPLETENESS_EVIDENCE", "ERROR", f"Completeness dimension {dim['key']} references missing evidence", dimension_id=dim["id"], evidence_id=ev_id)

    for cycle in _proof_cycles(ids, relations):
        add("PROOF_CYCLE", "WARN", "Positive proof relations contain a cycle", cycle=cycle)

    severity_counts: dict[str, int] = defaultdict(int)
    code_counts: dict[str, int] = defaultdict(int)
    for issue in issues:
        severity_counts[issue["severity"]] += 1
        code_counts[issue["code"]] += 1

    surface = surface_closure(store)
    state = "BLOCKED" if severity_counts.get("ERROR", 0) else "PARTIAL" if severity_counts.get("WARN", 0) else "MAPPED"
    return {
        "schema_version": "scan-integrity-report/0.1",
        "state": state,
        "issue_count": len(issues),
        "severity_counts": dict(sorted(severity_counts.items())),
        "code_counts": dict(sorted(code_counts.items())),
        "surface_closure": {
            "state": surface["state"],
            "surface_count": surface["surface_count"],
            "bound_count": surface["bound_count"],
            "partial_count": surface["partial_count"],
            "unresolved_count": surface["unresolved_count"],
        },
        "issues": issues,
    }


def write_integrity_outputs(store, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    audit = audit_integrity(store)
    closure = surface_closure(store)
    deep = effect_closure(store)
    (output / "integrity_report.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "surface_closure.json").write_text(json.dumps(closure, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "effect_closure.json").write_text(json.dumps(deep, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"integrity": audit, "surface_closure": closure, "effect_closure": deep}


def write_projection_manifest(output: Path, names: list[str]) -> dict[str, Any]:
    """Write hashes/countable metadata for canonical projection files.

    The manifest does not make a projection authoritative. It proves which exact exported bytes were
    emitted together and lets downstream tooling detect accidental divergence or stale copies.
    """
    files = []
    for name in names:
        path = output / name
        if not path.exists():
            continue
        data = path.read_bytes()
        files.append({"name": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    payload = {
        "schema_version": "scan-projection-manifest/0.1",
        "canonical_store": "scan_index.sqlite",
        "projections": files,
    }
    (output / "projection_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def refinement_completeness_updates(store, audit: dict[str, Any] | None = None,
                                    closure: dict[str, Any] | None = None,
                                    deep: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return R1 completeness dimensions derived from the current canonical graph.

    This is safe to call after semantic overlays because it recomputes proof-chain status rather than
    trusting an overlay to self-certify its own anchors.
    """
    audit = audit or audit_integrity(store)
    closure = closure or surface_closure(store)
    deep = deep or effect_closure(store)
    anchors = [o for o in store.semantic_objects() if o["object_type"] == "RECONSTRUCTION_ANCHOR"]
    proven = [o for o in anchors if _has_evidence_path(store, o["id"], max_depth=12)]
    if not anchors:
        anchor_state = "UNKNOWN"
    elif len(proven) == len(anchors):
        anchor_state = "MAPPED"
    elif proven:
        anchor_state = "PARTIAL"
    else:
        anchor_state = "BLOCKED"

    human_parent = stable_id("coverage-dimension", "human-surfaces")
    evidence_parent = stable_id("coverage-dimension", "evidence-integrity")
    return [
        {
            "id": evidence_parent,
            "key": "evidence-integrity",
            "label": "Canonical evidence-graph referential/provenance integrity",
            "state": audit.get("state", "UNKNOWN"),
            "parent_id": None,
            "attributes": {"severity_counts": audit.get("severity_counts", {}), "issue_count": audit.get("issue_count", 0)},
            "evidence_ids": [],
        },
        {
            "id": stable_id("coverage-dimension", "evidence-traceability"),
            "key": "evidence-traceability",
            "label": "Semantic claim/anchor proof-chain traceability",
            "state": anchor_state,
            "parent_id": evidence_parent,
            "attributes": {"anchor_count": len(anchors), "anchors_with_evidence_path": len(proven)},
            "evidence_ids": [],
        },
        {
            "id": stable_id("coverage-dimension", "human-surface-bindings"),
            "key": "human-surface-bindings",
            "label": "Mechanical surface-to-handler/route closure",
            "state": closure.get("state", "UNKNOWN"),
            "parent_id": human_parent,
            "attributes": {"bound": closure.get("bound_count", 0), "partial": closure.get("partial_count", 0), "unresolved": closure.get("unresolved_count", 0)},
            "evidence_ids": [],
        },
        {
            "id": stable_id("coverage-dimension", "human-surface-effect-closure"),
            "key": "human-surface-effect-closure",
            "label": "Surface-to-state/effect/boundary/feedback closure",
            "state": deep.get("state", "UNKNOWN"),
            "parent_id": human_parent,
            "attributes": {"closed": deep.get("closed_count", 0), "partial": deep.get("partial_count", 0),
                           "unresolved": deep.get("unresolved_count", 0),
                           "feedback_observed": deep.get("feedback_observed_count", 0)},
            "evidence_ids": [],
        },
        {
            "id": stable_id("coverage-dimension", "reconstruction-anchors"),
            "key": "reconstruction-anchors",
            "label": "Reconstruction anchor traceability",
            "state": anchor_state,
            "parent_id": evidence_parent,
            "attributes": {"anchor_count": len(anchors), "anchors_with_evidence_path": len(proven)},
            "evidence_ids": [],
        },
    ]


def refresh_refinement_completeness(store) -> dict[str, Any]:
    audit = audit_integrity(store)
    closure = surface_closure(store)
    deep = effect_closure(store)
    updates = refinement_completeness_updates(store, audit=audit, closure=closure, deep=deep)
    store.put_completeness(updates)
    return {"integrity": audit, "surface_closure": closure, "effect_closure": deep,
            "updated_dimensions": [x["key"] for x in updates]}


def effect_closure(store, *, max_depth: int = 12) -> dict[str, Any]:
    """Measure surface -> handler/call -> state/effect/boundary/feedback closure.

    This is intentionally evidence conservative. It does not claim that every user action must mutate
    state or cross the NEST. A presented dialog or explicit feedback is itself an observable terminal.
    Surfaces that only reach a handler/call chain remain PARTIAL until a mechanically supported effect,
    state change, NEST boundary, extension receptor, or presented/feedback surface is reached.
    """
    base = surface_closure(store)
    base_by_id = {r["surface_id"]: r for r in base["records"]}
    node_rows = store.query("SELECT id,kind,name,path,coverage,attributes_json FROM nodes")
    nodes = {r["id"]: r for r in node_rows}
    attrs = {nid: _decode_json(r.get("attributes_json"), {}) for nid, r in nodes.items()}
    edges = store.query("SELECT id,src,dst,kind,coverage,attributes_json,evidence_ids_json FROM edges ORDER BY src,kind,dst,id")
    by_src: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        by_src[edge["src"]].append(edge)

    traversal_kinds = {
        "resolves_to", "alternate_route_to", "emits", "dispatches_to", "invokes", "triggers",
        "triggers_async", "delivers_async_to",
        "routes_to", "handled_in", "calls", "produces_effect", "changes_state", "crosses_boundary",
        "opens_surface", "produces_feedback", "has_effect", "has_feedback", "reaches_extension",
    }
    terminal_kinds = {"effect", "state_change", "nest_boundary", "extension_receptor_candidate", "extension_receptor", "capability_factory", "persistence_operation", "error_path", "feedback"}

    records = []
    closed = partial = unresolved = 0
    with_feedback = 0
    by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "CLOSED": 0, "PARTIAL": 0, "UNRESOLVED": 0})

    for sid, binding in sorted(base_by_id.items(), key=lambda kv: (str(kv[1].get("path")), kv[1]["name"], kv[0])):
        surface_attrs = attrs.get(sid, {})
        # Presented/output surfaces are terminal observations, not entry denominators for deep action closure.
        if surface_attrs.get("surface_role") == "presented":
            continue

        queue = deque([(sid, 0, [])])
        visited = {sid}
        terminals: dict[str, dict[str, Any]] = {}
        feedbacks: dict[str, dict[str, Any]] = {}
        best_terminal_paths: list[list[dict[str, Any]]] = []
        reached_structural = False

        while queue:
            current, depth, path = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in by_src.get(current, []):
                if edge["kind"] not in traversal_kinds:
                    continue
                dst = edge["dst"]
                step = {"edge_id": edge["id"], "kind": edge["kind"], "src": edge["src"], "dst": dst, "coverage": edge["coverage"]}
                new_path = path + [step]
                node = nodes.get(dst)
                if node:
                    if node["kind"] in {"symbol", "handler_reference", "input_consumer", "call_reference"}:
                        reached_structural = True
                    dattrs = attrs.get(dst, {})
                    is_presented = node["kind"] in {"human_surface", "surface_factory_output"} and dattrs.get("surface_role") == "presented"
                    if node["kind"] in terminal_kinds or is_presented:
                        previous = terminals.get(dst)
                        terminal_rec = {"id": dst, "kind": node["kind"], "name": node["name"], "coverage": node["coverage"],
                                        "attributes": dattrs, "example_route": new_path}
                        if previous is None or len(new_path) < len(previous.get("example_route", [])):
                            terminals[dst] = terminal_rec
                        best_terminal_paths.append(new_path)
                    if node["kind"] == "feedback" or is_presented or edge["kind"] == "produces_feedback":
                        previous = feedbacks.get(dst)
                        feedback_rec = {"id": dst, "kind": node["kind"], "name": node["name"], "coverage": node["coverage"],
                                        "attributes": dattrs, "example_route": new_path}
                        if previous is None or len(new_path) < len(previous.get("example_route", [])):
                            feedbacks[dst] = feedback_rec
                if dst not in visited:
                    visited.add(dst)
                    queue.append((dst, depth + 1, new_path))

        if binding["closure"] == "UNRESOLVED":
            status = "UNRESOLVED"
            unresolved += 1
        elif terminals:
            status = "CLOSED"
            closed += 1
        else:
            status = "PARTIAL"
            partial += 1
        if feedbacks:
            with_feedback += 1
        stype = str(binding.get("surface_type") or "unknown")
        by_type[stype]["total"] += 1
        by_type[stype][status] += 1
        records.append({
            "surface_id": sid,
            "name": binding["name"],
            "surface_type": stype,
            "binding_closure": binding["closure"],
            "effect_closure": status,
            "reached_structural_path": reached_structural,
            "terminal_count": len(terminals),
            "feedback_count": len(feedbacks),
            "terminals": sorted(terminals.values(), key=lambda x: (x["kind"], x["name"], x["id"])),
            "feedback": sorted(feedbacks.values(), key=lambda x: (x["kind"], x["name"], x["id"])),
            "example_terminal_route": min(best_terminal_paths, key=len) if best_terminal_paths else [],
        })

    total = len(records)
    state = "UNKNOWN" if total == 0 else "MAPPED" if partial == 0 and unresolved == 0 else "PARTIAL"
    return {
        "schema_version": "scan-effect-closure/0.1",
        "state": state,
        "surface_count": total,
        "closed_count": closed,
        "partial_count": partial,
        "unresolved_count": unresolved,
        "feedback_observed_count": with_feedback,
        "closure_ratio": (closed / total) if total else None,
        "by_surface_type": dict(sorted(by_type.items())),
        "records": records,
    }
