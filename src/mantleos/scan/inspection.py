"""Settings over one verified SCAN graph; no second extractor or host process."""
from collections import Counter
from pathlib import PurePosixPath
from .common import ScanError, digest
from .investigator import _report
from .observations import snapshot_check

VIEWS = {
    'all': None,
    'application': {'module', 'class', 'function', 'import', 'call', 'config_key'},
    'artifact': {'module', 'binary_section', 'managed_module', 'assembly', 'import'},
    'members': {'class', 'function', 'field'},
    'boundaries': {'native_boundary', 'import'},
}


def settings(value=None):
    value = {} if value is None else value
    if not isinstance(value, dict) or value.keys() - {'view', 'detail', 'target', 'max_items'}:
        raise ScanError('Invalid inspection settings')
    result = {'view': 'all', 'detail': 'summary', 'target': '.', 'max_items': 2000, **value}
    if not isinstance(result['view'], str) or not isinstance(result['detail'], str) or result['view'] not in VIEWS or result['detail'] not in ('summary', 'full'):
        raise ScanError('Unknown inspection view or detail setting')
    target = result['target']
    if not isinstance(target, str) or len(target) > 1024 or '\\' in target:
        raise ScanError('Inspection target must be an inventoried relative path')
    if target != '.' and (not target or PurePosixPath(target).is_absolute()
                          or any(part in ('', '.', '..') for part in target.split('/'))
                          or ':' in target or '\x00' in target):
        raise ScanError('Inspection target must be an inventoried relative path')
    if type(result['max_items']) is not int or not 1 <= result['max_items'] <= 10000:
        raise ScanError('Inspection item budget must be between 1 and 10000')
    return result


def inspect(report, value=None, *, source=None):
    """Select application/artifact/member/boundary facts from the same snapshot."""
    graph = _report(report)
    selected = settings(value)
    snapshot_check(report, source if source is not None else report['source_root'])
    target = selected['target']
    files = [entry for entry in graph['files'] if target == '.' or entry['path'] == target
             or entry['path'].startswith(target + '/')]
    if target != '.' and not files:
        raise ScanError('Inspection target is not in the verified inventory')
    paths = {entry['path'] for entry in files}
    kinds = VIEWS[selected['view']]
    nodes = [node for node in graph['nodes'] if node['path'] in paths
             and (kinds is None or node['kind'] in kinds)]
    ids = {node['id'] for node in nodes}
    edges = [edge for edge in graph['edges'] if edge['src'] in ids and edge['dst'] in ids]
    budget = selected['max_items']
    retained_nodes = nodes[:budget]
    retained_ids = {node['id'] for node in retained_nodes}
    retained_edges = [edge for edge in edges if edge['src'] in retained_ids and edge['dst'] in retained_ids][:max(0, budget-len(retained_nodes))]
    full = selected['detail'] == 'full'
    gaps = [gap for gap in graph['gaps'] if gap['path'] in paths or gap['path'] == '*']
    result = {
        'schema': 'scan.inspection/1', 'engine': 'NATIVE_SCAN', 'settings': selected,
        'graph_digest': report['graph_digest'], 'source_root': report['source_root'],
        'files': files[:budget], 'file_count': len(files),
        'counts': dict(sorted(Counter(node['kind'] for node in nodes).items())),
        'nodes': retained_nodes if full else [], 'edges': retained_edges if full else [],
        'coverage_gaps': gaps[:budget], 'coverage_gap_count': len(gaps),
        'truncated': len(files) > budget or len(gaps) > budget
                     or (full and len(nodes)+len(edges) > len(retained_nodes)+len(retained_edges)),
        'extraction': 'REUSES_VERIFIED_GRAPH', 'specimen_executed': False,
        'external_processes': 0, 'runtime_behavior': 'UNKNOWN', 'promotion_authority': False,
    }
    result['sha256'] = digest(result)
    return result
