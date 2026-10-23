"""Derived functional graph: one read-only view of authoritative recipe/state/scan.

Do not persist a second writable model of anchors, dependencies or acceptance.
Static scan claims and Baker attestations are labeled separately from test evidence.
"""
from pathlib import Path
from .core import KPPError, digest, read_json


def evidence_kind(record):
    return record.get("kind", "manual") if isinstance(record, dict) else None


def accepted_ids(recipe, state):
    known = {a["id"] for a in recipe["anchors"]}
    from .testing import evidence_current
    result = {aid for aid, rec in state.get("accepted", {}).items()
            if aid in known and isinstance(rec, dict) and rec.get("recipe_hash") == state.get("recipe_hash")
            and evidence_current(rec)}
    if "reference_gui" in recipe:
        from .gui import validate_inventory, coverage as gui_coverage
        inventory=validate_inventory(state.get("gui_inventory"),recipe)
        if not gui_coverage(inventory)["accounted_for"]:
            result.discard(recipe["reference_gui"]["coverage_anchor"])
    return result


def coverage(recipe, state):
    """Declared coverage and acceptance, not a proof of semantic equivalence."""
    accepted = accepted_ids(recipe, state)
    required = [a for a in recipe["anchors"] if a["required"]]
    preserve = recipe.get("transformation", {}).get("preserve", [])
    claims = []
    for prop in preserve:
        links = [a["id"] for a in required if prop in a.get("preserves", [])]
        claims.append({"property": prop, "mandatory_anchors": links,
                       "declared_coverage": bool(links),
                       "accepted": bool(links) and all(a in accepted for a in links),
                       "evidence_status": [
                           {"anchor": a, "kind": evidence_kind(state.get("accepted", {}).get(a))}
                           for a in links]})
    remaining = [a["id"] for a in required if a["id"] not in accepted]
    report = {"schema": "kpp.coverage/1", "recipe_hash": state.get("recipe_hash"),
            "required_anchors": len(required), "accepted_anchors": len(required)-len(remaining),
            "unmet_anchors": remaining,
            "preservation": claims,
            "uncovered_properties": [p["property"] for p in claims if not p["declared_coverage"]],
            "unaccepted_properties": [p["property"] for p in claims if not p["accepted"]],
            "attestation_kinds": {
                "manual": sum(a["id"] in accepted and evidence_kind(state.get("accepted", {}).get(a["id"])) == "manual" for a in required),
                "other": sum(a["id"] in accepted and evidence_kind(state.get("accepted", {}).get(a["id"])) not in (None, "manual") for a in required),
            },
            "scope": "Declared recipe obligations and recorded Baker attestations; not independent behavioral proof"}
    if "reference_gui" in recipe:
        from .gui import coverage as gui_coverage
        report["reference_gui"]=gui_coverage(state["gui_inventory"],accepted)
    return report


def chase(recipe, state, activity=None):
    """Schedule from the same recipe graph edges used by coverage and handoff."""
    active = accepted_ids(recipe, state)
    from .construction import construction_plan
    use_chase = construction_plan(recipe)["ordering"] == "chase"
    activity = activity or {}
    results = []
    for anchor in recipe["anchors"]:
        if anchor["id"] in active:
            continue
        missing = [dep for dep in anchor.get("depends", []) if dep not in active]
        ready = not missing
        area = anchor.get("area", "other")
        score = ((100 if ready else -100) + min(100, max(0, activity.get(area, 0)))*5 - anchor["depth"]) if use_chase else int(ready)
        if anchor["required"]:
            score += 10
        results.append({"id": anchor["id"], "area": area, "depth": anchor["depth"],
                        "ready": ready, "missing_dependencies": missing, "priority": score,
                        "required": anchor["required"]})
    from .construction import construction_plan
    if not use_chase:
        # Recipe order among ready obligations; no activity or depth weighting.
        for item in results:
            item['priority'] = 1 if item['ready'] else 0
        return sorted(results, key=lambda e: not e['ready'])
    return sorted(results, key=lambda e: (-e["priority"], e["id"]))


def load_scan(path):
    path = Path(path)
    if path.stat().st_size > 64_000_000:
        raise KPPError('Scan evidence exceeds 64MB bound')
    from .scanner import verify_scan
    return verify_scan(read_json(path))


