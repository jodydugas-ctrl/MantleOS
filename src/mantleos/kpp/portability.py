"""Portable, read-only-by-default reflex transfer and deterministic recovery.

No execution, admission, Baker identity verification, or code deployment. Bundles
contain local operator claims, not cryptographic signatures. Unpack always requires
fresh executed Anchors and a fresh Baker decision in the receiving environment.
"""
import difflib
import hashlib
import os
import tempfile
import uuid
import zipfile
from pathlib import Path

from .core import KPPError, canonical, digest, read_json, write_json, validate_recipe, parse_json
from .reflex import STAGE_MANIFEST, APPROVAL_SCHEMA, audit, _relative_file
from .testing import validated_suite
from .workshop import load, log, mutating, preview_fingerprint, asset, supported_runtime
from .module_revisions import revision_sources

SCHEMA = 'kpp.reflex-bundle/1'
MAX_FILES = 160
MAX_BYTES = 16 * 1024 * 1024
FILES = ('review/recipe.json', 'review/request.json', 'review/plan.json',
         'review/approval.json')


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _json(data, label):
    try:
        value = parse_json(data.decode('utf-8'))
    except (UnicodeDecodeError, ValueError) as exc:
        raise KPPError('Invalid JSON in ' + label) from exc
    if not isinstance(value, dict):
        raise KPPError('Expected JSON object in ' + label)
    return value


def _safe_name(name):
    if not isinstance(name, str) or '\\' in name or name.startswith('/') or name.endswith('/'):
        raise KPPError('Unsafe bundle filename')
    parts = name.split('/')
    if any(p in ('', '.', '..') for p in parts) or ':' in parts[0]:
        raise KPPError('Unsafe bundle filename: ' + name)
    return name


def _read_file(path):
    if path.is_symlink() or not path.is_file():
        raise KPPError('Unsafe or missing input file: ' + str(path))
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise KPPError('Portable bundle file is too large')
    return data


def _check_relationships(payload):
    """Check all cross-artifact pins, without executing or trusting claims."""
    stage = _json(payload['candidate/' + STAGE_MANIFEST], STAGE_MANIFEST)
    recipe = validate_recipe(_json(payload['review/recipe.json'], 'recipe'))
    request = _json(payload['review/request.json'], 'request')
    plan = _json(payload['review/plan.json'], 'plan')
    approval = _json(payload['review/approval.json'], 'approval')
    suite = _json(payload['suite/suite.json'], 'suite')
    if stage.get('schema') != 'kpp.reflex-stage/1' or \
       stage.get('recipe_id') != recipe['id'] or stage.get('recipe_sha256') != digest(recipe):
        raise KPPError('Bundle candidate/recipe identity mismatch')
    if plan.get('schema') != 'kpp.reflex-plan/1' or \
       plan.get('recipe_id') != recipe['id'] or plan.get('recipe_sha256') != digest(recipe) or \
       stage.get('plan_sha256') != digest(plan) or stage.get('request_sha256') != digest(request) or \
       plan.get('request_sha256') != digest(request):
        raise KPPError('Bundle plan/request pins mismatch')
    point = plan.get('tentative_point', {})
    if not isinstance(point, dict) or plan.get('decision') != 'PROPOSAL_REQUIRES_BAKER_REVIEW':
        raise KPPError('Bundle has no accepted proposal site')
    if approval.get('schema') != APPROVAL_SCHEMA or approval.get('intent') != 'stage-adapter-only' or \
       not isinstance(approval.get('baker'), str) or not approval['baker'].strip() or \
       approval.get('plan_sha256') != digest(plan) or \
       approval.get('candidate_source_node') != point.get('source_node') or \
       approval.get('source_sha256') != point.get('source_sha256') or \
       stage.get('approval_sha256') != digest(approval) or \
       stage.get('selected_source_node') != point.get('source_node'):
        raise KPPError('Bundle staging approval mismatch')
    if stage.get('required_anchor_ids') != request.get('anchors'):
        raise KPPError('Bundle Anchor mapping mismatch')
    if suite.get('schema') != 'kpp.reflex-tests/1' or \
       suite.get('recipe_sha256') != digest(recipe) or suite.get('recipe_id') != recipe['id']:
        raise KPPError('Bundle suite recipe pin mismatch')
    stage_files = stage.get('files')
    if not isinstance(stage_files, dict) or not stage_files or any(
            not isinstance(name, str) or not isinstance(wanted, str)
            for name, wanted in stage_files.items()):
        raise KPPError('Bundle stage missing or invalid inventory')
    cases = suite.get('cases')
    if not isinstance(cases, list) or not 1 <= len(cases) <= 32 or any(
            not isinstance(case, dict) or not isinstance(case.get('script'), str)
            for case in cases):
        raise KPPError('Bundle has invalid test cases')
    expected_files = {'candidate/' + STAGE_MANIFEST, 'suite/suite.json', *FILES}
    for name, wanted in stage_files.items():
        _relative_file(name)
        expected_files.add('candidate/' + name)
        if _hash(payload.get('candidate/' + name, b'')) != wanted:
            raise KPPError('Bundle staged file pin mismatch')
    for case in cases:
        name = case['script']
        if name.startswith('.') or '/' in name or '\\' in name or not name.endswith('.py'):
            raise KPPError('Unsafe bundle test case name')
        expected_files.add('suite/' + name)
        if _hash(payload.get('suite/' + name, b'')) != case.get('sha256'):
            raise KPPError('Bundle test script pin mismatch')
    if set(payload) != expected_files:
        raise KPPError('Bundle contents do not match staged/test inventories')
    # No trust is transferred: historic absolute source paths remain mere notes.
    return recipe, stage


