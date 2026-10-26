"""Integrity-checked evaluation evidence, read-only projections and explicit replay.

Records carry claims and exact data. Hashes do not authenticate who evaluated it.
Nothing here imports the admission registry, operator API or effect dispatcher.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from importlib.resources import files

from . import __version__, canonical, vm
from .bytecode import decode, encode, MAX_PAYLOAD
from .compiler import compile_ir
from .parser import parse_program, parse_inputs
from .types import timestamp
from .errors import refuse

SCHEMA = 'mantle.reflex-evaluation/1'
TOOLKIT = 'reflex-book/' + __version__
MAX_RECORD_BYTES = 524288
HEX = re.compile(r'^[0-9a-f]+$')
REASONS = {'INPUT_MISSING','OBSERVATION_FUTURE','OBSERVATION_STALE','QUALITY_INADEQUATE',
           'GEOMETRY_UNSUPPORTED','BOUNDARY_UNCERTAIN','EXPLICIT_UNKNOWN'}


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def source_identity():
    """Digest shipped Python, specification and vectors; byte integrity, no authority."""
    base = files(__package__)
    pins = {}
    def visit(directory, prefix=''):
        for path in sorted(directory.iterdir(), key=lambda p:p.name):
            name = prefix + path.name
            if path.is_dir() and path.name != '__pycache__':
                visit(path, name+'/')
            elif path.is_file() and path.name.endswith(('.py','.md','.json','.cjs')):
                pins[name] = digest_bytes(path.read_bytes())
    visit(base)
    return {'toolkit':TOOLKIT, 'source_sha256':canonical.sha256(pins)}


def _exact(value, keys, what):
    if type(value) is not dict or set(value) != set(keys.split()):
        refuse('E_RECORD', 'Invalid '+what+' structure')


def _load(raw):
    # Separate bounded record loader. The 64 KiB program/input loader is unchanged.
    if type(raw) is not bytes or len(raw)>MAX_RECORD_BYTES:
        refuse('E_SIZE','Evaluation record exceeds 524288 bytes')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=canonical._pairs,
                           parse_float=canonical._not_number, parse_constant=canonical._not_number)
    except (UnicodeDecodeError, ValueError, RecursionError):
        refuse('E_RECORD','Invalid evaluation JSON')
    canonical._check(value)
    return value


def read(path):
    with Path(path).open('rb') as stream:
        value = _load(stream.read(MAX_RECORD_BYTES+1))
    validate(value)
    return value


def _seal(record):
    return {**record, 'record_sha256':canonical.sha256(record)}


def evaluate(executable, inputs, *, evaluated_at=None):
    """Explicit bounded reference evaluation. Never installs or approves a program."""
    prepared = vm.prepare(executable)
    bc = decode(executable)
    env = parse_inputs(inputs, bc['ir'])
    trace = vm.run_prepared(prepared, env, explain=True)
    at = evaluated_at or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    timestamp(at)
    record = _seal({'schema':SCHEMA, 'implementation':source_identity(),
                   'evaluated_at':at, 'authority':'NONE',
                   'executable_hex':executable.hex(), 'inputs':env, 'trace':trace,
                   'digests':{'executable_sha256':digest_bytes(executable),
                              'program_sha256':bc['program_sha256'],
                              'input_sha256':canonical.sha256(env),
                              'observation_values_sha256':canonical.sha256(env['values']),
                              'trace_sha256':canonical.sha256(trace)}})
    validate(record)
    return record


def validate(record):
    """Check syntax, pins and compile agreement, never evaluate the carried rule."""
    if len(canonical.dumps(record))>MAX_RECORD_BYTES:
        refuse('E_SIZE','Evaluation record too large')
    _exact(record, 'schema implementation evaluated_at authority executable_hex inputs trace digests record_sha256', 'record')
    if record['schema'] != SCHEMA:
        refuse('E_EDITION','Unsupported evaluation record version')
    if record['authority'] != 'NONE':
        refuse('E_AUTHORITY','Evaluation evidence supplies no authority')
    timestamp(record['evaluated_at'])
    _exact(record['implementation'], 'toolkit source_sha256', 'implementation')
    ident = record['implementation']
    if type(ident['toolkit']) is not str or not 1<=len(ident['toolkit'])<=80:
        refuse('E_RECORD','Invalid toolkit identity')
    if type(ident['source_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',ident['source_sha256']):
        refuse('E_RECORD','Invalid source digest')
    raw = record['executable_hex']
    if type(raw) is not str or not 80<=len(raw)<=2*(MAX_PAYLOAD+40) or not HEX.fullmatch(raw) or len(raw)%2:
        refuse('E_RECORD','Invalid executable encoding')
    executable = bytes.fromhex(raw)
    bc = decode(executable)
    env = parse_inputs(record['inputs'],bc['ir'])
    trace = record['trace']
    _exact(trace,'schema vm_version program_sha256 input_sha256 executed_pcs result refusal_code authorized decision reasons','trace')
    if (trace['schema']!='mantle.reflex-trace/0.2-experimental' or type(trace['vm_version']) is not str
            or len(trace['vm_version'])>80 or trace['authorized'] is not False or trace['refusal_code'] is not None):
        refuse('E_RECORD','Unsupported trace or authority claim')
    _exact(trace['result'],'status review_requested','result')
    if type(trace['decision']) is not str or trace['decision'] not in ('TRUE','FALSE','UNKNOWN'):
        refuse('E_RECORD','Invalid recorded decision')
    status = bc['ir']['outcomes'][trace['decision'].lower()]
    if trace['result'] != {'status':status, 'review_requested':status=='REQUEST_REVIEW' or
                          (status=='ANOMALY' and bc['ir']['on_anomaly']=='REQUEST_REVIEW')} or type(trace['result']['review_requested']) is not bool:
        refuse('E_RECORD','Inconsistent recorded result')
    pcs = trace['executed_pcs']
    if type(pcs) is not list or any(type(pc) is not int for pc in pcs) or pcs!=list(range(len(bc['instructions']))):
        refuse('E_RECORD','Invalid instruction references')
    reasons=trace['reasons']
    if type(reasons) is not list or len(reasons)>len(pcs) or (trace['decision']!='UNKNOWN' and reasons):
        refuse('E_RECORD','Invalid uncertainty reasons')
    for reason in reasons:
        _exact(reason,'code input pc','reason')
        if (type(reason['code']) is not str or reason['code'] not in REASONS or type(reason['pc']) is not int or
            not 0<=reason['pc']<len(pcs) or
            (reason['input'] is not None and (type(reason['input']) is not str or reason['input'] not in bc['ir']['inputs']))):
            refuse('E_RECORD','Invalid reason reference')
    if len({canonical.dumps(r) for r in reasons})!=len(reasons):
        refuse('E_RECORD','Duplicate reason')
    expected={'executable_sha256':digest_bytes(executable), 'program_sha256':bc['program_sha256'],
              'input_sha256':canonical.sha256(env), 'observation_values_sha256':canonical.sha256(env['values']),
              'trace_sha256':canonical.sha256(trace)}
    if (record['digests']!=expected or trace['program_sha256']!=bc['program_sha256'] or
        trace['input_sha256']!=expected['input_sha256'] or
        record['record_sha256']!=canonical.sha256({k:v for k,v in record.items() if k!='record_sha256'})):
        refuse('E_INTEGRITY','Evaluation record digest mismatch')
    return bc, env


def inspect_record(record):
    bc, env = validate(record)
    observations=[]
    for name,value in sorted(env['values'].items()):
        if type(value) is dict and value.get('type')=='GeoFix':
            delta = timestamp(env['clock_utc'])-timestamp(value['observed_at'])
            observations.append({'input':name,'observed_at':value['observed_at'],
                                 'age_seconds':delta.days*86400+delta.seconds,
                                 'source_claim':value['source'], 'evidence_class':'synthetic'})
    guards=[{'pc':i,'op':ins[0],'args':ins[1:]} for i,ins in enumerate(bc['instructions'])
            if ins[0] in ('CHECK_FRESH','CHECK_QUALITY','GUARD3')]
    # Include source guard declarations, even if an opcode name changes in a later edition.
    return {'schema':'mantle.reflex-inspection/1', 'status':'INTEGRITY_CHECKED',
            'checked':{'digests':record['digests'], 'record_sha256':record['record_sha256'],
                       'program_id':bc['ir']['id'], 'book':bc['ir']['book'],
                       'inputs':env, 'observations':observations, 'guards':bc['ir']['preconditions'],
                       'guard_instructions':guards},
            'recorded_claims':{'implementation':record['implementation'], 'evaluated_at':record['evaluated_at'],
                               'trace':record['trace']},
            'compatibility':'MATCH' if record['implementation']==source_identity() and record['trace']['vm_version']==vm.VM_VERSION else 'INCOMPATIBLE',
            'execution':'NOT_PERFORMED', 'authority':'NONE',
            'limits':'Digests check data integrity. Recorded decisions and timestamps are unverified claims until reproduction; reproduction cannot prove historical execution or authorship.'}


def compare(left, right):
    a,b=inspect_record(left),inspect_record(right)
    same_program=left['digests']['program_sha256']==right['digests']['program_sha256']
    compatible=(same_program and left['implementation']==right['implementation'] and
                left['trace']['vm_version']==right['trace']['vm_version'] and a['compatibility']==b['compatibility']=='MATCH')
    same_values=left['digests']['observation_values_sha256']==right['digests']['observation_values_sha256']
    return {'schema':'mantle.reflex-comparison/1', 'status':'COMPARED' if compatible else 'INCOMPATIBLE',
            'same_program':same_program,'same_observation_values':same_values,
            'same_input':left['digests']['input_sha256']==right['digests']['input_sha256'],
            'rule_clocks':[left['inputs']['clock_utc'],right['inputs']['clock_utc']],
            'freshness_changed':same_values and a['checked']['observations']!=b['checked']['observations'],
            'left':a,'right':b, 'execution':'NOT_PERFORMED', 'authority':'NONE'}


def reproduce(record):
    validate(record)
    if record['implementation']!=source_identity() or record['trace']['vm_version']!=vm.VM_VERSION:
        return {'status':'INCOMPATIBLE','authority':'NONE','execution':'NOT_PERFORMED'}
    actual=vm.run_prepared(vm.prepare(bytes.fromhex(record['executable_hex'])),record['inputs'],explain=True)
    matches=actual==record['trace']
    return {'schema':'mantle.reflex-reproduction/1','status':'REPRODUCED' if matches else 'MISMATCH',
            'trace_matches':matches,'actual_trace':actual,'record_sha256':record['record_sha256'],
            'execution':'BOUNDED_REFERENCE_EVALUATION','authority':'NONE',
            'limits':'A match establishes reproducibility, not authorship, approval or historical execution.'}


def render(projection):
    # JSON string escaping also escapes terminal controls, bidi and other Unicode labels.
    # Text and JSON views expose exactly the same projection and evidence distinctions.
    return json.dumps(projection,indent=2,ensure_ascii=True,sort_keys=True)


def demo(output):
    """One new directory, two evaluations of unchanged synthetic observation values."""
    from .cli import _write_new
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    try:
        base=files(__package__).joinpath('resources/examples')
        raw=encode(compile_ir(parse_program(base.joinpath('location_rule.json').read_bytes())))
        env=canonical.loads(base.joinpath('location_normal.json').read_bytes())
        fresh=evaluate(raw,env)
        env['clock_utc']='2026-10-23T12:10:00Z'
        stale=evaluate(raw,env)
        _write_new(output/'program.rfx',raw)
        _write_new(output/'input.json',canonical.dumps(fresh['inputs'])+b'\n')
        _write_new(output/'fresh.json',canonical.dumps(fresh)+b'\n')
        _write_new(output/'stale.json',canonical.dumps(stale)+b'\n')
        result=compare(fresh,stale)
        _write_new(output/'comparison.json',canonical.dumps(result)+b'\n')
        return result
    except BaseException:
        shutil.rmtree(output)
        raise
