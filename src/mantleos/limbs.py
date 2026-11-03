"""Optional Journal-backed limb composition; no fixed limb count or model client.

The owner registers existing, verified Engrams and trusted handlers. Intentions
are data. Neither handler availability nor a result supplies Body/Baker authority.
"""
from contextlib import contextmanager
import json
import hashlib
import inspect
import os
from pathlib import Path
import sqlite3
import time
import uuid

from . import journal, json_contract as c

SCHEMA='mantle.limb-composition/1'


def recipe_composition(recipe):
    value=recipe.get('limb_composition')
    if value is None:return {'enabled':False,'members':[],'workers':0}
    if recipe.get('schema')!='kpp.recipe/4' or 'engram-limbs' not in recipe.get('ingredients',[]):
        raise ValueError('Limb composition requires recipe/4 and the optional engram-limbs ingredient')
    c.shape(value,{'schema','members','workers'})
    if value['schema']!=SCHEMA:raise ValueError('Unsupported limb composition')
    members=value['members'];workers=value['workers']
    if type(members) is not list or len(members)>32 or type(workers) is not int or not 0<=workers<=8 or bool(members)!=bool(workers):
        raise ValueError('Invalid limb count or worker budget')
    ids=set();obligations={a['id'] for a in recipe['anchors']}
    for member in members:
        c.shape(member,{'id','interfaces','obligations'})
        c.identifier(member['id'])
        if member['id'] in ids:raise ValueError('Duplicate limb role')
        ids.add(member['id'])
        if type(member['interfaces']) is not list or any(type(i) is not str or not i for i in member['interfaces']):raise ValueError('Invalid limb interfaces')
        if type(member['obligations']) is not list or not member['obligations'] or any(i not in obligations for i in member['obligations']):raise ValueError('Limb needs existing obligation references')
    return {'enabled':bool(members),'members':members,'workers':workers}


def handler_pin(handler):
    source=inspect.getsourcefile(handler)
    if not source or not Path(source).is_file():raise ValueError('Handlers need reviewable source files')
    return c.digest({'module':handler.__module__,'name':handler.__qualname__,
                     'source':hashlib.sha256(Path(source).read_bytes()).hexdigest()})


def binding(engram):
    status=engram.status()
    return c.digest({'identity':status['identity'],'primer':status['primer_sha256'],
                     'snapshot':engram._meta('snapshot'),'register':c.digest(engram.register),
                     'design':engram.design_digest})


@contextmanager
def worker_lease(root,limb):
    path=Path(root)/('worker-'+limb+'.lock')
    stream=path.open('a+b')
    try:
        if not path.stat().st_size:stream.write(b'0');stream.flush()
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream,fcntl.LOCK_UN)
    finally:stream.close()



