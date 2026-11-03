"""Opt-in cumulative verification. Local reviewed scripts are NOT sandboxed.

Artifacts are integrity-bound workspace data, never model/operator authority.
Recipe obligations remain the only requirements and Baker acceptance is separate.
"""
import copy
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from .core import KPPError, digest, read_json, write_json
from .workshop import load, mutating, stamp, log

SUITE = 'kpp.satisfaction-suite/1'
REPORT = 'kpp.satisfaction-report/1'


def inventory(root):
    root = Path(root)
    if root.is_symlink() or getattr(root, 'is_junction', lambda: False)() or not root.is_dir():
        raise KPPError('Missing or unsafe source directory')
    result = {}
    total = 0
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise KPPError('Linked source is unsupported')
        if path.is_file():
            total += path.stat().st_size
            if total > 128 * 1024 * 1024 or len(result) >= 4096:
                raise KPPError('Verification inventory exceeds 4096 files / 128 MiB')
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not result:
        raise KPPError('Empty candidate/suite')
    return result


def verifier_pin():
    here = Path(__file__).parent
    return digest({**{n: hashlib.sha256((here.parent / n).read_bytes()).hexdigest() for n in ('anchors.py', 'anchor_design.py')}, **{n: hashlib.sha256((here / n).read_bytes()).hexdigest()
                   for n in ('satisfaction.py', 'core.py', 'graph.py', 'workshop.py', 'build.py', 'testing.py', 'construction.py')}})


def suite_spec(path, recipe):
    files = inventory(path)
    suite = read_json(Path(path) / 'suite.json')
    if suite.get('schema') != SUITE or suite.get('recipe_sha256') != digest(recipe):
        raise KPPError('Unsupported/stale satisfaction suite')
    cases = suite.get('cases')
    if not isinstance(cases, list) or not 1 <= len(cases) <= 256:
        raise KPPError('Suite needs 1..256 cases')
    known = {a['id'] for a in recipe['anchors']}
    ids = set()
    covered = set()
    for case in cases:
        if set(case) != {'id', 'obligations', 'script', 'relationship', 'requires'}:
            raise KPPError('Invalid satisfaction case fields')
        if not isinstance(case['id'], str) or not case['id'] or case['id'] in ids:
            raise KPPError('Duplicate/invalid case ID')
        ids.add(case['id'])
        refs = case['obligations']
        if not isinstance(refs, list) or not refs or any(x not in known for x in refs) or len(set(refs)) != len(refs):
            raise KPPError('Case must reference existing distinct obligations')
        covered.update(refs)
        name = case['script']
        if not isinstance(name, str) or Path(name).name != name or '/' in name or '\\' in name or not name.endswith('.py') or name not in files:
            raise KPPError('Case script must be a pinned root-level Python file')
        if not isinstance(case['relationship'], str) or not case['relationship'].strip():
            raise KPPError('Case needs declared relationship scope')
        if not isinstance(case['requires'], list) or any(not isinstance(x, str) for x in case['requires']):
            raise KPPError('Invalid case capability requirements')
    required = {a['id'] for a in recipe['anchors'] if a['required']}
    byid = {a['id']: a for a in recipe['anchors']}
    todo = list(required)
    while todo:
        for dep in byid[todo.pop()].get('depends', []):
            if dep not in required:
                required.add(dep); todo.append(dep)
    if required - covered:
        raise KPPError('Mandatory obligation has no verification case')
    return suite, files


def _store(workspace, value):
    key = digest(value)
    path = Path(workspace) / 'artifacts' / 'satisfaction' / (key + '.json')
    if path.is_symlink() or not path.resolve().is_relative_to(Path(workspace).resolve()):
        raise KPPError('Unsafe evidence path')
    if path.exists():
        if read_json(path) != value:
            raise KPPError('Changed retained evidence')
    else:
        write_json(path, value)
    return key


def _read(workspace, key):
    if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
        raise KPPError('Invalid evidence reference')
    path = Path(workspace) / 'artifacts' / 'satisfaction' / (key + '.json')
    if path.is_symlink() or not path.resolve().is_relative_to(Path(workspace).resolve()):
        raise KPPError('Unsafe evidence reference')
    value = read_json(path)
    if digest(value) != key:
        raise KPPError('Changed retained evidence')
    return value


