"""Optional techniques preserve legacy ordering and existing acceptance boundaries."""
import copy
from pathlib import Path
import tempfile
import unittest
from mantleos.kpp import core, graph, workshop, build
from mantleos.kpp.construction import construction_plan

RESOURCE=Path(core.__file__).parent/'resources'
def recipe():
    value=core.read_json(RESOURCE/'recipes/conventional-python-v4.json')
    value['construction']={'techniques':[]}
    value['anchors']=[{'id':name,'statement':'Verify '+name,'test':'Synthetic scoped check',
        'required':True,'depth':depth,'depends':deps,'area':area}
        for name,depth,deps,area in [('first',3,[],'file'),('second',1,[],'edit'),('third',1,['first'],'edit')]]
    return value

class ConstructionTests(unittest.TestCase):
    def test_no_chase_ignores_activity_depth_and_keeps_dependencies(self):
        value=recipe();core.validate_recipe(value)
        state={'recipe_hash':core.digest(value),'accepted':{}}
        self.assertEqual([r['id'] for r in graph.chase(value,state,{'edit':100})],['first','second','third'])
        value['construction']['techniques']=['chase']
        self.assertEqual(graph.chase(value,state,{'edit':100})[0]['id'],'second')
        value.pop('construction')
        self.assertEqual(construction_plan(value)['basis'],'legacy-default')
        self.assertEqual(graph.chase(value,state,{'edit':100})[0]['id'],'second')

    def test_malformed_and_legacy_declarations_fail(self):
        for declaration in [None,{},[],{'techniques':'chase'},{'techniques':['chase','chase']},
                            {'techniques':['other']},{'techniques':[],'extra':True}]:
            value=recipe();value['construction']=declaration
            with self.subTest(declaration=declaration),self.assertRaises(core.KPPError):core.validate_recipe(value)
        value=core.read_json(RESOURCE/'recipes/notepad-demo.json');pin=core.digest(value)
        self.assertEqual(construction_plan(value)['ordering'],'chase');core.validate_recipe(value)
        self.assertEqual(pin,core.digest(value))
        value['construction']={'techniques':[]}
        with self.assertRaises(core.KPPError):core.validate_recipe(value)

    def test_reports_and_actor_neutral_acceptance_and_drift(self):
        with tempfile.TemporaryDirectory() as root:
            ws=Path(root)/'ws';value=recipe();workshop.begin(ws,value,RESOURCE)
            self.assertEqual(build.step(ws)['next']['id'],'first')
            self.assertIn('Requirement order',workshop.handoff(ws))
            derived=graph.functional_graph(*workshop.load(ws))
            self.assertEqual(derived['construction']['ordering'],'requirements')
            with self.assertRaises(core.KPPError):workshop.finish(ws)
            with self.assertRaises(core.KPPError):workshop.accept(ws,'third','Synthetic evidence','collaborative-baker')
            workshop.accept(ws,'first','Synthetic attestation only','ai-baker')
            self.assertEqual(workshop.inspection(ws)['accepted'],1)
            changed=copy.deepcopy(value);changed['construction']['techniques']=['chase']
            self.assertNotEqual(core.digest(value),core.digest(changed))
            core.write_json(ws/'recipe.json',changed)
            with self.assertRaises(core.KPPError):workshop.load(ws)
