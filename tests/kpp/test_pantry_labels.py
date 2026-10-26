"""Labels avoid reading code into the model and do not make unsupported trust claims."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mantleos.kpp.core import KPPError, ingredient_catalog, read_json, write_json
from mantleos.kpp.pantry import discover, view, label
from mantleos.kpp.ingest import catalog_source
from mantleos.kpp.workshop import begin, handoff, load

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'

class PantryLabels(unittest.TestCase):
    def test_discovery_and_levels_do_not_interpret_source(self):
        with patch('mantleos.kpp.anchor.inspect_file',side_effect=AssertionError('should not inspect code')):
            results=discover(ROOT,'memory',context='bioagent')
            self.assertTrue(results['matches'])
            self.assertTrue(all(row['selection']=='ADVISORY_ONLY' for row in results['matches']))
            self.assertIn('chroma-png-memory',[row['id'] for row in results['matches']])
            item=view(ROOT,'kernel-relative-cells')
            self.assertEqual(item['source']['integrity'],'PIN_MATCH')
            self.assertEqual(item['evidence']['type'],'MANIFEST_STATEMENT_NOT_INDEPENDENT_PROOF')
            self.assertIn('minimum_fidelity',view(ROOT,'kernel-relative-cells','contract'))
            source=view(ROOT,'kernel-relative-cells','source')
            self.assertNotIn('print(',json.dumps(source))
            self.assertEqual(source['source']['source_access'],'EXPLICIT_ONLY')

    def test_stale_specimen_visible_but_not_usable(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)
            (dest/'pantry').mkdir()
            manifest=read_json(ROOT/'pantry/kernel-relative-cells.json')
            write_json(dest/'pantry/kernel-relative-cells.json',manifest)
            (dest/'specimens/mantleos').mkdir(parents=True)
            (dest/manifest['specimen']['path']).write_text('altered code',encoding='utf-8')
            result=view(dest,manifest['id'])
            self.assertEqual(result['source']['integrity'],'STALE_PIN_MISMATCH')
            with self.assertRaises(KPPError):ingredient_catalog(dest)

    def test_unbundled_reference_has_no_fake_evidence(self):
        result=view(ROOT,'anchor-tissue')
        self.assertEqual(result['source']['integrity'],'NO_SOURCE_PIN')
        self.assertEqual(result['status'],'reference')
        self.assertEqual(result['integration'],'REQUIRES_RECIPE_SPECIFIC_TESTS')

    def test_repository_locator_is_metadata_only_and_discoverable_by_department(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'pantry').mkdir()
            manifest={'schema':'kpp.ingredient/1','id':'sample-capability','version':'1.0.0',
                      'function':'A bounded locator test','status':'experimental',
                      'tags':['department:memory','hash-chain'],
                      'usage':{'use_when':'Select for a memory locator test','inputs':['text'],
                               'outputs':['declared source path'],'limits':'Metadata only.'},
                      'source':{'kind':'repository-files','repository':'owner/repo',
                                'paths':['src/mantleos/engram.py']}}
            write_json(root/'pantry/sample-capability.json',manifest)
            # The pantry manifest may be read; the declared repo source must not be opened.
            import builtins
            opened=[]; original_open=builtins.open
            def tracked_open(file,*args,**kwargs):
                opened.append(Path(file))
                return original_open(file,*args,**kwargs)
            with patch('builtins.open',side_effect=tracked_open), patch('pathlib.Path.read_bytes',side_effect=AssertionError('must not read source')):
                found=discover(root,'department:memory')
                self.assertEqual([x['id'] for x in found['matches']],['sample-capability'])
                label_value=view(root,'sample-capability')
                self.assertEqual(label_value['source']['integrity'],'DECLARED_LOCATION_ONLY')
                source=view(root,'sample-capability','source')
                self.assertEqual(source['source']['paths'],['src/mantleos/engram.py'])
                self.assertEqual(source['source']['source_access'],'EXPLICIT_ONLY')
                self.assertEqual(source['source']['integrity'],'DECLARED_LOCATION_ONLY')
            self.assertTrue(all(path.name=='sample-capability.json' for path in opened))

    def test_repository_locator_rejects_unsafe_and_duplicate_paths(self):
        unsafe=['../outside.py','src/../../outside.py','/absolute.py','C:/outside.py',
                'src\\outside.py','src//outside.py','src/./inside.py',
                'src/file.py:stream','src/bad|name.py','src/CON.txt']
        for paths in [[path] for path in unsafe] + [['src/a.py','src/a.py']]:
            with self.subTest(paths=paths), tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/'pantry').mkdir()
                write_json(root/'pantry/bad.json',{
                    'schema':'kpp.ingredient/1','id':'bad-source','version':'1.0.0',
                    'function':'Invalid locator','status':'reference',
                    'source':{'kind':'repository-files','repository':'owner/repo','paths':paths}})
                with self.assertRaises(KPPError): ingredient_catalog(root)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'pantry').mkdir()
            write_json(root/'pantry/bad.json',{
                'schema':'kpp.ingredient/1','id':'bad-source','version':'1.0.0',
                'function':'Invalid locator','status':'reference',
                'source':{'kind':'repository-files','repository':'../repo','paths':['src/file.py']}})
            with self.assertRaises(KPPError): ingredient_catalog(root)

    def test_stable_ids_and_department_tags_are_catalog_metadata(self):
        expected={'anchor-tissue','browser-file-io','chase-gate','chroma-png-memory',
                  'engram-continuity','external-project','fidelity-trace','interface-shell',
                  'kernel-relative-cells','local-draft-recovery','mind-body-boundary',
                  'progressive-web-runtime','python-tissue','text-editor',
                  'vcw-cartridge-memory','recipe-organ-contracts','checked-body-effects','reflex-book'}
        catalog=ingredient_catalog(ROOT)
        self.assertEqual(set(catalog),expected)
        departments={'memory','carriers','languages','body','cognition','construction'}
        for item in catalog.values():
            self.assertTrue(all(tag.split(':',1)[1] in departments for tag in item['tags']
                                if tag.startswith('department:')))
            self.assertTrue(any(tag.startswith('department:') for tag in item['tags']))
            if item['status']=='ready':
                self.assertIn(item['source']['kind'],('repository-files','bundled-files'),item['id'])
                if item['source']['kind']=='repository-files':
                    self.assertTrue(any(path.startswith('tests/') for path in item['source']['paths']),item['id'])
                self.assertIn('test',item['verified_with'].lower(),item['id'])
        result=discover(ROOT,'department:memory')
        ids={x['id'] for x in result['matches']}
        self.assertTrue({'chroma-png-memory','engram-continuity'} <= ids)
        self.assertNotIn('vcw-cube',catalog);self.assertNotIn('vcw-stack',catalog)

    def test_current_carrier_evidence_is_preserved(self):
        for ident in ('chroma-png-memory','vcw-cartridge-memory'):
            result=view(ROOT,ident)
            self.assertEqual(result['status'],'ready')
            self.assertEqual(result['source']['integrity'],'NOT_RECHECKED')
            self.assertEqual(view(ROOT,ident,'source')['source']['integrity'],'PIN_MATCH')

    def test_external_bounded_recheck_is_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);src=r/'source';src.mkdir()
            (src/'run.py').write_text('def demo(): return 1\n')
            (r/'pantry').mkdir()
            manifest=catalog_source(src,'sample-code',r/'pantry/sample-code.json')
            default=view(r,'sample-code')
            self.assertEqual(default['source']['integrity'],'NOT_RECHECKED')
            checked=view(r,'sample-code',check_external=True)
            self.assertEqual(checked['source']['integrity'],'INVENTORY_MATCH_BOUNDED')
            (src/'run.py').write_text('def demo(): return 2\n')
            self.assertEqual(view(r,'sample-code',check_external=True)['source']['integrity'],'STALE_INVENTORY')
            self.assertEqual(view(r,'sample-code')['source']['integrity'],'NOT_RECHECKED')

    def test_bake_pins_selection_labels_without_source(self):
        with tempfile.TemporaryDirectory() as d:
            ws=Path(d)/'ws';recipe=read_json(ROOT/'recipes/portable-memory-bake.json')
            begin(ws,recipe,ROOT)
            data=read_json(ws/'ingredient-labels.json')
            self.assertEqual([i['id'] for i in data['ingredients']],recipe['ingredients'])
            self.assertIn('Ingredient labels',handoff(ws))
            load(ws)
            data['ingredients'][0]['purpose']='changed!'
            write_json(ws/'ingredient-labels.json',data)
            with self.assertRaises(KPPError):load(ws)

    def test_no_unbounded_label_fields(self):
        obj=ingredient_catalog(ROOT)['text-editor']
        changed=json.loads(json.dumps(obj))
        changed['usage']['inputs']=['x'*2000]
        with self.assertRaises(KPPError):label(ROOT,changed)

if __name__=='__main__':unittest.main()

# CLI boundary: listing/selection can be performed without agent execution.
class PantryCLI(unittest.TestCase):
    def test_cli_discover_contract_and_source(self):
        import subprocess, sys, os
        env={**os.environ,"PYTHONPATH":str(Path(__import__('mantleos').__file__).parent.parent)}
        def run(*args):
            return subprocess.run([sys.executable,'-m','mantleos','kpp',*args],cwd=ROOT,env=env,
                                  text=True,capture_output=True,timeout=20)
        discovery=run('pantry','--query','pixel')
        self.assertEqual(discovery.returncode,0,discovery.stderr)
        result=json.loads(discovery.stdout)
        self.assertIn('kernel-relative-cells',[x['id'] for x in result['matches']])
        contract=run('pantry','--id','kernel-relative-cells','--level','contract')
        self.assertEqual(contract.returncode,0,contract.stderr)
        self.assertEqual(json.loads(contract.stdout)['source']['integrity'],'PIN_MATCH')
        bad=run('pantry','--level','source')
        self.assertEqual(bad.returncode,2)
        self.assertIn('require --id',bad.stderr)