@mutating
def start(workspace, candidate, suite, context, reviewed=False):
    if reviewed is not True:
        raise KPPError('Explicit suite/context review required')
    recipe, state = load(workspace)
    if state['phase'] != 'BUILDING' or 'satisfaction' in state:
        raise KPPError('Start requires a new BUILDING run; revised contracts need a new workspace')
    spec, files = suite_spec(suite, recipe)
    ctx = read_json(context)
    if not isinstance(ctx, dict) or not isinstance(ctx.get('capabilities'), dict):
        raise KPPError('Context needs explicit capability mapping')
    candidate = Path(candidate).resolve()
    if candidate == Path(suite).resolve() or candidate in Path(suite).resolve().parents or Path(suite).resolve() in candidate.parents:
        raise KPPError('Suite must be separate from candidate')
    if candidate == Path(workspace).resolve() or candidate in Path(workspace).resolve().parents or Path(workspace).resolve() in candidate.parents:
        raise KPPError('Candidate must be separate from workspace')
    run = {'schema': 'kpp.satisfaction-run/1', 'workspace_id': state['workspace_id'],
           'recipe_sha256': digest(recipe), 'suite_sha256': digest(files),
           'suite_root': str(Path(suite).resolve()), 'context_path': str(Path(context).resolve()),
           'context_sha256': digest(ctx), 'verifier_sha256': verifier_pin(),
           'baseline': inventory(candidate), 'candidate_root': str(candidate),
           'authority': 'NONE', 'at': stamp()}
    state['satisfaction'] = {'run': _store(workspace, run), 'reports': []}
    state['revision'] += 1
    write_json(Path(workspace) / 'state.json', state)
    log(workspace, 'SATISFACTION_STARTED', state['satisfaction'])
    return run


def _opened(workspace):
    recipe, state = load(workspace)
    ref = state.get('satisfaction')
    if not ref:
        raise KPPError('No satisfaction run; use satisfaction-start')
    run = _read(workspace, ref['run'])
    spec, files = suite_spec(run['suite_root'], recipe)
    if run['workspace_id'] != state['workspace_id'] or run['recipe_sha256'] != digest(recipe) or run['suite_sha256'] != digest(files) or run['verifier_sha256'] != verifier_pin() or run['context_sha256'] != digest(read_json(run['context_path'])):
        raise KPPError('Run contract, verifier, suite or context changed; review a new run')
    established = set()
    reports = []
    for key in ref['reports']:
        report = _read(workspace, key)
        if report['run'] != ref['run'] or report['prior'] != sorted(established):
            raise KPPError('Broken verification history')
        expected = [c['id'] for c in spec['cases'] if set(c['obligations']) & set(report['required_obligations'])]
        if [r['id'] for r in report['results']] != expected or (report['all_passed'] and (not report['candidate_integrity_after'] or any(r['outcome'] != 'PASS' for r in report['results']) or report['verified'] != report['required_obligations'])):
            raise KPPError('Malformed/omitted cumulative evidence')
        reports.append(report)
        if report['all_passed']:
            established.update(report['verified'])
    return recipe, state, run, spec, established, reports


def plan(workspace, batch_size=1):
    if type(batch_size) is not int or not 1 <= batch_size <= 32:
        raise KPPError('Batch size must be 1..32')
    recipe, state, run, spec, established, reports = _opened(workspace)
    from .graph import chase
    # Reuse scheduling without manufacturing acceptance records.
    order = chase(recipe, {**state, 'accepted': {}}, state.get('activity'))
    byid = {a['id']: a for a in recipe['anchors']}
    needed = {a['id'] for a in recipe['anchors'] if a['required']}
    todo = list(needed)
    while todo:
        for dep in byid[todo.pop()].get('depends', []):
            if dep not in needed:
                needed.add(dep); todo.append(dep)
    targets = [a['id'] for a in order if a['id'] in needed - established and
               set(byid[a['id']].get('depends', [])) <= established][:batch_size]
    protected = established | {a['id'] for a in recipe['anchors'] if a.get('preserves')}
    required = protected | set(targets)
    cases = [c for c in spec['cases'] if set(c['obligations']) & required]
    caps = read_json(run['context_path'])['capabilities']
    blockers = ['Unavailable capability: ' + cap for c in cases for cap in c['requires'] if caps.get(cap) is not True]
    current = inventory(run['candidate_root'])
    fresh = bool(reports and reports[-1]['all_passed'] and reports[-1]['candidate'] == current)
    if needed - established and not targets:
        blockers.append('No independently ready target')
    return {'schema': 'kpp.satisfaction-plan/1', 'run': state['satisfaction']['run'],
            'revision': state['revision'], 'targets': targets, 'prior': sorted(established),
            'required_obligations': sorted(required), 'required_cases': cases,
            'candidate': current, 'fidelity': recipe['fidelity'],
            'design_applications': sorted({x for aid in targets for x in byid[aid].get('design_anchors', [])}),
            'status': 'BLOCKED' if blockers else 'VERIFIED' if fresh and not needed - established else 'STALE' if established and not fresh else 'PENDING',
            'blockers': sorted(set(blockers)), 'acceptance': 'PENDING_BAKER', 'authority': 'NONE'}


