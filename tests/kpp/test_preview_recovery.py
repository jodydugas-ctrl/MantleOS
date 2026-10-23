"""Current-contract withdrawal, interrupted writers, and source-bound preview transport."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from mantleos.kpp.core import KPPError, read_json, write_json, validate_recipe
from mantleos.kpp.workshop import (begin, load, install_module, set_module_enabled, inspection,
                         accept, finish, preview_fingerprint, workspace_lock, recover_writer)
from mantleos.kpp.portability import export_preview, import_preview

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
RECIPE=read_json(ROOT/'recipes/progressive-calculator.json')


class PreviewRecovery(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.ws=self.root/'workspace'
        begin(self.ws,copy.deepcopy(RECIPE),ROOT)
        self.bundle=self.root/'preview.zip';self.restored=self.root/'restored'

    def install(self,mid='square',deps=()):
        return install_module(self.ws,mid,ROOT/'previews/calculator/square.js',deps)

    def checkpoint(self):
        recipe,state=load(self.ws)
        path=self.root/'browser-state.json'
        write_json(path,{'schema':'kpp.browser-state/1','profile':'json-body/1',
                         'recipe_sha256':state['recipe_hash'],'fingerprint':preview_fingerprint(recipe,state),
                         'body':{'left':'9','right':'4','operation':'subtract','result':'5'}})
        return path

    def test_explicit_state_profile_and_current_schema_only(self):
        recipe=copy.deepcopy(RECIPE);recipe['preview']['state_profile']='invented'
        with self.assertRaisesRegex(KPPError,'Unsupported preview state'):validate_recipe(recipe)
        recipe=copy.deepcopy(RECIPE);recipe['schema']='kpp.recipe/2'
        with self.assertRaisesRegex(KPPError,'Unsupported recipe'):validate_recipe(recipe)

    def test_disable_preserves_source_and_invalidates_acceptance(self):
        self.install();accept(self.ws,'usable-surface','Synthetic check','test-baker')
        before=(self.ws/'app/modules/square.js').read_bytes()
        set_module_enabled(self.ws,'square',False)
        self.assertEqual(inspection(self.ws)['accepted'],0)
        self.assertEqual(inspection(self.ws)['modules'],[])
        self.assertEqual(inspection(self.ws)['disabled_modules'],['square'])
        self.assertEqual((self.ws/'app/modules/square.js').read_bytes(),before)
        set_module_enabled(self.ws,'square',True)
        self.assertEqual(inspection(self.ws)['modules'],['square'])

    def test_dependents_require_explicit_cascade_and_ordered_reactivation(self):
        self.install();self.install('second',['square']);self.install('third',['second'])
        with self.assertRaisesRegex(KPPError,'cascade'):set_module_enabled(self.ws,'square',False)
        set_module_enabled(self.ws,'square',False,cascade=True)
        self.assertEqual(inspection(self.ws)['modules'],[])
        with self.assertRaisesRegex(KPPError,'dependencies first'):set_module_enabled(self.ws,'third',True)
        for mid in ('square','second','third'):set_module_enabled(self.ws,mid,True)
        self.assertEqual(inspection(self.ws)['modules'],['square','second','third'])

    def test_withdrawal_of_complete_app_reopens_build_without_forging_receipt(self):
        self.install()
        for anchor in RECIPE['anchors']:accept(self.ws,anchor['id'],'Synthetic fixture evidence only','test-baker')
        finish(self.ws);receipt=(self.ws/'completion-receipt.json').read_bytes()
        set_module_enabled(self.ws,'square',False)
        self.assertEqual(inspection(self.ws)['phase'],'BUILDING')
        self.assertEqual(inspection(self.ws)['accepted'],0)
        self.assertEqual((self.ws/'completion-receipt.json').read_bytes(),receipt)

    def test_missing_and_duplicate_activation_requests_refused(self):
        with self.assertRaisesRegex(KPPError,'not found'):set_module_enabled(self.ws,'missing',False)
        self.install()
        with self.assertRaisesRegex(KPPError,'already'):set_module_enabled(self.ws,'square',True)

    def test_enabled_child_with_disabled_parent_is_invalid(self):
        self.install();self.install('second',['square'])
        state=read_json(self.ws/'state.json');state['modules'][0]['enabled']=False;write_json(self.ws/'state.json',state)
        with self.assertRaisesRegex(KPPError,'disabled module'):load(self.ws)

    def test_malformed_module_state_refused(self):
        original=read_json(self.ws/'state.json')
        for malformed in (None,[None],[{'id':[]}],[{'id':'valid','depends':[], 'enabled':'yes'}]):
            state=copy.deepcopy(original);state['modules']=malformed;write_json(self.ws/'state.json',state)
            with self.subTest(modules=malformed),self.assertRaises(KPPError):load(self.ws)

    def test_forged_preview_kind_cannot_bypass_pins(self):
        state=read_json(self.ws/'state.json');state['preview_kind']='none';write_json(self.ws/'state.json',state)
        with self.assertRaisesRegex(KPPError,'disagrees with recipe'):load(self.ws)

    def test_live_writer_blocks_other_mutations_and_cannot_be_recovered(self):
        with workspace_lock(self.ws):
            with self.assertRaisesRegex(KPPError,'writer'):self.install()
            with self.assertRaisesRegex(KPPError,'still running'):recover_writer(self.ws,reviewed=True)
        self.assertFalse(read_json(self.ws/'.writer-lock.json')['pending'])

    def test_interrupted_writer_recovery_keeps_verified_committed_state(self):
        env={**os.environ,'PYTHONPATH':str(Path(__import__('mantleos').__file__).parent.parent)}
        code='import os,sys;from mantleos.kpp.workshop import workspace_lock\nwith workspace_lock(sys.argv[1]):os._exit(73)'
        child=subprocess.run([sys.executable,'-c',code,str(self.ws)],env=env,capture_output=True,timeout=10)
        self.assertEqual(child.returncode,73,child.stderr)
        self.assertTrue((self.ws/'.writer-lock.json').exists())
        with self.assertRaisesRegex(KPPError,'reviewed'):recover_writer(self.ws)
        self.assertTrue(recover_writer(self.ws,reviewed=True)['recovered'])
        self.assertEqual(inspection(self.ws)['modules'],[])
        self.install()

    def test_failed_state_publication_keeps_existing_generation(self):
        from mantleos.kpp import workshop
        original=workshop.write_json
        def fail_state(path,value):
            if Path(path).name=='state.json':raise OSError('injected publication interruption')
            return original(path,value)
        with patch.object(workshop,'write_json',side_effect=fail_state):
            with self.assertRaisesRegex(OSError,'interruption'):self.install()
        self.assertEqual(inspection(self.ws)['modules'],[])
        self.assertFalse(read_json(self.ws/'.writer-lock.json')['pending'])
        self.install()

    def test_malformed_interrupted_metadata_requires_explicit_review(self):
        for content in ('[1]','{truncated','{"schema":"unknown","pending":"maybe"}'):
            (self.ws/'.writer-lock.json').write_text(content,encoding='utf-8')
            with self.subTest(content=content):
                with self.assertRaisesRegex(KPPError,'reviewed'):self.install()
                self.assertTrue(recover_writer(self.ws,reviewed=True)['recovered'])
                self.assertEqual(inspection(self.ws)['modules'],[])

    def test_exact_preview_and_explicit_body_state_round_trip_without_acceptance(self):
        self.install();checkpoint=self.checkpoint()
        for anchor in RECIPE['anchors']:accept(self.ws,anchor['id'],'Synthetic check','test-baker')
        finish(self.ws)
        report=export_preview(self.ws,self.bundle,checkpoint)
        self.assertTrue(report['body_state_included'])
        self.assertEqual(inspection(self.ws)['phase'],'COMPLETE')
        result=import_preview(self.bundle,self.restored)
        self.assertEqual(result['execution'],'NONE')
        self.assertEqual(inspection(self.restored)['phase'],'BUILDING')
        self.assertEqual(inspection(self.restored)['accepted'],0)
        self.assertEqual(inspection(self.restored)['modules'],['square'])
        self.assertEqual(read_json(self.restored/'app/body-state.json')['body']['result'],'5')
        self.assertEqual((self.restored/'app/base.js').read_bytes(),(self.ws/'app/base.js').read_bytes())
        self.assertIn('PREVIEW_RESTORED',(self.restored/'history.jsonl').read_text(encoding='utf-8'))

    def test_transport_determinism_and_disabled_source_retention(self):
        self.install();set_module_enabled(self.ws,'square',False)
        other=self.root/'other.zip'
        export_preview(self.ws,self.bundle);export_preview(self.ws,other)
        self.assertEqual(self.bundle.read_bytes(),other.read_bytes())
        import_preview(self.bundle,self.restored)
        self.assertEqual(inspection(self.restored)['disabled_modules'],['square'])

    def approve(self):
        for anchor in RECIPE['anchors']:accept(self.ws,anchor['id'],'Synthetic check','test-baker')

    def test_completion_publication_interruption_never_claims_complete(self):
        from mantleos.kpp import workshop
        self.approve()
        original=workshop.write_json
        for failed_name in ('completion-receipt.json','state.json'):
            def fail(path,value):
                if Path(path).name==failed_name:raise OSError('injected interruption')
                return original(path,value)
            with self.subTest(path=failed_name),patch.object(workshop,'write_json',side_effect=fail):
                with self.assertRaises(OSError):finish(self.ws)
            self.assertEqual(inspection(self.ws)['phase'],'BUILDING')
        finish(self.ws)
        self.assertEqual(inspection(self.ws)['phase'],'COMPLETE')

    def test_completion_receipt_tampering_and_missing_receipt_refused(self):
        self.approve();finish(self.ws)
        path=self.ws/'completion-receipt.json';original=path.read_bytes()
        receipt=read_json(path);receipt['scope']='tampered';write_json(path,receipt)
        with self.assertRaisesRegex(KPPError,'disagrees'):load(self.ws)
        path.unlink()
        with self.assertRaisesRegex(KPPError,'missing'):load(self.ws)
        path.write_bytes(original)
        self.assertEqual(inspection(self.ws)['phase'],'COMPLETE')

    def test_prior_completion_and_approval_provenance_retained(self):
        self.install();self.approve();first=finish(self.ws)
        set_module_enabled(self.ws,'square',False)
        self.approve();second=finish(self.ws)
        receipts=[read_json(path) for path in (self.ws/'artifacts/receipts').glob('*.json')]
        self.assertIn(first,receipts);self.assertIn(second,receipts)
        history=(self.ws/'history.jsonl').read_text(encoding='utf-8')
        self.assertIn('Synthetic check',history);self.assertIn('test-baker',history)

    def test_stale_browser_checkpoint_and_unsupported_state_profile_refused(self):
        checkpoint=self.checkpoint();self.install()
        with self.assertRaisesRegex(KPPError,'stale'):export_preview(self.ws,self.bundle,checkpoint)
        self.assertFalse(self.bundle.exists())
        data=read_json(checkpoint);data['profile']='other';write_json(checkpoint,data)
        with self.assertRaisesRegex(KPPError,'Invalid browser state'):export_preview(self.ws,self.bundle,checkpoint)

    def test_existing_and_workspace_internal_outputs_refused(self):
        self.bundle.write_bytes(b'existing')
        with self.assertRaisesRegex(KPPError,'new and outside'):export_preview(self.ws,self.bundle)
        with self.assertRaisesRegex(KPPError,'new and outside'):export_preview(self.ws,self.ws/'nested.zip')
        self.restored.mkdir()
        with self.assertRaisesRegex(KPPError,'unused'):import_preview(self.bundle,self.restored)

    def test_output_parent_alias_into_workspace_is_refused(self):
        alias=self.root/'workspace-alias'
        try:
            alias.symlink_to(self.ws,target_is_directory=True)
        except OSError as error:
            self.skipTest('Directory symlink privilege unavailable: '+str(error))
        with self.assertRaisesRegex(KPPError,'new and outside'):
            export_preview(self.ws,alias/'nested.zip')
        self.assertFalse((self.ws/'nested.zip').exists())

    def test_tampered_duplicate_and_unsafe_archive_members_refused(self):
        export_preview(self.ws,self.bundle)
        with zipfile.ZipFile(self.bundle) as archive:
            blobs={entry.filename:archive.read(entry.filename) for entry in archive.infolist()}
        for filename,data in [('app/base.js',b'tampered'),('../escape.txt',b'escape')]:
            bad=self.root/'bad.zip'
            with zipfile.ZipFile(bad,'w') as archive:
                for name,content in blobs.items():archive.writestr(name,content)
                archive.writestr(filename,data)
            with self.subTest(filename=filename),self.assertRaises(KPPError):import_preview(bad,self.restored)
            self.assertFalse(self.restored.exists())


if __name__=='__main__':unittest.main()
