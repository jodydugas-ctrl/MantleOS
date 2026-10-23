"""Non-mutating Functional Economy proposal review.

Checks proposed structural consolidation; does NOT prove behavioral equivalence or
modify the baseline recipe. A revised recipe and repeated acceptance are required.
"""
from .core import KPPError


def evaluate(recipe, proposal):
    if not isinstance(proposal, dict) or proposal.get("schema") != "kpp.economy-proposal/1":
        raise KPPError("Unsupported Economy proposal schema")
    merges = proposal.get("merges")
    if not isinstance(merges, list) or not merges:
        raise KPPError("Economy proposal needs nonempty merges")
    byid = {a["id"]:a for a in recipe["anchors"]}
    removed=set(); targets=set(); blocks=[]; cautions=[]; planned=[]
    for pos, entry in enumerate(merges):
        if not isinstance(entry, dict): raise KPPError("Merge must be object")
        sources=entry.get("from")
        dest=entry.get("into")
        if not isinstance(sources,list) or not sources or len(set(sources)) != len(sources) or not all(
            isinstance(x,str) and x in byid for x in sources):
            raise KPPError("Merge sources must be distinct existing Anchors")
        if not isinstance(dest,str) or dest not in byid or dest in sources:
            raise KPPError("Merge destination must be a distinct existing Anchor")
        if any(x in removed for x in sources):raise KPPError("Anchor removed twice")
        removed.update(sources);targets.add(dest)
        if not isinstance(entry.get("coverage_rationale"),str) or not entry["coverage_rationale"].strip():
            blocks.append(f"merge {pos}: no functional coverage rationale")
        if not isinstance(entry.get("comparison_tests"),list) or not entry["comparison_tests"] or not all(
            isinstance(v,str) and v.strip() for v in entry["comparison_tests"]):
            blocks.append(f"merge {pos}: no baseline-versus-candidate test plan")
        old_areas={byid[x].get("area","other") for x in sources}
        new_area=byid[dest].get("area","other")
        if any(area != new_area for area in old_areas):
            cautions.append(f"merge {pos}: crosses functional area/possible authority boundary; separate review required")
        old_props={prop for x in sources for prop in byid[x].get("preserves", [])}
        surviving_props={prop for a in recipe["anchors"] if a["id"] not in removed for prop in a.get("preserves",[])}
        orphaned=old_props-surviving_props
        if orphaned:
            blocks.append(f"merge {pos}: preservation coverage would be lost for: {sorted(orphaned)}")
        planned.append({"removed":sources,"retained":dest,"original_tests":[byid[x]["test"] for x in sources],
                        "preserved_properties": sorted(old_props)})
    # Re-check coverage after ALL proposed removals, not one merge at a time.
    original_props={prop for a in recipe["anchors"] if a["required"] for prop in a.get("preserves",[])}
    retained_props={prop for a in recipe["anchors"] if a["id"] not in removed and a["required"] for prop in a.get("preserves",[])}
    if original_props-retained_props:
        blocks.append("All-merge result loses protected properties: "+repr(sorted(original_props-retained_props)))
    if removed & targets:
        blocks.append("A merge destination is removed by another merge")
    for a in recipe["anchors"]:
        if a["id"] in removed:continue
        stranded=[dep for dep in a.get("depends",[]) if dep in removed]
        if stranded:
            cautions.append(f"{a['id']}: dependencies on removed Anchors need explicit rewiring: {stranded}")
    return {"schema":"kpp.economy-review/1", "recipe_id":recipe["id"],
            "baseline_anchor_count":len(byid), "hypothetical_count":len(byid)-len(removed),
            "proposed_removals":sorted(removed),"merges":planned,
            "blocking_gaps":blocks,"required_reviews":cautions,
            "decision":"REJECTED_STRUCTURAL" if blocks else "PROPOSAL_ONLY_REQUIRES_RECIPE_REVISION_AND_RETEST",
            "proof_status":"NOT_PROVEN",
            "next_step":"Keep original recipe; prepare a separately versioned candidate, rerun every affected Anchor test and seek Baker acceptance. No automatic consolidation."}
