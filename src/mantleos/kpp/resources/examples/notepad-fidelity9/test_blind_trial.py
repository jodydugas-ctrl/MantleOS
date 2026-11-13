"""Blind Anchor logical interpretation protocol tests (no actual model calls)."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import blind_trial as b


class TestModelNeutralBlindProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public, cls.private = b.build_trial_data()
        cls.control = {a['trial_id']:{k:a[k] for k in b.FIELDS} for a in cls.private['answers']}

    def test_opaque_41_stimuli_with_no_expected_results(self):
        public=self.public
        self.assertEqual(41,len(public['trials']))
        self.assertEqual([f'T{i:04}' for i in range(1,42)],[t['id'] for t in public['trials']])
        self.assertEqual(9,public['anchor_count'])
        self.assertEqual(9,public['gate_family_count'])
        self.assertEqual(19,public['gate_condition_count'])
        for t in public['trials']:
            self.assertEqual(set(t),{'id','initial_state','stimulus','simulated_effect_failures',
                                     'action_clause','gate_families','host_profile',
                                     'file_session_observation'})
            self.assertNotIn('result',t)
            self.assertNotIn('outcome',t)
            self.assertNotIn('source_case',t)
            self.assertNotIn('expected_final',t)

    def test_all_19_clauses_and_nine_families_are_public_and_consistent(self):
        registry=self.public['gate_registry']
        all_conditions=registry['gate_conditions']
        all_families=registry['gate_families']
        self.assertEqual(19,len(all_conditions))
        self.assertEqual(9,len(all_families))
        self.assertEqual(19,len({g['gate_id'] for g in all_conditions}))
        self.assertEqual({'G-BUILD-01','G-UI-01'},
                         {g['gate_id'] for g in all_conditions if g['phase']!='RUNTIME'})
        owned=[c for family in all_families for c in family['clauses']]
        self.assertEqual(sorted(c['gate_id'] for c in all_conditions),sorted(owned))
        self.assertEqual(len(owned),len(set(owned)))
        self.assertEqual({f['id'] for f in all_families},
                         set(f['id'] for f in all_families))

    def test_all_17_supported_action_result_variants_are_enumerated(self):
        contract=self.public['result_contract']
        by_action=contract['allowed_result_kinds_by_action']
        kinds=contract['result_kinds']
        self.assertEqual(17,len(by_action))
        self.assertEqual({'snapshot','selection','match','none','replace'},set(kinds))
        for trial in self.public['trials']:
            act=trial['stimulus']['action']
            if act in by_action:
                self.assertIn(self.control[trial['id']]['result']['kind'],by_action[act]) if self.control[trial['id']]['result'] is not None else None
        self.assertEqual(['match','none'],by_action['find'])
        self.assertEqual(['replace'],by_action['replace-all'])

    def test_save_disk_equality_is_explicit_not_inferred_from_current_file(self):
        trials=self.public['trials']
        saves=[t for t in trials if t['stimulus']['action']=='save']
        self.assertEqual(2,len(saves))
        statuses={t['file_session_observation']['disk_comparison'] for t in saves}
        self.assertEqual({'NO_ASSOCIATION','MATCH'},statuses)
        self.assertEqual('MATCH',next(t for t in saves if t['initial_state']['active_path'])['file_session_observation']['disk_comparison'])
        self.assertNotIn('expected_digest',self.public['expected_response_schema']['state_fields'])
        for t in trials:
            self.assertEqual(t['initial_state']['active_path'],t['file_session_observation']['active_path'])
            self.assertEqual('TRUSTED_VIRTUAL_HOST_PRECOMMAND',t['file_session_observation']['observation_source'])
            self.assertIn(t['file_session_observation']['disk_comparison'],
                          self.public['file_session_observation_contract']['comparison_values'])

    def test_file_session_comparison_distinguishes_external_change_and_missing(self):
        from logical_engine import LogicalMachine, digest
        machine=LogicalMachine('same',files={'/virtual/doc.txt':b'old'})
        machine.active_path='/virtual/doc.txt'
        machine.expected_digest=digest(b'old')
        self.assertEqual('MATCH',b.file_session_observation(machine)['disk_comparison'])
        machine.files[machine.active_path]=b'outsider'
        self.assertEqual('MISMATCH',b.file_session_observation(machine)['disk_comparison'])
        outcome=machine.send('save')
        self.assertEqual('REJECTED_BY_GATE',outcome['outcome'])
        machine.files.pop(machine.active_path)
        self.assertEqual('MISSING',b.file_session_observation(machine)['disk_comparison'])
        machine.expected_digest=None
        machine.files[machine.active_path]=b'outside'
        self.assertEqual('UNKNOWN',b.file_session_observation(machine)['disk_comparison'])
        machine.active_path=None
        self.assertEqual('NO_ASSOCIATION',b.file_session_observation(machine)['disk_comparison'])

    def test_success_result_schema_is_not_ambiguous(self):
        self.assertEqual('notepad.blind-logic-challenge/2',self.public['schema'])
        for answer in self.private['answers']:
            result=answer['result']
            if result is None:
                continue
            spec=self.public['result_contract']['result_kinds'][result['kind']]
            self.assertEqual(set(spec['required_keys']),set(result))
            if 'selection' in result:
                self.assertEqual(2,len(result['selection']))
                self.assertTrue(all(type(v) is int for v in result['selection']))
            if 'count' in result:
                self.assertIs(type(result['count']),int)
                self.assertGreaterEqual(result['count'],0)

    def test_no_implementation_or_key_in_public_export(self):
        with TemporaryDirectory() as root:
            ch=Path(root)/'public';seal=Path(root)/'sealed'
            b.prepare(ch,seal)
            self.assertEqual({'challenge.json','START-HERE.md','response-template.jsonl'},
                             {p.name for p in ch.iterdir()})
            self.assertEqual({'private-key.json','SEAL-README.md'},
                             {p.name for p in seal.iterdir()})
            for p in ch.iterdir():
                raw=p.read_text('utf-8')
                self.assertNotIn('source_case',raw)
                self.assertNotIn('expected_final',raw)
                self.assertNotIn('def _dispatch(',raw)
                self.assertNotIn('def score(',raw)
            self.assertEqual(self.public,b.parse_json(ch/'challenge.json'))

    def test_control_41_of_41_not_model_evidence(self):
        scored=b.score(self.public,self.private,self.control)
        self.assertTrue(scored['complete_pass'])
        self.assertEqual((41,41,574),(scored['total_trials'],scored['passed_trials'],scored['field_passes']))
        self.assertIn('no evidence of independent LLM',scored['scope'])

    def test_tampered_packet_rejected_by_fingerprint(self):
        tampered=deepcopy(self.public)
        tampered['trials'][0]['stimulus']['action']='edit'
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            b.score(tampered,self.private,self.control)

    def test_wrong_text_detected_not_accepted(self):
        candidate=deepcopy(self.control)
        candidate['T0001']['state']['text']='INJECTED'
        result=b.score(self.public,self.private,candidate)
        self.assertFalse(result['complete_pass'])
        self.assertEqual(40,result['passed_trials'])
        self.assertIn('state.text',result['results'][0]['mismatches'])

    def test_wrong_history_detected(self):
        candidate=deepcopy(self.control)
        candidate['T0001']['state']['undo_stack']=[['bad','bad']]
        scored=b.score(self.public,self.private,candidate)
        self.assertIn('state.undo_stack',scored['results'][0]['mismatches'])

    def test_wrong_host_file_effect_detected(self):
        candidate=deepcopy(self.control)
        candidate['T0001']['state']['virtual_files']={'/unauthorized':{'text':'bad'}}
        scored=b.score(self.public,self.private,candidate)
        self.assertIn('state.virtual_files',scored['results'][0]['mismatches'])

    def test_missing_case_is_explicit_failure(self):
        candidate=deepcopy(self.control)
        candidate.pop('T0001')
        scored=b.score(self.public,self.private,candidate)
        self.assertEqual(40,scored['submitted_trials'])
        self.assertEqual(['MISSING_SUBMISSION'],scored['results'][0]['mismatches'])

    def test_unknown_case_not_admitted(self):
        candidate=deepcopy(self.control)
        candidate['fake']=candidate['T0001']
        with self.assertRaisesRegex(ValueError,'Unknown trial'):
            b.score(self.public,self.private,candidate)

    def test_duplicate_response_ids_rejected(self):
        with TemporaryDirectory() as root:
            f=Path(root)/'responses.jsonl'
            r=self.control['T0001']
            f.write_text(b.canonical(r)+'\n'+b.canonical(r)+'\n','utf-8')
            with self.assertRaisesRegex(ValueError,'duplicate trial_id'):
                b.load_responses(f)

    def test_invalid_json_duplicate_fields_and_nan_rejected(self):
        with TemporaryDirectory() as root:
            f=Path(root)/'response.jsonl'
            r=b.canonical(self.control['T0001'])
            f.write_text(r.replace('"trial_id":"T0001"','"trial_id":"T0001","trial_id":"T0001"')+'\n','utf-8')
            with self.assertRaisesRegex(ValueError,'Duplicate JSON field'):
                b.load_responses(f)
            f.write_text(r.replace('"revision":0','"revision":NaN')+'\n','utf-8')
            with self.assertRaisesRegex(ValueError,'Nonfinite JSON'):
                b.load_responses(f)

    def test_invalid_result_variants_and_bad_selection_rejected(self):
        success=next(v for v in self.control.values() if v['outcome']=='PREDICTED_FROM_ANCHORS')
        for bad_result,pattern in [({'kind':'DocumentSnapshot'},'result kind'),
                                   ({'kind':'snapshot','count':0},'result fields'),
                                   ({'kind':'match','selection':[True,2]},'selection'),
                                   ({'kind':'replace','count':True},'count')]:
            with self.subTest(result=bad_result), TemporaryDirectory() as root:
                entry=deepcopy(success);entry['result']=bad_result
                path=Path(root)/'model.jsonl';path.write_text(b.canonical(entry)+'\n','utf-8')
                with self.assertRaisesRegex(ValueError,pattern):b.load_responses(path)

    def test_rejection_must_explain_and_leave_null_result(self):
        rejected=next(k for k,v in self.control.items() if v['outcome']=='REJECTED_BY_GATE')
        wrong=deepcopy(self.control[rejected]);wrong['reason']=''
        with TemporaryDirectory() as root:
            f=Path(root)/'res.jsonl';f.write_text(b.canonical(wrong)+'\n','utf-8')
            with self.assertRaisesRegex(ValueError,'reason'):
                b.load_responses(f)

    def test_missing_state_keys_fail_validation(self):
        wrong=deepcopy(self.control['T0001']);wrong['state'].pop('dirty')
        with TemporaryDirectory() as root:
            f=Path(root)/'res.jsonl';f.write_text(b.canonical(wrong)+'\n','utf-8')
            with self.assertRaisesRegex(ValueError,'State projection fields'):
                b.load_responses(f)

    def test_separate_paths_required_for_prepare(self):
        with TemporaryDirectory() as root:
            base=Path(root)
            with self.assertRaisesRegex(ValueError,'disjoint'):
                b.prepare(base/'one',base/'one')
            (base/'already').mkdir()
            with self.assertRaisesRegex(ValueError,'must be new'):
                b.prepare(base/'already',base/'separate')

    def test_deterministic_challenge_and_key(self):
        next_public,next_private=b.build_trial_data()
        self.assertEqual(self.public,next_public)
        self.assertEqual(self.private,next_private)
        self.assertEqual(b.fingerprint(self.public),self.private['challenge_sha256'])

    def test_all_17_action_clauses_present(self):
        self.assertEqual(17,len({t['stimulus']['action'] for t in self.public['trials'] if t['action_clause']}))
        for trial in self.public['trials']:
            if trial['action_clause'] is not None:
                self.assertEqual(trial['action_clause']['action'],trial['stimulus']['action'])
                self.assertTrue(trial['gate_families'])


if __name__=='__main__':
    unittest.main()
