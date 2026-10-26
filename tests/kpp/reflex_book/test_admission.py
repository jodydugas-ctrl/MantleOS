"""Synthetic, isolated, host-driven M3 conformance and tamper tests."""
import copy
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from mantleos.reflex.admission import operator_issue_receipt,verify_approval,install
from mantleos.reflex.bytecode import encode
from mantleos.reflex.compiler import compile_ir
from mantleos.reflex.evidence import make_candidate,validate_candidate
from mantleos.reflex.errors import ReflexError
from mantleos.reflex.parser import parse_program
from mantleos.reflex.registry import ExperimentalRegistry

from .fixtures import workspace
ROOT=workspace()
FIX=ROOT/'examples'/'reflex_book'
NOW='2026-10-24T12:00:00Z'
END='2026-11-24T12:00:00Z'
SECRET=b'experimental-test-credential-only--0123456789-abcdef'
KEYS={'synthetic_operator':SECRET}
BASE1={'synthetic.routine':hashlib.sha256(b'first synthetic baseline').hexdigest()}
BASE2={'synthetic.routine':hashlib.sha256(b'second synthetic baseline').hexdigest()}
EVIDENCE=b'{"kind":"synthetic-test-receipt","test_results":"pass","scope":"unit-only"}'


def package(baselines=BASE1, *, proposed_by='model_author', nonce='review_01', predecessor=None):
    program=parse_program((FIX/'location_rule.json').read_bytes())
    binary=encode(compile_ir(program))
    cand=make_candidate(binary,EVIDENCE,evidence_refs=['synthetic:unit-tests'],
                        baseline_versions=baselines,proposed_by=proposed_by,predecessor_sha256=predecessor)
    approval=operator_issue_receipt(cand,issuer='synthetic_operator',reviewed_by='human_reviewer',
                    secret=SECRET,not_before_utc=NOW,expires_utc=END,nonce=nonce)
    return cand,binary,EVIDENCE,approval


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='reflex-registry-')
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test-only.sqlite'
        self.registry=ExperimentalRegistry(self.path)
        self.c,self.b,self.e,self.a=package()

    def _install(self,c=None,b=None,e=None,a=None,baselines=BASE1):
        return self.registry.install(c or self.c,b or self.b,e or self.e,a or self.a,
                                    trusted_issuers=KEYS,now_utc=NOW,current_baselines=baselines)

    def _activate(self,cid=None,baselines=BASE1):
        return self.registry.activate(cid or self.c['candidate_sha256'],trusted_issuers=KEYS,
                                      now_utc=NOW,current_baselines=baselines)

    def test_candidate_provenance_exact_binary_and_evidence(self):
        self.assertEqual(validate_candidate(self.c,self.b,self.e),self.c)
        for mutation,code in [(lambda x:x.__setitem__('program_id','example.forged'),'E_INTEGRITY'),
                               (lambda x:x.__setitem__('capabilities',['write:self']),'E_INTEGRITY')]:
            obj=copy.deepcopy(self.c);mutation(obj)
            with self.assertRaises(ReflexError) as x:
                validate_candidate(obj,self.b,self.e)
            self.assertEqual(x.exception.code,code)
        with self.assertRaises(ReflexError) as x:
            validate_candidate(self.c,self.b,b'changed')
        self.assertEqual(x.exception.code,'E_EVIDENCE')
        with self.assertRaises(ReflexError):
            validate_candidate(self.c,self.b[:-1],self.e)

    def test_unapproved_install_denied_without_mutating_ledger(self):
        with self.assertRaises(ReflexError) as x:
            install(self.c)
        self.assertEqual(x.exception.code,'E_AUTHORITY')
        for receipt,keys,code in [({},KEYS,'E_SHAPE'),(self.a,{},'E_AUTHORITY')]:
            with self.subTest(code=code),self.assertRaises(ReflexError) as x:
                self.registry.install(self.c,self.b,self.e,receipt,trusted_issuers=keys,
                                      now_utc=NOW,current_baselines=BASE1)
            self.assertEqual(x.exception.code,code)
        self.assertEqual(self.registry.audit()['event_count'],2)
        self.assertEqual(self.registry.audit()['installed_count'],0)

    def test_forged_operator_receipt_refused(self):
        checks=[('mac_sha256','0'*64,'E_AUTHORITY'),('scope','production-body','E_APPROVAL'),
                ('capabilities',['write:self'],'E_APPROVAL'),('candidate_sha256','0'*64,'E_APPROVAL'),
                ('decision','REVOKE','E_APPROVAL')]
        for name,mut,code in checks:
            bad=copy.deepcopy(self.a);bad[name]=mut
            with self.subTest(name=name),self.assertRaises(ReflexError) as x:
                verify_approval(self.c,bad,KEYS,NOW)
            self.assertEqual(x.exception.code,code)
        with self.assertRaises(ReflexError) as x:
            operator_issue_receipt(self.c,issuer='synthetic_operator',reviewed_by='model_author',
                                   secret=SECRET,not_before_utc=NOW,expires_utc=END,nonce='same_author')
        self.assertEqual(x.exception.code,'E_AUTHORITY')

    def test_approval_expiry_and_time_boundaries(self):
        verify_approval(self.c,self.a,KEYS,NOW)
        with self.assertRaises(ReflexError) as x:
            verify_approval(self.c,self.a,KEYS,END)
        self.assertEqual(x.exception.code,'E_EXPIRED')
        with self.assertRaises(ReflexError) as x:
            verify_approval(self.c,self.a,KEYS,'2026-10-23T12:00:00Z')
        self.assertEqual(x.exception.code,'E_EXPIRED')

    def test_install_does_not_activate_and_audit(self):
        obj=self._install()
        self.assertEqual(obj['state'],'INSTALLED_IN_SIMULATION')
        self.assertFalse(obj['production_body_authorized'])
        with self.assertRaises(ReflexError) as x:
            self.registry.run_active((FIX/'location_normal.json').read_bytes(),
                                     trusted_issuers=KEYS,now_utc=NOW,current_baselines=BASE1)
        self.assertEqual(x.exception.code,'E_NOT_ACTIVE')
        self.assertEqual(self.registry.audit()['event_count'],2)
        self.assertEqual(self._activate()['state'],'ACTIVE_IN_SIMULATION')
        output=self.registry.run_active((FIX/'location_anomaly.json').read_bytes(),
                                       trusted_issuers=KEYS,now_utc=NOW,current_baselines=BASE1)
        self.assertEqual(output['trace']['result']['status'],'ANOMALY')
        self.assertTrue(output['trace']['result']['review_requested'])
        self.assertFalse(output['trace']['authorized'])
        self.assertFalse(output['production_body_authorized'])
        self.assertEqual(self.registry.audit()['event_count'],4)
        self.registry.disable(now_utc=NOW)
        with self.assertRaises(ReflexError) as x:
            self.registry.run_active((FIX/'location_normal.json').read_bytes(),
                                     trusted_issuers=KEYS,now_utc=NOW,current_baselines=BASE1)
        self.assertEqual(x.exception.code,'E_NOT_ACTIVE')
        self.assertEqual(self.registry.audit()['event_count'],6)

    def test_duplicate_install_is_refused_without_state_change(self):
        self._install()
        with self.assertRaises(ReflexError) as x:
            self._install()
        self.assertEqual(x.exception.code,'E_DUPLICATE')
        self.assertEqual(self.registry.audit()['event_count'],2)

    def test_baseline_correction_quarantines_and_survives_restart(self):
        self._install();self._activate()
        with self.assertRaises(ReflexError) as x:
            self.registry.run_active((FIX/'location_normal.json').read_bytes(),
                                     trusted_issuers=KEYS,now_utc=NOW,current_baselines=BASE2)
        self.assertEqual(x.exception.code,'E_STALE')
        audit=ExperimentalRegistry(self.path).audit()
        self.assertEqual(audit['stale_count'],1)
        self.assertIsNone(audit['active_candidate_sha256'])
        with self.assertRaises(ReflexError) as x:
            self._activate()
        self.assertEqual(x.exception.code,'E_STALE')
        self.assertEqual(ExperimentalRegistry(self.path).audit()['event_count'],5)

    def test_rollback_cannot_escape_scope_revocation_or_staleness(self):
        self._install();self._activate()
        c2,b2,e2,a2=package(BASE1,proposed_by='model_author_2',nonce='review_02',
                            predecessor=self.c['candidate_sha256'])
        self._install(c2,b2,e2,a2)
        self._activate(c2['candidate_sha256'])
        self.registry.rollback(self.c['candidate_sha256'],trusted_issuers=KEYS,
                               now_utc=NOW,current_baselines=BASE1)
        self.assertEqual(self.registry.audit()['active_candidate_sha256'],self.c['candidate_sha256'])
        self.registry.revoke(self.c['candidate_sha256'],now_utc=NOW)
        self.assertIsNone(self.registry.audit()['active_candidate_sha256'])
        with self.assertRaises(ReflexError) as x:
            self.registry.rollback(self.c['candidate_sha256'],trusted_issuers=KEYS,
                                   now_utc=NOW,current_baselines=BASE1)
        self.assertIn(x.exception.code,('E_REVOKED','E_ROLLBACK'))
        self._activate(c2['candidate_sha256'])
        self.assertEqual(self.registry.audit()['revoked_count'],1)

    def test_atomic_failed_install_and_immutable_sql_rows(self):
        with self.assertRaises(ReflexError):
            self._install(baselines=BASE2)
        self.assertEqual(self.registry.audit()['event_count'],1)
        self._install()
        conn=sqlite3.connect(self.path)
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("UPDATE events SET kind='ACTIVATE' WHERE seq=1")
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute('DELETE FROM artifacts')
        conn.close()
        self.assertEqual(self.registry.audit()['event_count'],2)

    def test_audit_detects_privileged_database_tampering(self):
        self._install()
        conn=sqlite3.connect(self.path)
        conn.execute('DROP TRIGGER no_event_update')
        conn.execute("UPDATE events SET payload='{}' WHERE seq=1")
        conn.commit();conn.close()
        with self.assertRaises(ReflexError) as x:
            self.registry.audit()
        self.assertEqual(x.exception.code,'E_AUDIT')

    def test_missing_evidence_or_reviewer_cannot_claim_approval(self):
        with self.assertRaises(ReflexError):
            make_candidate(self.b,b'',evidence_refs=[],baseline_versions=BASE1,proposed_by='model_author')
        with self.assertRaises(ReflexError):
            operator_issue_receipt(self.c,issuer='synthetic_operator',reviewed_by='model_author',
                                   secret=SECRET,not_before_utc=NOW,expires_utc=END,nonce='x')


