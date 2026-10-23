"""AGENTIC/0.2: Anchor-defined, portable pause/resume and chat handoff.

Pure reference interpreter. Session checksums detect corruption, NOT tampering:
restored chat or PNG data remain untrusted until explicitly admitted by a host.
Tool callbacks are *read-only*, host registered and never authorized by a model.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .agentic_validation import AgenticError, _json_bytes, _decode, NAME, TOOL_ID, MAX_SOURCE_BYTES, MAX_HISTORY_BYTES
from .anchor_engine.tools.anchor_structure import check_structures

PROFILE = 'AGENTIC/0.2'
SESSION_SCHEMA = 'mantle.anchor-agent-session/0.2'
HANDOFF_SCHEMA = 'mantle.anchor-agent-handoff/0.2'
REPLY_SCHEMA = 'mantle.anchor-agent-reply/0.2'
PRIMER = Path(__file__).with_name('agentic_profiles') / 'primer_agentic_v0_2.txt'
DOC = re.compile(
    rf'ANCHOR BLUEPRINT: ({NAME})\nSTATUS: EXPERIMENTAL AGENTIC/0\.2\n\n'
    r'(BEGIN ANCHOR EXECUTION PRIMER\n.*?\nEND ANCHOR EXECUTION PRIMER)\n\n'
    rf'BEGIN MOLECULE ({NAME})\n(.*?)\nEND MOLECULE\n\n'
    rf'BEGIN EXECUTION\nRUN ({NAME})\nEND EXECUTION\n?', re.DOTALL)
OPS = (
    ('BlackHole','40','input','task'),
    ('Neutral','41','gateway','MIND.INFER'),
    ('WhiteHole','42','permission','host_tool_allowlist'),
    ('Neutral','43','tools',None),
    ('Neutral','44','checkpoint','hash_chain'),
    ('WhiteHole','45','limits',None),
    ('Neutral','49','session','portable_snapshot'),
    ('Neutral','4B','context',None),
    ('WhiteHole','4C','cancellation','explicit'),
    ('Neutral','4E','handoff','json_or_chromamem'),
    ('Neutral','46','condition','final_or_budget'),
)
HEX = re.compile(r'[0-9a-f]{64}\Z')
STATUSES = {'AWAITING_MIND','COMPLETED','TOOL_DENIED','TOOL_FAILED',
            'STEP_BUDGET_EXCEEDED','TOOL_BUDGET_EXCEEDED','CANCELLED'}


def _sha(obj):
    return hashlib.sha256(_json_bytes(obj, limit=MAX_HISTORY_BYTES)).hexdigest()


def _seal(obj):
    result = deepcopy(obj)
    result['sha256'] = _sha(result)
    return result


def _check_seal(obj, schema):
    if not isinstance(obj, dict) or obj.get('schema') != schema or not isinstance(obj.get('sha256'),str):
        raise AgenticError('INVALID_PORTABLE_ENVELOPE')
    data = {k:v for k,v in obj.items() if k!='sha256'}
    if not HEX.fullmatch(obj['sha256']) or _sha(data)!=obj['sha256']:
        raise AgenticError('PORTABLE_DIGEST_MISMATCH')


def parse(source: str) -> dict:
    if not isinstance(source,str) or not source or len(source.encode('utf-8'))>MAX_SOURCE_BYTES:
        raise AgenticError('INVALID_SOURCE_LENGTH')
    match = DOC.fullmatch(source)
    if match is None: raise AgenticError('INVALID_AGENTIC_BLUEPRINT')
    name, primer, molecule, _, run = match.groups()
    if name!=molecule or name!=run or primer!=PRIMER.read_text('utf-8').rstrip('\n'):
        raise AgenticError('UNMATCHED_NAME_OR_PRIMER')
    shapes = check_structures(source)
    if len(shapes)!=len(OPS):raise AgenticError('AGENTIC_OPERATION_COUNT')
    values={}
    for shape,(kind,opcode,key,required) in zip(shapes,OPS):
        if (shape.type,shape.opcode,shape.mass)!=(kind,opcode,'00'):
            raise AgenticError('UNSUPPORTED_OPCODE_OR_POLARITY')
        if not shape.variable.startswith(key+'='):raise AgenticError('UNEXPECTED_VARIABLE')
        value=_decode(shape.variable[len(key)+1:])
        if required is not None and required!=value:
            raise AgenticError('UNSUPPORTED_OPERATION_CONFIGURATION')
        values[key]=value
    tools, limits, context = values['tools'], values['limits'], values['context']
    if (not isinstance(tools,list) or len(tools)>16 or
        any(not isinstance(x,str) or not TOOL_ID.fullmatch(x) for x in tools) or len(tools)!=len(set(tools))):
        raise AgenticError('INVALID_TOOL_ALLOWLIST')
    if (not isinstance(limits,dict) or set(limits)!={'steps','tool_calls'} or
        any(type(limits[k]) is not int or not 0 < limits[k] <= 32 for k in limits)):
        raise AgenticError('INVALID_BUDGET')
    if (not isinstance(context,dict) or set(context)!={'max_messages'} or
        type(context['max_messages']) is not int or not 3<=context['max_messages']<=64):
        raise AgenticError('INVALID_CONTEXT_POLICY')
    return {'schema':'mantle.anchor-agentic-plan/0.2','profile':PROFILE,'name':name,
            'tools':tuple(tools),'limits':deepcopy(limits),'context':deepcopy(context),
            'operations':tuple(x[1] for x in OPS),
            'source_sha256':hashlib.sha256(source.encode('utf-8')).hexdigest(),
            'primer_sha256':hashlib.sha256(PRIMER.read_bytes()).hexdigest(),
            'authority':'NONE_FROM_BLUEPRINT'}


def _log(session, event, detail):
    packet={'seq':len(session['events'])+1, 'event':event, 'detail':deepcopy(detail),
            'previous_sha256':session['trace_head_sha256']}
    packet['sha256']=_sha(packet)
    session['events'].append(packet)
    session['trace_head_sha256']=packet['sha256']


def _session_check(plan, session, *, current_engram_base=None):
    _check_seal(session,SESSION_SCHEMA)
    expected={'schema','profile','name','source_sha256','primer_sha256','model_id',
              'engram_base','history','step','tool_calls','events','trace_head_sha256','status','text','sha256'}
    if set(session)!=expected:raise AgenticError('INVALID_SESSION_FIELDS')
    if (session['profile']!=PROFILE or session['name']!=plan['name'] or
        session['source_sha256']!=plan['source_sha256'] or
        session['primer_sha256']!=plan['primer_sha256']):
        raise AgenticError('SESSION_SOURCE_MISMATCH')
    if session['engram_base'] is not None and current_engram_base is None:
        raise AgenticError('ENGRAM_REVALIDATION_REQUIRED')
    if current_engram_base is not None and session['engram_base'] != current_engram_base:
        raise AgenticError('STALE_ENGRAM_BASE')
    if not isinstance(session['model_id'],str) or not 0<len(session['model_id'])<=128:
        raise AgenticError('INVALID_MODEL_ID')
    if (type(session['step']) is not int or not 0<=session['step']<=plan['limits']['steps'] or
        type(session['tool_calls']) is not int or not 0<=session['tool_calls']<=plan['limits']['tool_calls'] or
        session['status'] not in STATUSES):
        raise AgenticError('INVALID_SESSION_COUNTER')
    if ((session['status']=='COMPLETED' and not isinstance(session['text'],str)) or
        (session['status']!='COMPLETED' and session['text'] is not None)):
        raise AgenticError('INVALID_SESSION_TERMINAL')
    history=session['history']
    if not isinstance(history,list) or not history or not isinstance(history[0],dict) or history[0].get('role')!='user':
        raise AgenticError('INVALID_SESSION_HISTORY')
    if not isinstance(session['events'],list) or len(session['events'])>132:
        raise AgenticError('INVALID_SESSION_EVENTS')
    previous='0'*64
    for i,ev in enumerate(session['events']):
        if (not isinstance(ev,dict) or set(ev)!={'seq','event','detail','previous_sha256','sha256'} or
            ev['seq']!=i+1 or ev['previous_sha256']!=previous or
            _sha({k:v for k,v in ev.items() if k!='sha256'})!=ev['sha256']):
            raise AgenticError('INVALID_TRACE_CHAIN')
        previous=ev['sha256']
    if session['trace_head_sha256']!=previous:
        raise AgenticError('INVALID_TRACE_HEAD')
    _json_bytes(history,limit=MAX_HISTORY_BYTES)
    _json_bytes(session,limit=MAX_HISTORY_BYTES)
    return deepcopy(session)


def _request(plan,session):
    if session['status']!='AWAITING_MIND':return None
    max_messages=plan['context']['max_messages']
    history=session['history']
    if len(history)>max_messages:
        tail=history[-(max_messages-1):]
        # Keep the original user task and complete assistant/tool pairs.
        # Never place an orphaned tool observation at the start of projection.
        if tail and tail[0].get('role')=='tool':tail=tail[1:]
        projected=[history[0],*tail]
    else:
        projected=history
    req={'schema':'mantle.mind-request/0.2','model_id':session['model_id'],
         'source_sha256':session['source_sha256'],'messages':deepcopy(projected),
         'available_tools':list(plan['tools']),'step':session['step']+1,
         'provenance':'HOST_UNVERIFIED_CHAT_OR_MODEL',
         'effect_authority':'NONE_FROM_MODEL'}
    _json_bytes(req,limit=MAX_HISTORY_BYTES)
    return req


def _output(plan,session):
    session=_seal(session)
    # A handoff packet can be moved via clipboard, files, or ChromaMem PNG.
    # The sha256 is an integrity checksum, never authentication or permission.
    request=_request(plan,session)
    payload={'schema':HANDOFF_SCHEMA,'session':session,'request':request,
             'request_sha256':_sha(request) if request is not None else None,
             'status':session['status'],'authority':'UNTRUSTED_CARRIER_NO_EFFECTS'}
    return _seal(payload)


def begin(source, task, *, model_id='unbound', engram_base=None):
    plan=parse(source)
    if not isinstance(task,str) or not task.strip():raise AgenticError('INVALID_TASK')
    if not isinstance(model_id,str) or not model_id or len(model_id)>128:
        raise AgenticError('INVALID_MODEL_ID')
    _json_bytes(task)
    if engram_base is not None:
        if not isinstance(engram_base,dict) or len(_json_bytes(engram_base))>8192:
            raise AgenticError('INVALID_ENGRAM_BASE')
    session={'schema':SESSION_SCHEMA,'profile':PROFILE,'name':plan['name'],
             'source_sha256':plan['source_sha256'],'primer_sha256':plan['primer_sha256'],
             'model_id':model_id,'engram_base':deepcopy(engram_base),
             'history':[{'role':'user','content':task}], 'step':0,'tool_calls':0,
             'events':[],'trace_head_sha256':'0'*64,'status':'AWAITING_MIND','text':None}
    _log(session,'TURN_ADMITTED',{'source_sha256':plan['source_sha256'],'model_id':model_id})
    return _output(plan,session)


def verify_handoff(source, handoff, *, current_engram_base=None):
    plan=parse(source)
    _check_seal(handoff,HANDOFF_SCHEMA)
    if set(handoff)!={'schema','session','request','request_sha256','status','authority','sha256'}:
        raise AgenticError('INVALID_HANDOFF_FIELDS')
    if handoff['authority']!='UNTRUSTED_CARRIER_NO_EFFECTS':
        raise AgenticError('INVALID_HANDOFF_AUTHORITY')
    session=_session_check(plan,handoff['session'],current_engram_base=current_engram_base)
    req=_request(plan,session)
    if (handoff['request']!=req or handoff['request_sha256']!=(_sha(req) if req is not None else None)
            or handoff['status']!=session['status']):
        raise AgenticError('HANDOFF_REQUEST_MISMATCH')
    return deepcopy(handoff)


def reply_for(handoff,decision):
    """Prepare an explicit reply envelope; a manual chat can return equivalent JSON."""
    if not isinstance(handoff,dict) or handoff.get('request') is None:
        raise AgenticError('NO_PENDING_MIND_REQUEST')
    return {'schema':REPLY_SCHEMA,'request_sha256':handoff['request_sha256'],
            'decision':deepcopy(decision)}


def advance(source,handoff,reply,*,tools=None,authorized_tools=frozenset(),current_engram_base=None):
    plan=parse(source)
    verified=verify_handoff(source,handoff,current_engram_base=current_engram_base)
    session=deepcopy(verified['session']);session.pop('sha256')
    if session['status']!='AWAITING_MIND':raise AgenticError('SESSION_NOT_WAITING')
    if (not isinstance(reply,dict) or set(reply)!={'schema','request_sha256','decision'} or
        reply['schema']!=REPLY_SCHEMA or reply['request_sha256']!=verified['request_sha256']):
        raise AgenticError('INVALID_OR_STALE_MIND_REPLY')
    decision=reply['decision'];_json_bytes(decision)
    if not isinstance(decision,dict):raise AgenticError('INVALID_MIND_DECISION')
    tools={} if tools is None else tools
    if not isinstance(tools,Mapping) or any(not isinstance(k,str) or not callable(v) for k,v in tools.items()):
        raise AgenticError('INVALID_TOOL_REGISTRY')
    if not isinstance(authorized_tools,frozenset) or any(not isinstance(t,str) for t in authorized_tools):
        raise AgenticError('INVALID_HOST_ALLOWLIST')
    session['step']+=1
    kind=decision.get('kind')
    if kind=='final' and set(decision)=={'kind','text'} and isinstance(decision['text'],str):
        session['text']=decision['text'];session['status']='COMPLETED'
        _log(session,'MIND_FINAL',{'step':session['step'],'text_sha256':hashlib.sha256(decision['text'].encode()).hexdigest()})
    elif kind=='tool' and set(decision)=={'kind','name','arguments'} and isinstance(decision['name'],str) and isinstance(decision['arguments'],dict):
        name,arguments=decision['name'],decision['arguments']
        _log(session,'TOOL_PROPOSED',{'step':session['step'],'name':name,'arguments_sha256':_sha(arguments)})
        if name not in plan['tools'] or name not in authorized_tools or name not in tools:
            session['status']='TOOL_DENIED'
            _log(session,'TOOL_DENIED',{'name':name,'reason':'NOT_GRANTED_BY_HOST_AND_BLUEPRINT'})
        elif session['tool_calls']>=plan['limits']['tool_calls']:
            session['status']='TOOL_BUDGET_EXCEEDED'
            _log(session,'TOOL_BUDGET_EXCEEDED',{'name':name})
        else:
            session['tool_calls']+=1
            try:
                observation=tools[name](deepcopy(arguments))
                _json_bytes(observation)
            except Exception as exc:
                session['status']='TOOL_FAILED'
                _log(session,'TOOL_FAILED',{'name':name,'error_type':type(exc).__name__})
            else:
                session['history'].extend([{'role':'assistant','tool_call':{'name':name,'arguments':deepcopy(arguments)}},
                                           {'role':'tool','name':name,'observation':deepcopy(observation)}])
                _log(session,'TOOL_OBSERVED',{'name':name,'result_sha256':_sha(observation)})
                if session['step']>=plan['limits']['steps']:
                    session['status']='STEP_BUDGET_EXCEEDED'
    else:
        raise AgenticError('INVALID_MIND_DECISION')
    if session['status']!='AWAITING_MIND':
        _log(session,'TURN_STOPPED',{'status':session['status'],'tool_calls':session['tool_calls']})
    return _output(plan,session)


def cancel(source,handoff,*,current_engram_base=None):
    plan=parse(source)
    verified=verify_handoff(source,handoff,current_engram_base=current_engram_base)
    session=deepcopy(verified['session']);session.pop('sha256')
    if session['status']!='AWAITING_MIND':raise AgenticError('SESSION_ALREADY_TERMINAL')
    session['status']='CANCELLED'
    _log(session,'TURN_STOPPED',{'status':'CANCELLED','tool_calls':session['tool_calls']})
    return _output(plan,session)


def run(source, command, *, mind=None, tools=None, authorized_tools=frozenset(), model_id='unbound'):
    """Optional fully local driver. No SDK or network dependency; chat flow uses begin/advance."""
    if not isinstance(command,dict) or set(command)!={'task'}:
        raise AgenticError('INVALID_TASK')
    if not callable(mind):raise AgenticError('MIND_GATEWAY_NOT_BOUND')
    state=begin(source,command['task'],model_id=model_id)
    while state['status']=='AWAITING_MIND':
        decision=mind(deepcopy(state['request']))
        state=advance(source,state,reply_for(state,decision),
                      tools=tools,authorized_tools=authorized_tools)
    session=state['session']
    return {'schema':'mantle.anchor-agentic-receipt/0.2','profile':PROFILE,
            'status':session['status'],'text':session['text'],'tool_calls':session['tool_calls'],
            'trace_head_sha256':session['trace_head_sha256'],'events':session['events'],
            'source_sha256':session['source_sha256'],'model_id':session['model_id'],
            'engram_writes':0,'effect_claim':'NONE','authority':'HOST_TOOL_REGISTRATION_ONLY'}


def write_json(handoff,output):
    """Explicit, exclusive file export. No Engram commit or auto-execution."""
    _check_seal(handoff,HANDOFF_SCHEMA)
    target=Path(output)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as f:
        f.write(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n')
    return {'path':str(target),'sha256':handoff['sha256'],'authority':'NONE'}


def read_json(path):
    raw=Path(path).read_bytes()
    if len(raw)>MAX_HISTORY_BYTES:raise AgenticError('HANDOFF_SIZE_LIMIT')
    try: value=_decode(raw.decode('utf-8'))
    except UnicodeError as exc:raise AgenticError('INVALID_HANDOFF_ENCODING') from exc
    _check_seal(value,HANDOFF_SCHEMA)
    return value


def write_chroma_png(handoff,output):
    """Optional *lossless* PNG carrier using existing ChromaMem v5 validation.

    Image recompression or transformations will destroy the payload; treat as an
    explicit data export, not a sandbox bypass or an authentication mechanism.
    """
    from . import chromamem
    _check_seal(handoff,HANDOFF_SCHEMA)
    blob=json.dumps(handoff,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    if len(blob.encode())>MAX_HISTORY_BYTES:raise AgenticError('HANDOFF_SIZE_LIMIT')
    png=chromamem._encode([chromamem._record('mantle.agentic.handoff.001',blob,'PORTABLE_HANDOFF')])
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(png)
    return {'path':str(target),'bytes':len(png),'sha256':hashlib.sha256(png).hexdigest(),
            'authority':'UNTRUSTED_CARRIER_NO_EFFECTS'}


def read_chroma_png(path):
    from . import chromamem
    decoded=chromamem.decode(path)
    if len(decoded['records'])!=1:raise AgenticError('INVALID_HANDOFF_CARRIER')
    item=decoded['records'][0]
    if item['meta']!={'id':'mantle.agentic.handoff.001','group':'PORTABLE_HANDOFF'}:
        raise AgenticError('INVALID_HANDOFF_CARRIER')
    value=_decode(item['text'])
    _check_seal(value,HANDOFF_SCHEMA)
    return value
