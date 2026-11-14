"""Optional model-independent scoring of Anchor logical interpretation trials.

This is an evidence transport and comparison tool, NOT an Anchor interpreter,
canonical type registry, gate executor, effect broker, or Baker acceptance path.
Model-facing and sealed answer sources must be kept separate by the operator.
The caller must independently establish the origin of the answer key and model run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = 'anchor.logical-evidence-report/1'
MAX_BYTES = 2_000_000


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(data):
    return hashlib.sha256(canonical(data).encode('utf-8')).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def _read(path, limit=MAX_BYTES):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Input exceeds byte limit')
    return raw.decode('utf-8')


def parse_json(path):
    return json.loads(_read(path), object_pairs_hook=_unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+x)))


def parse_responses(path):
    """Parse bounded JSONL, rejecting duplicate keys and duplicate trial IDs."""
    result = {}
    # JSONL uses LF (with an optional preceding CR). Unicode line separators
    # inside JSON strings are data, so splitlines() would corrupt a record.
    for index, line in enumerate(_read(path).split('\n'), 1):
        if not line.strip():
            continue
        value = json.loads(line, object_pairs_hook=_unique,
                           parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+x)))
        if type(value) is not dict or type(value.get('trial_id')) is not str or not value['trial_id']:
            raise ValueError(f'Invalid response object on line {index}')
        tid = value['trial_id']
        if tid in result:
            raise ValueError(f'Duplicate trial ID: {tid}')
        result[tid] = value
    return result


def _unique_names(value, label):
    if type(value) is not list or not value or any(type(x) is not str or not x for x in value):
        raise ValueError('Invalid '+label)
    if len(value) != len(set(value)):
        raise ValueError('Duplicate '+label)
    return value


def _protocol(challenge, sealed):
    if type(challenge) is not dict or type(sealed) is not dict:
        raise ValueError('Challenge and key must be objects')
    if fingerprint(challenge) != sealed.get('challenge_sha256'):
        raise ValueError('Challenge fingerprint mismatch; reject mixed or modified key')
    spec = challenge.get('expected_response_schema')
    if type(spec) is not dict:
        raise ValueError('Missing response schema')
    fields = _unique_names(spec.get('required_fields'), 'response fields')
    state_fields = _unique_names(spec.get('state_fields'), 'state fields')
    outcomes = _unique_names(spec.get('outcomes'), 'outcomes')
    if not {'trial_id', 'outcome', 'result', 'state', 'gate_families', 'reason'} <= set(fields):
        raise ValueError('Incomplete response envelope')
    trials = challenge.get('trials')
    if type(trials) is not list or not trials or any(type(t) is not dict for t in trials):
        raise ValueError('Missing trials')
    ids = [t.get('id') for t in trials]
    if any(type(t) is not str or not t for t in ids) or len(ids) != len(set(ids)):
        raise ValueError('Duplicate/invalid challenge trial IDs')
    if any({'expected', 'source_case', 'answer'} & set(t) for t in trials):
        raise ValueError('Model-facing trial contains sealed fields')
    answers = sealed.get('answers')
    if type(answers) is not list or sealed.get('trial_count') != len(trials):
        raise ValueError('Incorrect sealed answer cardinality')
    expected = {}
    for entry in answers:
        if type(entry) is not dict or type(entry.get('trial_id')) is not str:
            raise ValueError('Invalid sealed answer')
        tid = entry['trial_id']
        if tid in expected:
            raise ValueError('Duplicate sealed answer')
        expected[tid] = entry['expected'] if 'expected' in entry else {k:entry[k] for k in fields if k!='trial_id'}
    if set(ids) != set(expected):
        raise ValueError('Sealed answers and public trial IDs differ')
    rc = challenge.get('result_contract', {})
    kinds = rc.get('result_kinds', {})
    by_action = rc.get('allowed_result_kinds_by_action', {})
    if type(kinds) is not dict or type(by_action) is not dict:
        raise ValueError('Invalid result contract')
    registry = challenge.get('gate_registry', {})
    gate_names = {f['id'] for f in registry.get('gate_families', [])} if registry else set()
    return fields, state_fields, outcomes, trials, expected, kinds, by_action, gate_names


def _validate_response(value, trial, fields, state_fields, outcomes, kinds, by_action, gate_names):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError('Incorrect response envelope')
    if value['outcome'] not in outcomes:
        raise ValueError('Unknown outcome')
    state = value['state']
    if type(state) is not dict or set(state) != set(state_fields):
        raise ValueError('Incorrect state projection')
    families = value['gate_families']
    if type(families) is not list or any(type(x) is not str for x in families) or len(families) != len(set(families)):
        raise ValueError('Invalid Gate family list')
    if gate_names and not set(families) <= gate_names:
        raise ValueError('Unknown Gate family')
    if type(value['reason']) is not str:
        raise ValueError('Invalid reason type')
    if value['outcome'] != 'PREDICTED_FROM_ANCHORS':
        if value['result'] is not None or not value['reason'].strip():
            raise ValueError('Rejected/undetermined result requires null and a reason')
        return
    if value['reason']:
        raise ValueError('Success reason must be empty')
    result = value['result']
    if type(result) is not dict or type(result.get('kind')) is not str:
        raise ValueError('Success needs a tagged result')
    kind = result['kind']
    if kind not in kinds:
        raise ValueError('Undeclared result kind')
    defined = kinds[kind]
    if set(result) != set(defined['required_keys']):
        raise ValueError('Result fields do not match declared kind')
    action = trial.get('stimulus', {}).get('action')
    if action in by_action and kind not in by_action[action]:
        raise ValueError('Result kind is not valid for action')
    if 'selection' in result:
        s = result['selection']
        if (type(s) is not list or len(s) != 2 or
            any(type(v) is not int or v < 0 for v in s) or s[0] > s[1]):
            raise ValueError('Invalid selection range')
    if 'count' in result and (type(result['count']) is not int or result['count'] < 0):
        raise ValueError('Invalid replace count')


def evaluate(challenge, sealed, submitted):
    """Score exact state/result agreement; treat reason *wording* as unverified.

    A malformed answer is reported per trial, not confused with an incorrect
    transition. Missing submissions also do not count as format-valid.
    """
    fields, state_fields, outcomes, trials, expected, kinds, by_action, gate_names = _protocol(challenge, sealed)
    if type(submitted) is not dict:
        raise ValueError('Submissions must map trial_id to response objects')
    ids = {t['id'] for t in trials}
    if set(submitted) - ids:
        raise ValueError('Submission contains unknown trial IDs')
    report = []
    correct_trials = valid_format = 0
    field_checks = field_matches = 0
    for trial in trials:
        tid = trial['id']
        response = submitted.get(tid)
        if response is None:
            report.append({'trial_id':tid, 'format':'MISSING', 'prediction':'NOT_SCORED', 'mismatches':['MISSING_SUBMISSION']})
            continue
        try:
            _validate_response(response, trial, fields, state_fields, outcomes, kinds, by_action, gate_names)
        except (ValueError, KeyError, TypeError) as exc:
            report.append({'trial_id':tid, 'format':'INVALID', 'prediction':'NOT_SCORED', 'mismatches':[str(exc)]})
            continue
        valid_format += 1
        answer = expected[tid]
        mismatches = []
        for field in ('outcome', 'result', 'gate_families'):
            field_checks += 1
            if response[field] == answer[field]:field_matches += 1
            else:mismatches.append(field)
        for field in state_fields:
            field_checks += 1
            if response['state'][field] == answer['state'][field]:field_matches += 1
            else:mismatches.append('state.'+field)
        # The text of a reason is not semantically checked: only its structural
        # presence is validated above. Do not misreport this as an exact field.
        if not mismatches:correct_trials += 1
        report.append({'trial_id':tid, 'format':'VALID', 'prediction':'MATCH' if not mismatches else 'MISMATCH', 'mismatches':mismatches})
    return {
        'schema':SCHEMA,
        'challenge_sha256':fingerprint(challenge),
        'total_trials':len(trials), 'submitted_trials':len(submitted),
        'format_valid_trials':valid_format, 'prediction_match_trials':correct_trials,
        'field_checks_excluding_reason_text':field_checks,
        'field_matches_excluding_reason_text':field_matches,
        'reason_policy':'NONEMPTY_FOR_REJECTION_OR_UNKNOWN; EMPTY_FOR_SUCCESS; SEMANTIC_TEXT_UNSCORED',
        'implementation_verification':'NOT_PERFORMED',
        'model_independence':'UNVERIFIED_WITHOUT_EXTERNAL_TRIAL_PROVENANCE',
        'baker_acceptance':'NOT_GRANTED',
        'trials':report,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description='Score model-neutral Anchor logical response evidence')
    parser.add_argument('--challenge',required=True)
    parser.add_argument('--key',required=True)
    parser.add_argument('--responses',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    result=evaluate(parse_json(args.challenge),parse_json(args.key),parse_responses(args.responses))
    with Path(args.out).open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='trials'},sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
