from __future__ import annotations

from pathlib import Path

from scan.anchor_code import build_anchor_blueprint, parse_anchor_code, to_anchor_code
from scan.agent_blueprint import render_agent_blueprint
from scan.conformance import compare_manifests
from scan.conformance_contract import parse_blueprint_manifest
from scan.adapters.web_frontend import WebFrontendAdapter
from scan.inventory import record_from_bytes


class FakeStore:
    def __init__(self):
        self._nodes = [
            {
                "id": "surface:save", "kind": "human_surface", "name": "Save",
                "path": "ui.html", "coverage": "MAPPED",
                "attributes_json": '{"surface_type":"html:button","surface_role":"input","tag":"button"}',
            },
            {
                "id": "nest:fs", "kind": "nest_boundary", "name": "filesystem",
                "path": "main.cpp", "coverage": "MAPPED",
                "attributes_json": '{"boundary_type":"filesystem","direction":"outbound","provider":"OS"}',
            },
        ]
        self._findings = [
            {
                "id": "finding:gap", "kind": "coverage_gap", "title": "unknown path",
                "coverage": "UNKNOWN", "attributes_json": '{"meaning":"not yet mapped"}',
            }
        ]

    def semantic_objects(self):
        return [
            {
                "id": "specimen:1", "object_type": "SPECIMEN", "subtype": "specimen",
                "label": "fixture", "coverage": "MAPPED",
                "attributes": {"specimen_id": "fixture", "fingerprint": {"value": "abc"}},
            },
            {
                "id": "evidence:1", "object_type": "EVIDENCE", "subtype": "DIRECT",
                "label": "surface exists", "coverage": "MAPPED",
                "attributes": {"path": "ui.html", "start_line": 1, "end_line": 1},
            },
            {
                "id": "finding:1", "object_type": "FINDING", "subtype": "coverage_gap",
                "label": "route unresolved", "coverage": "UNKNOWN", "attributes": {},
            },
        ]

    def semantic_relations(self):
        return [
            {
                "id": "relation:1", "src": "specimen:1", "dst": "finding:1",
                "kind": "calls", "status": "PARTIAL", "attributes": {},
                "evidence_ids": ["evidence:1"],
            }
        ]

    def completeness_dimensions(self):
        return [
            {
                "id": "complete:surface", "key": "human-surfaces",
                "label": "Human surfaces", "state": "PARTIAL",
                "attributes": {}, "evidence_ids": ["evidence:1"],
            }
        ]

    def query(self, sql, params=()):
        if "FROM nodes" in sql:
            return list(self._nodes)
        if "FROM findings" in sql:
            return list(self._findings)
        return []


def test_anchor_code_round_trip_preserves_static_runtime_firewall():
    store = FakeStore()
    blueprint = build_anchor_blueprint(
        store,
        {"specimen_id": "fixture", "fingerprint": {"value": "abc"}},
        engine_version="0.28.0",
    )
    parsed = parse_anchor_code(to_anchor_code(blueprint))
    assert parsed["header"]["schema"] == "AnchorCode/0.9"
    assert any(
        row["type"] == "EVIDENCE" and row["body"].get("kind") == "STATICALLY_DERIVED"
        for row in parsed["records"]
    )
    assert any(
        row["type"] == "REL" and row["body"].get("runtime_execution") == "UNKNOWN"
        for row in parsed["records"]
    )
    assert any(row["type"] == "UNKNOWN" for row in parsed["records"])


def test_blueprint_embeds_required_contracts_for_surface_and_nest():
    store = FakeStore()
    text = render_agent_blueprint(
        store,
        {"specimen_id": "fixture", "fingerprint": {"value": "abc"}},
        engine_version="0.28.0",
    )
    manifest = parse_blueprint_manifest(text)
    kinds = {row["kind"] for row in manifest["contracts"]}
    assert "human_surface" in kinds
    assert "nest_boundary" in kinds
    assert "candidate_execution" in manifest["contract_policy"]
    assert "does **not** claim runtime" in text


def test_conformance_detects_missing_and_regression():
    contract = {
        "contract_id": "ACB-HUMAN-1",
        "area": "human-surface",
        "kind": "human_surface",
        "coverage": "MAPPED",
        "enforcement": "REQUIRED",
        "comparison": "EXACT",
        "identity": {"surface_type": "html:button"},
        "expected": {"role": "save"},
        "count": 1,
        "source_refs": [],
    }
    baseline = {
        "schema_version": "scan-anchor-conformance-contract/0.1",
        "blueprint_schema": "scan-anchor-blueprint-md/0.4",
        "app_name": "fixture",
        "contracts": [contract],
    }
    satisfied = {**baseline, "contracts": [dict(contract)]}
    first = compare_manifests(baseline, satisfied)
    assert first["state"] == "PASS"
    missing = compare_manifests(baseline, {**baseline, "contracts": []}, previous_report=first)
    assert missing["state"] == "FAIL"
    assert missing["summary"]["regression_count"] == 1


def test_web_canvas_is_presented_until_human_event_evidence_exists(tmp_path: Path):
    adapter = WebFrontendAdapter()

    display = '<label for="size">Brush size</label><input id="size" type="range" value="4"><canvas id="preview"></canvas>'
    record = record_from_bytes("index.html", display.encode("utf-8"))
    result = adapter.extract(tmp_path, record, display)
    surfaces = [node for node in result.nodes if node.kind == "human_surface"]
    size = next(node for node in surfaces if node.attributes.get("dom_id") == "size")
    canvas = next(node for node in surfaces if node.attributes.get("dom_id") == "preview")
    assert size.name == "Brush size"
    assert canvas.attributes["surface_role"] == "presented"

    interactive = '<canvas id="paint" onpointerdown="beginPaint(event)"></canvas>'
    record2 = record_from_bytes("paint.html", interactive.encode("utf-8"))
    result2 = adapter.extract(tmp_path, record2, interactive)
    canvas2 = next(node for node in result2.nodes if node.kind == "human_surface")
    assert canvas2.attributes["surface_role"] == "input"
    assert any(edge.kind == "dispatches_to" and edge.src == canvas2.id for edge in result2.edges)


def test_plain_hyperlink_is_preserved_without_entering_action_denominator(tmp_path: Path):
    adapter = WebFrontendAdapter()
    html = '<a href="manual.html">Manual</a><a href="#" onclick="openPanel()">Panel</a>'
    record = record_from_bytes("index.html", html.encode("utf-8"))
    result = adapter.extract(tmp_path, record, html)

    plain = next(node for node in result.nodes if node.kind == "web_navigation_reference")
    assert plain.name == "Manual"
    assert plain.attributes["href"] == "manual.html"
    assert plain.attributes["surface_role"] == "navigation_candidate"

    actionable = [node for node in result.nodes if node.kind == "human_surface"]
    assert len(actionable) == 1
    assert actionable[0].name == "Panel"
    assert any(edge.kind == "dispatches_to" and edge.src == actionable[0].id for edge in result.edges)
