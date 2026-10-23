from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .typescript_electron import TypeScriptElectronAdapter as _BaseTypeScriptElectronAdapter
from .typescript_electron_precise import TypeScriptElectronAdapter as _V3TypeScriptElectronAdapter
from ..inventory import FileRecord
from ..model import Edge, ExtractionResult, Finding, Node, stable_id


class TypeScriptElectronAdapter(_V3TypeScriptElectronAdapter):
    """Final experimental adapter layer: raw physical UI controls keep source-site identity."""

    name = "typescript-electron"
    version = "4"

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        # Run the generic substrate extractor once, then apply the ordered refinements. Calling the
        # original base explicitly avoids removing <option> value nodes before physical surfaces
        # have been disambiguated by source location.
        result = _BaseTypeScriptElectronAdapter.extract(self, root, record, text)
        result = self._preserve_callsite_identity(record, result)
        result = self._preserve_surface_site_identity(record, result)
        result = self._remove_non_actionable_option_surfaces(result)
        self._add_inline_handler_resolution(record, result)
        self._add_destructured_react_prop_routes(record, result)
        self._add_react_state_changes(record, text, result)
        self._add_preload_channel_summaries(record, result)
        return result

    def _preserve_surface_site_identity(self, record: FileRecord, result: ExtractionResult) -> ExtractionResult:
        evidence_line = self._evidence_lines(result)
        surface_nodes = [n for n in result.nodes if n.kind == "human_surface"]
        if not surface_nodes:
            return result

        grouped: dict[str, list[Node]] = defaultdict(list)
        for node in surface_nodes:
            grouped[node.id].append(node)

        site_map: dict[str, dict[int | None, str]] = defaultdict(dict)
        replacements: list[Node] = []
        kept = [n for n in result.nodes if n.kind != "human_surface"]

        for old_id, nodes in grouped.items():
            by_line: dict[int | None, list[Node]] = defaultdict(list)
            for node in nodes:
                by_line[self._node_evidence_line(node, evidence_line)].append(node)
            for line, same_site in by_line.items():
                exemplar = same_site[0]
                attrs: dict[str, Any] = dict(exemplar.attributes or {})
                attrs["surface_site_line"] = line
                attrs["identity_rule"] = "file+surface-kind+label+source-line"
                ev_ids = sorted({eid for node in same_site for eid in node.evidence_ids})
                surface_type = attrs.get("surface_type") or attrs.get("tag") or "surface"
                new_id = stable_id("human_surface", record.id, surface_type, exemplar.name, line)
                site_map[old_id][line] = new_id
                replacements.append(Node(
                    new_id, "human_surface", exemplar.name, exemplar.file_id, exemplar.path,
                    exemplar.coverage, attrs, ev_ids,
                ))

        findings = list(result.findings)
        rebuilt: list[Edge] = []
        for edge in result.edges:
            src_sites = site_map.get(edge.src)
            dst_sites = site_map.get(edge.dst)
            if not src_sites and not dst_sites:
                rebuilt.append(edge)
                continue

            line = self._edge_evidence_line(edge, evidence_line)

            def resolve(endpoint: str, sites: dict[int | None, str] | None) -> str | None:
                if not sites:
                    return endpoint
                if line in sites:
                    return sites[line]
                if len(sites) == 1:
                    return next(iter(sites.values()))
                return None

            new_src = resolve(edge.src, src_sites)
            new_dst = resolve(edge.dst, dst_sites)
            if new_src is None or new_dst is None:
                findings.append(Finding(
                    stable_id("finding", record.id, self.name, self.version, "ambiguous-surface-edge", edge.id),
                    "resolution_gap",
                    f"Could not assign UI relation to one physical {record.language} surface",
                    "PARTIAL",
                    {
                        "old_edge_id": edge.id,
                        "edge_kind": edge.kind,
                        "source_surface_count": len(src_sites or {}),
                        "target_surface_count": len(dst_sites or {}),
                        "edge_evidence_lines": sorted({x for x in (evidence_line.get(eid) for eid in edge.evidence_ids) if x is not None}),
                        "meaning": "edge omitted rather than merging distinct physical controls with the same label",
                    },
                    list(edge.evidence_ids),
                ))
                continue

            rebuilt.append(Edge(
                stable_id("edge", new_src, edge.kind, new_dst, record.id, line),
                new_src, new_dst, edge.kind, edge.coverage,
                dict(edge.attributes or {}), list(edge.evidence_ids),
            ))

        result.nodes = kept + replacements
        result.edges = rebuilt
        result.findings = findings
        return result
