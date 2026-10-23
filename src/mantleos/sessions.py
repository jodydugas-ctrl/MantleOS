"""Durable NEST controller for native Anchor handoffs and bounded delegation.

Portable session state is separate from canonical Engram continuity. The existing
AGENTIC interpreter defines semantics; this module supplies durability, host
binding, cancellation and replay control without a second language or ledger.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import signal
import sqlite3
import subprocess
import tempfile
import time
import uuid

from . import agentic_continuity as agentic, cartridge, checkpoint, compiled, engram
from .transactions import atomic_bytes, body_lock


def escalation(task_class='routine', *, failures=0, conflicting=False):
    return {'delegate':task_class in {'architecture','security','research','complex'} or failures>=2 or conflicting,
            'authority':'ADVICE_ONLY','reason':'policy-signal','automatic_build':False}


@contextmanager
def database(nest, body=None):
    nest=Path(nest).resolve()
    if body is not None and nest.is_relative_to(Path(body).resolve()):
        raise ValueError('NEST must be outside portable Body')
    nest.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(nest/'sessions.sqlite',timeout=5)
    try:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, body TEXT NOT NULL, source TEXT NOT NULL, base TEXT NOT NULL, handoff TEXT NOT NULL, deadline REAL NOT NULL, attempts INTEGER NOT NULL, max_attempts INTEGER NOT NULL, lease REAL, state TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS replies (session_id TEXT NOT NULL, request_hash TEXT NOT NULL, reply_hash TEXT NOT NULL, handoff TEXT NOT NULL, PRIMARY KEY(session_id,request_hash))')
        yield db
        db.commit()
    except BaseException:
        db.rollback();raise
    finally:db.close()


def _row(db,session_id):
    row=db.execute('SELECT * FROM sessions WHERE id=?',(session_id,)).fetchone()
    if row is None:raise ValueError('Unknown session')
    return row


def _checked(row):
    body=Path(row['body'])
    cartridge.verify(body)
    current=checkpoint.identity(body)
    if current!=json.loads(row['base']):raise ValueError('Stale Engram base; begin a new session')
    handoff=json.loads(row['handoff'])
    agentic.verify_handoff(row['source'],handoff,current_engram_base=current)
    return handoff,current


def start(body,program,task,*,nest,timeout=300,max_attempts=3,model_id='unbound'):
    if type(timeout) not in {int,float} or not 1<=timeout<=86400:raise ValueError('Invalid session timeout')
    if type(max_attempts) is not int or not 1<=max_attempts<=5:raise ValueError('Invalid retry limit')
    body=Path(body).resolve()
    with body_lock(body):
        value=compiled.load(body)
        item=value['programs'].get(program)
        if item is None or item['profile']!='AGENTIC/0.2':raise ValueError('Session requires a compiled AGENTIC/0.2 program')
        source=compiled.relative_file(body,item['source']).read_text('utf-8')
        base=checkpoint.identity(body)
        handoff=agentic.begin(source,task,model_id=model_id,engram_base=base)
        session_id=uuid.uuid4().hex
        with database(nest,body) as db:
            db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)',
                (session_id,str(body),source,compiled.canonical(base),compiled.canonical(handoff),time.time()+timeout,0,max_attempts,None,'AWAITING_MIND'))
        return {'session_id':session_id,'handoff':handoff,'canonical_engram_writes':0}


def inspect(nest,session_id):
    with database(nest) as db:
        row=_row(db,session_id)
        return {'session_id':session_id,'state':row['state'],'attempts':row['attempts'],
                'deadline':row['deadline'],'handoff':json.loads(row['handoff'])}


def advance(nest,session_id,reply,*,allow_lookup=False):
    # Ordering is Body lock -> database transaction throughout admission paths.
    with database(nest) as db:body=Path(_row(db,session_id)['body'])
    with body_lock(body),database(nest,body) as db:
        db.execute('BEGIN IMMEDIATE');row=_row(db,session_id)
        handoff,base=_checked(row)
        request_hash=reply.get('request_sha256') if isinstance(reply,dict) else None
        reply_hash=compiled.digest(reply)
        previous=db.execute('SELECT * FROM replies WHERE session_id=? AND request_hash=?',(session_id,request_hash)).fetchone()
        if previous:
            if previous['reply_hash']!=reply_hash:raise ValueError('Conflicting replay')
            return {'session_id':session_id,'handoff':json.loads(previous['handoff']),'replayed':True}
        if row['state']!='AWAITING_MIND':raise ValueError('Session is not awaiting a reply')
        if time.time()>row['deadline']:raise ValueError('Session deadline expired')
        tools={'lookup':lambda arguments:compiled.query(body,arguments.get('text',arguments.get('term','')))} if allow_lookup else {}
        result=agentic.advance(row['source'],handoff,reply,tools=tools,
            authorized_tools=frozenset(tools),current_engram_base=base)
        encoded=compiled.canonical(result)
        db.execute('INSERT INTO replies VALUES (?,?,?,?)',(session_id,request_hash,reply_hash,encoded))
        db.execute('UPDATE sessions SET handoff=?,state=?,lease=NULL WHERE id=?',(encoded,result['status'],session_id))
        return {'session_id':session_id,'handoff':result,'canonical_engram_writes':0,'replayed':False}


def cancel(nest,session_id):
    with database(nest) as db:body=Path(_row(db,session_id)['body'])
    with body_lock(body),database(nest,body) as db:
        db.execute('BEGIN IMMEDIATE');row=_row(db,session_id)
        if row['state']=='CANCELLED':return {'session_id':session_id,'state':'CANCELLED'}
        # Cancellation retires a request even when its Body has since changed.
        handoff,base=json.loads(row['handoff']),json.loads(row['base'])
        result=agentic.cancel(row['source'],handoff,current_engram_base=base)
        db.execute('UPDATE sessions SET handoff=?,state=?,lease=NULL WHERE id=?',(compiled.canonical(result),'CANCELLED',session_id))
        return {'session_id':session_id,'state':'CANCELLED','handoff':result}


def export(nest,session_id,output):
    with database(nest) as db:
        row=_row(db,session_id);handoff,_=_checked(row)
    if str(output).lower().endswith('.png'):
        from . import chromamem
        payload=chromamem._encode([chromamem._record('mantle.agentic.handoff.001',compiled.canonical(handoff),'PORTABLE_HANDOFF')])
    else:payload=(compiled.canonical(handoff)+'\n').encode('utf-8')
    atomic_bytes(output,payload,replace=False)
    return {'result':'EXPORTED','output':str(output),'session_id':session_id,'sha256':handoff['sha256']}


def import_handoff(body,program,source,*,nest,timeout=300):
    body=Path(body).resolve()
    with body_lock(body):
        item=compiled.load(body)['programs'][program]
        if item['profile']!='AGENTIC/0.2':raise ValueError('Unsupported session profile')
        code=compiled.relative_file(body,item['source']).read_text('utf-8')
        state=agentic.read_chroma_png(source) if str(source).lower().endswith('.png') else agentic.read_json(source)
        base=checkpoint.identity(body);agentic.verify_handoff(code,state,current_engram_base=base)
        if state['session']['engram_base']!=base:raise ValueError('Unbound sessions cannot be silently adopted')
        if not 1<=timeout<=86400:raise ValueError('Invalid timeout')
        sid=uuid.uuid4().hex
        with database(nest,body) as db:
            db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (sid,str(body),code,compiled.canonical(base),compiled.canonical(state),time.time()+timeout,0,3,None,state['status']))
        return {'session_id':sid,'handoff':state,'replay_scope':'THIS_NEST_ONLY','canonical_engram_writes':0}


def accept(nest,session_id,*,evidence):
    """Explicit operator admission, separate from receiving a model response."""
    if not isinstance(evidence,str) or not evidence.strip() or len(evidence)>8192:raise ValueError('Admission evidence is required')
    with database(nest) as db:body=Path(_row(db,session_id)['body'])
    from .lifecycle import admit
    with body_lock(body),database(nest,body) as db:
        db.execute('BEGIN IMMEDIATE');row=_row(db,session_id)
        admission_key=compiled.digest({'session_id':session_id,'base':json.loads(row['base'])})
        prior=next((r for r in engram.read(body/'ENGRAM.jsonl') if r['type']=='session-admission' and r['body'].get('admission_key')==admission_key),None)
        if prior:
            db.execute('UPDATE sessions SET state=? WHERE id=?',('ADMITTED',session_id))
            return {'result':'ALREADY_ADMITTED','record':prior['id']}
        handoff,base=_checked(row)
        if row['state']!='COMPLETED':raise ValueError('Only completed sessions can be admitted')
        result=admit(body,'session-admission',{'session_id':session_id,'admission_key':admission_key,
            'text':handoff['session']['text'],'session_sha256':handoff['session']['sha256'],
            'evidence':evidence,'evidence_class':'OPERATOR_ATTESTATION'},expected_head=engram.head(body/'ENGRAM.jsonl'))
        db.execute('UPDATE sessions SET state=? WHERE id=?',('ADMITTED',session_id))
        return result


def _stop(process):
    if process.poll() is not None:return
    if os.name=='nt':
        subprocess.run([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/taskkill.exe'),
                        '/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
    else:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    if process.poll() is None:process.kill()
    process.wait(timeout=10)


def run_transport(nest,session_id,command,*,timeout=30,max_bytes=262144,allow_lookup=False):
    """One explicit bounded question dispatch to an operator-supplied JSON runner.

    This is a trusted host transport, not a sandbox for arbitrary model code.
    The runner receives only the pending request and returns an exact reply envelope.
    """
    if not isinstance(command,list) or not command or any(not isinstance(x,str) for x in command):raise ValueError('Runner must be an argument list')
    if not 1<=timeout<=300 or not 1024<=max_bytes<=1048576:raise ValueError('Invalid transport limits')
    with database(nest) as db:
        db.execute('BEGIN IMMEDIATE');row=_row(db,session_id);handoff,_=_checked(row)
        if row['state']!='AWAITING_MIND' or row['attempts']>=row['max_attempts']:raise ValueError('Session unavailable or retries exhausted')
        now=time.time()
        if now>=row['deadline']:raise ValueError('Session deadline expired')
        active=db.execute('SELECT count(*) FROM sessions WHERE lease>?',(now,)).fetchone()[0]
        if active>=2:raise ValueError('NEST worker concurrency budget exhausted')
        if row['lease'] is not None:
            raise ValueError('Prior transport lease requires explicit recovery')
        deadline=min(now+timeout,row['deadline'])
        db.execute('UPDATE sessions SET attempts=attempts+1,lease=? WHERE id=?',(deadline,session_id))
    status='TRANSPORT_FAILED'
    try:
        with tempfile.TemporaryDirectory(prefix='mantle-worker-',dir=Path(nest).resolve()) as td:
            td=Path(td);(td/'request.json').write_text(compiled.canonical({'request':handoff['request'],'request_sha256':handoff['request_sha256']}),encoding='utf-8')
            with (td/'request.json').open('rb') as stdin,(td/'reply.json').open('wb') as stdout,(td/'errors.txt').open('wb') as stderr:
                process=subprocess.Popen(command,stdin=stdin,stdout=stdout,stderr=stderr,
                    creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0,
                    start_new_session=os.name!='nt',cwd=td)
                try:
                    while process.poll() is None:
                        current=inspect(nest,session_id)
                        if current['state']=='CANCELLED':status='CANCELLED';raise ValueError('Session cancelled')
                        if time.time()>=deadline:status='TIMED_OUT';raise TimeoutError('Worker timed out')
                        if (td/'reply.json').stat().st_size>max_bytes or (td/'errors.txt').stat().st_size>65536:
                            raise ValueError('Worker output budget exceeded')
                        time.sleep(0.05)
                    if process.returncode:raise ValueError('Worker failed with exit code '+str(process.returncode))
                finally:_stop(process)
            raw=(td/'reply.json').read_bytes()
            if (td/'errors.txt').stat().st_size>65536:raise ValueError('Worker error-output budget exceeded')
            if len(raw)>max_bytes:raise ValueError('Worker output budget exceeded')
            reply=compiled.json_contract.loads(raw.decode('utf-8'))
            result=advance(nest,session_id,reply,allow_lookup=allow_lookup);status='RETURNED';return result
    finally:
        with database(nest) as db:
            db.execute('UPDATE sessions SET lease=NULL WHERE id=?',(session_id,))
            # Failures preserve the pending request; only an explicit invocation retries.
            db.execute('CREATE TABLE IF NOT EXISTS dispatch_events (session_id TEXT, status TEXT, at REAL)')
            db.execute('INSERT INTO dispatch_events VALUES (?,?,?)',(session_id,status,time.time()))


def recover(nest,session_id):
    with database(nest) as db:
        db.execute('BEGIN IMMEDIATE');row=_row(db,session_id)
        if row['lease'] is not None and row['lease']>time.time():raise ValueError('Worker lease is still active')
        db.execute('UPDATE sessions SET lease=NULL WHERE id=?',(session_id,))
        return {'result':'RECOVERED','state':row['state'],'automatic_retry':False}
