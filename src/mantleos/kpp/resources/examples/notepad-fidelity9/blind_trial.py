"""Model-neutral, source-hidden Notepad Anchor reasoning benchmark.

Prepare creates TWO disjoint exports: an interpreter-facing challenge containing
only declarative contract/stimuli and a private evaluator key containing expected
results. Scoring NEVER executes candidate-supplied code, imports a model SDK,
performs host effects, or claims independent LLM competence.

CLI:
  python blind_trial.py prepare --challenge-dir NEW --sealed-dir NEW
  python blind_trial.py score --key KEY.json --challenge CHALLENGE.json --responses FILE.jsonl --report NEW.json
  python blind_trial.py control --key KEY.json --output NEW.jsonl
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import random
import sys

from logical_engine import LogicalMachine, digest

HERE = Path(__file__).resolve().parent
CHALLENGE_SCHEMA = 'notepad.blind-logic-challenge/2'
KEY_SCHEMA = 'notepad.blind-logic-private-key/2'
RESPONSE_SCHEMA = 'notepad.blind-logic-response/1'
REPORT_SCHEMA = 'notepad.blind-logic-score/1'
FIELDS = ('trial_id', 'outcome', 'result', 'state', 'gate_families', 'reason')
STATE_FIELDS = ('text', 'clean_baseline', 'revision', 'dirty', 'undo_stack',
                'redo_stack', 'history_expected_revision', 'active_path',
                'clipboard', 'virtual_files')
VALID_OUTCOMES = {'PREDICTED_FROM_ANCHORS', 'REJECTED_BY_GATE', 'UNDETERMINED'}
MAX_RESPONSE_BYTES = 4096 * 41  # Enough for 41 complete bounded answers

# These are value-level output projections, not new Gates or Anchor definitions.
# One JSON variant is selected after applying the existing G-CMD-xx clause.
RESULT_VARIANTS = {
    'snapshot': {'required_keys': ['kind'], 'kind': 'snapshot', 'meaning': 'Document snapshot; no extra result fields'},
    'selection': {'required_keys': ['kind','selection'], 'kind': 'selection',
                  'selection': 'Two integer code-point offsets [start,end], half-open'},
    'match': {'required_keys': ['kind','selection'], 'kind': 'match',
              'selection': 'Matching code-point range [start,end], half-open'},
    'none': {'required_keys': ['kind'], 'kind': 'none',
             'meaning': 'Find completed successfully; no match exists under the declared search options'},
    'replace': {'required_keys': ['kind','count'], 'kind': 'replace',
                'count': 'Nonnegative integer number of matches replaced, including no-op replacements'},
}
ACTION_RESULT_KINDS = {
    'read':['snapshot'],'edit':['snapshot'],'insert':['snapshot'],'delete':['snapshot'],
    'undo':['snapshot'],'redo':['snapshot'],'new':['snapshot'],'open':['snapshot'],
    'save':['snapshot'],'save-as':['snapshot'],'copy':['snapshot'],'cut':['snapshot'],
    'paste':['snapshot'],'select-all':['selection'],'find':['match','none'],
    'replace-one':['replace'],'replace-all':['replace'],
}


def file_session_observation(machine):
    """Expose equality evidence, not a hidden SHA-256 value or presumed effect success.

    This is the virtual host's *pre-command* confirmed file-session observation.
    An associated file can be absent (Save then creates it) or externally altered.
    UNKNOWN is distinct from MISMATCH: unknown observations cannot be guessed.
    """
    path = machine.active_path
    if path is None:
        status = 'NO_ASSOCIATION'
    elif path not in machine.files:
        status = 'MISSING'
    elif machine.expected_digest is None:
        status = 'UNKNOWN'
    elif digest(machine.files[path]) == machine.expected_digest:
        status = 'MATCH'
    else:
        status = 'MISMATCH'
    return {'active_path':path, 'disk_comparison':status,
            'observation_source':'TRUSTED_VIRTUAL_HOST_PRECOMMAND'}


FILE_SESSION_OBSERVATION_CONTRACT = {
    'origin':'TRUSTED_VIRTUAL_HOST_PRECOMMAND',
    'comparison_values':{
        'NO_ASSOCIATION':'No active file path; Save rejects until associated through Open or Save As',
        'MISSING':'Active path absent from virtual files; Save may create file after other guards and confirmed FS_WRITE',
        'MATCH':'Current bytes at active path match last confirmed expected digest; not proof a future write succeeded',
        'MISMATCH':'Bytes at active path differ from last confirmed digest; Save and same-path Save As reject',
        'UNKNOWN':'Expected digest or required observation missing; do not assume equality',
    },
    'effect_order':'Check preconditions, perform virtual effect if authorized and available, then acknowledge baseline/path; effect failure must not be presented as a clean save',
    'not_an_output':'This input observation is intentionally not one of the ten public state projection fields or an independent authorization Gate.'
}


def complete_gate_registry(machine):
    """Show 9 families and all 19 clauses; no expected trial outcomes exposed."""
    conditions = deepcopy(machine.contract['gate_conditions'])
    families = deepcopy(machine.economy['gate_families'])
    assert len(conditions) == 19 and len(families) == 9
    return {'status':'PROJECT_PROPOSAL_NOT_CANONICAL_KPP',
            'gate_families':families, 'gate_conditions':conditions,
            'interpretation':'RUNTIME clauses govern user stimuli; G-UI-01 governs projection; G-BUILD-01 is offline build conformance and is not a user command gate.',
            'gate_counting':'19 independently testable clauses grouped into 9 proposed families; groups do not create new Gate conditions.'}


def declared_result_contract():
    return {'result_kinds':deepcopy(RESULT_VARIANTS),
            'allowed_result_kinds_by_action':deepcopy(ACTION_RESULT_KINDS),
            'rejection_or_undetermined':'result is exactly null; reason is nonempty',
            'success':'result is exactly one specified variant with no extra keys; reason is empty',
            'unsupported_command':'REJECTED_BY_GATE, result=null, gate_families=[], nonempty reason',
            'all_successful_commands':'One JSON result object, never a human-readable DocumentSnapshot label.'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return sha256(canonical(value).encode('utf-8')).hexdigest()


def parse_json(path, *, max_bytes=2_000_000):
    p=Path(path)
    if p.stat().st_size > max_bytes:
        raise ValueError('JSON input exceeds bound')
    def unique_pairs(pairs):
        result={}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    return json.loads(p.read_text('utf-8'), object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON'))) 


def file_projection(content):
    try:
        return {'text':content.decode('utf-8')}
    except UnicodeDecodeError:
        return {'bytes_hex':content.hex()}


def state_projection(machine):
    return {
        'text':machine.text,
        'clean_baseline':machine.baseline,
        'revision':machine.revision,
        'dirty':machine.dirty,
        'undo_stack':deepcopy(machine.undo),
        'redo_stack':deepcopy(machine.redo),
        'history_expected_revision':machine.expected_revision,
        'active_path':machine.active_path,
        'clipboard':machine.clipboard,
        'virtual_files':{k:file_projection(v) for k,v in sorted(machine.files.items())},
    }


def _scenario_machine(case):
    files={};aliases={}
    for key, value in case.get('files',{}).items():
        path='/virtual/'+key+'.txt'
        aliases['@'+key]=path
        files[path]=bytes.fromhex(value['hex']) if 'hex' in value else value['text'].encode('utf-8')
    for key in case.get('expected_files',{}):
        aliases.setdefault('@'+key,'/virtual/'+key+'.txt')
    machine=LogicalMachine(case['initial_text'],clipboard=case.get('clipboard',''),files=files)
    if case.get('fail_clipboard_read'):machine.fail_effects.add('CLIPBOARD_READ')
    if case.get('fail_clipboard_write'):machine.fail_effects.add('CLIPBOARD_WRITE')
    return machine, aliases


def build_trial_data():
    corpus=parse_json(HERE/'LOGICAL-TRACE-CORPUS.json')
    if len(corpus['cases'])!=32:
        raise ValueError('Unexpected scenario corpus count')
    trials=[]
    key_entries=[]
    reference=LogicalMachine()
    for case in corpus['cases']:
        machine, aliases=_scenario_machine(case)
        for step_index, step in enumerate(case['steps']):
            payload=deepcopy(step.get('payload'))
            if type(payload) is dict:
                payload={k:aliases.get(v,v) if type(v) is str else v for k,v in payload.items()}
            before=state_projection(machine)
            observed_file_session=file_session_observation(machine)
            result=machine.send(step['action'],payload)
            # Cross-check this independent interpreter against the existing frozen
            # corpus's per-step expected classification before sealing anything.
            wanted=step['outcome']
            if wanted=='rejected':
                if result['outcome']!='REJECTED_BY_GATE':
                    raise ValueError('Frozen scenario expectation failed: '+case['id'])
            else:
                if result['outcome']!='PREDICTED_FROM_ANCHORS' or result['result']['kind']!=wanted:
                    raise ValueError('Frozen scenario expectation failed: '+case['id'])
            source_packet=machine.last_packet
            # The source packet already contains no expected result. Convert the
            # host state to a comparison-friendly, model-runnable projection.
            trial={
                'initial_state':before,
                'stimulus':deepcopy(source_packet['stimulus']),
                'simulated_effect_failures':sorted(machine.fail_effects),
                'action_clause':deepcopy(source_packet['action_clause']),
                'gate_families':list(source_packet['gate_families']),
                'host_profile':source_packet['host_profile'],
                'file_session_observation':observed_file_session,
            }
            expected={
                'outcome':result['outcome'],
                'result':deepcopy(result.get('result')),
                'state':state_projection(machine),
                'gate_families':list(source_packet['gate_families']),
                'reason':'' if result['outcome']=='PREDICTED_FROM_ANCHORS' else str(result.get('reason','')),
            }
            trials.append(trial)
            key_entries.append({'source_case':case['id'],'source_step':step_index,'expected':expected})
        # A second preservation check pins each completed scenario's final state
        # to the original published expectations, independently of the new key.
        snap=machine.state()
        observed={name:snap[name] for name in ('text','revision','dirty','undo_count','redo_count')}
        if 'clipboard' in case['expected_final']:
            observed['clipboard']=snap['clipboard']
        if 'path' in case['expected_final']:
            observed['path']=next((alias for alias,path in aliases.items() if snap['path']==path),None)
        if observed!=case['expected_final']:
            raise ValueError('Frozen scenario final result drift: '+case['id'])
        for name,expected_text in case.get('expected_files',{}).items():
            if machine.files[aliases['@'+name]].decode('utf-8')!=expected_text:
                raise ValueError('Frozen scenario virtual file result drift: '+case['id'])
    if len(trials)!=41:
        raise ValueError('Unexpected stimulus count')
    # Opaque labels; original case names are private and cannot reveal correctness.
    order=list(range(len(trials)))
    random.Random(20261113).shuffle(order)
    public_trials=[];private_answers=[]
    for rank,offset in enumerate(order,1):
        ident=f'T{rank:04d}'
        entry={**trials[offset], 'id':ident}
        public_trials.append(entry)
        private_answers.append({'trial_id':ident,**key_entries[offset]['expected'],
                                'source_case':key_entries[offset]['source_case'],
                                'source_step':key_entries[offset]['source_step']})
    public={
        'schema':CHALLENGE_SCHEMA,
        'scope':'VIRTUAL_IN_MEMORY_ONLY; never claim OS file or clipboard effects',
        'purpose':'Predict each independent response using only declarative Anchor and Gate contracts.',
        'anchor_count':9,'gate_family_count':9,'gate_condition_count':19,
        'canonical_anchor_types':reference.contract['anchor_definition_types'],
        'anchor_applications':reference.contract['anchors'],
        'shared_semantics':reference.contract['semantics'],
        'rules':reference.economy['economy_rule'],
        'gate_registry':complete_gate_registry(reference),
        'file_session_observation_contract':deepcopy(FILE_SESSION_OBSERVATION_CONTRACT),
        'result_contract':declared_result_contract(),
        'trials':public_trials,
        'expected_response_schema':{
            'schema':RESPONSE_SCHEMA,
            'required_fields':list(FIELDS),
            'state_fields':list(STATE_FIELDS),
            'outcomes':sorted(VALID_OUTCOMES),
            'result':'null for rejected/undetermined; otherwise exact JSON variant in result_contract',
            'reason':'empty string for success; nonempty English explanation for rejection/unknown',
        },
    }
    private={'schema':KEY_SCHEMA,'challenge_sha256':fingerprint(public),
             'trial_count':len(private_answers),'answers':private_answers,
             'basis':'Independent reference interpreter + pre-existing scenario assertions; not a model accuracy score.'}
    return public,private


def prepare(challenge_dir, sealed_dir):
    ch=Path(challenge_dir);seal=Path(sealed_dir)
    if ch.resolve()==seal.resolve() or ch.resolve().is_relative_to(seal.resolve()) or seal.resolve().is_relative_to(ch.resolve()):
        raise ValueError('Challenge and sealed evaluator directories must be disjoint')
    if ch.exists() or seal.exists():
        raise ValueError('Output directories must be new; no overwrite')
    public, private=build_trial_data()
    ch.mkdir(parents=True);seal.mkdir(parents=True)
    (ch/'challenge.json').write_text(json.dumps(public,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (seal/'private-key.json').write_text(json.dumps(private,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (ch/'START-HERE.md').write_text(CHALLENGE_GUIDE,encoding='utf-8')
    (ch/'response-template.jsonl').write_text(canonical({'trial_id':'T0001',
        'outcome':'UNDETERMINED','result':None,
        'state':{key:None for key in STATE_FIELDS},
        'gate_families':[], 'reason':'Replace with contract-derived answer.'})+'\n',encoding='utf-8')
    (seal/'SEAL-README.md').write_text(SEALED_GUIDE,encoding='utf-8')
    return {'public_sha256':private['challenge_sha256'],'trials':len(public['trials']),
            'public_dir':str(ch),'sealed_dir':str(seal)}


def load_responses(path):
    b=Path(path).read_bytes()
    if len(b)>MAX_RESPONSE_BYTES:
        raise ValueError('Responses exceed byte limit')
    answers={}
    for index,line in enumerate(b.decode('utf-8').splitlines(),1):
        if not line.strip():continue
        value=json.loads(line,object_pairs_hook=lambda pairs:_unique(pairs),
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        if type(value) is not dict or set(value)!=set(FIELDS):
            raise ValueError('Response line '+str(index)+' needs exactly the declared fields')
        tid=value['trial_id']
        if type(tid) is not str or tid in answers:
            raise ValueError('Invalid or duplicate trial_id at line '+str(index))
        if value['outcome'] not in VALID_OUTCOMES:
            raise ValueError('Invalid outcome at line '+str(index))
        if type(value['state']) is not dict or set(value['state'])!=set(STATE_FIELDS):
            raise ValueError('State projection fields missing at line '+str(index))
        if type(value['gate_families']) is not list or any(type(x) is not str for x in value['gate_families']):
            raise ValueError('Invalid Gate identifiers at line '+str(index))
        if type(value['reason']) is not str:
            raise ValueError('Invalid reason at line '+str(index))
        if value['outcome']=='PREDICTED_FROM_ANCHORS':
            result=value['result']
            if type(result) is not dict or value['reason']:
                raise ValueError('Success needs a result and empty reason')
            kind=result.get('kind')
            if type(kind) is not str or kind not in RESULT_VARIANTS:
                raise ValueError('Unknown successful result kind at line '+str(index))
            if set(result) != set(RESULT_VARIANTS[kind]['required_keys']):
                raise ValueError('Successful result fields do not match kind at line '+str(index))
            if 'selection' in result:
                selection=result['selection']
                if (type(selection) is not list or len(selection)!=2 or
                    any(type(i) is not int or i<0 for i in selection) or
                    selection[0]>selection[1]):
                    raise ValueError('Invalid result selection at line '+str(index))
            if 'count' in result and (type(result['count']) is not int or result['count']<0):
                raise ValueError('Invalid result count at line '+str(index))
        elif value['result'] is not None or not value['reason']:
            raise ValueError('Rejection/unknown needs null result and reason')
        answers[tid]=value
    return answers


def _unique(pairs):
    o={}
    for k,v in pairs:
        if k in o:raise ValueError('Duplicate JSON field '+k)
        o[k]=v
    return o


def score(public,private,submitted):
    if public.get('schema')!=CHALLENGE_SCHEMA or private.get('schema')!=KEY_SCHEMA:
        raise ValueError('Wrong challenge/key schemas')
    if fingerprint(public)!=private['challenge_sha256']:
        raise ValueError('Challenge fingerprint does not match sealed private key')
    trial_ids=[t['id'] for t in public['trials']]
    if len(trial_ids)!=len(set(trial_ids)) or len(trial_ids)!=private['trial_count']:
        raise ValueError('Malformed challenge cardinality')
    if set(submitted)-set(trial_ids):
        raise ValueError('Unknown trial IDs')
    expected={r['trial_id']:r['expected'] if 'expected' in r else {k:r[k] for k in FIELDS if k!='trial_id'} for r in private['answers']}
    if set(expected)!=set(trial_ids):
        raise ValueError('Incomplete sealed answer key')
    cases=[];all_pass=0;fields_checked=0;field_pass=0
    for tid in trial_ids:
        got=submitted.get(tid)
        correct=expected[tid]
        field_mismatches=[]
        if got is None:
            field_mismatches=['MISSING_SUBMISSION']
        else:
            for field in ('outcome','result','gate_families'):
                fields_checked+=1
                if got[field]!=correct[field]:field_mismatches.append(field)
                else:field_pass+=1
            for field in STATE_FIELDS:
                fields_checked+=1
                if got['state'][field]!=correct['state'][field]:field_mismatches.append('state.'+field)
                else:field_pass+=1
            fields_checked+=1
            ok_reason=(got['reason']=='' if correct['outcome']=='PREDICTED_FROM_ANCHORS' else bool(got['reason']))
            if not ok_reason:field_mismatches.append('reason')
            else:field_pass+=1
        if not field_mismatches:all_pass+=1
        cases.append({'trial_id':tid,'pass':not field_mismatches,'mismatches':field_mismatches})
    return {'schema':REPORT_SCHEMA,'challenge_sha256':private['challenge_sha256'],
            'total_trials':len(trial_ids),'submitted_trials':len(submitted),
            'passed_trials':all_pass,'complete_pass':all_pass==len(trial_ids),
            'field_checks':fields_checked,'field_passes':field_pass,
            'results':cases,
            'scope':'MODEL-AGNOSTIC RESPONSE SCORING ONLY; no evidence of independent LLM unless execution provenance is separately established',
            'host_effect_claim':'VIRTUAL_ONLY; no real effects attested'}


def write_new(path,data):
    with Path(path).open('x',encoding='utf-8',newline='\n') as file:
        file.write(data)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    cmd=parser.add_subparsers(dest='cmd',required=True)
    p=cmd.add_parser('prepare',help='Produce separate public and private trial dirs')
    p.add_argument('--challenge-dir',required=True);p.add_argument('--sealed-dir',required=True)
    p=cmd.add_parser('control',help='Create a reference submission for verifier qualification, NOT an LLM run')
    p.add_argument('--key',required=True);p.add_argument('--output',required=True)
    p=cmd.add_parser('score',help='Score a response file without running candidate code or LLMs')
    p.add_argument('--challenge',required=True);p.add_argument('--key',required=True)
    p.add_argument('--responses',required=True);p.add_argument('--report',required=True)
    args=parser.parse_args(argv)
    try:
        if args.cmd=='prepare':
            result=prepare(args.challenge_dir,args.sealed_dir)
        elif args.cmd=='control':
            private=parse_json(args.key)
            if private.get('schema')!=KEY_SCHEMA:raise ValueError('Wrong private-key schema')
            lines=[canonical({k:(e[k] if k!='trial_id' else e['trial_id']) for k in FIELDS})
                   for e in private['answers']]
            write_new(args.output,'\n'.join(lines)+'\n')
            result={'control_file':args.output,'trials':len(lines),'provenance':'REFERENCE ANSWERS, NOT MODEL OUTPUT'}
        else:
            public=parse_json(args.challenge);private=parse_json(args.key)
            scored=score(public,private,load_responses(args.responses))
            write_new(args.report,json.dumps(scored,indent=2,ensure_ascii=False)+'\n')
            result={k:v for k,v in scored.items() if k not in ('results',)}
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
        return 0
    except (ValueError,KeyError,TypeError,FileNotFoundError,PermissionError,FileExistsError) as e:
        print('FAIL: '+str(e),file=sys.stderr)
        return 1


CHALLENGE_GUIDE='''# Notepad Anchor Code — Model-independent blind interpretation challenge

This is the **model-facing** packet only. The sealed expected results, reference
Python implementation, scenario labels and scoring machinery are intentionally absent.
This benchmark targets frontier models but does not depend on a model, SDK,
provider, chain-of-thought disclosure, Python runtime, or hosted API.

For **each** item in `challenge.json.trials`, use only its declared initial state,
stimulus, canonical Anchor types, the linked Gate condition and shared semantics.
Compute the **updated** state and user-visible result. Submit one standalone JSON
object per line to the evaluator as `responses.jsonl`; 41 lines, any order.

Required JSON keys exactly: `trial_id`, `outcome`, `result`, `state`,
`gate_families`, `reason`. The full state has 10 keys documented by the
`expected_response_schema`. Copy the initial state's virtual file values unless
an approved virtual effect changes them; do not invent real file/clipboard writes.
For a missing host observation or irreducible ambiguity, use `UNDETERMINED` and
explain why rather than fabricating a success. For rejected commands, use
`REJECTED_BY_GATE`, null result and preserve all state that should remain stable.
For successes use `PREDICTED_FROM_ANCHORS` and the clause-specific result object.

The explicit `result_contract` provides the exact allowed JSON result variants
and maps the 17 supported actions to those variants. `gate_registry` enumerates all
9 families and all 19 condition clauses. The build-time family is offline only,
not an additional runtime dispatch requirement. Each trial includes a pre-command
`file_session_observation.disk_comparison` from the trusted virtual host: MATCH,
MISMATCH, MISSING, NO_ASSOCIATION, or UNKNOWN. On Save, MISMATCH rejects, MISSING
may allow a new virtual write, and UNKNOWN requires UNDETERMINED if equality
is required. Do not calculate, invent, or assume a hidden expected SHA-256.
The observation is a precondition, not proof that a later write succeeded.

This is a **virtual host** exercise. Initial `virtual_files` values use either
`{"text":"..."}` for valid UTF-8 content or `{"bytes_hex":"fffe"}` for
invalid UTF-8. Do not compute SHA-256; it is intentionally excluded from the
required response. The provided prestate and contract still control the rules.
Document positions use Unicode code points, with half-open ranges.

Do not inspect any reference program, evaluator key or answered corpus. Do not
execute Python. All cases are independent snapshots, not a sequential API session.
The expectation is a falsifiable structured result, not disclosure of hidden model
reasoning. An operator should keep token/latency/retry/provenance logs separately.
'''

SEALED_GUIDE='''# Sealed evaluator material — DO NOT SHOW TO THE INTERPRETING MODEL

`private-key.json` maps opaque trial IDs to reference expected behavior and
original source-case labels. The cases were checked against existing Notepad
scenario expectations using the independent deterministic reference interpreter.
This does not establish frontier LLM accuracy, a universal formal proof, or KPP
Satisfaction/Baker acceptance. Keep the model-facing challenge directory separate.
`blind_trial.py control` can produce a reference response to qualify the scorer:
that control is **not** an LLM result and must never be reported as one.
'''

if __name__=='__main__':
    raise SystemExit(main())
