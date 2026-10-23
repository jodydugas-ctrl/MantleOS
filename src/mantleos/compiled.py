"""Versioned, indexed Bio-Software snapshots and a finite model-free interpreter."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re

from . import json_contract, cartridge, engram
from .transactions import atomic_bytes, ensure_clean

SCHEMA = 'mantle.compiled-body/1'
ABI = 'mantle.deterministic/1'
MAX_BYTES = 32 * 1024 * 1024
TOKEN = re.compile(r"[\w'-]+", re.UNICODE)


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('JSON size limit exceeded')
    return json_contract.loads(path.read_text('utf-8'))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def relative_file(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Unsafe program path')
    path = (Path(root)/name).resolve()
    if '..' in Path(name).parts or not path.is_relative_to(Path(root).resolve()) or not path.is_file():
        raise ValueError('Program source must be a portable Body file')
    return path


def bindings(body):
    return {rel:hashlib.sha256(path.read_bytes()).hexdigest()
            for path,rel in cartridge.tracked_paths(body)
            if rel not in {'COMPILED.json', 'ENGRAM.md'}}


def _programs(body):
    spec = read_json(body/'PROGRAMS.json') if (body/'PROGRAMS.json').exists() else {'schema':'mantle.programs/1','programs':[]}
    if set(spec) != {'schema','programs'} or spec['schema'] != 'mantle.programs/1' or not isinstance(spec['programs'],list) or len(spec['programs']) > 256:
        raise ValueError('Invalid program catalog')
    from .organs import system_registry
    registry = system_registry(body).capability_registry()
    compiled, required = {}, {}
    for program in spec['programs']:
        pid = json_contract.identifier(program.get('id'))
        if pid in compiled:
            raise ValueError('Duplicate program id')
        profile = program.get('profile')
        if profile == 'mantle.organ-call/1':
            json_contract.shape(program, {'id','profile','capability','arguments'})
            cap = registry.get(program['capability'])
            if type(program['arguments']) is not dict:
                raise ValueError('Organ arguments must be an object')
            # Mutating lifecycle operations are available explicitly through the registry,
            # but cannot be smuggled into a declarative read program.
            if cap.name not in {'body.status','body.verify','engram.query','anchor.language'}:
                raise ValueError('Organ program requires a supported read capability')
            contract = {'name':cap.name,'effect':cap.effect,'authority':cap.authority,'provider':cap.provider_id}
            required[cap.name] = contract
            compiled[pid] = {**deepcopy(program), 'contract':contract}
            continue
        json_contract.shape(program, {'id','profile','source'})
        path = relative_file(body, program['source'])
        from .anchor_app_document import read_source, is_document, parse
        source = read_source(path)
        item = {**program, 'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        if is_document(source):
            from .anchor_language import inspect_blueprint
            document_inspection = inspect_blueprint(source)
            if document_inspection['profile'] != profile:
                raise ValueError('Declared app document profile mismatch')
            item['app_document'] = document_inspection
            source = parse(source)['program']
        if profile == 'EMIT_TEXT/0.2':
            from .native_anchor import qualify_program
            from .anchor_engine.tools.anchor_runtime import program_stdout
            item.update(receipt=qualify_program(source,profile=profile), stdout=program_stdout(source))
        elif profile in {'AGENTIC/0.2','NOTEPAD_LLM/1.3'}:
            from .anchor_language import inspect_blueprint
            inspection=inspect_blueprint(source)
            if inspection['profile']!=profile:raise ValueError('Declared profile mismatch')
            item.update(inspection=inspection)
            if profile=='NOTEPAD_LLM/1.3':
                from .anchor_engine.tools.anchor_notepad import load_blueprint
                name,seed=load_blueprint(source)
                item.update(notepad_name=name,notepad_seed=seed)
        else:
            raise ValueError('Unsupported compiled profile: '+str(profile))
        compiled[pid] = item
    return compiled, required


def compile_body(body):
    """Compile a staged, verified Body. Never calls a model or runs generated Python."""
    body = Path(body).resolve()
    cartridge.verify(body)
    source_bindings=bindings(body)
    programs=required=None
    if (body/'COMPILED.json').exists():
        previous=json.loads((body/'COMPILED.json').read_text('utf-8'),object_pairs_hook=_unique)
        if previous.get('schema')==SCHEMA and previous.get('runtime_abi')==ABI and previous.get('sha256')==digest({k:v for k,v in previous.items() if k!='sha256'}):
            stable=lambda sources:{k:v for k,v in sources.items() if k not in {'ENGRAM.jsonl','PROGRAM-STATE.json'}}
            if stable(previous.get('sources',{}))==stable(source_bindings):
                programs,required=previous['programs'],previous['required_capabilities']
    if programs is None:programs, required = _programs(body)
    records = engram.read(body/'ENGRAM.jsonl')
    from .projection import build
    index = build(records)
    birth = read_json(body/'BIRTH.json')
    value = {'schema':SCHEMA, 'runtime_abi':ABI,
             'identity':birth['id'], 'ledger_head':engram.head(body/'ENGRAM.jsonl'),
             'sources':source_bindings, 'programs':programs, 'required_capabilities':required,
             'records':records, 'record_ids':{r['id']:i for i,r in enumerate(records)},
             'index':index}
    if 'version' in birth:
        from . import __version__
        value['compiler_version'] = __version__
    value['sha256'] = digest(value)
    encoded = (canonical(value)+'\n').encode('utf-8')
    if len(encoded) > MAX_BYTES:
        raise ValueError('Compiled Body exceeds size limit')
    atomic_bytes(body/'COMPILED.json', encoded)
    cartridge.write_manifest(body)
    return {'schema':'mantle.compile-receipt/1','result':'COMPILED','sha256':value['sha256'],
            'identity':value['identity'],'ledger_head':value['ledger_head'],
            'programs':sorted(programs),'records':len(records),'model_calls':0}


def _validate_program(program):
    profile = program['profile']
    if profile in {'AGENTIC/0.2','NOTEPAD_LLM/1.3'}:
        if program['inspection']['profile']!=profile:raise ValueError('Compiled profile mismatch')
        return
    if profile == 'mantle.organ-call/1':
        if program['capability'] not in {'body.status','body.verify','engram.query','anchor.language'}:
            raise ValueError('Unsupported organ program')
        return
    if profile in {'EMIT_TEXT/0.2'}:
        output = program['stdout'].encode('utf-8')
        if hashlib.sha256(output).hexdigest() != program['receipt']['stdout_sha256'] or len(output) > 131072:
            raise ValueError('Native output receipt mismatch')
        return
    raise ValueError('Unsupported compiled profile')


def load(body, *, expected_sha256=None):
    body = Path(body).resolve()
    ensure_clean(body)
    cartridge.verify(body)
    if (body/'TISSUE.json').exists():
        from .tissue import verify_body
        verify_body(body)
    path = body/'COMPILED.json'
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Compiled Body exceeds size limit')
    # The compiled envelope can exceed ordinary proposal JSON budgets.
    value = json.loads(path.read_text('utf-8'), object_pairs_hook=_unique)
    signature = value.get('sha256')
    if value.get('schema') != SCHEMA or value.get('runtime_abi') != ABI:
        raise ValueError('Unsupported compiled Body version')
    if signature != digest({k:v for k,v in value.items() if k!='sha256'}):
        raise ValueError('Compiled Body digest mismatch')
    if expected_sha256 is not None and signature != expected_sha256:
        raise ValueError('Compiled Body does not match trusted receipt')
    if value['sources'] != bindings(body):
        raise ValueError('Compiled Body is stale; compile after changes')
    records=engram.read(body/'ENGRAM.jsonl')
    ledger_head=records[-1]['sha256'] if records else engram.ZERO
    if value['identity'] != read_json(body/'BIRTH.json')['id'] or value['ledger_head'] != ledger_head:
        raise ValueError('Compiled identity or continuity mismatch')
    if value['records']!=records or value['record_ids']!={r['id']:i for i,r in enumerate(records)}:
        raise ValueError('Compiled records disagree with canonical history')
    from .organs import system_registry
    registry = system_registry(body).capability_registry()
    for name, contract in value['required_capabilities'].items():
        cap = registry.get(name)
        if contract != {'name':name,'effect':cap.effect,'authority':cap.authority,'provider':cap.provider_id}:
            raise ValueError('Compiled capability binding changed')
    for program in value['programs'].values():
        _validate_program(program)
    return value


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate compiled key')
        value[key] = item
    return value


def inspect(body):
    value = load(body)
    return {'schema':SCHEMA,'identity':value['identity'],'sha256':value['sha256'],
            'ledger_head':value['ledger_head'],'records':len(value['records']),
            'programs':{k:p['profile'] for k,p in value['programs'].items()},
            'runtime_abi':value['runtime_abi'],'model_calls':0}


def query(body, text='', *, record_id=None, limit=8, types=None, include_superseded=False, head=None, evidence=False):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Query limit must be 1..100')
    value = load(body)
    records=value['records'];index=value['index']
    if head is not None and head!=value['ledger_head']:
        from .projection import build
        if head==engram.ZERO:records=[]
        else:
            position=next((i for i,r in enumerate(records) if r['sha256']==head),None)
            if position is None:raise ValueError('Unknown historical head')
            records=records[:position+1]
        index=build(records)
    if record_id is not None:
        matches = [r for r in records if r['id']==record_id]
    else:
        from . import projection
        if evidence:return projection.evidence(records,index,text,limit=limit)
        return projection.query(records,index,text,limit=limit,types=types,include_superseded=include_superseded)
    return {'ledger_head':records[-1]['sha256'] if records else engram.ZERO,'matches':matches,'model_calls':0}


def execute(body, program_id, inputs=None, state=None, *, budget=4096):
    value = load(body)
    if program_id not in value['programs']:
        raise ValueError('Unknown compiled program')
    program = value['programs'][program_id]
    profile = program['profile']
    if profile == 'EMIT_TEXT/0.2':
        if inputs or state is not None:
            raise ValueError('EMIT_TEXT takes no inputs or state')
        result = {'status':'applied','stdout':program['stdout']}
    elif profile in {'AGENTIC/0.2'}:
        raise ValueError('Cognition is optional and currently unbound; use session start for an explicit handoff')
    elif profile=='NOTEPAD_LLM/1.3':
        from .anchor_engine.tools.anchor_notepad import Session
        if not isinstance(inputs,dict):raise ValueError('NOTEPAD requires an explicit JSON COMMAND')
        if state is None and (Path(body)/'PROGRAM-STATE.json').exists():
            state = read_json(Path(body)/'PROGRAM-STATE.json').get(program_id)
        outcome=Session(deepcopy(program['notepad_seed'] if state is None else state)).step(inputs)
        result={'schema':'mantle.anchor-execution/1','profile':profile,'result':outcome,'state':outcome['state'],
                'effect_claim':outcome['effect_claim'],'host':'NO_EXPORT_CAPABILITY'}
    else:
        if inputs or state is not None:
            raise ValueError('Bound organ program takes no dynamic inputs')
        from .organs import system_registry
        cap = system_registry(body).capability_registry().get(program['capability'])
        result = {'status':'applied','observation':cap.provider(deepcopy(program['arguments']))}
        if not cap.verifier(result['observation']):
            raise ValueError('Organ result failed verification')
    return {'schema':'mantle.compiled-run/1','program':program_id,'profile':profile,
            'compiled_sha256':value['sha256'],'result':result,'model_calls':0}
