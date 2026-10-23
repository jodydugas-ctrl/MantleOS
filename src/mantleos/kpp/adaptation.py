"""Advisory functional-fit and read-only reflex-point discovery.

No source is evaluated, patched, imported, installed, admitted, or tested by this
module. Its output is a reviewable, source-pinned proposal, NOT runtime evidence.
"""
import re
from pathlib import Path
from .core import KPPError, digest, ingredient_catalog, validate_recipe
from .pantry import label
from .scanner import scan
from .graph import functional_graph, coverage

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset({"a", "an", "and", "the", "to", "of", "for", "with", "on", "in", "from", "is", "be", "after", "before", "new", "existing", "function", "behavior"})
_ALLOWED_TIMINGS = ("after-success", "before-call", "on-error")


def words(s):
    return set(_WORD.findall(s.lower())) - _STOP


def _request(request):
    if not isinstance(request, dict) or request.get("schema") != "kpp.adaptation-request/1":
        raise KPPError("Expected kpp.adaptation-request/1")
    need = request.get("capability")
    if not isinstance(need, str) or not need.strip() or len(need) > 300:
        raise KPPError("Adaptation request needs a bounded capability")
    baseline = request.get("existing_capabilities", [])
    if not isinstance(baseline, list) or len(baseline) > 40 or any(
            not isinstance(s, str) or not s.strip() or len(s) > 300 for s in baseline):
        raise KPPError("Invalid existing_capabilities list")
    if "ingredient_id" in request and (not isinstance(request["ingredient_id"], str) or not request["ingredient_id"].strip()):
        raise KPPError("Invalid ingredient_id")
    trigger = request.get("trigger")
    if trigger is not None:
        if not isinstance(trigger, dict) or trigger.get("timing") not in _ALLOWED_TIMINGS or not isinstance(trigger.get("function_hint"), str) or not trigger["function_hint"].strip() or len(trigger["function_hint"]) > 128:
            raise KPPError("trigger needs timing and function_hint")
    anchors = request.get("anchors")
    if anchors is not None and (not isinstance(anchors, dict) or set(anchors) != {"original", "reflex", "optional_absent"} or
                                any(not isinstance(v, str) or not v for v in anchors.values()) or len(set(anchors.values())) != 3):
        raise KPPError("anchors must map distinct original, reflex and optional_absent Anchor IDs")
    return request


def fit(repo, request, limit=8):
    """Metadata-based relevance, never semantic compatibility or acquisition authority."""
    _request(request)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise KPPError("Fit limit must be in 1..50")
    catalog = ingredient_catalog(repo, check_sources=False)
    need = request["capability"].strip()
    need_words = words(need)
    if not need_words:
        raise KPPError("Capability has no meaningful matching terms")
    declared = request.get("existing_capabilities", [])
    # An exact user assertion supports a no-change recommendation, not actual
    # runtime coverage. Fuzzy matching is deliberately never treated as proof.
    already_declared = any(words(item) == need_words for item in declared)
    candidates = []
    for item in catalog.values():
        lbl = label(repo, item)
        surface = " ".join([item["id"], item["function"], *item.get("capabilities", []),
                            *item.get("tags", []), lbl["use_when"], *lbl["outputs"]])
        match = sorted(need_words & words(surface))
        if not match:
            continue
        # Explicit evidence for each score, not a model confidence probability.
        candidates.append({"id": item["id"], "matched_terms": match,
                           "term_overlap_count": len(match),
                           "declared_status": lbl["status"],
                           "source_integrity": lbl["source"]["integrity"],
                           "manifest_sha256": lbl["manifest_sha256"],
                           "overlap_with_declared_baseline": sorted(set.union(
                               set(), *(words(s) & words(surface) for s in declared))) if declared else [],
                           "disposition": "REVIEW_ONLY_NOT_ADMITTED",
                           "evidence": "Manifest metadata relevance, not functional proof"})
    candidates.sort(key=lambda x: (-x["term_overlap_count"], x["id"]))
    chosen = request.get("ingredient_id")
    if chosen and chosen not in catalog:
        raise KPPError("Requested ingredient is absent from Pantry: " + chosen)
    return {"schema":"kpp.functional-fit/1", "capability":need,
            "request_sha256":digest(request), "baseline_claims":declared,
            "recommendation":("NO_CHANGE_PROPOSED_USER_ASSERTED_COVERAGE" if already_declared
                              else "REVIEW_REUSE_BEFORE_NEW_CONSTRUCTION"),
            "candidate_ingredient_id": chosen,
            "matches":candidates[:limit], "total_matches":len(candidates),
            "note":"Exact baseline claims are user-provided, not verified. Metadata terms are not compatibility, safety or behavior proof. No automatic installation or acceptance."}


