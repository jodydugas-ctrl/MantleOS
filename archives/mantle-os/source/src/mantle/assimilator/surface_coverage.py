#!/usr/bin/env python3
"""GUI/control surface coverage for assimilation evidence.

The surface inventory is the AppAI's nerve map: every visible affordance should
be known, connected to evidence when possible, and left as an explicit
maintenance finding when it is not yet proven.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List


SURFACE_KINDS = {"ui-action", "ui-widget", "ui-menu", "ui-toolbar"}
DESTRUCTIVE_HINTS = (
    "delete", "trash", "remove", "clear", "close", "exit", "quit", "print",
    "save", "reload", "rename", "update", "install",
)
OUTPUTFUL_HINTS = (
    "open", "new", "save", "reload", "print", "export", "find", "replace",
    "copy", "paste", "undo", "redo", "zoom", "split", "show", "hide",
    "toggle", "select", "sort", "convert", "format", "run", "record",
)
TEXT_INPUT_HINTS = (
    "edit", "editor", "text", "textbox", "lineedit", "textedit", "plaintextedit",
    "scintilla", "prompt", "search", "replace", "input",
)


def normalize_surface_id(value: Any) -> str:
    text = str(value or "").strip()
    for prefix in ("&", "ui->"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    if "::" in text:
        text = text.rsplit("::", 1)[-1]
    if "." in text and text.split(".", 1)[0].startswith("Q"):
        text = text.split(".", 1)[1]
    return text.strip()


def flatten_dissection_symbols(dissection: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for file_rec in dissection.get("files", []):
        module = file_rec.get("module")
        for sym in file_rec.get("symbols", []):
            rec = dict(sym)
            rec.setdefault("module", module)
            out.append(rec)
    return out


def _surface_type(kind: str, class_name: str = "") -> str:
    if kind == "ui-action":
        return "action"
    if kind == "ui-menu":
        return "menu"
    if kind == "ui-toolbar":
        return "toolbar"
    if class_name:
        return "widget:%s" % class_name
    return "widget"


def _edge_surface_id(edge: Dict[str, Any]) -> str:
    return normalize_surface_id(edge.get("sender") or edge.get("surface"))


def _is_not_implemented(surface_id: str, label: str, edges: List[Dict[str, Any]]) -> bool:
    low = ("%s %s %s" % (
        surface_id,
        label,
        " ".join(str(edge.get("slot", "")) for edge in edges),
    )).lower()
    return "not implemented" in low or "not_currently_implemented" in low


def _is_risky(surface_id: str, label: str) -> bool:
    low = ("%s %s" % (surface_id, label)).lower()
    return any(hint in low for hint in DESTRUCTIVE_HINTS)


def _may_emit_output(surface_id: str, label: str, surface_type: str) -> bool:
    low = ("%s %s %s" % (surface_id, label, surface_type)).lower()
    return surface_type.startswith(("menu", "toolbar", "widget")) or any(
        hint in low for hint in OUTPUTFUL_HINTS
    )


def _text_commit_policy(surface_id: str, label: str, surface_type: str,
                        class_name: str = "") -> str:
    low = ("%s %s %s %s" % (surface_id, label, surface_type, class_name)).lower()
    if any(hint in low for hint in TEXT_INPUT_HINTS):
        return "submit_or_blur"
    return ""


def _surface_test_plan(surface: Dict[str, Any]) -> Dict[str, Any]:
    risk = surface.get("risk")
    may_emit_output = _may_emit_output(
        str(surface.get("id") or ""),
        str(surface.get("label") or ""),
        str(surface.get("surface_type") or ""),
    )
    if surface.get("vcw_status") == "verified_body_operation":
        phase = "regression"
    elif risk == "guarded":
        phase = "guarded_probe"
    else:
        phase = "systematic_probe"
    return {
        "surface": surface.get("id"),
        "phase": phase,
        "risk": risk,
        "nerve_requirement": (
            "register a Body nerve or explicit observer for this surface; no MIND "
            "operability claim is allowed until the nerve writes proof to VCW"
        ),
        "pre_state_requirement": (
            "snapshot reachable state/display variables before interaction and write "
            "the observation to VCW"
        ),
        "action_requirement": (
            "operate through the user-facing surface or a host-native equivalent; "
            "destructive/guarded surfaces require a safe fixture or dry-run harness"
        ),
        "output_requirement": (
            "capture all visible outputs, dialogs, document/view changes, emitted "
            "status text, files/clipboard changes, and relevant state variables into VCW"
            if may_emit_output else
            "record that no user-visible output channel is expected, then verify by "
            "post-action observation"
        ),
        "post_state_requirement": (
            "read back the body state/output after interaction; ok=true requires "
            "post-action evidence, not merely a non-throwing call"
        ),
        "vcw_requirement": (
            "write USER_SURFACE_TEST, BODY_ACTION_PROOF, and SURFACE_OUTPUT_OBSERVED "
            "events into the current Prime VCW"
        ),
        "commit_policy": surface.get("commit_policy", ""),
        "commit_requirement": (
            "for text input surfaces, do not record every keypress; write one "
            "HOST_TEXT_COMMIT event on submit, blur/focus-loss, declared host "
            "commit boundary, or explicit Body readback"
            if surface.get("commit_policy") == "submit_or_blur" else ""
        ),
        "current_status": surface.get("vcw_status"),
    }


def build_systematic_body_test_plan(surfaces: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_surface_test_plan(surface) for surface in surfaces]


def build_surface_coverage(symbols: Iterable[Dict[str, Any]],
                           edges: Iterable[Dict[str, Any]] | None = None,
                           *,
                           verified_controls: Iterable[str] | None = None,
                           observer_controls: Iterable[str] | None = None) -> Dict[str, Any]:
    """Return a machine-readable GUI nerve coverage matrix."""
    verified = {normalize_surface_id(c) for c in (verified_controls or [])}
    observed = {normalize_surface_id(c) for c in (observer_controls or [])}
    by_id: Dict[str, Dict[str, Any]] = {}
    all_edges = list(edges or [])

    for sym in symbols:
        kind = sym.get("kind")
        if kind not in SURFACE_KINDS:
            continue
        sid = normalize_surface_id(sym.get("surface_id") or sym.get("symbol"))
        if not sid:
            continue
        rec = by_id.setdefault(sid, {
            "id": sid,
            "surface_type": _surface_type(kind, sym.get("class", "")),
            "label": sym.get("label") or sym.get("text") or sid,
            "module": sym.get("module"),
            "line": sym.get("line"),
            "kind": kind,
            "class": sym.get("class"),
            "shortcut": sym.get("shortcut", ""),
            "placements": [],
            "connection_evidence": [],
        })
        for placement in sym.get("placements", []):
            if placement and placement not in rec["placements"]:
                rec["placements"].append(placement)

    for edge in all_edges:
        sid = _edge_surface_id(edge)
        if not sid:
            continue
        rec = by_id.setdefault(sid, {
            "id": sid,
            "surface_type": "dynamic_surface",
            "label": sid,
            "module": edge.get("module"),
            "line": edge.get("line"),
            "kind": "dynamic-signal",
            "class": "",
            "shortcut": "",
            "placements": [],
            "connection_evidence": [],
        })
        proof = {
            "kind": edge.get("kind", "connection"),
            "module": edge.get("module"),
            "line": edge.get("line"),
            "signal": edge.get("signal"),
            "slot": edge.get("slot"),
            "raw": edge.get("raw"),
        }
        if proof not in rec["connection_evidence"]:
            rec["connection_evidence"].append(proof)
        observed.add(sid)

    surfaces = []
    maintenance_findings = []
    for sid in sorted(by_id):
        rec = by_id[sid]
        edges_for_surface = rec["connection_evidence"]
        if sid in verified:
            status = "verified_body_operation"
        elif _is_not_implemented(sid, rec.get("label", ""), edges_for_surface):
            status = "not_implemented"
        elif sid in observed or edges_for_surface:
            status = "observer_registered"
        elif rec["surface_type"].startswith(("menu", "toolbar", "widget")):
            status = "sense_only"
        else:
            status = "maintenance_gap"
        rec["vcw_status"] = status
        rec["risk"] = "guarded" if _is_risky(sid, rec.get("label", "")) else "low"
        rec["commit_policy"] = _text_commit_policy(
            sid, rec.get("label", ""), rec.get("surface_type", ""), rec.get("class", "")
        )
        rec["proof_requirement"] = (
            "observed in surface inventory plus connection evidence; ok=true requires "
            "Body operation and post-action readback"
        )
        rec["attempted"] = bool(edges_for_surface or sid in verified or sid in observed)
        rec["verified"] = status == "verified_body_operation"
        surfaces.append(rec)
        if status != "verified_body_operation":
            maintenance_findings.append({
                "surface": sid,
                "status": status,
                "risk": rec["risk"],
                "proposal": (
                    "MIND may propose a Body nerve or verifier; Body must implement and "
                    "prove it before this surface is claimed as operable."
                ),
            })

    status_counts = Counter(s["vcw_status"] for s in surfaces)
    type_counts = Counter(s["surface_type"].split(":", 1)[0] for s in surfaces)
    body_test_plan = build_systematic_body_test_plan(surfaces)
    return {
        "kind": "GUI_NERVE_COVERAGE",
        "schema_version": "mantle-gui-nerve-coverage-v3",
        "total_surfaces": len(surfaces),
        "status_counts": dict(status_counts),
        "type_counts": dict(type_counts),
        "surfaces": surfaces,
        "maintenance_findings": maintenance_findings,
        "body_test_plan": body_test_plan,
        "working_surface_types": sorted(type_counts),
        "vocabulary_aliases": {},
        "creative_work_policy": (
            "MIND authors creative material; Body may place, save, render, and verify it"
        ),
        "contract": {
            "no_silent_gui_omission": True,
            "all_user_surfaces_require_body_tests": True,
            "all_outputs_must_enter_vcw": True,
            "known_surface_policy": (
                "every discovered GUI surface is classified as verified, observer-only, "
                "sense-only, not implemented, or a maintenance gap"
            ),
            "systematic_body_test_policy": (
                "after initial Body birth, Body must systematically probe every mapped "
                "user-manipulable surface with safe fixtures/dry-runs for guarded "
                "surfaces, attach a nerve or explicit observer, capture outputs and "
                "state variables, and write proofs into VCW"
            ),
            "effectful_claim_policy": (
                "resident may claim operation only with Body-owned Action Execution Proof"
            ),
            "output_truth_policy": (
                "visible outputs, dialogs, files, clipboard changes, status text, "
                "document/view changes, emitted events, and relevant variables are "
                "truth only after they are recorded into VCW"
            ),
            "text_commit_policy": (
                "text inputs use commit_policy=submit_or_blur: keypresses are "
                "transient Senses activity, while submit, blur/focus-loss, declared "
                "host commit boundaries, or explicit Body readback create durable "
                "HOST_TEXT_COMMIT entries"
            ),
            "working_surface_policy": (
                "tabs/documents/views are recorded only when the host declares them or "
                "Body observes them, then mirrored into SELF/VCW state; no generic app "
                "is assumed to have a tab surface"
            ),
        },
    }


def render_surface_coverage_markdown(coverage: Dict[str, Any],
                                     title: str = "GUI Nerve Coverage") -> str:
    lines = [
        "# %s" % title,
        "",
        "- **Schema:** `%s`" % coverage.get("schema_version", "unknown"),
        "- **Total GUI surfaces:** %s" % coverage.get("total_surfaces", 0),
        "- **No silent GUI omission:** `%s`" % str(
            coverage.get("contract", {}).get("no_silent_gui_omission", False)
        ).lower(),
        "- **All user surfaces require Body tests:** `%s`" % str(
            coverage.get("contract", {}).get("all_user_surfaces_require_body_tests", False)
        ).lower(),
        "- **All outputs must enter VCW:** `%s`" % str(
            coverage.get("contract", {}).get("all_outputs_must_enter_vcw", False)
        ).lower(),
        "- **Text commit policy:** %s" % (
            coverage.get("contract", {}).get("text_commit_policy", "not declared")
        ),
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status, count in sorted((coverage.get("status_counts") or {}).items()):
        lines.append("| %s | %s |" % (status, count))
    lines += [
        "",
        "## Type Counts",
        "",
        "| Type | Count |",
        "|---|---:|",
    ]
    for typ, count in sorted((coverage.get("type_counts") or {}).items()):
        lines.append("| %s | %s |" % (typ, count))
    lines += [
        "",
        "## Surface Samples",
        "",
        "| Surface | Type | Status | Risk | Commit | Evidence |",
        "|---|---|---|---|---|---:|",
    ]
    for surface in (coverage.get("surfaces") or [])[:60]:
        lines.append("| `%s` | %s | %s | %s | %s | %d |" % (
            surface.get("id"),
            surface.get("surface_type"),
            surface.get("vcw_status"),
            surface.get("risk"),
            surface.get("commit_policy") or "",
            len(surface.get("connection_evidence") or []),
        ))
    findings = coverage.get("maintenance_findings") or []
    lines += [
        "",
        "## Maintenance Findings",
        "",
        "Unverified surfaces are explicit DREAM/MAINTENANCE work items. The MIND may",
        "propose a Body nerve or verifier, but Body must implement and prove it before",
        "the surface is claimed as operable.",
        "",
    ]
    if findings:
        for finding in findings[:80]:
            lines.append("- `%s`: %s (%s)" % (
                finding.get("surface"),
                finding.get("status"),
                finding.get("risk"),
            ))
        if len(findings) > 80:
            lines.append("- ... and %d more" % (len(findings) - 80))
    else:
        lines.append("- none")
    plan = coverage.get("body_test_plan") or []
    lines += [
        "",
        "## Systematic Body Test Plan",
        "",
        "Every user-manipulable surface needs a Body nerve or explicit observer,",
        "safe action proof, output/state capture, and VCW writeback. Guarded",
        "surfaces require a fixture or dry-run harness before operation.",
        "",
        "| Surface | Phase | Risk | VCW Status |",
        "|---|---|---|---|",
    ]
    for item in plan[:80]:
        lines.append("| `%s` | %s | %s | %s |" % (
            item.get("surface"),
            item.get("phase"),
            item.get("risk"),
            item.get("current_status"),
        ))
    if len(plan) > 80:
        lines.append("| ... | ... | ... | %d more |" % (len(plan) - 80))
    return "\n".join(lines) + "\n"
