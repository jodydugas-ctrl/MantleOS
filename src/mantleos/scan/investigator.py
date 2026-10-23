"""Bounded static feature trace, snapshot comparison and change-impact dossiers."""
from collections import defaultdict, deque
import re
from .common import ScanError, digest
from .scanner import verify_report
from .symbols import SCHEMA

MAX_INPUT_RECORDS = 500000
EDGE_LABELS = {"contains": "STATIC_CONTAINMENT", "inside_loop": "STATIC_REPETITION",
               "possible_call": "POSSIBLE_STATIC_CALL", "possible_import": "POSSIBLE_STATIC_IMPORT"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
COVERED = {"STRUCTURE_ONLY", "STRUCTURE_AND_PARTIAL_FLOW"}
QUESTION_WORDS = {"where", "which", "how", "does", "do", "is", "the", "to", "a", "an", "of", "in", "what", "when", "and", "or", "for"}
TRACE_SCOPE = "Possible static relationships only; paths do not prove runtime causality or behavior"
DIFF_SCOPE = "Static evidence and candidate correspondences only; runtime impact and equivalence remain UNKNOWN"
STATUSES = {"CHANGED", "UNCHANGED", "MOVED", "RENAMED", "ADDED", "REMOVED", "AMBIGUOUS", "UNKNOWN_COVERAGE"}


def _report(report):
    if not isinstance(report, dict) or not isinstance(report.get("graph"), dict):
        raise ScanError("Scan report object missing")
    graph = report.get("graph", {})
    if not all(isinstance(graph.get(key), list) for key in ("nodes", "edges", "files", "gaps")):
        raise ScanError("Scan graph collections missing")
    if sum(len(graph[key]) for key in ("nodes", "edges", "files", "gaps")) > MAX_INPUT_RECORDS:
        raise ScanError("Investigator input record budget exceeded")
    for node in graph["nodes"]:
        if (not isinstance(node, dict) or not all(isinstance(node.get(key), str) for key in ("id", "kind", "name", "path")) or
            not isinstance(node.get("attributes"), dict) or not isinstance(node.get("comparison", {}), dict) or
            any(node.get(key) is not None and (type(node[key]) is not int or node[key] < 1) for key in ("line", "end_line"))):
            raise ScanError("Invalid syntax record")
        if not _comparable(node):
            raise ScanError("Current comparison metadata required; rescan the source")
    for edge in graph["edges"]:
        if not isinstance(edge, dict) or not all(isinstance(edge.get(key), str) for key in ("id", "kind", "src", "dst")):
            raise ScanError("Invalid relationship record")
    if len({edge["id"] for edge in graph["edges"]}) != len(graph["edges"]):
        raise ScanError("Duplicate relationship IDs")
    for entry in graph["files"]:
        if not isinstance(entry, dict) or not all(isinstance(entry.get(key), str) for key in ("path", "family", "status")):
            raise ScanError("Invalid file coverage record")
    scope = graph.get("scope", {})
    if (not isinstance(scope, dict) or scope.get("modality") != "STATIC" or scope.get("specimen_executed") is not False or
        scope.get("runtime_observed") is not False):
        raise ScanError("Investigator requires a static, non-executed source graph")
    verify_report(report)
    return graph


def _limit(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ScanError(f"{name} must be an integer between {low} and {high}")


def _select(nodes, selector, limit):
    if isinstance(selector, list):
        if not selector or len(selector) > 64 or not all(isinstance(item, str) and len(item) <= 256 for item in selector):
            raise ScanError("Explicit origin list must contain 1-64 bounded node IDs")
        by_id = {node["id"]: node for node in nodes}
        if any(item not in by_id for item in selector):
            raise ScanError("Unknown origin node ID")
        matches = [by_id[item] for item in sorted(set(selector))]
    else:
        if not isinstance(selector, str) or not selector.strip() or len(selector) > 256:
            raise ScanError("Feature selector must contain 1-256 characters")
        matches = [node for node in nodes if selector in (node["id"], node.get("symbol_key"))]
        if not matches:
            matches = [node for node in nodes if selector in
                       (node["name"], node.get("comparison", {}).get("qualified_name"))]
        if not matches:
            terms = [term for term in re.findall(r"[\w]+", selector.casefold()) if term not in QUESTION_WORDS]
            matches = [node for node in nodes if terms and all(term in
                       (node["path"] + " " + node["name"] + " " + node.get("comparison", {}).get("qualified_name", "")).casefold()
                       for term in terms)]
    matches = sorted(matches, key=lambda node: (node["path"], node["line"] or 0, node["id"]))
    return matches[:limit], len(matches) > limit


def trace(report, selector, *, direction="dependencies", max_depth=6, max_nodes=256,
          max_edges=512, edge_kinds=None):
    graph = _report(report)
    if direction not in ("dependencies", "impact"):
        raise ScanError("Direction must be dependencies or impact")
    for value, name, low, high in ((max_depth, "max_depth", 0, 32), (max_nodes, "max_nodes", 1, 4096),
                                   (max_edges, "max_edges", 0, 8192)):
        _limit(value, name, low, high)
    if edge_kinds is not None and (not isinstance(edge_kinds, (list, tuple, set, frozenset)) or
                                  not all(isinstance(kind, str) for kind in edge_kinds)):
        raise ScanError("Edge types must be a collection of documented names")
    kinds = set(EDGE_LABELS if edge_kinds is None else edge_kinds)
    if not kinds <= EDGE_LABELS.keys():
        raise ScanError("Only documented static edge types may be traversed")
    origins, origin_limit = _select(graph["nodes"], selector, min(64, max_nodes))
    nodes = {node["id"]: node for node in graph["nodes"]}
    adjacency = defaultdict(list)
    resolved = set()
    for edge in graph["edges"]:
        if edge["kind"] in ("possible_call", "possible_import"):
            resolved.add(edge.get("occurrence"))
        if edge["kind"] in kinds:
            source, target = edge["src"], edge["dst"]
            if direction == "impact":
                source, target = target, source
            adjacency[source].append((target, edge))
    for edges in adjacency.values():
        edges.sort(key=lambda pair: (pair[0], pair[1]["id"]))
    pending = deque(node["id"] for node in origins)
    routes = {node["id"]: {"origin": node["id"], "nodes": [node["id"]], "edges": [], "labels": []} for node in origins}
    selected_edges, reasons, examined = {}, set(), 0
    if origin_limit:
        reasons.add("ORIGINS")
    while pending:
        current = pending.popleft()
        route = routes[current]
        if len(route["edges"]) >= max_depth:
            if any(target not in routes for target, _ in adjacency[current]):
                reasons.add("DEPTH")
            continue
        for target, edge in adjacency[current]:
            if examined >= max_edges:
                reasons.add("EDGES")
                pending.clear()
                break
            examined += 1
            if target not in routes:
                if len(routes) >= max_nodes:
                    reasons.add("NODES")
                    continue
                routes[target] = {"origin": route["origin"], "nodes": route["nodes"] + [target],
                                  "edges": route["edges"] + [edge["id"]],
                                  "labels": route["labels"] + [EDGE_LABELS[edge["kind"]]]}
                pending.append(target)
            selected_edges[edge["id"]] = edge
    unresolved = [{"node": node_id, "path": nodes[node_id]["path"], "line": nodes[node_id]["line"],
                   "reason": "No unique static binding; runtime/dynamic/external target is UNKNOWN"}
                  for node_id in sorted(routes) if nodes[node_id]["kind"] in ("call", "import") and node_id not in resolved]
    return {"schema": "scan.trace/1", "graph_digest": report["graph_digest"], "selector": selector,
            "direction": direction, "origins": [node["id"] for node in origins],
            "nodes": [nodes[node_id] for node_id in sorted(routes)],
            "edges": [selected_edges[edge_id] for edge_id in sorted(selected_edges)],
            "paths": [routes[node_id] for node_id in sorted(routes)], "unresolved": unresolved,
            "limits": {"depth": max_depth, "nodes": max_nodes, "examined_edges": max_edges, "origins": 64},
            "examined_edges": examined, "truncated": bool(reasons), "limit_reasons": sorted(reasons),
            "coverage_gaps": graph["gaps"], "status": "STATIC_PATHS" if origins else "NO_MATCH",
            "scope": TRACE_SCOPE}


def _comparable(node):
    comparison = node.get("comparison", {})
    return (comparison.get("schema") == SCHEMA and isinstance(comparison.get("logical_key"), str)
            and re.fullmatch(r"logical:[0-9a-f]{64}", comparison["logical_key"]) is not None
            and type(comparison.get("ambiguous")) is bool and comparison.get("authority") == "COMPARISON_HINT_ONLY"
            and isinstance(comparison.get("logical_scope"), list) and isinstance(comparison.get("scope"), list)
            and isinstance(comparison.get("qualified_name"), str)
            and isinstance(node.get("symbol_key"), str) and re.fullmatch(r"symbol:[0-9a-f]{64}", node["symbol_key"]) is not None and
            all(isinstance(node.get(key), str) and SHA.fullmatch(node[key]) for key in ("syntax_sha256", "relocation_sha256")))


def _reference(node):
    return {key: node.get(key) for key in ("id", "symbol_key", "kind", "name", "path", "line", "end_line", "source_sha256")}


def _absence_known(graph, files, node):
    entry = files.get(node["path"])
    if entry is not None:
        return entry["status"] in COVERED
    return graph.get("scope", {}).get("inventory_exhausted_within_exclusions") is True


def snapshot_diff(left, right, *, max_items=5000, max_candidates=1000, impact_nodes=256):
    before, after = _report(left), _report(right)
    _limit(max_items, "max_items", 1, 20000)
    _limit(max_candidates, "max_candidates", 0, 5000)
    _limit(impact_nodes, "impact_nodes", 1, 4096)
    buckets = [defaultdict(list), defaultdict(list)]
    files = [{entry["path"]: entry for entry in graph["files"]} for graph in (before, after)]
    changes, unmatched, candidate_count = [], [[], []], 0
    counts = defaultdict(int)
    def record(status, old=None, new=None, **details):
        counts[status] += 1
        if len(changes) < max_items:
            changes.append({"status": status, "before": _reference(old) if old else None,
                            "after": _reference(new) if new else None, **details})
    for side, graph in enumerate((before, after)):
        for node in graph["nodes"]:
            buckets[side][node["comparison"]["logical_key"]].append(node)
    for key in sorted(buckets[0].keys() | buckets[1].keys()):
        old_group, new_group = buckets[0][key], buckets[1][key]
        if len(old_group) > 1 or len(new_group) > 1 or any(node["comparison"]["ambiguous"] for node in old_group + new_group):
            record("AMBIGUOUS", before_candidates=[_reference(node) for node in old_group[:32]],
                   after_candidates=[_reference(node) for node in new_group[:32]],
                   candidates_truncated=len(old_group) > 32 or len(new_group) > 32,
                   reason="Duplicate declaration/occurrence or ambiguous enclosing scope; no ordinal-based identity assertion")
        elif old_group and new_group:
            old, new = old_group[0], new_group[0]
            changed = old["syntax_sha256"] != new["syntax_sha256"]
            record("CHANGED" if changed else "UNCHANGED", old, new, match="LOGICAL_KEY_HINT",
                   evidence_rebound=old["id"] != new["id"],
                   location_changed=(old["line"], old["end_line"]) != (new["line"], new["end_line"]),
                   signature_changed=old.get("signature_sha256") != new.get("signature_sha256"),
                   scope="Static syntax comparison, not runtime equivalence")
        else:
            unmatched[0].extend(old_group)
            unmatched[1].extend(new_group)
    moved = [defaultdict(list), defaultdict(list)]
    for side in (0, 1):
        for node in unmatched[side]:
            moved[side][(node["kind"], node["relocation_sha256"])].append(node)
    consumed = set()
    for key in sorted(moved[0].keys() & moved[1].keys()):
        old_group, new_group = moved[0][key], moved[1][key]
        if candidate_count >= max_candidates:
            continue
        candidate_count += 1
        if len(old_group) == len(new_group) == 1:
            old, new = old_group[0], new_group[0]
            renamed = old["name"] != new["name"]
            relocated = old["path"] != new["path"] or old["comparison"]["logical_scope"][:-1] != new["comparison"]["logical_scope"][:-1]
            record("MOVED" if relocated else "RENAMED", old, new, renamed=renamed,
                   match="NORMALIZED_SYNTAX_CANDIDATE", confidence="CANDIDATE_ONLY",
                   scope="Similar syntax ignoring declaration name; no behavioral identity or equivalence is asserted")
        else:
            record("AMBIGUOUS", before_candidates=[_reference(node) for node in old_group[:32]],
                   after_candidates=[_reference(node) for node in new_group[:32]],
                   candidates_truncated=len(old_group) > 32 or len(new_group) > 32,
                   reason="Multiple possible moves/renames share normalized syntax; no match selected")
        consumed.update(node["id"] for node in old_group + new_group)
    for side, status in ((0, "REMOVED"), (1, "ADDED")):
        other = after if side == 0 else before
        for node in unmatched[side]:
            if node["id"] in consumed:
                continue
            known = _absence_known(other, files[1 - side], node)
            record(status if known else "UNKNOWN_COVERAGE", node if side == 0 else None, node if side == 1 else None,
                   reason="Static record absent in covered snapshot" if known else "Other snapshot lacks sufficient coverage to establish absence")
    file_changes = []
    file_count = 0
    for path in sorted(files[0].keys() | files[1].keys()):
        old, new = files[0].get(path), files[1].get(path)
        if old == new:
            continue
        file_count += 1
        if len(file_changes) < max_items:
            covered = (not old or old["status"] in COVERED) and (not new or new["status"] in COVERED)
            file_changes.append({"path": path, "before": old, "after": new,
                                 "class": "SOURCE_INVENTORY_CHANGE" if covered else "UNSUPPORTED_OR_LIMITED_COVERAGE",
                                 "behavior": "UNKNOWN"})
    impact = {}
    for side, report in (("before", left), ("after", right)):
        seeds = sorted({change[side]["id"] for change in changes if change.get(side) and change["status"] != "UNCHANGED"})
        impact[side] = trace(report, seeds[:64], direction="impact", max_nodes=impact_nodes) if seeds else None
        if impact[side] and len(seeds) > 64:
            impact[side]["truncated"] = True
            impact[side]["limit_reasons"].append("CHANGE_ORIGINS")
    omitted = sum(counts.values()) - len(changes)
    result = {"schema": "scan.diff/1", "before_graph_digest": left["graph_digest"], "after_graph_digest": right["graph_digest"],
              "changes": changes, "counts": dict(sorted(counts.items())), "file_changes": file_changes,
              "impact": impact, "coverage_gaps": {"before": before["gaps"], "after": after["gaps"]},
              "limits": {"items": max_items, "candidate_groups": max_candidates, "impact_nodes": impact_nodes,
                         "input_records": MAX_INPUT_RECORDS}, "omitted_items": omitted,
              "omitted_file_changes": file_count - len(file_changes), "candidate_groups_examined": candidate_count,
              "candidate_budget_exhausted": len(moved[0].keys() & moved[1].keys()) > candidate_count,
              "truncated": bool(omitted or file_count > len(file_changes) or len(moved[0].keys() & moved[1].keys()) > candidate_count
                                or any(change.get("candidates_truncated") for change in changes)
                                or any(value and value["truncated"] for value in impact.values())),
              "scope": DIFF_SCOPE}
    result["dossier_sha256"] = digest(result)
    return result


def _verify_trace(value, report):
    """Validate source references and path math independently of traversal."""
    graph = _report(report)
    if not isinstance(value, dict) or value.get("schema") != "scan.trace/1" or value.get("graph_digest") != report["graph_digest"] or value.get("scope") != TRACE_SCOPE:
        raise ScanError("Trace schema, source identity or static scope mismatch")
    limits = value["limits"]
    for key, low, high in (("nodes", 1, 4096), ("depth", 0, 32), ("examined_edges", 0, 8192)):
        _limit(limits[key], key, low, high)
    _limit(value["examined_edges"], "examined_edges", 0, limits["examined_edges"])
    if limits["origins"] != 64 or type(value["truncated"]) is not bool:
        raise ScanError("Trace origin or truncation contract mismatch")
    original_nodes = {node["id"]: node for node in graph["nodes"]}
    original_edges = {edge["id"]: edge for edge in graph["edges"]}
    nodes = {node["id"]: node for node in value["nodes"]}
    edges = {edge["id"]: edge for edge in value["edges"]}
    if len(nodes) != len(value["nodes"]) or len(nodes) > limits["nodes"] or len(edges) != len(value["edges"]) or len(edges) > limits["examined_edges"]:
        raise ScanError("Trace record budget or uniqueness mismatch")
    if any(original_nodes.get(key) != node for key, node in nodes.items()):
        raise ScanError("Trace node differs from its source evidence")
    if any(original_edges.get(key) != edge or edge["kind"] not in EDGE_LABELS or edge["src"] not in nodes or edge["dst"] not in nodes for key, edge in edges.items()):
        raise ScanError("Trace edge differs from static source evidence")
    if value["direction"] not in ("impact", "dependencies") or not set(value["origins"]) <= nodes.keys():
        raise ScanError("Invalid trace direction or origins")
    selected, _ = _select(graph["nodes"], value["selector"], min(64, limits["nodes"]))
    if value["origins"] != [node["id"] for node in selected]:
        raise ScanError("Trace origins do not match the bounded selector")
    endpoints = set()
    for route in value["paths"]:
        if (not route["nodes"] or route["origin"] not in value["origins"] or route["nodes"][0] != route["origin"] or
            len(route["nodes"]) != len(route["edges"]) + 1 or len(route["labels"]) != len(route["edges"]) or
            len(route["edges"]) > limits["depth"] or not set(route["nodes"]) <= nodes.keys()):
            raise ScanError("Invalid trace route or depth")
        endpoints.add(route["nodes"][-1])
        for index, edge_id in enumerate(route["edges"]):
            edge = edges.get(edge_id)
            if edge is None or route["labels"][index] != EDGE_LABELS[edge["kind"]]:
                raise ScanError("Trace path label is not the source's static relationship")
            source, target = (edge["dst"], edge["src"]) if value["direction"] == "impact" else (edge["src"], edge["dst"])
            if route["nodes"][index:index + 2] != [source, target]:
                raise ScanError("Trace path is disconnected")
    if endpoints != nodes.keys() or len(value["paths"]) != len(nodes):
        raise ScanError("Trace path coverage mismatch")
    return {"result": "PASS", "scope": "STATIC_REFERENCE_AND_PATH_CONSISTENCY_ONLY", "graph_digest": report["graph_digest"]}


def _verify_diff(value, left, right):
    """Check a dossier's byte identity, references and claimed match classes."""
    before, after = _report(left), _report(right)
    if not isinstance(value, dict) or value.get("schema") != "scan.diff/1" or value.get("scope") != DIFF_SCOPE:
        raise ScanError("Diff schema or static scope mismatch")
    body = {key: item for key, item in value.items() if key != "dossier_sha256"}
    if digest(body) != value.get("dossier_sha256") or value["before_graph_digest"] != left["graph_digest"] or value["after_graph_digest"] != right["graph_digest"]:
        raise ScanError("Diff identity mismatch")
    nodes = [{node["id"]: node for node in graph["nodes"]} for graph in (before, after)]
    logical = [{node["comparison"]["logical_key"] for node in graph["nodes"] if _comparable(node)} for graph in (before, after)]
    files = [{entry["path"]: entry for entry in graph["files"]} for graph in (before, after)]
    _limit(value["limits"]["items"], "items", 1, 20000)
    if len(value["changes"]) > value["limits"]["items"]:
        raise ScanError("Diff output record budget exceeded")
    def reference(ref, side):
        if ref is None:
            return None
        node = nodes[side].get(ref["id"])
        if node is None or ref != _reference(node):
            raise ScanError("Diff reference does not match source evidence")
        return node
    observed_counts = defaultdict(int)
    for change in value["changes"]:
        status = change["status"]
        if status not in STATUSES:
            raise ScanError("Unknown diff status")
        observed_counts[status] += 1
        old, new = reference(change.get("before"), 0), reference(change.get("after"), 1)
        for side, key in ((0, "before_candidates"), (1, "after_candidates")):
            if len(change.get(key, [])) > 32:
                raise ScanError("Ambiguous candidate budget exceeded")
            for item in change.get(key, []):
                reference(item, side)
        if status in ("CHANGED", "UNCHANGED"):
            if not old or not new or not _comparable(old) or not _comparable(new) or old["comparison"]["logical_key"] != new["comparison"]["logical_key"] or old["comparison"]["ambiguous"] or new["comparison"]["ambiguous"]:
                raise ScanError("Diff logical match is not supported")
            if (old["syntax_sha256"] == new["syntax_sha256"]) != (status == "UNCHANGED"):
                raise ScanError("Diff syntax claim contradicts source fingerprints")
        elif status in ("MOVED", "RENAMED"):
            if not old or not new or old["kind"] != new["kind"] or old["relocation_sha256"] != new["relocation_sha256"] or change.get("confidence") != "CANDIDATE_ONLY":
                raise ScanError("Diff move/rename lacks a candidate syntax match")
        elif status in ("ADDED", "REMOVED"):
            side = 1 if status == "ADDED" else 0
            node = new if side == 1 else old
            if not node or node["comparison"]["logical_key"] in logical[1 - side] or not _absence_known(after if side == 0 else before, files[1 - side], node):
                raise ScanError("Diff absence claim lacks covered source evidence")
    if (any(key not in STATUSES or type(count) is not int or count < observed_counts[key] for key, count in value["counts"].items()) or
        any(key not in value["counts"] for key in observed_counts) or sum(value["counts"].values()) - len(value["changes"]) != value["omitted_items"]):
        raise ScanError("Diff count/omission receipt inconsistent")
    for side, report in (("before", left), ("after", right)):
        if value["impact"][side] is not None:
            verify_trace(value["impact"][side], report)
    return {"result": "PASS", "scope": "STATIC_RECEIPT_CONSISTENCY_ONLY", "dossier_sha256": value["dossier_sha256"]}


def verify_trace(value, report):
    try:
        return _verify_trace(value, report)
    except ScanError:
        raise
    except (KeyError, TypeError, AttributeError, IndexError, ValueError, RecursionError) as error:
        raise ScanError("Malformed trace receipt: " + str(error)[:300]) from error


def verify_diff(value, left, right):
    try:
        return _verify_diff(value, left, right)
    except ScanError:
        raise
    except (KeyError, TypeError, AttributeError, IndexError, ValueError, RecursionError) as error:
        raise ScanError("Malformed diff receipt: " + str(error)[:300]) from error
