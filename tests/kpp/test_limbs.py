import copy
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest

from mantleos import limbs, journal, specimens

entered=threading.Event()
release=threading.Event()
barrier=None


def echo(value):return {'observed':value}


def hold(value):
    entered.set()
    if not release.wait(10):raise RuntimeError('Test synchronization timeout')
    return value


def overlap(value):
    barrier.wait(timeout=10)
    return value


class LimbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.base=Path(cls.tmp.name)
        cls.seeds=[]
        for n in range(2):
            body=cls.base/('body-'+str(n));specimens.fresh(body,name='Synthetic limb '+str(n))
            path=cls.base/('seed-'+str(n)+'.engram');journal.from_body(body,path);cls.seeds.append(path)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):
        self.case=tempfile.TemporaryDirectory();self.addCleanup(self.case.cleanup)
        self.root=Path(self.case.name);self.paths=[]
        for n,seed in enumerate(self.seeds):
            p=self.root/(str(n)+'.engram');shutil.copyfile(seed,p);self.paths.append(p)
        entered.clear();release.clear()

    def create(self,count=2,workers=2,handler=echo):
        members=[{'id':'L'+str(n),'journal':str(self.paths[n]),'grants':['observe']} for n in range(count)]
        return limbs.LimbSet.create(self.root/'runtime',members,worker_limit=workers,approved=True,handlers={'observe':handler})

    def test_zero_and_single_are_opt_in(self):
        self.assertEqual(limbs.recipe_composition({})['workers'],0)
        empty=self.create(0,0);self.assertEqual(empty.status()['members'],[])
        self.assertEqual(empty.run_one({},broker=lambda *a:True)['status'],'BUSY')

    def test_duplicate_and_memory_isolation(self):
        runtime=self.create()
        runtime.submit('L0','observe',{'color':'amber'},request_id='one')
        runtime.run_one({'observe':echo},broker=lambda *a:True)
        self.assertTrue(runtime.submit('L0','observe',{'color':'amber'},request_id='one')['replay'])
        with self.assertRaises(ValueError):runtime.submit('L0','observe',{'color':'cobalt'},request_id='one')
        with journal.Journal(self.paths[0]) as a,journal.Journal(self.paths[1]) as b:
            self.assertEqual(len(a.records),2);self.assertEqual(b.records,[])

    def test_denied_handler_and_disabled_limb(self):
        runtime=self.create(1,1)
        with self.assertRaises(PermissionError):runtime.submit('L0','execute',{},request_id='one')
        runtime.submit('L0','observe',{},request_id='one')
        with self.assertRaises(PermissionError):runtime.run_one({'observe':echo},broker=lambda *a:False)
        runtime.enable('L0',False,approved=True)
        with self.assertRaises(PermissionError):runtime.submit('L0','observe',{},request_id='two')

    def test_results_reject_forged_metadata(self):
        runtime=self.create(1,1)
        runtime.submit('L0','observe',{'color':'amber'},request_id='one')
        runtime.run_one({'observe':echo},broker=lambda *a:True)
        self.assertEqual(runtime.results(broker=lambda *a:True)[0]['value'],{'observed':{'color':'amber'}})
        with runtime.db() as db:
            db.execute('UPDATE tasks SET result=?',(json.dumps({'value':'forged','record_sha256':'0'*64}),))
        with self.assertRaises(ValueError):runtime.results(broker=lambda *a:True)

    def test_revocation_during_work_retains_review_state(self):
        runtime=self.create(1,1,hold)
        runtime.submit('L0','observe',{},request_id='one')
        errors=[]
        def worker():
            try:runtime.run_one({'observe':hold},broker=lambda *a:True)
            except PermissionError:errors.append('revoked')
        t=threading.Thread(target=worker);t.start()
        try:
            self.assertTrue(entered.wait(10));runtime.enable('L0',False,approved=True)
        finally:release.set();t.join(10)
        self.assertEqual(errors,['revoked'])
        self.assertEqual(runtime.recover(reviewed=True)['tasks'][0]['phase'],'NEEDS_REVIEW')

    def test_active_recovery_refused_and_no_repeated_handler(self):
        runtime=self.create(1,1,hold)
        runtime.submit('L0','observe',{'number':1},request_id='one')
        errors=[]
        def worker():
            try:runtime.run_one({'observe':hold},broker=lambda *a:True)
            except Exception as e:errors.append(e)
        t=threading.Thread(target=worker);t.start()
        try:
            self.assertTrue(entered.wait(10))
            with self.assertRaises(OSError):runtime.recover(reviewed=True)
        finally:release.set();t.join(10)
        self.assertEqual(errors,[])
        self.assertEqual(runtime.run_one({'observe':hold},broker=lambda *a:True)['status'],'IDLE')

    def test_registered_identity_cannot_be_replaced(self):
        runtime=self.create(1,1)
        runtime.submit('L0','observe',{},request_id='one')
        shutil.copyfile(self.paths[1],self.paths[0])
        with self.assertRaises(ValueError):runtime.run_one({'observe':echo},broker=lambda *a:True)
        self.assertEqual(runtime.status()['tasks'][0]['phase'],'NEEDS_REVIEW')

    def test_computation_is_outside_global_writer(self):
        runtime=self.create(2,2,hold)
        runtime.submit('L0','observe',{},request_id='one')
        runtime.submit('L1','observe',{},request_id='two')
        workers=[threading.Thread(target=lambda:runtime.run_one({'observe':hold},broker=lambda *a:True)) for _ in range(2)]
        for t in workers:t.start()
        try:
            self.assertTrue(entered.wait(10))
            # Status and a third queued intention remain available during computation.
            runtime.submit('L1','observe',{'later':True},request_id='three')
            self.assertEqual(len(runtime.status()['tasks']),3)
        finally:
            release.set()
            for t in workers:t.join(10)

    def test_actual_overlap_and_worker_budget(self):
        global barrier
        barrier=threading.Barrier(2)
        runtime=self.create(2,2,overlap)
        for n in range(2):runtime.submit('L'+str(n),'observe',{'n':n},request_id='task-'+str(n))
        errors=[]
        def worker():
            try:runtime.run_one({'observe':overlap},broker=lambda *a:True)
            except Exception as e:errors.append(e)
        a=threading.Thread(target=worker);b=threading.Thread(target=worker)
        a.start();b.start();a.join(20);b.join(20)
        self.assertFalse(a.is_alive() or b.is_alive());self.assertEqual(errors,[])
        self.assertTrue(all(t['phase']=='RESULT' for t in runtime.status()['tasks']))

    def test_single_worker_prevents_overlapping_callbacks(self):
        runtime=self.create(2,1,hold)
        for n in range(2):runtime.submit('L'+str(n),'observe',{},request_id='task-'+str(n))
        t=threading.Thread(target=lambda:runtime.run_one({'observe':hold},broker=lambda *a:True));t.start()
        try:
            self.assertTrue(entered.wait(10))
            self.assertEqual(runtime.run_one({'observe':hold},broker=lambda *a:True)['status'],'BUSY')
        finally:release.set();t.join(10)

    def test_queued_configuration_change_requires_review(self):
        runtime=self.create(1,1)
        runtime.submit('L0','observe',{},request_id='one')
        runtime.enable('L0',False,approved=True);runtime.enable('L0',True,approved=True)
        with self.assertRaises(PermissionError):runtime.run_one({'observe':echo},broker=lambda *a:True)

    def test_committed_result_recovery_does_not_repeat_callback(self):
        runtime=self.create(1,1)
        runtime.submit('L0','observe',{},request_id='one')
        runtime.run_one({'observe':echo},broker=lambda *a:True)
        with runtime.db() as db:db.execute("UPDATE tasks SET phase='RUNNING',result=NULL")
        self.assertEqual(runtime.recover(reviewed=True)['tasks'][0]['phase'],'RESULT')
        self.assertEqual(runtime.run_one({'observe':echo},broker=lambda *a:True)['status'],'IDLE')

    def test_queue_limit_and_handler_pin(self):
        runtime=self.create(1,1)
        for n in range(128):runtime.submit('L0','observe',{},request_id='task-'+str(n))
        with self.assertRaises(ValueError):runtime.submit('L0','observe',{},request_id='overflow')
        with self.assertRaises(PermissionError):runtime.run_one({'observe':hold},broker=lambda *a:True)

    def test_queued_content_and_primer_substitution(self):
        runtime=self.create(1,1)
        runtime.submit('L0','observe',{'color':'amber'},request_id='one')
        with runtime.db() as db:db.execute('UPDATE tasks SET input=?',(json.dumps({'color':'forged'}),))
        with self.assertRaises(PermissionError):runtime.run_one({'observe':echo},broker=lambda *a:True)
        with runtime.db() as db:db.execute('UPDATE tasks SET input=?',(limbs.c.canonical({'color':'amber'}),))
        import sqlite3
        with sqlite3.connect(self.paths[0]) as db:db.execute("UPDATE meta SET value=? WHERE key='primer'",(json.dumps({'changed':True}),))
        db.close()
        with self.assertRaises(ValueError):runtime.run_one({'observe':echo},broker=lambda *a:True)

    def test_interrupted_result_admission_reconciles_canonical_journal(self):
        runtime=self.create(1,1)
        runtime.submit('L0','observe',{},request_id='one')
        with runtime.db() as db:db.execute("CREATE TRIGGER fail_result BEFORE UPDATE OF result ON tasks WHEN NEW.phase='RESULT' BEGIN SELECT RAISE(ABORT,'injected interruption'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):runtime.run_one({'observe':echo},broker=lambda *a:True)
        with runtime.db() as db:db.execute('DROP TRIGGER fail_result')
        self.assertEqual(runtime.recover(reviewed=True)['tasks'][0]['phase'],'RESULT')
        self.assertEqual(len(runtime.results(broker=lambda *a:True)),1)
