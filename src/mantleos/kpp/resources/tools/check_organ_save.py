"""Repeatable, opt-in local Save organ qualification and reviewed replacement demo."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager

SOURCE = next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir())
sys.path.insert(0,str(SOURCE))
from mantleos.kpp.core import KPPError, read_json, write_json
from mantleos.kpp.workshop import begin, install_module, load
from mantleos.kpp.module_revisions import replace_module, restore_module, sha
from mantleos.kpp.portability import export_preview, import_preview

RESOURCE = SOURCE/'mantleos/kpp/resources'


def require(value, message):
    if not value: raise AssertionError(message)


@contextmanager
def preview(workspace):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    url=f'http://127.0.0.1:{port}'
    process=subprocess.Popen([sys.executable,'-m','mantleos','kpp','serve','--workspace',str(workspace),'--port',str(port)],
                             env={**os.environ,'PYTHONPATH':str(SOURCE)},stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        until=time.monotonic()+12
        while True:
            if process.poll() is not None:raise RuntimeError('Preview exited: '+process.stderr.read().decode(errors='replace')[-1500:])
            try:
                with urllib.request.urlopen(url+'/snapshot',timeout=0.5) as response:
                    if response.status==200:break
            except (OSError,ValueError):
                if time.monotonic()>until:raise RuntimeError('Preview did not start')
                time.sleep(0.1)
        yield url
    finally:
        process.terminate()
        try:process.communicate(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.communicate(timeout=5)


def verify(workspace, source, output, chromium):
    command=[sys.executable,'-m','mantleos','kpp','module-test','--workspace',str(workspace),'--id','save',
             '--source',str(source),'--organs',str(RESOURCE/'contracts/notepad-organs.json'),
             '--output',str(output),'--execute','--reviewed']
    if chromium:command.extend(['--chromium',chromium])
    result=subprocess.run(command,env={**os.environ,'PYTHONPATH':str(SOURCE)},capture_output=True,timeout=100)
    if result.returncode not in (0,3):raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])
    report=read_json(output/'report.json')
    if report['result']=='BLOCKED':raise RuntimeError('Browser verification blocked: '+json.dumps(report['runtime']))
    return report


def exercise(output, chromium=None):
    from playwright.sync_api import sync_playwright
    workspace=output/'workspace'
    begin(workspace,read_json(RESOURCE/'recipes/notepad-organs.json'),RESOURCE)
    for mid,dependencies in [('edit',[]),('save',['edit']),('open',['edit'])]:
        install_module(workspace,mid,RESOURCE/f'previews/notepad-organs/{mid}.js',dependencies)
    original=(RESOURCE/'previews/notepad-organs/save.js').read_text(encoding='utf-8')
    candidates=output/'candidates';candidates.mkdir()
    good=candidates/'save-reviewed.js';good.write_text(original.replace(',3000)',',2000)'),encoding='utf-8')
    corrupt=candidates/'save-corrupt.js';corrupt.write_text(original.replace('new Blob([input.text]','new Blob(["CORRUPTED"]'),encoding='utf-8')
    destructive=candidates/'save-draft-loss.js';destructive.write_text(original.replace('link.click();',"link.click();app.restore('Injected draft loss');"),encoding='utf-8')
    fault=candidates/'save-activation-fault.js'
    fault.write_text(good.read_text(encoding='utf-8').replace("'use strict';", "'use strict';\n if(window.injectActivationFailure){window.NotepadBody.restore('Injected activation damage');throw new Error('Injected activation fault');}"),encoding='utf-8')
    checks={}
    baseline=load(workspace)[1]
    for label,candidate in [('corrupt',corrupt),('draft-loss',destructive)]:
        report=verify(workspace,candidate,output/('verification-'+label),chromium)
        require(report['result']=='FAIL',label+' mutation escaped runtime checks')
        try:
            replace_module(workspace,'save',candidate,output/('verification-'+label)/'report.json',
                           expected_revision=baseline['revision'],reviewed=True)
        except KPPError:
            pass
        else:raise AssertionError('Broken candidate was admitted: '+label)
        require(load(workspace)[1]==baseline,'Rejected mutation changed active workspace')
        checks[label+'-regression-rejected']='PASS'
    verified=verify(workspace,good,output/'verification-good',chromium)
    require(verified['result']=='PASS','Good Save candidate failed browser checks')
    checks['candidate-browser-behavior']='PASS'
    with preview(workspace) as url, sync_playwright() as driver:
        options={'headless':True}
        if chromium:options['executable_path']=chromium
        browser=driver.chromium.launch(**options)
        try:
            context=browser.new_context(accept_downloads=True)
            page=context.new_page();errors=[];downloads=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('download',lambda download:downloads.append(download))
            page.goto(url,wait_until='domcontentloaded')
            page.wait_for_function("() => window.KPP&&window.KPP.has('save')&&window.KPP.has('open')",timeout=10000)
            draft='Preserve this living draft\nCaf\u00e9 \u6f22\u5b57 \U0001f680\n'
            page.locator('#notes').fill(draft)
            page.evaluate("() => {window.originalEditor=window.NotepadBody.editor;window.NotepadBody.setFilename('organ-proof.txt');window.NotepadBody.editor.setSelectionRange(3,9);}")
            before=page.evaluate('() => window.KPPBody.snapshot()')
            state=replace_module(workspace,'save',good,output/'verification-good/report.json',
                                 expected_revision=baseline['revision'],reviewed=True)
            page.wait_for_function('(revision) => window.KPP.status().revision>=revision&&window.KPP.has("save")',arg=state['revision'],timeout=10000)
            require(page.evaluate('() => window.KPPBody.snapshot()')==before,'Replacement changed Body state')
            require(page.evaluate('() => window.originalEditor===window.NotepadBody.editor'),'Replacement remounted the editor')
            checks['live-replacement-preserves-state']='PASS'
            with page.expect_download(timeout=6000) as pending:page.locator('#save').click()
            require(Path(pending.value.path()).read_bytes()==draft.encode(),'Replacement saved wrong bytes')
            checks['replacement-download']='PASS'
            # Verification runs in a separate process while the actual editor remains mounted.
            fault_report=verify(workspace,fault,output/'verification-activation-fault',chromium)
            require(fault_report['result']=='PASS','Activation fixture failed in its untriggered environment')
            page.locator('#notes').fill(draft+'Continued typing before failure')
            page.evaluate("() => {window.injectActivationFailure=true;window.NotepadBody.editor.setSelectionRange(2,8);}")
            before=page.evaluate('() => window.KPPBody.snapshot()')
            state=replace_module(workspace,'save',fault,output/'verification-activation-fault/report.json',
                                 expected_revision=state['revision'],reviewed=True)
            page.wait_for_function("() => Boolean(window.KPP.status().failed.save)",timeout=10000)
            require(page.evaluate('() => window.KPPBody.snapshot()')==before,'Activation failure lost draft/selection/filename')
            require(page.locator('#save').is_disabled() and not page.locator('#open').is_disabled(),'Failure did not isolate Save')
            checks['activation-failure-preserves-state']='PASS'
            page.locator('#notes').fill(before['text']+'\nTyping still works')
            page.evaluate("() => {window.injectActivationFailure=false;window.NotepadBody.editor.setSelectionRange(1,7);}")
            before=page.evaluate('() => window.KPPBody.snapshot()')
            state=restore_module(workspace,'save',expected_revision=state['revision'],reviewed=True)
            page.wait_for_function('(revision) => window.KPP.status().revision>=revision&&window.KPP.has("save")',arg=state['revision'],timeout=10000)
            require(page.evaluate('() => window.KPPBody.snapshot()')==before,'Restoration changed user state')
            start=len(downloads)
            with page.expect_download(timeout=6000) as pending:page.locator('#save').click()
            require(Path(pending.value.path()).read_bytes()==before['text'].encode(),'Restored Save produced wrong bytes')
            page.wait_for_timeout(250)
            require(len(downloads)==start+1,'Restoration left duplicate Save listeners')
            require(not errors,'Unexpected browser errors: '+repr(errors))
            checks['restoration-and-handler-cleanup']='PASS'
            checkpoint=output/'browser-state.json';write_json(checkpoint,page.evaluate('() => window.KPP.exportState()'))
            page.screenshot(path=str(output/'notepad-organ.png'),full_page=True)
            bundle=output/'notepad-preview.zip';export_preview(workspace,bundle,checkpoint)
            incoming=output/'restored';import_preview(bundle,incoming)
            require(load(incoming)[1]['accepted']=={},'Acceptance crossed transport boundary')
            with preview(incoming) as receiving_url:
                receiving=browser.new_page();receiving.goto(receiving_url,wait_until='domcontentloaded')
                receiving.wait_for_function("() => window.KPP&&window.KPP.has('save')",timeout=10000)
                require(receiving.evaluate('() => window.KPPBody.snapshot()')==before,'Transport lost Body checkpoint')
                receiving.close()
            checks['transport-and-recovered-browser-state']='PASS'
            context.close()
            browser_version=browser.version
        finally:browser.close()
    recipe,state=load(workspace)
    require(state['phase']=='BUILDING' and state['accepted']=={},'Demonstration granted acceptance')
    return {'schema':'kpp.organ-save-demonstration/1','result':'PASS','checks':checks,
            'browser':'Chromium '+browser_version,'workspace':str(workspace),
            'history':str(workspace/'history.jsonl'),'recipe_sha256':state['recipe_hash'],
            'retained_save_revisions':len(next(m for m in state['modules'] if m['id']=='save')['revisions']),
            'verification_reports':['verification-'+name+'/report.json' for name in ('corrupt','draft-loss','good','activation-fault')],
            'phase':state['phase'],'acceptance':'NOT_GRANTED'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New directory for synthetic workspaces and evidence')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--reviewed',action='store_true')
    parser.add_argument('--chromium')
    args=parser.parse_args(argv)
    if not args.execute or not args.reviewed:parser.error('Local browser execution requires --execute --reviewed')
    output=args.output.resolve()
    if output.exists():parser.error('Choose a new output directory')
    output.mkdir(parents=True)
    try:
        report=exercise(output,args.chromium)
    except Exception as error:
        report={'schema':'kpp.organ-save-demonstration/1','result':'FAIL','error':str(error)[:2500],'acceptance':'NOT_GRANTED'}
    write_json(output/'report.json',report)
    print(json.dumps(report,indent=2))
    return 0 if report['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
