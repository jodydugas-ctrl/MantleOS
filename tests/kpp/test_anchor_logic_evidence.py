"""Pure contract evidence tests; no LLM, host effects or application execution."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from mantleos import anchor_logic_evidence as e


class TestAnchorLogicalEvidence(unittest.TestCase):
    def setUp(self):
        self.public = {
            'schema':'demo.challenge/1',
            'gate_registry':{'gate_families':[{'id':'G-ACCESS'}]},
            'result_contract':{
                'result_kinds':{'snapshot':{'required_keys':['kind']}},
                'allowed_result_kinds_by_action':{'read':['snapshot']}},
            'expected_response_schema':{
                'required_fields':['trial_id','outcome','result','state','gate_families','reason'],
                'state_fields':['value'],
                'outcomes':['PREDICTED_FROM_ANCHORS','REJECTED_BY_GATE','UNDETERMINED']},
            'trials':[{'id':'T01','stimulus':{'action':'read'},'initial_state':{'value':'x'}},
                      {'id':'T02','stimulus':{'action':'unsupported'},'initial_state':{'value':'x'}}],
        }
        self.first={'trial_id':'T01','outcome':'PREDICTED_FROM_ANCHORS',
                    'result':{'kind':'snapshot'},'state':{'value':'x'},
                    'gate_families':['G-ACCESS'],'reason':''}
        self.second={'trial_id':'T02','outcome':'REJECTED_BY_GATE',
                     'result':None,'state':{'value':'x'},
                     'gate_families':['G-ACCESS'],'reason':'Unsupported action'}
        self.key={'schema':'demo.key/1','challenge_sha256':e.fingerprint(self.public),
                  'trial_count':2,'answers':[
                      {'trial_id':'T01','expected':{k:v for k,v in self.first.items() if k!='trial_id'}},
                      {'trial_id':'T02','expected':{k:v for k,v in self.second.items() if k!='trial_id'}}]}

    def test_reference_control_only_proves_scorer(self):
        report=e.evaluate(self.public,self.key,{'T01':self.first,'T02':self.second})
        self.assertEqual((2,2,2),(report['total_trials'],report['format_valid_trials'],report['prediction_match_trials']))
        self.assertEqual((8,8),(report['field_checks_excluding_reason_text'],report['field_matches_excluding_reason_text']))
        self.assertEqual('NOT_PERFORMED',report['implementation_verification'])
        self.assertIn('UNVERIFIED',report['model_independence'])

    def test_cli_scores_lf_and_crlf_identically_and_preserves_unicode(self):
        text = 'Café 🐦\r\nline\u0085next\u2028paragraph\u2029end'
        self.first['state']['value'] = text
        self.key['answers'][0]['expected']['state']['value'] = text
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = []
            for newline, label in (('\n', 'lf'), ('\r\n', 'crlf')):
                public = root / 'challenge.json'
                key = root / 'sealed.json'
                responses = root / 'responses.jsonl'
                report = root / f'{label}-report.json'
                for path, data in ((public, self.public), (key, self.key)):
                    raw = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
                    path.write_bytes(raw.replace('\n', newline).encode('utf-8'))
                rows = [e.canonical(row) for row in (self.first, self.second)]
                responses.write_bytes((newline.join(rows) + newline).encode('utf-8'))
                self.assertEqual(e.parse_responses(responses)['T01']['state']['value'], text)
                self.assertEqual(e.main(['--challenge', str(public), '--key', str(key),
                                         '--responses', str(responses), '--out', str(report)]), 0)
                reports.append(report.read_bytes())
            self.assertEqual(reports[0], reports[1])
            self.assertNotIn(b'\r\n', reports[0])
            self.assertEqual(json.loads(reports[0])['prediction_match_trials'], 2)

    def test_wrong_state_is_detected(self):
        changed=deepcopy(self.first); changed['state']['value']='wrong'
        report=e.evaluate(self.public,self.key,{'T01':changed,'T02':self.second})
        self.assertEqual(1,report['prediction_match_trials'])
        self.assertIn('state.value',report['trials'][0]['mismatches'])

    def test_bad_result_variant_is_format_invalid(self):
        changed=deepcopy(self.first);changed['result']={'kind':'snapshot','count':1}
        report=e.evaluate(self.public,self.key,{'T01':changed,'T02':self.second})
        self.assertEqual(1,report['format_valid_trials'])
        self.assertEqual('INVALID',report['trials'][0]['format'])

    def test_wrong_gate_is_rejected(self):
        changed=deepcopy(self.first);changed['gate_families']=['G-NOT-DECLARED']
        report=e.evaluate(self.public,self.key,{'T01':changed,'T02':self.second})
        self.assertEqual('INVALID',report['trials'][0]['format'])

    def test_drifted_challenge_fails_closed(self):
        bad=deepcopy(self.public);bad['trials'][0]['stimulus']['action']='write'
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            e.evaluate(bad,self.key,{'T01':self.first})

    def test_missing_submission_is_not_pass(self):
        report=e.evaluate(self.public,self.key,{'T01':self.first})
        self.assertEqual(1,report['prediction_match_trials'])
        self.assertEqual('MISSING',report['trials'][1]['format'])

    def test_unsupported_result_kind_is_invalid_even_if_expected(self):
        changed=deepcopy(self.first); changed['result']={'kind':'match'}
        report=e.evaluate(self.public,self.key,{'T01':changed})
        self.assertEqual('INVALID',report['trials'][0]['format'])

    def test_opaque_reason_text_is_not_claimed_semantically_checked(self):
        changed=deepcopy(self.second); changed['reason']='Different nonempty words'
        report=e.evaluate(self.public,self.key,{'T01':self.first,'T02':changed})
        self.assertEqual(2,report['prediction_match_trials'])
        self.assertIn('UNSCORED',report['reason_policy'])

    def test_public_expected_field_rejected(self):
        public=deepcopy(self.public);public['trials'][0]['expected']={'value':'x'}
        key=deepcopy(self.key);key['challenge_sha256']=e.fingerprint(public)
        with self.assertRaisesRegex(ValueError,'sealed fields'):
            e.evaluate(public,key,{'T01':self.first})


if __name__=='__main__':unittest.main()
