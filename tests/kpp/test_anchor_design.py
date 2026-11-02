import copy, json, sqlite3, tempfile, unittest, shutil, uuid
from contextlib import closing
from pathlib import Path
from mantleos import anchor_design as d, anchors, journal, specimens
from mantleos.kpp.core import validate_recipe

class DesignTests(unittest.TestCase):
 def setUp(self):self.design=d.journal_design()
 def test_constants_rehashed_tampering_rejected(self):
  a=self.design['applications'][0];a['singularity']='Invented';a['sha256']=d.c.digest({k:v for k,v in a.items() if k!='sha256'})
  with self.assertRaises(ValueError):d.validate(self.design)
 def test_bad_flow_and_duplicate_owner(self):
  self.design['flows'][0]['to']='missing'
  with self.assertRaises(ValueError):d.validate(self.design)
  self.design=d.journal_design();self.design['state'].append({'id':'experience','owner':'N-HOST'})
  with self.assertRaises(ValueError):d.validate(self.design)
 def test_non_identifier_reference_rejected(self):
  self.design['flows'][0]['to']={}
  with self.assertRaises(ValueError):d.validate(self.design)
 def test_missing_and_wrong_guard(self):
  del self.design['effects'][0]['guard']
  with self.assertRaises(ValueError):d.validate(self.design)
  self.design=d.journal_design();self.design['effects'][0]['guard']='N-HOST'
  with self.assertRaises(ValueError):d.validate(self.design)
 def test_render_and_economy_are_advisory(self):
  self.assertEqual(d.render(self.design),d.render(copy.deepcopy(self.design)))
  self.assertIn('NOT AN EXECUTABLE',d.render(self.design));self.assertEqual(d.review(self.design)['authority'],'NONE')
 def test_recipe_coverage_and_old_recipe(self):
  root=Path(__file__).resolve().parents[1]
  if not (root/'src/mantleos').is_dir():root=root.parent
  resources=root/'src/mantleos/kpp/resources/recipes'
  old=json.loads((resources/'journal-engram.json').read_text('utf8'));validate_recipe(old);self.assertNotIn('anchor_design',old)
  recipe=json.loads((resources/'journal-engram-design.json').read_text('utf8'));validate_recipe(recipe)
  recipe['anchors'][0]['design_anchors']=['missing']
  with self.assertRaises(ValueError):validate_recipe(recipe)
  recipe['anchors'][0]['design_anchors']=[]
  with self.assertRaises(ValueError):validate_recipe(recipe)

class JournalDesignTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.base=Path(cls.tmp.name)
  cls.body=cls.base/'body';specimens.fresh(cls.body,name='Synthetic Finch')
  cls.seed=cls.base/'seed.engram';journal.from_body(cls.body,cls.seed)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):
  self.file=self.base/(uuid.uuid4().hex+'.engram');shutil.copyfile(self.seed,self.file)
 def test_projection_full_primer_and_stale_design(self):
  with journal.Journal(self.file) as j:
   frame=j.open('Remember amber',request_id='one',model_id='SYNTHETIC')
   self.assertEqual(frame['payload']['primer']['content'],j.founding['compiled'])
   self.assertEqual(frame['payload']['anchor_design']['sha256'],j.design_digest)
   design=copy.deepcopy(j.design);design['purpose']='Reviewed revised design'
   with closing(sqlite3.connect(self.file)) as db:
    db.execute("UPDATE meta SET value=? WHERE key='anchor_design'",(journal.canon(design),));db.commit()
   with self.assertRaises(ValueError):j.submit('one',{'kind':'reply','reply':'Amber remembered.','observation_sha256':None},broker=lambda a,n:True)
   self.assertEqual(len(j.records),0)
 def test_legacy_explicit_export_and_roundtrip(self):
  with closing(sqlite3.connect(self.file)) as db:
   db.execute("DELETE FROM meta WHERE key='anchor_design'");db.commit()
  with journal.Journal(self.file) as j:
   self.assertIsNone(j.design);saved=self.file.with_suffix('.saved.engram');j.export(saved)
  with journal.Journal(saved) as j:
   self.assertEqual(j.design,d.journal_design())
   for fmt in ['cartridge','chroma']:
    target=self.base/(uuid.uuid4().hex+('.png' if fmt=='chroma' else '.vcw'));j.export(target,format=fmt)
    from mantleos.kernel import verify_restored_output
    body=self.base/uuid.uuid4().hex;verify_restored_output(target,body,format=fmt)
    self.assertEqual(json.loads((body/'ANCHOR-DESIGN.json').read_text('utf8')),j.design)
 def test_frame_projection_tamper_and_exact_replay(self):
  with journal.Journal(self.file) as j:
   j.open('Hello',request_id='one',model_id='SYNTHETIC')
   proposal={'kind':'reply','reply':'Hello from the committed engine.','observation_sha256':None}
   result=j.submit('one',proposal,broker=lambda a,n:True)
   self.assertEqual(result['language_packets'],1)
   self.assertEqual(j.submit('one',None,broker=lambda a,n:True)['reply'],proposal['reply'])
   self.assertEqual(j.records[-1]['body']['design_sha256'],j.design_digest)
