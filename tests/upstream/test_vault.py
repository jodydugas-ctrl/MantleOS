import importlib.util, tempfile, unittest, zipfile, json, os, shutil
from pathlib import Path

from mantleos import vault_store as v
IDENTITY={'birth_sha256':'a'*64,'primer_sha256':'b'*64,'cartridge_id':'raven-test'}

class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'store.rvcar';self.start=v.initialize(self.p,IDENTITY)
    def insert(self,id='notes/hello.txt',data=b'Hello'):
        return v.commit(self.p,[(id,data,'text/plain','note',['test'],'sample')],anchor=self.start['sha256'])
    def test_initialization(self):self.assertEqual(v.verify(self.p)['generation'],0)
    def test_append_and_read(self):
        h=self.insert();self.assertEqual(v.retrieve(self.p,'notes/hello.txt'),b'Hello');self.assertEqual(h['generation'],1)
    def test_idempotent_put(self):
        h=self.insert();self.assertEqual(self.insert()['sha256'],h['sha256'])
    def test_reject_immutable_rewrite(self):
        self.insert()
        with self.assertRaisesRegex(ValueError,'Immutable'):self.insert(data=b'CHANGED')
    def test_reject_stale_writer(self):
        self.insert()
        with self.assertRaisesRegex(ValueError,'Stale'):v.commit(self.p,[('x',b'd','','',[],'')],expected=self.start['sha256'])
    def test_history_and_anchor(self):
        self.insert();self.insert('media/img.png',b'\x89PNG\r\n\x1a\n')
        self.assertEqual(v.verify(self.p,anchor=self.start['sha256'])['generation'],2)
    def test_bad_anchor(self):
        with self.assertRaisesRegex(ValueError,'ancestry'):v.verify(self.p,anchor='f'*64)
    def test_wrong_identity(self):
        with self.assertRaisesRegex(ValueError,'identity'):v.verify(self.p,{**IDENTITY,'cartridge_id':'other'})
    def test_corrupt_zip_blob(self):
        self.insert();evil=self.p.with_suffix('.bad');
        with zipfile.ZipFile(self.p) as src,zipfile.ZipFile(evil,'w') as dst:
            for name in src.namelist():dst.writestr(name,b'corrupted' if name.startswith('blobs/') else src.read(name))
        with self.assertRaisesRegex(ValueError,'corruption'):v.verify(evil)
    def test_missing_blob(self):
        self.insert();evil=self.p.with_suffix('.bad')
        with zipfile.ZipFile(self.p) as src,zipfile.ZipFile(evil,'w') as dst:
            for name in src.namelist():
                if not name.startswith('blobs/'):dst.writestr(name,src.read(name))
        with self.assertRaises(ValueError):v.verify(evil)
    def test_missing_history(self):
        self.insert();evil=self.p.with_suffix('.bad')
        with zipfile.ZipFile(self.p) as src,zipfile.ZipFile(evil,'w') as dst:
            for name in src.namelist():
                if not name.startswith('history/'):dst.writestr(name,src.read(name))
        with self.assertRaisesRegex(ValueError,'revision'):v.verify(evil)
    def test_zip_path_attack(self):
        self.insert();evil=self.p.with_suffix('.bad')
        with zipfile.ZipFile(self.p) as src,zipfile.ZipFile(evil,'w') as dst:
            for name in src.namelist():dst.writestr(name,src.read(name))
            dst.writestr('../escape',b'harm')
        with self.assertRaisesRegex(ValueError,'Unsafe'):v.verify(evil)
    def test_search(self):
        self.insert('artifacts/old-mantle-build.zip',b'data');self.assertEqual(len(v.search(self.p,'mantle')),1)
    def test_two_binary_types(self):
        self.insert('media/picture.png',b'\x89PNG\r\n\x1a\n');self.insert('chat/old.txt','café'.encode())
        self.assertEqual(v.retrieve(self.p,'media/picture.png'),b'\x89PNG\r\n\x1a\n')
        self.assertEqual(v.retrieve(self.p,'chat/old.txt').decode(),'café')
    def test_prior_generation_preserved(self):
        a=self.insert();b=self.insert('notes/second',b'2')
        self.assertEqual(json.loads(zipfile.ZipFile(self.p).read(f"history/{a['generation']:08d}-{a['sha256']}.json"))['sha256'],a['sha256'])
    def test_concurrent_working_epoch_branch_rejected(self):
        self.insert('ledger/working-epoch/record-0000001-'+'a'*16+'.json',b'first')
        with self.assertRaisesRegex(ValueError,'branch required'):
            self.insert('ledger/working-epoch/record-0000001-'+'b'*16+'.json',b'branch')
    def test_working_epoch_gap_rejected(self):
        with self.assertRaisesRegex(ValueError,'non-contiguous'):
            self.insert('ledger/working-epoch/record-0000002-'+'a'*16+'.json',b'gap')
    def test_duplicate_archive_entries(self):
        self.insert();evil=self.p.with_suffix('.bad')
        with zipfile.ZipFile(self.p) as src,zipfile.ZipFile(evil,'w') as dst:
            for name in src.namelist():dst.writestr(name,src.read(name))
            dst.writestr('INDEX.json',src.read('INDEX.json'))
        with self.assertRaisesRegex(ValueError,'Duplicate'):v.verify(evil)

if __name__=='__main__':unittest.main(verbosity=2)
