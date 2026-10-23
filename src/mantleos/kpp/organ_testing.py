"""Opt-in real-browser Save checks; source pins do not authenticate reports."""
import copy
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import uuid

from .core import KPPError, digest, read_json, write_json
from .module_revisions import sha, select_candidate, source_path, revision_sources
from .organs import project, evidence, recheck_source
from .scanner import scan
from .workshop import load, workspace_lock, preview_fingerprint

CASES = ('unicode-download', 'empty-download', 'one-download-per-action',
         'synthetic-gesture-refused', 'download-failure-preserves-body',
         'resource-cleanup', 'storage-unavailable', 'open-independent', 'clean-browser')


def test_identity():
    package = Path(__file__).parent
    return digest({name: sha((package / name).read_bytes()) for name in (
        'organ_testing.py', 'organs.py', 'module_revisions.py', 'workshop.py',
        'scanner.py', 'server.py', 'assets/progressive.js')})


def _candidate(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise KPPError('Missing/unsafe candidate source')
    with path.open('rb') as stream:
        data = stream.read(512001)
    if not data or len(data) > 512000:
        raise KPPError('Candidate must be nonempty and under 512KB')
    return data


def _baseline(recipe, state, module):
    return {'workspace_id': state['workspace_id'], 'revision': state['revision'],
            'fingerprint': preview_fingerprint(recipe, state), 'recipe_sha256': digest(recipe),
            'module_id': module['id'], 'module_sha256': module['sha256']}


def _module(state, module_id):
    module = next((m for m in state['modules'] if m['id'] == module_id), None)
    if module_id != 'save' or module is None or not module['enabled']:
        raise KPPError('This qualified browser profile requires an enabled Notepad save module')
    return module


def _bindings(recipe, mapping, scan_report, module):
    relative = source_path(module).removeprefix('app/')
    return {'schema': 'kpp.organ-scan-bindings/1', 'recipe_sha256': digest(recipe),
            'mapping_sha256': digest(mapping), 'links': [{'anchor_id': 'save-file',
            'files': [relative], 'nodes': [n['id'] for n in scan_report['native_report']['graph']['nodes']
                                          if n['path'] == relative]}]}


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def browser_checks(workspace, chromium=None):
    """Execute only the explicitly reviewed local specimen in Chromium."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        return {'result': 'BLOCKED', 'checks': [], 'reason': 'Playwright unavailable: ' + str(error)}
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        port = port_socket.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).parents[2])}
    server = subprocess.Popen([sys.executable, '-m', 'mantleos', 'kpp', 'serve',
                               '--workspace', str(workspace), '--port', str(port)],
                              env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    checks = []
    def record(name, function):
        try:
            function()
            checks.append({'name': name, 'result': 'PASS'})
        except Exception as error:
            checks.append({'name': name, 'result': 'FAIL', 'error': str(error)[:1500]})
    try:
        deadline = time.monotonic() + 12
        while True:
            if server.poll() is not None:
                raise RuntimeError('Trial preview exited: ' + server.stderr.read().decode(errors='replace')[-1200:])
            try:
                with urllib.request.urlopen(url + '/snapshot', timeout=0.5) as response:
                    if response.status == 200:
                        break
            except (OSError, ValueError):
                if time.monotonic() > deadline:
                    raise RuntimeError('Trial preview did not become ready')
                time.sleep(0.1)
        with sync_playwright() as driver:
            options = {'headless': True}
            if chromium:
                options['executable_path'] = chromium
            browser = driver.chromium.launch(**options)
            try:
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                errors, downloads = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('download', lambda download: downloads.append(download))
                page.goto(url, wait_until='domcontentloaded')
                page.wait_for_function("() => window.KPP && window.KPP.has('save') && window.KPP.has('open')", timeout=12000)

                def save_text(text, filename):
                    page.locator('#notes').fill(text)
                    page.evaluate('(name) => {window.NotepadBody.setFilename(name); const e=window.NotepadBody.editor;e.setSelectionRange(0,Math.min(3,e.value.length));}', filename)
                    before = page.evaluate('() => window.KPPBody.snapshot()')
                    with page.expect_download(timeout=6000) as pending:
                        page.locator('#save').click()
                    download = pending.value
                    _assert(download.failure() is None, 'Browser download failed')
                    _assert(download.suggested_filename == filename, 'Download filename changed')
                    _assert(Path(download.path()).read_bytes() == text.encode('utf-8'), 'Download bytes differ from editor UTF-8')
                    _assert(page.evaluate('() => window.KPPBody.snapshot()') == before, 'Save changed Body state')
                    status = page.locator('#save-status').inner_text()
                    _assert('Download initiated' in status and 'saved to disk' not in status.lower(), 'Save did not report download initiation honestly')
                record('unicode-download', lambda: save_text('Keep this draft\nCaf\u00e9 \u6f22\u5b57 \U0001f680\n', 'Unicode notes.txt'))
                record('empty-download', lambda: save_text('', 'empty.txt'))

                def once():
                    start = len(downloads)
                    save_text('Exactly one download', 'once.txt')
                    page.wait_for_timeout(250)
                    _assert(len(downloads) == start + 1, 'Save produced duplicate downloads')
                record('one-download-per-action', once)

                def synthetic():
                    start = len(downloads)
                    page.evaluate("() => document.getElementById('save').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
                    page.wait_for_timeout(250)
                    _assert(len(downloads) == start, 'Synthetic event initiated a download')
                record('synthetic-gesture-refused', synthetic)

                def refusal():
                    before = page.evaluate('() => window.KPPBody.snapshot()')
                    page.evaluate("() => {window.oldCreateURL=URL.createObjectURL;URL.createObjectURL=()=>{throw new Error('Injected download refusal')}}")
                    try:
                        page.locator('#save').click()
                        _assert(page.evaluate('() => window.KPPBody.snapshot()') == before, 'Failed Save changed the draft or selection')
                        _assert(page.evaluate("() => window.KPP.has('open')"), 'Save failure withdrew Open')
                        _assert('failed' in page.locator('#save-status').inner_text().lower(), 'Save failure was not disclosed')
                    finally:
                        page.evaluate('() => {URL.createObjectURL=window.oldCreateURL;delete window.oldCreateURL;}')
                record('download-failure-preserves-body', refusal)

                def cleanup():
                    from .workshop import set_module_enabled
                    page.evaluate("() => {window.revokedURLs=[];window.oldRevokeURL=URL.revokeObjectURL;URL.revokeObjectURL=(url)=>{window.revokedURLs.push(url);window.oldRevokeURL(url)}}")
                    save_text('Cleanup check', 'cleanup.txt')
                    set_module_enabled(workspace, 'save', False)
                    page.wait_for_function("() => !window.KPP.has('save')", timeout=10000)
                    _assert(page.evaluate('() => window.revokedURLs.length') > 0, 'Withdrawal leaked pending object URLs')
                    set_module_enabled(workspace, 'save', True)
                    page.wait_for_function("() => window.KPP.has('save')", timeout=10000)
                    start = len(downloads)
                    save_text('After reactivation', 'reactivated.txt')
                    page.wait_for_timeout(200)
                    _assert(len(downloads) == start + 1, 'Reactivation leaked duplicate handlers')
                record('resource-cleanup', cleanup)

                def storage():
                    blocked = browser.new_context(accept_downloads=True)
                    try:
                        blocked.add_init_script("Storage.prototype.getItem=function(){throw new Error('Storage disabled')};Storage.prototype.setItem=function(){throw new Error('Storage disabled')};")
                        alternate = blocked.new_page(); alternate.goto(url, wait_until='domcontentloaded')
                        alternate.wait_for_function("() => window.KPP && window.KPP.has('save')", timeout=10000)
                        alternate.locator('#notes').fill('Memory remains usable \u2713')
                        _assert('unavailable' in alternate.locator('#save-status').inner_text().lower(), 'Storage failure was hidden')
                        with alternate.expect_download(timeout=6000) as pending:
                            alternate.locator('#save').click()
                        _assert(Path(pending.value.path()).read_bytes() == 'Memory remains usable \u2713'.encode(), 'Save depends on persistent storage')
                        _assert(alternate.locator('#notes').input_value() == 'Memory remains usable \u2713', 'Storage failure lost the draft')
                    finally:
                        blocked.close()
                record('storage-unavailable', storage)

                def open_file():
                    page.once('dialog', lambda dialog: dialog.accept())
                    payload = 'Opened independently \u2713\n'
                    page.locator('#filepicker').set_input_files({'name': 'opened.txt', 'mimeType': 'text/plain', 'buffer': payload.encode()})
                    page.wait_for_function('(text) => window.NotepadBody.draft() === text', arg=payload, timeout=6000)
                    _assert(page.evaluate('() => window.NotepadBody.filename()') == 'opened.txt', 'Open did not preserve filename interface')
                record('open-independent', open_file)
                record('clean-browser', lambda: _assert(not errors, 'Browser errors: ' + repr(errors)))
                context.close()
                return {'result': 'PASS' if all(c['result'] == 'PASS' for c in checks) else 'FAIL',
                        'browser': 'Chromium ' + browser.version, 'checks': checks,
                        'acceptance': 'NOT_GRANTED'}
            finally:
                browser.close()
    except Exception as error:
        return {'result': 'BLOCKED' if not checks else 'FAIL', 'checks': checks, 'reason': str(error)[:1500]}
    finally:
        server.terminate()
        try:
            server.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill(); server.communicate(timeout=5)


def run_module_tests(workspace, module_id, source, mapping, output, *, execute=False, reviewed=False, chromium=None):
    """Create an isolated source snapshot; tests never mutate/admit into the baseline."""
    if execute is not True or reviewed is not True:
        raise KPPError('Browser execution requires --execute --reviewed; there is no JavaScript sandbox')
    workspace, output = Path(workspace).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(workspace):
        raise KPPError('Test output must be a new directory outside the baseline workspace')
    content = _candidate(source)
    with workspace_lock(workspace):
        recipe, state = load(workspace)
        module = _module(state, module_id)
        projection = project(recipe, mapping)
        if not any(o['id'] == 'save' and 'save-file' in o['anchor_ids'] for o in mapping['organs']):
            raise KPPError('Save checks require the save-file organ contract')
        baseline = _baseline(recipe, state, module)
        output.mkdir(parents=True)
        trial = output / 'trial'
        # Copy the pinned preview only, never arbitrary workspace files or symlink targets.
        if state.get('gui_evidence') or 'reference_gui' in recipe:
            raise KPPError('This Save profile does not qualify GUI-reference recipes')
        trial.mkdir(); (trial/'artifacts').mkdir(); (trial/'app/modules').mkdir(parents=True)
        paths = ['recipe.json', 'ingredient-labels.json', 'history.jsonl', 'app/runtime.js']
        paths.extend('app/'+name for name in recipe['preview']['assets'])
        for installed in state['modules']:
            paths.extend(revision_sources(installed))
        if state.get('initial_body_sha256'):
            paths.append('app/body-state.json')
        for relative in paths:
            original = workspace/relative
            if original.is_symlink() or not original.resolve().is_relative_to(workspace):
                raise KPPError('Unsafe pinned test source')
            target = trial/relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original.read_bytes())
        trial_state = copy.deepcopy(state)
        trial_state['workspace_id'] = uuid.uuid4().hex
        trial_state['accepted'] = {}; trial_state['phase'] = 'BUILDING'
        trial_module = _module(trial_state, module_id)
        select_candidate(trial, trial_module, content)
        trial_state['revision'] += 1
        write_json(trial / 'state.json', trial_state)
    source_root = trial / 'app'
    report_scan = scan(source_root, depth=3)
    bindings = _bindings(recipe, mapping, report_scan, trial_module)
    observations = evidence(recipe, mapping, bindings, report_scan, source_root)
    # The runner is pinned before execution as well as at verification time.
    identity_before = test_identity()
    runtime = browser_checks(trial, chromium)
    recheck_source(report_scan, source_root)
    current_recipe, current_state = load(workspace)
    if (_baseline(current_recipe, current_state, _module(current_state, module_id)) != baseline
            or test_identity() != identity_before or sha(_candidate(source)) != sha(content)):
        runtime = {**runtime, 'result': 'FAIL', 'reason': 'Baseline, candidate or test implementation changed during testing'}
    report = {'schema': 'kpp.module-test-report/1', 'baseline': baseline,
              'candidate_sha256': sha(content), 'candidate_source': str(Path(source).resolve()),
              'trial_workspace': str(trial), 'test_identity': identity_before,
              'recipe': recipe, 'mapping': mapping, 'projection': projection,
              'scan': report_scan, 'bindings': bindings, 'source_evidence': observations,
              'runtime': runtime, 'result': runtime['result'], 'authority': 'NONE',
              'acceptance': 'NOT_GRANTED', 'execution': 'EXPLICIT_REVIEWED_LOCAL_BROWSER'}
    report['sha256'] = digest(report)
    write_json(output / 'report.json', report)
    write_json(output / 'scan.json', report_scan)
    write_json(output / 'organ-evidence.json', observations)
    return report


def verify_module_evidence(report, workspace, module_id, source):
    """Recheck exact artifacts; explicit review supplies authority, never a digest."""
    try:
        if (report.get('schema') != 'kpp.module-test-report/1'
                or report.get('sha256') != digest({k: v for k, v in report.items() if k != 'sha256'})
                or report.get('result') != 'PASS' or report.get('runtime', {}).get('result') != 'PASS'
                or report.get('execution') != 'EXPLICIT_REVIEWED_LOCAL_BROWSER'):
            raise KPPError('Missing, failed or tampered module evidence')
        cases = report['runtime']['checks']
        if (len(cases) != len(CASES) or {c['name'] for c in cases} != set(CASES)
                or any(c['result'] != 'PASS' for c in cases)):
            raise KPPError('Incomplete browser behavior evidence')
        recipe, state = load(workspace)
        module = _module(state, module_id)
        if report['baseline'] != _baseline(recipe, state, module) or report['recipe'] != recipe:
            raise KPPError('Stale baseline workspace evidence')
        if report['candidate_sha256'] != sha(_candidate(source)):
            raise KPPError('Candidate source differs from tested bytes')
        if report['test_identity'] != test_identity():
            raise KPPError('Test implementation changed; rerun browser checks')
        if report['projection'] != project(recipe, report['mapping']):
            raise KPPError('Organ projection differs from tested contract')
        trial = Path(report['trial_workspace'])
        trial_recipe, trial_state = load(trial)
        trial_module = _module(trial_state, module_id)
        if (trial_recipe != recipe or trial_module['sha256'] != report['candidate_sha256']
                or trial_module['depends'] != module['depends'] or trial_module.get('previous_sha256') != module['sha256']):
            raise KPPError('Trial does not contain the tested candidate and dependencies')
        # Tests must use the same enabled dependencies, seeds and runtime as the baseline.
        fields = ('id', 'sha256', 'depends', 'enabled')
        others = lambda value: [{k: m[k] for k in fields} for m in value['modules'] if m['id'] != module_id]
        if (others(trial_state) != others(state)
                or trial_state['runtime_sha256'] != state['runtime_sha256']
                or trial_state['preview_asset_sha256'] != state['preview_asset_sha256']):
            raise KPPError('Trial dependency/runtime source differs from baseline')
        wanted = _bindings(recipe, report['mapping'], report['scan'], trial_module)
        if report['bindings'] != wanted:
            raise KPPError('Scan does not bind the candidate implementation')
        if report['source_evidence'] != evidence(recipe, report['mapping'], report['bindings'], report['scan'], trial / 'app'):
            raise KPPError('Source evidence differs from pinned scan')
        return report
    except (KeyError, TypeError, AttributeError, OSError, ValueError) as error:
        raise KPPError(str(error)) from error
