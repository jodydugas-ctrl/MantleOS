"""Guarded, opt-in Python reflex staging. Never import inspected source at stage time.

This is a bounded adapter path, not a general AST rewriter or executed Anchor engine.
"""
import ast
import hashlib
import keyword
import shutil
from pathlib import Path

from .core import KPPError, digest, read_json, write_json
from .scanner import scan
from .workshop import load

APPROVAL_SCHEMA = 'kpp.reflex-approval/1'
STAGE_SCHEMA = 'kpp.reflex-stage/1'
ADAPTER = 'kpp_reflex_adapter.py'
STAGE_MANIFEST = 'kpp-reflex-stage.json'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _relative_file(path):
    if not isinstance(path, str) or not path or '\\' in path or path.startswith('/'):
        raise KPPError('Unsafe staged source path')
    p = Path(path)
    if p.is_absolute() or any(part in ('', '.', '..') for part in path.split('/')):
        raise KPPError('Unsafe staged source path')
    return p


def _safe_identifier(s):
    return isinstance(s, str) and s.isidentifier() and not keyword.iskeyword(s) and not s.startswith('__')


def _stage_template(module, function):
    # Identifiers are AST-validated before interpolation. Adapter cannot evaluate
    # text from either the request or the proposal except those identifiers.
    return (f'''"""KPP staged after-success reflex. Original body is copied without edits.

Generated adapter, not an assertion that application Anchors have been verified.
Contract: optional organ.on_success(result, *args, **kwargs); failure-isolated.
"""
from {module} import {function} as _kpp_original


def run_with_reflex(*args, organ=None, **kwargs):
    result = _kpp_original(*args, **kwargs)
    if organ is not None and isinstance(result, dict) and result.get("ok") is True:
        try:
            callback = getattr(organ, "on_success", None)
            if callable(callback):
                # Isolate modifications to the result payload where possible;
                # arbitrary side effects on passed objects cannot be proven safe.
                from copy import deepcopy
                callback(deepcopy(result), *args, **kwargs)
        except Exception:
            # Optional observer failures do not alter the successful result.
            # Applications needing diagnostics should supply a logging organ.
            pass
    return result
''').encode('utf-8')


def _selected_function(data, name, line):
    try:
        tree = ast.parse(data.decode('utf-8'))
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise KPPError('Cannot parse selected Python module') from exc
    # Only a single undecorated module-level sync function is supported.
    matches = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name and n.lineno == line]
    if len(matches) != 1:
        raise KPPError('Selected trigger is not a top-level synchronous function')
    node = matches[0]
    if node.decorator_list or any(isinstance(n, (ast.Yield, ast.YieldFrom, ast.Await)) for n in ast.walk(node)):
        raise KPPError('Decorators, generators and async calls are unsupported in staged triggers')
    all_params = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if node.args.vararg: all_params.append(node.args.vararg)
    if node.args.kwarg: all_params.append(node.args.kwarg)
    if any(n.arg == 'organ' for n in all_params):
        raise KPPError('Original callable already accepts organ; adapter would shadow an argument')
    return node


def approval_template(plan):
    """Produce an unsigned, incomplete approval template. Never self-approve."""
    if not isinstance(plan, dict) or plan.get('schema') != 'kpp.reflex-plan/1' or \
            plan.get('decision') != 'PROPOSAL_REQUIRES_BAKER_REVIEW' or \
            not isinstance(plan.get('tentative_point'), dict):
        raise KPPError('No single proposed site for an approval template')
    point = plan['tentative_point']
    if not isinstance(point.get('source_node'), str) or not point.get('source_sha256'):
        raise KPPError('Unpinned proposal site cannot be approved')
    return {'schema':APPROVAL_SCHEMA, 'intent':'stage-adapter-only',
            'plan_sha256':digest(plan), 'candidate_source_node':point['source_node'],
            'source_sha256':point['source_sha256'], 'baker':'',
            'instruction':'Baker: inspect proposed site, source, risks and Anchors; enter your name in baker to authorize STAGING ONLY. Delete this instruction field if desired.'}


