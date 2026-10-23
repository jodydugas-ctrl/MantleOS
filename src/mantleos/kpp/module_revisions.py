"""Reviewed source selection using the existing workspace lock and history."""
import hashlib
import re
from pathlib import Path

from .core import KPPError, SLUG, digest, read_json, write_json

HEX = re.compile(r'^[a-f0-9]{64}$')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_path(module):
    """Derive paths from checked identities, never an imported path field."""
    mid = module.get('id')
    if not isinstance(mid, str) or not SLUG.fullmatch(mid):
        raise KPPError('Invalid revision module identity')
    pin = module.get('sha256')
    if not isinstance(pin, str) or not HEX.fullmatch(pin):
        raise KPPError('Invalid module source pin')
    if 'revisions' in module:
        return f'app/module-revisions/{mid}/{pin}.js'
    return f'app/modules/{mid}.js'


def revision_sources(module):
    source_path(module)
    revisions = module.get('revisions')
    if revisions is None:
        return {source_path(module): module['sha256']}
    if (not isinstance(revisions, list) or not 2 <= len(revisions) <= 128
            or type(module.get('generation')) is not int or module['generation'] < 1):
        raise KPPError('Invalid module revision history')
    pins = set()
    result = {}
    for revision in revisions:
        if (not isinstance(revision, dict) or set(revision) != {'sha256', 'bytes'}
                or not isinstance(revision['sha256'], str) or not HEX.fullmatch(revision['sha256'])
                or revision['sha256'] in pins or type(revision['bytes']) is not int
                or not 0 < revision['bytes'] <= 512000):
            raise KPPError('Invalid or duplicate retained revision')
        pin = revision['sha256']; pins.add(pin)
        result[f"app/module-revisions/{module['id']}/{pin}.js"] = pin
    if module['sha256'] not in pins or module.get('previous_sha256') not in pins:
        raise KPPError('Selected/predecessor revision is not retained')
    if module.get('bytes') != next(r['bytes'] for r in revisions if r['sha256'] == module['sha256']):
        raise KPPError('Selected revision byte count mismatch')
    result[f"app/modules/{module['id']}.js"] = revisions[0]['sha256']
    return result


def validate_sources(workspace, module):
    root = Path(workspace).resolve()
    for relative, pin in revision_sources(module).items():
        path = root / relative
        if (any(p.is_symlink() for p in (path, *path.parents) if p != root.parent)
                or not path.is_file() or not path.resolve().is_relative_to(root)):
            raise KPPError('Missing/unsafe retained module source: ' + relative)
        with path.open('rb') as stream:
            blob = stream.read(512001)
        if len(blob) > 512000 or sha(blob) != pin:
            raise KPPError('Missing/modified installed module or retained source: ' + module['id'])


def _immutable(workspace, relative, content):
    path = Path(workspace) / relative
    if not path.resolve().is_relative_to(Path(workspace).resolve()) or any(p.is_symlink() for p in (path, *path.parents)):
        raise KPPError('Unsafe revision source path')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as stream:
            stream.write(content)
            stream.flush()
            import os
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != content:
            raise KPPError('Immutable revision collision')


def select_candidate(workspace, module, content):
    """Prepare immutable source; caller owns workspace lock and state publication.

    Also used in an explicitly reviewed disposable browser-test workspace.
    Preparing bytes does not publish a source selection.
    """
    pin = sha(content)
    if not content or len(content) > 512000 or pin == module['sha256']:
        raise KPPError('Candidate must be changed, nonempty and under 512KB')
    if 'revisions' not in module:
        original = (Path(workspace) / source_path(module)).read_bytes()
        if sha(original) != module['sha256']:
            raise KPPError('Baseline source changed')
        module['revisions'] = [{'sha256': module['sha256'], 'bytes': len(original)}]
        _immutable(workspace, f"app/module-revisions/{module['id']}/{module['sha256']}.js", original)
    if pin not in {r['sha256'] for r in module['revisions']}:
        if len(module['revisions']) >= 128:
            raise KPPError('Retained revision budget reached')
        module['revisions'].append({'sha256': pin, 'bytes': len(content)})
    _immutable(workspace, f"app/module-revisions/{module['id']}/{pin}.js", content)
    module['previous_sha256'] = module['sha256']
    module['sha256'], module['bytes'] = pin, len(content)
    module['generation'] = module.get('generation', 0) + 1


def _context(workspace, module_id, expected_revision, reviewed):
    from .workshop import load, asset
    recipe, state = load(workspace)
    if reviewed is not True:
        raise KPPError('Module source selection requires explicit --reviewed')
    if type(expected_revision) is not int or state['revision'] != expected_revision:
        raise KPPError('Stale workspace revision')
    if state.get('runtime_sha256') != sha(asset('progressive.js')):
        raise KPPError('Replacement requires the current runtime in a new workspace; no implicit runtime upgrade')
    module = next((m for m in state['modules'] if m['id'] == module_id), None)
    if module is None or not module['enabled']:
        raise KPPError('An enabled installed module is required')
    return recipe, state, module


def _publish(workspace, state, module, operation, detail):
    from .workshop import log
    if state['accepted']:
        log(workspace, 'ACCEPTANCE_INVALIDATED', {'reason': operation, 'records': state['accepted']})
    state['accepted'] = {}
    state['phase'] = 'BUILDING'
    state['revision'] += 1
    event = {'id': module['id'], 'revision': state['revision'], 'sha256': module['sha256'],
             'previous_sha256': module['previous_sha256'], **detail}
    log(workspace, operation + '_PREPARED', event)
    write_json(Path(workspace) / 'state.json', state)
    log(workspace, operation, event)
    return state


def replace_module(workspace, module_id, source, evidence, *, expected_revision, reviewed=False):
    from .workshop import workspace_lock
    from .organ_testing import verify_module_evidence
    with workspace_lock(workspace):
        recipe, state, module = _context(workspace, module_id, expected_revision, reviewed)
        report = read_json(evidence)
        verify_module_evidence(report, workspace, module_id, source)
        candidate = Path(source).read_bytes()
        if sha(candidate) != report['candidate_sha256']:
            raise KPPError('Candidate changed after evidence verification')
        select_candidate(workspace, module, candidate)
        return _publish(workspace, state, module, 'MODULE_REPLACED', {'evidence_sha256': digest(report)})


def restore_module(workspace, module_id, *, expected_revision, reviewed=False):
    from .workshop import workspace_lock
    with workspace_lock(workspace):
        recipe, state, module = _context(workspace, module_id, expected_revision, reviewed)
        if 'revisions' not in module:
            raise KPPError('No predecessor revision to restore')
        previous = module['previous_sha256']
        module['previous_sha256'] = module['sha256']
        module['sha256'] = previous
        module['bytes'] = next(r['bytes'] for r in module['revisions'] if r['sha256'] == previous)
        module['generation'] += 1
        return _publish(workspace, state, module, 'MODULE_RESTORED', {})
