"""Opt-in real Node-RED embedding; synthetic resident, not browser/LLM evidence."""
from contextlib import closing
import http.cookiejar
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from urllib import request, error

from mantleos import studio, studio_editor, specimens, journal
from mantleos.limbs import LimbSet


@unittest.skipUnless(os.environ.get('STUDIO_MODULES') and shutil.which('node'),
                     'Owner-provisioned Node-RED absent; embedding untested')
class StudioHostTests(unittest.TestCase):
    def test_owner_selected_editor_reuses_body_and_preserves_native_automation(self):
        with tempfile.TemporaryDirectory(prefix='studio-host-') as td:
            root=Path(td); nest=root/'nest'
            studio.initialize_heart(nest,b'Synthetic host founding source\n')
            body=root/'body';specimens.fresh(body,name='Synthetic resident host persona')
            journal.from_body(body,nest/'prime.engram')
            LimbSet.create(nest/'limb-runtime',[],worker_limit=0,approved=True)
            resources=Path(studio.__file__).parent/'kpp/resources/examples/anchor-studio'
            node=shutil.which('node')
            pins=subprocess.run([node,str(resources/'editor-fixtures.cjs'),str(root)],
                                capture_output=True,text=True,timeout=20,check=True)
            selected=json.loads(pins.stdout)
            with closing(socket.socket()) as reservation:
                reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
            base=f'http://127.0.0.1:{port}'
            env={**os.environ,'STUDIO_NEST':str(nest),'STUDIO_PORT':str(port),
                 'STUDIO_PYTHON':sys.executable,'PYTHONPATH':str(Path(studio.__file__).parent.parent),
                 'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'}
            opener=request.build_opener(request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            process=None; log=None
            def api(path,value=None):
                headers={'Accept':'text/html' if value is None and path=='/' else 'application/json'}
                data=None
                if value is not None:
                    data=json.dumps(value).encode();headers['Content-Type']='application/json'
                req=request.Request(base+path,data=data,headers=headers)
                try:
                    with opener.open(req,timeout=20) as response:
                        raw=response.read();status=response.status;kind=response.headers.get('Content-Type','')
                except error.HTTPError as response:
                    with response:
                        raw=response.read();status=response.code;kind=response.headers.get('Content-Type','')
                return status,json.loads(raw) if 'application/json' in kind else raw.decode('utf8')
            def start(label):
                nonlocal process,log
                log=(root/(label+'.log')).open('w',encoding='utf8')
                process=subprocess.Popen([node,str(resources/'launcher.cjs')],env=env,stdout=log,stderr=log)
                deadline=time.monotonic()+180
                while time.monotonic()<deadline:
                    if process.poll() is not None:
                        log.flush();self.fail((root/(label+'.log')).read_text('utf8'))
                    try:
                        status,_=api('/')
                        if status==200:return
                    except (OSError,error.URLError):pass
                    time.sleep(.1)
                self.fail('Synthetic host startup timed out')
            def stop():
                nonlocal process,log
                if process and process.poll() is None:
                    try:
                        self.assertEqual(api('/studio/shutdown',{})[0],200)
                        process.wait(timeout=30)
                        self.assertEqual(process.returncode,0)
                    finally:
                        if process.poll() is None:process.kill();process.wait(timeout=10)
                if log:log.close();log=None
                process=None
            try:
                start('ordinary')
                self.assertIn('Anchor Studio',api('/')[1])
                self.assertEqual(api('/healthz')[1]['status'],'ok')
                self.assertEqual(api('/rest/settings')[0],404)
                # Real ordinary Node-RED HTTP automation, no function/effect or
                # external services. The same deployed flow survives stasis and
                # both editor activation and source-withdrawal restarts.
                flows=[{'id':'host-tab','type':'tab','label':'Synthetic host baseline'},
                    {'id':'host-in','z':'host-tab','type':'http in','url':'/qualification-ping','method':'get','upload':False,'wires':[['host-value']]},
                    {'id':'host-value','z':'host-tab','type':'change','rules':[{'t':'set','p':'payload','pt':'msg','to':'native Body alive','tot':'str'}],'wires':[['host-out']]},
                    {'id':'host-out','z':'host-tab','type':'http response','statusCode':'200','headers':{},'wires':[]}]
                self.assertEqual(api('/red/flows',flows)[0],204)
                # Node-RED acknowledges the saved revision before its
                # asynchronous runtime deployment registers the HTTP node.
                deadline=time.monotonic()+15
                ping=api('/flows/qualification-ping')
                while ping[0]==404 and time.monotonic()<deadline:
                    time.sleep(.1)
                    ping=api('/flows/qualification-ping')
                self.assertEqual(ping,(200,'native Body alive'))
                self.assertEqual(api('/studio/phase',{'active':False})[0],200)
                self.assertEqual(api('/healthz')[1]['resident_phase'],'STASIS')
                self.assertEqual(api('/flows/qualification-ping'),(200,'native Body alive'))
                stop()
                studio_editor.configure(nest,node=node,package_root=selected['packageRoot'],
                    editor_profile=selected['editorProfile'],catalog_root=selected['catalogRoot'],
                    catalog_profile=selected['catalogProfile'],reviewed=True)
                start('selected-editor')
                self.assertIn('synthetic editor host fixture',api('/')[1])
                self.assertEqual(api('/healthz')[1]['status'],'ok')
                self.assertIn('resident-panel.js',api('/')[1])
                self.assertIn('synthetic editor host fixture',api('/workflow/synthetic')[1])
                self.assertEqual(api('/flows/qualification-ping'),(200,'native Body alive'))
                resident=api('/appai/status')[1]
                self.assertEqual(resident['persona'],'Synthetic resident host persona')
                self.assertEqual(resident['context'],'RESIDENT_MEMORY')
                self.assertEqual(resident['mind_route'],'SUPERVISED')
                project_id=api('/rest/projects/personal')[1]['data']['id']
                self.assertEqual(api('/rest/credentials')[1]['scope'],'DESCRIPTORS_ONLY_NO_SECRET_DATA')
                self.assertEqual(api('/rest/credentials/for-workflow?projectId='+project_id)[1]['data'],[])
                self.assertEqual(api('/rest/tags')[1]['data'],[])
                created=api('/rest/workflows',{'name':'Durable host graph','nodes':[],'connections':{}})
                self.assertEqual(created[0],200);workflow_id=created[1]['data']['id']
                self.assertEqual(api('/rest/workflows/'+workflow_id+'/run',{})[0],501)
                message={'request_id':'host-fixture-1','user':'Remember synthetic cobalt'}
                self.assertEqual(api('/appai/conversation',message)[1]['status'],'AWAITING_MIND')
                with studio.database(nest) as db:
                    frame=json.loads(db.execute('SELECT frame FROM mind WHERE id=?',(message['request_id'],)).fetchone()[0])
                self.assertIn('Synthetic resident host persona',frame['frame']['payload']['primer']['content'])
                self.assertEqual(frame['editor_configuration_sha256'],studio_editor.private_config(nest)['sha256'])
                exact='  Synthetic cobalt retained.\n🌊  '
                result=api('/studio/mind-submit',{'request_id':message['request_id'],
                    'proposal':{'kind':'reply','reply':exact,'observation_sha256':None}})
                self.assertEqual(result[1]['status'],'COMMITTED')
                first=api('/appai/result/'+message['request_id'])[1]
                self.assertEqual(first['reply'],exact)
                self.assertEqual(api('/appai/conversation',message)[1],first)
                self.assertEqual(api('/appai/result/'+message['request_id'])[1],first)
                self.assertEqual(api('/studio/phase',{'active':False})[0],200)
                self.assertEqual(api('/appai/result/'+message['request_id'])[1]['status'],'STASIS')
                self.assertEqual(api('/flows/qualification-ping'),(200,'native Body alive'))
                stop();start('fresh-process')
                self.assertEqual(api('/appai/result/'+message['request_id'])[1],first)
                self.assertEqual(api('/rest/workflows/'+workflow_id)[1]['data']['name'],'Durable host graph')
                self.assertEqual(api('/flows/qualification-ping'),(200,'native Body alive'))
                stop()
                studio_editor.disable(nest,reviewed=True)
                start('withdrawn-editor')
                self.assertEqual(api('/rest/settings')[0],404)
                self.assertEqual(api('/flows/qualification-ping'),(200,'native Body alive'))
                self.assertEqual(api('/studio/result/'+message['request_id'])[1]['reply'],exact)
                from mantleos.studio_workflows import APPLICATION
                store=nest/'operational-workflows/workflows.sqlite'
                with closing(sqlite3.connect(store)) as db,db:db.execute('PRAGMA application_id=12345')
                try:
                    self.assertEqual(api('/healthz'),(503,{'status':'unavailable'}))
                    self.assertEqual(api('/flows/qualification-ping'),(200,'native Body alive'))
                finally:
                    with closing(sqlite3.connect(store)) as db,db:db.execute('PRAGMA application_id='+str(APPLICATION))
                self.assertEqual(api('/healthz')[1]['status'],'ok')
            finally:
                stop()


if __name__=='__main__':unittest.main()
