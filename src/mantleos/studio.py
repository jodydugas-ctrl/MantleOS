"""Node-RED resident Studio: deterministic Heart and opt-in Journal MIND routes.

No provider calls, installation or background service occurs at import.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
import uuid
from contextlib import contextmanager, nullcontext, ExitStack, closing

from . import journal, primer, specimens, lifecycle, birth, studio_project, json_contract as c
from .transactions import body_lock, atomic_bytes

_sessions={}

def _session(path):
    key=str(Path(path).resolve())
    if key not in _sessions:_sessions[key]=journal.Journal(path)
    return _sessions[key]


ROLES = ('body-mapping','design','contracts','construction','verification','repair','memory','communications')
ADDENDUM = ('Anchor Studio is a fresh Node-RED resident AppAI. Its embodiment is this approved Node-RED NEST, '
            'not a humanoid. The Compiler identity, history and grants are not inherited. '
            'Canonical Anchor singularities are immutable. Graphs and model proposals grant no authority. '
            'Prime Mind publishes intentions; independent Engram limbs act within their grants. '
            'Preserve Node-RED operations, checked effects, provenance, and separate Baker acceptance. '
            'For delegated work you may put a JSON object in the committed reply with schema studio.intent-proposal/1, '
            'text, and intentions (at most eight objects with role and value). This is a proposal; '
            'the operator must explicitly publish it. Ordinary conversation remains plain text.')


def controller_pin():
    root=Path(__file__).parent
    return c.digest({name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('studio.py','studio_handlers.py','studio_project.py','studio_workflows.py','studio_auto_mind.py','studio_mind_config.py','studio_mind_budget.py','studio_mind_provider.py','studio_demo.py','limbs.py','journal.py','anchors.py','anchor_design.py','anchor_language.py','effects.py','json_contract.py','transactions.py','primer.py','cartridge.py','kpp/resources/examples/anchor-studio/launcher.cjs','kpp/resources/examples/anchor-studio/json-worker.cjs','kpp/resources/examples/anchor-studio/committed-events.cjs','kpp/resources/examples/anchor-studio/local-access.cjs','kpp/resources/examples/anchor-studio/workspace.html','kpp/resources/examples/anchor-studio/workspace.css','kpp/resources/examples/anchor-studio/workspace.js','kpp/resources/examples/anchor-studio/conditions.cjs','kpp/resources/examples/anchor-studio/palette/nodes.js','kpp/resources/examples/anchor-studio/palette/nodes.html')})


def rebind_source(nest,*,reviewed=False):
    from .limbs import worker_lease
    if reviewed is not True:raise PermissionError('Owner source review required')
    with worker_lease(nest,'controller'), ExitStack() as stopped, closing(sqlite3.connect(Path(nest)/'studio.sqlite')) as db, db:
        if (Path(nest)/'limb-runtime/limbs.sqlite').exists():
            for member in limb_set(nest).status()['members']:stopped.enter_context(worker_lease(Path(nest)/'limb-runtime',member['id']))
        db.execute('BEGIN IMMEDIATE')
        db.execute("UPDATE settings SET value=? WHERE key='phase'",(json.dumps('STASIS'),))
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('controller_pin',json.dumps(controller_pin())))
        db.execute("UPDATE mind SET phase='NEEDS_REVIEW' WHERE phase='AWAITING_MIND'")
        db.execute('INSERT INTO events(id,kind,value,at) VALUES (?,?,?,?)',('source-'+uuid.uuid4().hex,'controller.source.reviewed',c.canonical({'sha256':controller_pin()}),time.time()))
    return {'status':'STASIS','controller_pin':controller_pin()}


@contextmanager
def database(nest):
    db=sqlite3.connect(Path(nest)/'studio.sqlite',timeout=10)
    db.execute('PRAGMA synchronous=FULL')
    try:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='settings'").fetchone():
            row=db.execute("SELECT value FROM settings WHERE key='controller_pin'").fetchone()
            if not row or json.loads(row[0])!=controller_pin():raise ValueError('Controller source changed; stop and explicitly review/rebind source')
            founder=db.execute("SELECT value FROM settings WHERE key='founding_sha256'").fetchone()
            if founder and json.loads(founder[0])!=hashlib.sha256((Path(nest)/'founding.txt').read_bytes()).hexdigest():raise ValueError('Private founding source changed')
        with db:yield db
    finally:db.close()


def initialize_heart(nest,raw):
    nest=Path(nest)
    if nest.exists():raise ValueError('Studio NEST must be new')
    raw.decode('utf-8-sig')
    nest.mkdir(parents=True)
    atomic_bytes(nest/'founding.txt',raw,replace=False)
    atomic_bytes(nest/'STUDIO-ROLE.txt',ADDENDUM.encode(),replace=False)
    with database(nest) as db:
        db.executescript('''CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE events(seq INTEGER PRIMARY KEY,id TEXT UNIQUE,kind TEXT,value TEXT,at REAL);
        CREATE TABLE limbs(role TEXT PRIMARY KEY,identity TEXT,path TEXT);
        CREATE TABLE intentions(id TEXT PRIMARY KEY,role TEXT,value TEXT,phase TEXT,result TEXT);
        CREATE TABLE mind(id TEXT PRIMARY KEY,user TEXT,phase TEXT,frame TEXT,reply TEXT);
        ''')
        for key,value in {'phase':'STASIS','identity':'studio-'+uuid.uuid4().hex,'founding_sha256':hashlib.sha256(raw).hexdigest(),'controller_pin':controller_pin(),'next_beat':time.time()+600}.items():
            db.execute('INSERT INTO settings VALUES (?,?)',(key,json.dumps(value)))
        db.execute('INSERT INTO events(id,kind,value,at) VALUES (?,?,?,?)',('heart-first','heart.established','{}',time.time()))


def initialize(nest,founding):
    nest=Path(nest);raw=Path(founding).read_bytes()
    initialize_heart(nest,raw)
    # Founding source is retained exactly; role/embodiment is separate context.
    for role in ('prime',)+ROLES:
        body=nest/('birth-'+role)
        text=raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n').strip()+'\n'
        founder=birth.make_birth(bio_id='studio-founder',name='Anchor Studio',description='Cuttlefish founding source',persona_name='Frame-Preserving Cuttlefish',persona=text)
        material=(founder,{'PERSONA.md':text.encode(),'COMMANDMENTS.md':(founder['primer']['commandments'].strip()+'\n').encode()}, {'source_sha256':hashlib.sha256(raw).hexdigest(),'transformation':'universal-newline text view; original retained in NEST'})
        specimens.fresh(body,name='Anchor Studio '+role,expression='appai' if role=='prime' else 'engram',founding=material)
        path=nest/(role+'.engram');journal.from_body(body,path)
        with journal.Journal(path) as engram:
            identity=engram.status()['identity']
        if role!='prime':
            with database(nest) as db:db.execute('INSERT INTO limbs VALUES (?,?,?)',(role,identity,str(path.resolve())))
    migrate_limbs(nest,approved=True)
    return status(nest)


def _setting(db,key):return json.loads(db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()[0])


def status(nest):
    with database(nest) as db:
        prime=_sessions.get(str((Path(nest)/'prime.engram').resolve()))
        persona=prime.status() if prime else None
        return {'phase':_setting(db,'phase'),'identity':_setting(db,'identity'),
                'persona':({'name':persona['persona'],'identity':persona['identity'],
                            'primer_sha256':persona['primer_sha256']} if persona else None),
                'heartbeats':db.execute("SELECT count(*) FROM events WHERE kind LIKE 'heart.%'").fetchone()[0],
                'limbs':[{'role':r,'identity':i} for r,i in db.execute('SELECT role,identity FROM limbs ORDER BY role')],
                'pending_mind':db.execute("SELECT count(*) FROM mind WHERE phase='AWAITING_MIND'").fetchone()[0],
                'intentions':[{'id':i,'role':r,'phase':p} for i,r,p in db.execute('SELECT id,role,phase FROM intentions ORDER BY rowid')],
                'limb_runtime':limb_set(nest).status() if (Path(nest)/'limb-runtime/limbs.sqlite').exists() else {'status':'MIGRATION_REQUIRED'},
                'mind_route':'OPENROUTER_OWNER_CONFIGURED' if (Path(nest)/'mind-route.json').exists() else 'SUPERVISED_HOST_ONLY'}


def event(nest,kind,value,request_id):
    c.canonical(value,limit=16384)
    with body_lock(Path(nest)),database(nest) as db:
        previous=db.execute('SELECT kind,value FROM events WHERE id=?',(request_id,)).fetchone()
        encoded=c.canonical(value)
        if previous:
            if previous!=(kind,encoded):raise ValueError('Duplicate event has different content')
            return {'status':'REPLAY'}
        if _setting(db,'phase')!='ACTIVE' and kind!='host.started':return {'status':'STASIS'}
        if kind=='pain' and db.execute("SELECT 1 FROM events WHERE kind='pain' AND at>?",(time.time()-5,)).fetchone():
            return {'status':'COALESCED'}
        db.execute('INSERT INTO events(id,kind,value,at) VALUES (?,?,?,?)',(request_id,kind,encoded,time.time()))
        if kind in ('conversation','pain','scheduled','host.started'):
            db.execute('INSERT INTO events(id,kind,value,at) VALUES (?,?,?,?)',('beat-'+request_id,'heart.'+kind,encoded,time.time()))
        return {'status':'RECORDED','request_id':request_id}


def phase(nest,active):
    if type(active) is not bool:raise ValueError('Explicit boolean phase required')
    with body_lock(Path(nest)),database(nest) as db:
        db.execute("UPDATE settings SET value=? WHERE key='phase'",(json.dumps('ACTIVE' if active else 'STASIS'),))
    return status(nest)


def limb_set(nest):
    from .limbs import LimbSet
    return LimbSet(Path(nest)/'limb-runtime')


def boot(nest):
    """Verify/pin resident sessions once before activation; no model or handlers."""
    from .limbs import binding
    started=time.perf_counter()
    with database(nest):pass
    prime=_session(Path(nest)/'prime.engram');prime.status()
    runtime=limb_set(nest)
    with runtime.db() as db:members=db.execute('SELECT path,identity,binding FROM members').fetchall()
    for path,identity,expected in members:
        engram=_session(path)
        if engram.status()['identity']!=identity or binding(engram)!=expected:raise ValueError('Resident limb identity/source changed')
    return {'status':'VERIFIED','sessions':1+len(members),'startup_verification_ms':(time.perf_counter()-started)*1000,'model_calls':0}


def migrate_limbs(nest,*,approved=False):
    from .limbs import LimbSet
    from .studio_handlers import handle
    if approved is not True:raise PermissionError('Owner migration approval required')
    with body_lock(Path(nest)),database(nest) as db:
        if _setting(db,'phase')!='STASIS':raise ValueError('Quiesce Studio before limb migration')
        if db.execute("SELECT 1 FROM intentions WHERE phase!='RESULT'").fetchone():raise ValueError('Reconcile incomplete legacy intentions first')
        members=[{'id':role,'journal':path,'grants':['studio.limb']} for role,path in db.execute('SELECT role,path FROM limbs ORDER BY role')]
        result=LimbSet.create(Path(nest)/'limb-runtime',members,worker_limit=2,approved=True,handlers={'studio.limb':handle})
        db.execute('INSERT INTO events(id,kind,value,at) VALUES (?,?,?,?)',('shared-limb-migration','limbs.migrated',c.canonical({'members':[m['id'] for m in members],'legacy_history':'retained'}),time.time()))
    return result.status()


def intention(nest,role,value,request_id):
    if role not in ROLES:raise ValueError('Unknown limb')
    with database(nest) as db:
        old=db.execute('SELECT role,value FROM intentions WHERE id=?',(request_id,)).fetchone()
        if old:
            if old!=(role,c.canonical(value)):raise ValueError('Changed legacy intention replay')
            return {'id':request_id,'status':'REPLAY','provenance':'legacy-studio-queue'}
    return limb_set(nest).submit(role,'studio.limb',{'role':role,'input':value,'nest':str(Path(nest).resolve())},request_id=request_id)


def work(nest,role=None):
    from .studio_handlers import handle
    if status(nest)['phase']!='ACTIVE':return {'status':'STASIS'}
    return limb_set(nest).run_one({'studio.limb':handle},broker=lambda limb,operation:status(nest)['phase']=='ACTIVE',opener=lambda path:nullcontext(_session(path)))


def conversation(nest,user,request_id,model_label):
    c.identifier(request_id)
    if type(user) is not str or not user.strip() or len(user.encode())>16384 or type(model_label) is not str or not model_label:raise ValueError('Invalid conversation input/model label')
    with body_lock(Path(nest)),database(nest) as db:
        old=db.execute('SELECT user,phase,frame,reply FROM mind WHERE id=?',(request_id,)).fetchone()
        if old:
            if old[0]!=user:raise ValueError('Changed conversation replay')
            if old[1]=='COMMITTED':return committed_result(nest,request_id)
            if old[1]!='AWAITING_MIND':raise ValueError('Conversation requires review')
            if _setting(db,'phase')!='ACTIVE':return {'status':'STASIS'}
            return json.loads(old[2])
        if _setting(db,'phase')!='ACTIVE':raise ValueError('Studio is in stasis')
        if db.execute("SELECT 1 FROM mind WHERE phase='AWAITING_MIND'").fetchone():raise ValueError('One MIND request is already pending')
        with nullcontext(_session(Path(nest)/'prime.engram')) as mind:
            frame=mind.open(user,request_id=request_id,model_id=model_label)
        observations=[];omitted=0
        available=max(0,16384-len(c.canonical(frame['payload']['memory']).encode('utf8'))-256)
        runtime=limb_set(nest)
        latest={r['limb']:r for r in runtime.results(broker=lambda limb,op:True,limit=32,opener=lambda path:nullcontext(_session(path)))}
        with runtime.db() as coordination:
            members=coordination.execute('SELECT id,path,identity,binding FROM members ORDER BY id').fetchall()
            counts={(role,phase):count for role,phase,count in coordination.execute('SELECT limb,phase,count(*) FROM tasks GROUP BY limb,phase')}
            pending={role:coordination.execute("SELECT id,phase,input FROM tasks WHERE limb=? AND phase IN ('READY','RUNNING','NEEDS_REVIEW') ORDER BY rowid LIMIT 2",(role,)).fetchall() for role,_,_,_ in members}
        for role,path,identity,source in members:
            observation=latest.get(role)
            text=c.canonical(observation['value']) if observation else ''
            projection={'role':role,'identity':identity,'source_sha256':source,'head':_session(path).status()['head'],
                'pending':{p:counts.get((role,p),0) for p in ('READY','RUNNING','NEEDS_REVIEW')},
                'record_sha256':observation['record_sha256'] if observation else None,'excerpt':text[:1024],'truncated':len(text)>1024,
                'earlier_results_omitted':max(0,counts.get((role,'RESULT'),0)-int(observation is not None))}
            projection['pending_requests']=[{'id':rid,'phase':p,'input_sha256':c.digest(c.loads(raw)),
                'excerpt':c.canonical(c.loads(raw).get('input',{}))[:256]} for rid,p,raw in pending[role]]
            projection['pending_requests_omitted']=max(0,sum(projection['pending'].values())-len(pending[role]))
            size=len(c.canonical(projection).encode('utf8'))
            if size<=available:observations.append(projection);available-=size
            else:omitted+=1
        wrapper={'frame':frame,'studio_addendum':ADDENDUM,'controller_pin':controller_pin(),'limb_observations':observations,'limb_observations_omitted':omitted,'prepared_at':time.time(),'model_label':model_label,'status':'AWAITING_MIND'}
        if (Path(nest)/'mind-route.json').exists():
            from .studio_auto_mind import _load
            route,_=_load(nest)
            wrapper['mind_route_revision']=route['revision']
        db.execute('INSERT INTO mind VALUES (?,?,?,?,?)',(request_id,user,'AWAITING_MIND',c.canonical(wrapper),None))
    event(nest,'conversation',{'request_id':request_id},'conversation-'+request_id)
    return wrapper


def submit(nest,request_id,proposal):
    with body_lock(Path(nest)),database(nest) as db:
        item=db.execute('SELECT phase,reply,frame FROM mind WHERE id=?',(request_id,)).fetchone()
        if not item:raise ValueError('Unknown conversation')
        if item[0]=='NEEDS_REVIEW':raise ValueError('Conversation requires recovery review')
        if item[0]=='AWAITING_MIND' and json.loads(item[2]).get('controller_pin')!=controller_pin():raise ValueError('Stale Studio preparation')
        if _setting(db,'phase')!='ACTIVE':raise ValueError('Studio is in stasis')
        prior_wrapper=json.loads(item[2])
        if item[0]=='AWAITING_MIND' and 'mind_route_revision' in prior_wrapper:
            from .studio_auto_mind import validate_result
            validate_result(nest,request_id,prior_wrapper,proposal)
        with nullcontext(_session(Path(nest)/'prime.engram')) as mind:
            result=mind.submit(request_id,proposal,broker=lambda authority,name: (authority=='release' and name=='publication.release') or (authority=='read' and name in ('body.status','engram.query')))
        reply=result.get('reply')
        if reply is None:
            wrapper={'frame':result,'studio_addendum':ADDENDUM,'controller_pin':controller_pin(),'status':'AWAITING_MIND'}
            if 'mind_route_revision' in prior_wrapper:
                wrapper['mind_route_revision']=prior_wrapper['mind_route_revision']
            db.execute('UPDATE mind SET frame=? WHERE id=?',(c.canonical(wrapper),request_id))
            return wrapper
        db.execute("UPDATE mind SET phase='COMMITTED',reply=? WHERE id=?",(reply,request_id))
        return {'status':'COMMITTED','reply':reply,'receipt':result}


def pulse(nest):
    due=False
    with body_lock(Path(nest)),database(nest) as db:
        if _setting(db,'phase')=='ACTIVE' and time.time()>=_setting(db,'next_beat'):
            db.execute("UPDATE settings SET value=? WHERE key='next_beat'",(json.dumps(time.time()+600),))
            due=True
    if due:event(nest,'scheduled',{},'scheduled-'+uuid.uuid4().hex)
    return {'scheduled':due}


def dispatch(nest,request):
    op=request.get('op');args=request.get('args',{})
    allowed={'status':status,'boot':boot,'phase':phase,'event':event,'intention':intention,
             'conversation':conversation,'submit':submit,'mind_pending':mind_pending,'pulse':pulse,'work':work,
             'publish_intentions':publish_intentions,'result':committed_result,'project_get':project_get,'project_set':project_set,'flow_draft':flow_draft,'kpp_prepare':kpp_prepare,
             'demo_test':demo_test,'demo_accept':demo_accept,'project_bundle':project_bundle,'project_import':project_import}
    if op not in allowed:raise ValueError('Unsupported Studio operation')
    return allowed[op](nest,**args)


def mind_pending(nest):
    """Controller scheduling projection; no private cognition context."""
    with database(nest) as db:
        row=db.execute("SELECT id FROM mind WHERE phase='AWAITING_MIND' ORDER BY rowid LIMIT 1").fetchone()
        return {'request_id':row[0]} if row else {'status':'IDLE'}


def publish_intentions(nest,request_id):
    released=committed_result(nest,request_id)
    if released['status']!='COMMITTED':raise ValueError('Committed active reply required')
    proposed=c.loads(released['reply'])
    c.shape(proposed,{'schema','text','intentions'})
    if proposed['schema']!='studio.intent-proposal/1' or type(proposed['intentions']) is not list or not 1<=len(proposed['intentions'])<=8:raise ValueError('Invalid intention proposal')
    # Explicit operator RPC publishes only data retrieved from the committed reply.
    prefix='mind-'+hashlib.sha256(request_id.encode()).hexdigest()[:24]
    results=[]
    for index,item in enumerate(proposed['intentions']):
        c.shape(item,{'role','value'})
        if item['role'] not in ROLES:raise ValueError('Unknown proposed role')
        c.canonical(item['value'],limit=8192)
    for index,item in enumerate(proposed['intentions']):
        results.append(intention(nest,item['role'],item['value'],prefix+'-'+str(index)))
    return {'commit_head':released['commit_head'],'intentions':results,'authority':'OWNER_PUBLISH_UNDER_EXISTING_GRANTS'}


def committed_result(nest,request_id):
    with body_lock(Path(nest)),database(nest) as db:
        if _setting(db,'phase')!='ACTIVE':return {'status':'STASIS'}
        row=db.execute('SELECT phase FROM mind WHERE id=?',(request_id,)).fetchone()
        if not row:raise ValueError('Unknown conversation')
        with nullcontext(_session(Path(nest)/'prime.engram')) as mind:
            # A crash can occur after the canonical commit but before controller state.
            # Reconcile from the canonical request binding; never regenerate a reply.
            if not mind.db.execute('SELECT 1 FROM requests WHERE id=?',(request_id,)).fetchone():
                return {'status':row[0]}
            result=mind.submit(request_id,None,broker=lambda authority,name: authority=='release' and name=='publication.release')
        db.execute("UPDATE mind SET phase='COMMITTED',reply=? WHERE id=?",(result['reply'],request_id))
        return {'status':'COMMITTED','reply':result['reply'],'commit_head':result['commit_head']}


def recover_mind(nest,request_id,*,reviewed=False):
    if reviewed is not True:raise PermissionError('Stopped controller and owner review required')
    from .limbs import worker_lease
    with worker_lease(nest,'controller'),body_lock(Path(nest)),database(nest) as db:
        if _setting(db,'phase')!='STASIS':raise ValueError('Recovery requires stasis')
        with journal.Journal(Path(nest)/'prime.engram') as mind:
            canonical=mind.db.execute('SELECT 1 FROM requests WHERE id=?',(request_id,)).fetchone()
            if canonical:
                db.execute("UPDATE mind SET phase='COMMITTED' WHERE id=?",(request_id,))
                return {'status':'CANONICAL_COMMIT_RECONCILED','release':'REQUIRES_ACTIVE_AUTHORITY'}
            result=mind.recover(request_id,reviewed=True)
        db.execute("UPDATE mind SET phase='NEEDS_REVIEW' WHERE id=?",(request_id,))
        return result


def demo_test(nest):
    from .studio_demo import qualify
    with database(nest) as db:
        if _setting(db,'phase')!='ACTIVE':raise ValueError('Studio is in stasis')
    return qualify(nest)


def demo_accept(nest,confirmed=False):
    from .studio_demo import accept
    with database(nest) as db:
        if _setting(db,'phase')!='ACTIVE':raise ValueError('Studio is in stasis')
    # This RPC is exposed only through the authenticated operator controller.
    return accept(nest,baker='Authenticated local Studio operator',confirmed=confirmed)


def project_get(nest):
    path=Path(nest)/'project.json'
    if not path.exists():return {'status':'NO_PROJECT'}
    value=studio_project.validate(c.loads(path.read_text('utf8')))
    return {'project':value,'revision':c.digest(value),'inspection':studio_project.inspection(value)}


def project_set(nest,value,expected_revision):
    value=studio_project.validate(value)
    with body_lock(Path(nest)):
        old=project_get(nest)
        if old.get('revision')!=expected_revision:raise ValueError('Stale project revision')
        atomic_bytes(Path(nest)/'project.json',c.canonical(value).encode(),replace=True)
    return project_get(nest)


def project_bundle(nest):
    import base64,tempfile
    with tempfile.TemporaryDirectory(prefix='studio-save-') as td:
        target=Path(td)/'project.anchorstudio'
        receipt=studio_project.save(project_get(nest)['project'],target)
        return {**receipt,'base64':base64.b64encode(target.read_bytes()).decode('ascii')}


def project_import(nest,encoded,expected_revision):
    import base64,tempfile
    if type(encoded) is not str or len(encoded)>750000:raise ValueError('Browser project import exceeds transport limit; use CLI')
    raw=base64.b64decode(encoded,validate=True)
    with tempfile.TemporaryDirectory(prefix='studio-import-') as td:
        path=Path(td)/'incoming.anchorstudio';path.write_bytes(raw)
        return project_set(nest,studio_project.load(path),expected_revision)


def flow_draft(nest,flows):
    project=project_get(nest)
    if 'project' not in project:raise ValueError('Select a reviewed project first')
    value=studio_project.from_flows(flows,project['project']['recipe'])
    return {'project':value,'base_revision':project['revision'],'inspection':studio_project.inspection(value)}


def kpp_prepare(nest):
    """Operator-only preparation; no candidate execution or acceptance."""
    from .kpp import workshop, build
    project=project_get(nest)['project']
    if project['unresolved']:raise ValueError('Resolve visual relationships before KPP preparation')
    recipe=project['recipe']
    target=Path(nest)/'kpp-workspaces'/c.digest(recipe)
    if not target.exists():
        workshop.begin(target,recipe,Path(__file__).parent/'kpp/resources')
    return {'workspace':str(target.resolve()),'step':build.step(target),'authority':'NONE'}


def main(argv=None):
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(prog='mantleos studio')
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('init','status','stasis','activate','serve','workflow-serve','mind-serve','mind-configure','mind-status','mind-next','mind-submit','import','export','run','migrate-limbs','rebind-source','recover-mind'):
        p=sub.add_parser(command);p.add_argument('--nest',type=Path,required=True)
        if command in ('rebind-source','recover-mind'):p.add_argument('--reviewed',action='store_true')
        if command=='recover-mind':p.add_argument('--request-id',required=True)
        if command=='init':p.add_argument('--founding',type=Path,required=True)
        if command=='mind-configure':
            p.add_argument('--owner-file',type=Path,required=True)
            p.add_argument('--catalog',type=Path,required=True)
            p.add_argument('--accounting-file',type=Path)
            p.add_argument('--reviewed',action='store_true')
        if command=='run':
            p.add_argument('--node',type=Path,required=True);p.add_argument('--modules',type=Path,required=True);p.add_argument('--port',type=int,default=18880)
        if command=='mind-submit':
            p.add_argument('--request-id',required=True);p.add_argument('--proposal',type=Path,required=True)
        if command in ('import','export'):p.add_argument('--file',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.command in ('mind-serve','mind-configure','mind-status'):
        from . import studio_auto_mind
        if args.command=='mind-serve':return studio_auto_mind.serve(args.nest)
        if args.command=='mind-configure':
            result=studio_auto_mind.configure(args.nest,owner_file=args.owner_file,
                catalog=c.loads(args.catalog.read_text('utf8')),accounting_file=args.accounting_file,
                reviewed=args.reviewed)
        else:result=studio_auto_mind.public_status(args.nest)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    if args.command=='run':
        import os,subprocess
        if not 1024<=args.port<=65535:raise ValueError('Invalid loopback port')
        env={**os.environ,'STUDIO_NEST':str(args.nest.resolve()),'STUDIO_MODULES':str(args.modules.resolve()),'STUDIO_PYTHON':sys.executable,'STUDIO_PORT':str(args.port),'PYTHONPATH':str(Path(__file__).resolve().parent.parent)}
        return subprocess.call([str(args.node.resolve()),str(Path(__file__).parent/'kpp/resources/examples/anchor-studio/launcher.cjs')],env=env)
    if args.command=='workflow-serve':
        from .studio_workflows import WorkflowStore, serve
        def check_source():
            with database(args.nest):pass  # Pinned controller, founding source and established Heart.
        check_source()
        return serve(WorkflowStore(args.nest/'operational-workflows'),check_source=check_source)
    if args.command=='serve':
        from concurrent.futures import ProcessPoolExecutor
        from multiprocessing import get_context
        from .limbs import worker_lease
        with worker_lease(args.nest,'controller'), ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as workers:
            inflight={}
            for line in sys.stdin:
                request={}
                try:
                    request=c.loads(line)
                    if request.get('op')=='pulse':
                        result=pulse(args.nest)
                        ready=[t['limb'] for t in limb_set(args.nest).status()['tasks'] if t['phase']=='READY']
                        for role,future in list(inflight.items()):
                            if future.done():
                                try:future.result()
                                except Exception as error:event(args.nest,'pain',{'worker':role,'error':type(error).__name__},'worker-'+uuid.uuid4().hex)
                                del inflight[role]
                        for role in [r for r in ready if r not in inflight][:max(0,2-len(inflight))]:
                            inflight[role]=workers.submit(work,args.nest,role)
                    else:result=dispatch(args.nest,request)
                    response={'id':request.get('id'),'ok':True,'result':result}
                except Exception as exc:response={'id':request.get('id'),'ok':False,'error':type(exc).__name__+': '+str(exc)}
                print(json.dumps(response),flush=True)
        return 0
    if args.command=='recover-mind':result=recover_mind(args.nest,args.request_id,reviewed=args.reviewed)
    elif args.command=='rebind-source':result=rebind_source(args.nest,reviewed=args.reviewed)
    elif args.command=='migrate-limbs':result=migrate_limbs(args.nest,approved=True)
    elif args.command=='init':result=initialize(args.nest,args.founding)
    elif args.command=='status':result=status(args.nest)
    elif args.command in ('stasis','activate'):result=phase(args.nest,args.command=='activate')
    elif args.command=='mind-submit':result=submit(args.nest,args.request_id,c.loads(args.proposal.read_text('utf8')))
    elif args.command=='import':
        current=project_get(args.nest)
        result=project_set(args.nest,studio_project.load(args.file),current.get('revision'))
    elif args.command=='export':result=studio_project.save(project_get(args.nest)['project'],args.file)
    else:
        with database(args.nest) as db:
            row=db.execute("SELECT id,frame FROM mind WHERE phase='AWAITING_MIND' ORDER BY rowid LIMIT 1").fetchone()
            result={'status':'IDLE'} if not row else {'request_id':row[0],**json.loads(row[1])}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
