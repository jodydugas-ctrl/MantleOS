"""Recipe-owned organ projections and source-bound observations, never approval."""
import copy
import hashlib
from pathlib import Path, PurePosixPath

from .core import KPPError, SLUG, digest, validate_recipe
from .scanner import verify_scan
from ..scan.common import source_paths


def _keys(value, required, label):
    if not isinstance(value, dict) or set(value) != set(required):
        raise KPPError('Invalid fields in ' + label)


def _strings(value, label, slugs=False):
    if not isinstance(value, list) or any(not isinstance(s, str) or not s.strip() for s in value):
        raise KPPError(label + ' must be a string list')
    if len(set(value)) != len(value) or (slugs and any(not SLUG.fullmatch(s) for s in value)):
        raise KPPError('Duplicate or invalid ' + label)
    return value


def project(recipe, mapping):
    """Validate all ownership/dependencies against the existing KPP recipe."""
    validate_recipe(recipe)
    _keys(mapping, ('schema', 'recipe_id', 'recipe_sha256', 'organs'), 'organ mapping')
    if (mapping['schema'] != 'organ.mapping/0.1' or mapping['recipe_id'] != recipe['id']
            or mapping['recipe_sha256'] != digest(recipe)):
        raise KPPError('Organ mapping recipe pin mismatch')
    declarations = mapping['organs']
    if not isinstance(declarations, list) or not declarations:
        raise KPPError('Organ mapping requires declarations')
    anchors = {a['id']: a for a in recipe['anchors']}
    owners, organs = {}, {}
    for organ in declarations:
        _keys(organ, ('id', 'role', 'anchor_ids', 'requires', 'interfaces', 'capabilities', 'failure_policy'), 'organ')
        oid = organ['id']
        if not isinstance(oid, str) or not SLUG.fullmatch(oid) or oid in organs:
            raise KPPError('Duplicate or invalid organ id')
        if not isinstance(organ['role'], str) or not organ['role'].strip():
            raise KPPError('Organ requires a role')
        ids = _strings(organ['anchor_ids'], 'Anchor references', True)
        if not ids:
            raise KPPError('Organ requires Anchor references')
        for aid in ids:
            if aid not in anchors or aid in owners:
                raise KPPError('Unknown or multiply owned Anchor: ' + aid)
            owners[aid] = oid
        _strings(organ['requires'], 'organ dependencies', True)
        _strings(organ['capabilities'], 'declared capabilities')
        _keys(organ['interfaces'], ('inputs', 'outputs'), 'organ interfaces')
        for fields in organ['interfaces'].values():
            if not isinstance(fields, dict) or any(not isinstance(k, str) or not k.strip()
                    or not isinstance(v, str) or not v.strip() for k, v in fields.items()):
                raise KPPError('Interface descriptions must be string mappings')
        _keys(organ['failure_policy'], ('condition', 'response'), 'failure policy')
        if any(not isinstance(s, str) or not s.strip() for s in organ['failure_policy'].values()):
            raise KPPError('Failure policy requires condition and response')
        organs[oid] = organ
    if set(owners) != set(anchors):
        raise KPPError('Every recipe Anchor needs exactly one organ owner')
    dependencies = {}
    for oid, organ in organs.items():
        explicit = set(organ['requires'])
        if oid in explicit or explicit - organs.keys():
            raise KPPError('Unknown or self organ dependency')
        needed = {owners[d] for aid in organ['anchor_ids'] for d in anchors[aid].get('depends', [])
                  if owners[d] != oid}
        if needed - explicit:
            raise KPPError('Missing dependency from the KPP graph: ' + oid)
        dependencies[oid] = explicit
    pending = set(organs)
    while pending:
        ready = {oid for oid in pending if not dependencies[oid].intersection(pending)}
        if not ready:
            raise KPPError('Cycle in organ dependencies')
        pending -= ready
    return {'schema': 'organ.projection/0.1', 'source_recipe_id': recipe['id'],
            'source_recipe_sha256': digest(recipe), 'source_mapping_sha256': digest(mapping),
            'organ_count': len(organs), 'organs': copy.deepcopy(declarations),
            'authority': 'NONE', 'runtime_enforcement': 'NOT_ESTABLISHED',
            'kpp_acceptance': 'NOT_GRANTED', 'qualification': 'PROJECTION_ONLY'}


