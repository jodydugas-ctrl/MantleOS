"""Exercise public CLI transport and independent GUI reporting with synthetic data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from mantleos.kpp import png
from mantleos.kpp.core import read_json, write_json

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'

class CurrentCLI(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.ws=self.root/'workspace'

    def call(self,*args):
        env={**os.environ,'PYTHONPATH':str(Path(__import__('mantleos').__file__).parent.parent)}
        result=subprocess.run([sys.executable,'-m','mantleos','kpp',*map(str,args)],cwd=ROOT,env=env,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
        return json.loads(result.stdout.decode('utf-8'))

    def test_gui_capture_compare_matrix_and_separate_review_routes(self):
        self.call('new','--recipe',ROOT/'recipes/qt-gui-coverage-demo.json','--workspace',self.ws)
        entry=read_json(ROOT/'references/synthetic-qt-inventory.json')['entries'][0]['id']
        image=self.root/'capture.png';image.write_bytes(png.encode(2,2,bytes([12,24,36,255]*4)))
        claims=self.root/'claims.json'
        write_json(claims,[{'entry_id':entry,'locator':{'region':[0,0,2,2]},'represented':True,'functional':False,'tested':False}])
        common=['--workspace',self.ws,'--capture',image,'--method','screenshot','--actor','test observer','--mode','normal','--ui-state','empty']
        reference=self.call('gui-record',*common,'--surface','reference')
        candidate=self.call('gui-record',*common,'--surface','candidate','--entries',entry,'--entry-observations',claims)
        self.assertEqual(self.call('gui-evidence','--workspace',self.ws,'--id',candidate['id'])['schema'],'kpp.gui-observation/1')
        comparison=self.call('gui-compare','--workspace',self.ws,'--reference',reference['id'],'--candidate',candidate['id'],'--actor','test observer')
        self.assertEqual(comparison['metrics']['changed_pixels'],0)
        before=self.call('gui-matrix','--workspace',self.ws)['counts']
        self.assertEqual((before['accounted_for'],before['represented'],before['functional'],before['tested'],before['accepted']),(20,1,0,0,0))
        self.call('gui-accept','--workspace',self.ws,'--anchor','gui-coverage','--id',comparison['id'],'--baker','synthetic baker','--evidence','Synthetic pixel obligation only — not behavior')
        after=self.call('gui-matrix','--workspace',self.ws)['counts']
        self.assertEqual((after['represented'],after['functional'],after['tested'],after['accepted']),(1,0,0,20))

    def test_module_activation_and_preview_transport_routes(self):
        self.call('new','--recipe',ROOT/'recipes/progressive-calculator.json','--workspace',self.ws)
        self.call('install','--workspace',self.ws,'--id','square','--source',ROOT/'previews/calculator/square.js')
        self.call('module-disable','--workspace',self.ws,'--id','square')
        self.assertEqual(self.call('status','--workspace',self.ws)['disabled_modules'],['square'])
        self.call('module-enable','--workspace',self.ws,'--id','square')
        bundle=self.root/'preview.zip';receiving=self.root/'receiving'
        self.call('preview-export','--workspace',self.ws,'--out',bundle)
        self.assertEqual(self.call('preview-import','--bundle',bundle,'--output',receiving)['execution'],'NONE')
        status=self.call('status','--workspace',receiving)
        self.assertEqual(status['accepted'],0);self.assertEqual(status['modules'],['square'])