@mutating
def test(workspace, execute=False, reviewed=False, batch_size=1, timeout=15):
    if execute is not True or reviewed is not True or type(timeout) is not int or not 1 <= timeout <= 60:
        raise KPPError('Use --execute --reviewed and timeout 1..60; local scripts are not sandboxed')
    packet = plan(workspace, batch_size)
    if packet['blockers']:
        raise KPPError('; '.join(packet['blockers']))
    recipe, state, run, spec, established, reports = _opened(workspace)
    if state['phase'] != 'BUILDING':
        raise KPPError('Verification requires BUILDING state')
    results = []
    for case in packet['required_cases']:
        try:
            done = subprocess.run([sys.executable, '-I', '-B', str(Path(run['suite_root']) / case['script']), run['candidate_root']],
                                  cwd=run['suite_root'], capture_output=True, timeout=timeout)
            outcome = 'PASS' if done.returncode == 0 else 'FAIL'
            output = (done.stdout + done.stderr)[-2048:].decode('utf-8', 'replace')
        except subprocess.TimeoutExpired:
            outcome, output = 'TIMEOUT', ''
        results.append({'id': case['id'], 'outcome': outcome, 'output': output})
    # Reopen all contracts and candidate after execution, under the workspace writer lock.
    _opened(workspace)
    if load(workspace)[1] != state:
        raise KPPError('Workspace changed during verification')
    after = inventory(run['candidate_root'])
    passed = bool(results) and all(r['outcome'] == 'PASS' for r in results) and after == packet['candidate']
    report = {**packet, 'schema': REPORT, 'workspace': str(Path(workspace).resolve()),
              'recipe_sha256': digest(recipe), 'results': results, 'all_passed': passed, 'status': 'VERIFIED' if passed else 'FAILED',
              'verified': sorted(set(packet['required_obligations'])) if passed else [],
              'candidate_integrity_after': after == packet['candidate'], 'at': stamp(),
              'execution': 'EXPLICIT_REVIEWED_LOCAL_PYTHON',
              'limitations': 'Integrity is not authentication. Reviewed scripts have arbitrary local effects; no sandbox. Only declared cases are checked.'}
    key = _store(workspace, report)
    if passed:
        destination = Path(workspace) / 'artifacts' / 'satisfaction' / ('candidate-' + digest(after))
        if not destination.exists():
            shutil.copytree(run['candidate_root'], destination)
        if inventory(destination) != after:
            raise KPPError('Candidate snapshot changed during capture')
    state['satisfaction']['reports'].append(key)
    state['revision'] += 1
    write_json(Path(workspace) / 'state.json', state)
    log(workspace, 'SATISFACTION_TESTED', {'report': key, 'all_passed': passed})
    return {**report, 'report_path': str(Path(workspace).resolve() / 'artifacts' / 'satisfaction' / (key + '.json'))}


def check(workspace, report=None):
    recipe, state, run, spec, established, reports = _opened(workspace)
    if not reports:
        raise KPPError('No executed evidence')
    current = reports[-1]
    if report is not None and report != current:
        raise KPPError('Report is not the latest retained execution')
    if not current['all_passed'] or current['candidate'] != inventory(run['candidate_root']):
        raise KPPError('Failed/stale execution evidence')
    return {'fresh': True, 'anchors': current['verified'], 'report': current,
            'candidate_manifest_sha256': digest(current['candidate']),
            'suite_manifest_sha256': run['suite_sha256']}


def completion_guard(workspace):
    recipe, state = load(workspace)
    if 'satisfaction' in state:
        verified = set(check(workspace)['anchors'])
        if any(a['required'] and a['id'] not in verified for a in recipe['anchors']):
            raise KPPError('Cumulative verification does not cover all mandatory obligations')


def accept_report(workspace, report_path, baker):
    """Called under testing.accept_tested's existing writer lock."""
    report = read_json(report_path)
    result = check(workspace, report)
    recipe, state = load(workspace)
    for aid in result['anchors']:
        anchor = next(a for a in recipe['anchors'] if a['id'] == aid)
        state['accepted'][aid] = {'anchor_id': aid, 'statement': anchor['statement'],
            'test': anchor['test'], 'kind': 'satisfaction-executed', 'baker': baker,
            'evidence': 'Current cumulative reviewed local checks', 'at': stamp(),
            'recipe_hash': state['recipe_hash'], 'revision': state['revision'],
            'report_path': str(Path(report_path).resolve()), 'report_sha256': digest(report)}
    state['revision'] += 1
    write_json(Path(workspace) / 'state.json', state)
    log(workspace, 'SATISFACTION_BAKER_ACCEPTED', {'anchors': result['anchors'], 'baker': baker})
    return {'accepted_anchors': result['anchors'], 'acceptance': 'BAKER_ATTESTED'}
