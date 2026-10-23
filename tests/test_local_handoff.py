"""Synthetic offline export/update boundaries; never invoke remote services."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0, str(TOOLS))
import project_files as files
import project_container as container
import kpp_upstream as updater


PASS = lambda candidate, logs: [{'name': 'synthetic-unit-validator', 'result': 'PASS'}]


class LocalHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mantle-local-handoff-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root, self.source = self.base/'mantle', self.base/'kpp'
        self.root.mkdir();self.source.mkdir()
        for name in files.ROOT_FILES:
            (self.root/name).write_bytes(b'synthetic fixture\n')
        (self.root/'.gitattributes').write_bytes(b'* -text\n')
        (self.root/'.gitignore').write_bytes(b'.work/\n__pycache__/\n')
        source = {'src/mantleos/anchors.py': b'# synthetic anchors\n',
                  'src/mantleos/cells.py': b'# synthetic cells\n',
                  'src/mantleos/tissue.py': b'# synthetic tissue\n',
                  'src/mantleos/kpp/resources/SYSTEMS.md': b'synthetic systems\n',
                  'src/mantleos/optional.py': b'# retained predecessor\r\n',
                  'tests/test_synthetic.py': b'# synthetic upstream test\n',
                  'LICENSE': b'synthetic license\n', 'THIRD-PARTY-NOTICES.md': b'synthetic attribution\n'}
        for name, content in source.items():
            path = self.source/name;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(content)
        self.pin_source()
        updater.seed(self.root, self.source)
        (self.root/'docs/LOCAL-HANDOFF.md').write_text('Synthetic handoff fixture.\n', encoding='utf-8')
        (self.root/'docs/product.md').write_bytes(b'MantleOS owned\n')
        files.refresh(self.root)

    def pin_source(self):
        pins = {p.relative_to(self.source).as_posix(): files.sha(p.read_bytes())
                for p in (self.source/'src').rglob('*') if p.is_file()}
        files.write_json(self.source/'SHARED-SOURCE.json', {'schema': 'mantle.shared-source/1',
                         'files': pins, 'source_digest': files.digest(pins)})

    def proposal(self):
        (self.source/'src/mantleos/anchors.py').write_bytes(b'# reviewed replacement\n')
        (self.source/'src/mantleos/optional.py').unlink()
        (self.source/'src/mantleos/new.py').write_bytes(b'# reviewed addition\n')
        self.pin_source()
        directory = self.base/'proposal'
        return directory, updater.plan(self.root, self.source, directory)

    def test_exact_inventory_and_export_private_exclusion(self):
        for name in ('credentials.json', '.env.local', 'old.zip', 'engram.jsonl', 'state.json'):
            (self.root/'docs'/name).write_bytes(b'PRIVATE SENTINEL')
        (self.root/'instruction-kit.zip').write_bytes(b'old kit')
        (self.root/'.work').mkdir();(self.root/'.work/private.txt').write_bytes(b'PRIVATE SENTINEL')
        files.verify(self.root)
        destination = self.base/'export'
        files.copy_project(self.root, destination)
        self.assertEqual(set(files.collect(destination)), set(files.read_json(self.root/files.MANIFEST)['files']))
        self.assertFalse(any(b'PRIVATE SENTINEL' in p.read_bytes() for p in destination.rglob('*') if p.is_file()))

    def test_export_rejects_missing_modified_and_unreviewed_source(self):
        path = self.root/'docs/product.md';original = path.read_bytes()
        for replacement in (None, b'modified'):
            if replacement is None:path.unlink()
            else:path.write_bytes(replacement)
            with self.assertRaises(files.ProjectError):files.copy_project(self.root, self.base/'export')
            path.write_bytes(original)
        (self.root/'docs/new.md').write_text('not inventoried')
        with self.assertRaises(files.ProjectError):files.verify(self.root)

    def test_export_rejects_unsafe_inventory_and_recursive_target(self):
        with self.assertRaises(files.ProjectError):files.copy_project(self.root, self.root/'docs/nested')
        value = files.read_json(self.root/files.MANIFEST);value['files']['../secret'] = '0'*64
        value['source_digest'] = files.digest(value['files']);files.write_json(self.root/files.MANIFEST, value)
        with self.assertRaises(files.ProjectError):files.verify(self.root)

    def test_add_replace_delete_apply_restore_and_product_preservation(self):
        prior = files.read_json(self.root/updater.LOCK)
        directory, plan = self.proposal()
        self.assertEqual({'add','replace','delete'}, {c['operation'] for c in plan['changes']})
        self.assertEqual('APPLIED', updater.apply(self.root,directory,self.source,reviewed=True,validator=PASS)['result'])
        self.assertFalse((self.root/'src/mantleos/optional.py').exists())
        self.assertEqual(b'MantleOS owned\n', (self.root/'docs/product.md').read_bytes())
        updater.check(self.root);files.verify(self.root)
        self.assertEqual('RESTORED', updater.restore(self.root,reviewed=True)['result'])
        self.assertEqual(prior, files.read_json(self.root/updater.LOCK))
        self.assertEqual(b'# retained predecessor\r\n', (self.root/'src/mantleos/optional.py').read_bytes())
        self.assertFalse((self.root/'src/mantleos/new.py').exists())
        self.assertEqual(2, len(list((self.root/'upstream/history').glob('*.json'))))
        files.verify(self.root);updater.check(self.root)

    def test_explicit_review_required(self):
        directory,_ = self.proposal()
        for action in (lambda:updater.apply(self.root,directory,self.source,validator=PASS),
                       lambda:updater.restore(self.root),lambda:updater.recover(self.root)):
            with self.assertRaises(files.ProjectError):action()

    def test_failed_validation_leaves_all_source_unchanged(self):
        directory,_ = self.proposal();before = files.collect(self.root)
        with self.assertRaisesRegex(files.ProjectError,'validation failed'):
            updater.apply(self.root,directory,self.source,reviewed=True,
                          validator=lambda *args:[{'result':'FAIL'}])
        self.assertEqual(before, files.collect(self.root));files.verify(self.root)

    def test_validation_cannot_repin_a_changed_candidate(self):
        directory,_ = self.proposal();before = files.collect(self.root)
        def change(candidate, logs):
            (candidate/'docs/product.md').write_bytes(b'changed by candidate tests')
            files.refresh(candidate);return PASS(candidate,logs)
        with self.assertRaisesRegex(files.ProjectError,'modified the staged'):
            updater.apply(self.root,directory,self.source,reviewed=True,validator=change)
        self.assertEqual(before, files.collect(self.root))

    def test_stale_destination_and_source_refused(self):
        directory,_ = self.proposal()
        (self.root/'docs/product.md').write_text('independent edit');files.refresh(self.root)
        with self.assertRaisesRegex(files.ProjectError,'Stale'):
            updater.apply(self.root,directory,self.source,reviewed=True,validator=PASS)
        directory2 = self.base/'new-plan';updater.plan(self.root,self.source,directory2)
        (self.source/'src/mantleos/new.py').write_bytes(b'upstream drift');self.pin_source()
        with self.assertRaisesRegex(files.ProjectError,'changed after planning'):
            updater.apply(self.root,directory2,self.source,reviewed=True,validator=PASS)

    def test_source_manifest_and_payload_tampering_refused(self):
        directory,_ = self.proposal()
        (directory/'payload/src/mantleos/new.py').write_bytes(b'tampered')
        with self.assertRaisesRegex(files.ProjectError,'payload was modified'):
            updater.apply(self.root,directory,self.source,reviewed=True,validator=PASS)
        (self.source/'src/mantleos/new.py').write_bytes(b'unpinned')
        with self.assertRaisesRegex(files.ProjectError,'pin mismatch'):updater.snapshot(self.source)

    def test_payload_extra_and_missing_refused(self):
        directory,_ = self.proposal();extra = directory/'payload/extra.py';extra.write_bytes(b'extra')
        with self.assertRaisesRegex(files.ProjectError,'missing or unpinned'):
            updater.apply(self.root,directory,self.source,reviewed=True,validator=PASS)
        extra.unlink();(directory/'payload/src/mantleos/new.py').unlink()
        with self.assertRaisesRegex(files.ProjectError,'missing or unpinned'):
            updater.apply(self.root,directory,self.source,reviewed=True,validator=PASS)

    def test_existing_local_owned_change_and_addition_conflict(self):
        (self.root/'src/mantleos/anchors.py').write_bytes(b'local edit')
        with self.assertRaisesRegex(files.ProjectError,'Local conflict'):updater.check(self.root)
        (self.root/'src/mantleos/anchors.py').write_bytes((self.source/'src/mantleos/anchors.py').read_bytes())
        (self.root/'src/mantleos/new.py').write_bytes(b'Mantle owned');files.refresh(self.root)
        with self.assertRaisesRegex(files.ProjectError,'conflicts'):self.proposal()

    def test_source_or_destination_changed_during_validation(self):
        directory,_ = self.proposal()
        def change(candidate,logs):
            (self.root/'docs/product.md').write_bytes(b'concurrent edit');files.refresh(self.root)
            return PASS(candidate,logs)
        with self.assertRaisesRegex(files.ProjectError,'changed during validation'):
            updater.apply(self.root,directory,self.source,reviewed=True,validator=change)
        self.assertEqual(b'concurrent edit',(self.root/'docs/product.md').read_bytes())
        updater.check(self.root)

    def test_publication_exception_restores_source_and_appends_recovery(self):
        # Runner temporary directories may have equivalent unresolved path aliases.
        self.root = self.root/'..'/self.root.name
        directory,_ = self.proposal();before = (self.root/'src/mantleos/anchors.py').read_bytes()
        original = updater._write_target;failed = False
        def fail_once(root,name,content):
            nonlocal failed
            if Path(root).resolve() == self.root.resolve() and name == 'src/mantleos/new.py' and not failed:
                failed = True;raise OSError('injected publication failure')
            return original(root,name,content)
        with patch.object(updater,'_write_target',fail_once), self.assertRaises(OSError):
            updater.apply(self.root,directory,self.source,reviewed=True,validator=PASS)
        self.assertTrue(failed, 'The publication failure must actually be injected')
        self.assertEqual(before,(self.root/'src/mantleos/anchors.py').read_bytes())
        updater.check(self.root);files.verify(self.root)
        self.assertFalse((self.root/updater.WORK/'pending.json').exists())
        self.assertEqual(1, len(list((self.root/'upstream/history').glob('recovery-*.json'))))

    def test_process_interruption_is_gated_and_recoverable(self):
        directory,_ = self.proposal();before = (self.root/'src/mantleos/anchors.py').read_bytes()
        script = '''import sys,os
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import kpp_upstream as u
original=u._write_target
def interrupted(root,name,content):
    original(root,name,content)
    if Path(root).resolve()==Path(sys.argv[2]).resolve() and name=='src/mantleos/anchors.py':os._exit(79)
u._write_target=interrupted
u.apply(Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4]),reviewed=True,
        validator=lambda *a:[{'result':'PASS','name':'synthetic-crash-probe'}])
'''
        result = subprocess.run([sys.executable,'-c',script,str(TOOLS),str(self.root),str(directory),str(self.source)],capture_output=True,timeout=60)
        self.assertEqual(79,result.returncode,result.stderr.decode(errors='replace'))
        with self.assertRaisesRegex(files.ProjectError,'interrupted'):updater.check(self.root)
        self.assertEqual('RESTORED',updater.recover(self.root,reviewed=True)['result'])
        self.assertEqual(before,(self.root/'src/mantleos/anchors.py').read_bytes())
        updater.check(self.root);files.verify(self.root)

    def test_concurrent_writer_rejected(self):
        with updater.writer(self.root),self.assertRaisesRegex(files.ProjectError,'writer is active'):
            with updater.writer(self.root):pass

    def test_modified_retained_source_refuses_restoration(self):
        directory,_ = self.proposal()
        result = updater.apply(self.root,directory,self.source,reviewed=True,validator=PASS)
        backup = self.root/updater.WORK/result['transaction']/'before/src/mantleos/anchors.py'
        backup.write_bytes(b'changed backup')
        with self.assertRaisesRegex(files.ProjectError,'backup is missing or changed'):
            updater.restore(self.root,reviewed=True)
        updater.check(self.root)

    def test_source_export_not_misrepresented_as_published_commit(self):
        value = updater.snapshot(self.source)
        self.assertIsNone(value['upstream']['base_commit'])
        self.assertFalse(value['upstream']['published_revision_verified'])
        self.assertEqual('local-source-export',value['upstream']['snapshot_kind'])

    def test_dirty_git_snapshot_records_base_without_publication_claim(self):
        container.git(self.source,'init','--template=','-b','main')
        container.git(self.source,'-c','user.name=Synthetic Test','-c','user.email=test@invalid',
                      '-c','commit.gpgsign=false','add','--all')
        container.git(self.source,'-c','user.name=Synthetic Test','-c','user.email=test@invalid',
                      '-c','commit.gpgsign=false','commit','-m','synthetic fixture')
        (self.source/'uncommitted.txt').write_text('dirty synthetic source')
        value = updater.snapshot(self.source)['upstream']
        self.assertTrue(value['dirty']);self.assertEqual('local-working-snapshot',value['snapshot_kind'])
        self.assertEqual(40,len(value['base_commit']));self.assertFalse(value['published_revision_verified'])

    def test_git_container_and_bundle_roundtrip_exact_bytes_no_remotes(self):
        output = self.base/'container'
        result = container.package(self.root,output,self.base/'handoff.zip')
        self.assertEqual('PASS',result['result'])
        clone = self.base/'clone'
        container.git(self.base,'clone',str(output/'MantleOS.bundle'),str(clone))
        container.git(clone,'remote','remove','origin')
        self.assertEqual(result['commit'],container.repository_check(clone)['commit'])
        self.assertEqual(b'# retained predecessor\r\n',(clone/'src/mantleos/optional.py').read_bytes())
        self.assertEqual('',container.git(clone,'remote'))
        container.verify_container(output)
        (output/'HANDOFF.md').write_bytes(b'modified')
        with self.assertRaises(files.ProjectError):container.verify_container(output)


if __name__ == '__main__':
    unittest.main()
