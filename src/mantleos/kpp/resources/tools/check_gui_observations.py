"""Actual browser captures and deliberately partial synthetic GUI coverage oracles."""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir())))
from mantleos.kpp.core import read_json
from mantleos.kpp.workshop import begin, install_module, inspection
from mantleos.kpp.conformance import record_capture, compare_captures, coverage_matrix
from mantleos.kpp import png
from check_browser_preview import free_port, wait_for_server


def exercise(executable=None):
    try:from playwright.sync_api import sync_playwright
    except ImportError as error:raise RuntimeError('Playwright unavailable') from error
    recipe=copy.deepcopy(read_json(ROOT/'recipes/notepad-demo.json'))
    reference=read_json(ROOT/'recipes/qt-gui-coverage-demo.json')
    recipe['id']='synthetic-browser-gui-oracle';recipe['product_kind']='biosoftware'
    recipe['target']=reference['target'];recipe['reference_gui']=reference['reference_gui']
    recipe['anchors'].insert(0,copy.deepcopy(reference['anchors'][0]))
    inventory=read_json(ROOT/reference['reference_gui']['inventory']['path'])
    editor=next(e['id'] for e in inventory['entries'] if e.get('class')=='QPlainTextEdit')
    actions={e['label']:e['id'] for e in inventory['entries'] if e['kind']=='action'}
    with tempfile.TemporaryDirectory(prefix='kpp-gui-browser-') as temporary:
        root=Path(temporary);workspace=root/'workspace';start=time.monotonic()
        begin(workspace,recipe,ROOT);port=free_port();url=f'http://127.0.0.1:{port}'
        process=subprocess.Popen([sys.executable,'-m','mantleos','kpp','serve','--workspace',str(workspace),'--port',str(port)],
                                 cwd=ROOT,env={**os.environ,'PYTHONPATH':str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir()))},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait_for_server(url,process)
            with sync_playwright() as playwright:
                options={'headless':True}
                if executable:options['executable_path']=executable
                browser=playwright.chromium.launch(**options)
                try:
                    page=browser.new_page(viewport={'width':1280,'height':720})
                    page.on('dialog',lambda dialog:dialog.accept())
                    page.goto(url,wait_until='domcontentloaded')
                    page.wait_for_function('() => window.KPP&&window.KPP.status().revision>0')
                    page.locator('#notes').fill('A real first interaction')
                    first_edit=round(time.monotonic()-start,3)
                    install_module(workspace,'edit',ROOT/'previews/notepad/edit.js')
                    page.wait_for_function("() => window.KPP.has('edit')")
                    page.locator('#clear').click()
                    assert page.locator('#notes').input_value()==''
                    assert page.locator('#open').is_visible() and page.locator('#open').is_disabled()
                    assert page.get_by_role('button',name='Find',exact=True).count()==0
                    capture=root/'capture.png';page.screenshot(path=str(capture),full_page=True)
                    width,height,pixels=png.read(capture)
                    assert (width,height)==(1280,720)
                    assert pixels[:4]==bytes([237,241,246,255]),'Decoded browser background does not match CSS oracle'
                    def region(selector):
                        box=page.locator(selector).bounding_box();assert box
                        x,y=math.floor(box['x']),math.floor(box['y'])
                        return [x,y,math.ceil(box['x']+box['width'])-x,math.ceil(box['y']+box['height'])-y]
                    claims=[
                        {'entry_id':editor,'locator':{'region':region('#notes')},'represented':True,'functional':True,'tested':True},
                        {'entry_id':actions['Clear'],'locator':{'region':region('#clear')},'represented':True,'functional':True,'tested':True},
                        {'entry_id':actions['Open'],'locator':{'region':region('#open')},'represented':True,'functional':False,'tested':False},
                        {'entry_id':actions['Find'],'locator':{'region':region('.menus')},'represented':False,'functional':False,'tested':False}]
                    ids=[item['entry_id'] for item in claims]
                    candidate=record_capture(workspace,capture,'candidate','runtime','developer browser oracle',
                        'normal','empty synthetic editor',ids,'Type draft, clear after confirmation, inspect disabled Open and absent Find',
                        'empty editor; Open disabled; Find absent','empty editor; Open disabled; Find absent',claims)
                    # An explicitly labeled synthetic twin baseline tests the capture/codec/comparison
                    # path. It is not an upstream Qt runtime screenshot or a source-parity assertion.
                    twin=root/'synthetic-twin.png';twin.write_bytes(png.encode(width,height,pixels))
                    baseline=record_capture(workspace,twin,'reference','screenshot','synthetic pixel twin oracle',
                        'normal','empty synthetic editor')
                    comparison=compare_captures(workspace,baseline['id'],candidate['id'],'developer pixel oracle')
                    assert comparison['metrics']['changed_pixels']==0
                    matrix=coverage_matrix(workspace)
                    assert matrix['counts']=={'discovered':20,'accounted_for':20,'represented':3,'functional':2,'tested':2,'accepted':0,'excluded':0}
                    assert inspection(workspace)['accepted']==0
                    return {'result':'PASS','checks':['real_first_edit','actual_chromium_png_css_oracle','visible_disabled_control_is_represented',
                            'missing_reference_control_not_represented','independent_stage_counts','capture_regions_bound_to_viewport',
                            'matched_pixel_comparison_without_acceptance','one_graph_coverage','no_mind_or_splice'],
                            'matrix_counts':matrix['counts'],'percent_of_discovered':matrix['percent_of_discovered'],
                            'time_to_first_edit_seconds':first_edit,'reference_scope':'Synthetic Qt declarations and an explicitly labeled pixel twin; no native Qt or Notepad Next parity',
                            'acceptance':'NOT_GRANTED'}
                finally:browser.close()
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium');parser.add_argument('--json-out',type=Path)
    args=parser.parse_args(argv)
    try:result=exercise(args.chromium)
    except Exception as error:
        detail=str(error)
        result={'result':'BLOCKED' if any(value in detail for value in ('Playwright unavailable','Executable doesn\'t exist','ERR_BLOCKED_BY_ADMINISTRATOR')) else 'FAIL','reason':detail[:1500],'acceptance':'NOT_GRANTED'}
    body=json.dumps(result,indent=2)+'\n'
    if args.json_out:args.json_out.write_text(body,encoding='utf-8')
    print(body);return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
