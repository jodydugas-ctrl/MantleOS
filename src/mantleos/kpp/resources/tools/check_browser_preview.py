"""Opt-in, real Chromium end-to-end exercise of KPP's progressive Notepad.

Requires Playwright and an installed Chromium; not required to use KPP itself.
Starts only the bundled trusted demo with a loopback preview, and closes it.
No browser emulation, mocks or automatic downloads from the network.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir())))
from mantleos.kpp.core import read_json
from mantleos.kpp.workshop import begin, install_module


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for_server(url, process, seconds=12):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if process.poll() is not None:
            raise RuntimeError('Preview server exited before accepting requests')
        try:
            with urllib.request.urlopen(url+'/snapshot', timeout=0.5) as response:
                if response.status == 200:
                    return
        except (OSError, ValueError):
            time.sleep(0.1)
    raise RuntimeError('Preview server did not become ready on loopback')


def exercise(executable=None, screenshot=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError('Playwright unavailable; install it separately to run this optional browser gate') from exc

    with tempfile.TemporaryDirectory(prefix='kpp-browser-') as td:
        ws=Path(td)/'workspace'
        begin(ws, read_json(ROOT/'recipes/notepad-demo.json'), ROOT)
        port=free_port()
        url=f'http://127.0.0.1:{port}'
        env=dict(os.environ, PYTHONPATH=str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir())))
        server=subprocess.Popen([sys.executable,'-m','mantleos','kpp','serve','--workspace',str(ws),'--port',str(port)],
                                cwd=ROOT,env=env, stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        try:
            wait_for_server(url, server)
            with sync_playwright() as pw:
                options={'headless': True, 'args':['--no-sandbox','--disable-dev-shm-usage']}
                if executable:
                    options['executable_path']=executable
                browser=pw.chromium.launch(**options)
                try:
                    context=browser.new_context(accept_downloads=True)
                    page=context.new_page()
                    errors=[]
                    page.on('pageerror',lambda error: errors.append(str(error)))
                    page.on('dialog',lambda dialog: dialog.accept())
                    response=page.goto(url,wait_until='domcontentloaded',timeout=12000)
                    assert response.status==200, f'Bad server status: {response.status}'
                    editor=page.locator('#notes')
                    assert editor.is_enabled(), 'Initial editor not usable'
                    assert not page.locator('#observe').is_checked(), 'Activity must default to off'
                    assert page.locator('#save').is_disabled() and page.locator('#clear').is_disabled(), 'Modules must begin gated'
                    text='Real browser draft \u2014 \u2713 \u00e9 \u6f22\u5b57'
                    editor.fill(text)
                    page.reload(wait_until='domcontentloaded')
                    assert page.locator('#notes').input_value()==text, 'Draft recovery across reload failed'
                    if screenshot:
                        Path(screenshot).parent.mkdir(parents=True,exist_ok=True)
                        page.screenshot(path=str(screenshot),full_page=True)
                    page.evaluate("() => {document.getElementById('notes').setSelectionRange(3,7);window.editorBefore=document.getElementById('notes')}")
                    # Modules are added while the same mounted textarea remains usable.
                    install_module(ws,'edit',ROOT/'previews/notepad/edit.js')
                    page.locator('#clear').wait_for(state='visible')
                    page.wait_for_function("() => !document.getElementById('clear').disabled",timeout=10000)
                    assert page.locator('#save').is_disabled(), 'File actions became available too early'
                    assert page.locator('#notes').input_value()==text, 'Bake lost existing editor state'
                    assert page.evaluate("() => document.getElementById('notes')===window.editorBefore && window.editorBefore.selectionStart===3 && window.editorBefore.selectionEnd===7"), 'Mounted editor/caret changed'
                    install_module(ws,'files',ROOT/'previews/notepad/files.js',['edit'])
                    page.wait_for_function("() => !document.getElementById('save').disabled",timeout=10000)
                    assert page.locator('#notes').input_value()==text
                    # A nonmutating module without readiness is visibly failed and remains gated.
                    rejected=Path(td)/'no-ready.js';rejected.write_text('/* no readiness acknowledgment */',encoding='utf-8')
                    page.evaluate("() => {const b=document.createElement('button');b.id='failed-control';b.dataset.requires='no-ready';b.disabled=true;document.getElementById('app').appendChild(b)}")
                    install_module(ws,'no-ready',rejected)
                    page.wait_for_function("() => document.getElementById('kpp-progress').textContent.includes('module issue')",timeout=10000)
                    assert page.locator('#failed-control').is_disabled()
                    assert page.locator('#notes').input_value()==text
                    with page.expect_download(timeout=10000) as info:
                        page.locator('#save').click()
                    download=info.value
                    saved=Path(td)/'download.txt'
                    download.save_as(saved)
                    assert saved.read_text(encoding='utf-8')==text, 'Downloaded Unicode bytes not preserved'
                    replacement='Opened a second file\nUTF-8: caf\u00e9\n'
                    upload=Path(td)/'new.txt';upload.write_text(replacement,encoding='utf-8')
                    page.locator('#filepicker').set_input_files(str(upload))
                    page.wait_for_function("() => document.getElementById('notes').value === 'Opened a second file\\nUTF-8: caf\\u00e9\\n'",timeout=10000)
                    page.locator('#clear').click()
                    assert page.locator('#notes').input_value()=='', 'Clear failed'
                    assert not errors, 'Browser JS errors: '+repr(errors)
                    context.close()
                    return {'result':'PASS','browser':'Chromium via Playwright',
                            'checks':['initial_editor','privacy_default','module_gates','draft_recovery',
                                      'progressive_admission','mounted_editor_selection_preserved','failed_readiness_gated',
                                      'unicode_download','file_open','clear','console_page_errors'],
                            'acceptance':'NOT_GRANTED'}
                finally:
                    browser.close()
        finally:
            server.terminate()
            try: server.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill();server.communicate(timeout=5)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Opt-in Chromium browser E2E of bundled, trusted KPP example')
    parser.add_argument('--chromium',help='Installed Chromium executable (default Playwright bundled browser)')
    parser.add_argument('--json-out',type=Path,help='Optional report path; do not write inside release repository')
    parser.add_argument('--screenshot',type=Path,help='Capture the actual first editable surface; appearance evidence only')
    args=parser.parse_args(argv)
    try:
        report=exercise(args.chromium,args.screenshot)
    except Exception as exc:
        detail=str(exc)
        blocked=('ERR_BLOCKED_BY_ADMINISTRATOR' in detail or 'Playwright unavailable' in detail or
                 'Executable doesn\'t exist' in detail or 'browserType.launch: Failed to launch' in detail)
        report={'result':'BLOCKED' if blocked else 'FAIL','error':detail[:1500]}
    print(json.dumps(report,sort_keys=True))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True,exist_ok=True)
        args.json_out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return 0 if report['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
