#!/usr/bin/env python3
"""
mantle.assimilator.report  --  the assimilation artifacts (Mantle OS)

Produces the Phase 0 artifacts the Stage-1 audit consumes: the APP_INVENTORY markdown
(the read-only gate a human signs before any hook is inserted) and the machine-readable
assimilation map (JSON). A dry run = scan + map + report, ZERO writes to the host.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..primer import appai_commandments, appai_truths

from .scanner import scan_project
from .organ_map import build_map, propose_genome, ORGANS
from .surface_coverage import render_surface_coverage_markdown
from .coverage import InsertionState


def dry_run(root: str) -> Dict[str, Any]:
    """The read-only assimilation pipeline: dissect -> map -> artifacts. Touches nothing."""
    dissection = scan_project(root)
    amap = build_map(dissection)
    amap["insertion_state"] = InsertionState.OBSERVED_CAUSAL_GRAPH.value
    amap["runtime_hook_verified"] = False
    return {"dissection": dissection, "map": amap,
            "inventory_md": render_inventory(amap, dissection)}


def render_inventory(amap: Dict[str, Any], dissection: Dict[str, Any]) -> str:
    """The APP_INVENTORY.md artifact (see guides/Assimilation_Guide.md), pre-filled
    from the dissection. The READ-ONLY sign-off line stays unsigned -- a human signs it;
    only then may Phase 5+ insert any hook (HF-B42)."""
    L = []
    L.append("# APP INVENTORY & ORGAN MAP — %s" % os.path.basename(amap["host"]))
    L.append("")
    L.append("*Generated READ-ONLY by `mantle.assimilator` (Path B, Phase 0). No host file "
             "was modified. Hook insertion (Phase 5+) is authorized ONLY after the sign-off "
             "line below is signed.*")
    L.append("")
    L.append("## A.1 Host identity")
    L.append("- **Root:** `%s`" % amap["host"])
    L.append("- **Insertion state:** `%s`" % amap.get("insertion_state"))
    L.append("- **Runtime hook verified:** `%s`" %
             str(bool(amap.get("runtime_hook_verified"))).lower())
    L.append("- **Python files:** %d" % dissection["python_files"])
    substrate = dissection.get("substrate") or {}
    if substrate:
        L.append("- **Detected substrate:** %s" % ", ".join(substrate.get("languages", [])))
        L.append("- **Build files:** %s" % (
            ", ".join("`%s`" % p for p in substrate.get("build_files", [])[:8])
            or "none"))
        L.append("- **Adaptive native/tooling required:** %d file(s)" %
                 substrate.get("coverage", {}).get("requires_adaptive_native_tools", 0))
    L.append("")
    if substrate:
        L.append("## A.2 Substrate coverage")
        L.append("")
        L.append("MantleOS is code-agnostic by discovery and explicit parser evidence, not by")
        L.append("pretending one scanner sees every host. Per-file gaps remain authoritative.")
        L.append("")
        L.append("- **Overall scan state:** `%s`" % dissection.get("coverage_state", "unknown"))
        L.append("- **Parser gaps:** %d" % dissection.get("parser_gap_count", 0))
        for row in substrate.get("coverage", {}).get("states", []):
            parser = row.get("parser") or {}
            L.append("- `%s`: `%s` via `%s` (%d/%d file(s) parsed)" % (
                row.get("language"), row.get("state"), parser.get("parser", "none"),
                row.get("parsed_files", 0), row.get("first_party_files", 0)))
        for gap in substrate["unsupported"]:
            L.append("- `%s`: %d file(s) -- %s" %
                     (gap["substrate"], gap["files"], gap["reason"]))
        L.append("")
    L.append("## A.3/A.4 Symbol-role summary")
    L.append("")
    L.append("| Role | Count |")
    L.append("|------|-------|")
    for role, n in sorted(amap["role_counts"].items(), key=lambda kv: -kv[1]):
        L.append("| %s | %d |" % (role, n))
    L.append("")
    L.append("## The organ map (host tissue -> organs)")
    L.append("")
    for organ in ORGANS:
        syms = amap["organs"][organ]
        L.append("### %s (%d symbol%s)" % (organ.capitalize(), len(syms),
                                           "" if len(syms) == 1 else "s"))
        for s in syms[:12]:
            L.append("- `%s:%d`  `%s`  (%s)" % (s["module"], s["line"], s["symbol"], s["role"]))
        if len(syms) > 12:
            L.append("- ... and %d more" % (len(syms) - 12))
        if not syms:
            L.append("- *none found — an app with no %s is information too*" % organ)
        L.append("")
    L.append("### Remains external host code (%d)" % len(amap["external_host_code"]))
    L.append("*INTERNAL_UTILITY symbols are wrapped only if they touch an organ surface.*")
    L.append("")
    if amap["missing_organs"]:
        L.append("> **Missing organs:** %s — fragile seams the assimilation should "
                 "compensate for." % ", ".join(amap["missing_organs"]))
        L.append("")
    L.append("## A.7 Proposed cube genome")
    L.append("")
    L.append("| Band | Head | Span | Encoding | Purpose |")
    L.append("|------|------|------|----------|---------|")
    for b in propose_genome(amap["role_counts"]):
        L.append("| %s | %d | %d | %s%s | %s |"
                 % (b["band"], b["head"], b["span"], b["encoding"],
                    " (private)" if b["private"] else "", b["purpose"]))
    L.append("")
    evidence = amap.get("host_evidence_index") or {}
    if evidence:
        L.append("## A.8 Resident host evidence index")
        L.append("")
        L.append("The resident must consult this local evidence before generic MIND chat.")
        L.append("Provider reasoning may interpret the evidence after authorization, but it")
        L.append("must not replace the evidence index or hide missing evidence.")
        L.append("")
        L.append("- **Schema:** `%s`" % evidence.get("schema_version", "unknown"))
        L.append("- **Local-first consultation:** `%s`" %
                 str(evidence.get("local_first_consultation", False)).lower())
        sources = evidence.get("evidence_sources", [])
        L.append("- **Evidence sources:** %s" % (
            ", ".join("`%s`" % s for s in sources) if sources else "none"))
        controls = evidence.get("control_surfaces", [])
        if controls:
            L.append("- **Observed control surfaces:** %s" % ", ".join(
                "`%s`" % c.get("control") for c in controls[:8]))
        else:
            L.append("- **Observed control surfaces:** none")
        limitations = evidence.get("limitations", [])
        if limitations:
            L.append("- **Known limits:** %s" % " ".join(limitations[:2]))
        runtime_policies = evidence.get("runtime_policies", {})
        if runtime_policies:
            L.append("")
            L.append("### Resident runtime contract")
            L.append("")
            L.append("Future resident terminals generated from this evidence must preserve these")
            L.append("boundaries:")
            for key in (
                "command_channel_policy",
                "mind_body_lane_policy",
                "directive_fail_closed_policy",
                "transcript_vcw_policy",
                "secret_boundary_policy",
                "surface_retrieval_policy",
                "body_proof_policy",
                "text_commit_policy",
                "mind_context_rehydration_policy",
                "heartbeat_scheduler_policy",
            ):
                if runtime_policies.get(key):
                    L.append("- **%s:** %s" % (key, runtime_policies[key]))
        L.append("")
    coverage = amap.get("surface_coverage") or {}
    if coverage:
        L.append("## A.8.1 GUI nerve coverage")
        L.append("")
        L.append("- **Total GUI/control surfaces:** %d" %
                 coverage.get("total_surfaces", 0))
        L.append("- **Status counts:** `%s`" %
                 json.dumps(coverage.get("status_counts", {}), sort_keys=True))
        L.append("- **Maintenance findings:** %d" %
                 len(coverage.get("maintenance_findings", [])))
        L.append("- **Contract:** every discovered GUI surface is either verified, "
                 "observer-only, sense-only, not implemented, or an explicit "
                 "maintenance gap.")
        L.append("")
    L.append("## A.9 Gap report")
    if amap["gap_report"]:
        for g in amap["gap_report"]:
            L.append("- `%s` — %s" % (g.get("module", g.get("symbol", "?")),
                                      g.get("why", "DEPRECATED")))
    else:
        L.append("- none")
    L.append("")
    L.append("## A.11 READ-ONLY sign-off (the Phase 0 gate)")
    L.append("```")
    L.append("APP INVENTORY COMPLETE — NO HOST CODE MODIFIED")
    L.append("  Host                 : %s" % amap["host"])
    L.append("  Files modified so far: 0   (MUST be 0)")
    L.append("  Approved to instrument (Phase 1+): [ ]  by ____________  date __________")
    L.append("")
    L.append("  >>> Hook insertion (Phase 5+) is authorized ONLY after this line is signed. <<<")
    L.append("```")
    return "\n".join(L)


def emit_spore(result: Dict[str, Any], out_png: str) -> Dict[str, Any]:
    """Scan the app, emit a SPORE: condense a dry-run dissection into a germ-carrying
    spore PNG -- the one artifact that births this host's resident AppAI anywhere.

    The germ declares the resident's identity, do-no-harm truths, the app bands the
    organ map proposed (host_state / host_actions), and the observed organ map as
    inert data. The spore also carries a source descriptor (host path + census
    fingerprint) so the hatch receipt can audit provenance. Emitting is still Phase 0:
    ZERO writes to the host; hatching the spore faces the Stage-1 gate like any birth,
    and host code stays OTHER until proven. Requires Pillow."""
    import hashlib

    amap = result["map"]
    dissection = result["dissection"]
    host = amap["host"]
    name = "%s.Resident" % os.path.basename(os.path.abspath(host)).title().replace("_", "")

    from ..anchor import census
    host_census = census(host)
    census_blob = json.dumps(host_census, sort_keys=True).encode("utf-8")

    app_bands = [{"band": b["band"], "head": b["head"], "span": b.get("span", 1),
                  "encoding": b.get("encoding", "log-json"),
                  "private": bool(b.get("private")), "purpose": b.get("purpose", b["band"])}
                 for b in propose_genome(amap["role_counts"])
                 if 550 <= b["head"] <= 749]
    organ_summary = {organ: [s["symbol"] for s in syms]
                     for organ, syms in amap["organs"].items() if syms}

    germ = {
        "schema": "mantle-germ-v2",
        "identity": {"name": name,
                     "purpose": "resident AppAI assimilated read-only from %s"
                                % os.path.basename(host),
                     "born_of": "assimilation"},
        "truths": appai_truths([
            "The host is my body's home; I never harm it.",
            "Host code is OTHER until proven.",
        ]),
        "commandments": appai_commandments([
            "Do no harm to the host.",
        ]),
        "genome": app_bands,
        "assimilation": {                      # observed facts, inert data
            "role_counts": amap["role_counts"],
            "organ_map": organ_summary,
            "host_evidence_index": amap.get("host_evidence_index", {}),
            "missing_organs": amap["missing_organs"],
            "python_files": dissection["python_files"],
        },
    }

    build = (
        "# HOW TO BUILD THE RESIDENT AppAI IN THIS SPORE\n\n"
        "This spore was emitted by a READ-ONLY assimilation (Path B, Phase 0) of the\n"
        "host %r. Zero host files were modified.\n\n"
        "With Mantle 2:\n"
        "  python -m mantle lifecycle authorize hatch this_file.png nest/ --approve --out=hatch-auth.json\n"
        "  python -m mantle hatch this_file.png --out=nest/ --auth=hatch-auth.json\n"
        "Without: decode my payload (Quickstart on the image) and read key 'germ'.\n\n"
        "The germ's `assimilation` block is the observed organ map -- which host\n"
        "symbols play which organ roles (%s). Treat it as observed fact, not law.\n"
        "The hatched body is a resident: it mirrors host state into its bands and\n"
        "wraps host effectors fail-open. Host code remains OTHER until the standing\n"
        "gates prove otherwise; hook insertion still requires the signed\n"
        "APP_INVENTORY (HF-B42).\n"
        % (os.path.basename(host), ", ".join(sorted(organ_summary)) or "none found")
    )
    source = {
        "kind": "assimilation",
        "path": os.path.basename(host),
        "sha256": "sha256:" + hashlib.sha256(census_blob).hexdigest(),
        "notes": "census fingerprint over %d host file(s); emitted read-only"
                 % len(host_census),
    }

    from .. import spore as _spore
    _spore.pack_germ(germ, out_png, task=germ["identity"]["purpose"],
                     build=build, source=source)
    return {"path": out_png, "germ": germ, "source": source,
            "host_files": len(host_census)}


def write_artifacts(result: Dict[str, Any], out_dir: str, *,
                    allow_host_nest: bool = False) -> Dict[str, str]:
    """Write APP_INVENTORY.md + assimilation_map.json NEXT TO the operator (never into
    the host tree). Returns the written paths."""
    host = os.path.realpath(result["dissection"]["root"])
    out_real = os.path.realpath(out_dir)
    if out_real == host or out_real.startswith(host + os.sep):
        nest_real = os.path.realpath(os.path.join(host, ".mantle"))
        if allow_host_nest and (out_real == nest_real or out_real.startswith(nest_real + os.sep)):
            pass
        else:
            raise ValueError("assimilation artifacts must be written outside the host tree: %s"
                             % out_dir)
    os.makedirs(out_dir, exist_ok=True)
    md = os.path.join(out_dir, "APP_INVENTORY.md")
    js = os.path.join(out_dir, "assimilation_map.json")
    with open(md, "w", encoding="utf-8") as f:
        f.write(result["inventory_md"])
    with open(js, "w", encoding="utf-8") as f:
        json.dump(result["map"], f, indent=2)
    coverage = result["map"].get("surface_coverage") or {}
    paths = {"inventory": md, "map": js}
    if coverage:
        cov = os.path.join(out_dir, "GUI_NERVE_COVERAGE.json")
        with open(cov, "w", encoding="utf-8") as f:
            json.dump(coverage, f, indent=2)
        paths["surface_coverage"] = cov
        cov_md = os.path.join(out_dir, "GUI_NERVE_COVERAGE.md")
        with open(cov_md, "w", encoding="utf-8") as f:
            f.write(render_surface_coverage_markdown(coverage))
        paths["surface_coverage_md"] = cov_md
    return paths
