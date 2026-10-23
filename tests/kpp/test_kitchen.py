import tempfile
import unittest
from pathlib import Path
from mantleos.kpp.core import KPPError, find_repo_root, ingredient_catalog, read_json, validate_recipe
from mantleos.kpp.workshop import begin, load, inspection, accept, finish, priorities, install_module, handoff
from mantleos.kpp.scanner import scan

ROOT=find_repo_root()
RECIPE=read_json(ROOT/'recipes/notepad-demo.json')

class Contracts(unittest.TestCase):
    def test_ambiguous_or_nonfinite_json_contracts_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ambiguous.json'
            for source in ('{"required":true,"required":false}','{"fidelity":NaN}','{"fidelity":Infinity}'):
                path.write_text(source,encoding='utf-8')
                with self.subTest(source=source),self.assertRaises(KPPError):read_json(path)
    def test_pantry_and_recipes(self):
        self.assertGreater(len(ingredient_catalog(ROOT)),10)
        for f in (ROOT/'recipes').glob('*.json'):
            validate_recipe(read_json(f))
    def test_recipe_duplicate_and_cycles_refused(self):
        import copy
        x=copy.deepcopy(RECIPE)
        x['anchors'][1]['id']=x['anchors'][0]['id']
        with self.assertRaises(KPPError):validate_recipe(x)
        x=copy.deepcopy(RECIPE)
        x['anchors'][0]['depends']=['draft-safety']
        with self.assertRaises(KPPError):validate_recipe(x)
    def test_progressive_not_complete_until_all_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            ws=Path(t)/'workspace'
            begin(ws,RECIPE,ROOT)
            self.assertFalse(inspection(ws)['all_required_satisfied'])
            with self.assertRaises(KPPError):finish(ws)
            install_module(ws,'edit',ROOT/'previews/notepad/edit.js')
            install_module(ws,'files',ROOT/'previews/notepad/files.js',['edit'])
            self.assertEqual(inspection(ws)['modules'],['edit','files'])
            # Acceptance order respects dependencies.
            with self.assertRaises(KPPError):accept(ws,'save-file','pretend check','operator')
            for a in RECIPE['anchors']:
                accept(ws,a['id'],"Manual browser check performed","test-baker")
            self.assertTrue(inspection(ws)['all_required_satisfied'])
            receipt=finish(ws)
            self.assertEqual(receipt['required_anchors'],6)
            self.assertEqual(inspection(ws)['phase'],'COMPLETE')
            with self.assertRaises(KPPError):finish(ws)
    def test_install_invalidates_previous_acceptance(self):
        with tempfile.TemporaryDirectory() as t:
            ws=Path(t)/'workspace';begin(ws,RECIPE,ROOT)
            accept(ws,'ui-surface','observed','baker')
            install_module(ws,'edit',ROOT/'previews/notepad/edit.js')
            self.assertEqual(inspection(ws)['accepted'],0)
            with self.assertRaises(KPPError):finish(ws)
            # After installation, a published module cannot be silently rewritten.
            (ws/'app'/'modules'/'edit.js').write_text('changed')
            with self.assertRaises(KPPError):load(ws)
    def test_manual_module_and_handoff(self):
        with tempfile.TemporaryDirectory() as t:
            ws=Path(t)/'workspace';begin(ws,RECIPE,ROOT)
            src=Path(t)/'extension.js';src.write_text("window.KPP.define('extension', function(context) {});")
            install_module(ws,'extension',src)
            self.assertIn('Baker',handoff(ws))
            with self.assertRaises(KPPError):install_module(ws,'extension',src)
            with self.assertRaises(KPPError):install_module(ws,'unknown',src,['no-such-dependency'])
    def test_source_scan_is_readonly_and_deeper(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/'demo.py').write_text('def a():\n    return b()\ndef b():\n    return 1\n')
            (p/'a.html').write_text('<button id="save">Save</button>')
            first=scan(p,1);deeper=scan(p,3)
            self.assertEqual(len(first['edges']),0)
            self.assertGreater(len(deeper['edges']),0)
            self.assertTrue(any(v.get('id')=='save' for v in deeper['nodes'].values()))
            self.assertFalse((p/'__pycache__').exists())
    def test_chase_priority(self):
        with tempfile.TemporaryDirectory() as t:
            ws=Path(t)/'workspace';begin(ws,RECIPE,ROOT)
            self.assertEqual(priorities(ws)[0]['ready'],True)
            self.assertFalse(any(a['id']=='save-file' and a['ready'] for a in priorities(ws)))
            accept(ws,'ui-surface','observed','baker')
            accept(ws,'editing-actions','tested','baker')
            self.assertTrue(next(a for a in priorities(ws) if a['id']=='save-file')['ready'])

if __name__=='__main__':unittest.main()
