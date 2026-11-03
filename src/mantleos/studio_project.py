"""Portable Studio design data. Import never executes code or transfers approval."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import zipfile

from . import anchor_design, anchors, json_contract as c
from .kpp.core import validate_recipe
from .transactions import atomic_bytes

SCHEMA = 'anchor-studio.project/1'
LIMIT = 16 * 1024 * 1024


def validate(value):
    required={'schema', 'id', 'recipe', 'layout', 'unresolved', 'provenance', 'evidence'}
    c.require(type(value) is dict and required<=set(value)<=required|{'fixtures'},'Unexpected project fields')
    c.require(value['schema'] == SCHEMA, 'Unsupported Studio project')
    c.identifier(value['id'])
    recipe = validate_recipe(value['recipe'])
    design = anchor_design.recipe_design(recipe)
    c.require(design is not None, 'Studio project needs an explicit canonical design')
    ids = {a['id'] for a in design['applications']}
    c.require(type(value['layout']) is dict and set(value['layout']) <= ids, 'Unknown layout application')
    for position in value['layout'].values():
        c.require(type(position) is list and len(position) == 2 and all(type(x) in (int, float) and abs(x) <= 1e6 for x in position), 'Invalid canvas coordinates')
    for key in ('unresolved', 'provenance', 'evidence'):
        c.require(type(value[key]) is list and len(value[key]) <= 256, 'Invalid project collection')
    # Only content references, never arbitrary flow payloads, transcript or credentials.
    for key in ('provenance', 'evidence'):
        for ref in value[key]:
            c.shape(ref, {'kind', 'sha256'})
            c.text(ref['kind']); pin = ref['sha256']
            c.require(type(pin) is str and len(pin) == 64 and all(x in '0123456789abcdef' for x in pin), 'Invalid content reference')
    for edge in value['unresolved']:
        c.shape(edge, {'from', 'to'})
        c.require(edge['from'] in ids and edge['to'] in ids, 'Unknown unresolved endpoint')
    fixtures=value.get('fixtures',{})
    c.require(type(fixtures) is dict and len(fixtures)<=32,'Invalid public fixtures')
    for name,item in fixtures.items():
        c.require(type(name) is str and (name=='suite.json' or re.fullmatch(r'case_[A-Za-z0-9_]+\.py',name)), 'Unsafe fixture name')
        c.shape(item,{'content','sha256'})
        c.require(type(item['content']) is str and len(item['content'].encode('utf8'))<=65536,'Fixture too large')
        c.require(hashlib.sha256(item['content'].encode('utf8')).hexdigest()==item['sha256'],'Fixture digest mismatch')
    c.canonical(value)
    return value


def save(value, target):
    import io
    value = validate(value)
    raw = c.canonical(value, limit=LIMIT).encode('utf-8')
    manifest = {'schema': 'anchor-studio.manifest/1', 'files': {'project.json': hashlib.sha256(raw).hexdigest()},
                'execution': 'NONE', 'acceptance': 'NOT_TRANSFERRED'}
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in [('project.json', raw), ('manifest.json', c.canonical(manifest).encode())]:
            info = zipfile.ZipInfo(name, (1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    atomic_bytes(Path(target), out.getvalue(), replace=False)
    return {'sha256': hashlib.sha256(out.getvalue()).hexdigest(), 'status': 'DESIGN_ONLY', 'execution': 'NONE'}


def load(source):
    source = Path(source)
    c.require(source.stat().st_size <= LIMIT, 'Studio archive too large')
    with zipfile.ZipFile(source) as z:
        entries = z.infolist()
        c.require(len(entries) == 2 and {i.filename for i in entries} == {'project.json','manifest.json'}, 'Unexpected or duplicate project entries')
        c.require(all(i.file_size <= LIMIT and not i.flag_bits & 1 for i in entries) and sum(i.file_size for i in entries) <= LIMIT, 'Unsafe project archive')
        raw = z.read('project.json'); manifest = c.loads(z.read('manifest.json').decode())
        c.require(manifest.get('schema') == 'anchor-studio.manifest/1' and manifest.get('files') == {'project.json': hashlib.sha256(raw).hexdigest()}, 'Project manifest mismatch')
        value = validate(c.loads(raw.decode()))
    return value


def inspection(value):
    value = validate(value)
    return {'schema': SCHEMA, 'id': value['id'], 'sha256': c.digest(value),
            'status': 'MAPPING_BLOCKED' if value['unresolved'] else 'STRUCTURALLY_VALID',
            'evidence': 'HISTORICAL_REQUIRES_RECHECK', 'acceptance': 'PENDING_BAKER', 'execution': 'NONE'}


def from_flows(flows, recipe):
    """Explicit draft extraction; normal automation never becomes design or code."""
    validate_recipe(recipe)
    source=c.digest(flows)
    if isinstance(flows,dict):flows=flows['flows']
    if not isinstance(flows,list):raise ValueError('Expected Node-RED flow list')
    types={'anchor-blackhole':'BlackHole','anchor-neutral':'Neutral','anchor-whitehole':'WhiteHole'}
    selected=[n for n in flows if n.get('type') in types]
    ids={n['id']:n['applicationId'] for n in selected}
    if len(ids)!=len(selected) or len(set(ids.values()))!=len(selected):raise ValueError('Duplicate design ID')
    applications=[anchors.application(n['applicationId'],definition_id=types[n['type']],attributes={
        'responsibility':n.get('responsibility',''),**{k:n[field] for k,field in [('tissue','tissueId'),('organ','organId'),('contract','contractRef')] if n.get(field)}}) for n in selected]
    prior=anchor_design.recipe_design(recipe)
    if prior is None:raise ValueError('Provide an explicit reviewed recipe/design')
    if {a['id'] for a in applications}!={a['id'] for a in prior['applications']}:raise ValueError('Changed application membership needs a reviewed recipe revision')
    # Preserve explicit canonical relationships; wires remain a separate unresolved draft.
    import copy
    recipe=copy.deepcopy(recipe);recipe['anchor_design']['applications']=applications
    unresolved=[]
    for n in selected:
        for output in n.get('wires',[]):
            for target in output:
                if target not in ids:raise ValueError('Design wire crosses into operational flow')
                unresolved.append({'from':n['applicationId'],'to':ids[target]})
    return validate({'schema':SCHEMA,'id':recipe['id'],'recipe':recipe,
        'layout':{n['applicationId']:[n.get('x',0),n.get('y',0)] for n in selected},'unresolved':unresolved,
        'provenance':[{'kind':'node-red-flow-export','sha256':source}],'evidence':[]})
