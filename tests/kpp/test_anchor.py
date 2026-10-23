"""Prove exactly what the Anchor specimens and bridge do (and do not do)."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mantleos.kpp.anchor import PRIMER, run_file, interpret, inspect_file, bridge_python
from mantleos.kpp.core import KPPError, ingredient_catalog, validate_recipe
from mantleos.kpp.workshop import begin, report_observation, inspection

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
SPECIMENS=ROOT/'specimens'/'mantleos'

class AnchorSpecimenTests(unittest.TestCase):
    def test_four_specimens_emit_literal_python(self):
        for specimen in sorted(SPECIMENS.glob('*.anchor')):
            with self.subTest(specimen=specimen.name):
                out=run_file(specimen)
                self.assertIn('if __name__ == "__main__":',out)
                compile(out,str(specimen),'exec')
                self.assertEqual(inspect_file(specimen)['effect'],'TEXT_ONLY; nothing executed')

    def test_no_partial_output_on_invalid_anchor(self):
        s=(SPECIMENS/'chase-stop.anchor').read_text(encoding='utf-8')
        for changed in [s.replace(' -01 ', ' -99 ',1),s.replace('RUN ChaseStop','RUN Imposter'),s.replace(PRIMER,'UNTRUSTED INSTRUCTIONS')]:
            with self.assertRaises(KPPError):interpret(changed)

    def test_refuse_unsafe_unicode(self):
        s=(SPECIMENS/'chase-stop.anchor').read_text(encoding='utf-8')
        s=s.replace(' -text=', ' -text="\\ud800"\nOther: Neutral -01 -00 -text=',1)
        with self.assertRaises(KPPError):interpret(s)

    def test_bridge_refuses_overwrite_and_has_no_side_effect(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'intent.py'
            receipt=bridge_python(SPECIMENS/'intent-boundary.anchor',dest)
            self.assertEqual(receipt['effect'],'PYTHON_FILE_WRITTEN; no execution or host permission granted')
            self.assertTrue(dest.is_file())
            self.assertNotIn('eval(',dest.read_text())
            with self.assertRaises(KPPError):bridge_python(SPECIMENS/'intent-boundary.anchor',dest)

    def run_script(self,script,*args,input=None,check=True):
        return subprocess.run([sys.executable,str(script),*map(str,args)],input=input,
                              text=True,capture_output=True,check=check,timeout=8)

    def test_intent_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            script=Path(d)/'boundary.py'
            bridge_python(SPECIMENS/'intent-boundary.anchor',script)
            ok=json.loads(self.run_script(script,input='{"action":"remember","payload":{"text":"hello"}}').stdout)
            no=json.loads(self.run_script(script,input='{"action":"overwrite","payload":{}}').stdout)
            self.assertTrue(ok['accepted'])
            self.assertEqual(ok['body_operation'],'memory.append')
            self.assertFalse(no['accepted'])

    def test_memory_ledger_append_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'memory.py'; data=Path(d)/'events.jsonl'
            bridge_python(SPECIMENS/'memory-ledger.anchor',p)
            self.run_script(p,'append',data,'--text','one')
            self.run_script(p,'append',data,'--text','two')
            records=json.loads(self.run_script(p,'read',data).stdout)
            self.assertEqual([x['text'] for x in records],['one','two'])
            b=data.read_text();data.write_text(b.replace('one','not-one',1))
            self.assertNotEqual(self.run_script(p,'read',data,check=False).returncode,0)

    def test_chase_stop(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'chase.py';bridge_python(SPECIMENS/'chase-stop.anchor',p)
            ok=json.loads(self.run_script(p,'--reference-ms',100,'--candidate-ms',104,'--behavior-equal','--tests-pass').stdout)
            no=json.loads(self.run_script(p,'--reference-ms',100,'--candidate-ms',106,'--behavior-equal','--tests-pass').stdout)
            self.assertEqual(ok['status'],'TARGET_REACHED_WITHIN_CHECK_SCOPE')
            self.assertEqual(no['status'],'CHASE_ACTIVE')

    def test_kernel_relative_cells(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cells.py';bridge_python(SPECIMENS/'kernel-cells.anchor',p)
            pixel=json.loads(self.run_script(p,'--kernel','pixel','--value','[1,2,255]').stdout)
            tape=json.loads(self.run_script(p,'--kernel','tape','--value','"hello"').stdout)
            self.assertEqual(pixel['payload'][2],255)
            self.assertEqual(tape['payload']['record']['text'],'hello')

    def test_pantry_pin_and_transformation_recipe(self):
        catalog=ingredient_catalog(ROOT)
        self.assertEqual(sum('specimen' in v for v in catalog.values()),4)
        recipe=validate_recipe(json.loads((ROOT/'recipes'/'portable-memory-bake.json').read_text()))
        self.assertEqual(recipe['mode'],'transformation')
        bad=json.loads(json.dumps(recipe))
        bad['transformation']['may_change'].append(bad['transformation']['preserve'][0])
        with self.assertRaises(KPPError):validate_recipe(bad)
        with tempfile.TemporaryDirectory() as d:
            ws=Path(d)/'ws'
            begin(ws,recipe,ROOT)
            self.assertFalse((ws/'app').exists(), 'Non-browser recipe should not create a fake Notepad app')
            self.assertTrue((ws/'artifacts').exists())
            report=report_observation(ws,'unplanned feature','observed after experiment')
            self.assertEqual(report['disposition'],'BAKER_REVIEW_REQUIRED; NOT_A_RECIPE_ANCHOR')
            self.assertEqual(inspection(ws)['accepted'],0)
            self.assertFalse(inspection(ws)['all_required_satisfied'])

if __name__=='__main__':unittest.main()
