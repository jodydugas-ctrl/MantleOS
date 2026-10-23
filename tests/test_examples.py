"""Synthetic example boundaries. Real Hermes qualification is a separate opt-in run."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from mantleos import (anchor_app_document, anchor_apps, appai, compiled, engram,
                      examples, lifecycle, missions, observer, primer, specimens)
from mantleos.transactions import write_json


def synthetic_host(root):
    """Tiny host fixture; never presented as an upstream Hermes parity test."""
    root.mkdir()
    original = ''.join(f'# seam-{i}\n' for i in range(8)) + 'def native():\n    return 42\n'
    (root / 'host.py').write_text(original, encoding='utf-8', newline='\n')
    spec = {'repository': 'synthetic', 'commit': 'fixture',
            'files': {'host.py': hashlib.sha256(original.encode()).hexdigest()},
            'insertions': [{'path': 'host.py', 'symbol': 'native', 'semantic_event': 'event-' + str(i),
                            'direction': 'AFFERENT', 'anchor': f'# seam-{i}', 'source': 'pass\n'} for i in range(8)]}
    appai._integrate(root, spec)
    return original


class AppAITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.base = Path(cls.fixture.name) / 'host'
        cls.original = synthetic_host(cls.base)
        appai.birth(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.host = self.root / 'host'; shutil.copytree(self.base, self.host)
        self.specimen = self.root / 'specimen'; self.specimen.mkdir()
        (self.specimen / 'sample.py').write_text('raise RuntimeError("NEVER_EXECUTE_ME")\n', encoding='utf-8')

    def policy(self, **kwargs):
        appai.phase(self.host, True)
        return missions.authorize(self.host, self.specimen, self.root / 'representatives', approved=True, **kwargs)

    def test_self_is_whole_nest_and_reversal_preserves_private_state(self):
        status = appai.status(self.host)
        self.assertEqual(status['self'], str(self.host.resolve()))
        self.assertEqual(status['nest'], status['self'])
        self.assertNotEqual(status['system_directory'], status['self'])
        out = appai.reverse(self.host)
        self.assertEqual((self.host / 'host.py').read_text(), self.original)
        self.assertTrue((Path(out['retained_system_files']) / 'private/body/BIRTH.json').exists())
        self.assertFalse((self.host / 'mantle').exists())

    def test_drift_refuses_reversal_without_overwrite(self):
        (self.host / 'host.py').write_text('operator change')
        with self.assertRaisesRegex(ValueError, 'drift'):
            appai.reverse(self.host)
        self.assertEqual((self.host / 'host.py').read_text(), 'operator change')

    def test_nerves_stasis_and_native_authority(self):
        values = {'session_id': 's', 'turn_id': 't'}
        self.assertEqual(appai.before_mind(self.host, user_message='@appai hello', **values)['context'], '')
        self.assertIn('stasis', appai.authorize_tool(self.host, tool_name='read', **values))
        self.assertIsNone(appai.authorize_tool(self.host, tool_name='read', session_id='native', turn_id='n'))
        appai.phase(self.host, True)
        self.assertIn('SELF', appai.before_mind(self.host, user_message='@appai hello', **values)['context'])
        self.assertIn('grant', appai.authorize_tool(self.host, tool_name='read', **values))
        appai.phase(self.host, True, allowed_tools=['read'])
        self.assertIsNone(appai.authorize_tool(self.host, tool_name='read', **values))
        for callback in (appai.session_started, appai.after_mind, appai.tool_completed, appai.turn_ended, appai.session_ended):
            callback(self.host, **values, arguments={'password': 'DO_NOT_RETAIN'}, assistant_response='PRIVATE_REPLY')
        text = (appai.body(self.host) / 'ENGRAM.jsonl').read_text()
        self.assertNotIn('DO_NOT_RETAIN', text); self.assertNotIn('PRIVATE_REPLY', text)
        before = len(engram.read(appai.body(self.host) / 'ENGRAM.jsonl'))
        appai.before_mind(self.host, user_message='@appai hello', **values)
        self.assertEqual(len(engram.read(appai.body(self.host) / 'ENGRAM.jsonl')), before)
        self.assertEqual(appai.tick(self.host)['heartbeats'], 1)

    def test_policy_requires_authority_and_separate_nests(self):
        with self.assertRaises(PermissionError):
            missions.authorize(self.host, self.specimen, self.root / 'reps')
        with self.assertRaises(ValueError):
            missions.authorize(self.host, self.host, self.root / 'reps', approved=True)
        with self.assertRaises(ValueError):
            missions.authorize(self.host, self.specimen, self.host / 'reps', approved=True)

    def test_representative_inherits_only_primer_and_no_recursive_delegation(self):
        policy = self.policy()
        appai.record(self.host, 'private-memory', {'text': 'PARENT_ONLY_MEMORY'})
        child = missions.dispatch(self.host, policy['id'], request_id='one', context={'mission': 'inspect'})
        self.assertEqual(missions.dispatch(self.host, policy['id'], request_id='one', context={'mission': 'inspect'})['id'], child['id'])
        with self.assertRaises(ValueError):
            missions.dispatch(self.host, policy['id'], request_id='one', context={'different': True})
        with self.assertRaises(PermissionError):
            missions.dispatch(self.host, policy['id'], request_id='two')
        for name in ('PERSONA.md', 'COMMANDMENTS.md'):
            self.assertEqual((Path(child['body']) / 'PRIMER' / name).read_bytes(),
                             (appai.body(self.host) / 'PRIMER' / name).read_bytes())
        self.assertEqual(engram.read(Path(child['body']) / 'ENGRAM.jsonl'), [])
        instruction = compiled.read_json(Path(child['body']) / 'MISSION.json')
        self.assertEqual(instruction['context'], {'mission': 'inspect'})
        self.assertFalse(instruction['authority_carried'])
        self.assertNotEqual(compiled.read_json(Path(child['body']) / 'BIRTH.json')['id'],
                            compiled.read_json(appai.body(self.host) / 'BIRTH.json')['id'])
        with self.assertRaises(PermissionError):
            specimens.representative(child['body'], self.root / 'grandchild', 'recursive')
        self.assertFalse((Path(child['body']) / 'missions.sqlite3').exists())

    def test_complete_mission_review_and_idempotent_admission(self):
        policy = self.policy(duration=300)
        value = missions.dispatch(self.host, policy['id'], request_id='complete')
        before = (self.specimen / 'sample.py').read_bytes()
        returned = missions.run(self.host, value['id'])
        self.assertEqual(returned['phase'], 'RETURNED')
        self.assertFalse(returned['report']['specimen_executed'])
        self.assertEqual((self.specimen / 'sample.py').read_bytes(), before)
        parent = appai.body(self.host)
        self.assertFalse(any(r['type'] == 'mission-return' for r in engram.read(parent / 'ENGRAM.jsonl')))
        appai.tick(self.host)  # Parent still operates while its representative awaits admission.
        evidence = missions.review(self.host, value['id'])
        with self.assertRaises(PermissionError):
            missions.admit(self.host, value['id'], approval='wrong')
        result = missions.admit(self.host, value['id'], approval=evidence['sha256'])
        self.assertFalse(result['replay'])
        self.assertTrue(missions.admit(self.host, value['id'], approval=evidence['sha256'])['replay'])
        returns = [r for r in engram.read(parent / 'ENGRAM.jsonl') if r['type'] == 'mission-return']
        self.assertEqual(len(returns), 1)
        self.assertNotIn('report', returns[0]['body'])
        self.assertEqual(appai.status(self.host)['allowed_tools'], [])
        for fmt, ext in [('cartridge', 'vcw'), ('chroma', 'png')]:
            image = self.root / ('child.' + ext)
            lifecycle.save(value['body'], image, format=fmt)
            restored = self.root / ('restored-' + fmt)
            lifecycle.restore(image, restored)
            self.assertEqual(compiled.load(restored)['sha256'], compiled.load(value['body'])['sha256'])
            self.assertEqual(compiled.read_json(restored / 'MISSION.json')['id'], value['id'])
            self.assertEqual(len(engram.read(restored / 'ENGRAM.jsonl')), 1)

    def test_revocation_and_expiration_block_dispatch_and_admission(self):
        expired = self.policy(ttl=1, now=0)
        with self.assertRaises(PermissionError):
            missions.dispatch(self.host, expired['id'], request_id='expired')
        policy = self.policy(duration=300)
        value = missions.dispatch(self.host, policy['id'], request_id='revoked')
        returned = missions.run(self.host, value['id'])
        with patch('mantleos.missions.time.time', return_value=returned['deadline'] + 1):
            with self.assertRaises(PermissionError):
                missions.admit(self.host, value['id'], approval=returned['report_sha256'])
        missions.revoke(self.host, policy['id'])
        with self.assertRaises(PermissionError):
            missions.admit(self.host, value['id'], approval=returned['report_sha256'])
        with self.assertRaises(PermissionError):
            missions.dispatch(self.host, policy['id'], request_id='again')

    def test_interrupted_worker_requires_recovery_not_redispatch(self):
        policy = self.policy(duration=300)
        value = missions.dispatch(self.host, policy['id'], request_id='interrupt')
        with missions._db(self.host) as db:
            value['phase'] = 'RUNNING'; missions._put(db, value)
        with self.assertRaises(ValueError):
            missions.run(self.host, value['id'])
        self.assertEqual(missions.recover(self.host, value['id'])['phase'], 'INTERRUPTED')
        self.assertEqual(missions.dispatch(self.host, policy['id'], request_id='interrupt')['phase'], 'INTERRUPTED')

    def test_stasis_recovery_preserves_pending_work_and_returned_evidence(self):
        policy = self.policy(duration=300)
        ready = missions.dispatch(self.host, policy['id'], request_id='stasis-recovery')
        appai.phase(self.host, False)
        self.assertEqual(missions.recover(self.host, ready['id'])['phase'], 'READY')
        with self.assertRaises(PermissionError):
            missions.run(self.host, ready['id'])
        appai.phase(self.host, True)
        returned = missions.run(self.host, ready['id'])
        appai.phase(self.host, False)
        self.assertEqual(missions.recover(self.host, ready['id']), returned)
        with self.assertRaises(PermissionError):
            missions.admit(self.host, ready['id'], approval=returned['report_sha256'])
        appai.phase(self.host, True)
        self.assertFalse(missions.admit(self.host, ready['id'], approval=returned['report_sha256'])['replay'])

    def test_stasis_does_not_suspend_mission_expiry(self):
        policy = self.policy(duration=300)
        ready = missions.dispatch(self.host, policy['id'], request_id='stasis-expiry')
        appai.phase(self.host, False)
        with patch('mantleos.missions.time.time', return_value=ready['deadline'] + 1):
            self.assertEqual(missions.recover(self.host, ready['id'])['phase'], 'EXPIRED_OR_REVOKED')
        appai.phase(self.host, True)
        revoked = missions.dispatch(self.host, policy['id'], request_id='stasis-revoked')
        appai.phase(self.host, False)
        missions.revoke(self.host, policy['id'])
        self.assertEqual(missions.recover(self.host, revoked['id'])['phase'], 'REVOKED')

    def test_stasis_recovery_reconciles_birth_without_restarting_worker(self):
        policy = self.policy(duration=300)
        value = missions.dispatch(self.host, policy['id'], request_id='stasis-interrupted')
        appai.phase(self.host, False)
        for phase, expected in [('CREATING', 'READY'), ('RUNNING', 'INTERRUPTED')]:
            with missions._db(self.host) as db:
                value['phase'] = phase
                missions._put(db, value)
            with patch('mantleos.missions.subprocess.run') as worker:
                self.assertEqual(missions.recover(self.host, value['id'])['phase'], expected)
                worker.assert_not_called()

    def test_recovery_does_not_disguise_policy_mismatch_as_expiration(self):
        policy = self.policy(duration=300)
        value = missions.dispatch(self.host, policy['id'], request_id='mismatched-target')
        with missions._db(self.host) as db:
            value['source'] = str(self.root / 'different-specimen')
            missions._put(db, value)
        with self.assertRaisesRegex(PermissionError, 'target differs'):
            missions.recover(self.host, value['id'])
        self.assertEqual(missions.inspect(self.host, value['id']), value)

    def test_resident_cycle_restarts_without_duplicate_dispatch(self):
        policy = self.policy(duration=300)
        first = appai.run(self.host, policy_id=policy['id'], request_id='cycle')
        self.assertEqual(first['mission']['phase'], 'RETURNED')
        second = appai.run(self.host, policy_id=policy['id'], request_id='cycle')
        self.assertEqual(first['mission']['id'], second['mission']['id'])
        self.assertEqual(second['heartbeats'], first['heartbeats'] + 1)

    def test_interrupted_birth_and_timeout_leave_parent_intact(self):
        import subprocess
        policy = self.policy(duration=300)
        with patch('mantleos.missions.specimens.representative', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                missions.dispatch(self.host, policy['id'], request_id='birth-failure')
        failed = missions.dispatch(self.host, policy['id'], request_id='birth-failure')
        self.assertEqual(missions.recover(self.host, failed['id'])['phase'], 'INTERRUPTED')
        ready = missions.dispatch(self.host, policy['id'], request_id='timeout')
        before = compiled.load(appai.body(self.host))['sha256']
        with patch('mantleos.missions.subprocess.run', side_effect=subprocess.TimeoutExpired('observer', 1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                missions.run(self.host, ready['id'])
        self.assertEqual(missions.inspect(self.host, ready['id'])['phase'], 'FAILED')
        self.assertEqual(compiled.load(appai.body(self.host))['sha256'], before)


class ExampleTests(unittest.TestCase):
    def test_advisory_header_does_not_define_app_semantics(self):
        source = anchor_apps.notepad_source()
        changed = source.replace(anchor_app_document.LAUNCH, 'Advisory text only. No host permissions granted.')
        result = anchor_app_document.parse(changed)
        self.assertEqual(result['contract']['profile'], 'NOTEPAD_LLM/1.3')
        with self.assertRaises(ValueError):
            anchor_app_document.parse(changed.replace('BEGIN ANCHOR PROGRAM', 'BROKEN PROGRAM', 1))
        tampered = changed.replace('const INITIAL=', 'const BAD=', 1)
        with self.assertRaises(ValueError):
            anchor_app_document.parse(tampered)

    def test_observer_detects_changes_without_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / 'source'; source.mkdir()
            (source / 'bad.py').write_text('raise Exception("not executed")\n')
            a = observer.observe(source, root / 'scan-a')
            self.assertEqual(a['changed_paths'], ['bad.py'])
            b = observer.observe(source, root / 'scan-b', previous=a['snapshot'])
            self.assertEqual(b['changed_paths'], [])
            with self.assertRaises(ValueError): observer.observe(source, source / 'output')

    def test_fresh_engram_scripted_host_and_real_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            specimens.fresh(root / 'body')
            self.assertEqual(engram.read(root / 'body/ENGRAM.jsonl'), [])
            examples.scripted_encounter(root / 'body')
            before = len(engram.read(root / 'body/ENGRAM.jsonl'))
            examples.scripted_encounter(root / 'body')
            self.assertEqual(len(engram.read(root / 'body/ENGRAM.jsonl')), before)
            handoff = examples.handoff(root, 'Hello', request_id='host-turn')
            self.assertEqual(handoff['status'], 'WAITING_FOR_HOST')
            self.assertFalse(handoff['model_called'])


if __name__ == '__main__':
    unittest.main()