class LimbSet:
    def __init__(self,root):
        self.root=Path(root).resolve()
        if not (self.root/'limbs.sqlite').is_file():raise ValueError('Limb composition is not initialized')

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.root/'limbs.sqlite',timeout=10)
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:yield db
        finally:db.close()

    @classmethod
    def create(cls,root,members,*,worker_limit=1,approved=False,handlers=None):
        if approved is not True:raise PermissionError('Owner approval required to register Engrams')
        if type(members) is not list or len(members)>32:raise ValueError('Composition supports 0..32 declared limbs')
        if type(worker_limit) is not int or not 0<=worker_limit<=8 or (bool(members) != bool(worker_limit)):
            raise ValueError('Use zero workers for no limbs, otherwise 1..8 workers')
        handlers=handlers or {}
        pins={name:handler_pin(fn) for name,fn in handlers.items()}
        validated=[];ids=set();identities=set();paths=set()
        for member in members:
            c.shape(member,{'id','journal','grants'})
            c.identifier(member['id'])
            if member['id'] in ids:raise ValueError('Duplicate limb ID')
            if type(member['grants']) is not list or any(type(g) is not str or not g for g in member['grants']):raise ValueError('Explicit handler grants required')
            original=Path(member['journal'])
            if original.is_symlink() or getattr(original,'is_junction',lambda:False)():raise ValueError('Linked Journal path')
            path=original.resolve()
            if path in paths or path.is_symlink():raise ValueError('Each limb needs its own Journal')
            with journal.Journal(path) as engram:
                identity=engram.status()['identity'];fingerprint=binding(engram)
            if identity in identities:raise ValueError('Each limb needs a distinct identity')
            ids.add(member['id']);identities.add(identity);paths.add(path)
            if set(member['grants'])-pins.keys():raise ValueError('Every grant needs an owner-pinned handler')
            validated.append((member['id'],str(path),identity,c.canonical(sorted(set(member['grants']))),fingerprint))
        root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
        db=sqlite3.connect(root/'limbs.sqlite')
        try:
            db.executescript('''PRAGMA synchronous=FULL;
            CREATE TABLE members(id TEXT PRIMARY KEY,path TEXT UNIQUE,identity TEXT UNIQUE,grants TEXT,binding TEXT,enabled INTEGER);
            CREATE TABLE tasks(id TEXT PRIMARY KEY,limb TEXT,operation TEXT,input TEXT,phase TEXT,token TEXT,result TEXT);
            CREATE TABLE config(workers INTEGER,pins TEXT,revision INTEGER);
            CREATE TABLE admissions(task TEXT PRIMARY KEY,binding TEXT NOT NULL);
            ''')
            db.execute('INSERT INTO config VALUES (?,?,1)',(worker_limit,c.canonical(pins)))
            db.executemany('INSERT INTO members VALUES (?,?,?,?,?,1)',validated);db.commit()
        finally:db.close()
        return cls(root)

    def upgrade(self,*,reviewed=False):
        """Explicit idle-registry upgrade; historical task/Journal records are retained."""
        if reviewed is not True:raise PermissionError('Owner registry upgrade review required')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM tasks WHERE phase IN ('READY','RUNNING','NEEDS_REVIEW')").fetchone():raise ValueError('Reconcile outstanding work before registry upgrade')
            db.execute('CREATE TABLE IF NOT EXISTS admissions(task TEXT PRIMARY KEY,binding TEXT NOT NULL)')
        return self.status()

    @staticmethod
    def _admission(db,limb,operation):
        member=db.execute('SELECT identity,binding,grants,enabled FROM members WHERE id=?',(limb,)).fetchone()
        pins,revision=db.execute('SELECT pins,revision FROM config').fetchone()
        if not member or not member[3] or operation not in json.loads(member[2]):raise PermissionError('Limb operation is not granted')
        return {'identity':member[0],'source':member[1],'grants':json.loads(member[2]),'revision':revision,'handler':json.loads(pins).get(operation)}

    def submit(self,limb,operation,value,*,request_id):
        c.identifier(request_id);raw=c.canonical(value,limit=16384)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            member=db.execute('SELECT grants,enabled FROM members WHERE id=?',(limb,)).fetchone()
            if not member or not member[1] or operation not in json.loads(member[0]):raise PermissionError('Limb operation is not granted')
            old=db.execute('SELECT limb,operation,input FROM tasks WHERE id=?',(request_id,)).fetchone()
            if old and old!=(limb,operation,raw):raise ValueError('Changed intention replay')
            if not old:
                if db.execute("SELECT count(*) FROM tasks WHERE phase IN ('READY','RUNNING')").fetchone()[0]>=128:raise ValueError('Limb queue is full')
                db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?,?)',(request_id,limb,operation,raw,'READY',None,None))
                db.execute('INSERT INTO admissions VALUES (?,?)',(request_id,c.canonical({**self._admission(db,limb,operation),'request_sha256':c.digest({'limb':limb,'operation':operation,'input':value})})))
        return {'request_id':request_id,'replay':bool(old)}

    def status(self):
        with self.db() as db:
            return {'schema':SCHEMA,'worker_limit':db.execute('SELECT workers FROM config').fetchone()[0],
                'members':[{'id':i,'identity':identity,'enabled':bool(e)} for i,identity,e in db.execute('SELECT id,identity,enabled FROM members ORDER BY id')],
                'tasks':[{'id':i,'limb':limb,'phase':phase} for i,limb,phase in db.execute('SELECT id,limb,phase FROM tasks ORDER BY rowid DESC LIMIT 128')],
                'authority':'NONE_FROM_INTENTION_OR_RESULT'}

    def results(self,*,broker,limit=32,opener=None):
        if type(limit) is not int or not 1<=limit<=32:raise ValueError('Result bound must be 1..32')
        with self.db() as db:
            rows=db.execute("SELECT t.id,t.limb,t.token,t.result,m.path,m.binding,t.operation,t.input FROM tasks t JOIN members m ON m.id=t.limb WHERE t.phase='RESULT' AND t.rowid IN (SELECT max(rowid) FROM tasks WHERE phase='RESULT' GROUP BY limb) ORDER BY t.rowid DESC LIMIT 32").fetchall()
        result=[];seen=set()
        for task,limb,token,raw,path,expected,operation,payload in rows:
            if limb in seen:continue
            seen.add(limb)
            if not broker(limb,'result.read'):raise PermissionError('Limb result read denied')
            receipt=c.loads(raw)
            with (opener(path) if opener else journal.Journal(path)) as engram:
                if binding(engram)!=expected:raise ValueError('Limb source changed')
                intended=next((r for r in engram.records if r['type']=='limb-intention' and r['body'].get('task_id')==task and r['body'].get('token')==token),None)
                if not intended or intended['body'].get('operation')!=operation or intended['body'].get('input_sha256')!=c.digest(c.loads(payload)):raise ValueError('Task binding changed')
                record=next((r for r in engram.records if r['sha256']==receipt['record_sha256']),None)
                if not record or record['type']!='limb-result' or record['body'].get('task_id')!=task or record['body'].get('token')!=token or record['body'].get('result')!=receipt['value']:
                    raise ValueError('Forged or stale limb result')
                result.append({'limb':limb,'request_id':task,'record_sha256':record['sha256'],'head':engram.head(),'value':receipt['value']})
            if len(result)>=limit:break
        return result

    def enable(self,limb,enabled,*,approved=False):
        if approved is not True or type(enabled) is not bool:raise PermissionError('Owner-selected boolean required')
        with self.db() as db:
            if not db.execute('SELECT 1 FROM members WHERE id=?',(limb,)).fetchone():raise ValueError('Unknown limb')
            db.execute('UPDATE members SET enabled=? WHERE id=?',(int(enabled),limb))
            db.execute('UPDATE config SET revision=revision+1')

    def run_one(self,handlers,*,broker,opener=None):
        """Execute one trusted host callback; caller supplies execution isolation.

        Global claim serialization does not serialize independent computation.
        Shared Body effects must still use the host's separate checked broker.
        """
        if not callable(broker):raise PermissionError('Independent host broker required')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            limit=db.execute('SELECT workers FROM config').fetchone()[0]
            if db.execute("SELECT count(*) FROM tasks WHERE phase='RUNNING'").fetchone()[0]>=limit:return {'status':'BUSY'}
            row=db.execute("SELECT t.id,t.limb,t.operation,t.input,m.path,m.identity,m.binding FROM tasks t JOIN members m ON m.id=t.limb WHERE t.phase='READY' AND m.enabled=1 AND NOT EXISTS (SELECT 1 FROM tasks r WHERE r.limb=t.limb AND r.phase='RUNNING') ORDER BY t.rowid LIMIT 1").fetchone()
            if not row:return {'status':'IDLE'}
            task,limb,op,raw,path,identity,expected_binding=row
            admission=db.execute('SELECT binding FROM admissions WHERE task=?',(task,)).fetchone()
            expected_admission={**self._admission(db,limb,op),'request_sha256':c.digest({'limb':limb,'operation':op,'input':c.loads(raw)})}
            if not admission or c.loads(admission[0])!=expected_admission:raise PermissionError('Queued intention configuration or content changed')
            pins,epoch=db.execute("SELECT pins,revision FROM config").fetchone()
            if op not in handlers or json.loads(pins).get(op)!=handler_pin(handlers[op]):raise PermissionError("Handler source changed or absent")
            if op not in handlers or not callable(handlers[op]) or not broker(limb,op):raise PermissionError('Host did not authorize this handler')
            token=uuid.uuid4().hex
            db.execute("UPDATE tasks SET phase='RUNNING',token=? WHERE id=?",(token,task))
        try:
            with worker_lease(self.root,limb), (opener(path) if opener else journal.Journal(path)) as engram:
                with self.db() as db:
                    claim=db.execute('SELECT phase,token FROM tasks WHERE id=?',(task,)).fetchone()
                    if claim!=('RUNNING',token):raise PermissionError('Stale task claim')
                if binding(engram)!=expected_binding:raise ValueError('Limb founding/source/register changed')
                if engram.status()['identity']!=identity:raise ValueError('Limb identity changed')
                engram.append_record('limb-intention','limb-runtime',{'task_id':task,'token':token,'operation':op,'input_sha256':c.digest(json.loads(raw)),'binding_sha256':expected_binding,'policy_revision':epoch,'handler_sha256':json.loads(pins)[op]},expected_head=engram.head())
                result=handlers[op](json.loads(raw));c.canonical(result,limit=16384)
                with self.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    live=db.execute('SELECT enabled FROM members WHERE id=?',(limb,)).fetchone()[0]
                    current={**self._admission(db,limb,op),'request_sha256':c.digest({'limb':limb,'operation':op,'input':c.loads(raw)})}
                    claim=db.execute('SELECT phase,token,input FROM tasks WHERE id=?',(task,)).fetchone()
                    if claim!=('RUNNING',token,raw) or not live or not broker(limb,op) or c.loads(admission[0])!=current or handler_pin(handlers[op])!=json.loads(pins)[op] or binding(engram)!=expected_binding:raise PermissionError('Limb claim, authorization or source changed')
                    record=engram.append_record('limb-result','limb-runtime',{'task_id':task,'token':token,'result':result},expected_head=engram.head())
                    db.execute("UPDATE tasks SET phase='RESULT',result=? WHERE id=? AND token=? AND phase='RUNNING'",(c.canonical({'value':result,'record_sha256':record['sha256']}),task,token))
            return {'status':'RESULT','request_id':task,'limb':limb,'result':result,'record_sha256':record['sha256']}
        except BaseException:
            with self.db() as db:db.execute("UPDATE tasks SET phase='NEEDS_REVIEW' WHERE id=? AND token=?",(task,token))
            raise

    def recover(self,*,reviewed=False):
        if reviewed is not True:raise PermissionError('Explicit stopped-worker recovery review required')
        # Never rerun an uncertain callback. Retain all task and Journal history.
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute("SELECT t.id,t.token,m.path,t.limb,m.binding,t.operation,t.input FROM tasks t JOIN members m ON m.id=t.limb WHERE t.phase IN ('RUNNING','NEEDS_REVIEW')").fetchall()
            for task,token,path,limb,expected,operation,payload in rows:
                with worker_lease(self.root,limb), journal.Journal(path) as engram:
                    if binding(engram)!=expected:raise ValueError('Recovery limb binding changed')
                    result=next((r for r in reversed(engram.records) if r['type']=='limb-result' and r['body'].get('task_id')==task and r['body'].get('token')==token),None)
                    intended=next((r for r in engram.records if r['type']=='limb-intention' and r['body'].get('task_id')==task and r['body'].get('token')==token),None)
                    if result and (not intended or intended['body'].get('operation')!=operation or intended['body'].get('input_sha256')!=c.digest(c.loads(payload))):raise ValueError('Recovery task/input binding changed')
                if result:
                    db.execute("UPDATE tasks SET phase='RESULT',result=? WHERE id=?",(c.canonical({'value':result['body']['result'],'record_sha256':result['sha256']}),task))
                else:db.execute("UPDATE tasks SET phase='NEEDS_REVIEW' WHERE id=?",(task,))
        return self.status()


