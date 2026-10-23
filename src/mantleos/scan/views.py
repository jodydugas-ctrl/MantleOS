"""Read-only filters over one graph. Metaphors never upgrade evidence."""
from collections import deque
from .common import ScanError
from .scanner import verify_report


def view(report, specification):
    verify_report(report)
    kinds = set(specification["kinds"])
    nodes = [n for n in report["graph"]["nodes"] if (not kinds or n["kind"] in kinds)
             and max(n["loop_depth"], n["attributes"].get("nested_depth", 0)) >= specification["min_loop_depth"]]
    ids = {n["id"] for n in nodes}
    return {"schema": "scan.view/1", "graph_digest": report["graph_digest"], "filter": specification,
            "nodes": nodes, "edges": [e for e in report["graph"]["edges"] if e["src"] in ids and e["dst"] in ids],
            "evidence_upgraded": False, "gaps": report["graph"]["gaps"]}


def query(report, start, direction="impact", limit=256):
    verify_report(report)
    if direction not in ("impact", "dependencies") or not 1 <= limit <= 4096:
        raise ScanError("Invalid direction or traversal limit")
    nodes = {n["id"]: n for n in report["graph"]["nodes"]}
    if start not in nodes: raise ScanError("Unknown node ID")
    links = {}
    for edge in report["graph"]["edges"]:
        if edge["kind"] not in ("possible_call", "possible_import"): continue
        src, dst = edge["src"], edge["dst"]
        if direction == "impact": src, dst = dst, src
        links.setdefault(src, []).append((dst, edge["id"]))
    pending, seen, paths = deque([start]), {start}, []
    truncated = False
    while pending:
        current = pending.popleft()
        for target, eid in sorted(links.get(current, [])):
            if target in seen: continue
            if len(seen) >= limit:
                truncated = True
                continue
            seen.add(target)
            pending.append(target)
            paths.append({"from": current, "to": target, "edge": eid})
    return {"graph_digest": report["graph_digest"], "direction": direction, "nodes": [nodes[i] for i in sorted(seen)],
            "paths": paths, "truncated": truncated, "scope": "Possible static dependencies only; dynamic and external paths can be absent"}



def html_surfaces(report):
    """Project captured HTML controls without reading source paths."""
    verify_report(report)
    surfaces = {item['path']: {'sha256': item['sha256'], 'items': []}
                for item in report['graph']['files']
                if item['family'] == 'interface' and item['path'].lower().endswith(('.html', '.htm'))
                and item['status'] == 'STRUCTURE_ONLY'}
    for node in report['graph']['nodes']:
        if 'html_control' in node['attributes']:
            surfaces[node['path']]['items'].append(node['attributes']['html_control'])
    if sum(len(group['items']) for group in surfaces.values()) > 10000:
        raise ScanError('HTML surface record budget exceeded')
    return surfaces


def interface_inventory(report, identity, *, prefix=''):
    """Derive the recipe inventory from one verified graph, with no file I/O."""
    from .common import digest
    verify_report(report)
    if not isinstance(identity, str) or not identity.strip() or len(identity) > 2048:
        raise ScanError('Interface inventory requires a source identity')
    selected = [item for item in report['graph']['files']
                if item['path'].startswith(prefix) and item['path'].lower().endswith('.ui')
                and item['status'] != 'FILTERED']
    if not selected:
        raise ScanError('Interface inventory requires .ui files with supported declarations')
    for item in selected:
        if item['status'] != 'STRUCTURE_ONLY':
            reasons = [g['reason'] for g in report['graph']['gaps'] if g['path'] in (item['path'], '*')]
            raise ScanError('Incomplete interface inventory: ' + '; '.join(reasons))
    if not report['graph']['scope']['inventory_exhausted_within_exclusions']:
        raise ScanError('Incomplete interface inventory: source file/time budget')
    if len(selected) > 256 or sum(item['bytes'] for item in selected) > 16000000:
        raise ScanError('Interface source inventory budget exceeded')
    files = {item['path'][len(prefix):]: item['sha256'] for item in selected}
    for path in files:
        if not path or '\\' in path or ':' in path or any(p in ('.', '..', '') for p in path.split('/')):
            raise ScanError('Interface evidence needs safe relative paths')
    entries = []
    for node in report['graph']['nodes']:
        value = node['attributes'].get('interface_entry')
        if value is not None and node['path'].startswith(prefix) and node['path'][len(prefix):] in files:
            entry = {**value, 'id': value['id'][len(prefix):], 'file': value['file'][len(prefix):]}
            entries.append(entry)
    if not entries:
        raise ScanError('Interface inventory requires .ui files with supported declarations')
    if len(entries) > 10000:
        raise ScanError('Interface declarations exceed scan entry limit')
    entries.sort(key=lambda entry: (entry['file'], int(entry['id'].rsplit('#', 1)[1])))
    return {'schema': 'kpp.gui-inventory/2',
            'source': {'identity': identity, 'revision': digest(files), 'files': files},
            'entries': entries,
            'uninspected': ['Reference runtime, conditional visibility, platform differences and dynamic menus',
                            'Action handlers, keyboard/pointer behavior, accessibility and drag/drop',
                            'Screenshot geometry/theme and visual conformance']}
