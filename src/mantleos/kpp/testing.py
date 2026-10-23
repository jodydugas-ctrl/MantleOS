"""Source-bound, explicitly authorized local Python checks; no execution sandbox."""
import hashlib
import subprocess
import sys
from pathlib import Path

from .core import KPPError, digest, read_json, write_json
from .reflex import STAGE_MANIFEST, audit
from .workshop import load, log, stamp, mutating

SCHEMA = 'kpp.reflex-tests/1'
REPORT = 'kpp.reflex-test-report/2'
HEX64 = set('0123456789abcdef')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _test_path(root, name):
    if not isinstance(name, str) or not name.endswith('.py') or '/' in name or '\\' in name or name.startswith('.'):
        raise KPPError('Tests must be root-level named Python files')
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise KPPError('Missing/unsafe pinned test: ' + name)
    return path


def validated_suite(suite_dir, recipe, stage):
    root = Path(suite_dir).resolve()
    if not root.is_dir():
        raise KPPError('Test suite directory does not exist')
    if (root / 'suite.json').is_symlink():
        raise KPPError('Suite manifest symlink not permitted')
    suite = read_json(root / 'suite.json')
    if not isinstance(suite, dict) or suite.get('schema') != SCHEMA:
        raise KPPError('Unsupported executed Anchor suite')
    if suite.get('recipe_id') != recipe['id'] or suite.get('recipe_sha256') != digest(recipe):
        raise KPPError('Test suite recipe pin is stale')
    cases = suite.get('cases')
    if not isinstance(cases, list) or not cases or len(cases) > 32:
        raise KPPError('Suite needs 1..32 Anchor checks')
    bound = stage.get('required_anchor_ids')
    if not isinstance(bound, dict) or set(bound) != {'original', 'reflex', 'optional_absent'} or not all(isinstance(v,str) for v in bound.values()):
        raise KPPError('Staged candidate missing mapped required Anchors')
    requested = set(bound.values())
    required = {a['id'] for a in recipe['anchors'] if a['required']}
    ids = set()
    paths = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'anchor', 'script', 'sha256'}:
            raise KPPError('Invalid test case definition')
        aid, filename, pinned = case['anchor'], case['script'], case['sha256']
        if not isinstance(aid, str) or aid not in required or aid in ids:
            raise KPPError('Invalid/duplicate required Anchor in suite')
        if filename in paths:
            raise KPPError('Same test file cannot be reused for multiple Anchors')
        if not isinstance(pinned, str) or len(pinned) != 64 or not set(pinned) <= HEX64:
            raise KPPError('Invalid test hash')
        path = _test_path(root, filename)
        if sha_bytes(path.read_bytes()) != pinned:
            raise KPPError('Pinned test source changed: ' + filename)
        ids.add(aid)
        paths.add(filename)
    if ids != requested:
        raise KPPError('Test suite does not cover exactly the staged reflex Anchors')
    # No extra test files or symlinks that might act as shadow imports.
    observed = {p.name for p in root.iterdir()}
    if observed != paths | {'suite.json'}:
        raise KPPError('Test suite directory has unpinned files')
    return suite