def remember(value):
    """Trusted local specimen: retain supplied semantic data in this limb's result."""
    c.canonical(value,limit=8192)
    return {'remembered':value}


def digest_input(value):return {'sha256':c.digest(value)}


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(prog='mantleos limbs')
    commands=parser.add_subparsers(dest='op',required=True)
    for op in ('init','status','submit','run','disable','enable','recover','birth','upgrade'):
        p=commands.add_parser(op)
        if op!='birth':p.add_argument('--root',type=Path,required=True)
        if op in ('init','disable','enable','recover','upgrade'):p.add_argument('--reviewed',action='store_true')
        if op=='init':
            p.add_argument('--members',type=Path,required=True);p.add_argument('--workers',type=int,default=1)
        if op=='submit':
            p.add_argument('--limb',required=True);p.add_argument('--operation',choices=('remember','digest'),required=True)
            p.add_argument('--input',type=Path,required=True);p.add_argument('--request-id',required=True)
        if op in ('disable','enable'):p.add_argument('--limb',required=True)
        if op=='run':p.add_argument('--reviewed',action='store_true')
        if op=='birth':
            p.add_argument('--out',type=Path,required=True);p.add_argument('--founding',type=Path);p.add_argument('--name',default='Raven')
    args=parser.parse_args(argv);handlers={'remember':remember,'digest':digest_input}
    if args.op=='birth':result=journal.create(args.out,founding=args.founding,name=args.name)
    elif args.op=='init':result=LimbSet.create(args.root,c.loads(args.members.read_text('utf8')),worker_limit=args.workers,approved=args.reviewed,handlers=handlers).status()
    else:
        runtime=LimbSet(args.root)
        if args.op=='status':result=runtime.status()
        elif args.op=='submit':result=runtime.submit(args.limb,args.operation,c.loads(args.input.read_text('utf8')),request_id=args.request_id)
        elif args.op=='run':
            if not args.reviewed:raise PermissionError('Explicit host execution review required')
            result=runtime.run_one(handlers,broker=lambda limb,op:op in handlers)
        elif args.op=='recover':result=runtime.recover(reviewed=args.reviewed)
        elif args.op=='upgrade':result=runtime.upgrade(reviewed=args.reviewed)
        else:
            runtime.enable(args.limb,args.op=='enable',approved=args.reviewed);result=runtime.status()
    print(json.dumps(result,ensure_ascii=True,indent=2));return 0
