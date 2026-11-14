import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from mantleos import studio_project as s


class StudioProjectTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        if not (root/'src/mantleos').is_dir():root=root.parent
        recipe=json.loads((root/'src/mantleos/kpp/resources/recipes/journal-engram-design.json').read_text('utf8'))
        self.value=dict(schema=s.SCHEMA,id='Studio-Demo',recipe=recipe,layout={},unresolved=[],provenance=[],evidence=[])

    def test_recipe_handoff_uses_saved_revision_and_resolved_design(self):
        from mantleos import json_contract as contract, studio

        with tempfile.TemporaryDirectory() as td:
            nest = Path(td)
            with self.assertRaisesRegex(ValueError, 'Save a project'):
                studio.dispatch(nest, {'op': 'recipe_export'})
            project = nest / 'project.json'
            project.write_text(contract.canonical(self.value), encoding='utf-8')
            result = studio.dispatch(nest, {'op': 'recipe_export'})
            self.assertEqual(result['revision'], contract.digest(self.value))
            self.assertEqual(contract.loads(result['source']), self.value['recipe'])
            self.assertEqual(result['id'], self.value['recipe']['id'])
            apps = self.value['recipe']['anchor_design']['applications']
            self.value['unresolved'] = [{'from': apps[0]['id'], 'to': apps[1]['id']}]
            project.write_text(contract.canonical(self.value), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Resolve and save'):
                studio.dispatch(nest, {'op': 'recipe_export'})

    def test_roundtrip_is_deterministic_and_not_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.anchorstudio';b=Path(td)/'b.anchorstudio'
            s.save(self.value,a);s.save(self.value,b)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(s.load(a),self.value)
            self.assertEqual(s.inspection(s.load(a))['acceptance'],'PENDING_BAKER')

    def test_unknown_fields_and_singularities_rejected(self):
        value=copy.deepcopy(self.value);value['credentials']='secret'
        with self.assertRaises(ValueError):s.validate(value)
        self.value['recipe']['anchor_design']['applications'][0]['singularity']='changed'
        with self.assertRaises(ValueError):s.validate(self.value)

    def test_layout_and_unresolved_references_checked(self):
        self.value['layout']['missing']=[0,0]
        with self.assertRaises(ValueError):s.validate(self.value)
        self.value['layout']={};self.value['unresolved']=[{'from':'missing','to':'missing'}]
        with self.assertRaises(ValueError):s.validate(self.value)

    def test_unsafe_zip_and_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'bad.anchorstudio'
            with zipfile.ZipFile(path,'w') as z:z.writestr('../project.json','{}')
            with self.assertRaises(ValueError):s.load(path)
            with self.assertRaises(FileExistsError):s.save(self.value,path)

    def test_public_fixtures_are_bounded_data(self):
        from mantleos.studio_demo import project
        value=project();self.assertEqual(len(value['fixtures']),5)
        value['fixtures']['case_input.py']['content']='changed'
        with self.assertRaises(ValueError):s.validate(value)

    def test_flow_wires_stay_unresolved(self):
        from mantleos.studio_demo import project
        value=project();apps=value['recipe']['anchor_design']['applications']
        types={'BlackHole':'anchor-blackhole','Neutral':'anchor-neutral','WhiteHole':'anchor-whitehole'}
        nodes=[{'id':str(i),'applicationId':a['id'],'type':types[a['type']],'responsibility':a['attributes']['responsibility'],'x':100*i,'y':100,'wires':[[str(i+1)]] if i<3 else []} for i,a in enumerate(apps)]
        draft=s.from_flows(nodes,value['recipe'])
        self.assertEqual(len(draft['unresolved']),3)
        self.assertEqual(s.inspection(draft)['status'],'MAPPING_BLOCKED')
        nodes[0]['wires']=[['operational-node']]
        with self.assertRaises(ValueError):s.from_flows(nodes,value['recipe'])
