"""Fixed synthetic Qt oracles, pinned coverage, and refusal of silent scope changes."""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from mantleos.kpp.core import KPPError, digest, read_json, validate_recipe, write_json
from mantleos.kpp.gui import scan_qt, coverage, read_inventory, validate_inventory
from mantleos.kpp.graph import functional_graph, coverage as graph_coverage
from mantleos.kpp.workshop import begin, load, accept, finish, inspection

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
RECIPE=read_json(ROOT/'recipes/qt-gui-coverage-demo.json')


class GUIContracts(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.repo=self.root/'repo'
        for folder in ('pantry','specimens','references'):
            shutil.copytree(ROOT/folder,self.repo/folder)
        self.recipe=copy.deepcopy(RECIPE)
        self.inventory=read_json(self.repo/'references/synthetic-qt-inventory.json')
        self.ws=self.root/'workspace'

    def repin(self):
        self.recipe['reference_gui']['inventory']['sha256']=digest(self.inventory)
        write_json(self.repo/'references/synthetic-qt-inventory.json',self.inventory)

    def test_fixed_static_counts_shortcuts_placements_and_connections(self):
        obj=scan_qt(self.repo/'references/synthetic-qt','synthetic-qt-editor')
        report=coverage(obj)
        self.assertEqual(report['observed_entries'],20)
        self.assertEqual(report['by_kind'],{'action':3,'action-placement':5,'connection':2,'tab-order':1,'widget':9})
        self.assertEqual(report['by_disposition'],{'required':20})
        self.assertEqual(len(report['unaccounted']),20)
        self.assertTrue(any(e['shortcut']=='Ctrl+O' for e in obj['entries']))
        self.assertTrue(any(e['declaration'].get('slot')=='clear()' for e in obj['entries']))
        self.assertEqual(report['visual_conformance'],'NOT_MEASURED')
        self.assertEqual(report['runtime_behavior'],'NOT_OBSERVED')
        self.assertEqual(obj['source']['revision'],digest(obj['source']['files']))

    def test_deterministic_nonexecuting_scan(self):
        source=self.repo/'references/synthetic-qt'
        before={p.name:p.read_bytes() for p in source.iterdir()}
        self.assertEqual(scan_qt(source,'fixture'),scan_qt(source,'fixture'))
        self.assertEqual(before,{p.name:p.read_bytes() for p in source.iterdir()})
        self.assertFalse((source/'__pycache__').exists())

    def test_gui_contract_is_optional_but_old_recipe_schema_is_rejected(self):
        validate_recipe(read_json(ROOT/'recipes/progressive-calculator.json'))
        self.recipe['schema']='kpp.recipe/1'
        with self.assertRaisesRegex(KPPError,'Unsupported recipe'):validate_recipe(self.recipe)

    def test_contract_requires_pinned_target_and_mandatory_coverage_anchor(self):
        for field,value in [('source',''),('reference_version','master')]:
            recipe=copy.deepcopy(self.recipe);recipe['target'][field]=value
            with self.subTest(field=field),self.assertRaises(KPPError):validate_recipe(recipe)
        self.recipe['anchors'][0]['required']=False
        with self.assertRaisesRegex(KPPError,'mandatory'):validate_recipe(self.recipe)

    def test_inventory_path_escape_refused_before_workspace_creation(self):
        self.recipe['reference_gui']['inventory']['path']='references/../secret.json'
        with self.assertRaisesRegex(KPPError,'safe relative'):begin(self.ws,self.recipe,self.repo)
        self.assertFalse(self.ws.exists())

    def test_missing_inventory_has_no_partial_workspace(self):
        (self.repo/'references/synthetic-qt-inventory.json').unlink()
        with self.assertRaisesRegex(KPPError,'Missing'):begin(self.ws,self.recipe,self.repo)
        self.assertFalse(self.ws.exists())

    def test_inventory_changed_without_repin_is_refused(self):
        self.inventory['entries'][0]['disposition']='deferred'
        write_json(self.repo/'references/synthetic-qt-inventory.json',self.inventory)
        with self.assertRaisesRegex(KPPError,'pin mismatch'):begin(self.ws,self.recipe,self.repo)

    def test_omission_refused_even_when_inventory_is_rehashed(self):
        self.inventory['entries'].pop();self.repin()
        with self.assertRaisesRegex(KPPError,'omitted'):begin(self.ws,self.recipe,self.repo)

    def test_declared_label_rewrite_cannot_change_reference(self):
        self.inventory['entries'][0]['label']='Different target';self.repin()
        with self.assertRaisesRegex(KPPError,'changed discovered'):read_inventory(self.recipe,self.repo)

    def test_changed_source_bytes_require_recipe_revision(self):
        path=self.repo/'references/synthetic-qt/MainWindow.ui'
        path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaisesRegex(KPPError,'source bytes changed'):begin(self.ws,self.recipe,self.repo)

    def test_source_identity_mismatch_is_refused(self):
        self.recipe['target']['source']='other'
        with self.assertRaisesRegex(KPPError,'source pins disagree'):begin(self.ws,self.recipe,self.repo)

    def test_unknown_and_optional_anchor_links_are_refused(self):
        self.inventory['entries'][0]['anchor_ids']=['not-in-recipe'];self.repin()
        with self.assertRaisesRegex(KPPError,'mandatory Anchors'):begin(self.ws,self.recipe,self.repo)

    def test_status_never_supplies_acceptance(self):
        self.inventory['entries'][0]['status']='accepted';self.repin()
        with self.assertRaisesRegex(KPPError,'acceptance cannot'):begin(self.ws,self.recipe,self.repo)

    def test_unknowns_cannot_be_silently_erased(self):
        self.inventory['uninspected']=[];self.repin()
        with self.assertRaisesRegex(KPPError,'uninspected runtime'):begin(self.ws,self.recipe,self.repo)

    def test_exclusion_requires_scope_attestation(self):
        self.inventory['entries'][0]['disposition']='excluded';self.repin()
        with self.assertRaisesRegex(KPPError,'Baker scope'):begin(self.ws,self.recipe,self.repo)

    def test_deferred_without_obligation_cannot_be_accepted_or_completed(self):
        entry=self.inventory['entries'][0];entry['disposition']='deferred';entry['anchor_ids']=[];self.repin()
        begin(self.ws,self.recipe,self.repo)
        self.assertEqual(inspection(self.ws)['reference_gui']['unaccounted'],[entry['id']])
        with self.assertRaisesRegex(KPPError,'unaccounted'):accept(self.ws,'gui-coverage','review','test-baker')
        with self.assertRaisesRegex(KPPError,'unmet mandatory'):finish(self.ws)

    def test_reviewed_scope_exclusion_is_visible_without_acceptance(self):
        entry=self.inventory['entries'][0];entry['disposition']='excluded';entry['anchor_ids']=[]
        entry['scope_approval']={'baker':'synthetic-test-review','evidence':'Fixture scope exclusion for test only'};self.repin()
        begin(self.ws,self.recipe,self.repo)
        report=inspection(self.ws)['reference_gui']
        self.assertTrue(report['accounted_for'])
        self.assertEqual(len(report['scope_exclusions']),1)
        self.assertEqual(inspection(self.ws)['accepted'],0)

    def test_one_graph_and_manual_acceptance_keep_unknowns_and_no_parity_claim(self):
        begin(self.ws,self.recipe,self.repo)
        recipe,state=load(self.ws)
        graph=functional_graph(recipe,state)
        self.assertEqual(len([n for n in graph['nodes'] if n['kind']=='gui-observation']),20)
        self.assertEqual(len([e for e in graph['edges'] if e['kind']=='accounts-for-gui']),20)
        self.assertEqual(graph_coverage(recipe,state)['accepted_anchors'],0)
        accept(self.ws,'gui-coverage','Synthetic fixture declaration audit only','test-baker')
        result=finish(self.ws)
        self.assertEqual(result['coverage']['reference_gui']['unaccepted_entries'],[])
        self.assertTrue(result['coverage']['reference_gui']['uninspected'])
        self.assertEqual(result['coverage']['reference_gui']['visual_conformance'],'NOT_MEASURED')

    def test_workspace_snapshot_tampering_refused(self):
        begin(self.ws,self.recipe,self.repo)
        state=read_json(self.ws/'state.json');state['gui_inventory']['entries'].pop();write_json(self.ws/'state.json',state)
        with self.assertRaisesRegex(KPPError,'pin mismatch'):load(self.ws)

    def test_xml_entities_utf16_entities_and_malformed_input_refused(self):
        source=self.root/'xml';source.mkdir();path=source/'bad.ui'
        dtd='<!DOCTYPE ui [<!ENTITY hidden "value">]><ui><widget name="w" class="QWidget"/></ui>'
        for content in (dtd.encode(),dtd.encode('utf-16'),b'<ui><widget>'):
            path.write_bytes(content)
            with self.subTest(content=content[:20]),self.assertRaises(KPPError):scan_qt(source,'fixture')

    def test_oversized_source_and_empty_roots_refused(self):
        source=self.root/'xml';source.mkdir()
        with self.assertRaisesRegex(KPPError,'requires .ui'):scan_qt(source,'fixture')
        (source/'large.ui').write_bytes(b'x'*2_000_001)
        with self.assertRaisesRegex(KPPError,'byte budget'):scan_qt(source,'fixture')

    def test_duplicate_ids_and_unknown_schema_refused(self):
        self.inventory['entries'].append(copy.deepcopy(self.inventory['entries'][0]))
        with self.assertRaisesRegex(KPPError,'duplicate'):validate_inventory(self.inventory)
        self.inventory['schema']='other'
        with self.assertRaisesRegex(KPPError,'Unsupported'):validate_inventory(self.inventory)


if __name__=='__main__':unittest.main()
