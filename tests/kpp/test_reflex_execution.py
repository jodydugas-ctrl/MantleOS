"""Executed source-bound Anchors, Baker gate, stale evidence and graph links."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from mantleos.kpp.adaptation import reflex_plan
from mantleos.kpp.core import KPPError, digest, read_json, write_json, validate_recipe
from mantleos.kpp.graph import functional_graph, coverage
from mantleos.kpp.reflex import approval_template, stage
from mantleos.kpp.scanner import scan
from mantleos.kpp.testing import run_suite, accept_tested, verify_report
from mantleos.kpp.workshop import begin, load, finish, inspection

ROOT = Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
SOURCE = ROOT / 'examples/adaptive-reflex'
SUITE = ROOT / 'examples/reflex-anchors'
RECIPE = read_json(ROOT / 'recipes/adaptive-reflex-demo.json')
REQUEST = read_json(SOURCE / 'request.json')


class ExecutedReflexTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ws = self.root / 'workspace'
        self.candidate = self.root / 'candidate'
        self.report = self.root / 'report.json'
        begin(self.ws, RECIPE, ROOT)
        rec, state = load(self.ws)
        plan = reflex_plan(ROOT, rec, state, REQUEST, SOURCE)
        approval = approval_template(plan)
        approval['baker'] = 'test-stage-review'
        stage(self.ws, REQUEST, plan, approval, SOURCE, self.candidate, ROOT)

    def execute(self, **kwargs):
        params = dict(workspace=self.ws, candidate_dir=self.candidate, suite_dir=SUITE,
                      out=self.report, execute=True,reviewed=True)
        params.update(kwargs)
        return run_suite(**params)

    def approve(self):
        self.execute()
        return accept_tested(self.ws, self.report, self.candidate, SUITE, 'test-baker')

    def test_success_does_not_auto_accept(self):
        result=self.execute()
        self.assertTrue(result['all_passed'])
        self.assertEqual([x['outcome'] for x in result['results']], ['PASS']*3)
        self.assertEqual(inspection(self.ws)['accepted'], 0)
        self.assertEqual(verify_report(read_json(self.report),self.candidate,SUITE)['fresh'], True)
        with self.assertRaisesRegex(KPPError,'unmet mandatory'): finish(self.ws)

    def test_baker_accepts_then_completion_receipt_is_source_bound(self):
        result=self.approve()
        self.assertEqual(result['kind'],'executed')
        self.assertEqual(inspection(self.ws)['accepted'],3)
        receipt=finish(self.ws)
        self.assertEqual(receipt['coverage']['accepted_anchors'],3)
        self.assertEqual({rec['kind'] for rec in receipt['accepted'].values()}, {'executed'})
        (self.candidate/'task_agent.py').write_text('x = 2\n')
        status=inspection(self.ws)
        self.assertFalse(status['completion_evidence_current'])
        self.assertEqual(status['accepted'], 0)
        with self.assertRaises(KPPError):verify_report(read_json(self.report),self.candidate,SUITE)

    def test_mutated_suite_script_invalidates_all_accepted_evidence(self):
        suite=self.root/'suite'; shutil.copytree(SUITE,suite)
        run_suite(self.ws,self.candidate,suite,self.report,execute=True,reviewed=True)
        accept_tested(self.ws,self.report,self.candidate,suite,'test-baker')
        self.assertEqual(inspection(self.ws)['accepted'],3)
        (suite/'check_original.py').write_text((suite/'check_original.py').read_text()+'# changed\n')
        self.assertEqual(inspection(self.ws)['accepted'],0)

    def test_tampered_report_invalidates_acceptance(self):
        self.approve()
        rep=read_json(self.report);rep['results'][0]['stdout_tail']='forged'
        write_json(self.report,rep)
        self.assertEqual(inspection(self.ws)['accepted'],0)

    def test_script_sha_or_exit_code_forgery_rejected(self):
        self.execute()
        report=read_json(self.report)
        report['results'][0]['script_sha256'] = '0'*64
        with self.assertRaises(KPPError):verify_report(report,self.candidate,SUITE)
        report=read_json(self.report)
        report['results'][0]['returncode']=5
        with self.assertRaises(KPPError):verify_report(report,self.candidate,SUITE)

    def test_missing_execute_gate_and_blank_baker(self):
        with self.assertRaisesRegex(KPPError,'--execute'):self.execute(execute=False)
        self.assertFalse(self.report.exists())
        self.execute()
        with self.assertRaises(KPPError):accept_tested(self.ws,self.report,self.candidate,SUITE,'')
        self.assertEqual(inspection(self.ws)['accepted'],0)

    def test_failing_anchor_report_blocks_acceptance(self):
        suite=self.root/'suite';shutil.copytree(SUITE,suite)
        script=suite/'check_reflex.py';script.write_text("raise AssertionError('fixed oracle mismatch')\n")
        obj=read_json(suite/'suite.json')
        import hashlib
        obj['cases'][1]['sha256'] = hashlib.sha256(script.read_bytes()).hexdigest()
        write_json(suite/'suite.json',obj)
        result=run_suite(self.ws,self.candidate,suite,self.report,execute=True,reviewed=True)
        self.assertFalse(result['all_passed'])
        self.assertEqual(result['results'][1]['outcome'],'FAIL')
        with self.assertRaises(KPPError):accept_tested(self.ws,self.report,self.candidate,suite,'operator')

    def test_mutated_candidate_before_execution_refused(self):
        (self.candidate/'task_agent.py').write_text('not the original\n')
        with self.assertRaises(KPPError):self.execute()
        self.assertFalse(self.report.exists())

    def test_unknown_suite_and_extra_fixture_rejected(self):
        suite=self.root/'suite';shutil.copytree(SUITE,suite)
        (suite/'rogue.py').write_text('pass\n')
        with self.assertRaisesRegex(KPPError,'unpinned files'):
            self.execute(suite_dir=suite)

    def test_test_attempt_to_change_candidate_is_detected(self):
        suite=self.root/'suite';shutil.copytree(SUITE,suite)
        script=suite/'check_reflex.py'
        script.write_text('import sys\nfrom pathlib import Path\n(Path(sys.argv[1])/"task_agent.py").write_text("evil = 1\\n")\n')
        import hashlib
        obj=read_json(suite/'suite.json');obj['cases'][1]['sha256']=hashlib.sha256(script.read_bytes()).hexdigest()
        write_json(suite/'suite.json',obj)
        result=run_suite(self.ws,self.candidate,suite,self.report,execute=True,reviewed=True)
        self.assertFalse(result['all_passed'])
        self.assertEqual(result['candidate_integrity_after'],'FAILED_OR_CHANGED')

    def test_graph_reflex_edges_and_static_attachment_are_derived(self):
        recipe, state=load(self.ws)
        graph=functional_graph(recipe,state,scan(SOURCE,depth=2))
        relations={e['kind'] for e in graph['edges']}
        self.assertTrue({'triggers-reflex','invokes-ingredient','verifies-reflex-obligation','possible-attachment-match'} <= relations)
        self.assertEqual(len([n for n in graph['nodes'] if n['kind']=='reflex']),1)

    def test_invalid_reflex_preservation_and_duplicate_rejected(self):
        for edit in ('missing', 'duplicate', 'nonmandatory'):
            with self.subTest(edit=edit):
                r=json.loads(json.dumps(RECIPE))
                if edit=='missing':r['reflexes'][0]['anchors']=['nonexistent']
                elif edit=='duplicate':r['reflexes'].append(r['reflexes'][0])
                else:
                    r['anchors'][1]['required']=False
                with self.assertRaises(KPPError):validate_recipe(r)


if __name__=='__main__':unittest.main()