def functional_graph(recipe, state, scan=None, activity=None, workspace=None):
    """Scoped cross-view graph. Scanned source is evidence, never executable authority."""
    accepted = accepted_ids(recipe, state)
    from .language import binding_mode
    shared_binding, applications = None, {}
    if binding_mode(recipe) == 'shared-neutral':
        from .. import kitchen
        shared_binding = kitchen.bind(recipe)
        applications = {item['id']: item for item in shared_binding['applications']}
    nodes = []
    edges = []
    for ing in recipe["ingredients"]:
        nodes.append({"id": "ingredient:"+ing, "kind":"ingredient", "label":ing,
                      "basis": "recipe-declared"})
    for reference in state.get("gui_evidence",[]):
        nodes.append({"id":"gui-evidence:"+reference["id"],"kind":"gui-evidence-reference",
                      "label":reference["id"],"basis":"recorded-source-bound-evidence; freshness checked at acceptance"})
    for aid,record in state.get("accepted",{}).items():
        if isinstance(record,dict) and record.get("kind")=="gui-reviewed":
            edges.append({"from":"anchor:"+aid,"to":"gui-evidence:"+record["gui_evidence_id"],
                          "kind":"baker-reviewed-gui-evidence","basis":"current" if aid in accepted else "stale"})
    for a in recipe["anchors"]:
        aid = "anchor:"+a["id"]
        nodes.append({"id":aid, "kind":"anchor", "label":a["statement"], "depth":a["depth"],
                      "area":a.get("area", "other"), "required":a["required"],
                      "status":"BAKER_ACCEPTED" if a["id"] in accepted else "UNMET",
                      "basis":"recipe-declared", **({'application': applications[a['id']]} if a['id'] in applications else {})})
        for dep in a.get("depends", []):
            edges.append({"from":aid, "to":"anchor:"+dep, "kind":"depends-on", "basis":"recipe-declared"})
    if "reference_gui" in recipe:
        for entry in state["gui_inventory"]["entries"]:
            gid="gui:"+entry["id"]
            nodes.append({"id":gid,"kind":"gui-observation","label":entry["label"],
                          "disposition":entry["disposition"],"discovered":True,"basis":"static-declaration-not-runtime-proof"})
            for anchor in entry["anchor_ids"]:
                edges.append({"from":"anchor:"+anchor,"to":gid,"kind":"accounts-for-gui",
                              "basis":"pinned-inventory-declaration"})
    for prop in recipe.get("transformation", {}).get("preserve", []):
        pid = "preserve:"+digest(prop)[:16]
        nodes.append({"id":pid, "kind":"preservation-obligation", "label":prop,
                      "basis":"recipe-declared"})
        for a in recipe["anchors"]:
            if prop in a.get("preserves", []):
                edges.append({"from":"anchor:"+a["id"],"to":pid,"kind":"covers-preservation",
                              "basis":"recipe-declared"})
    for ref in recipe.get("reflexes", []):
        rid = "reflex:" + ref["id"]
        src = "runtime-function:" + ref["source"]
        if not any(node["id"] == src for node in nodes):
            nodes.append({"id":src,"kind":"declared-attachment-point", "label":ref["source"],
                          "basis":"recipe-declared-not-runtime-proof"})
        nodes.append({"id":rid,"kind":"reflex", "label":ref["id"],
                      "timing":ref["timing"],"basis":"recipe-declared"})
        edges.append({"from":src,"to":rid,"kind":"triggers-reflex", "basis":"recipe-declared"})
        edges.append({"from":rid,"to":"ingredient:"+ref["ingredient"],
                      "kind":"invokes-ingredient", "basis":"recipe-declared"})
        for anchor_id in ref["anchors"]:
            edges.append({"from":"anchor:"+anchor_id,"to":rid,
                          "kind":"verifies-reflex-obligation", "basis":"recipe-declared"})
    if scan is not None:
        from .scanner import verify_scan
        verify_scan(scan)
        for key, item in scan["nodes"].items():
            nodes.append({"id":"source:"+key,"kind":"source-observation",
                          "label":key,"source_kind":item.get("kind"),
                          "basis":"static-source-observation"})
        for ref in recipe.get("reflexes", []):
            for key in scan["nodes"]:
                if key.split("@", 1)[0] == ref["source"]:
                    edges.append({"from":"source:"+key,
                                  "to":"runtime-function:"+ref["source"],
                                  "kind":"possible-attachment-match",
                                  "basis":"static-observation-not-runtime-proof"})
        for edge in scan["edges"]:
            if edge.get("from") in scan["nodes"] and edge.get("to") in scan["nodes"]:
                edges.append({"from":"source:"+edge["from"], "to":"source:"+edge["to"],
                              "kind":edge.get("kind", "static-relationship"),
                              "basis":"static-source-observation-not-runtime-proof"})
    matrix=None
    if workspace is not None and "gui_inventory" in state:
        from .conformance import coverage_matrix
        matrix=coverage_matrix(workspace)
    from .construction import construction_plan
    return {"construction":construction_plan(recipe), "schema":"kpp.functional-graph/1", "recipe_hash":state["recipe_hash"],
            "nodes":nodes,"edges":edges,"anchor_binding":shared_binding,
            "views":{
                "fidelity": {str(d):sorted(a["id"] for a in recipe["anchors"] if a["depth"] == d)
                             for d in sorted({a["depth"] for a in recipe["anchors"]})},
                "chase":chase(recipe,state,activity),  # compatibility alias for requirement ordering
                "requirements":chase(recipe,state,activity),
                "coverage":coverage(recipe,state)},
            "gui_matrix":matrix,
            "scan":None if scan is None else {"requested_depth":scan.get("requested_depth"),
                 "scope":scan.get("scope"),"limitations":scan.get("limitations"),
                 "skipped":scan.get("skipped",[])},
            "limitations":"Graph is derived from recipe assertions, Baker acceptance and optional static scan; no inferred runtime equivalence"}