def reflex_plan(repo, workspace_recipe, workspace_state, request, source_dir, depth=2):
    """Find names matching a trigger hint within a fresh read-only static scan.

    Require a preservation-bearing recipe and three distinct mandatory Anchors,
    leaving the final connection choice, patch and runtime tests to a Baker/Oven.
    """
    _request(request)
    recipe = validate_recipe(workspace_recipe)
    if recipe.get("mode") != "transformation":
        raise KPPError("Reflex planning requires a transformation recipe")
    if not request.get("trigger") or not request.get("anchors"):
        raise KPPError("Reflex planning needs trigger and original/reflex/optional_absent Anchors")
    protected = recipe.get("transformation", {}).get("preserve", [])
    if not protected:
        raise KPPError("Reflex planning needs explicit preserved properties")
    required = {a["id"]: a for a in recipe["anchors"] if a["required"]}
    assigned = request["anchors"]
    if any(value not in required for value in assigned.values()):
        raise KPPError("Requested reflex Anchors must be mandatory and present in the recipe")
    if not (set(required[assigned["original"]].get("preserves", [])) & set(protected)):
        raise KPPError("Original-behavior Anchor must cover a declared preserved property")
    chosen = request.get("ingredient_id")
    if not chosen or chosen not in recipe["ingredients"]:
        raise KPPError("Reflex ingredient must be declared in the pinned recipe")
    match = fit(repo, request)
    current_scan = scan(source_dir, depth=depth)
    graph = functional_graph(recipe, workspace_state, current_scan)
    byfile = {file["path"]:file["sha256"] for file in current_scan["files"]}
    hint = request["trigger"]["function_hint"].lower().strip()
    hw = words(hint)
    candidates = []
    for node in graph["nodes"]:
        if node["kind"] != "source-observation" or node.get("source_kind") not in ("FunctionDef", "AsyncFunctionDef"):
            continue
        key = node["label"]
        if "::" not in key or "@" not in key:continue
        rel, full_name = key.split("::", 1)
        name, line = full_name.rsplit("@", 1)
        simple = name.lower()
        # Exact > token overlap > no candidate. Do not infer runtime success paths.
        matched = sorted(hw & words(simple))
        if not matched and hint != simple:continue
        score = 100 if simple == hint else len(matched) * 10
        candidates.append({"source_node":node["id"], "file":rel, "line":int(line),
                           "function":name, "source_sha256":byfile.get(rel),
                           "match_terms":matched, "relevance_score":score,
                           "insertion_point_verified":False,
                           "reason":"Static function-name match only; timing and side effects unverified"})
    candidates.sort(key=lambda c: (-c["relevance_score"],c["file"],c["line"],c["function"]))
    # Do not present a winner if equal-highest scores are ambiguous.
    tentative = (candidates[0] if len(candidates) == 1 or
                 (len(candidates) > 1 and candidates[0]["relevance_score"] > candidates[1]["relevance_score"])
                 else None) if candidates else None
    return {"schema":"kpp.reflex-plan/1", "status":"REVIEW_REQUIRED_NO_MUTATION",
            "recipe_id":recipe["id"],"recipe_sha256":workspace_state["recipe_hash"],
            "request_sha256":digest(request),"functional_graph_sha256":digest(graph),
            "source_inventory_sha256":digest(current_scan["files"]),
            "source_root":str(Path(source_dir).resolve()),
            "scan":{"depth":depth,"skipped":current_scan["skipped"],"scope":current_scan["scope"]},
            "capability":request["capability"],"timing":request["trigger"]["timing"],
            "ingredient_id":chosen,"fit":match,
            "preservation":coverage(recipe,workspace_state),
            "required_anchor_ids":assigned,"candidate_points":candidates[:20],
            "tentative_point":tentative,
            "decision":("NO_MATCH_REVIEW_MANUALLY" if not candidates else
                        "AMBIGUOUS_REVIEW_MANUALLY" if tentative is None else "PROPOSAL_REQUIRES_BAKER_REVIEW"),
            "minimum_change_proposal":[
                "Review the indicated callable and its callers against real success and failure paths.",
                "Prefer an optional wrapper, adapter, or existing hook; do not rewrite the original application body if unnecessary.",
                "Trigger the organ only at the reviewed timing; preserve return values, exceptions and existing effects.",
                "Keep the original application operating when the added organ or optional MIND is absent.",
                "Obtain approval, implement in a separate candidate, and execute pinned baseline and new-behavior Anchor tests.",
                "Re-scan and reverify all source hashes after edits; this proposal is stale if the baseline changes."
            ],
            "execution":"NONE", "verification":"NONE", "admission":"NOT_AUTHORIZED",
            "limitations":"No patches or executed Anchor tests; static matching cannot establish a safe connection point or program equivalence."}
