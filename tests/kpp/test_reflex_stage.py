"""Constrained stage approval, pinned sources, negative checks and fixed oracles."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mantleos.kpp.adaptation import reflex_plan
from mantleos.kpp.core import KPPError, digest, read_json, write_json
from mantleos.kpp.reflex import audit, stage, approval_template
from mantleos.kpp.workshop import begin, load

ROOT = Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
SOURCE = ROOT / 'examples/adaptive-reflex'
REQUEST = read_json(SOURCE / 'request.json')
RECIPE = read_json(ROOT / 'recipes/adaptive-reflex-demo.json')


def approval_for(plan):
    c = plan['tentative_point']
    return {'schema':'kpp.reflex-approval/1', 'intent':'stage-adapter-only',
            'plan_sha256':digest(plan), 'source_sha256':c['source_sha256'],
            'candidate_source_node':c['source_node'], 'baker':'operator-review'}


class ReflexStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ws = self.root / 'ws'
        begin(self.ws, RECIPE, ROOT)
        recipe, state = load(self.ws)
        self.plan = reflex_plan(ROOT, recipe, state, REQUEST, SOURCE)
        self.approval = approval_for(self.plan)
        self.target = self.root / 'candidate'

    def stage(self, **overrides):
        params = dict(workspace=self.ws, request=REQUEST, plan=self.plan,
                      approval=self.approval, source_dir=SOURCE, output_dir=self.target)
        params.update(overrides)
        return stage(**params)

    def test_stage_preserves_original_bytes_and_pins(self):
        original = {p.name:p.read_bytes() for p in SOURCE.glob('*.py')}
        output = self.stage()
        self.assertEqual(output['status'],'STAGED_UNVERIFIED')
        self.assertEqual(output['anchor_verification'],'NONE')
        self.assertEqual(audit(self.target)['integrity'],'PASS')
        m = read_json(self.target / 'kpp-reflex-stage.json')
        self.assertEqual(m['required_anchor_ids'], REQUEST['anchors'])
        self.assertEqual(m['anchor_execution'],'NOT_RUN')
        self.assertEqual(m['approval_sha256'],digest(self.approval))
        for filename, data in original.items():
            self.assertEqual((self.target/filename).read_bytes(), data)
            self.assertEqual((SOURCE/filename).read_bytes(), data)
        self.assertIn(b'def run_with_reflex', (self.target/'kpp_reflex_adapter.py').read_bytes())

    def test_generated_adapter_fixed_outputs_reflex_absence_and_failures(self):
        self.stage()
        script = '''from task_agent import TaskAgent,run_command
from kpp_reflex_adapter import run_with_reflex
from continuity import Continuity
baseline, integrated = TaskAgent(), TaskAgent()
organ=Continuity()
cases=[('add','tea',{'ok': True,'message':'Added: tea'}),
       ('unknown',None,{'ok':False,'message':'Unknown or invalid command'}),
       ('list',None,{'ok':True,'message':['tea']})]
for cmd,value,expected in cases:
    assert run_command(baseline,cmd,value)==expected
    assert run_with_reflex(integrated,cmd,value,organ=organ)==expected
assert [i['command'] for i in organ.recall()]==['add','list']
no_organ=TaskAgent()
assert run_with_reflex(no_organ,'add','tea')=={'ok':True,'message':'Added: tea'}
assert run_with_reflex(no_organ,'list')=={'ok':True,'message':['tea']}
class RaisingOrgan:
    def on_success(self,*args,**kwargs): raise RuntimeError('organ down')
assert run_with_reflex(TaskAgent(),'add','tea',organ=RaisingOrgan())=={'ok':True,'message':'Added: tea'}
class MutatingOrgan:
    def on_success(self,result,*args,**kwargs): result['message']='bad'
assert run_with_reflex(TaskAgent(),'add','tea',organ=MutatingOrgan())=={'ok':True,'message':'Added: tea'}
print('PASS staged fixed-oracle, reflex, optional-absent, failures')
'''
        out = subprocess.run([sys.executable, '-c', script], cwd=self.target,
                             capture_output=True, text=True, timeout=15)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('PASS staged',out.stdout)
        # Imported Python code writes a __pycache__; audit is meant for the
        # freshly staged candidate, not a candidate after runtime execution.

    def test_changed_source_is_rejected_without_output(self):
        src = self.root / 'source'; src.mkdir()
        for p in SOURCE.glob('*.py'):
            (src / p.name).write_bytes(p.read_bytes())
        recipe,state=load(self.ws)
        new_plan = reflex_plan(ROOT,recipe,state,REQUEST,src)
        approval = approval_for(new_plan)
        (src / 'task_agent.py').write_text('def run_command(): return True\n')
        with self.assertRaisesRegex(KPPError,'Saved proposal does not match'):
            self.stage(plan=new_plan, approval=approval, source_dir=src)
        self.assertFalse(self.target.exists())

    def test_approval_template_requires_real_baker_entry(self):
        blank = approval_template(self.plan)
        self.assertEqual(blank['baker'], '')
        with self.assertRaises(KPPError):self.stage(approval=blank)
        blank['baker'] = 'reviewed person'
        self.assertEqual(self.stage(approval=blank)['status'],'STAGED_UNVERIFIED')

    def test_forged_plan_rejected_even_if_self_consistently_approved(self):
        altered = json.loads(json.dumps(self.plan))
        altered['tentative_point']['function'] = 'not_the_actual_function'
        with self.assertRaisesRegex(KPPError,'freshly recomputed'):
            self.stage(plan=altered, approval=approval_for(altered))
        self.assertFalse(self.target.exists())

    def test_wrong_approval_plan_node_source_or_intent(self):
        for key,value in [('plan_sha256','0'*64),('candidate_source_node','wrong'),
                          ('source_sha256','0'*64),('intent','execute-without-consent'),('baker','')]:
            with self.subTest(key=key):
                bad = dict(self.approval); bad[key]=value
                with self.assertRaises(KPPError):self.stage(approval=bad)
                self.assertFalse(self.target.exists())

    def test_wrong_request_or_workspace_rejected(self):
        bad = dict(REQUEST);bad['capability']='Something different'
        with self.assertRaises(KPPError):self.stage(request=bad)
        recipe=read_json(self.ws / 'recipe.json');recipe['goal']='tamper'
        write_json(self.ws / 'recipe.json',recipe)
        with self.assertRaises(KPPError):self.stage()

    def test_ambiguous_and_unsupported_timing_refused(self):
        plan = dict(self.plan);plan['decision']='AMBIGUOUS_REVIEW_MANUALLY'
        with self.assertRaisesRegex(KPPError,'unambiguous'):
            self.stage(plan=plan,approval=approval_for(plan))
        new_req = json.loads(json.dumps(REQUEST));new_req['trigger']['timing']='before-call'
        recipe,state=load(self.ws)
        plan = reflex_plan(ROOT,recipe,state,new_req,SOURCE)
        with self.assertRaisesRegex(KPPError,'Only after-success'):
            self.stage(request=new_req,plan=plan,approval=approval_for(plan))

    def test_only_top_level_undecorated_functions_staged(self):
        for body in [
            'class Wrap:\n    def run_command(self): return {"ok":True}\n',
            '@staticmethod\ndef run_command(): return {"ok":True}\n',
            'def run_command(organ): return {"ok":True}\n',
            'def run_command():\n    yield {"ok":True}\n',
        ]:
            with self.subTest(body=body):
                src=self.root/'fake';src.mkdir(exist_ok=True)
                (src/'body.py').write_text(body)
                recipe,state=load(self.ws)
                plan=reflex_plan(ROOT,recipe,state,REQUEST,src)
                # A method is a scanner false-positive; fail rather than patch.
                if plan['tentative_point'] is None:
                    continue
                with self.assertRaises(KPPError):
                    self.stage(source_dir=src, plan=plan, approval=approval_for(plan))
                (src/'body.py').unlink()

    def test_original_exception_is_not_intercepted_and_no_organ_event(self):
        src=self.root/'raising'; src.mkdir()
        (src/'task_agent.py').write_text('def run_command(value):\n    if value == "fail": raise ValueError("original error")\n    return {"ok": True, "message": value}\n')
        recipe,state=load(self.ws)
        proposed=reflex_plan(ROOT,recipe,state,REQUEST,src)
        self.stage(source_dir=src,plan=proposed,approval=approval_for(proposed))
        script="from kpp_reflex_adapter import run_with_reflex\nclass Count:\n    calls=0\n    def on_success(self,*args,**kwargs):self.calls+=1\norgan=Count()\ntry: run_with_reflex('fail',organ=organ)\nexcept ValueError as exc:assert str(exc)=='original error'\nelse:raise AssertionError('Original exception swallowed')\nassert organ.calls==0\nassert run_with_reflex('yes',organ=organ)=={'ok':True,'message':'yes'}\nassert organ.calls==1\n"
        out=subprocess.run([sys.executable,'-c',script],cwd=self.target,capture_output=True,text=True,timeout=15)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)

    def test_reject_output_inside_source_or_existing_destination(self):
        with self.assertRaisesRegex(KPPError,'separate unused'):
            self.stage(output_dir=SOURCE/'staged')
        self.target.mkdir()
        with self.assertRaisesRegex(KPPError,'must not exist'):
            self.stage()

    def test_audit_detects_mutation_extra_and_symlink(self):
        self.stage()
        (self.target / 'task_agent.py').write_text('tampered\n')
        with self.assertRaisesRegex(KPPError,'hash mismatch'):audit(self.target)
        (self.target / 'task_agent.py').write_bytes((SOURCE/'task_agent.py').read_bytes())
        (self.target / 'extra.py').write_text('unexpected')
        with self.assertRaisesRegex(KPPError,'inventory differs'):audit(self.target)
        (self.target / 'extra.py').unlink()
        try:
            (self.target / 'link.py').symlink_to(self.target / 'task_agent.py')
        except (OSError,NotImplementedError):
            self.skipTest('Host does not permit creating symlinks')
        with self.assertRaisesRegex(KPPError,'Symlinks'):audit(self.target)

    def test_cli_staging_path(self):
        plan_file = self.root/'plan.json';approval_file=self.root/'approval.json'
        write_json(plan_file,self.plan);write_json(approval_file,self.approval)
        env={**os.environ, 'PYTHONPATH':str(Path(__import__('mantleos').__file__).parent.parent)}
        def cli(*args):
            return subprocess.run([sys.executable, '-m','mantleos','kpp',*args], cwd=ROOT, env=env,
                                  capture_output=True,text=True,timeout=20)
        result=cli('reflex-stage','--workspace',str(self.ws),'--request',str(SOURCE/'request.json'),
                   '--plan',str(plan_file),'--approval',str(approval_file),'--source',str(SOURCE),
                   '--output',str(self.target))
        self.assertEqual(result.returncode,0,result.stderr)
        audited=cli('reflex-audit','--candidate',str(self.target))
        self.assertEqual(audited.returncode,0,audited.stderr)
        self.assertEqual(json.loads(audited.stdout)['integrity'],'PASS')

if __name__=='__main__': unittest.main()
