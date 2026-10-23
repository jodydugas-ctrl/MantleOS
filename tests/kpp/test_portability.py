"""Portable candidate transport: fixed source/test pins; fail-closed restore."""
import hashlib
import json
import shutil
import subprocess
import sys
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from mantleos.kpp.adaptation import reflex_plan
from mantleos.kpp.core import KPPError, read_json, write_json, digest
from mantleos.kpp.portability import export_bundle, import_bundle, review_candidate, MAX_BYTES
from mantleos.kpp.reflex import approval_template, stage, audit, STAGE_MANIFEST
from mantleos.kpp.testing import validated_suite, run_suite, verify_report
from mantleos.kpp.workshop import begin, load, inspection

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
SOURCE=ROOT/'examples/adaptive-reflex'
SUITE=ROOT/'examples/reflex-anchors'
RECIPE=read_json(ROOT/'recipes/adaptive-reflex-demo.json')
REQUEST=read_json(SOURCE/'request.json')

class PortableCandidateTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.ws=self.root/'workspace'
        self.candidate=self.root/'candidate'
        self.bundle=self.root/'candidate.zip'
        self.recovered=self.root/'recovered'
        begin(self.ws, RECIPE, ROOT)
        recipe, state=load(self.ws)
        plan=reflex_plan(ROOT,recipe,state,REQUEST,SOURCE)
        approval=approval_template(plan)
        approval['baker']='operator-review-of-demo'
        self.request=self.root/'request.json'
        self.plan=self.root/'plan.json'
        self.approval=self.root/'approval.json'
        for p,v in ((self.request,REQUEST),(self.plan,plan),(self.approval,approval)):
            write_json(p,v)
        stage(self.ws,REQUEST,plan,approval,SOURCE,self.candidate,ROOT)

    def pack(self,**kw):
        args=dict(workspace=self.ws,candidate=self.candidate,suite=SUITE,
                  request=self.request,plan=self.plan,approval=self.approval,output=self.bundle)
        args.update(kw)
        return export_bundle(**args)

    def test_export_import_is_independently_checkable_and_has_no_acceptance(self):
        result=self.pack()
        self.assertEqual(result['execution'],'NONE')
        self.assertEqual(result['sha256'], hashlib.sha256(self.bundle.read_bytes()).hexdigest())
        returned=import_bundle(self.bundle,self.recovered)
        self.assertEqual(returned['integrity'],'PASS')
        self.assertEqual(returned['acceptance'],'NOT_TRANSFERRED')
        self.assertEqual(inspection(self.ws)['accepted'],0)
        audit(self.recovered/'candidate')
        recipe=read_json(self.recovered/'review/recipe.json')
        validated_suite(self.recovered/'suite', recipe, read_json(self.recovered/'candidate'/STAGE_MANIFEST))
        self.assertEqual((self.candidate/'task_agent.py').read_bytes(),
                         (self.recovered/'candidate/task_agent.py').read_bytes())
        self.assertIn('not deployed or accepted', (self.recovered/'RECOVERY.md').read_text())
        # Fresh workspace is mandatory; prior report/acceptance does not travel.
        new_ws=self.root/'fresh-ws'
        begin(new_ws,recipe,ROOT)
        fresh_report=self.root/'fresh-report.json'
        observed=run_suite(new_ws,self.recovered/'candidate',self.recovered/'suite',fresh_report,execute=True,reviewed=True)
        self.assertTrue(observed['all_passed'])
        self.assertTrue(verify_report(read_json(fresh_report),self.recovered/'candidate',self.recovered/'suite')['fresh'])
        self.assertEqual(inspection(new_ws)['accepted'],0)

    def test_review_shows_only_adapter_addition_and_refuses_changed_original(self):
        review=review_candidate(self.candidate,SOURCE)
        self.assertEqual(review['status'],'ADDITIVE_CANDIDATE')
        self.assertIn('+++ kpp_reflex_adapter.py',review['unified_diff'])
        self.assertEqual(review['original_files_unchanged'],7)
        self.assertTrue((SOURCE/'task_agent.py').exists())
        other=self.root/'changed-source';shutil.copytree(SOURCE,other)
        (other/'task_agent.py').write_text('changed\n')
        with self.assertRaises(KPPError):review_candidate(self.candidate,other)

    def test_refuse_broken_symlink_as_recovery_output(self):
        self.pack()
        try:
            self.recovered.symlink_to(self.root/'missing')
        except (OSError,NotImplementedError):
            self.skipTest('Host does not permit creating symlinks')
        with self.assertRaises(KPPError):import_bundle(self.bundle,self.recovered)
        self.assertTrue(self.recovered.is_symlink())

    def test_cli_export_import_and_review_commands(self):
        env={**os.environ,'PYTHONPATH':str(Path(__import__('mantleos').__file__).parent.parent)}
        common=[sys.executable,'-m','mantleos','kpp']
        review=subprocess.run(common+['reflex-review','--candidate',str(self.candidate),'--source',str(SOURCE)],cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertEqual(review.returncode,0,review.stderr)
        self.assertEqual(json.loads(review.stdout)['status'],'ADDITIVE_CANDIDATE')
        export=subprocess.run(common+['reflex-export','--workspace',str(self.ws),'--candidate',str(self.candidate),'--suite',str(SUITE),'--request',str(self.request),'--plan',str(self.plan),'--approval',str(self.approval),'--out',str(self.bundle)],cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertEqual(export.returncode,0,export.stderr)
        incoming=subprocess.run(common+['reflex-import','--bundle',str(self.bundle),'--output',str(self.recovered)],cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertEqual(incoming.returncode,0,incoming.stderr)
        self.assertEqual(json.loads(incoming.stdout)['integrity'],'PASS')

    def test_repeat_exports_have_same_bytes(self):
        self.pack()
        other=self.root/'another.zip'
        self.pack(output=other)
        self.assertEqual(self.bundle.read_bytes(),other.read_bytes())

    def test_does_not_overwrite_existing_paths(self):
        self.pack()
        with self.assertRaises(KPPError):self.pack()
        import_bundle(self.bundle,self.recovered)
        with self.assertRaises(KPPError):import_bundle(self.bundle,self.recovered)

    def test_rejects_missing_or_stale_review_claims(self):
        approval=read_json(self.approval);approval['baker']='different-operator'
        write_json(self.approval,approval)
        with self.assertRaisesRegex(KPPError,'approval'):self.pack()
        self.assertFalse(self.bundle.exists())

    def test_source_modified_prevents_export(self):
        (self.candidate/'task_agent.py').write_text('modified\n')
        with self.assertRaises(KPPError):self.pack()
        self.assertFalse(self.bundle.exists())

    def test_refuse_unpinned_suite_file(self):
        tests=self.root/'tests';shutil.copytree(SUITE,tests)
        (tests/'shadow.py').write_text('import os\n')
        with self.assertRaises(KPPError):self.pack(suite=tests)

    def _repack(self, mapping, dest):
        with zipfile.ZipFile(dest,'w') as z:
            for name, content in mapping.items():z.writestr(name, content)

    def test_tamper_rejected_before_any_files_written(self):
        self.pack()
        with zipfile.ZipFile(self.bundle) as z:
            entries={k:z.read(k) for k in z.namelist()}
        entries['candidate/task_agent.py'] += b'# forged\n'
        hostile=self.root/'tampered.zip';self._repack(entries,hostile)
        with self.assertRaises(KPPError):import_bundle(hostile,self.recovered)
        self.assertFalse(self.recovered.exists())

    def test_zip_slip_and_absolute_paths_rejected(self):
        self.pack()
        with zipfile.ZipFile(self.bundle) as z:
            entries={k:z.read(k) for k in z.namelist()}
        for bad in ('../outside.py','/tmp/outside.py','candidate/../../outside.py','C:/drive.py'):
            with self.subTest(bad=bad):
                hostile=self.root/('hostile'+str(len(bad))+str(bad.count('/'))+'.zip')
                self._repack({**entries,bad:b'unsafe'},hostile)
                with self.assertRaises(KPPError):import_bundle(hostile,self.recovered)
                self.assertFalse(self.recovered.exists())
                hostile.unlink()

    def test_duplicate_and_symlink_zip_entries_rejected(self):
        self.pack()
        duplicate=self.root/'duplicate.zip'
        with zipfile.ZipFile(self.bundle) as z,zipfile.ZipFile(duplicate,'w') as out:
            for item in z.infolist():out.writestr(item.filename,z.read(item))
            out.writestr('candidate/task_agent.py',b'evil')
        with self.assertRaises(KPPError):import_bundle(duplicate,self.recovered)
        symlink=self.root/'symlink.zip'
        with zipfile.ZipFile(self.bundle) as z,zipfile.ZipFile(symlink,'w') as out:
            for item in z.infolist():out.writestr(item.filename,z.read(item))
            item=zipfile.ZipInfo('candidate/other.py');item.create_system=3
            item.external_attr=(0o120777<<16)
            out.writestr(item,'/etc/passwd')
        with self.assertRaises(KPPError):import_bundle(symlink,self.recovered)
        self.assertFalse(self.recovered.exists())

    def test_oversize_archive_member_rejected_without_extraction(self):
        self.pack()
        with zipfile.ZipFile(self.bundle) as z:
            entries={k:z.read(k) for k in z.namelist()}
        oversize=self.root/'oversize.zip'
        self._repack({**entries,'oversize.bin':b'x'*(MAX_BYTES+1)},oversize)
        with self.assertRaises(KPPError):import_bundle(oversize,self.recovered)
        self.assertFalse(self.recovered.exists())

    def test_corrupt_internal_record_rejected_even_when_inventory_rehashed(self):
        self.pack()
        with zipfile.ZipFile(self.bundle) as z:
            entries={k:z.read(k) for k in z.namelist()}
        stage=json.loads(entries['candidate/kpp-reflex-stage.json'])
        stage['files']=42
        entries['candidate/kpp-reflex-stage.json']=(json.dumps(stage)+'\n').encode()
        manifest=json.loads(entries['bundle.json'])
        manifest['files']['candidate/kpp-reflex-stage.json']=hashlib.sha256(entries['candidate/kpp-reflex-stage.json']).hexdigest()
        entries['bundle.json']=(json.dumps(manifest)+'\n').encode()
        tampered=self.root/'forged-consistent.zip';self._repack(entries,tampered)
        with self.assertRaises(KPPError):import_bundle(tampered,self.recovered)
        self.assertFalse(self.recovered.exists())

    def test_rejects_symlink_in_source(self):
        try:
            (self.candidate/'escape.py').symlink_to('/etc/passwd')
        except (OSError,NotImplementedError):
            self.skipTest('Host does not permit creating symlinks')
        with self.assertRaises(KPPError):self.pack()

if __name__ == '__main__':unittest.main()