def verify_report(report, candidate_dir, suite_dir, recipe=None):
    """Recheck freshness; does not re-execute or authenticate evidence."""
    try:
        root, tests = Path(candidate_dir).resolve(), Path(suite_dir).resolve()
        if not isinstance(report, dict) or report.get('schema') != REPORT:
            raise KPPError('Invalid execution report')
        if root != Path(report['candidate_root']).resolve() or tests != Path(report['suite_root']).resolve():
            raise KPPError('Report paths differ from candidate/suite')
        audit(root)
        stage = read_json(root / STAGE_MANIFEST)
        if digest(stage) != report.get('candidate_manifest_sha256'):
            raise KPPError('Candidate manifest has changed')
        if recipe is None:
            recipe = read_json(report['workspace_recipe_path'])
        if digest(recipe) != report.get('recipe_sha256'):
            raise KPPError('Recipe pin in report is stale')
        suite = validated_suite(tests, recipe, stage)
        if digest(suite) != report.get('suite_manifest_sha256'):
            raise KPPError('Suite has changed')
        if stage.get('recipe_sha256') != digest(recipe):
            raise KPPError('Candidate recipe pin differs')
        cases = report.get('results')
        if not isinstance(cases, list) or len(cases) != len(suite['cases']) or any(
                not isinstance(x, dict) or x.get('anchor') != spec['anchor'] or
                x.get('script_sha256') != spec['sha256'] or
                x.get('returncode') != 0 for x, spec in zip(cases, suite['cases'])):
            raise KPPError('Executed results differ from pinned suite definition')
        if report.get('execution') != 'EXPLICIT_REVIEWED_LOCAL_PYTHON':
            raise KPPError('Unsupported execution report')
        if report.get('all_passed') is not True or any(c.get('outcome') != 'PASS' for c in cases):
            raise KPPError('Executed Anchor suite has failures')
        if report.get('candidate_integrity_after') != 'PASS':
            raise KPPError('Test run changed candidate bytes')
        return {'fresh':True, 'anchors':[x['anchor'] for x in cases],
                'candidate_manifest_sha256':digest(stage), 'suite_manifest_sha256':digest(suite)}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, KPPError):
            raise
        raise KPPError('Cannot verify execution evidence: ' + str(exc)) from exc


def run_suite(workspace, candidate_dir, suite_dir, out, execute=False, timeout=15,
              reviewed=False):
    if not execute:
        raise KPPError('Running arbitrary test scripts requires explicit --execute and trusted suite review')
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise KPPError('Timeout must be between 1 and 60 seconds per check')
    if reviewed is not True:
        raise KPPError('Local test execution requires explicit --reviewed; scripts must be trusted')
    recipe, state = load(workspace)
    if state['phase'] != 'BUILDING':
        raise KPPError('Cannot run build verification after completion')
    root, tests = Path(candidate_dir).resolve(), Path(suite_dir).resolve()
    output = Path(out).resolve()
    if output.exists() or output == root or root in output.parents or output == tests or tests in output.parents:
        raise KPPError('Report must be new and outside candidate and suite directories')
    audit(root)
    stage = read_json(root / STAGE_MANIFEST)
    if stage.get('recipe_id') != recipe['id'] or stage.get('recipe_sha256') != state['recipe_hash']:
        raise KPPError('Candidate staged for a different recipe')
    suite = validated_suite(tests, recipe, stage)
    results = []
    for case in suite['cases']:
        script = _test_path(tests, case['script'])
        try:
            done = subprocess.run([sys.executable, '-I', '-B', str(script), str(root)],
                                  cwd=tests, capture_output=True, text=True,
                                  errors='replace', timeout=timeout,
                                  env={'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONIOENCODING':'utf-8'})
            outcome = 'PASS' if done.returncode == 0 else 'FAIL'
            stdout, stderr = done.stdout[-2048:], done.stderr[-2048:]
            code = done.returncode
        except subprocess.TimeoutExpired as exc:
            outcome, code = 'TIMEOUT', None
            stdout = (exc.stdout or b'').decode('utf-8', 'replace')[-2048:] if isinstance(exc.stdout, bytes) else (exc.stdout or '')[-2048:]
            stderr = (exc.stderr or b'').decode('utf-8', 'replace')[-2048:] if isinstance(exc.stderr, bytes) else (exc.stderr or '')[-2048:]
        results.append({'anchor':case['anchor'], 'script_sha256':case['sha256'],
                        'outcome':outcome, 'returncode':code, 'stdout_tail':stdout, 'stderr_tail':stderr})
    # A test script is untrusted code; detect changes but don't claim sandboxing.
    candidate_integrity = 'PASS'
    try:
        audit(root)
        if digest(read_json(root / STAGE_MANIFEST)) != digest(stage):
            raise KPPError('Staged metadata modified during test run')
        if digest(validated_suite(tests, recipe, stage)) != digest(suite):
            raise KPPError('Test suite metadata modified during test run')
    except (KPPError, OSError):
        candidate_integrity = 'FAILED_OR_CHANGED'
    report = {'schema':REPORT, 'at':stamp(), 'recipe_id':recipe['id'],
              'recipe_sha256':state['recipe_hash'],
              'workspace_recipe_path':str((Path(workspace)/'recipe.json').resolve()),
              'candidate_root':str(root), 'suite_root':str(tests),
              'candidate_manifest_sha256':digest(stage),
              'suite_manifest_sha256':digest(suite),
              'results':results, 'candidate_integrity_after':candidate_integrity,
              'all_passed':all(c['outcome']=='PASS' for c in results) and candidate_integrity=='PASS',
              'execution':'EXPLICIT_REVIEWED_LOCAL_PYTHON',
              'acceptance':'PENDING_BAKER',
              'limitations':'Reviewed local execution has no sandbox and may have arbitrary side effects. '
                            'PASS proves only specified fixtures against pinned local bytes; not arbitrary equivalence.'}
    write_json(output,report)
    return report


