"""Actual hosted-browser fixed oracles for managed failure, withdrawal and transport."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir())))
from mantleos.kpp.core import read_json, write_json
from mantleos.kpp.workshop import begin, install_module, set_module_enabled, inspection
from mantleos.kpp.portability import export_preview, import_preview
from check_browser_preview import free_port, wait_for_server


def server(workspace):
    port=free_port();url=f'http://127.0.0.1:{port}'
    process=subprocess.Popen([sys.executable,'-m','mantleos','kpp','serve','--workspace',str(workspace),'--port',str(port)],
                             cwd=ROOT,env={**os.environ,'PYTHONPATH':str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir()))},
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:wait_for_server(url,process)
    except Exception:process.terminate();process.wait(timeout=5);raise
    return process,url


def exercise(executable=None):
    try:from playwright.sync_api import sync_playwright
    except ImportError as error:raise RuntimeError('Playwright unavailable') from error
    with tempfile.TemporaryDirectory(prefix='kpp-managed-browser-') as temporary:
        root=Path(temporary);workspace=root/'workspace';processes=[]
        begin(workspace,read_json(ROOT/'recipes/notepad-demo.json'),ROOT)
        process,url=server(workspace);processes.append(process)
        try:
            with sync_playwright() as playwright:
                options={'headless':True}
                if executable:options['executable_path']=executable
                browser=playwright.chromium.launch(**options)
                try:
                    page=browser.new_page();errors=[]
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.goto(url,wait_until='domcontentloaded')
                    page.wait_for_function('() => window.KPP && window.KPP.status().revision>0')
                    text='Keep my draft \u2713 caf\u00e9 \u6f22\u5b57'
                    page.locator('#notes').fill(text)
                    page.evaluate("() => document.getElementById('notes').setSelectionRange(3,9)")
                    install_module(workspace,'edit',ROOT/'previews/notepad/edit.js')
                    install_module(workspace,'files',ROOT/'previews/notepad/files.js',['edit'])
                    page.wait_for_function("() => window.KPP.has('files')")
                    assert page.locator('#notes').input_value()==text
                    assert page.evaluate("() => document.getElementById('notes').selectionStart===3&&document.getElementById('notes').selectionEnd===9")
                    # Reviewed destructive fixture fails during activation after making managed resources.
                    broken=root/'broken.js'
                    broken.write_text("window.KPP.define('broken',ctx=>{const n=document.createElement('button');n.id='leaked-control';ctx.append(document.getElementById('app'),n);ctx.listen(document.getElementById('notes'),'input',()=>window.leakedCalls++);window.NotepadBody.restore('destroyed');throw new Error('deliberate activation failure');});",encoding='utf-8')
                    page.evaluate('() => {window.leakedCalls=0;}')
                    install_module(workspace,'broken',broken)
                    page.wait_for_function("() => Boolean(window.KPP.status().failed.broken)")
                    assert page.locator('#notes').input_value()==text
                    assert page.locator('#leaked-control').count()==0
                    assert page.evaluate("() => document.getElementById('notes').selectionStart===3&&document.getElementById('notes').selectionEnd===9")
                    calls=page.evaluate('() => window.leakedCalls')
                    page.locator('#notes').fill(text+' retained')
                    assert page.evaluate('() => window.leakedCalls')==calls,'Failed activation leaked an input listener'
                    text+=' retained'
                    set_module_enabled(workspace,'broken',False)
                    page.wait_for_function("() => !window.KPP.status().failed.broken")
                    # A successful module may also fail during a user action; restore that action's input state.
                    event_fault=root/'event-fault.js'
                    event_fault.write_text("window.KPP.define('event-fault',ctx=>{const n=document.createElement('button');n.id='fault-action';n.textContent='Synthetic failing action';ctx.append(document.getElementById('app'),n);ctx.listen(n,'click',()=>{window.NotepadBody.restore('lost by action');throw new Error('deliberate action failure');});});",encoding='utf-8')
                    install_module(workspace,'event-fault',event_fault)
                    page.wait_for_function("() => window.KPP.has('event-fault')")
                    page.locator('#fault-action').click()
                    page.wait_for_function("() => Boolean(window.KPP.status().failed['event-fault'])")
                    assert page.locator('#notes').input_value()==text
                    assert page.locator('#fault-action').count()==0
                    assert page.evaluate("() => window.KPP.has('edit')&&window.KPP.has('files')")
                    set_module_enabled(workspace,'event-fault',False)
                    # Unwinding a managed property must keep the user's newer draft, not its
                    # value when the module was activated.
                    property_module=root/'property-cell.js'
                    property_module.write_text("window.KPP.define('property-cell',ctx=>{const editor=document.getElementById('notes');ctx.property(editor,'value',editor.value);});",encoding='utf-8')
                    install_module(workspace,'property-cell',property_module)
                    page.wait_for_function("() => window.KPP.has('property-cell')")
                    text+=' newer';page.locator('#notes').fill(text)
                    set_module_enabled(workspace,'property-cell',False)
                    page.wait_for_function("() => !window.KPP.has('property-cell')")
                    assert page.locator('#notes').input_value()==text
                    set_module_enabled(workspace,'edit',False,cascade=True)
                    page.wait_for_function("() => !window.KPP.has('edit')&&!window.KPP.has('files')")
                    assert page.locator('#clear').is_disabled() and page.locator('#save').is_disabled()
                    assert page.locator('#notes').input_value()==text
                    for mid in ('edit','files'):set_module_enabled(workspace,mid,True)
                    page.wait_for_function("() => window.KPP.has('files')")
                    dialogs=[]
                    decision={'accept':False}
                    def dialog_decision(dialog):
                        dialogs.append(dialog.message)
                        dialog.accept() if decision['accept'] else dialog.dismiss()
                    page.on('dialog',dialog_decision)
                    page.locator('#clear').click()
                    assert len(dialogs)==1,'Reactivation duplicated an event listener'
                    assert page.locator('#notes').input_value()==text
                    # Invalid UTF-8 must leave existing draft intact.
                    invalid=root/'invalid.txt';invalid.write_bytes(b'\xff\xfe\xff')
                    page.locator('#filepicker').set_input_files(str(invalid))
                    # Replacement confirmation was dismissed; repeat with no draft for decode refusal,
                    # then restore the protected draft using its explicit product adapter.
                    assert page.locator('#notes').input_value()==text
                    state_before=page.evaluate('() => window.KPPBody.snapshot()')
                    page.evaluate("() => window.NotepadBody.restore('')")
                    page.locator('#filepicker').set_input_files(str(invalid))
                    page.wait_for_function("() => document.getElementById('save-status').textContent.startsWith('Open failed:')")
                    assert page.locator('#notes').input_value()==''
                    page.evaluate('(state) => window.KPPBody.restore(state)',state_before)
                    # Delay an actual File read, then type and verify it cannot clobber
                    # the newer draft. Also prevent a withdrawn/re-enabled reader completing.
                    decision['accept']=True
                    pending=root/'pending.txt';pending.write_text('Delayed replacement',encoding='utf-8')
                    page.evaluate("() => {window.originalReader=File.prototype.arrayBuffer;File.prototype.arrayBuffer=function(){return new Promise(resolve=>{window.delayedRead=()=>window.originalReader.call(this).then(resolve);});};}")
                    page.locator('#filepicker').set_input_files(str(pending))
                    page.wait_for_function('() => Boolean(window.delayedRead)')
                    text+=' typed during read';page.locator('#notes').fill(text)
                    page.evaluate('() => window.delayedRead()')
                    page.wait_for_function("() => document.getElementById('save-status').textContent.startsWith('Draft changed during file read')")
                    assert page.locator('#notes').input_value()==text
                    page.evaluate('() => {window.delayedRead=null;}')
                    page.locator('#filepicker').set_input_files(str(pending))
                    page.wait_for_function('() => Boolean(window.delayedRead)')
                    set_module_enabled(workspace,'files',False)
                    page.wait_for_function("() => !window.KPP.has('files')")
                    set_module_enabled(workspace,'files',True)
                    page.wait_for_function("() => window.KPP.has('files')")
                    page.evaluate('() => window.delayedRead()')
                    assert page.locator('#notes').input_value()==text
                    page.evaluate('() => {File.prototype.arrayBuffer=window.originalReader;}')
                    page.evaluate("() => document.getElementById('notes').setSelectionRange(3,9)")
                    checkpoint=root/'state.json'
                    write_json(checkpoint,page.evaluate('() => window.KPP.exportState()'))
                    bundle=root/'preview.zip';restored=root/'restored'
                    export_preview(workspace,bundle,checkpoint);import_preview(bundle,restored)
                    assert inspection(restored)['accepted']==0
                    other,other_url=server(restored);processes.append(other)
                    receiving=browser.new_page();receiving.on('pageerror',lambda error:errors.append(str(error)))
                    receiving.goto(other_url,wait_until='domcontentloaded')
                    receiving.wait_for_function("() => window.KPP&&window.KPP.has('files')")
                    assert receiving.locator('#notes').input_value()==text
                    assert receiving.evaluate("() => document.getElementById('notes').selectionStart===3&&document.getElementById('notes').selectionEnd===9")
                    assert receiving.locator('#clear').is_enabled() and receiving.locator('#save').is_enabled()
                    assert not errors,errors
                    return {'result':'PASS','checks':['mounted_selection_preserved','destructive_activation_restored',
                            'failed_resources_removed','failed_action_restored','working_extensions_retained',
                            'dependency_withdrawal_gated','reactivation_without_duplicate_handlers',
                            'withdrawal_keeps_newer_property_state','cancel_preserves_draft','invalid_utf8_refused',
                            'typing_during_read_preserved','withdrawn_reader_cannot_complete_after_reactivation','source_bound_body_transport',
                            'receiving_origin_draft_and_selection','no_page_errors'],
                            'acceptance':'NOT_GRANTED'}
                finally:browser.close()
        finally:
            for process in processes:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium');parser.add_argument('--json-out',type=Path)
    args=parser.parse_args(argv)
    try:result=exercise(args.chromium)
    except Exception as error:
        message=str(error)
        result={'result':'BLOCKED' if any(value in message for value in ('Playwright unavailable','Executable doesn\'t exist','ERR_BLOCKED_BY_ADMINISTRATOR')) else 'FAIL','reason':message[:1500],'acceptance':'NOT_GRANTED'}
    body=json.dumps(result,indent=2)+'\n'
    if args.json_out:args.json_out.write_text(body,encoding='utf-8')
    print(body);return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
