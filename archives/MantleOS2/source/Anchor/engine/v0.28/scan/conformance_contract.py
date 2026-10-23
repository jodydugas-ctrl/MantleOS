from __future__ import annotations

"""Machine-readable contracts embedded in an Anchor Blueprint.

The Blueprint remains the portable human/agent handoff. This module adds a
small deterministic contract manifest to that same Markdown file so a later
candidate can be rescanned and compared without access to the original source
or original SQLite database.

Contracts deliberately describe only facts SCAN mechanically observed. Source
paths and line numbers are provenance, not matching keys, so a reconstruction is
free to reorganize files while preserving the mapped contract.
"""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

CONFORMANCE_CONTRACT_SCHEMA = "scan-anchor-conformance-contract/0.1"
MANIFEST_BEGIN = "<!-- SCAN_CONFORMANCE_MANIFEST_BEGIN -->"
MANIFEST_END = "<!-- SCAN_CONFORMANCE_MANIFEST_END -->"


def _json_value(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _attrs(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("attributes")
    if isinstance(value, dict):
        return value
    parsed = _json_value(row.get("attributes_json"), {})
    return parsed if isinstance(parsed, dict) else {}


def _rows(store, table: str, order: str) -> list[dict[str, Any]]:
    try:
        return [dict(x) for x in store.query(f"SELECT * FROM {table} ORDER BY {order}")]
    except Exception:
        return []


def _clean_string(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def _clean(value: Any, *, sort_lists: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            str(k): _clean(v, sort_lists=sort_lists)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
            if v is not None and v != ""
        }
    if isinstance(value, (list, tuple)):
        values = [_clean(v, sort_lists=sort_lists) for v in value]
        if sort_lists:
            try:
                return sorted(values, key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
            except Exception:
                return values
        return values
    return _clean_string(value)


def _hash(value: Any) -> str:
    data = json.dumps(_clean(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(data).hexdigest()


def _coverage(row: dict[str, Any]) -> str:
    return str(row.get("coverage") or "UNKNOWN").upper()


def _source_ref(row: dict[str, Any]) -> dict[str, Any]:
    attrs = _attrs(row)
    result = {"path": str(row.get("path") or "")}
    line = attrs.get("line") or attrs.get("surface_site_line")
    if isinstance(line, int):
        result["line"] = line
    return result


def _contract(
    *,
    area: str,
    kind: str,
    identity: dict[str, Any],
    expected: dict[str, Any],
    row: dict[str, Any],
    enforcement: str = "REQUIRED",
    comparison: str = "EXACT",
) -> dict[str, Any]:
    identity = _clean(identity, sort_lists=True)
    expected = _clean(expected, sort_lists=True)
    coverage = _coverage(row)
    if coverage != "MAPPED":
        enforcement = "ADVISORY"
    seed = {"area": area, "kind": kind, "identity": identity, "expected": expected}
    prefix = re.sub(r"[^A-Z0-9]+", "-", area.upper()).strip("-")[:10] or "CONTRACT"
    contract_id = f"ACB-{prefix}-{_hash(seed)[:12]}"
    return {
        "contract_id": contract_id,
        "area": area,
        "kind": kind,
        "coverage": coverage,
        "enforcement": enforcement,
        "comparison": comparison,
        "identity": identity,
        "expected": expected,
        "source_refs": [_source_ref(row)],
    }


def _node_contracts(nodes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in nodes:
        kind = str(row.get("kind") or "")
        attrs = _attrs(row)
        name = str(row.get("name") or "")

        if kind == "build_script":
            out.append(_contract(
                area="build", kind=kind, row=row,
                identity={"system": attrs.get("system"), "script": attrs.get("script") or name, "role": attrs.get("role")},
                expected={"command": attrs.get("command"), "invocation": attrs.get("invocation")},
            ))
        elif kind == "build_target":
            out.append(_contract(
                area="build", kind=kind, row=row,
                identity={"name": name, "system": attrs.get("system") or attrs.get("generator")},
                expected={"arguments": attrs.get("arguments"), "target_type": attrs.get("target_type")},
            ))
        elif kind == "dependency_reference":
            out.append(_contract(
                area="dependencies", kind=kind, row=row,
                identity={"name": name, "scope": attrs.get("scope")},
                expected={"declared_version": attrs.get("declared_version"), "mechanism": attrs.get("mechanism")},
                enforcement="ADVISORY", comparison="COMPATIBLE",
            ))
        elif kind == "entry_point":
            out.append(_contract(
                area="entrypoints", kind=kind, row=row,
                identity={"entry_type": attrs.get("entry_type"), "script_type": attrs.get("script_type")},
                expected={
                    "rendered": attrs.get("rendered"), "root_expression": attrs.get("root_expression"),
                    "callee": attrs.get("callee"),
                },
            ))
        elif kind == "mount_point":
            out.append(_contract(
                area="entrypoints", kind=kind, row=row,
                identity={"element_id": attrs.get("element_id") or name, "tag": attrs.get("tag")},
                expected={},
            ))
        elif kind == "state_member":
            out.append(_contract(
                area="state", kind=kind, row=row,
                identity={"state_name": attrs.get("state_name") or name, "owner": attrs.get("component_function") or attrs.get("owner_class")},
                expected={
                    "initial_value": attrs.get("initial_value"), "declared_type": attrs.get("declared_type") or attrs.get("static_type"),
                    "setter": attrs.get("setter"), "hook": attrs.get("hook"),
                },
            ))
        elif kind == "member_symbol":
            out.append(_contract(
                area="state", kind=kind, row=row,
                identity={"name": name, "owner": attrs.get("owner_class")},
                expected={"declared_type": attrs.get("declared_type") or attrs.get("static_type"), "initial_value": attrs.get("initial_value")},
                enforcement="ADVISORY", comparison="COMPATIBLE",
            ))
        elif kind == "state_change":
            out.append(_contract(
                area="state", kind=kind, row=row,
                identity={"state_name": attrs.get("state_name") or name, "function": attrs.get("function") or attrs.get("caller_qualified_name")},
                expected={"setter": attrs.get("setter"), "operator": attrs.get("operator"), "mechanism": attrs.get("classification") or attrs.get("mechanism") or attrs.get("hook")},
            ))
        elif kind == "input_domain":
            out.append(_contract(
                area="input-routing", kind=kind, row=row,
                identity={"name": name, "function": attrs.get("function")},
                expected={"values": sorted(attrs.get("values") or []), "mechanism": attrs.get("mechanism")},
            ))
        elif kind == "dispatch_route":
            out.append(_contract(
                area="input-routing", kind=kind, row=row,
                identity={"map_name": attrs.get("map_name"), "input": attrs.get("input"), "function": attrs.get("function")},
                expected={"target": attrs.get("target"), "mechanism": attrs.get("mechanism")},
            ))
        elif kind == "guard":
            condition = attrs.get("condition") or attrs.get("expression") or name
            direct_actions = attrs.get("actions") if isinstance(attrs.get("actions"), list) else None
            out.append(_contract(
                area="input-routing", kind=kind, row=row,
                identity={"function": attrs.get("function") or attrs.get("caller_qualified_name"), "condition": condition},
                expected={"actions": direct_actions},
            ))
        elif kind == "human_surface_container":
            out.append(_contract(
                area="human-surface", kind=kind, row=row,
                identity={"surface_type": attrs.get("surface_type"), "title": attrs.get("title") or name},
                expected={"classification": attrs.get("classification")},
            ))
        elif kind in {"human_surface", "surface_factory_output"}:
            out.append(_contract(
                area="human-surface", kind=kind, row=row,
                identity={
                    "surface_type": attrs.get("surface_type"), "surface_role": attrs.get("surface_role"),
                    "tag": attrs.get("tag"), "component_function": attrs.get("component_function"),
                },
                expected={
                    "event_props": sorted(attrs.get("event_props") or []), "role": attrs.get("role"),
                    "disabled_condition": attrs.get("disabled_condition"), "hidden_condition": attrs.get("hidden_condition"),
                },
            ))
        elif kind == "component_instance":
            out.append(_contract(
                area="component-composition", kind=kind, row=row,
                identity={
                    "component": attrs.get("component") or name, "owner_function": attrs.get("owner_function"),
                    "text": attrs.get("text"), "condition": attrs.get("condition"),
                },
                expected={"props": attrs.get("props") or {}},
                enforcement="ADVISORY", comparison="EQUIVALENT_ALLOWED",
            ))
        elif kind == "visual_variant":
            out.append(_contract(
                area="visual-layout", kind=kind, row=row,
                identity={"map_name": attrs.get("map_name"), "variant": attrs.get("variant")},
                expected={"value": attrs.get("value")},
                enforcement="ADVISORY", comparison="EQUIVALENT_ALLOWED",
            ))
        elif kind == "visual_contract":
            out.append(_contract(
                area="visual-layout", kind=kind, row=row,
                identity={
                    "owner_function": attrs.get("owner_function"), "tag": attrs.get("tag") or name,
                    "text": attrs.get("text"), "condition": attrs.get("condition"),
                },
                expected={
                    "class_name": attrs.get("class_name"), "class_tokens": sorted(attrs.get("class_tokens") or []),
                    "style": attrs.get("style"),
                },
                enforcement="ADVISORY", comparison="EQUIVALENT_ALLOWED",
            ))
        elif kind == "event":
            out.append(_contract(
                area="events", kind=kind, row=row,
                identity={"name": name, "framework": attrs.get("framework")},
                expected={"binding": attrs.get("binding"), "sender_expression": attrs.get("sender_expression")},
            ))
        elif kind == "handler_reference":
            out.append(_contract(
                area="events", kind=kind, row=row,
                identity={"name": name, "framework": attrs.get("framework"), "component": attrs.get("component"), "prop": attrs.get("prop")},
                expected={"expression": attrs.get("expression"), "role": attrs.get("role")},
                enforcement="ADVISORY", comparison="COMPATIBLE",
            ))
        elif kind in {
            "effect", "environment_boundary", "nest_boundary", "persistence_provider", "persistence_operation",
            "capability_factory", "extension_receptor", "async_task",
        }:
            out.append(_contract(
                area="effects-boundaries", kind=kind, row=row,
                identity={
                    "kind": kind, "name": name, "effect_type": attrs.get("effect_type"),
                    "operation": attrs.get("operation"), "capability": attrs.get("capability"),
                },
                expected={
                    "direction": attrs.get("direction"), "provider": attrs.get("provider") or attrs.get("provider_type"),
                    "api": attrs.get("api"), "mechanism": attrs.get("mechanism"), "boundary_type": attrs.get("boundary_type"),
                },
            ))
    return out


def _merge_contracts(contracts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in contracts:
        signature = _hash({
            "area": item["area"], "kind": item["kind"], "identity": item["identity"],
            "expected": item["expected"], "enforcement": item["enforcement"], "comparison": item["comparison"],
        })
        if signature not in grouped:
            grouped[signature] = {**item, "count": 0, "source_refs": []}
        grouped[signature]["count"] += 1
        for ref in item.get("source_refs") or []:
            if ref not in grouped[signature]["source_refs"]:
                grouped[signature]["source_refs"].append(ref)
    return sorted(grouped.values(), key=lambda x: (x["area"], x["kind"], x["contract_id"]))


def build_conformance_manifest(
    store,
    specimen: dict[str, Any],
    *,
    engine_version: str,
    blueprint_schema: str,
    snapshot=None,
) -> dict[str, Any]:
    nodes = _rows(store, "nodes", "kind,path,name,id")
    all_contracts = _merge_contracts(_node_contracts(nodes))
    required = [c for c in all_contracts if c.get("enforcement") == "REQUIRED"]
    advisory = [c for c in all_contracts if c.get("enforcement") != "REQUIRED"]
    advisory_area_counts: dict[str, int] = {}
    for item in advisory:
        area = str(item.get("area") or "unknown")
        advisory_area_counts[area] = advisory_area_counts.get(area, 0) + 1
    fingerprint = specimen.get("fingerprint")
    if isinstance(fingerprint, dict):
        fingerprint = fingerprint.get("value")
    return {
        "schema_version": CONFORMANCE_CONTRACT_SCHEMA,
        "blueprint_schema": blueprint_schema,
        "generator": f"scan-software-body/{engine_version}",
        "app_name": str(specimen.get("repository") or specimen.get("specimen_id") or specimen.get("root") or "application").rstrip("/").rsplit("/", 1)[-1].removesuffix(".git"),
        "source_fingerprint": fingerprint,
        "contract_policy": {
            "source_paths_are_provenance_not_match_keys": True,
            "mapped_required_contracts_drive_pass_fail": True,
            "partial_unknown_blocked_source_facts_are_advisory": True,
            "equivalent_allowed_contracts_require_runtime_or_visual_evidence_for_strong_equivalence": True,
            "candidate_execution": "NOT_REQUIRED_BY_STATIC_CONFORMANCE",
        },
        "summary": {
            "observed_contract_count": len(all_contracts),
            "embedded_contract_count": len(required),
            "required_contract_count": len(required),
            "advisory_contract_count": len(advisory),
            "advisory_area_counts": dict(sorted(advisory_area_counts.items())),
            "areas": sorted({c["area"] for c in all_contracts}),
        },
        "contracts": required,
    }


def render_manifest_block(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "\n".join([
        MANIFEST_BEGIN,
        "```json",
        payload,
        "```",
        MANIFEST_END,
    ])


def parse_blueprint_manifest(path_or_text: Path | str) -> dict[str, Any]:
    if isinstance(path_or_text, Path):
        text = path_or_text.read_text(encoding="utf-8")
    else:
        raw = str(path_or_text)
        candidate = Path(raw)
        if "\n" not in raw and candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
        else:
            text = raw
    start = text.find(MANIFEST_BEGIN)
    end = text.find(MANIFEST_END)
    if start < 0 or end < 0 or end <= start:
        raise ValueError("Anchor Blueprint does not contain the current SCAN conformance manifest; regenerate it with this SCAN release")
    body = text[start + len(MANIFEST_BEGIN):end]
    match = re.search(r"```json\s*(\{.*\})\s*```", body, re.DOTALL)
    if not match:
        raise ValueError("Anchor Blueprint conformance manifest is malformed")
    value = json.loads(match.group(1))
    if not isinstance(value, dict) or value.get("schema_version") != CONFORMANCE_CONTRACT_SCHEMA:
        raise ValueError(f"unsupported conformance manifest schema: {value.get('schema_version') if isinstance(value, dict) else type(value).__name__}")
    if not isinstance(value.get("contracts"), list):
        raise ValueError("conformance manifest contracts must be a list")
    return value