if __name__=='__main__':unittest.main()

class RecoveryAndExpiryTests(unittest.TestCase):
    """Deliberately exercise interrupted publication and reloaded registry."""
    setUp=AdmissionTests.setUp
    _install=AdmissionTests._install
    _activate=AdmissionTests._activate
    def test_transaction_crash_rolls_back_partial_install(self):
        from unittest.mock import patch
        def interrupt(*_args,**_kwargs):
            raise RuntimeError('simulated crash before audit append')
        with patch.object(self.registry,'_append',side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError,'simulated crash'):
                self._install()
        # The artifact INSERT and audit APPEND share one SQLite transaction.
        reopened=ExperimentalRegistry(self.path)
        audit=reopened.audit()
        self.assertEqual(audit['event_count'],0)
        self.assertEqual(audit['installed_count'],0)
        self._install()
        self.assertEqual(reopened.audit()['installed_count'],1)

    def test_expired_live_approval_fails_closed(self):
        self._install();self._activate()
        with self.assertRaises(ReflexError) as x:
            self.registry.run_active((FIX/'location_anomaly.json').read_bytes(),
                  trusted_issuers=KEYS,now_utc=END,current_baselines=BASE1)
        self.assertEqual(x.exception.code,'E_EXPIRED')
        self.assertEqual(self.registry.audit()['event_count'],3)

    def test_host_key_rotation_revokes_execution_right(self):
        self._install();self._activate()
        with self.assertRaises(ReflexError) as x:
            self.registry.run_active((FIX/'location_normal.json').read_bytes(),
                  trusted_issuers={'synthetic_operator':b'Z'*40},now_utc=NOW,
                  current_baselines=BASE1)
        self.assertEqual(x.exception.code,'E_AUTHORITY')
        self.assertEqual(self.registry.audit()['event_count'],3)

