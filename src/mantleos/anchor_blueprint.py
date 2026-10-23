"""Anchor Blueprint contracts: self-describing semantic IR for project/software meaning.

An Anchor Blueprint describes source semantics only: behavior, invariants, effects, authority,
failures, workflows, evidence, and acceptance contracts. It deliberately contains no Persona,
PRIMER, continuity policy, or Bio-Software identity. Those belong to a separate birth contract.
The Blueprint is intentionally readable by a capable LLM that has never seen MantleOS.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .scan.scanner import verify_report
from . import anchors as model

SCHEMA = "anchor.blueprint/3"
ID_RE = re.compile(r"[a-z][a-z0-9_.-]{0,95}$")
BODY_ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,47}$")
SYSTEM_IDS = {
    "system.neural",
    "system.memory",
    "system.immune",
    "system.metabolism",
    "system.expression",
}
EFFECT_CLASSES = {"READ", "COMPUTE", "MUTATE", "PUBLISH", "EXTERNAL"}
ATTRIBUTE_ROLES = {
    "NEUTRAL",
    "ATTRACTOR",
    "REPULSOR",
    "INVARIANT",
    "TRANSFORMATION",
    "EFFECT",
    "LIFECYCLE",
    "AUTHORITY",
    "FAILURE",
    "OBSERVABLE",
}
ANCHOR_STATUSES = {"SOURCE_OBSERVED", "INFERRED_SUPPORTED", "INFERRED_UNVERIFIED"}

ANCHOR_RULES = [
    "Every Anchor applies a source-defined immutable singularity; its contextual statement, evidence, depth and dependencies are attributes.",
    "Only BlackHole, WhiteHole and Neutral are Anchor types. The kind field classifies an application attribute, never a new Anchor type or singularity.",
    "INVARIANT must remain true across the declared scope. TRANSFORMATION relates explicit before/after state. EFFECT requires a declared system interface.",
    "AUTHORITY limits who or what may request an effect. FAILURE describes behavior that must remain explicit rather than being silently converted into success.",
    "UNKNOWN or missing information must not be invented. Preserve uncertainty until evidence resolves it.",
    "Implementation examples are replaceable unless an anchor explicitly makes an implementation detail observable.",
]

EXECUTION_PROTOCOL = [
    "Read this Blueprint before attempting the represented workflow; no prior MantleOS or AnchorCode knowledge is required.",
    "Select a workflow matching the requested outcome. Resolve every referenced anchor and required input before acting.",
    "Evaluate REPULSOR, INVARIANT, AUTHORITY, and FAILURE obligations before requesting consequential effects.",
    "Use only interfaces declared in systems. Follow each interface's input/output/usage/verification contract.",
    "Treat an intended or attempted effect as incomplete until the declared verification condition is satisfied by an observation.",
    "After each consequential step, compare the observed result with the step's anchors and workflow success conditions.",
    "If a required anchor, interface, authority, or value cannot be resolved, stop that path and report the unresolved dependency rather than improvising it.",
]

EVIDENCE_PROTOCOL = [
    "Source evidence supports why an anchor exists; it does not by itself prove every runtime behavior.",
    "Do not upgrade INFERRED_UNVERIFIED anchors to facts without additional evidence.",
    "A successful external effect requires an observation satisfying the declared verifier; model confidence is not effect evidence.",
    "Acceptance contracts define observable behavior that a synthesized implementation must preserve.",
]


def apply_obligation(identifier, statement, *, definition_id='Neutral', kind='INVARIANT',
                     status='INFERRED_UNVERIFIED', requires=(), guarantees=(), evidence=()):
    """Project view of the same Anchor; obligations are contextual attributes."""
    base = model.definition(definition_id)
    return {'id': identifier, 'definition_id': base.id, 'type': base.type,
            'singularity': base.singularity, 'kind': kind, 'status': status,
            'statement': statement, 'requires': list(requires), 'guarantees': list(guarantees),
            'evidence': list(evidence)}


def _digest(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def _string_list(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{label} must be {'a non-empty ' if nonempty else ''}list")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{label} must contain non-empty strings")
    return value


def validate_blueprint(value: dict, *, require_ready: bool = False) -> dict:
    """Validate an Anchor Blueprint and cross-reference its semantic contracts.

    This is deliberately dependency-free validation. The JSON schema in spec/schemas is
    documentation/tooling support; these checks enforce the invariants used by the runtime.
    """
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError(f"Expected {SCHEMA}")
    required = {
        "schema", "id", "name", "version", "status", "purpose", "source",
        "bootstrap", "systems", "anchors", "workflows", "acceptance_contracts", "unknowns",
    }
    missing = required - set(value)
    if missing:
        raise ValueError(f"Anchor Blueprint missing fields: {sorted(missing)}")
    extra = set(value) - (required | {"discovery"})
    if extra:
        raise ValueError(f"Anchor Blueprint has unknown top-level fields: {sorted(extra)}")
    if not isinstance(value["id"], str) or not BODY_ID_RE.fullmatch(value["id"]):
        raise ValueError(f"Invalid blueprint id: {value['id']!r}")
    _nonempty_text(value["name"], "name")
    _nonempty_text(value["version"], "version")
    _nonempty_text(value["purpose"], "purpose")
    if value["status"] not in {"DRAFT", "READY"}:
        raise ValueError("Blueprint status must be DRAFT or READY")
    if require_ready and value["status"] != "READY":
        raise ValueError("A Bio-Software build requires a READY Anchor Blueprint")

    source = value["source"]
    if not isinstance(source, dict):
        raise ValueError("source must be an object")
    for field in ("kind", "locator", "source_digest"):
        _nonempty_text(source.get(field), f"source.{field}")
    if not re.fullmatch(r"[0-9a-f]{64}", source["source_digest"]):
        raise ValueError("source.source_digest must be a sha256 hex digest")
    if source.get("scan_graph_digest") is not None and not re.fullmatch(r"[0-9a-f]{64}", str(source["scan_graph_digest"])):
        raise ValueError("source.scan_graph_digest must be null or a sha256 hex digest")


    bootstrap = value["bootstrap"]
    if not isinstance(bootstrap, dict):
        raise ValueError("bootstrap must be an object")
    if bootstrap.get("audience") != "mantle-naive-llm":
        raise ValueError("bootstrap.audience must be mantle-naive-llm")
    _nonempty_text(bootstrap.get("purpose"), "bootstrap.purpose")
    _string_list(bootstrap.get("anchor_rules"), "bootstrap.anchor_rules", nonempty=True)
    _string_list(bootstrap.get("execution_protocol"), "bootstrap.execution_protocol", nonempty=True)
    _string_list(bootstrap.get("evidence_protocol"), "bootstrap.evidence_protocol", nonempty=True)
    _nonempty_text(bootstrap.get("completion_rule"), "bootstrap.completion_rule")

    systems = value["systems"]
    if not isinstance(systems, list):
        raise ValueError("systems must be a list")
    system_ids: set[str] = set()
    interfaces: dict[str, dict] = {}
    for system in systems:
        if not isinstance(system, dict):
            raise ValueError("system contracts must be objects")
        sid = system.get("id")
        if sid not in SYSTEM_IDS or sid in system_ids:
            raise ValueError(f"Invalid or duplicate system id: {sid!r}")
        system_ids.add(sid)
        _nonempty_text(system.get("purpose"), f"{sid}.purpose")
        if not isinstance(system.get("interfaces"), list):
            raise ValueError(f"{sid}.interfaces must be a list")
        for interface in system["interfaces"]:
            if not isinstance(interface, dict):
                raise ValueError(f"{sid} interface must be an object")
            name = _id(interface.get("name"), "interface name")
            if name in interfaces:
                raise ValueError(f"Duplicate interface name: {name}")
            if interface.get("effect") not in EFFECT_CLASSES:
                raise ValueError(f"Invalid effect class for {name}")
            authority = interface.get("authority")
            if authority is not None:
                _id(authority, f"authority for {name}")
            _nonempty_text(interface.get("provider"), f"{name}.provider")
            _nonempty_text(interface.get("usage"), f"{name}.usage")
            if not isinstance(interface.get("input"), dict) or not isinstance(interface.get("output"), dict):
                raise ValueError(f"{name} input/output must be objects")
            _nonempty_text(interface.get("verification"), f"{name}.verification")
            interfaces[name] = interface

    anchors = value["anchors"]
    if not isinstance(anchors, list):
        raise ValueError("anchors must be a list")
    anchor_ids: set[str] = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise ValueError("anchors must contain objects")
        aid = _id(anchor.get("id"), "anchor id")
        if aid in anchor_ids:
            raise ValueError(f"Duplicate anchor id: {aid}")
        anchor_ids.add(aid)
        model.validate_binding(anchor)
        if anchor.get("kind") not in ATTRIBUTE_ROLES:
            raise ValueError(f"Invalid Anchor attribute role: {anchor.get('kind')!r}")
        if anchor.get("status") not in ANCHOR_STATUSES:
            raise ValueError(f"Invalid anchor status for {aid}")
        _nonempty_text(anchor.get("statement"), f"{aid}.statement")
        _string_list(anchor.get("requires"), f"{aid}.requires")
        _string_list(anchor.get("guarantees"), f"{aid}.guarantees")
        evidence = anchor.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError(f"{aid}.evidence must be a list")
        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError(f"{aid}.evidence items must be objects")
            _nonempty_text(item.get("path"), f"{aid}.evidence.path")
            if item.get("sha256") is not None and not re.fullmatch(r"[0-9a-f]{64}", str(item["sha256"])):
                raise ValueError(f"{aid}.evidence.sha256 must be a sha256 digest")
        if require_ready:
            if anchor["status"] == "INFERRED_UNVERIFIED":
                raise ValueError(f"READY Blueprint contains unverified anchor: {aid}")
            if not evidence:
                raise ValueError(f"READY Blueprint anchor lacks evidence: {aid}")

    # Anchor dependencies must resolve after all IDs are known.
    for anchor in anchors:
        unresolved = sorted(set(anchor["requires"]) - anchor_ids)
        if unresolved:
            raise ValueError(f"Anchor {anchor['id']} requires unknown anchors: {unresolved}")

    workflows = value["workflows"]
    if not isinstance(workflows, list):
        raise ValueError("workflows must be a list")
    workflow_ids: set[str] = set()
    for flow in workflows:
        if not isinstance(flow, dict):
            raise ValueError("workflows must contain objects")
        fid = _id(flow.get("id"), "workflow id")
        if fid in workflow_ids:
            raise ValueError(f"Duplicate workflow id: {fid}")
        workflow_ids.add(fid)
        _nonempty_text(flow.get("purpose"), f"{fid}.purpose")
        steps = flow.get("steps")
        if not isinstance(steps, list) or (require_ready and not steps):
            raise ValueError(f"{fid}.steps must be {'non-empty ' if require_ready else ''}list")
        _string_list(flow.get("success"), f"{fid}.success", nonempty=require_ready)
        _string_list(flow.get("failures"), f"{fid}.failures")
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError(f"{fid} steps must be objects")
            sid = step.get("anchor")
            if sid not in anchor_ids:
                raise ValueError(f"Workflow {fid} references unknown anchor: {sid!r}")
            _nonempty_text(step.get("instruction"), f"{fid}.step.instruction")
            interface = step.get("interface")
            if interface is not None and interface not in interfaces:
                raise ValueError(f"Workflow {fid} references unknown interface: {interface!r}")

    contracts = value["acceptance_contracts"]
    if not isinstance(contracts, list):
        raise ValueError("acceptance_contracts must be a list")
    contract_ids: set[str] = set()
    for contract in contracts:
        if not isinstance(contract, dict):
            raise ValueError("acceptance_contracts must contain objects")
        cid = _id(contract.get("id"), "acceptance contract id")
        if cid in contract_ids:
            raise ValueError(f"Duplicate acceptance contract id: {cid}")
        contract_ids.add(cid)
        _nonempty_text(contract.get("statement"), f"{cid}.statement")
        refs = _string_list(contract.get("anchors"), f"{cid}.anchors", nonempty=require_ready)
        unresolved = sorted(set(refs) - anchor_ids)
        if unresolved:
            raise ValueError(f"Acceptance contract {cid} references unknown anchors: {unresolved}")
        evidence = contract.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError(f"{cid}.evidence must be a list")
        _nonempty_text(contract.get("test_hint"), f"{cid}.test_hint")
        if require_ready and not evidence:
            raise ValueError(f"READY acceptance contract lacks evidence: {cid}")

    unknowns = value["unknowns"]
    if not isinstance(unknowns, list):
        raise ValueError("unknowns must be a list")
    for unknown in unknowns:
        if not isinstance(unknown, dict):
            raise ValueError("unknowns must contain objects")
        _id(unknown.get("id"), "unknown id")
        _nonempty_text(unknown.get("statement"), "unknown.statement")
        if type(unknown.get("blocking")) is not bool:
            raise ValueError("unknown.blocking must be boolean")
        if require_ready and unknown["blocking"]:
            raise ValueError(f"READY Blueprint contains blocking unknown: {unknown['id']}")

    if require_ready:
        if not anchors:
            raise ValueError("READY Blueprint requires at least one semantic anchor")
        if not workflows:
            raise ValueError("READY Blueprint requires at least one workflow")
        if not contracts:
            raise ValueError("READY Blueprint requires at least one acceptance contract")

    result = deepcopy(value)
    result["blueprint_sha256"] = _digest(value)
    return result


def completion_report(value: dict) -> dict:
    bp = validate_blueprint(value)
    blocking = [u["id"] for u in bp["unknowns"] if u["blocking"]]
    unverified = [a["id"] for a in bp["anchors"] if a["status"] == "INFERRED_UNVERIFIED"]
    ready_error = None
    if bp["status"] == "READY":
        try:
            validate_blueprint(value, require_ready=True)
        except ValueError as exc:
            ready_error = str(exc)
    ready = bp["status"] == "READY" and not blocking and not unverified and ready_error is None
    return {
        "schema": "anchor.blueprint-validation/2",
        "blueprint_id": bp["id"],
        "blueprint_sha256": bp["blueprint_sha256"],
        "declared_status": bp["status"],
        "synthesis_ready": ready,
        "mantle_naive_llm_bootstrap": True,
        "counts": {
            "systems": len(bp["systems"]),
            "interfaces": sum(len(s["interfaces"]) for s in bp["systems"]),
            "anchors": len(bp["anchors"]),
            "workflows": len(bp["workflows"]),
            "acceptance_contracts": len(bp["acceptance_contracts"]),
            "unknowns": len(bp["unknowns"]),
        },
        "blocking_unknowns": blocking,
        "unverified_anchors": unverified,
        "ready_error": ready_error,
    }


def _evidence_candidates(report: dict, limit: int = 250) -> list[dict]:
    files = {f["path"]: f for f in report["graph"]["files"]}
    candidates = []
    priority = {
        "function": 0, "class": 1, "route": 2, "command": 2, "config_key": 3,
        "import": 5, "call": 6, "loop": 7, "module": 8,
    }
    for node in report["graph"]["nodes"]:
        kind = node.get("kind", "node")
        if kind not in priority:
            continue
        entry = {
            "node_id": node.get("id"),
            "path": node.get("path"),
            "kind": kind,
            "name": node.get("name"),
            "line": node.get("line"),
            "end_line": node.get("end_line"),
            "owner": node.get("owner"),
            "attributes": node.get("attributes", {}),
        }
        f = files.get(entry["path"], {})
        if f.get("sha256"):
            entry["file_sha256"] = f["sha256"]
        candidates.append((priority[kind], entry["path"] or "", str(entry["name"] or ""), entry))
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    return [x[3] for x in candidates[:limit]]


def draft_from_scan(
    report: dict,
    *,
    blueprint_id: str,
    name: str,
    purpose: str,
    version: str = "0.1.0",
) -> dict:
    """Create an evidence-grounded DRAFT Blueprint from a SCAN report.

    This function intentionally does not pretend static structure is semantic discovery.
    It packages the evidence and the exact reasoning task that a strong LLM/agent must
    complete before the Blueprint may become READY.
    """
    verify_report(report)
    if not isinstance(blueprint_id, str) or not BODY_ID_RE.fullmatch(blueprint_id):
        raise ValueError(f"Invalid blueprint id: {blueprint_id!r}")
    inventory_receipt = [
        {"path": f["path"], "sha256": f.get("sha256"), "status": f.get("status")}
        for f in report["graph"]["files"]
    ]
    source_digest = _digest(inventory_receipt)
    gaps = report["graph"].get("gaps", [])
    value = {
        "schema": SCHEMA,
        "id": blueprint_id,
        "name": name,
        "version": version,
        "status": "DRAFT",
        "purpose": purpose,
        "source": {
            "kind": "scan-report",
            "locator": report.get("source_root", "unknown-source"),
            "revision": None,
            "source_digest": source_digest,
            "scan_graph_digest": report["graph_digest"],
        },
        "bootstrap": {
            "audience": "mantle-naive-llm",
            "purpose": "This Blueprint is a semantic execution contract. Its rules below are sufficient to interpret a READY Blueprint without prior MantleOS or AnchorCode knowledge.",
            "anchor_rules": deepcopy(ANCHOR_RULES),
            "execution_protocol": deepcopy(EXECUTION_PROTOCOL),
            "evidence_protocol": deepcopy(EVIDENCE_PROTOCOL),
            "completion_rule": "A workflow is complete only when every referenced anchor remains satisfied and every consequential effect has passed its declared verification condition.",
        },
        "systems": [],
        "anchors": [],
        "workflows": [],
        "acceptance_contracts": [],
        "unknowns": [
            {
                "id": "semantic.anchor.discovery",
                "statement": "Infer the minimum semantic obligations whose removal would leave externally meaningful behavior, state transition, authority, or failure semantics under-specified.",
                "blocking": True,
            },
            {
                "id": "system.interface.binding",
                "statement": "Map each consequential project operation used by a workflow to a self-described Body system interface with effect, authority, input/output, usage, and verification contracts.",
                "blocking": True,
            },
            {
                "id": "behavior.acceptance.coverage",
                "statement": "Bind important original behavior/tests to anchors so unexplained acceptance behavior remains visible instead of being silently dropped.",
                "blocking": True,
            },
        ],
        "discovery": {
            "schema": "anchor.discovery-context/1",
            "task": [
                "Read project source, tests, docs, schemas, configuration, entrypoints, persistence code, errors, and external integrations using this SCAN evidence as an index.",
                "Do not summarize functions one-for-one. Infer the smallest set of semantic obligations required for the software to continue behaving as itself.",
                "For each inferred anchor, attach concrete source/test evidence. Use INFERRED_UNVERIFIED when evidence is insufficient.",
                "Define workflows in terms of anchors and declared system interfaces, not hidden implementation assumptions.",
                "Create acceptance contracts for externally meaningful behaviors and link each one back to the anchors that explain it.",
                "Retain unresolved implications as explicit unknowns. Set status to READY only when no blocking unknown remains and all anchors needed for workflows are evidenced.",
                "Do not infer a Persona, PRIMER, continuity policy, or Bio-Software identity from the repository. Those are supplied separately at Bio-Software birth.",
            ],
            "scan_scope": report["graph"].get("scope", {}),
            "coverage_gaps": gaps,
            "evidence_candidates": _evidence_candidates(report),
            "inventory": inventory_receipt,
        },
    }
    validate_blueprint(value)
    return value


def render_runner_guide(value: dict) -> str:
    """Render a cold-start guide for a Mantle/Anchor-naive LLM or agent."""
    bp = validate_blueprint(value, require_ready=True)
    lines = [
        f"# Anchor Blueprint Runner Guide — {bp['name']}",
        "",
        "> This document is intentionally self-contained. You do not need prior knowledge of MantleOS or AnchorCode.",
        "",
        "## Purpose",
        "",
        bp["purpose"],
        "",
        "## How to interpret this Blueprint",
        "",
    ]
    for rule in bp["bootstrap"]["anchor_rules"]:
        lines.append(f"- {rule}")
    lines += ["", "## Execution protocol", ""]
    for i, rule in enumerate(bp["bootstrap"]["execution_protocol"], 1):
        lines.append(f"{i}. {rule}")
    lines += ["", "## Evidence protocol", ""]
    for rule in bp["bootstrap"]["evidence_protocol"]:
        lines.append(f"- {rule}")
    lines += ["", f"**Completion rule:** {bp['bootstrap']['completion_rule']}", "", "## Required systems and interfaces", ""]
    if not bp["systems"]:
        lines.append("No external/project interfaces are required by this Blueprint.")
    for system in bp["systems"]:
        lines += [f"### `{system['id']}`", "", system["purpose"], ""]
        for interface in system["interfaces"]:
            authority = interface["authority"] if interface["authority"] is not None else "none"
            lines += [
                f"#### `{interface['name']}`",
                "",
                f"- Effect: `{interface['effect']}`",
                f"- Authority: `{authority}`",
                f"- Provider binding: `{interface['provider']}`",
                f"- Use: {interface['usage']}",
                f"- Input contract: `{json.dumps(interface['input'], sort_keys=True, ensure_ascii=False)}`",
                f"- Output contract: `{json.dumps(interface['output'], sort_keys=True, ensure_ascii=False)}`",
                f"- Verification: {interface['verification']}",
                "",
            ]
    lines += ["## Semantic anchors", ""]
    for anchor in bp["anchors"]:
        lines += [
            f"### `{anchor['id']}` — {anchor['kind']}",
            "",
            anchor["statement"],
            "",
            f"Status: `{anchor['status']}`",
        ]
        if anchor["requires"]:
            lines.append("Requires: " + ", ".join(f"`{x}`" for x in anchor["requires"]))
        if anchor["guarantees"]:
            lines.append("Guarantees: " + "; ".join(anchor["guarantees"]))
        lines.append("")
    lines += ["## Workflows", ""]
    for flow in bp["workflows"]:
        lines += [f"### `{flow['id']}`", "", flow["purpose"], ""]
        for i, step in enumerate(flow["steps"], 1):
            suffix = f" via `{step['interface']}`" if step.get("interface") else ""
            lines.append(f"{i}. `{step['anchor']}`{suffix}: {step['instruction']}")
        lines += ["", "Success when:"] + [f"- {x}" for x in flow["success"]]
        if flow["failures"]:
            lines += ["", "Explicit failure conditions:"] + [f"- {x}" for x in flow["failures"]]
        lines.append("")
    lines += ["## Acceptance contracts", ""]
    for contract in bp["acceptance_contracts"]:
        lines += [
            f"- `{contract['id']}`: {contract['statement']} (anchors: {', '.join(contract['anchors'])}). Test guidance: {contract['test_hint']}",
        ]
    if bp["unknowns"]:
        lines += ["", "## Known non-blocking unknowns", ""]
        for unknown in bp["unknowns"]:
            lines.append(f"- `{unknown['id']}`: {unknown['statement']}")
    lines += ["", f"Blueprint identity (sha256): `{bp['blueprint_sha256']}`", ""]
    return "\n".join(lines)


def write_blueprint(path: str | Path, value: dict) -> dict:
    bp = validate_blueprint(value)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return completion_report(value)