def stage(workspace, request, plan, approval, source_dir, output_dir, repo=None):
    """Stage a source-pinned candidate after explicit plan-specific human attestation.

    No output is written until all integrity/eligibility constraints pass. Does
    not execute target code, test Anchors, or imply Baker's final acceptance.
    """
    from .adaptation import _request
    _request(request)
    recipe, state = load(workspace)
    if not isinstance(plan, dict) or plan.get('schema') != 'kpp.reflex-plan/1':
        raise KPPError('Stage requires a saved kpp.reflex-plan/1 proposal')
    if plan.get('decision') != 'PROPOSAL_REQUIRES_BAKER_REVIEW' or not isinstance(plan.get('tentative_point'), dict):
        raise KPPError('No unambiguous candidate approved for staging')
    if plan.get('recipe_id') != recipe['id'] or plan.get('recipe_sha256') != state['recipe_hash']:
        raise KPPError('Proposal recipe/workspace pin is stale')
    if plan.get('request_sha256') != digest(request):
        raise KPPError('Adaptation request has changed since planning')
    if plan.get('timing') != 'after-success' or request['trigger']['timing'] != 'after-success':
        raise KPPError('Only after-success adapters are implemented')
    if plan.get('ingredient_id') != request.get('ingredient_id') or request['ingredient_id'] not in recipe['ingredients']:
        raise KPPError('Ingredient/recipe mismatch')
    if plan.get('required_anchor_ids') != request['anchors']:
        raise KPPError('Requested Anchor mapping changed')

    if not isinstance(approval, dict) or approval.get('schema') != APPROVAL_SCHEMA:
        raise KPPError('Missing explicit reflex staging approval')
    candidate = plan['tentative_point']
    if (approval.get('plan_sha256') != digest(plan) or
        approval.get('candidate_source_node') != candidate.get('source_node') or
        approval.get('source_sha256') != candidate.get('source_sha256') or
        approval.get('intent') != 'stage-adapter-only' or
        not isinstance(approval.get('baker'), str) or not approval['baker'].strip()):
        raise KPPError('Approval does not precisely authorize this proposal/site/source')
    if not candidate.get('source_sha256') or not isinstance(candidate.get('line'), int):
        raise KPPError('Selected candidate lacks file pin or line number')

    root = Path(source_dir).resolve()
    target = Path(output_dir).resolve()
    ws = Path(workspace).resolve()
    if not root.is_dir() or root != Path(plan.get('source_root', '')).resolve():
        raise KPPError('Proposal source root differs from approved source')
    # Reproduce the *actual* planner outcome: a caller cannot manufacture a
    # source node or decision in JSON and then self-consistently "approve" it.
    from .adaptation import reflex_plan
    # The caller selects the recipe/Pantry checkout, as with reflex-plan.
    from .core import find_repo_root
    fresh = reflex_plan(repo or find_repo_root(), recipe, state, request, root,
                        depth=plan.get('scan', {}).get('depth'))
    if digest(fresh) != digest(plan):
        raise KPPError('Saved proposal does not match freshly recomputed planner output')
    if target == root or root in target.parents or target in root.parents or target == ws or ws in target.parents:
        raise KPPError('Staged output must be a separate unused directory, outside source and workspace')
    if target.exists():
        raise KPPError('Stage destination must not exist (no overwrite)')
    depth = plan.get('scan', {}).get('depth')
    current = scan(root, depth=depth)
    native = current['native_report']['graph']
    if (not native['scope']['inventory_exhausted_within_exclusions'] or not current['files']
            or any(entry.get('sha256') is None or entry['status'] in ('ERROR', 'LIMIT') for entry in native['files'])):
        raise KPPError('Refusing incomplete source inventory for staged candidate')
    if digest(current['files']) != plan.get('source_inventory_sha256'):
        raise KPPError('Source inventory changed since proposal')
    if len(current['files']) > 100:
        raise KPPError('Staging supports at most 100 pinned source/data files')
    rel = _relative_file(candidate['file'])
    if len(rel.parts) != 1 or rel.suffix != '.py' or rel.stem == 'kpp_reflex_adapter':
        raise KPPError('Adapter currently supports a root-level Python module only')
    name = candidate['function']
    if not _safe_identifier(rel.stem) or not _safe_identifier(name):
        raise KPPError('Unsupported module/function name')
    # When a recipe declares functional Reflex edges they are authoritative
    # about the approved source→ingredient/timing/Anchor relationship.
    if recipe.get('reflexes') and not any(
            ref['source'] == rel.as_posix() + '::' + name and
            ref['ingredient'] == request['ingredient_id'] and
            ref['timing'] == 'after-success' and
            set(ref['anchors']) == set(request['anchors'].values())
            for ref in recipe['reflexes']):
        raise KPPError('Selected stage site does not match recipe Functional Graph Reflex connection')
    bypath = {f['path']: f for f in current['files']}
    if rel.as_posix() not in bypath or bypath[rel.as_posix()]['sha256'] != candidate['source_sha256']:
        raise KPPError('Candidate source file hash does not match inventory')
    # Trust no single signature from the prior static scanner: check actual AST.
    _selected_function((root / rel).read_bytes(), name, candidate['line'])
    if ADAPTER in bypath or STAGE_MANIFEST in bypath:
        raise KPPError('Source already contains reserved staging filename')
    if any(not _relative_file(f['path']).as_posix() == f['path'] for f in current['files']):
        raise KPPError('Invalid inventory path')
    source_bytes = {}
    for f in current['files']:
        p = root / _relative_file(f['path'])
        if p.is_symlink() or any(x.is_symlink() for x in p.parents if x != root and root in x.parents):
            raise KPPError('Symlink detected within candidate source')
        data = p.read_bytes()
        if _sha(data) != f['sha256']:
            raise KPPError('Source modified while staging')
        source_bytes[f['path']] = data
    adapter = _stage_template(rel.stem, name)
    stage_hashes = {**{k:_sha(v) for k,v in source_bytes.items()}, ADAPTER:_sha(adapter)}
    metadata = {
        'schema': STAGE_SCHEMA, 'status': 'STAGED_UNVERIFIED',
        'plan_sha256': digest(plan), 'approval_sha256': digest(approval),
        'recipe_id': recipe['id'], 'recipe_sha256': state['recipe_hash'],
        'request_sha256': digest(request), 'baker_approval_claim': approval['baker'],
        'selected_source_node': candidate['source_node'],
        'function': name, 'timing': 'after-success',
        'original_source_root': str(root),
        'source_inventory_sha256': digest(current['files']),
        'files': dict(sorted(stage_hashes.items())),
        'required_anchor_ids': request['anchors'],
        'anchor_execution': 'NOT_RUN', 'admission': 'NOT_AUTHORIZED',
        'note': 'Approval is a local operator attestation, not a digital signature. Run independent fixed-oracle and negative Anchor tests; Baker decides acceptance.'
    }
    # Keep the entire copied original body in the candidate; original source stays untouched.
    try:
        target.mkdir(parents=True, exist_ok=False)
        for filename, data in source_bytes.items():
            dest = target / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        (target / ADAPTER).write_bytes(adapter)
        write_json(target / STAGE_MANIFEST, metadata)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return {'schema':STAGE_SCHEMA, 'status':'STAGED_UNVERIFIED',
            'candidate':str(target), 'manifest':str(target/STAGE_MANIFEST),
            'files':len(stage_hashes), 'selected_source_node':candidate['source_node'],
            'execution':'NONE', 'anchor_verification':'NONE', 'acceptance':'NOT_GRANTED'}


def audit(candidate_dir):
    """Verify staged bytes against local manifest; no code execution or signature claim."""
    root = Path(candidate_dir).resolve()
    manifest = read_json(root / STAGE_MANIFEST)
    if not isinstance(manifest, dict) or manifest.get('schema') != STAGE_SCHEMA:
        raise KPPError('Not a KPP staged candidate')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise KPPError('Invalid candidate file inventory')
    paths = list(root.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise KPPError('Symlinks are not allowed in staged candidate')
    observed = {p.relative_to(root).as_posix() for p in paths if p.is_file()}
    expected = set(files) | {STAGE_MANIFEST}
    if observed != expected:
        raise KPPError('Staged file inventory differs: added or missing files')
    for name, wanted in files.items():
        rel = _relative_file(name)
        p = root / rel
        if p.is_symlink() or not p.is_file() or not isinstance(wanted, str) or _sha(p.read_bytes()) != wanted:
            raise KPPError('Staged hash mismatch: ' + name)
    return {'schema':'kpp.reflex-audit/1', 'integrity':'PASS',
            'checked_files':len(files), 'anchor_execution':'NOT_RUN',
            'admission':'NOT_AUTHORIZED', 'note':'Internal byte consistency, not authorship or behavioral equivalence'}