class PackagingAndConcurrencyTests(unittest.TestCase):
    setUp=AdmissionTests.setUp
    _install=AdmissionTests._install
    _activate=AdmissionTests._activate

    def test_candidate_cli_uses_only_submitted_evidence(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'candidate.json'
            cmd=[sys.executable,'-m','mantleos.reflex.cli','candidate',
                 str(FIX/'m3_location_candidate.rfx'),'--evidence',
                 str(ROOT/'docs/reflex/TEST-RECEIPT.json'),'--baselines',
                 str(FIX/'m3_baseline_versions.json'),'--proposed-by','synthetic_model',
                 '--evidence-ref','synthetic:m0-test-receipt','--output',str(output)]
            completed=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=True)
            self.assertIn('CANDIDATE_ONLY',completed.stdout)
            self.assertIn('"authorized":false',completed.stdout)
            self.assertEqual(output.read_bytes().rstrip(b'\n'),
                             (FIX/'m3_candidate.json').read_bytes().rstrip(b'\n'))

    def test_concurrent_install_has_one_success_only(self):
        from concurrent.futures import ThreadPoolExecutor
        def attempt(_):
            try:
                return self._install()['state']
            except ReflexError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=3) as pool:
            outcomes=list(pool.map(attempt,range(3)))
        self.assertEqual(outcomes.count('INSTALLED_IN_SIMULATION'),1)
        self.assertEqual(outcomes.count('E_DUPLICATE'),2)
        audit=self.registry.audit()
        self.assertEqual(audit['installed_count'],1)
        self.assertEqual(audit['event_count'],3)

    def test_refusal_audit_redacts_observation_data(self):
        self._install();self._activate()
        bad=(FIX/'location_normal.json').read_bytes().replace(b'synthetic:',b'real-data:')
        with self.assertRaises(ReflexError) as x:
            self.registry.run_active(bad,trusted_issuers=KEYS,now_utc=NOW,
                                     current_baselines=BASE1)
        self.assertEqual(x.exception.code,'E_SOURCE')
        from contextlib import closing
        with closing(sqlite3.connect(self.path)) as conn:
            raw='\n'.join(record[0] for record in conn.execute('SELECT payload FROM events'))
        self.assertNotIn('real-data:',raw)
        self.assertNotIn(SECRET.decode('ascii'),raw)
        self.assertIn('E_SOURCE',raw)
        self.assertEqual(self.registry.audit()['event_count'],3)
