"""Reviewed carrier exceptions never authorize unrelated private source files."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

# This file is copied into MantleOS/tests after the reviewed promotion completes.
ROOT=(Path(__file__).resolve().parents[1] if Path(__file__).parent.name=='tests'
      else Path(__file__).resolve().parent/'github-consolidation/MantleOS')
sys.path.insert(0,str(ROOT/'tools'))
import project_files as files

class ReviewedEngramExports(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for name in files.ROOT_FILES:(self.root/name).write_bytes(b'synthetic\n')
        module=self.root/'src/mantleos/kpp/artifacts.py';module.parent.mkdir(parents=True)
        source=ROOT/'src/mantleos/kpp/artifacts.py'
        if not source.exists():source=ROOT.parent/'KPP-review/src/mantleos/kpp/artifacts.py'
        module.write_bytes(source.read_bytes())
        self.folder=self.root/'examples/engrams/artifacts';self.folder.mkdir(parents=True)
        pins={}
        for name in ('raven-fresh.vcw','raven-fresh.vcw.png'):
            (self.folder/name).write_bytes(b'synthetic reviewed payload')
            pins[name]=hashlib.sha256((self.folder/name).read_bytes()).hexdigest()
        self.record={'schema':'kpp.reviewed-engram-examples/1','review':'PUBLIC_REVIEWED','files':pins}
        self.write()

    def write(self):(self.folder/'MANIFEST.json').write_text(json.dumps(self.record))

    def test_only_explicit_assets_enter_handoffs(self):
        (self.root/'docs').mkdir()
        (self.root/'docs/private.vcw').write_bytes(b'PRIVATE')
        (self.root/'docs/credentials.json').write_bytes(b'PRIVATE')
        manifest=files.refresh(self.root)
        self.assertIn('examples/engrams/artifacts/raven-fresh.vcw',manifest['files'])
        self.assertNotIn('docs/private.vcw',manifest['files'])
        self.assertNotIn('docs/credentials.json',manifest['files'])
        with tempfile.TemporaryDirectory() as parent:
            out=Path(parent)/'handoff';files.copy_project(self.root,out)
            self.assertTrue((out/'examples/engrams/artifacts/raven-fresh.vcw').is_file())
            self.assertFalse((out/'docs/credentials.json').exists())

    def test_extra_and_pending_assets_refused(self):
        extra=self.folder/'private.vcw';extra.write_bytes(b'PRIVATE')
        with self.assertRaises(ValueError):files.refresh(self.root)
        extra.unlink();self.record['review']='PENDING';self.write()
        with self.assertRaises(ValueError):files.refresh(self.root)

    def test_modified_and_missing_payloads_refused(self):
        path=self.folder/'raven-fresh.vcw';path.write_bytes(b'changed')
        with self.assertRaises(ValueError):files.refresh(self.root)
        path.unlink()
        with self.assertRaises((ValueError,OSError)):files.refresh(self.root)

if __name__=='__main__':unittest.main()