def export_bundle(workspace, candidate, suite, request, plan, approval, output):
    """Export a portable candidate and review record; NO accepted test report."""
    out = Path(output).absolute()
    if out.exists() or out.is_symlink():
        raise KPPError('Bundle output already exists (no overwrite)')
    recipe, state = load(workspace)
    candidate, suite = Path(candidate).resolve(), Path(suite).resolve()
    if out.resolve().is_relative_to(candidate) or out.resolve().is_relative_to(suite):
        raise KPPError('Bundle output cannot be inside source or suite')
    audit(candidate)
    stage = read_json(candidate / STAGE_MANIFEST)
    if stage.get('recipe_sha256') != state['recipe_hash']:
        raise KPPError('Candidate does not belong to current workspace recipe')
    tests = validated_suite(suite, recipe, stage)
    payload = {}
    payload['candidate/' + STAGE_MANIFEST] = _read_file(candidate / STAGE_MANIFEST)
    for name in stage['files']:
        payload['candidate/' + name] = _read_file(candidate / _relative_file(name))
    payload['suite/suite.json'] = _read_file(suite / 'suite.json')
    for case in tests['cases']:
        payload['suite/' + case['script']] = _read_file(suite / case['script'])
    inputs = {'review/recipe.json':Path(workspace) / 'recipe.json',
              'review/request.json':Path(request), 'review/plan.json':Path(plan),
              'review/approval.json':Path(approval)}
    for key, path in inputs.items():
        payload[key] = _read_file(path)
    _check_relationships(payload)
    if len(payload) > MAX_FILES or sum(map(len, payload.values())) > MAX_BYTES:
        raise KPPError('Bundle exceeds size/entry cap')
    inventory = {name:_hash(blob) for name, blob in sorted(payload.items())}
    manifest = {'schema':SCHEMA, 'transfer':'UNVERIFIED_STAGED_CANDIDATE',
                'recipe_id':recipe['id'], 'recipe_sha256':digest(recipe),
                'files':inventory, 'acceptance':'NOT_TRANSFERRED',
                'test_execution':'NOT_TRANSFERRED',
                'recovery':'Use extracted original source copies; do not alter or deploy original application',
                'warning':'Hash inventory is internal consistency, not an authenticity signature. Review source and tests before running.'}
    _write_archive(out,payload,manifest)
    return {'schema':SCHEMA, 'bundle':str(out), 'files':len(payload),
            'sha256':_hash(out.read_bytes()), 'execution':'NONE',
            'acceptance':'NOT_TRANSFERRED'}

