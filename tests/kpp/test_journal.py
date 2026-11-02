import json,sqlite3,tempfile,unittest
from pathlib import Path
from mantleos import journal,specimens,anchor_language

class JournalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.base=Path(cls.tmp.name)
  cls.body=cls.base/'body';specimens.fresh(cls.body,name='Synthetic Finch')
  cls.seed=cls.base/'seed.engram';journal.from_body(cls.body,cls.seed)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):
  import shutil,uuid
  self.file=self.base/(uuid.uuid4().hex+'.engram');shutil.copyfile(self.seed,self.file);self.j=journal.Journal(self.file)
 def tearDown(self):self.j.close()
 def opened(self,rid='test',text='Remember cobalt'):
  return self.j.open(text,request_id=rid,model_id='SYNTHETIC_FIXTURE')
 def reply(self,text='I remember cobalt.',obs=None):return {'kind':'reply','reply':text,'observation_sha256':obs}
 def grant(self,a,n):return True
 def test_commit_replay_and_reopen(self):
  frame=self.opened();self.assertEqual(frame['payload']['primer']['content'],self.j.founding['compiled'])
  result=self.j.submit('test',self.reply(),broker=self.grant)
  self.assertEqual(result['language_packets'],1);self.assertFalse(result['replayed'])
  self.assertTrue(self.j.submit('test',None,broker=self.grant)['replayed'])
  self.assertEqual(len(self.j.records),1)
  with journal.Journal(self.file) as other:self.assertTrue(other.recall('cobalt')['matches'])
  with self.assertRaises(ValueError):self.opened(text='different')
 def test_denied_release(self):
  self.opened()
  with self.assertRaises(PermissionError):self.j.submit('test',self.reply())
  self.assertEqual(len(self.j.records),0)
 def test_action_bindings_and_limit(self):
  self.opened();f=self.j.submit('test',{'kind':'action','capability':'body.status','arguments':{}},broker=self.grant)
  self.assertEqual(f['payload']['observation']['stage'],'VERIFIED')
  with self.assertRaises(ValueError):self.j.submit('test',self.reply(obs='forged'),broker=self.grant)
  with self.assertRaises(ValueError):self.j.submit('test',{'kind':'action','capability':'body.status','arguments':{}},broker=self.grant)
  self.assertEqual(self.j.submit('test',self.reply(obs=f['payload']['observation_sha256']),broker=self.grant)['language_packets'],2)
 def test_denied_action(self):
  self.opened();f=self.j.submit('test',{'kind':'action','capability':'body.status','arguments':{}})
  self.assertEqual(f['payload']['observation']['stage'],'FAILED')
 def test_stale_and_unknown_actions(self):
  self.opened()
  with self.assertRaises(ValueError):self.j.submit('test',{'kind':'action','capability':'shell','arguments':{}},broker=self.grant)
  self.opened('other');self.j.submit('other',self.reply(),broker=self.grant)
  with self.assertRaises(ValueError):self.j.submit('test',self.reply(),broker=self.grant)
 def test_corruption_and_immutability(self):
  self.opened();self.j.submit('test',self.reply(),broker=self.grant)
  with self.assertRaises(sqlite3.IntegrityError):self.j.db.execute('UPDATE records SET raw=?',('{}',))
  db=sqlite3.connect(self.file);db.execute('DROP TRIGGER retain_records_update');db.execute("UPDATE records SET raw='{}'");db.commit();db.close()
  with self.assertRaises((ValueError,KeyError)):self.j.status()
 def test_export_roundtrip(self):
  self.opened();self.j.submit('test',self.reply(),broker=self.grant)
  for fmt,ext in [('journal','engram'),('cartridge','vcw'),('chroma','png')]:
   output=self.file.with_suffix('.saved.'+ext);self.j.export(output,format=fmt)
   if fmt=='journal':
    with journal.Journal(output) as other:self.assertEqual(other.records,self.j.records)
   else:
    from mantleos.kernel import verify_restored_output
    import uuid
    body=self.base/uuid.uuid4().hex;verify_restored_output(output,body,format=fmt)
    from mantleos.engram import read
    self.assertEqual(read(body/'ENGRAM.jsonl'),self.j.records)
    converted=body.with_suffix('.engram');journal.from_body(body,converted)
    with journal.Journal(converted) as restored:self.assertTrue(restored.submit('test',None,broker=self.grant)['replayed'])
 def test_recovery_and_failed_export(self):
  self.opened()
  with self.assertRaises(PermissionError):self.j.recover('test')
  self.j.recover('test',reviewed=True)
  with self.assertRaises(ValueError):self.j.submit('test',self.reply(),broker=self.grant)
  with self.assertRaises(FileExistsError):self.j.export(self.file)
 def test_anchor_redefinition(self):
  r=json.loads(json.dumps(self.j.register));r['anchors'][0]['singularity']='changed'
  with self.assertRaises(ValueError):anchor_language.validate_register(r)
 def test_atomic_failure(self):
  self.opened()
  self.j.db.execute("CREATE TRIGGER fail_request BEFORE INSERT ON requests BEGIN SELECT RAISE(ABORT,'injected'); END")
  with self.assertRaises(sqlite3.IntegrityError):self.j.submit('test',self.reply(),broker=self.grant)
  self.assertEqual(self.j.head(),journal.ZERO);self.assertEqual(len(self.j.records),0)
 def test_incremental_index_matches_rebuild(self):
  from mantleos.projection import build
  first=self.j.append_record('face','synthetic',{'voice':'first'},expected_head=self.j.head())
  second=self.j.append_record('face','synthetic',{'voice':'second'},expected_head=self.j.head())
  self.j.append_record('memory','synthetic',{'text':'withdraw second','supersedes':second['id']},expected_head=self.j.head())
  self.assertEqual(self.j.index,build(self.j.records))
  self.assertEqual(self.j.records[self.j.index['active_face']]['id'],first['id'])
 def test_missing_replay_index(self):
  self.opened();self.j.submit('test',self.reply(),broker=self.grant)
  db=sqlite3.connect(self.file);db.execute('DELETE FROM requests');db.commit();db.close()
  with self.assertRaisesRegex(ValueError,'replay index'):self.j.status()
 def test_pending_founding_tamper(self):
  self.opened();row=self.j.db.execute('SELECT raw FROM pending').fetchone();p=json.loads(row[0])
  p['frame']['payload']['primer']['content']='forged'
  self.j.db.execute('UPDATE pending SET raw=?',(journal.canon(p),))
  with self.assertRaises(ValueError):self.j.submit('test',self.reply(),broker=self.grant)
 def test_default_setup_and_custom_founding(self):
  import os
  from unittest.mock import patch
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaisesRegex(ValueError,'Raven setup'):journal.create(self.base/'missing.engram')

if __name__=='__main__':unittest.main()
