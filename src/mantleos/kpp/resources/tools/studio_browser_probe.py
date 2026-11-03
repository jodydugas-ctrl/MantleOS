"""Optional real-browser probe of a local operator-owned calculator Studio.

Requires separately provisioned Playwright and Chromium. Executes no imported
code. --reviewed permits temporary public project edits and packaged local tests.
--accept-demo additionally exercises synthetic Baker acceptance of the calculator.
"""
import argparse
import copy
import json
from pathlib import Path
from urllib.parse import urlparse

from mantleos import anchors, studio_demo


def run(nest,url,chromium,output,*,reviewed=False,accept_demo=False):
    if reviewed is not True:raise PermissionError('Explicit browser effect review required')
    parsed=urlparse(url)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.path not in ('','/') or parsed.username or parsed.password:raise ValueError('Use a local loopback origin')
    from playwright.sync_api import sync_playwright
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    origin=url.rstrip('/');original=studio_demo.project();observed=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=str(chromium),headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000})
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        response=page.goto(origin+'/studio',wait_until='networkidle')
        assert response.status==200 and 'www-authenticate' not in response.headers
        current=context.request.get(origin+'/studio/project').json()
        if current.get('project')!=original:browser.close();raise ValueError('Probe requires the unchanged packaged calculator project')
        page.wait_for_function("document.getElementById('projectResult').textContent==='STRUCTURALLY_VALID'")
        page.get_by_role('button',name='N-CALC Neutral',exact=True).click()
        assert 'Own arithmetic result' in page.locator('#selection').inner_text()
        page.locator('.tabs [data-view="contracts"]').click()
        page.locator('details').filter(has=page.locator('#project')).locator('summary').click()
        def save(value):
            page.locator('#project').fill(json.dumps(value))
            with page.expect_response(lambda r:r.url==origin+'/studio/project' and r.request.method=='POST') as response:
                page.get_by_role('button',name='Validate and save revision',exact=True).click()
            result=response.value.json()
            if 'error' in result:raise ValueError(result['error'])
            return result
        try:
            for count in (1,3,4,9):
                value=copy.deepcopy(original);value.pop('fixtures');value['id']='Probe-'+str(count)
                apps=[anchors.application('APP-'+str(i),definition_id='Neutral' if count==1 else ('BlackHole','Neutral','WhiteHole')[i%3],attributes={'responsibility':'Synthetic browser responsibility '+str(i)}) for i in range(count)]
                value['recipe']['anchor_design'].update(applications=apps,flows=[],state=[],effects=[])
                for obligation in value['recipe']['anchors']:obligation['design_anchors']=[a['id'] for a in apps]
                value['layout']={a['id']:[100+i*100,100] for i,a in enumerate(apps)}
                result=save(value);assert result['inspection']['status']=='STRUCTURALLY_VALID'
                observed.append(count)
            page.locator('#linkFrom').select_option('APP-0');page.locator('#linkTo').select_option('APP-1')
            page.locator('#linkMeaning').fill('Reviewed relation <img src=x onerror=window.hostile=true>')
            page.get_by_role('button',name='Add typed relationship',exact=True).click()
            result=save(json.loads(page.locator('#project').input_value()))
            assert len(result['project']['recipe']['anchor_design']['flows'])==1 and not page.evaluate('window.hostile===true')
        finally:save(original)
        page.locator('.tabs [data-view="verification"]').click()
        page.get_by_role('button',name='Run packaged regression and repair',exact=True).click()
        page.wait_for_function("document.getElementById('evaluation').textContent.includes('PENDING_BAKER')",timeout=30000)
        stages=json.loads(page.locator('#evaluation').inner_text())['stages']
        assert [s['all_passed'] for s in stages]==[True,True,True,False,True]
        if accept_demo:
            page.on('dialog',lambda dialog:dialog.accept())
            page.get_by_role('button',name='Baker: accept current verified calculator',exact=True).click()
            page.wait_for_function("document.getElementById('evaluation').textContent.includes('kpp.completion/1')",timeout=30000)
        with page.expect_download() as download:page.get_by_role('link',name='Export',exact=True).click()
        download.value.save_as(str(output/'Anchor-Studio-Demo.anchorstudio'))
        page.locator('.tabs [data-view="canvas"]').click()
        page.screenshot(path=str(output/'studio.png'));browser.close()
    report={'automatic_local_access':'FRESH_BROWSER_NO_CREDENTIALS','applications':observed,'typed_relationship':'PASS','hostile_label':'PASS','regression_repair':[s['all_passed'] for s in stages],
        'baker_action':'SYNTHETIC_CALCULATOR_ONLY' if accept_demo else 'NOT_REQUESTED','page_errors':errors,
        'scope':'Real browser project editor and packaged calculator; no general product acceptance'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if errors:raise RuntimeError('Browser errors recorded; inspect report')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--nest',type=Path,required=True);p.add_argument('--url',default='http://127.0.0.1:18880')
    p.add_argument('--chromium',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--reviewed',action='store_true');p.add_argument('--accept-demo',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.nest,a.url,a.chromium,a.output,reviewed=a.reviewed,accept_demo=a.accept_demo),indent=2))
