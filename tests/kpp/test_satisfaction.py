import copy
import json
import tempfile
import unittest
from pathlib import Path

from mantleos.kpp import satisfaction as s
from mantleos.kpp.core import digest, write_json, KPPError
from mantleos.kpp.workshop import begin, load, accept, finish
from mantleos.kpp.testing import accept_tested, evidence_current
from mantleos.kpp.build import step, run
from mantleos.anchor_design import render_contract, journal_design


class SatisfactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        repo = Path(__file__).resolve().parents[1]
        if not (repo / 'src/mantleos').is_dir():
            repo = repo.parent
        if not (repo / 'recipes').exists():
            repo = repo / 'src/mantleos/kpp/resources'
        self.repo = repo
        self.recipe = json.loads((repo / 'recipes/conventional-python-v4.json').read_text('utf8'))
        self.recipe['id'] = 'cumulative-test'
        self.recipe['anchors'] = [dict(id=n, statement=n, test='Check '+n, required=True, depth=i+1,
                                      depends=[] if n in ('a','b') else ['a','b']) for i,n in enumerate('abc')]
        self.ws = self.root/'workspace'
        begin(self.ws, self.recipe, repo)
        self.candidate = self.root/'candidate'; self.candidate.mkdir()
        self.data = self.candidate/'value.json'; write_json(self.data, dict(a=True,b=True,c=True,deep=True))
        self.suite = self.root/'suite'; self.suite.mkdir()
        cases = []
        for name, aid in [('a','a'),('deep','a'),('b','b'),('c','c')]:
            (self.suite/(name+'.py')).write_text('import json,sys\nfrom pathlib import Path\nassert json.loads((Path(sys.argv[1])/"value.json").read_text())["'+name+'"]\n')
            cases.append(dict(id=name, obligations=[aid], script=name+'.py', relationship='State consequence '+name,requires=[]))
        self.spec = dict(schema=s.SUITE,recipe_sha256=digest(self.recipe),cases=cases)
        write_json(self.suite/'suite.json',self.spec)
        self.context=self.root/'context.json';write_json(self.context,dict(capabilities={}))
        s.start(self.ws,self.candidate,self.suite,self.context,reviewed=True)

    def execute(self, **kw):
        return s.test(self.ws,execute=True,reviewed=True,**kw)

    def test_cumulative_regression_repair_and_baker(self):
        self.assertEqual(s.plan(self.ws)['targets'],['a'])
        self.assertEqual(s.plan(self.ws)['status'],'PENDING')
        a=self.execute();self.assertTrue(a['all_passed'])
        self.assertEqual(s.plan(self.ws)['status'],'PENDING')
        self.assertEqual(load(self.ws)[1]['accepted'],{})
        write_json(self.data,dict(a=True,b=True,c=True,deep=False))
        self.assertEqual(s.plan(self.ws)['status'],'STALE')
        fail=self.execute();self.assertFalse(fail['all_passed'])
        self.assertEqual([(x['id'],x['outcome']) for x in fail['results']],[('a','PASS'),('deep','FAIL'),('b','PASS')])
        self.assertEqual(s.plan(self.ws)['prior'],['a'])
        self.assertEqual(s.plan(self.ws)['status'],'FAILED')
        write_json(self.data,dict(a=True,b=True,c=True,deep=True))
        self.assertEqual(s.plan(self.ws)['status'],'STALE')
        self.assertTrue(self.execute()['all_passed'])
        final=self.execute();self.assertEqual(final['verified'],['a','b','c'])
        self.assertEqual(step(self.ws)['decision'],'AWAITING_REVIEW')
        accept_tested(self.ws,final['report_path'],self.candidate,self.suite,'Synthetic Baker')
        self.assertTrue(all(evidence_current(r) for r in load(self.ws)[1]['accepted'].values()))
        finish(self.ws)
        self.assertEqual(step(self.ws)["decision"],"COMPLETE")

    def test_batch_atomic_and_dependencies(self):
        p=s.plan(self.ws,32);self.assertEqual(p['targets'],['a','b'])
        write_json(self.data,dict(a=True,b=False,c=True,deep=True))
        self.assertFalse(self.execute(batch_size=2)['all_passed'])
        self.assertEqual(s.plan(self.ws)['prior'],[])
        self.assertEqual(s.plan(self.ws)['status'],'FAILED')
        write_json(self.data,dict(a=True,b=True,c=True,deep=True))
        self.assertEqual(s.plan(self.ws)['status'],'STALE')
        self.execute(batch_size=2)
        self.assertEqual(s.plan(self.ws)['targets'],['c'])

    def test_manual_acceptance_cannot_bypass_gate(self):
        for aid in 'abc':accept(self.ws,aid,'manual','Baker')
        with self.assertRaises(KPPError):finish(self.ws)

    def test_suite_change_blocks(self):
        self.execute()
        (self.suite/'deep.py').write_text('pass\n')
        with self.assertRaises(KPPError):s.plan(self.ws)

    def test_context_change_blocks(self):
        write_json(self.context,dict(capabilities={'print':True}))
        with self.assertRaises(KPPError):s.plan(self.ws)

    def test_readonly_determinism_and_restart(self):
        before=(self.ws/'state.json').read_bytes()
        self.assertEqual(s.plan(self.ws),s.plan(self.ws))
        self.assertEqual(before,(self.ws/'state.json').read_bytes())
        self.execute();self.assertEqual(s.plan(self.ws)['targets'],['b'])

    def test_no_execution_without_review(self):
        with self.assertRaises(KPPError):s.test(self.ws,execute=True)

    def test_failed_latest_and_changed_candidate_reject_release(self):
        self.execute()
        write_json(self.data,dict(a=False,b=True,c=True,deep=True))
        with self.assertRaises(KPPError):s.check(self.ws)
        self.execute()
        with self.assertRaises(KPPError):s.check(self.ws)

    def test_missing_evidence_and_tampered_history(self):
        r=self.execute();Path(r['report_path']).write_text('{}')
        with self.assertRaises(KPPError):s.plan(self.ws)

    def test_preview_before_refinement(self):
        calls=[]
        result=run(self.ws,open_preview=lambda p: calls.append('preview') or {'status':'OPENED'},
                   refine=lambda p: calls.append('refine') or 'BLOCKED')
        self.assertEqual(calls,['preview','refine']);self.assertEqual(result['status'],'BLOCKED')

    def test_missing_capability_is_blocked(self):
        spec=copy.deepcopy(self.spec);spec['cases'][0]['requires']=['print']
        write_json(self.suite/'suite.json',spec)
        other=self.root/'other';begin(other,self.recipe,self.repo)
        s.start(other,self.candidate,self.suite,self.context,reviewed=True)
        self.assertEqual(s.plan(other)['status'],'BLOCKED')
        with self.assertRaises(KPPError):s.test(other,execute=True,reviewed=True)

    def test_missing_mandatory_case_rejected(self):
        spec=copy.deepcopy(self.spec);spec['cases']=[c for c in spec['cases'] if c['id']!='c']
        write_json(self.suite/'suite.json',spec)
        with self.assertRaises(KPPError):s.suite_spec(self.suite,self.recipe)

    def test_test_mutation_cannot_pass_integrity(self):
        script=self.suite/'a.py';script.write_text('import sys\nfrom pathlib import Path\n(Path(sys.argv[1])/"mutation").write_text("changed")\n')
        other=self.root/'other';begin(other,self.recipe,self.repo)
        s.start(other,self.candidate,self.suite,self.context,reviewed=True)
        r=s.test(other,execute=True,reviewed=True)
        self.assertFalse(r['all_passed']);self.assertFalse(r['candidate_integrity_after'])

    def test_unreferenced_artifact_not_adopted(self):
        write_json(self.ws/'artifacts/satisfaction/unreferenced.json',{'all_passed':True})
        self.assertEqual(s.plan(self.ws)['prior'],[])

    def test_many_applications_are_supported(self):
        from mantleos import anchors,anchor_design
        design=dict(schema=anchor_design.SCHEMA,id='many',purpose='No four application rule',
                    applications=[anchors.application('N-'+str(i),definition_id='Neutral',attributes={'responsibility':'Own state '+str(i)}) for i in range(12)],
                    flows=[],state=[dict(id='s-'+str(i),owner='N-'+str(i)) for i in range(12)],effects=[])
        self.assertEqual(len(anchor_design.validate(design)['applications']),12)

    def test_full_contract_deterministic(self):
        recipe=copy.deepcopy(self.recipe);recipe['anchor_design']=journal_design()
        for a in recipe['anchors']:a['design_anchors']=[x['id'] for x in recipe['anchor_design']['applications']]
        text=render_contract(recipe)
        self.assertEqual(text,render_contract(recipe))
        for a in recipe['anchors']:self.assertIn(a['test'],text)
        self.assertIn('DESIGN CONTRACT ONLY',text)


if __name__ == '__main__':unittest.main()
