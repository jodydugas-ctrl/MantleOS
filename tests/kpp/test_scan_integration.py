"""Review evidence for the previously divergent shared scanner changes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from mantleos.scan import scanner as native
from mantleos.scan.common import ScanError
from mantleos.kpp import scanner as kpp
from mantleos.kpp.core import digest, write_json


class SharedScanIntegration(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.source=self.root/'source';self.source.mkdir()
        (self.source/'code.py').write_text('raise RuntimeError("NEVER EXECUTE")\ndef operate():\n return helper()\ndef helper():\n return 2\n')
        (self.source/'form.ui').write_text('<ui><widget name="main" class="QWidget"><action name="save"/></widget></ui>')
        (self.source/'index.html').write_text('<button id="save">Save</button>')
        (self.source/'data.json').write_text('{"inert":true}')

    def test_serial_parallel_and_filter_order_are_equivalent(self):
        serial=native.scan(self.source,self.root/'serial')
        parallel=native.scan(self.source,self.root/'parallel',execution='parallel')
        explicit=native.scan(self.source,self.root/'explicit',filters=['data','code','interface','code'])
        self.assertEqual(serial['graph'],parallel['graph'])
        self.assertEqual(serial['graph'],explicit['graph'])
        self.assertFalse(serial['graph']['scope']['specimen_executed'])

    def test_barrier_proves_captured_file_extraction_overlap(self):
        barrier=Barrier(2,timeout=5);original=native.extract
        def extract(path,*args,**kwargs):
            if path in ('code.py','form.ui'):barrier.wait()
            return original(path,*args,**kwargs)
        with patch.object(native,'extract',side_effect=extract):
            value=native.scan(self.source,self.root/'parallel',execution='parallel')
        self.assertTrue(all(f['status'] not in ('ERROR','LIMIT') for f in value['graph']['files']))

    def test_filters_preserve_complete_inventory_with_explicit_filtered_states(self):
        value=native.scan(self.source,self.root/'code-only',filters=['code'])
        statuses={f['path']:f['status'] for f in value['graph']['files']}
        self.assertEqual(set(statuses),{'code.py','form.ui','index.html','data.json'})
        self.assertEqual({statuses[x] for x in ('form.ui','index.html','data.json')},{'FILTERED'})
        self.assertTrue(all(n['path']=='code.py' for n in value['graph']['nodes']))
        for opts in ({'filters':['invented']},{'execution':'swarm'}):
            with self.assertRaises(ScanError):native.scan(self.source,self.root/'invalid',**opts)

    def test_html_projection_uses_canonical_graph_and_keeps_existing_control_ids(self):
        value=kpp.scan(self.source,depth=3)
        control=next(v for v in value['nodes'].values() if v.get('id')=='save')
        self.assertEqual(control['file'],'index.html')
        self.assertIn(control['evidence_node'],{n['id'] for n in value['native_report']['graph']['nodes']})
        changed=copy.deepcopy(value);changed['html_surfaces']['index.html']['items'].clear()
        changed['sha256']=digest({k:v for k,v in changed.items() if k!='sha256'})
        with self.assertRaisesRegex(ValueError,'projection'):kpp.verify_scan(changed)

    def test_trace_cli_uses_only_its_declared_arguments(self):
        value=native.scan(self.source,self.root/'snapshot');report=self.root/'scan.json';write_json(report,value)
        env={**os.environ,'PYTHONPATH':str(Path(__import__('mantleos').__file__).parent.parent)}
        result=subprocess.run([sys.executable,'-m','mantleos','scan','trace',str(report),'operate'],
                              capture_output=True,env=env,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        self.assertIn('STATIC',result.stdout.decode())


if __name__=='__main__':unittest.main()
