"""Optional real Chromium end-to-end test for custom, non-Notepad progressive delivery.

This uses the real loopback server and Playwright. No mock/screenshot is accepted
as proof of a full host integration. No network downloads are performed.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir())))
from mantleos.kpp.core import read_json
from mantleos.kpp.workshop import begin, install_module
from check_browser_preview import free_port,wait_for_server


def exercise(executable=None):
    try:from playwright.sync_api import sync_playwright
    except ImportError as exc:raise RuntimeError('Playwright not installed (optional test)') from exc
    with tempfile.TemporaryDirectory(prefix='kpp-calc-browser-') as td:
        ws=Path(td)/'workspace'
        begin(ws,read_json(ROOT/'recipes/progressive-calculator.json'),ROOT)
        port=free_port();url=f'http://127.0.0.1:{port}'
        env={**os.environ,'PYTHONPATH':str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir()))}
        proc=subprocess.Popen([sys.executable,'-m','mantleos','kpp','serve','--workspace',str(ws),'--port',str(port)],
                              cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait_for_server(url,proc)
            with sync_playwright() as pw:
                options={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
                if executable:options['executable_path']=executable
                browser=pw.chromium.launch(**options)
                try:
                    context=browser.new_context()
                    page=context.new_page()
                    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                    response=page.goto(url,wait_until='domcontentloaded',timeout=12000)
                    assert response.status==200
                    assert page.locator('h1').inner_text()=='Calculator'
                    assert page.locator('#square').is_disabled()
                    assert 'BUILDING' in page.locator('#kpp-progress').inner_text()
                    page.locator('#calculate').click()
                    assert page.locator('#result').inner_text()=='5'
                    # Add independently reviewed module while user state lives in mounted nodes.
                    install_module(ws,'square',ROOT/'previews/calculator/square.js')
                    page.wait_for_function("() => !document.getElementById('square').disabled",timeout=10000)
                    assert page.locator('#result').inner_text()=='5'
                    assert page.locator('#left').input_value()=='2'
                    page.locator('#square').click()
                    assert page.locator('#result').inner_text()=='25'
                    page.locator('#operation').select_option('subtract')
                    page.locator('#left').fill('9');page.locator('#right').fill('4')
                    page.locator('#calculate').click()
                    assert page.locator('#result').inner_text()=='5'
                    page.reload(wait_until='domcontentloaded')
                    assert page.locator('#result').inner_text()=='5', 'Origin-local result recovery failed'
                    assert page.locator('#left').input_value()=='9'
                    assert not errors, 'Page errors: '+repr(errors)
                    context.close()
                    return {'result':'PASS','checks':['actual_first_surface','base_arithmetic','optional_module_gate',
                                                     'non_replacing_module_activation','existing_result_preserved',
                                                     'arithmetic_after_extension','origin_storage_recovery','no_page_errors'],
                            'acceptance':'NOT_GRANTED'}
                finally:browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Real browser check of custom KPP progressive calculator')
    parser.add_argument('--chromium')
    parser.add_argument('--json-out',type=Path)
    args=parser.parse_args(argv)
    try:result=exercise(args.chromium)
    except Exception as error:
        reason=str(error)
        result={'result':'BLOCKED' if any(s in reason for s in ('ERR_BLOCKED_BY_ADMINISTRATOR','Executable doesn\'t exist','BrowserType.launch','Playwright not installed')) else 'FAIL',
                'reason':reason[:600], 'acceptance':'NOT_GRANTED'}
    body=json.dumps(result,indent=2)+'\n'
    if args.json_out:args.json_out.write_text(body,encoding='utf-8')
    print(body)
    return 0 if result['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
