"""File-only upload bootstrap regressions. Language packets here are scripted."""
from contextlib import closing
import hashlib,io,json,os,sqlite3,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from mantleos import journal,journal_bootstrap,specimens

class UploadTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
  specimens.fresh(cls.root/'body',name='Synthetic Upload')
  cls.seed=cls.root/'seed.engram';journal.from_body(cls.root/'body',cls.seed)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_artifact_only_boot_and_continuity(self):
  import shutil
  host=self.root/'isolated';host.mkdir();carrier=host/'uploaded.engram';shutil.copyfile(self.seed,carrier)
  with closing(sqlite3.connect(carrier)) as db, db:meta={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM meta')}
  self.assertEqual(hashlib.sha256(meta['bootstrap'].encode()).hexdigest(),meta['bootstrap_sha256'])
  boot=host/'bootstrap.py';boot.write_text(meta['bootstrap'],encoding='utf8')
  env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','MANTLE_RAVEN_SOURCE')};env.update(TEMP=str(host),TMP=str(host))
  def run(script,*args):
   r=subprocess.run([sys.executable,'-I','-S',str(script),*map(str,args)],cwd=host,env=env,capture_output=True,text=True,encoding='utf8')
   self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
  mounted=host/'mounted';result=run(boot,carrier,mounted)
  self.assertFalse(result['runtime_executed']);launcher=mounted/'journal_host.py'
  frame=run(launcher,'open',carrier,'--request-id','first','--model-id','SCRIPTED_FIXTURE','--user','Remember cobalt')
  self.assertEqual(frame['payload']['primer']['sha256'],meta['primer']['sha256'])
  packet=host/'packet.json';packet.write_text(json.dumps({'kind':'reply','reply':'Recorded cobalt.','observation_sha256':None}))
  committed=run(launcher,'submit',carrier,'--request-id','first','--proposal',packet,'--allow-release')
  self.assertEqual(committed['reply'],'Recorded cobalt.')
  saved=host/'saved.engram';run(launcher,'export',carrier,'--output',saved)
  second=host/'second';run(boot,saved,second)
  frame=run(second/'journal_host.py','open',saved,'--request-id','second','--model-id','SCRIPTED_FIXTURE','--user','What did I ask you to remember?')
  self.assertIn('cobalt',json.dumps(frame['payload']['memory']))
  self.assertEqual(run(second/'journal_host.py','inspect',saved)['identity'],meta['identity'])
 def test_corrupt_snapshot_refused_before_extraction(self):
  import shutil
  carrier=self.root/'corrupt.engram';shutil.copyfile(self.seed,carrier)
  with closing(sqlite3.connect(carrier)) as db, db:
   db.execute('DROP TRIGGER retain_objects_update');db.execute("UPDATE objects SET payload=X'00'")
  target=self.root/'bad-runtime'
  with self.assertRaises(ValueError):journal_bootstrap.extract(carrier,target)
  self.assertFalse(target.exists())
 def test_unsafe_snapshot_path_refused(self):
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:z.writestr('../escape.py','bad')
  blob=raw.getvalue();carrier=self.root/'unsafe.engram'
  with closing(sqlite3.connect(carrier)) as db, db:
   db.executescript('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE objects(sha256 TEXT PRIMARY KEY,payload BLOB);')
   h=hashlib.sha256(blob).hexdigest();db.executemany('INSERT INTO meta VALUES (?,?)',[('schema',json.dumps(journal.SCHEMA)),('snapshot',json.dumps(h))]);db.execute('INSERT INTO objects VALUES (?,?)',(h,blob))
  with self.assertRaises(ValueError):journal_bootstrap.extract(carrier,self.root/'unsafe-runtime')
  self.assertFalse((self.root/'escape.py').exists())
 def test_old_journal_export_adds_upload_contract(self):
  import shutil
  carrier=self.root/'old-carrier.engram';shutil.copyfile(self.seed,carrier)
  with closing(sqlite3.connect(carrier)) as db, db:
   db.execute("DELETE FROM meta WHERE key IN ('host_contract','bootstrap','bootstrap_sha256')")
  saved=self.root/'upgraded.engram'
  with journal.Journal(carrier) as source:
   before=source.status();source.export(saved)
  with journal.Journal(saved) as receiving:
   self.assertEqual(receiving.status()['identity'],before['identity'])
   self.assertEqual(receiving.status()['primer_sha256'],before['primer_sha256'])
   self.assertEqual(receiving.head(),before['head'])
  with closing(sqlite3.connect(saved)) as db:
   contract=json.loads(db.execute("SELECT value FROM meta WHERE key='host_contract'").fetchone()[0])
  self.assertEqual(contract['schema'],'mantle.journal-host-contract/1')
 def test_bootstrap_metadata_tamper_rejected(self):
  import shutil
  carrier=self.root/'bad-contract.engram';shutil.copyfile(self.seed,carrier)
  with closing(sqlite3.connect(carrier)) as db, db:db.execute('UPDATE meta SET value=? WHERE key=?',(json.dumps('bad code'),'bootstrap'))
  with self.assertRaises(ValueError):journal.Journal(carrier)

if __name__=='__main__':unittest.main()
