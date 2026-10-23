"""Archived data must be explicit and pinned; live-source exclusions stay strict."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import archive_inventory as archive
import project_files as files


class ArchiveInventoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for name in files.ROOT_FILES:
            (self.root/name).write_text('synthetic\n')
        p = self.root/'archives/old/history.bundle'
        p.parent.mkdir(parents=True); p.write_bytes(b'synthetic inert bundle')
        self.name = p.relative_to(self.root).as_posix()
        self.record = {'schema':'mantle.archive-files/1', 'review_status':'PENDING',
                       'files':{self.name:hashlib.sha256(p.read_bytes()).hexdigest()}}
        self.write()

    def write(self):
        (self.root/archive.MANIFEST).write_text(json.dumps(self.record))

    def test_pinned_binary_exports_and_live_private_exclusions_remain(self):
        files.refresh(self.root)
        (self.root/'docs').mkdir(); (self.root/'docs/credentials.json').write_text('private sentinel')
        files.verify(self.root)
        target=self.root.parent/(self.root.name+'-export')
        self.addCleanup(__import__('shutil').rmtree,target,True)
        files.copy_project(self.root,target)
        self.assertEqual((target/self.name).read_bytes(),b'synthetic inert bundle')
        self.assertFalse((target/'docs/credentials.json').exists())
        self.assertFalse(files.allowed('docs/history.bundle'))

    def test_missing_modified_and_unlisted_files_refused(self):
        p=self.root/self.name
        p.write_bytes(b'changed')
        with self.assertRaises(files.ProjectError):archive.inventory(self.root)
        p.unlink()
        with self.assertRaises(files.ProjectError):archive.inventory(self.root)
        p.write_bytes(b'synthetic inert bundle')
        (p.parent/'.env').write_bytes(b'private sentinel')
        with self.assertRaises(files.ProjectError):archive.inventory(self.root)

    def test_unsafe_names_and_git_metadata_refused(self):
        for name in ('../outside','src/history.bundle','archives/.git/config',archive.MANIFEST):
            self.record['files']={name:'0'*64};self.write()
            with self.subTest(name=name),self.assertRaises(files.ProjectError):archive.inventory(self.root)

    def test_integrity_does_not_complete_publication_review(self):
        archive.inventory(self.root)
        with self.assertRaises(files.ProjectError):archive.inventory(self.root,require_reviewed=True)
        self.record['review_status']='PUBLIC_REVIEWED';self.write()
        archive.inventory(self.root,require_reviewed=True)

    def test_manifest_cannot_be_removed_to_bypass_checks(self):
        (self.root/archive.MANIFEST).unlink()
        with self.assertRaisesRegex(files.ProjectError,'require archives/ARCHIVE-FILES'):
            files.refresh(self.root)


if __name__=='__main__':unittest.main()
