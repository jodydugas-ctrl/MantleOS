#!/usr/bin/env python3
"""
mantle.assimilator.evidence -- resident host evidence index and consultation

Phase-0 dissection does not only produce a report for humans. A resident AppAI
needs a compact, machine-readable index it can consult before generic MIND chat.
This module keeps that shape canonical for assimilate, anchor, graft, spores, and
examples.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from ..resident.protocol import RESIDENT_RUNTIME_POLICIES, relevant_surface_slice
from .surface_coverage import build_surface_coverage, flatten_dissection_symbols


STOP_WORDS = frozenset(
    "how do i the a an to of in is what where which my this app use run does can "
    "you it for with and or me about tell explain software host your".split()
)


def build_host_evidence_index(amap: Dict[str, Any],
                              dissection: Dict[str, Any]) -> Dict[str, Any]:
    """Build the resident's local-first consultation index from Phase-0 evidence."""
    substrate = dissection.get("substrate") or amap.get("substrate") or {}
    surface_coverage = amap.get("surface_coverage")
    if not isinstance(surface_coverage, dict):
        symbols = flatten_dissection_symbols(dissection)
        surface_coverage = build_surface_coverage(symbols)
    organ_summary: Dict[str, Any] = {}
    for organ, syms in (amap.get("organs") or {}).items():
        roles = sorted({s.get("role", "unknown") for s in syms})
        organ_summary[organ] = {
            "count": len(syms),
            "roles": roles,
            "samples": [
                {
                    "symbol": s.get("symbol"),
                    "module": s.get("module"),
                    "line": s.get("line"),
                    "role": s.get("role"),
                }
                for s in syms[:8]
            ],
        }

    control_surfaces = [
        {
            "control": s.get("symbol"),
            "module": s.get("module"),
            "line": s.get("line"),
            "role": s.get("role"),
            "proof_requirement": (
                "attempted action plus body-owned verification before ok=true"
            ),
        }
        for s in (amap.get("organs") or {}).get("limbs", [])[:12]
    ]
    for surface in (surface_coverage.get("surfaces") or []):
        if surface.get("surface_type") not in {"action", "dynamic_surface"}:
            continue
        control_surfaces.append({
            "control": surface.get("id"),
            "module": surface.get("module"),
            "line": surface.get("line"),
            "role": "GUI_SURFACE",
            "vcw_status": surface.get("vcw_status"),
            "risk": surface.get("risk"),
            "proof_requirement": surface.get("proof_requirement"),
        })

    deduped_controls = []
    seen_controls = set()
    for control in control_surfaces:
        cid = control.get("control")
        if not cid or cid in seen_controls:
            continue
        seen_controls.add(cid)
        deduped_controls.append(control)
    control_surfaces = deduped_controls

    gaps = [
        {
            "source": g.get("module", g.get("symbol", "unknown")),
            "why": g.get("why", "unknown"),
        }
        for g in amap.get("gap_report", [])
    ]
    limitations: List[str] = []
    missing = amap.get("missing_organs") or []
    if missing:
        limitations.append(
            "Missing organ evidence: %s." % ", ".join(missing)
        )
    unsupported = substrate.get("unsupported") or []
    if unsupported:
        limitations.append(
            "Some host surfaces need adaptive parser/observer/verifier tools before "
            "instrumentation."
        )
    if not control_surfaces:
        limitations.append(
            "No Limb control surface was observed; effectful actions need an explicit "
            "ControlBridge before use."
        )
    missing_surfaces = [
        item.get("surface")
        for item in surface_coverage.get("maintenance_findings", [])
        if item.get("status") == "maintenance_gap"
    ]
    if missing_surfaces:
        limitations.append(
            "GUI nerve maintenance gaps remain for %d surface(s); they must be proposed "
            "to Body before any operability claim." % len(missing_surfaces)
        )
    body_test_plan = surface_coverage.get("body_test_plan") or []
    unproven_body_tests = [
        item for item in body_test_plan
        if item.get("current_status") != "verified_body_operation"
    ]
    if unproven_body_tests:
        limitations.append(
            "Systematic Body testing remains for %d user surface(s); outputs and "
            "state variables from each test must be written into VCW before the "
            "resident may treat them as truth." % len(unproven_body_tests)
        )

    return {
        "kind": "HOST_EVIDENCE_INDEX",
        "schema_version": "mantle-host-evidence-v2",
        "local_first_consultation": True,
        "host": amap.get("host") or dissection.get("root"),
        "host_identity": {
            "name": os.path.basename(amap.get("host") or dissection.get("root", "")),
            "python_files": dissection.get("python_files", 0),
            "multilang": bool(dissection.get("multilang")),
            "substrate_languages": substrate.get("languages", []),
            "build_files": substrate.get("build_files", [])[:12],
        },
        "evidence_sources": [
            "APP_INVENTORY.md",
            "assimilation_map.json",
            "substrate census",
            "organ map",
            "gap report",
            "control surface map",
        ],
        "organ_summary": organ_summary,
        "control_surfaces": control_surfaces,
        "surface_coverage_summary": {
            "kind": surface_coverage.get("kind"),
            "schema_version": surface_coverage.get("schema_version"),
            "total_surfaces": surface_coverage.get("total_surfaces", 0),
            "status_counts": surface_coverage.get("status_counts", {}),
            "type_counts": surface_coverage.get("type_counts", {}),
            "maintenance_findings": len(surface_coverage.get("maintenance_findings", [])),
            "body_test_plan_items": len(body_test_plan),
            "unproven_body_test_items": len(unproven_body_tests),
        },
        "runtime_policies": dict(RESIDENT_RUNTIME_POLICIES),
        "body_test_plan_summary": [
            {
                "surface": item.get("surface"),
                "phase": item.get("phase"),
                "risk": item.get("risk"),
                "current_status": item.get("current_status"),
                "vcw_requirement": item.get("vcw_requirement"),
                "output_requirement": item.get("output_requirement"),
                "commit_policy": item.get("commit_policy"),
                "commit_requirement": item.get("commit_requirement"),
            }
            for item in body_test_plan[:40]
        ],
        "gaps": gaps,
        "limitations": limitations,
        "consultation_contract": {
            "answer_host_questions_from": [
                "host_identity",
                "organ_summary",
                "control_surfaces",
                "surface_coverage_summary",
                "gaps",
                "limitations",
            ],
            "provider_mind_role": (
                "may reason over resident evidence after Phase-2 authorization; "
                "must not replace the evidence index"
            ),
            "missing_evidence_policy": "name the gap instead of guessing",
            "command_channel_policy": RESIDENT_RUNTIME_POLICIES["command_channel_policy"],
            "body_command_policy": RESIDENT_RUNTIME_POLICIES["body_command_policy"],
            "mind_body_lane_policy": RESIDENT_RUNTIME_POLICIES["mind_body_lane_policy"],
            "directive_fail_closed_policy": RESIDENT_RUNTIME_POLICIES["directive_fail_closed_policy"],
            "transcript_vcw_policy": RESIDENT_RUNTIME_POLICIES["transcript_vcw_policy"],
            "secret_boundary_policy": RESIDENT_RUNTIME_POLICIES["secret_boundary_policy"],
            "surface_retrieval_policy": RESIDENT_RUNTIME_POLICIES["surface_retrieval_policy"],
            "body_proof_policy": RESIDENT_RUNTIME_POLICIES["body_proof_policy"],
            "text_commit_policy": RESIDENT_RUNTIME_POLICIES["text_commit_policy"],
            "mind_context_rehydration_policy": RESIDENT_RUNTIME_POLICIES["mind_context_rehydration_policy"],
            "heartbeat_scheduler_policy": RESIDENT_RUNTIME_POLICIES["heartbeat_scheduler_policy"],
            "effectful_action_policy": (
                "plain-English host-surface requests are interpreted by the resident "
                "MIND against mapped SELF/body evidence; effectful operations require "
                "Body-owned Action Execution Proof"
            ),
            "working_surface_policy": (
                "active documents, tabs, panels, canvases, sheets, routes, and other "
                "working surfaces are host-specific anatomy discovered from GUI "
                "coverage or live Body evidence and recorded into the VCW; they are "
                "not implied by Mantle's universal Body maintenance commands"
            ),
            "systematic_body_test_policy": (
                "after Body birth, every mapped user surface is systematically probed "
                "through a safe Body nerve or observer; action proof, visible output, "
                "state variables, and any resulting working-surface changes are "
                "recorded into VCW"
            ),
            "output_truth_policy": (
                "displays, files, clipboard values, dialogs, status text, emitted "
                "events, and relevant variables are not known to the resident unless "
                "they are represented in VCW"
            ),
            "creative_work_policy": (
                "creative/generative content must be authored by the resident MIND, "
                "never by Body reflexes; Body may only place or verify MIND-authored "
                "or user-literal content"
            ),
            "reset_policy": (
                "resident VCW resets must be explicit maintenance commands that "
                "recreate Prime from current evidence and clear transient runtime "
                "residue"
            ),
        },
    }