def recheck_source(report, source):
    """Recheck complete bounded inventory, including new files, without execution."""
    verify_scan(report)
    root = Path(source).resolve()
    if root != Path(report['root']).resolve():
        raise KPPError('Scan source root mismatch')
    graph = report['native_report']['graph']
    if not graph['scope'].get('inventory_exhausted_within_exclusions'):
        raise KPPError('Scan inventory is incomplete')
    inventory = {item['path']: item for item in graph['files']}
    observed = {}
    limit = graph['limits']['file_bytes']
    for path in source_paths(root):
        relative = path.relative_to(root).as_posix()
        if relative not in inventory:
            raise KPPError('Scan source inventory changed: ' + relative)
        with path.open('rb') as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise KPPError('Source exceeds scan byte budget: ' + relative)
        observed[relative] = hashlib.sha256(data).hexdigest()
    if set(observed) != set(inventory) or any(observed[p] != inventory[p].get('sha256') for p in observed):
        raise KPPError('Scan source pins are stale')
    return digest(observed)


def scanner_identity(report):
    directory = Path(__file__).parents[1] / 'scan'
    implementation = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(directory.iterdir()) if p.suffix in ('.py', '.cjs')}
    return digest({'implementation': implementation,
                   'adapters': report['native_report']['graph']['adapter_revisions']})


def evidence(recipe, mapping, bindings, report, source):
    """Join explicit file/node references to obligations; preserve native coverage."""
    projection = project(recipe, mapping)
    source_pin = recheck_source(report, source)
    _keys(bindings, ('schema', 'recipe_sha256', 'mapping_sha256', 'links'), 'scan bindings')
    if (bindings['schema'] != 'kpp.organ-scan-bindings/1' or bindings['recipe_sha256'] != digest(recipe)
            or bindings['mapping_sha256'] != digest(mapping)):
        raise KPPError('Scan binding recipe/mapping pin mismatch')
    graph = report['native_report']['graph']
    files = {f['path']: f for f in graph['files']}
    nodes = {n['id']: n for n in graph['nodes']}
    links = {}
    if not isinstance(bindings['links'], list):
        raise KPPError('Scan bindings require a list')
    for link in bindings['links']:
        _keys(link, ('anchor_id', 'files', 'nodes'), 'scan binding')
        aid = link['anchor_id']
        if not isinstance(aid, str) or aid not in {a['id'] for a in recipe['anchors']} or aid in links:
            raise KPPError('Duplicate or unknown binding Anchor')
        paths = _strings(link['files'], 'bound source paths')
        refs = _strings(link['nodes'], 'graph references')
        if not paths:
            raise KPPError('A binding needs source files')
        for path in paths:
            if (path not in files or '\\' in path or ':' in path or PurePosixPath(path).is_absolute()
                    or any(p in ('', '.', '..') for p in path.split('/'))):
                raise KPPError('Unknown or unsafe bound source path')
        if any(ref not in nodes or nodes[ref]['path'] not in paths for ref in refs):
            raise KPPError('Invalid graph reference or unrelated source file')
        links[aid] = link
    observations = []
    for anchor in recipe['anchors']:
        link = links.get(anchor['id'])
        observations.append({'anchor_id': anchor['id'],
            'static_evidence': 'OBSERVED' if link else 'UNMAPPED',
            'files': [{'path': p, 'sha256': files[p]['sha256'], 'coverage': files[p]['status'],
                       'limitations': files[p].get('limitations', [])} for p in link['files']] if link else [],
            'graph_references': list(link['nodes']) if link else [],
            'runtime_test': 'NOT_RUN_BY_SCANNER', 'baker_acceptance': 'NOT_GRANTED'})
    return {'schema': 'kpp.organ-evidence/1', 'recipe_sha256': digest(recipe),
            'mapping_sha256': projection['source_mapping_sha256'], 'source_sha256': source_pin,
            'scan_sha256': report['sha256'], 'graph_digest': report['graph_digest'],
            'scanner_identity': scanner_identity(report), 'observations': observations,
            'gaps': copy.deepcopy(graph['gaps']), 'authority': 'NONE', 'kpp_acceptance': 'NOT_GRANTED'}
