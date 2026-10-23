"""Contract, evidence and publication gates. Browser unit fixtures are synthetic."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mantleos.kpp.core import KPPError, digest, read_json, write_json
from mantleos.kpp.organs import project, evidence
from mantleos.kpp.scanner import scan
from mantleos.kpp.module_revisions import replace_module, restore_module, source_path, sha
from mantleos.kpp.organ_testing import CASES, run_module_tests, verify_module_evidence
from mantleos.kpp.workshop import begin, install_module, load, asset, recover_writer, workspace_lock
from mantleos.kpp.portability import export_preview, import_preview

ROOT = Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent / 'resources'
RECIPE = read_json(ROOT / 'recipes/notepad-organs.json')
MAPPING = read_json(ROOT / 'contracts/notepad-organs.json')


class OrganContracts(unittest.TestCase):
    def setUp(self):
        self.recipe, self.mapping = copy.deepcopy(RECIPE), copy.deepcopy(MAPPING)

    def test_ownership_is_a_projection_of_all_six_existing_obligations(self):
        value = project(self.recipe, self.mapping)
        self.assertEqual(value['organ_count'], 4)
        self.assertEqual(value['source_recipe_sha256'], digest(self.recipe))
        self.assertEqual(value['kpp_acceptance'], 'NOT_GRANTED')
        self.assertEqual(value['authority'], 'NONE')
        value['organs'][0]['anchor_ids'].clear()
        self.assertTrue(self.mapping['organs'][0]['anchor_ids'])
        old = read_json(ROOT / 'recipes/notepad-demo.json')
        self.assertEqual(self.recipe['anchors'], old['anchors'])

    def test_bad_pin_missing_duplicate_unknown_and_cycles_are_refused(self):
        changes = [lambda m: m.update(recipe_sha256='0'*64),
                   lambda m: m['organs'][0]['anchor_ids'].pop(),
                   lambda m: m['organs'][1]['anchor_ids'].append('ui-surface'),
                   lambda m: m['organs'][1]['anchor_ids'].append('unknown'),
                   lambda m: m['organs'][1].update(requires=[]),
                   lambda m: m['organs'][0].update(requires=['save']),
                   lambda m: m['organs'][1].update(requires=['save'])]
        for change in changes:
            mapping = copy.deepcopy(self.mapping); change(mapping)
            with self.subTest(mapping=mapping), self.assertRaises(KPPError):
                project(self.recipe, mapping)

    def test_pinned_actual_graph_and_native_coverage_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source.py').write_text('raise RuntimeError("DO NOT EXECUTE")\ndef save():\n return 1\n')
            (root / 'unknown.xyz').write_bytes(b'opaque\x00')
            report = scan(root)
            nodes = [n['id'] for n in report['native_report']['graph']['nodes'] if n['path'] == 'source.py']
            bindings = {'schema':'kpp.organ-scan-bindings/1','recipe_sha256':digest(self.recipe),
                        'mapping_sha256':digest(self.mapping),'links':[{'anchor_id':'save-file',
                        'files':['source.py', 'unknown.xyz'],'nodes':nodes}]}
            value = evidence(self.recipe, self.mapping, bindings, report, root)
            observed = next(e for e in value['observations'] if e['anchor_id']=='save-file')
            self.assertEqual(observed['static_evidence'], 'OBSERVED')
            expected = {f['path']:f['status'] for f in report['native_report']['graph']['files']}
            self.assertEqual({f['path']:f['coverage'] for f in observed['files']}, expected)
            self.assertEqual(value['observations'][0]['static_evidence'], 'UNMAPPED')
            changed = copy.deepcopy(bindings); changed['links'][0]['nodes']=['invented']
            with self.assertRaisesRegex(KPPError,'graph reference'):
                evidence(self.recipe,self.mapping,changed,report,root)
            (root / 'extra.py').write_text('pass\n')
            with self.assertRaisesRegex(KPPError,'inventory changed'):
                evidence(self.recipe,self.mapping,bindings,report,root)
            (root / 'extra.py').unlink(); (root / 'source.py').write_text('changed')
            with self.assertRaisesRegex(KPPError,'stale'):
                evidence(self.recipe,self.mapping,bindings,report,root)


class ModuleRevisionGates(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.ws = self.root / 'workspace'
        begin(self.ws, copy.deepcopy(RECIPE), ROOT)
        for mid, deps in [('edit', []), ('save', ['edit']), ('open', ['edit'])]:
            install_module(self.ws, mid, ROOT / f'previews/notepad-organs/{mid}.js', deps)
        self.original = (self.ws / 'app/modules/save.js').read_bytes()
        self.source = self.root / 'candidate.js'
        self.source.write_bytes(self.original.replace(b'},3000)', b'},2000)') + b'\n/* reviewed candidate fixture */\n')
        self.report_path = self.root / 'checks/report.json'

    def report(self, result='PASS'):
        # Intentionally synthetic gate fixture; actual browser execution is separately opt-in.
        runtime = {'result':result,'browser':'SYNTHETIC UNIT FIXTURE',
                   'checks':[{'name':name,'result':result} for name in CASES]}
        with patch('mantleos.kpp.organ_testing.browser_checks', return_value=runtime):
            return run_module_tests(self.ws,'save',self.source,copy.deepcopy(MAPPING),
                                    self.report_path.parent,execute=True,reviewed=True)

    def replace(self, **kw):
        return replace_module(self.ws, 'save', self.source, self.report_path,
                              expected_revision=load(self.ws)[1]['revision'], reviewed=True, **kw)

    def test_review_and_execution_flags_are_required(self):
        with self.assertRaisesRegex(KPPError,'--execute --reviewed'):
            run_module_tests(self.ws,'save',self.source,MAPPING,self.root/'no-execution')
        self.report()
        with self.assertRaisesRegex(KPPError,'--reviewed'):
            replace_module(self.ws,'save',self.source,self.report_path,expected_revision=4)

    def test_replacement_keeps_original_and_restoration_appends_history(self):
        self.report(); self.replace()
        recipe, state = load(self.ws)
        module = next(m for m in state['modules'] if m['id']=='save')
        self.assertEqual((self.ws/'app/modules/save.js').read_bytes(),self.original)
        self.assertEqual((self.ws/source_path(module)).read_bytes(),self.source.read_bytes())
        self.assertEqual(len(module['revisions']),2)
        self.assertEqual(module['depends'],['edit'])
        self.assertEqual(state['accepted'],{})
        restored = restore_module(self.ws,'save',expected_revision=state['revision'],reviewed=True)
        module = next(m for m in restored['modules'] if m['id']=='save')
        self.assertEqual(module['sha256'],sha(self.original))
        self.assertEqual(restored['phase'],'BUILDING')
        history = (self.ws/'history.jsonl').read_text()
        self.assertIn('MODULE_REPLACED',history); self.assertIn('MODULE_RESTORED',history)

    def test_failed_report_and_changed_candidate_cannot_replace_baseline(self):
        self.report('FAIL')
        with self.assertRaisesRegex(KPPError,'failed'):
            self.replace()
        self.assertEqual((self.ws/'app/modules/save.js').read_bytes(),self.original)
        report = read_json(self.report_path)
        report['result']='PASS'; report['runtime']['result']='PASS'
        report['sha256']=digest({k:v for k,v in report.items() if k!='sha256'})
        write_json(self.report_path,report)
        with self.assertRaisesRegex(KPPError,'Incomplete'):
            self.replace()

    def test_stale_revision_report_source_and_test_identity_are_refused(self):
        report = self.report()
        with self.assertRaisesRegex(KPPError,'Stale workspace'):
            replace_module(self.ws,'save',self.source,self.report_path,expected_revision=0,reviewed=True)
        self.source.write_bytes(self.source.read_bytes()+b'\n// drift')
        with self.assertRaisesRegex(KPPError,'tested bytes'):
            verify_module_evidence(report,self.ws,'save',self.source)
        self.source.write_bytes(self.source.read_bytes().removesuffix(b'\n// drift'))
        (Path(report['trial_workspace'])/'app/base.js').write_text('tamper')
        with self.assertRaises(KPPError):
            self.replace()

    def test_replacement_refuses_active_writer_and_publication_failure_keeps_baseline(self):
        self.report()
        with workspace_lock(self.ws):
            with self.assertRaisesRegex(KPPError,'active'):
                self.replace()
        before = (self.ws/'state.json').read_bytes()
        with patch('mantleos.kpp.module_revisions.write_json',side_effect=OSError('injected publication failure')):
            with self.assertRaises(OSError): self.replace()
        self.assertEqual((self.ws/'state.json').read_bytes(),before)
        self.assertEqual(load(self.ws)[1]['modules'][1]['sha256'],sha(self.original))
        self.replace()  # Complete immutable staging can be reused; no partial state was adopted.

    def test_retained_source_tamper_blocks_load_and_transport(self):
        self.report(); self.replace()
        module = load(self.ws)[1]['modules'][1]
        prior = self.ws / f"app/module-revisions/save/{module['previous_sha256']}.js"
        prior.write_bytes(b'tampered')
        with self.assertRaisesRegex(KPPError,'modified'):
            load(self.ws)
        with self.assertRaises(KPPError):
            export_preview(self.ws,self.root/'bad.zip')

    def test_interrupted_publication_requires_recovery_and_keeps_committed_source(self):
        self.report()
        before=(self.ws/'state.json').read_bytes()
        code='''import os,sys
from unittest.mock import patch
from mantleos.kpp.module_revisions import replace_module
with patch('mantleos.kpp.module_revisions.write_json',side_effect=lambda *a,**k:os._exit(73)):
 replace_module(sys.argv[1],'save',sys.argv[2],sys.argv[3],expected_revision=int(sys.argv[4]),reviewed=True)
'''
        env={**os.environ,'PYTHONPATH':str(Path(__import__('mantleos').__file__).parent.parent)}
        child=subprocess.run([sys.executable,'-c',code,str(self.ws),str(self.source),str(self.report_path),
                              str(load(self.ws)[1]['revision'])],env=env,capture_output=True,timeout=15)
        self.assertEqual(child.returncode,73,child.stderr)
        self.assertEqual((self.ws/'state.json').read_bytes(),before)
        with self.assertRaisesRegex(KPPError,'interrupted'):
            self.replace()
        self.assertTrue(recover_writer(self.ws,reviewed=True)['recovered'])
        self.assertEqual(load(self.ws)[1]['modules'][1]['sha256'],sha(self.original))
        self.replace()

    def test_different_trial_dependencies_and_tampered_report_are_refused(self):
        report=self.report()
        changed=copy.deepcopy(report);changed['candidate_sha256']='0'*64
        with self.assertRaisesRegex(KPPError,'tampered'):
            verify_module_evidence(changed,self.ws,'save',self.source)
        trial=Path(report['trial_workspace']);recipe,state=load(trial)
        dependency=trial/'app/modules/edit.js'
        dependency.write_bytes(dependency.read_bytes()+b'\n// different dependency')
        state['modules'][0]['sha256']=sha(dependency.read_bytes())
        state['modules'][0]['bytes']=dependency.stat().st_size
        write_json(trial/'state.json',state)
        with self.assertRaisesRegex(KPPError,'dependency/runtime'):
            verify_module_evidence(report,self.ws,'save',self.source)

    def test_stale_baseline_and_changed_test_implementation_invalidate_evidence(self):
        report=self.report()
        with patch('mantleos.kpp.organ_testing.test_identity',return_value='0'*64):
            with self.assertRaisesRegex(KPPError,'Test implementation changed'):
                verify_module_evidence(report,self.ws,'save',self.source)
        from mantleos.kpp.workshop import set_module_enabled
        set_module_enabled(self.ws,'open',False)
        with self.assertRaisesRegex(KPPError,'Stale baseline'):
            verify_module_evidence(report,self.ws,'save',self.source)

    def test_preview_transport_retains_revisions_and_clears_acceptance(self):
        self.report(); self.replace()
        bundle = self.root/'preview.zip'; incoming = self.root/'incoming'
        export_preview(self.ws,bundle); import_preview(bundle,incoming)
        recipe, state = load(incoming)
        self.assertEqual(state['accepted'],{})
        self.assertEqual(state['phase'],'BUILDING')
        self.assertNotEqual(state['workspace_id'],load(self.ws)[1]['workspace_id'])
        self.assertEqual(len(state['modules'][1]['revisions']),2)
        restore_module(incoming,'save',expected_revision=state['revision'],reviewed=True)
        self.assertEqual(load(incoming)[1]['modules'][1]['sha256'],sha(self.original))

    def test_legacy_runtime_is_retained_without_silent_upgrade(self):
        recipe, state = load(self.ws)
        legacy = asset('progressive-v1.js')
        (self.ws/'app/runtime.js').write_bytes(legacy)
        state['runtime_sha256']=sha(legacy); write_json(self.ws/'state.json',state)
        self.assertEqual(load(self.ws)[1]['runtime_sha256'],sha(legacy))
        export_preview(self.ws,self.root/'legacy.zip')
        import_preview(self.root/'legacy.zip',self.root/'legacy-import')
        with self.assertRaisesRegex(KPPError,'no implicit runtime upgrade'):
            self.replace()


if __name__=='__main__':
    unittest.main()
