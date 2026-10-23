"""KPP views over canonical SCAN evidence; no second Python/JS analyzer."""
from pathlib import Path
import tempfile

from ..scan.scanner import scan as native_scan, verify_report
from ..scan.views import html_surfaces, interface_inventory
from .core import KPPError, digest

SCHEMA = 'kpp.static-scan/2'

def _project(report, depth, surfaces):
    nodes, links, keys = {}, [], {}
    for node in report['graph']['nodes']:
        kind = node['kind']
        if kind in ('function', 'class'):
            key = f"{node['path']}::{node['name']}@{node['line']}"
            if key in nodes:
                key += '#' + node['id'].split(':', 1)[-1]
            source_kind = 'ClassDef' if kind == 'class' else ('AsyncFunctionDef' if node['attributes'].get('async_function') else 'FunctionDef')
        else:
            key, source_kind = node['id'], kind
        keys[node['id']] = key
        nodes[key] = {'kind': source_kind, 'file': node['path'], 'line': node['line'],
                      'evidence_node': node['id'], 'evidence': node['evidence'],
                      **node['attributes'].get('html_control', {})}
    if depth >= 2:
        for edge in report['graph']['edges']:
            if edge['kind'] in ('possible_call', 'possible_import'):
                links.append({'from': keys[edge['src']], 'to': keys[edge['dst']],
                              'kind': 'possible-static-call' if edge['kind'] == 'possible_call' else 'possible-static-import',
                              'evidence_edge': edge['id'], 'evidence': edge['evidence']})
    paths = []
    if depth >= 3:
        adjacency = {}
        for edge in links:
            adjacency.setdefault(edge['from'], set()).add(edge['to'])
        for start in sorted(adjacency):
            frontier, seen = [(start, 0)], {start}
            for current, hops in frontier:
                if hops >= depth - 1:
                    continue
                for dest in sorted(adjacency.get(current, ())):
                    if dest not in seen:
                        seen.add(dest); frontier.append((dest, hops + 1))
                        paths.append({'from': start, 'to': dest, 'hops': hops + 1})
                        if len(paths) >= 20000:
                            break
                if len(paths) >= 20000:
                    break
            if len(paths) >= 20000:
                break
    return nodes, links, paths


def verify_scan(value):
    try:
        if value.get('schema') != SCHEMA:
            raise KPPError('Unsupported scan evidence; rescan with the shared SCAN engine')
        report = verify_report(value['native_report'])
        if value['root'] != report['source_root'] or value['graph_digest'] != report['graph_digest']:
            raise KPPError('Scan source identity mismatch')
        depth = value['requested_depth']
        if type(depth) is not int or not 1 <= depth <= 32:
            raise KPPError('Invalid scan depth')
        if value['html_surfaces'] != html_surfaces(report):
            raise KPPError('HTML surface projection differs from canonical evidence')
        expected = _inventory(report, value['source_identity'])
        if value['interface_inventory'] != expected:
            raise KPPError('Interface inventory projection differs from canonical evidence')
        nodes, edges, paths = _project(report, depth, value['html_surfaces'])
        if (nodes, edges, paths) != (value['nodes'], value['edges'], value['reachable']):
            raise KPPError('KPP scan projection differs from canonical evidence')
        if value['sha256'] != digest({k: v for k, v in value.items() if k != 'sha256'}):
            raise KPPError('KPP scan projection checksum mismatch')
        return value
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise KPPError(str(error)) from error


def _inventory(report, identity):
    if any(e['path'].lower().endswith('.ui') and e['status'] != 'FILTERED' for e in report['graph']['files']):
        return interface_inventory(report, identity)
    return None


def scan(root, depth=1, max_files=400, max_bytes=1_000_000, *, workspace=None,
         filters=None, identity=None, execution='serial'):
    if type(depth) is not int or not 1 <= depth <= 32:
        raise KPPError('Depth must be 1..32')
    root = Path(root).resolve()
    identity = root.name if identity is None else identity
    try:
        options = dict(max_files=max_files, max_file_bytes=max_bytes, filters=filters, execution=execution)
        if workspace is None:
            with tempfile.TemporaryDirectory(prefix='kpp-scan-') as temporary:
                report = native_scan(root, temporary, **options)
        else:
            report = native_scan(root, workspace, **options)
        surfaces = html_surfaces(report)
        inventory = _inventory(report, identity)
        nodes, edges, paths = _project(report, depth, surfaces)
        result = {'schema': SCHEMA, 'root': str(root), 'requested_depth': depth,
                  'engine': 'mantleos.scan', 'graph_digest': report['graph_digest'],
                  'native_report': report, 'html_surfaces': surfaces,
                  'source_identity': identity, 'interface_inventory': inventory,
                  'scope': 'Canonical SCAN evidence with derived recipe and interface views',
                  'limitations': 'Static syntax only; source hashes are not authentication; no runtime causality or approval',
                  'files': [{'path': e['path'], 'bytes': e['bytes'], 'sha256': e['sha256']}
                            for e in report['graph']['files'] if e.get('sha256')],
                  'nodes': nodes, 'edges': edges, 'reachable': paths,
                  'skipped': [{'file': gap['path'], 'reason': gap['reason']} for gap in report['graph']['gaps']],
                  'bounded': {'max_files': max_files, 'max_bytes_per_file': max_bytes}}
        result['sha256'] = digest(result)
        return verify_scan(result)
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise KPPError(str(error)) from error
