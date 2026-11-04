"""Local synthetic spending guards; no credentials or inference APIs."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from mantleos.studio_mind_budget import MindBudget, AttemptConflict


def bindings(value='a'):
    return {name:value*64 for name in ('frame_sha256','source_sha256',
            'config_sha256','route_sha256','policy_sha256')}


class MindBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'provider.sqlite'
        self.store=MindBudget(self.path,create=True)

    def reserve(self, request='one', **overrides):
        values=dict(purpose='mind',request_id=request,binding=bindings(),
                    maximum_micro_usd=60,cap_micro_usd=100)
        values.update(overrides)
        return self.store.reserve(**values)

    def test_explicit_initialization_and_no_unrelated_database_adoption(self):
        missing=self.path.parent/'missing'
        with self.assertRaises(FileNotFoundError):MindBudget(missing)
        self.assertFalse(missing.exists())
        wrong=self.path.parent/'other'
        with closing(sqlite3.connect(wrong)) as db:
            db.execute('CREATE TABLE other (x)');db.commit()
        with self.assertRaises(ValueError):MindBudget(wrong,create=True)
        with closing(sqlite3.connect(wrong)) as db:
            self.assertEqual(db.execute('SELECT name FROM sqlite_master').fetchall(),[('other',)])

    def test_restart_unknown_outcome_duplicate_and_claim_binding(self):
        first=self.reserve()
        self.store.sent(purpose='mind',request_id='one',claim=first['claim'])
        self.store=MindBudget(self.path)
        self.assertEqual(self.reserve(),{'status':'SENT','new':False})
        self.assertEqual(self.store.retained_result(purpose='mind',request_id='one',
                         binding=bindings())['status'],'NEEDS_REVIEW')
        with self.assertRaises(AttemptConflict):
            self.store.sent(purpose='mind',request_id='one',claim=first['claim'])
        with self.assertRaises(AttemptConflict):self.reserve(binding=bindings('b'))
        with self.assertRaises(PermissionError):self.reserve('two')

    def test_model_key_policy_changes_never_reset_stable_account(self):
        self.reserve()
        self.store=MindBudget(self.path)
        with self.assertRaises(PermissionError):self.reserve('new-route',binding=bindings('b'))
        # Raising a cap is an owner operation; it retains all earlier exposure.
        self.reserve('new-route',binding=bindings('b'),cap_micro_usd=150)
        status=self.store.status({'mind':150,'limbs':50})
        self.assertEqual(status['accounts']['mind']['encumbered_micro_usd'],120)
        self.assertEqual(status['accounts']['mind']['remaining_micro_usd'],30)
        self.assertEqual(self.store.status({'mind':20,'limbs':50})['accounts']['mind']['remaining_micro_usd'],0)

    def test_account_identity_and_explicit_schema_upgrade_preserve_holds(self):
        self.reserve()
        identity=self.store.identity()
        self.assertEqual(MindBudget(self.path).identity(),identity)
        # Reconstruct the actual previous schema, retaining its attempt table.
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('DROP TABLE accounting_identity')
            db.execute('PRAGMA user_version=1')
            db.commit()
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            MindBudget(self.path)
        upgraded=MindBudget(self.path,create=True)
        self.assertNotEqual(upgraded.identity(),identity)
        self.assertEqual(upgraded.status({'mind':100,'limbs':50})['accounts']['mind']['encumbered_micro_usd'],60)
        self.assertFalse(upgraded.reserve(purpose='mind',request_id='one',binding=bindings(),
            maximum_micro_usd=60,cap_micro_usd=100)['new'])

    def test_competing_limbs_share_one_atomic_cap(self):
        def reserve(i):
            try:return self.reserve(str(i),purpose='limbs',maximum_micro_usd=40)['new']
            except PermissionError:return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            accepted=list(pool.map(reserve,range(12)))
        self.assertEqual(sum(accepted),2)
        status=self.store.status({'mind':100,'limbs':100})
        self.assertEqual(status['accounts']['limbs']['encumbered_micro_usd'],80)
        self.assertEqual(status['accounts']['mind']['encumbered_micro_usd'],0)

    def test_result_durable_before_admission_and_conservative_billing(self):
        first=self.reserve()
        with self.assertRaises(AttemptConflict):
            self.store.result(purpose='mind',request_id='one',claim=first['claim'],value={})
        self.store.sent(purpose='mind',request_id='one',claim=first['claim'])
        with self.assertRaises(AttemptConflict):
            self.store.result(purpose='mind',request_id='one',claim='forged',value={})
        value={'proposal':{'kind':'reply','reply':'hello','observation_sha256':None},
               'model':'example/model','latency_ms':12,'usage':{'cost':0}}
        self.store.result(purpose='mind',request_id='one',claim=first['claim'],value=value,cost_micro_usd=0)
        self.store=MindBudget(self.path)
        saved=self.store.retained_result(purpose='mind',request_id='one',binding=bindings())
        self.assertEqual(saved['value'],value)
        self.assertEqual(saved['status'],'RESULT')
        self.store.admitted(purpose='mind',request_id='one',claim=saved['claim'])
        self.assertEqual(self.reserve()['status'],'ADMITTED')
        # A remote zero-cost assertion never frees locally authorized reservation.
        self.assertEqual(self.store.status({'mind':100,'limbs':50})['accounts']['mind']['encumbered_micro_usd'],60)
        with self.assertRaises(AttemptConflict):
            self.store.result(purpose='mind',request_id='one',claim=first['claim'],value=value)

    def test_over_limit_billing_retained_and_corruption_refused(self):
        first=self.reserve()
        self.store.sent(purpose='mind',request_id='one',claim=first['claim'])
        self.store.result(purpose='mind',request_id='one',claim=first['claim'],value={'x':1},cost_micro_usd=110)
        self.assertEqual(self.store.status({'mind':100,'limbs':50})['accounts']['mind']['remaining_micro_usd'],0)
        with self.assertRaises(PermissionError):self.reserve('another',maximum_micro_usd=0)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE attempts SET result='{}'")
            db.commit()
        with self.assertRaisesRegex(ValueError,'Corrupt'):
            self.store.retained_result(purpose='mind',request_id='one',binding=bindings())

    def test_bounds_redaction_and_interrupted_transaction(self):
        for value in (-1,True,1.1,2**53):
            with self.assertRaises(ValueError):self.reserve(maximum_micro_usd=value)
        with self.assertRaises(ValueError):self.reserve(binding={'frame_sha256':'a'*64})
        first=self.reserve()
        with self.assertRaises(RuntimeError):
            with self.store._write() as db:
                db.execute("UPDATE attempts SET state='SENT'")
                raise RuntimeError('injected before commit')
        self.assertEqual(self.reserve()['status'],'RESERVED')
        status=str(self.store.status({'mind':100,'limbs':50}))
        self.assertNotIn(first['claim'],status)
        self.assertNotIn('a'*64,status)


if __name__=='__main__':unittest.main()
