"""Model-neutral semantic discovery protocol for Anchor Blueprints.

MantleOS does not call a specific language model here. Instead it emits a bounded,
hash-bound request that any capable reasoning model/agent can consume, verifies a strict
proposal against the exact source specimen, emits a separately bound critique request,
and only promotes the Blueprint to READY after both deterministic and external critique
pass.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from .anchor_blueprint import completion_report, validate_blueprint
from .anchors import DEFINITIONS

DISCOVERY_REQUEST_SCHEMA = "anchor.discovery-request/1"
DISCOVERY_PROPOSAL_SCHEMA = "anchor.discovery-proposal/1"
CRITIQUE_REQUEST_SCHEMA = "anchor.discovery-critique-request/1"
CRITIQUE_SCHEMA = "anchor.discovery-critique/1"


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_keys(value: dict, required: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    missing = required - set(value)
    extra = set(value) - required
    if missing or extra:
        raise ValueError(f"{label} fields mismatch; missing={sorted(missing)} extra={sorted(extra)}")


def _source_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("Evidence path must be non-empty text")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Unsafe source path: {relative!r}")
    raw = root / Path(*pure.parts)
    if raw.is_symlink():
        raise ValueError(f"Source evidence may not be a symlink: {relative!r}")
    path = raw.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Source path escapes source root: {relative!r}") from exc
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Source evidence is not a regular file: {relative!r}")
    return path


def _decode_text(data: bytes) -> tuple[str | None, str | None]:
    # utf-8-sig also accepts ordinary UTF-8 and strips only a real BOM.
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return None, None


def _merge_ranges(ranges: list[tuple[int, int]], max_line: int) -> list[tuple[int, int]]:
    cleaned = []
    for start, end in sorted(ranges):
        start = max(1, min(int(start), max_line))
        end = max(start, min(int(end), max_line))
        if cleaned and start <= cleaned[-1][1] + 2:
            cleaned[-1] = (cleaned[-1][0], max(cleaned[-1][1], end))
        else:
            cleaned.append((start, end))
    return cleaned


def _priority(relative: str, evidence_paths: set[str]) -> tuple[int, str]:
    p = relative.lower()
    name = PurePosixPath(relative).name.lower()
    if "test" in p or "spec" in p:
        rank = 0
    elif name.startswith("readme") or p.startswith("docs/") or "/docs/" in p:
        rank = 1
    elif relative in evidence_paths:
        rank = 2
    elif name.endswith((".json", ".toml", ".yaml", ".yml")):
        rank = 3
    else:
        rank = 4
    return rank, relative


def _excerpt_records(text: str, ranges: list[tuple[int, int]], char_budget: int) -> tuple[list[dict], int]:
    lines = text.splitlines(keepends=True)
    if not lines:
        lines = [""]
    used = 0
    out = []
    for start, end in ranges:
        segment = "".join(lines[start - 1:end])
        encoded = segment.encode("utf-8")
        if out and used + len(encoded) > char_budget:
            break
        if not out and len(encoded) > char_budget:
            # Keep only whole source lines. A partial line must never be advertised as
            # a citable complete line range.
            kept = []
            kept_bytes = 0
            for line in lines[start - 1:end]:
                line_bytes = line.encode("utf-8")
                if kept_bytes + len(line_bytes) > char_budget:
                    break
                kept.append(line)
                kept_bytes += len(line_bytes)
            if not kept:
                continue
            segment = "".join(kept)
            end = start + len(kept) - 1
            encoded = segment.encode("utf-8")
        out.append({
            "line_start": start,
            "line_end": end,
            "sha256": _sha(encoded),
            "text": segment,
        })
        used += len(encoded)
    return out, used


def _request_core(value: dict) -> dict:
    return {k: v for k, v in value.items() if k != "request_sha256"}


def _critique_request_core(value: dict) -> dict:
    return {k: v for k, v in value.items() if k != "critique_request_sha256"}


def build_discovery_request(
    draft: dict,
    source_root: str | Path,
    *,
    max_total_bytes: int = 1_500_000,
    max_file_bytes: int = 96_000,
    context_lines: int = 8,
) -> dict:
    """Create a bounded, source-bound semantic discovery request.

    All SCAN inventory hashes are rechecked before request creation. Text excerpts include
    files SCAN could not structurally parse when they fit the budget, so unsupported syntax
    does not silently disappear from semantic review.
    """
    bp = validate_blueprint(draft)
    if bp["status"] != "DRAFT":
        raise ValueError("Semantic discovery requests require a DRAFT Anchor Blueprint")
    discovery = bp.get("discovery")
    if not isinstance(discovery, dict) or discovery.get("schema") != "anchor.discovery-context/1":
        raise ValueError("DRAFT Blueprint lacks anchor.discovery-context/1")
    if type(max_total_bytes) is not int or not 32_000 <= max_total_bytes <= 8_000_000:
        raise ValueError("max_total_bytes must be an integer from 32000 through 8000000")
    if type(max_file_bytes) is not int or not 4_000 <= max_file_bytes <= 512_000:
        raise ValueError("max_file_bytes must be an integer from 4000 through 512000")
    if type(context_lines) is not int or not 0 <= context_lines <= 40:
        raise ValueError("context_lines must be an integer from 0 through 40")

    root = Path(source_root).resolve()
    if not root.is_dir():
        raise ValueError("source_root must be a directory")

    inventory = discovery.get("inventory")
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("Discovery context has no SCAN inventory")
    inventory_receipt = [
        {"path": item.get("path"), "sha256": item.get("sha256"), "status": item.get("status")}
        for item in inventory if isinstance(item, dict)
    ]
    if len(inventory_receipt) != len(inventory) or _digest(inventory_receipt) != bp["source"]["source_digest"]:
        raise ValueError("DRAFT source_digest does not match its discovery inventory")
    candidates = discovery.get("evidence_candidates", [])
    evidence_paths = {c.get("path") for c in candidates if isinstance(c, dict) and isinstance(c.get("path"), str)}
    by_path_candidates: dict[str, list[dict]] = {}
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str):
            by_path_candidates.setdefault(candidate["path"], []).append(candidate)

    receipts = []
    decoded: dict[str, tuple[str, bytes, dict]] = {}
    for item in inventory:
        if not isinstance(item, dict):
            raise ValueError("Discovery inventory items must be objects")
        relative = item.get("path")
        expected = item.get("sha256")
        if expected is None:
            receipts.append({"path": relative, "sha256": None, "status": item.get("status"), "available": False})
            continue
        path = _source_path(root, relative)
        data = path.read_bytes()
        actual = _sha(data)
        if actual != expected:
            raise ValueError(f"Source drift for {relative}: expected {expected}, observed {actual}")
        text, encoding = _decode_text(data)
        receipt = {
            "path": relative,
            "sha256": actual,
            "bytes": len(data),
            "status": item.get("status"),
            "text_encoding": encoding,
        }
        receipts.append(receipt)
        if text is not None:
            decoded[relative] = (text, data, receipt)

    excerpts = []
    total = 0
    omitted_text = []
    for relative in sorted(decoded, key=lambda p: _priority(p, evidence_paths)):
        text, data, receipt = decoded[relative]
        lines = text.splitlines(keepends=True) or [""]
        if total >= max_total_bytes:
            omitted_text.append(relative)
            continue
        remaining_total = max_total_bytes - total
        file_budget = min(max_file_bytes, remaining_total)
        if len(data) <= file_budget:
            ranges = [(1, len(lines))]
        else:
            ranges = []
            for c in by_path_candidates.get(relative, []):
                line = c.get("line")
                end = c.get("end_line")
                if isinstance(line, int):
                    end = end if isinstance(end, int) else line
                    ranges.append((line - context_lines, end + context_lines))
            # Unsupported docs/TS and large files still get a bounded leading context.
            if not ranges:
                ranges = [(1, min(len(lines), 200))]
            ranges = _merge_ranges(ranges, len(lines))
        file_excerpts, used = _excerpt_records(text, ranges, file_budget)
        if not file_excerpts:
            omitted_text.append(relative)
            continue
        total += used
        excerpts.append({
            "path": relative,
            "file_sha256": receipt["sha256"],
            "status": receipt.get("status"),
            "excerpts": file_excerpts,
        })
        # A large file represented only by bounded regions remains explicitly partial.
        covered_lines = sum(e["line_end"] - e["line_start"] + 1 for e in file_excerpts)
        if covered_lines < len(lines):
            omitted_text.append(relative)

    core = {
        "schema": DISCOVERY_REQUEST_SCHEMA,
        "blueprint": {
            "id": bp["id"],
            "sha256": bp["blueprint_sha256"],
            "source_digest": bp["source"]["source_digest"],
            "scan_graph_digest": bp["source"].get("scan_graph_digest"),
            "purpose": bp["purpose"],
        },
        "task": [
            "Infer the minimum semantic obligations whose removal would leave externally meaningful behavior, state transition, authority, or failure behavior under-specified.",
            "Do not produce one anchor per function. Compress implementation facts into the smallest defensible semantic graph.",
            "Cite only evidence line ranges present in this request. Preserve weak implications as INFERRED_UNVERIFIED or as explicit blocking unknowns.",
            "Define Body system interfaces from the runner's perspective: purpose, effect, authority, provider binding, input/output, usage, and verifier.",
            "Define representative workflows and acceptance contracts. Every workflow anchor must be covered by at least one acceptance contract before READY promotion.",
            "Do not set Blueprint READY status. MantleOS owns promotion after independent critique.",
        ],
        "proposal_contract": {
            "schema": DISCOVERY_PROPOSAL_SCHEMA,
            "required_top_level_fields": [
                "schema", "request_sha256", "blueprint_id", "blueprint_sha256",
                "systems", "anchors", "workflows", "acceptance_contracts", "unknowns",
            ],
            "evidence_reference": {
                "required": ["path", "sha256", "line_start", "line_end", "reason"],
                "rule": "The cited inclusive line range must be wholly contained in an excerpt supplied by this request and its file hash must match.",
            },
            "anchor_statuses": ["SOURCE_OBSERVED", "INFERRED_SUPPORTED", "INFERRED_UNVERIFIED"],
            "anchor_model": {
                "rule": "Apply an existing immutable Anchor; put source obligations in attributes, never invent a singularity.",
                "required_binding_fields": ["definition_id", "type", "singularity"],
                "definitions": {name: {"type": base.type, "singularity": base.singularity}
                                for name, base in DEFINITIONS.items()},
            },
            "unknown_rule": "Any unresolved behavior that could affect equivalence must remain an explicit unknown; use blocking=true when it prevents synthesis confidence.",
        },
        "scan_context": {
            "scope": discovery.get("scan_scope", {}),
            "coverage_gaps": discovery.get("coverage_gaps", []),
            "evidence_candidates": candidates,
        },
        "source_receipts": receipts,
        "source_excerpts": excerpts,
        "request_limits": {
            "max_total_bytes": max_total_bytes,
            "max_file_bytes": max_file_bytes,
            "context_lines": context_lines,
            "excerpt_bytes": total,
            "partially_or_unrepresented_text_files": sorted(set(omitted_text)),
        },
    }
    result = deepcopy(core)
    result["request_sha256"] = _digest(core)
    return result


def validate_discovery_request(request: dict, draft: dict | None = None) -> dict:
    required = {
        "schema", "blueprint", "task", "proposal_contract", "scan_context",
        "source_receipts", "source_excerpts", "request_limits", "request_sha256",
    }
    _exact_keys(request, required, "discovery request")
    if request["schema"] != DISCOVERY_REQUEST_SCHEMA:
        raise ValueError(f"Expected {DISCOVERY_REQUEST_SCHEMA}")
    if request["request_sha256"] != _digest(_request_core(request)):
        raise ValueError("Discovery request identity mismatch")
    if draft is not None:
        bp = validate_blueprint(draft)
        if request["blueprint"].get("id") != bp["id"] or request["blueprint"].get("sha256") != bp["blueprint_sha256"]:
            raise ValueError("Discovery request is bound to a different Blueprint")
        if request["blueprint"].get("source_digest") != bp["source"]["source_digest"]:
            raise ValueError("Discovery request source binding mismatch")
    return deepcopy(request)


def _request_excerpt_index(request: dict) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for file_record in request["source_excerpts"]:
        path = file_record.get("path")
        if isinstance(path, str):
            index[path] = file_record.get("excerpts", [])
    return index


def _normalize_evidence(
    items: Any,
    *,
    request: dict,
    source_root: Path,
    label: str,
) -> list[dict]:
    if not isinstance(items, list):
        raise ValueError(f"{label}.evidence must be a list")
    excerpt_index = _request_excerpt_index(request)
    receipt_index = {r.get("path"): r for r in request["source_receipts"] if isinstance(r, dict)}
    out = []
    for i, raw in enumerate(items):
        required = {"path", "sha256", "line_start", "line_end", "reason"}
        allowed = required | {"node_id"}
        if not isinstance(raw, dict) or required - set(raw) or set(raw) - allowed:
            raise ValueError(f"{label}.evidence[{i}] must contain exactly {sorted(required)} plus optional node_id")
        relative = raw["path"]
        expected = raw["sha256"]
        if receipt_index.get(relative, {}).get("sha256") != expected:
            raise ValueError(f"{label} cites a file hash not present in the discovery request: {relative}")
        start, end = raw["line_start"], raw["line_end"]
        if type(start) is not int or type(end) is not int or start < 1 or end < start:
            raise ValueError(f"{label} has invalid evidence line range for {relative}")
        containing = [e for e in excerpt_index.get(relative, []) if e.get("line_start", 0) <= start and e.get("line_end", -1) >= end]
        if not containing:
            raise ValueError(f"{label} cites lines not supplied in the bounded discovery request: {relative}:{start}-{end}")
        path = _source_path(source_root, relative)
        data = path.read_bytes()
        if _sha(data) != expected:
            raise ValueError(f"Source drift while resolving evidence: {relative}")
        text, _ = _decode_text(data)
        if text is None:
            raise ValueError(f"Evidence source is not UTF-8 text: {relative}")
        lines = text.splitlines(keepends=True) or [""]
        if end > len(lines):
            raise ValueError(f"Evidence line range exceeds source: {relative}:{start}-{end}")
        segment = "".join(lines[start - 1:end])
        reason = raw["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{label} evidence reason must be non-empty text")
        node_id = raw.get("node_id")
        if node_id is not None:
            matches = [c for c in request.get("scan_context", {}).get("evidence_candidates", [])
                       if isinstance(c, dict) and c.get("node_id") == node_id and c.get("path") == relative]
            if not matches:
                raise ValueError(f"{label} cites an unknown SCAN node_id: {node_id}")
            node = matches[0]
            node_start, node_end = node.get("line"), node.get("end_line")
            if isinstance(node_start, int) and isinstance(node_end, int) and (end < node_start or start > node_end):
                raise ValueError(f"{label} node_id does not overlap its cited source range: {node_id}")
        normalized = dict(raw)
        normalized["excerpt_sha256"] = _sha(segment.encode("utf-8"))
        out.append(normalized)
    return out


def _normalize_proposal_evidence(proposal: dict, request: dict, source_root: Path) -> dict:
    value = deepcopy(proposal)
    anchors = value.get("anchors")
    contracts = value.get("acceptance_contracts")
    if not isinstance(anchors, list) or not isinstance(contracts, list):
        raise ValueError("Proposal anchors and acceptance_contracts must be lists")
    for anchor in anchors:
        if not isinstance(anchor, dict) or not isinstance(anchor.get("id"), str):
            raise ValueError("Proposal anchors must be objects with ids")
        anchor["evidence"] = _normalize_evidence(anchor.get("evidence"), request=request, source_root=source_root, label=anchor["id"])
        if anchor.get("status") in {"SOURCE_OBSERVED", "INFERRED_SUPPORTED"} and not anchor["evidence"]:
            raise ValueError(f"Supported anchor lacks evidence: {anchor['id']}")
    for contract in contracts:
        if not isinstance(contract, dict) or not isinstance(contract.get("id"), str):
            raise ValueError("Proposal acceptance contracts must be objects with ids")
        contract["evidence"] = _normalize_evidence(contract.get("evidence"), request=request, source_root=source_root, label=contract["id"])
    return value


def ingest_discovery_proposal(
    draft: dict,
    request: dict,
    proposal: dict,
    source_root: str | Path,
) -> dict:
    """Verify a model/agent proposal and return a still-DRAFT candidate Blueprint."""
    bp = validate_blueprint(draft)
    if bp["status"] != "DRAFT":
        raise ValueError("Discovery proposals may only be applied to DRAFT Blueprints")
    req = validate_discovery_request(request, draft)
    required = {
        "schema", "request_sha256", "blueprint_id", "blueprint_sha256",
        "systems", "anchors", "workflows", "acceptance_contracts", "unknowns",
    }
    _exact_keys(proposal, required, "discovery proposal")
    if proposal["schema"] != DISCOVERY_PROPOSAL_SCHEMA:
        raise ValueError(f"Expected {DISCOVERY_PROPOSAL_SCHEMA}")
    if proposal["request_sha256"] != req["request_sha256"]:
        raise ValueError("Discovery proposal is bound to a different request")
    if proposal["blueprint_id"] != bp["id"] or proposal["blueprint_sha256"] != bp["blueprint_sha256"]:
        raise ValueError("Discovery proposal is bound to a different Blueprint")

    root = Path(source_root).resolve()
    if not root.is_dir():
        raise ValueError("source_root must be a directory")
    limits = req.get("request_limits", {})
    reproduced = build_discovery_request(
        draft, root,
        max_total_bytes=limits.get("max_total_bytes"),
        max_file_bytes=limits.get("max_file_bytes"),
        context_lines=limits.get("context_lines"),
    )
    if reproduced != req:
        raise ValueError("Discovery request is not the canonical rendering of this Blueprint and source specimen")
    normalized = _normalize_proposal_evidence(proposal, req, root)

    candidate = deepcopy(draft)
    for key in ("systems", "anchors", "workflows", "acceptance_contracts", "unknowns"):
        candidate[key] = deepcopy(normalized[key])
    candidate["status"] = "DRAFT"
    discovery = deepcopy(candidate.get("discovery", {}))
    discovery["semantic_proposal"] = {
        "schema": DISCOVERY_PROPOSAL_SCHEMA,
        "request_sha256": req["request_sha256"],
        "proposal_sha256": _digest(normalized),
        "source_evidence_resolved": True,
        "promotion": "PENDING_INDEPENDENT_CRITIQUE",
    }
    candidate["discovery"] = discovery
    validate_blueprint(candidate)
    return candidate


def semantic_lint(candidate: dict) -> list[dict]:
    """Deterministic critique checks that do not pretend to solve semantic inference."""
    bp = validate_blueprint(candidate)
    findings = []
    acceptance_by_anchor: dict[str, set[str]] = {}
    for contract in bp["acceptance_contracts"]:
        for aid in contract["anchors"]:
            acceptance_by_anchor.setdefault(aid, set()).add(contract["id"])
    workflow_anchors: set[str] = set()
    used_interfaces: set[str] = set()
    for workflow in bp["workflows"]:
        for step in workflow["steps"]:
            workflow_anchors.add(step["anchor"])
            if step.get("interface"):
                used_interfaces.add(step["interface"])
    for aid in sorted(workflow_anchors):
        if aid not in acceptance_by_anchor:
            findings.append({
                "id": f"coverage.workflow-anchor.{aid}",
                "severity": "BLOCKING",
                "statement": f"Workflow anchor {aid} has no acceptance-contract coverage.",
                "refs": [aid],
            })
    for anchor in bp["anchors"]:
        if anchor["status"] == "INFERRED_UNVERIFIED":
            findings.append({
                "id": f"evidence.unverified.{anchor['id']}",
                "severity": "BLOCKING",
                "statement": f"Anchor {anchor['id']} remains INFERRED_UNVERIFIED.",
                "refs": [anchor["id"]],
            })
        elif not anchor["evidence"]:
            findings.append({
                "id": f"evidence.missing.{anchor['id']}",
                "severity": "BLOCKING",
                "statement": f"Supported anchor {anchor['id']} has no resolved source evidence.",
                "refs": [anchor["id"]],
            })
    for unknown in bp["unknowns"]:
        if unknown["blocking"]:
            findings.append({
                "id": f"unknown.blocking.{unknown['id']}",
                "severity": "BLOCKING",
                "statement": f"Blocking semantic unknown remains: {unknown['id']}.",
                "refs": [unknown["id"]],
            })
    all_interfaces = {i["name"] for system in bp["systems"] for i in system["interfaces"]}
    for name in sorted(all_interfaces - used_interfaces):
        findings.append({
            "id": f"interface.unused.{name}",
            "severity": "WARNING",
            "statement": f"Declared interface {name} is not exercised by a representative workflow.",
            "refs": [name],
        })
    represented = workflow_anchors | set(acceptance_by_anchor)
    for anchor in bp["anchors"]:
        if anchor["id"] not in represented:
            findings.append({
                "id": f"anchor.orphan.{anchor['id']}",
                "severity": "WARNING",
                "statement": f"Anchor {anchor['id']} is not referenced by a workflow or acceptance contract.",
                "refs": [anchor["id"]],
            })
    return findings


def build_critique_request(candidate: dict) -> dict:
    bp = validate_blueprint(candidate)
    proposal_receipt = bp.get("discovery", {}).get("semantic_proposal") if isinstance(bp.get("discovery"), dict) else None
    if not isinstance(proposal_receipt, dict) or proposal_receipt.get("promotion") != "PENDING_INDEPENDENT_CRITIQUE":
        raise ValueError("Candidate has no verified semantic proposal receipt")
    deterministic = semantic_lint(candidate)
    core = {
        "schema": CRITIQUE_REQUEST_SCHEMA,
        "blueprint_id": bp["id"],
        "candidate_blueprint_sha256": bp["blueprint_sha256"],
        "proposal_sha256": proposal_receipt["proposal_sha256"],
        "discovery_request_sha256": proposal_receipt["request_sha256"],
        "task": [
            "Act as an independent semantic critic. Do not merely restate the proposal.",
            "Look for missing implications, anchors that are implementation trivia, unsupported claims, contradictory anchors, missing authority/failure semantics, hidden provider assumptions, and acceptance behavior not explained by anchors.",
            "Treat deterministic BLOCKING findings as unresolved unless the candidate itself is revised; critique cannot waive them.",
            "Return PASS only if the semantic graph is sufficiently evidenced and scoped for synthesis. Otherwise return REVISE with explicit BLOCKING findings.",
        ],
        "deterministic_findings": deterministic,
        "candidate": {
            "purpose": bp["purpose"],
            "source": bp["source"],
            "systems": bp["systems"],
            "anchors": bp["anchors"],
            "workflows": bp["workflows"],
            "acceptance_contracts": bp["acceptance_contracts"],
            "unknowns": bp["unknowns"],
            "scan_context": bp.get("discovery", {}).get("coverage_gaps", []),
        },
        "response_contract": {
            "schema": CRITIQUE_SCHEMA,
            "required_top_level_fields": ["schema", "critique_request_sha256", "verdict", "findings", "summary"],
            "verdicts": ["PASS", "REVISE"],
            "finding_severities": ["BLOCKING", "WARNING"],
        },
    }
    result = deepcopy(core)
    result["critique_request_sha256"] = _digest(core)
    return result


def validate_critique_request(request: dict, candidate: dict | None = None) -> dict:
    required = {
        "schema", "blueprint_id", "candidate_blueprint_sha256", "proposal_sha256",
        "discovery_request_sha256", "task", "deterministic_findings", "candidate",
        "response_contract", "critique_request_sha256",
    }
    _exact_keys(request, required, "critique request")
    if request["schema"] != CRITIQUE_REQUEST_SCHEMA:
        raise ValueError(f"Expected {CRITIQUE_REQUEST_SCHEMA}")
    if request["critique_request_sha256"] != _digest(_critique_request_core(request)):
        raise ValueError("Critique request identity mismatch")
    if candidate is not None:
        bp = validate_blueprint(candidate)
        if request["blueprint_id"] != bp["id"] or request["candidate_blueprint_sha256"] != bp["blueprint_sha256"]:
            raise ValueError("Critique request is bound to a different candidate Blueprint")
        expected = build_critique_request(candidate)
        if request != expected:
            raise ValueError("Critique request content does not match the bound candidate Blueprint")
    return deepcopy(request)


def validate_critique(critique: dict, request: dict) -> dict:
    req = validate_critique_request(request)
    required = {"schema", "critique_request_sha256", "verdict", "findings", "summary"}
    _exact_keys(critique, required, "semantic critique")
    if critique["schema"] != CRITIQUE_SCHEMA:
        raise ValueError(f"Expected {CRITIQUE_SCHEMA}")
    if critique["critique_request_sha256"] != req["critique_request_sha256"]:
        raise ValueError("Semantic critique is bound to a different critique request")
    if critique["verdict"] not in {"PASS", "REVISE"}:
        raise ValueError("Critique verdict must be PASS or REVISE")
    if not isinstance(critique["summary"], str) or not critique["summary"].strip():
        raise ValueError("Critique summary must be non-empty text")
    if not isinstance(critique["findings"], list):
        raise ValueError("Critique findings must be a list")
    normalized = deepcopy(critique)
    seen = set()
    for finding in normalized["findings"]:
        required_f = {"id", "severity", "statement", "refs"}
        _exact_keys(finding, required_f, "critique finding")
        fid = finding["id"]
        if not isinstance(fid, str) or not fid.strip() or fid in seen:
            raise ValueError("Critique finding ids must be unique non-empty text")
        seen.add(fid)
        if finding["severity"] not in {"BLOCKING", "WARNING"}:
            raise ValueError(f"Invalid critique severity for {fid}")
        if not isinstance(finding["statement"], str) or not finding["statement"].strip():
            raise ValueError(f"Critique finding {fid} statement must be non-empty text")
        if not isinstance(finding["refs"], list) or any(not isinstance(x, str) or not x for x in finding["refs"]):
            raise ValueError(f"Critique finding {fid} refs must be a list of non-empty strings")
    if critique["verdict"] == "PASS" and any(f["severity"] == "BLOCKING" for f in normalized["findings"]):
        raise ValueError("A PASS critique cannot contain BLOCKING findings")
    return normalized


def finalize_discovery(candidate: dict, critique_request: dict, critique: dict) -> dict:
    """Promote a critiqued candidate to READY, or refuse promotion."""
    bp = validate_blueprint(candidate)
    req = validate_critique_request(critique_request, candidate)
    reviewed = validate_critique(critique, req)
    deterministic_blocking = [f for f in req["deterministic_findings"] if f.get("severity") == "BLOCKING"]
    if deterministic_blocking:
        ids = [f.get("id") for f in deterministic_blocking]
        raise ValueError(f"Deterministic semantic critique still has blocking findings: {ids}")
    if reviewed["verdict"] != "PASS":
        raise ValueError("Independent semantic critique requires revision; READY promotion refused")
    external_blocking = [f for f in reviewed["findings"] if f["severity"] == "BLOCKING"]
    if external_blocking:
        raise ValueError("Independent semantic critique contains blocking findings")

    ready = deepcopy(candidate)
    ready["status"] = "READY"
    discovery = deepcopy(ready.get("discovery", {}))
    proposal_receipt = discovery.get("semantic_proposal", {})
    discovery["semantic_promotion"] = {
        "schema": "anchor.discovery-promotion/1",
        "request_sha256": proposal_receipt.get("request_sha256"),
        "proposal_sha256": proposal_receipt.get("proposal_sha256"),
        "critique_request_sha256": req["critique_request_sha256"],
        "critique_sha256": _digest(reviewed),
        "verdict": "PASS",
        "deterministic_findings": len(req["deterministic_findings"]),
        "external_findings": len(reviewed["findings"]),
    }
    if isinstance(discovery.get("semantic_proposal"), dict):
        discovery["semantic_proposal"]["promotion"] = "READY_AFTER_INDEPENDENT_CRITIQUE"
    ready["discovery"] = discovery
    validate_blueprint(ready, require_ready=True)
    return ready


def discovery_report(value: dict) -> dict:
    report = completion_report(value)
    discovery = value.get("discovery", {}) if isinstance(value, dict) else {}
    report["semantic_discovery"] = {
        "proposal": discovery.get("semantic_proposal") if isinstance(discovery, dict) else None,
        "promotion": discovery.get("semantic_promotion") if isinstance(discovery, dict) else None,
    }
    return report
