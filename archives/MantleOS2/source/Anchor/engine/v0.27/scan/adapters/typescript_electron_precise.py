from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
import re
from typing import Any

from .typescript_electron import TypeScriptElectronAdapter as _BaseTypeScriptElectronAdapter
from ..inventory import FileRecord
from ..model import Edge, ExtractionResult, Finding, Node, stable_id


class TypeScriptElectronAdapter(_BaseTypeScriptElectronAdapter):
    """TypeScript/React/Electron refinement with conservative site identity and route synthesis.

    Raw source locations remain distinct. Higher-order React/Electron routing edges are added only
    when the detailed lower-level path is already present in the extracted graph. This lets SCAN
    reason across framework plumbing without discarding the drill-down evidence that justifies it.
    """

    name = "typescript-electron"
    version = "3"

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        result = super().extract(root, record, text)
        result = self._preserve_callsite_identity(record, result)
        result = self._remove_non_actionable_option_surfaces(result)
        self._add_inline_handler_resolution(record, result)
        self._add_destructured_react_prop_routes(record, result)
        self._add_react_state_changes(record, text, result)
        self._add_preload_channel_summaries(record, result)
        return result

    @staticmethod
    def _evidence_lines(result: ExtractionResult) -> dict[str, int | None]:
        return {ev.id: ev.start_line for ev in result.evidence}

    @staticmethod
    def _node_evidence_line(node: Node, evidence_line: dict[str, int | None]) -> int | None:
        lines = {evidence_line.get(eid) for eid in node.evidence_ids if evidence_line.get(eid) is not None}
        if len(lines) == 1:
            return next(iter(lines))
        value = (node.attributes or {}).get("callsite_line") or (node.attributes or {}).get("line")
        return value if isinstance(value, int) else None

    @staticmethod
    def _edge_evidence_line(edge: Edge, evidence_line: dict[str, int | None]) -> int | None:
        lines = {evidence_line.get(eid) for eid in edge.evidence_ids if evidence_line.get(eid) is not None}
        if len(lines) == 1:
            return next(iter(lines))
        return None

    def _preserve_callsite_identity(self, record: FileRecord, result: ExtractionResult) -> ExtractionResult:
        evidence_line = self._evidence_lines(result)
        call_nodes = [n for n in result.nodes if n.kind == "call_reference"]
        if not call_nodes:
            return result

        grouped: dict[str, list[Node]] = defaultdict(list)
        for n in call_nodes:
            grouped[n.id].append(n)

        site_map: dict[str, dict[int | None, str]] = defaultdict(dict)
        replacements: list[Node] = []
        kept_non_calls = [n for n in result.nodes if n.kind != "call_reference"]

        for old_id, nodes in grouped.items():
            by_line: dict[int | None, list[Node]] = defaultdict(list)
            for n in nodes:
                by_line[self._node_evidence_line(n, evidence_line)].append(n)
            for line, same_site in by_line.items():
                exemplar = same_site[0]
                attrs: dict[str, Any] = dict(exemplar.attributes or {})
                attrs["callsite_line"] = line
                attrs["identity_rule"] = "file+callee+source-line"
                ev_ids = sorted({eid for n in same_site for eid in n.evidence_ids})
                new_id = stable_id("call_reference", record.id, attrs.get("callee") or exemplar.name, line)
                site_map[old_id][line] = new_id
                replacements.append(Node(
                    new_id, "call_reference", exemplar.name, exemplar.file_id, exemplar.path,
                    exemplar.coverage, attrs, ev_ids,
                ))

        findings = list(result.findings)
        rebuilt_edges: list[Edge] = []
        for edge in result.edges:
            src_sites = site_map.get(edge.src)
            dst_sites = site_map.get(edge.dst)
            if not src_sites and not dst_sites:
                rebuilt_edges.append(edge)
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
                    stable_id("finding", record.id, self.name, self.version, "ambiguous-callsite-edge", edge.id),
                    "resolution_gap",
                    f"Could not assign structural edge to one {record.language} call site",
                    "PARTIAL",
                    {
                        "old_edge_id": edge.id,
                        "edge_kind": edge.kind,
                        "source_callsite_count": len(src_sites or {}),
                        "target_callsite_count": len(dst_sites or {}),
                        "edge_evidence_lines": sorted({x for x in (evidence_line.get(eid) for eid in edge.evidence_ids) if x is not None}),
                        "meaning": "edge omitted rather than allowing unrelated repeated calls to share a behavior path",
                    },
                    list(edge.evidence_ids),
                ))
                continue

            rebuilt_edges.append(Edge(
                stable_id("edge", new_src, edge.kind, new_dst, record.id, line),
                new_src, new_dst, edge.kind, edge.coverage,
                dict(edge.attributes or {}), list(edge.evidence_ids),
            ))

        result.nodes = kept_non_calls + replacements
        result.edges = rebuilt_edges
        result.findings = findings
        return result

    @staticmethod
    def _remove_non_actionable_option_surfaces(result: ExtractionResult) -> ExtractionResult:
        """HTML option elements are values inside a select, not independent action entrances."""
        removed = {
            n.id for n in result.nodes
            if n.kind == "human_surface" and (n.attributes or {}).get("tag") == "option"
        }
        if not removed:
            return result
        result.nodes = [n for n in result.nodes if n.id not in removed]
        result.edges = [e for e in result.edges if e.src not in removed and e.dst not in removed]
        return result

    @staticmethod
    def _edge_key(edge: Edge) -> tuple[str, str, str]:
        return edge.src, edge.kind, edge.dst

    def _append_edge(self, record: FileRecord, result: ExtractionResult, src: str, dst: str, kind: str,
                     *, coverage: str = "PARTIAL", attributes: dict[str, Any] | None = None,
                     evidence_ids: list[str] | None = None, line: int | None = None) -> None:
        existing = {self._edge_key(e) for e in result.edges}
        if (src, kind, dst) in existing:
            return
        result.edges.append(Edge(
            stable_id("edge", src, kind, dst, record.id, line), src, dst, kind, coverage,
            attributes or {}, sorted(set(evidence_ids or [])),
        ))

    def _add_inline_handler_resolution(self, record: FileRecord, result: ExtractionResult) -> None:
        evidence_line = self._evidence_lines(result)
        callbacks_by_line: dict[int, list[Node]] = defaultdict(list)
        for node in result.nodes:
            if node.kind != "symbol" or not node.name.startswith("<jsx-callback@"):
                continue
            line = self._node_evidence_line(node, evidence_line)
            if line is not None:
                callbacks_by_line[line].append(node)

        for handler in list(result.nodes):
            if handler.kind != "handler_reference":
                continue
            attrs = handler.attributes or {}
            expression = str(attrs.get("expression") or "")
            if "=>" not in expression:
                continue
            line = self._node_evidence_line(handler, evidence_line)
            candidates = callbacks_by_line.get(line or -1, [])
            if len(candidates) != 1:
                continue
            callback = candidates[0]
            self._append_edge(
                record, result, handler.id, callback.id, "resolves_to", coverage="MAPPED",
                attributes={"resolution": "same_jsx_expression_source_location"},
                evidence_ids=sorted(set(handler.evidence_ids + callback.evidence_ids)), line=line,
            )

    @staticmethod
    def _parse_binding_names(binding: str) -> list[tuple[str, str]]:
        """Return (prop_name, local_name) pairs from a shallow object binding pattern."""
        value = binding.strip()
        if not (value.startswith("{") and value.endswith("}")):
            return []
        out: list[tuple[str, str]] = []
        for raw in value[1:-1].split(","):
            item = raw.strip()
            if not item or item.startswith("..."):
                continue
            item = item.split("=", 1)[0].strip()
            if ":" in item:
                prop, local = [x.strip() for x in item.split(":", 1)]
            else:
                prop = local = item
            if re.fullmatch(r"[A-Za-z_$][\w$]*", prop) and re.fullmatch(r"[A-Za-z_$][\w$]*", local):
                out.append((prop, local))
        return out

    def _add_destructured_react_prop_routes(self, record: FileRecord, result: ExtractionResult) -> None:
        evidence_line = self._evidence_lines(result)
        component_locals: dict[tuple[str, str], str] = {}
        for node in result.nodes:
            if node.kind != "symbol" or not node.name[:1].isupper():
                continue
            attrs = node.attributes or {}
            if attrs.get("symbol_role") != "function":
                continue
            for parameter in attrs.get("parameters") or []:
                for prop, local in self._parse_binding_names(str(parameter)):
                    component_locals[(node.name, local)] = prop

        if not component_locals:
            return

        nodes = {n.id: n for n in result.nodes}
        existing_prop_nodes = {
            ((n.attributes or {}).get("component"), (n.attributes or {}).get("prop")): n
            for n in result.nodes
            if n.kind == "handler_reference" and (n.attributes or {}).get("role") == "prop_endpoint"
        }

        for edge in list(result.edges):
            if edge.kind != "dispatches_to":
                continue
            surface = nodes.get(edge.src)
            handler = nodes.get(edge.dst)
            if not surface or not handler or surface.kind != "human_surface" or handler.kind != "handler_reference":
                continue
            component = str((surface.attributes or {}).get("component_function") or "").split(".")[-1]
            local = handler.name.strip()
            prop = component_locals.get((component, local))
            if not prop:
                continue
            endpoint = existing_prop_nodes.get((component, prop))
            if endpoint is None:
                line = self._node_evidence_line(surface, evidence_line)
                endpoint = Node(
                    stable_id("handler_reference", f"react-prop:{component}:{prop}", f"{component}.{prop}"),
                    "handler_reference", f"{component}.{prop}", record.id, record.path, "PARTIAL",
                    {"framework": "react", "component": component, "prop": prop, "role": "prop_endpoint",
                     "resolution": "destructured_component_parameter"},
                    sorted(set(surface.evidence_ids + handler.evidence_ids)),
                )
                result.nodes.append(endpoint)
                nodes[endpoint.id] = endpoint
                existing_prop_nodes[(component, prop)] = endpoint
            self._append_edge(
                record, result, handler.id, endpoint.id, "routes_to", coverage="PARTIAL",
                attributes={"resolution": "destructured_component_parameter"},
                evidence_ids=sorted(set(handler.evidence_ids + endpoint.evidence_ids)),
                line=self._node_evidence_line(surface, evidence_line),
            )

    @staticmethod
    def _react_state_setters(text: str) -> dict[str, dict[str, Any]]:
        setters: dict[str, dict[str, Any]] = {}
        array_pattern = re.compile(
            r"\b(?:const|let)\s*\[\s*([A-Za-z_$][\w$]*)\s*,\s*([A-Za-z_$][\w$]*)\s*\]\s*=\s*useState(?:\s*<[^;\n=]+>)?\s*\(",
            re.MULTILINE,
        )
        for match in array_pattern.finditer(text):
            state_name, setter = match.groups()
            setters[setter] = {"state": state_name, "hook": "useState", "coverage": "MAPPED"}

        object_pattern = re.compile(
            r"\b(?:const|let)\s*\{([^{}]+)\}\s*=\s*([A-Za-z_$][\w$]*State)\s*\(",
            re.MULTILINE,
        )
        for match in object_pattern.finditer(text):
            binding, hook = match.groups()
            if not hook.startswith("use"):
                continue
            for prop, local in TypeScriptElectronAdapter._parse_binding_names("{" + binding + "}"):
                if not local.startswith("set") or len(local) <= 3 or not local[3:4].isupper():
                    continue
                setters.setdefault(local, {
                    "state": prop[3:4].lower() + prop[4:] if prop.startswith("set") else prop,
                    "hook": hook,
                    "coverage": "PARTIAL",
                })
        return setters

    def _add_react_state_changes(self, record: FileRecord, text: str, result: ExtractionResult) -> None:
        setters = self._react_state_setters(text)
        if not setters:
            return
        for call in list(result.nodes):
            if call.kind != "call_reference":
                continue
            callee = str((call.attributes or {}).get("callee") or call.name).strip()
            if callee not in setters:
                continue
            spec = setters[callee]
            line = (call.attributes or {}).get("callsite_line")
            coverage = str(spec["coverage"])
            state_id = stable_id("state_change", record.id, callee, line)
            state = Node(
                state_id, "state_change", f"React state via {callee}", record.id, record.path, coverage,
                {
                    "state_name": spec["state"], "setter": callee, "hook": spec["hook"],
                    "classification": "direct_react_useState" if coverage == "MAPPED" else "custom_state_hook_setter_candidate",
                    "line": line,
                },
                list(call.evidence_ids),
            )
            if not any(n.id == state_id for n in result.nodes):
                result.nodes.append(state)
            self._append_edge(
                record, result, call.id, state_id, "changes_state", coverage=coverage,
                attributes={"resolution": state.attributes["classification"]},
                evidence_ids=list(call.evidence_ids), line=line if isinstance(line, int) else None,
            )

    def _add_preload_channel_summaries(self, record: FileRecord, result: ExtractionResult) -> None:
        """Compress proven preload method -> symbol -> IPC call -> channel paths.

        The direct detailed path remains intact. The summary edge exists only to stop framework plumbing
        depth from hiding a terminal that is already mechanically proven.
        """
        nodes = {n.id: n for n in result.nodes}
        by_src: dict[str, list[Edge]] = defaultdict(list)
        for edge in result.edges:
            by_src[edge.src].append(edge)

        endpoints = [
            n for n in result.nodes
            if n.kind == "handler_reference" and (n.attributes or {}).get("role") == "preload_api"
        ]
        allowed = {"resolves_to", "calls", "crosses_boundary"}
        for endpoint in endpoints:
            queue = deque([(endpoint.id, 0, [], list(endpoint.evidence_ids), True)])
            visited = {endpoint.id}
            while queue:
                current, depth, path, ev_ids, all_mapped = queue.popleft()
                if depth >= 4:
                    continue
                for edge in by_src.get(current, []):
                    if edge.kind not in allowed:
                        continue
                    dst = nodes.get(edge.dst)
                    if dst is None:
                        continue
                    next_path = path + [edge.id]
                    next_ev = sorted(set(ev_ids + list(edge.evidence_ids) + list(dst.evidence_ids)))
                    next_mapped = all_mapped and edge.coverage == "MAPPED" and dst.coverage == "MAPPED"
                    if dst.kind == "ipc_channel":
                        self._append_edge(
                            record, result, endpoint.id, dst.id, "routes_to",
                            coverage="MAPPED" if next_mapped else "PARTIAL",
                            attributes={"resolution": "proven_preload_ipc_summary", "detail_edge_ids": next_path},
                            evidence_ids=next_ev,
                        )
                        continue
                    if edge.dst not in visited:
                        visited.add(edge.dst)
                        queue.append((edge.dst, depth + 1, next_path, next_ev, next_mapped))