def _write_archive(out,payload,manifest):
    if len(payload)>MAX_FILES or sum(map(len,payload.values()))>MAX_BYTES:
        raise KPPError('Bundle exceeds size/entry cap')
    blobs = {'bundle.json':(canonical(manifest)+'\n').encode('utf-8'), **payload}
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(out, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name, blob in sorted(blobs.items()):
                zi = zipfile.ZipInfo(name, (1980,1,1,0,0,0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = (0o100600 << 16)
                z.writestr(zi, blob)
    except Exception:
        out.unlink(missing_ok=True)
        raise
def _read_archive(path, schema=SCHEMA, relationships=_check_relationships):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise KPPError('Missing/unsafe reflex bundle')
    try:
        with zipfile.ZipFile(path) as z:
            entries = z.infolist()
            if not entries or len(entries) > MAX_FILES+1:
                raise KPPError('Invalid bundle entry count')
            payload = {}
            total = 0
            for item in entries:
                name = _safe_name(item.filename)
                typ = (item.external_attr >> 16) & 0o170000
                if name in payload or item.is_dir() or typ not in (0, 0o100000):
                    raise KPPError('Duplicate, symlink or nonregular archive member')
                if item.file_size > MAX_BYTES or total + item.file_size > MAX_BYTES:
                    raise KPPError('Bundle uncompressed size limit exceeded')
                data = z.read(item)
                total += len(data)
                payload[name] = data
    except (zipfile.BadZipFile, RuntimeError, EOFError, OSError) as exc:
        raise KPPError('Unreadable reflex bundle') from exc
    if 'bundle.json' not in payload:
        raise KPPError('Bundle is missing its inventory')
    manifest = _json(payload.pop('bundle.json'), 'bundle.json')
    inventory = manifest.get('files')
    if manifest.get('schema') != schema or not isinstance(inventory, dict) or \
       set(payload) != set(inventory) or \
       any(not isinstance(wanted, str) or len(wanted) != 64 or
           _hash(data) != wanted for name, data in payload.items()
           for wanted in [inventory[name]]):
        raise KPPError('Bundle inventory or hash mismatch')
    recipe, stage = relationships(payload)
    if manifest.get('recipe_id') != recipe['id'] or manifest.get('recipe_sha256') != digest(recipe):
        raise KPPError('Bundle metadata recipe mismatch')
    return manifest, payload

PREVIEW_SCHEMA='kpp.preview-bundle/1'

def _preview_relationships(payload):
    for name in ('recipe.json','state.json','ingredient-labels.json','history.jsonl'):
        if name not in payload:raise KPPError('Preview bundle missing '+name)
    recipe=validate_recipe(_json(payload['recipe.json'],'recipe'))
    state=_json(payload['state.json'],'workspace')
    if recipe['delivery_mode']!='progressive-web' or state.get('schema')!='kpp.workspace/3' or state.get('recipe_hash')!=digest(recipe):
        raise KPPError('Preview bundle recipe/workspace mismatch')
    if state.get('accepted')!={} or state.get('phase')!='BUILDING':
        raise KPPError('Preview recovery must not transfer acceptance')
    labels=_json(payload['ingredient-labels.json'],'labels')
    if digest(labels)!=state.get('ingredient_labels_hash') or labels.get('recipe_hash')!=digest(recipe):
        raise KPPError('Preview ingredient labels changed')
    expected={'recipe.json','state.json','ingredient-labels.json','history.jsonl','app/runtime.js'}
    if not supported_runtime(payload.get('app/runtime.js',b''), state.get('runtime_sha256')):
        raise KPPError('Unsupported carried preview runtime')
    for name,pin in recipe['preview']['assets'].items():
        expected.add('app/'+name)
        if _hash(payload.get('app/'+name,b''))!=pin['sha256']:raise KPPError('Carried preview seed differs from recipe')
    modules=state.get('modules')
    if not isinstance(modules,list) or len(modules)>256 or any(not isinstance(m,dict) for m in modules):
        raise KPPError('Invalid carried modules')
    for mod in modules:
        if not isinstance(mod.get('id'),str) or not isinstance(mod.get('sha256'),str):raise KPPError('Invalid carried module identity')
        for name,pin in revision_sources(mod).items():
            _safe_name(name);expected.add(name)
            if _hash(payload.get(name,b''))!=pin:raise KPPError('Carried module source changed')
    if state.get('initial_body_sha256'):
        expected.add('app/body-state.json')
        data=payload.get('app/body-state.json',b'')
        if _hash(data)!=state['initial_body_sha256']:raise KPPError('Carried Body state changed')
        initial=_json(data,'Body state')
        if initial.get('schema')!='kpp.browser-state/1' or initial.get('profile')!='json-body/1' or not isinstance(initial.get('body'),dict):
            raise KPPError('Unsupported carried Body state')
    for reference in state.get('gui_evidence',[]):
        name=reference['path'];_safe_name(name)
        if not name.startswith('artifacts/gui/'):raise KPPError('Invalid carried GUI artifact path')
        expected.add(name);data=payload.get(name,b'')
        if _hash(data)!=reference['sha256']:raise KPPError('Carried GUI evidence changed')
        record=_json(data,'GUI evidence')
        if digest(record)!=reference['id'] or record.get('schema') not in ('kpp.gui-observation/1','kpp.gui-comparison/1'):
            raise KPPError('Unsupported carried GUI evidence')
        for key in ('capture','difference'):
            if key in record:
                item=record[key];name=item['path'];_safe_name(name)
                if not name.startswith('artifacts/gui/'):raise KPPError('Invalid carried GUI capture path')
                expected.add(name)
                if _hash(payload.get(name,b''))!=item['sha256']:raise KPPError('Carried GUI capture changed')
    if set(payload)!=expected:raise KPPError('Unexpected preview bundle files')
    return recipe,state

@mutating
def export_preview(workspace,output,browser_state=None):
    """Carry exact reviewed preview sources and optional source-bound user data."""
    out=Path(output).absolute();workspace=Path(workspace).resolve()
    if out.exists() or out.is_symlink() or out.resolve().is_relative_to(workspace):
        raise KPPError('Preview bundle must be new and outside workspace')
    recipe,state=load(workspace)
    if state['preview_kind']!='progressive-web':raise KPPError('No progressive preview to export')
    payload={name:_read_file(workspace/name) for name in ('recipe.json','ingredient-labels.json','history.jsonl')}
    for name in (*recipe['preview']['assets'],'runtime.js'):
        payload['app/'+name]=_read_file(workspace/'app'/name)
    for mod in state['modules']:
        for name in revision_sources(mod):
            payload[name]=_read_file(workspace/name)
    if state['gui_evidence']:
        from .conformance import read_evidence, _artifact
        for reference in state['gui_evidence']:
            record=read_evidence(workspace,reference['id'],require_current=False)
            payload[reference['path']]=_read_file(_artifact(workspace,reference['path']))
            for key in ('capture','difference'):
                if key in record:
                    name=record[key]['path'];payload[name]=_read_file(_artifact(workspace,name))
    if browser_state is not None:
        data=_read_file(Path(browser_state));initial=_json(data,'browser checkpoint')
        if initial.get('schema')!='kpp.browser-state/1' or initial.get('profile')!=recipe['preview']['state_profile'] or not isinstance(initial.get('body'),dict):
            raise KPPError('Invalid browser state checkpoint')
        if initial.get('recipe_sha256')!=digest(recipe) or initial.get('fingerprint')!=preview_fingerprint(recipe,state):
            raise KPPError('Browser checkpoint source pin is stale')
        payload['app/body-state.json']=data;state['initial_body_sha256']=_hash(data)
    elif state.get('initial_body_sha256'):
        payload['app/body-state.json']=_read_file(workspace/'app/body-state.json')
    state['accepted']={};state['phase']='BUILDING';state['revision']=1
    payload['state.json']=(canonical(state)+'\n').encode('utf-8')
    _preview_relationships(payload)
    manifest={'schema':PREVIEW_SCHEMA,'recipe_id':recipe['id'],'recipe_sha256':digest(recipe),
              'files':{name:_hash(data) for name,data in sorted(payload.items())},
              'acceptance':'NOT_TRANSFERRED','execution':'NONE',
              'scope':'Exact current preview sources and explicit Body checkpoint; not deployment or code approval'}
    _write_archive(out,payload,manifest)
    return {'schema':PREVIEW_SCHEMA,'bundle':str(out),'sha256':_hash(out.read_bytes()),
            'body_state_included':'app/body-state.json' in payload,'acceptance':'NOT_TRANSFERRED','execution':'NONE'}

def import_preview(bundle,output):
    out=Path(output).absolute()
    if out.exists() or out.is_symlink() or not out.parent.is_dir():raise KPPError('Preview recovery requires unused output and existing parent')
    manifest,payload=_read_archive(bundle,PREVIEW_SCHEMA,_preview_relationships)
    if manifest.get('acceptance')!='NOT_TRANSFERRED':raise KPPError('Bundle cannot grant acceptance')
    with tempfile.TemporaryDirectory(prefix='.kpp-preview-',dir=out.parent) as temporary:
        root=Path(temporary)/'workspace';root.mkdir()
        for name,data in payload.items():
            path=root.joinpath(*_safe_name(name).split('/'));path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        (root/'artifacts').mkdir(exist_ok=True)
        state=read_json(root/'state.json');state['workspace_id']=uuid.uuid4().hex;write_json(root/'state.json',state)
        load(root)
        log(root,'PREVIEW_RESTORED',{'bundle_sha256':_hash(Path(bundle).read_bytes()),'acceptance':'NOT_TRANSFERRED','execution':'NONE'})
        os.rename(root,out)
    return {'schema':'kpp.preview-recovery/1','workspace':str(out),'integrity':'PASS','execution':'NONE','acceptance':'NOT_TRANSFERRED'}


def import_bundle(bundle, output):
    """Fail-closed archive recovery to a NEW directory; never run source/test code."""
    out = Path(output).absolute()
    if out.exists() or out.is_symlink() or not out.parent.is_dir():
        raise KPPError('Recovery destination must be unused and parent must exist')
    manifest, payload = _read_archive(bundle)
    # Stage into same-volume private temp dir and validate as a real candidate.
    with tempfile.TemporaryDirectory(prefix='.kpp-recover-', dir=out.parent) as tmp:
        root = Path(tmp) / 'transfer'
        root.mkdir()
        for name, data in payload.items():
            path = root.joinpath(*_safe_name(name).split('/'))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        write_json(root / 'bundle.json', manifest)
        recipe = validate_recipe(read_json(root / 'review' / 'recipe.json'))
        audit(root / 'candidate')
        validated_suite(root / 'suite', recipe, read_json(root / 'candidate' / STAGE_MANIFEST))
        # Restore is not a Baker decision and does not recreate accepted state.
        (root / 'RECOVERY.md').write_text(
            '# Recovered KPP Reflex Candidate\n\n'
            'This is a staged copy, **not deployed or accepted**. The original app was never changed by staging.\n'
            'To roll back a proposed integration, use the unchanged original application instead of this candidate.\n'
            'The bundled candidate contains exact original source copies plus kpp_reflex_adapter.py; inspect them.\n\n'
            'For fresh verification in a KPP checkout with the same Pantry ingredients:\n\n'
            '```sh\n'
            'kpp new --recipe review/recipe.json --workspace /path/to/fresh-workspace\n'
            'kpp test --execute --reviewed --workspace /path/to/fresh-workspace --candidate candidate --suite suite --out /path/to/fresh-report.json\n'
            'kpp test-check --report /path/to/fresh-report.json --candidate candidate --suite suite\n'
            'kpp test-accept --workspace /path/to/fresh-workspace --report /path/to/fresh-report.json --candidate candidate --suite suite --baker YOUR_REVIEWED_ID\n'
            '```\n'
            'Running tests executes Python; only run reviewed scripts permitted on this host.\n'
            'Prior approval is historical staging context only; no acceptance travels with this bundle.\n'
            'Absolute source-root paths in the historic stage/plan are not portable and must not be treated as active source authority.\n', encoding='utf-8')
        os.rename(root, out)
    return {'schema':'kpp.reflex-recovery/1','output':str(out),
            'candidate':str(out/'candidate'),'suite':str(out/'suite'),
            'files':len(payload), 'integrity':'PASS',
            'execution':'NONE', 'acceptance':'NOT_TRANSFERRED',
            'next':'Review source and fixtures; create fresh workspace, execute Anchors only with authorization.'}


def review_candidate(candidate, source):
    """Read-only comparison to pinned originals, with reviewable additive diff.

    Independent source path may differ from its historic staging location, but
    its *bytes* must match exactly. No patch/rollback is applied by this command.
    """
    from .reflex import ADAPTER
    candidate, source = Path(candidate).resolve(), Path(source).resolve()
    if candidate == source or candidate in source.parents or source in candidate.parents:
        raise KPPError('Original source and candidate must be separate trees')
    audit(candidate)
    manifest = read_json(candidate / STAGE_MANIFEST)
    original = {name:sha for name,sha in manifest['files'].items() if name != ADAPTER}
    import time
    from ..scan.discovery import snapshot, _directory
    source_observed = snapshot(_directory(source), deadline=time.monotonic() + 30,
                               max_files=100, max_bytes=16_000_000, max_file_bytes=1_000_000)
    if source_observed != original:
        raise KPPError('Source differs from the approved stage baseline; diff/rollback assurance unavailable')
    try:
        addition = (candidate / ADAPTER).read_text(encoding='utf-8').splitlines(keepends=True)
    except UnicodeDecodeError as exc:
        raise KPPError('Adapter text is not UTF-8') from exc
    patch = ''.join(difflib.unified_diff([], addition,fromfile='/dev/null',tofile=ADAPTER))
    return {'schema':'kpp.reflex-review/1','status':'ADDITIVE_CANDIDATE',
            'original_source':str(source),'original_files_unchanged':len(original),
            'added_file':ADAPTER,'unified_diff':patch,
            'rollback':'Continue using original source; original application was not changed by staging. No deployment performed.',
            'evidence':'File byte comparison only; no behavioral equivalence or authenticity proof'}