@mutating
def accept_tested(workspace, report_path, candidate_dir, suite_dir, baker):
    from .workshop import stamp
    if not isinstance(baker, str) or not baker.strip():
        raise KPPError('Explicit nonblank Baker identity/label required')
    recipe, state = load(workspace)
    if state['phase'] != 'BUILDING':
        raise KPPError('Cannot accept tests after completion')
    report = read_json(report_path)
    result = verify_report(report, candidate_dir, suite_dir, recipe=recipe)
    if Path(report['workspace_recipe_path']).resolve() != (Path(workspace)/'recipe.json').resolve():
        raise KPPError('Report was produced for a different workspace')
    accepted = dict(state['accepted'])
    for case in report['results']:
        aid = case['anchor']
        anchor = next(a for a in recipe['anchors'] if a['id'] == aid)
        accepted[aid] = {'anchor_id':aid, 'statement':anchor['statement'],
                         'test':anchor['test'], 'kind':'executed', 'baker':baker.strip(),
                         'evidence':'Executed source-pinned Python fixture: '+case['outcome'],
                         'at':stamp(), 'recipe_hash':state['recipe_hash'],
                         'revision':state['revision'],
                         'report_path':str(Path(report_path).resolve()),
                         'report_sha256':digest(report), 'candidate_root':report['candidate_root'],
                         'suite_root':report['suite_root']}
    state['accepted'] = accepted
    state['revision'] += 1
    write_json(Path(workspace)/'state.json',state)
    log(workspace,'EXECUTED_ANCHORS_BAKER_ACCEPTED',{'anchors':result['anchors'],
                  'records':[accepted[aid] for aid in result['anchors']],
                  'baker':baker.strip(), 'report_sha256':digest(report)})
    return {'accepted_anchors':result['anchors'], 'kind':'executed',
            'report_sha256':digest(report), 'acceptance':'BAKER_ATTESTED',
            'note':'Acceptance invalidates automatically when report, suite, or candidate bytes change.'}


def evidence_current(record):
    """Used by Functional Graph. Missing/mutated bytes mean no acceptance."""
    try:
        if record.get('kind')=='gui-reviewed':
            from .conformance import evidence_current as gui_current
            return gui_current(record)
        if record.get('kind') != 'executed':
            return True
        report = read_json(record['report_path'])
        if digest(report) != record['report_sha256']:
            return False
        if record.get('anchor_id') not in verify_report(report,record['candidate_root'],record['suite_root'])['anchors']:
            return False
        return record.get('recipe_hash') == report['recipe_sha256']
    except (KeyError, OSError, KPPError, ValueError, TypeError):
        return False