def answer_from_host_evidence(question: str, amap: Dict[str, Any]) -> str:
    """Deterministic resident answer from the canonical host evidence index."""
    index = amap.get("host_evidence_index")
    if not isinstance(index, dict):
        index = build_host_evidence_index(amap, {
            "root": amap.get("host"),
            "python_files": 0,
            "multilang": False,
            "substrate": amap.get("substrate") or {},
        })

    lowered = question.lower()
    if any(word in lowered for word in ("limit", "cannot", "gap", "unsupported")):
        lines = ["Known host evidence limits:"]
        for item in index.get("limitations") or ["No limitations recorded."]:
            lines.append("- %s" % item)
        for gap in index.get("gaps", [])[:6]:
            lines.append("- %s: %s" % (gap.get("source"), gap.get("why")))
        return "\n".join(lines)

    if any(word in lowered for word in ("control", "action", "limb", "body", "can you do")):
        controls = index.get("control_surfaces") or []
        if not controls:
            return (
                "I have no verified Limb controls in my Phase-0 evidence yet. A Body "
                "operation needs a ControlBridge and post-action proof before ok=true."
            )
        surface_summary = index.get("surface_coverage_summary") or {}
        lines = ["Observed Body/Limb controls from local evidence:"]
        if surface_summary:
            lines.append("- GUI surfaces: %s; statuses: %s" % (
                surface_summary.get("total_surfaces", 0),
                surface_summary.get("status_counts", {}),
            ))
            lines.append("- Systematic Body tests: %s planned; %s unproven" % (
                surface_summary.get("body_test_plan_items", 0),
                surface_summary.get("unproven_body_test_items", 0),
            ))
        surface_coverage = amap.get("surface_coverage") or {}
        matches = relevant_surface_slice(surface_coverage, question, limit=6)
        if matches:
            lines.append("Relevant surfaces from complete coverage:")
            for surface in matches:
                lines.append("- `%s` label=%r status=%s risk=%s" % (
                    surface.get("id"),
                    surface.get("label"),
                    surface.get("vcw_status"),
                    surface.get("risk"),
                ))
        for c in controls[:8]:
            status = c.get("vcw_status") or c.get("role")
            lines.append("- `%s` at %s:%s [%s]" % (
                c.get("control"), c.get("module"), c.get("line"), status))
        lines.append("Every control must produce Action Execution Proof before success.")
        contract = index.get("consultation_contract", {})
        if contract.get("command_channel_policy"):
            lines.append(contract["command_channel_policy"])
        if contract.get("mind_body_lane_policy"):
            lines.append(contract["mind_body_lane_policy"])
        if contract.get("directive_fail_closed_policy"):
            lines.append(contract["directive_fail_closed_policy"])
        if contract.get("transcript_vcw_policy"):
            lines.append(contract["transcript_vcw_policy"])
        if contract.get("secret_boundary_policy"):
            lines.append(contract["secret_boundary_policy"])
        if contract.get("surface_retrieval_policy"):
            lines.append(contract["surface_retrieval_policy"])
        if contract.get("body_proof_policy"):
            lines.append(contract["body_proof_policy"])
        if contract.get("text_commit_policy"):
            lines.append(contract["text_commit_policy"])
        if contract.get("mind_context_rehydration_policy"):
            lines.append(contract["mind_context_rehydration_policy"])
        if contract.get("heartbeat_scheduler_policy"):
            lines.append(contract["heartbeat_scheduler_policy"])
        if contract.get("effectful_action_policy"):
            lines.append(contract["effectful_action_policy"])
        if contract.get("working_surface_policy"):
            lines.append(contract["working_surface_policy"])
        if contract.get("systematic_body_test_policy"):
            lines.append(contract["systematic_body_test_policy"])
        if contract.get("output_truth_policy"):
            lines.append(contract["output_truth_policy"])
        if contract.get("creative_work_policy"):
            lines.append(contract["creative_work_policy"])
        if contract.get("reset_policy"):
            lines.append(contract["reset_policy"])
        return "\n".join(lines)

    tokens = [t for t in re.findall(r"[a-z_]+", lowered) if t not in STOP_WORDS]
    scored: List[tuple] = []
    for organ, summary in (index.get("organ_summary") or {}).items():
        for sample in summary.get("samples", []):
            hay = ("%s %s %s %s" % (
                organ, sample.get("symbol"), sample.get("module"), sample.get("role")
            )).lower()
            score = sum(2 if t in str(sample.get("symbol", "")).lower() else 1
                        for t in tokens if t in hay)
            if score:
                scored.append((score, organ, sample))
    scored.sort(key=lambda item: -item[0])

    lines: List[str] = []
    if scored:
        lines.append("From my host evidence index (observed, not guessed):")
        for _score, organ, sample in scored[:6]:
            lines.append("- %s: `%s` at %s:%s [%s]" % (
                organ,
                sample.get("symbol"),
                sample.get("module"),
                sample.get("line"),
                sample.get("role"),
            ))
    else:
        host_identity = index.get("host_identity") or {}
        languages = host_identity.get("substrate_languages") or ["unknown substrate"]
        lines.append("A structural overview of my host from local evidence:")
        lines.append("- host: %s" % (host_identity.get("name") or index.get("host")))
        lines.append("- substrate: %s" % ", ".join(languages))
        for organ, summary in (index.get("organ_summary") or {}).items():
            count = summary.get("count", 0)
            samples = ", ".join(
                str(s.get("symbol")) for s in summary.get("samples", [])[:4]
                if s.get("symbol")
            )
            lines.append("- %s: %d symbol(s)%s" % (
                organ, count, (": " + samples) if samples else ""))
    if index.get("limitations"):
        lines.append("Limits: %s" % " ".join(index["limitations"][:2]))
    return "\n".join(lines)
