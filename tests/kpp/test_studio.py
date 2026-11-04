"""Heart and MIND protocol tests; full eight-limb evidence is separate."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest
from mantleos import studio, specimens, journal
from mantleos.limbs import LimbSet


class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();base=Path(cls.tmp.name)
        body=base/'body';specimens.fresh(body,name='Synthetic Studio test persona')
        cls.seed=base/'prime.engram';journal.from_body(body,cls.seed)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):
        self.tmpcase=tempfile.TemporaryDirectory();self.addCleanup(self.tmpcase.cleanup)
        self.nest=Path(self.tmpcase.name)/'nest';studio.initialize_heart(self.nest,b'Synthetic founding source\r\n')
        shutil.copyfile(self.seed,self.nest/'prime.engram')
        LimbSet.create(self.nest/'limb-runtime',[],worker_limit=0,approved=True)
        studio.phase(self.nest,True)
        self.addCleanup(self.close_journal)

    def close_journal(self):
        key=str((self.nest/'prime.engram').resolve());j=studio._sessions.pop(key,None)
        if j:j.close()

    def test_heart_events_are_durable_bounded_and_not_model_calls(self):
        studio.event(self.nest,'pain',{'fixture':'missing'},'pain-one')
        self.assertEqual(studio.event(self.nest,'pain',{'fixture':'missing'},'pain-one')['status'],'REPLAY')
        self.assertEqual(studio.event(self.nest,'pain',{},'pain-two')['status'],'COALESCED')
        self.assertEqual(studio.status(self.nest)['pending_mind'],0)
        with studio.database(self.nest) as db:db.execute("UPDATE settings SET value='0' WHERE key='next_beat'")
        self.assertTrue(studio.pulse(self.nest)['scheduled'])
        self.assertFalse(studio.pulse(self.nest)['scheduled'])

    def test_exact_commit_replay_and_stasis(self):
        f=studio.conversation(self.nest,'Remember amber','user-one','SYNTHETIC_FIXTURE')
        self.assertIn('Synthetic Studio test persona',f['frame']['payload']['primer']['content'])
        p={'kind':'reply','reply':'Amber retained.','observation_sha256':None}
        a=studio.submit(self.nest,'user-one',p);b=studio.submit(self.nest,'user-one',None)
        self.assertEqual(a['reply'],b['reply']);self.assertTrue(b['receipt']['replayed'])
        studio.phase(self.nest,False)
        self.assertEqual(studio.conversation(self.nest,'Remember amber','user-one','SYNTHETIC_FIXTURE')['status'],'STASIS')
        with self.assertRaises(ValueError):studio.submit(self.nest,'user-one',None)

    def test_duplicate_input_and_second_pending_request_rejected(self):
        studio.conversation(self.nest,'First','user-one','SYNTHETIC_FIXTURE')
        with self.assertRaises(ValueError):studio.conversation(self.nest,'Changed','user-one','SYNTHETIC_FIXTURE')
        with self.assertRaises(ValueError):studio.conversation(self.nest,'Second','user-two','SYNTHETIC_FIXTURE')

    def test_checked_observation_must_bind_reply(self):
        studio.conversation(self.nest,'Inspect','user-one','SYNTHETIC_FIXTURE')
        frame=studio.submit(self.nest,'user-one',{'kind':'action','capability':'body.status','arguments':{}})
        with self.assertRaises(ValueError):studio.submit(self.nest,'user-one',{'kind':'reply','reply':'Wrong observation','observation_sha256':'0'*64})
        result=studio.submit(self.nest,'user-one',{'kind':'reply','reply':'Checked result.','observation_sha256':frame['frame']['payload']['observation_sha256']})
        self.assertEqual(result['reply'],'Checked result.')

    def test_changed_controller_preparation_denied(self):
        studio.conversation(self.nest,'First','user-one','SYNTHETIC_FIXTURE')
        with studio.database(self.nest) as db:
            frame=json.loads(db.execute('SELECT frame FROM mind').fetchone()[0]);frame['controller_pin']='0'*64
            db.execute('UPDATE mind SET frame=?',(json.dumps(frame),))
        with self.assertRaises(ValueError):studio.submit(self.nest,'user-one',{'kind':'reply','reply':'Stale','observation_sha256':None})

    def test_missing_or_changed_source_binding_fails_closed(self):
        with studio.database(self.nest) as db:db.execute("UPDATE settings SET value=? WHERE key='controller_pin'",(json.dumps('0'*64),))
        with self.assertRaises(ValueError):studio.status(self.nest)

    def test_canonical_commit_recovers_controller_interruption(self):
        studio.conversation(self.nest,'First','user-one','SYNTHETIC_FIXTURE')
        with studio.database(self.nest) as db:db.execute("CREATE TRIGGER interrupt_reply BEFORE UPDATE ON mind WHEN NEW.phase='COMMITTED' BEGIN SELECT RAISE(ABORT,'interruption'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):studio.submit(self.nest,'user-one',{'kind':'reply','reply':'Durable exact reply','observation_sha256':None})
        with studio.database(self.nest) as db:db.execute('DROP TRIGGER interrupt_reply')
        result=studio.committed_result(self.nest,'user-one')
        self.assertEqual(result['reply'],'Durable exact reply')

    def test_founding_file_change_is_rejected(self):
        (self.nest/'founding.txt').write_bytes(b'changed')
        with self.assertRaises(ValueError):studio.status(self.nest)

    def test_boot_reuses_verified_sessions_without_model_or_handlers(self):
        first=studio.boot(self.nest);second=studio.boot(self.nest)
        self.assertEqual(first['sessions'],1);self.assertEqual(second['model_calls'],0)
        self.assertEqual(len(studio._session(self.nest/'prime.engram').records),0)

    def test_public_persona_is_verified_metadata_not_a_fixed_ui_label(self):
        self.assertIsNone(studio.status(self.nest)['persona'])
        studio.boot(self.nest)
        verified=studio._session(self.nest/'prime.engram').status()
        self.assertEqual(studio.status(self.nest)['persona'],{
            'name':verified['persona'],'identity':verified['identity'],
            'primer_sha256':verified['primer_sha256']})
        self.assertNotEqual(verified['persona'],'Frame-Preserving Cuttlefish')

    def test_foreign_append_reuses_snapshot_and_still_checks_metadata(self):
        from unittest.mock import patch
        import sqlite3
        live=studio._session(self.nest/'prime.engram')
        with journal.Journal(self.nest/'prime.engram') as other:
            other.append_record('observation','synthetic',{'text':'foreign append'},expected_head=other.head())
        with patch('mantleos.cartridge.unpack',side_effect=AssertionError('Unchanged snapshot unpacked')):
            self.assertEqual(live.status()['records'],1)
        db=sqlite3.connect(self.nest/'prime.engram')
        try:db.execute("UPDATE meta SET value='{}' WHERE key='primer'");db.commit()
        finally:db.close()
        with self.assertRaises(ValueError):live.status()
