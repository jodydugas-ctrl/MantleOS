"""Independent stage evidence: accounting never promotes appearance, behavior or review."""
import copy
from pathlib import Path
import shutil
import tempfile
import unittest

from mantleos.kpp.core import KPPError, digest, read_json, write_json
from mantleos.kpp import png
from mantleos.kpp.workshop import begin, accept, inspection
from mantleos.kpp.conformance import record_capture, coverage_matrix

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
RECIPE=read_json(ROOT/'recipes/qt-gui-coverage-demo.json')


class IndependentGUIMatrix(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.ws=self.root/'workspace';begin(self.ws,RECIPE,ROOT)
        self.capture=self.root/'capture.png';self.capture.write_bytes(png.encode(10,10,bytes([20,30,40,255]*100)))
        self.ids=[entry['id'] for entry in read_json(ROOT/'references/synthetic-qt-inventory.json')['entries']]

    def record(self,ids,flags,method='runtime',state='main-window',observed='expected'):
        entries=[{'entry_id':entry_id,'locator':{'region':[0,0,5,5]},
                  'represented':values[0],'functional':values[1],'tested':values[2]} for entry_id,values in zip(ids,flags)]
        return record_capture(self.ws,self.capture,'candidate',method,'synthetic-observer','normal',state,ids,
                              'exercise selected control' if method=='runtime' else None,
                              'expected' if method=='runtime' else None,
                              observed if method=='runtime' else None,entries)

    def test_accounting_is_100_percent_with_no_implied_presence_behavior_or_acceptance(self):
        matrix=coverage_matrix(self.ws)
        self.assertEqual(matrix['counts'],{'discovered':20,'accounted_for':20,'represented':0,'functional':0,'tested':0,'accepted':0,'excluded':0})
        self.assertEqual(matrix['percent_of_discovered']['accounted_for'],100)
        self.assertEqual(matrix['percent_of_discovered']['represented'],0)

    def test_independent_counts_do_not_promote_other_stages(self):
        self.record(self.ids[:3],[(True,False,False),(True,True,False),(False,False,True)])
        counts=coverage_matrix(self.ws)['counts']
        self.assertEqual(counts['represented'],2)
        self.assertEqual(counts['functional'],1)
        self.assertEqual(counts['tested'],1)
        self.assertEqual(counts['accepted'],0)

    def test_screenshot_can_support_presence_but_not_behavior_or_testing(self):
        self.record(self.ids[:1],[(True,False,False)],method='screenshot')
        self.assertEqual(coverage_matrix(self.ws)['counts']['represented'],1)
        for flags in ([(True,True,False)],[(True,False,True)]):
            with self.assertRaisesRegex(KPPError,'screenshot cannot'):self.record(self.ids[:1],flags,method='screenshot')

    def test_exercised_failed_behavior_counts_as_tested_without_acceptance(self):
        result=self.record(self.ids[:1],[(True,False,True)],observed='failed')
        matrix=coverage_matrix(self.ws)
        self.assertEqual(matrix['counts']['tested'],1)
        self.assertFalse(matrix['rows'][0]['tested']['observations'][0]['interaction_matches'])
        self.assertEqual(matrix['counts']['accepted'],0)
        with self.assertRaisesRegex(KPPError,'failed recorded'):accept(self.ws,'gui-coverage','review','test-baker',kind='gui-reviewed',evidence_id=result['id'])

    def test_shared_anchor_acceptance_is_an_obligation_only(self):
        accept(self.ws,'gui-coverage','Synthetic declaration-audit obligation only','test-baker')
        matrix=coverage_matrix(self.ws)
        self.assertEqual(matrix['counts']['accepted'],20)
        self.assertEqual(matrix['counts']['represented'],0)
        self.assertEqual(matrix['counts']['functional'],0)
        self.assertEqual(matrix['counts']['tested'],0)

    def test_conflicting_observations_in_same_context_do_not_claim_presence(self):
        self.record(self.ids[:1],[(True,False,False)])
        self.record(self.ids[:1],[(False,False,False)])
        matrix=coverage_matrix(self.ws)
        self.assertEqual(matrix['counts']['represented'],0)
        self.assertTrue(matrix['rows'][0]['represented']['conflicted'])

    def test_conditional_presence_keeps_explicit_contexts(self):
        self.record(self.ids[:1],[(True,False,False)],state='menu-open')
        self.record(self.ids[:1],[(False,False,False)],state='menu-closed')
        matrix=coverage_matrix(self.ws)
        self.assertEqual(matrix['counts']['represented'],1)
        self.assertFalse(matrix['rows'][0]['represented']['conflicted'])
        self.assertEqual(len(matrix['rows'][0]['represented']['observations']),2)

    def test_capture_tamper_removes_stage_support(self):
        result=self.record(self.ids[:1],[(True,True,True)])
        (self.ws/result['capture']['path']).write_bytes(b'tampered')
        matrix=coverage_matrix(self.ws)
        self.assertEqual(matrix['counts']['represented'],0)
        self.assertEqual(matrix['counts']['functional'],0)
        self.assertEqual(matrix['counts']['tested'],0)
        self.assertEqual(len(matrix['stale_evidence']),1)

    def test_exclusion_reason_remains_visible_without_automatic_stage_support(self):
        repo=self.root/'repo'
        for folder in ('pantry','specimens','references'):shutil.copytree(ROOT/folder,repo/folder)
        inventory=read_json(repo/'references/synthetic-qt-inventory.json')
        entry=inventory['entries'][0];entry['disposition']='excluded';entry['anchor_ids']=[]
        entry['scope_approval']={'baker':'synthetic-test-baker','evidence':'Explicit synthetic fixture scope exclusion'}
        write_json(repo/'references/synthetic-qt-inventory.json',inventory)
        recipe=copy.deepcopy(RECIPE);recipe['reference_gui']['inventory']['sha256']=digest(inventory)
        other=self.root/'excluded-workspace';begin(other,recipe,repo)
        matrix=coverage_matrix(other)
        self.assertEqual(matrix['counts']['accounted_for'],20)
        self.assertEqual(matrix['counts']['excluded'],1)
        self.assertEqual(matrix['rows'][0]['excluded']['reason'],'Explicit synthetic fixture scope exclusion')
        self.assertFalse(matrix['rows'][0]['accepted']['supported'])
        self.assertEqual(inspection(other)['gui_matrix']['counts'],matrix['counts'])

    def test_locator_must_identify_a_bounded_capture_region(self):
        claims=[{'entry_id':self.ids[0],'locator':{'region':[0,0,20,20]},'represented':True,'functional':False,'tested':False}]
        with self.assertRaisesRegex(KPPError,'outside'):record_capture(self.ws,self.capture,'candidate','screenshot','actor','normal','state',self.ids[:1],entry_observations=claims)


if __name__=='__main__':unittest.main()
