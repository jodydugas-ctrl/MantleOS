"""Anchor Journal Engram /1. Local durable carrier; host-supplied language only.

Storage is SQLite; CELL and Anchor semantics remain the shared definitions.
Hashes check integrity, never publisher identity or effect authority.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import uuid
from . import anchor_language, cartridge, engram, primer
from .anchor_design import journal_design
from .effects import Capability, CapabilityRegistry, CheckedActionExecutor

SCHEMA = 'mantle.journal-engram/1'
PROTOCOL = 'mantle.journal-encounter/1'
ZERO = engram.ZERO
canon = engram.canonical

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def digest(value):
    return sha(canon(value).encode())

def _new(path):
    path = Path(path).resolve()
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def bootstrap_metadata():
    from .journal_bootstrap import contract
    source = Path(__file__).with_name('journal_bootstrap.py').read_text('utf8')
    return {'host_contract':contract(),'bootstrap':source,'bootstrap_sha256':sha(source.encode())}

def from_body(body, output):
    """Capture a verified Body without executing its carried source."""
    body = Path(body).resolve()
    cartridge.verify(body)
    founding = primer.load_primer(body)
    records = engram.read(body/'ENGRAM.jsonl')
    register = anchor_language.validate_register(json.loads((body/'ANCHOR-REGISTER.json').read_text('utf8')))
    with tempfile.TemporaryDirectory(prefix='journal-pack-') as td:
        archive = Path(td)/'body.vcw'
        cartridge.pack(body, archive)
        raw = archive.read_bytes()
    design_path=body/'ANCHOR-DESIGN.json'
    from .anchor_design import validate, journal_design
    design=validate(json.loads(design_path.read_text('utf8'))) if design_path.exists() else journal_design()
    target = _new(output)
    db = sqlite3.connect(target)
    try:
        db.executescript('''
        PRAGMA synchronous=FULL;
        CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE objects(sha256 TEXT PRIMARY KEY,payload BLOB NOT NULL);
        CREATE TABLE records(seq INTEGER PRIMARY KEY,sha256 TEXT UNIQUE NOT NULL,raw TEXT NOT NULL);
        CREATE TABLE requests(id TEXT PRIMARY KEY,input TEXT NOT NULL,record_sha256 TEXT NOT NULL);
        CREATE TABLE pending(id TEXT PRIMARY KEY,raw TEXT NOT NULL);
        CREATE TRIGGER retain_objects_update BEFORE UPDATE ON objects BEGIN SELECT RAISE(ABORT,'immutable object'); END;
        CREATE TRIGGER retain_objects_delete BEFORE DELETE ON objects BEGIN SELECT RAISE(ABORT,'immutable object'); END;
        CREATE TRIGGER retain_records_update BEFORE UPDATE ON records BEGIN SELECT RAISE(ABORT,'append-only record'); END;
        CREATE TRIGGER retain_records_delete BEFORE DELETE ON records BEGIN SELECT RAISE(ABORT,'append-only record'); END;
        ''')
        birth = json.loads((body/'BIRTH.json').read_text('utf8'))
        values = {'anchor_design':design,**bootstrap_metadata(),'schema':SCHEMA,'snapshot':sha(raw),'primer':founding,'register':register,
                  'identity':birth['id'],'persona':birth['primer']['persona_name'],
                  'exported_head':records[-1]['sha256'] if records else ZERO}
        db.executemany('INSERT INTO meta VALUES (?,?)',[(k,canon(v)) for k,v in values.items()])
        db.execute('INSERT INTO objects VALUES (?,?)',(sha(raw),raw))
        for r in records:
            db.execute('INSERT INTO records VALUES (?,?,?)',(r['seq'],r['sha256'],canon(r)))
            if r['source']=='journal-bridge':
                db.execute('INSERT INTO requests VALUES (?,?,?)',(r['body']['request_id'],r['body']['user'],r['sha256']))
        db.commit()
    finally:
        db.close()
    with Journal(target) as journal:
        return journal.status()

def create(output, *, founding=None, default_primer=None, name='Raven'):
    """Fresh identity/experience. Explicit founding wins over private default."""
    from . import specimens
    selected = founding or default_primer or os.environ.get('MANTLE_RAVEN_SOURCE')
    if not selected:
        raise ValueError('Raven setup required: --founding BODY_OR_CARRIER or MANTLE_RAVEN_SOURCE')
    selected = Path(selected)
    if selected.is_dir():
        birth = json.loads((selected/'BIRTH.json').read_text('utf8'))
        primer.verify_lock(selected)
        material = (birth,{n:(selected/'PRIMER'/n).read_bytes() for n in ('COMMANDMENTS.md','PERSONA.md')},
                    {'source':'operator-selected founding material','executed':False})
    else:
        material = specimens.founding_material(selected)
    with tempfile.TemporaryDirectory(prefix='journal-birth-') as td:
        body = Path(td)/'body'
        specimens.fresh(body,name=name,founding=material)
        return from_body(body,output)

class Journal:
    def __init__(self,path):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        self.db = sqlite3.connect(self.path,timeout=5,isolation_level=None)
        self.db.execute('PRAGMA trusted_schema=OFF')
        self.db.execute('PRAGMA synchronous=FULL')
        try: self.verify()
        except BaseException:
            self.db.close()
            raise

    def __enter__(self): return self
    def __exit__(self,*args): self.close()
    def close(self): self.db.close()
    def _meta(self,key): return json.loads(self.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()[0])
    def _version(self): return self.db.execute('PRAGMA data_version').fetchone()[0]
    def _fresh(self):
        if self._version()!=self.version:
            self.verify()
    def head(self):
        row = self.db.execute('SELECT sha256 FROM records ORDER BY seq DESC LIMIT 1').fetchone()
        return row[0] if row else ZERO

    def verify(self):
        # Ledger rows, metadata and replay bindings must come from one SQLite
        # snapshot. A cooperating writer may commit between individual queries.
        version=self._version()
        owned=not self.db.in_transaction
        if owned:self.db.execute('BEGIN')
        try:
            result=self._verify_snapshot()
            # Keep the version observed before acquiring the read snapshot. A
            # later foreign commit must trigger another refresh, never be hidden
            # by recording its version alongside the older verified records.
            self.version=version
            if owned:self.db.commit()
            return result
        except BaseException:
            if owned:self.db.rollback()
            raise

    def _verify_snapshot(self):
        if self.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('SQLite integrity failure')
        if self._meta('schema')!=SCHEMA: raise ValueError('Unsupported journal schema')
        for h,raw in self.db.execute('SELECT sha256,payload FROM objects'):
            if sha(raw)!=h: raise ValueError('Journal object corruption')
        snapshot = self.db.execute('SELECT payload FROM objects WHERE sha256=?',(self._meta('snapshot'),)).fetchone()
        if snapshot is None: raise ValueError('Missing snapshot')
        # Recheck object bytes above on every refresh. An unchanged verified snapshot
        # need not be unpacked/compiled again when a cooperating process appended.
        # The ledger and all live metadata are still checked below; no timestamp trust.
        key=self._meta('snapshot')
        cached=getattr(self,'_snapshot_cache',None)
        if cached is None or cached[0]!=key:
            with tempfile.TemporaryDirectory(prefix='journal-verify-') as td:
                archive=Path(td)/'body.vcw'; archive.write_bytes(snapshot[0])
                body=Path(td)/'body';cartridge.unpack(archive,body)
                view={'records':engram.read(body/'ENGRAM.jsonl'),'primer':primer.load_primer(body),
                      'register':anchor_language.validate_register(json.loads((body/'ANCHOR-REGISTER.json').read_text('utf8'))),
                      'birth':json.loads((body/'BIRTH.json').read_text('utf8'))}
            self._snapshot_cache=(key,canon(view))
        view=json.loads(self._snapshot_cache[1])
        original=view['records'];reg=view['register'];birth=view['birth']
        if view['primer']!=self._meta('primer'):raise ValueError('Founding material mismatch')
        if reg!=self._meta('register'):raise ValueError('Register differs from snapshot')
        if birth['id']!=self._meta('identity') or birth['primer']['persona_name']!=self._meta('persona'):raise ValueError('Identity mismatch')
        self.records=[];previous=ZERO
        for seq,h,raw in self.db.execute('SELECT seq,sha256,raw FROM records ORDER BY seq'):
            r=json.loads(raw)
            if (seq!=len(self.records)+1 or r['seq']!=seq or r['sha256']!=h or
                r.get('prev_sha256',r.get('prev'))!=previous or engram.hash_record(r)!=h or canon(r)!=raw):
                raise ValueError('Journal chain corruption')
            self.records.append(r);previous=h
        if self.records[:len(original)]!=original: raise ValueError('Snapshot history prefix changed')
        for rid,user,h in self.db.execute('SELECT id,input,record_sha256 FROM requests'):
            matches=[r for r in self.records if r['sha256']==h]
            if len(matches)!=1 or matches[0]['body'].get('request_id')!=rid or matches[0]['body'].get('user')!=user:
                raise ValueError('Replay binding corruption')
        expected_requests={}
        for record in self.records:
            if record['source']=='journal-bridge':
                body=record['body'];rid=body['request_id']
                if rid in expected_requests:raise ValueError('Duplicate canonical request')
                anchor_language.validate_message(body['anchor_message'])
                expected_requests[rid]=(body['user'],record['sha256'])
        actual_requests={rid:(user,h) for rid,user,h in self.db.execute('SELECT id,input,record_sha256 FROM requests')}
        if actual_requests!=expected_requests:raise ValueError('Incomplete replay index')
        if self._meta('exported_head') not in {ZERO,*(r['sha256'] for r in self.records)}:
            raise ValueError('Exported head is not in retained history')
        extra={k:json.loads(v) for k,v in self.db.execute("SELECT key,value FROM meta WHERE key IN ('host_contract','bootstrap','bootstrap_sha256')")}
        if extra:
            from .journal_bootstrap import contract
            if set(extra)!={'host_contract','bootstrap','bootstrap_sha256'} or extra['host_contract']!=contract() or sha(extra['bootstrap'].encode())!=extra['bootstrap_sha256']:
                raise ValueError('Invalid journal host bootstrap contract')
        from .anchor_design import validate, projection
        row=self.db.execute("SELECT value FROM meta WHERE key='anchor_design'").fetchone()
        self.design=validate(json.loads(row[0])) if row else None
        self.design_projection=projection(self.design) if self.design else None
        self.design_digest=self.design_projection['sha256'] if self.design else None
        self.founding=self._meta('primer');self.register=reg
        from .projection import build
        self.index=build(self.records)
        return {'result':'VERIFIED','records':len(self.records),'head':previous,'executed':False}

    def status(self):
        self._fresh()
        return {'schema':SCHEMA,'identity':self._meta('identity'),'persona':self._meta('persona'),
                'records':len(self.records),'head':self.head(),'exported_head':self._meta('exported_head'),
                'primer_sha256':self.founding['sha256'],'language':anchor_language.DIALECT}

    def _insert(self,kind,source,body,expected_head):
        if self.head()!=expected_head: raise ValueError('Stale journal head')
        r={'schema':'mantle.engram-record/1','seq':len(self.records)+1,'id':uuid.uuid4().hex,
           'type':kind,'source':source,'body':body,'prev_sha256':expected_head}
        r['sha256']=engram.hash_record(r)
        from .cells import append_segment
        append_segment(r)
        self.db.execute('INSERT INTO records VALUES (?,?,?)',(r['seq'],r['sha256'],canon(r)))
        return r

    def _remember(self,r):
        self.records.append(r)
        # Index only new records. Supersession/effect semantics retain shared build rules.
        from .projection import build
        delta=build([r]); offset=len(self.records)-1
        self.index['texts'].extend(delta['texts'])
        for token,indices in delta['postings'].items(): self.index['postings'].setdefault(token,[]).append(offset)
        self.index['superseded']=sorted(set(self.index['superseded'])|set(delta['superseded']))
        for k in delta['effect_terminals']: self.index['effect_terminals'][k]=offset
        if delta['active_face'] is not None:self.index['active_face']=offset
        if self.index['active_face'] is not None and self.records[self.index['active_face']]['id'] in self.index['superseded']:
            self.index['active_face']=next((i for i in range(len(self.records)-1,-1,-1)
                if self.records[i]['type']=='face' and self.records[i]['id'] not in self.index['superseded']),None)

    def append_record(self,kind,source,body,*,expected_head):
        self._fresh();self.db.execute('BEGIN IMMEDIATE')
        try:
            r=self._insert(kind,source,body,expected_head);self.db.commit()
        except BaseException:
            self.db.rollback();raise
        self._remember(r);return r

    def recall(self,text,*,limit=6):
        self._fresh()
        from .projection import query
        return query(self.records,self.index,text,limit=limit)

    def _primer_frame(self):
        return {'sha256':self.founding['sha256'],'content':self.founding['compiled'],
                'load_order':self.founding['load_order']}

    def _context(self,text):
        recent=[r for r in self.records if r['type']=='turn'][-2:]
        items=[{'record_sha256':r['sha256'],'user':r['body'].get('user',''),
                'reply':r['body'].get('reply','')} for r in recent]
        matches=self.recall(text)['matches']
        recent_hashes={r['sha256'] for r in recent}
        projected=[]
        for match in matches:
            if match['record_sha256'] in recent_hashes: continue
            record=self.records[match['seq']-1]
            if record['type']=='turn':
                body=record['body']
                match={k:v for k,v in match.items() if k!='excerpt'}
                match['excerpt']=canon({'user':body.get('user',''),'reply':body.get('reply','')})[:1600]
                match['excerpt_truncated']=len(canon(body))>1600
            projected.append(match)
        matches=projected
        out=[];used=0
        for item in items+matches:
            size=len(canon(item).encode())
            if used+size<=16384:out.append(item);used+=size
        return {'items':out,'omitted':len(items)+len(matches)-len(out),'budget_bytes':16384,'ledger_head':self.head()}

    def open(self,user,*,request_id,model_id):
        self._fresh()
        if not isinstance(user,str) or not user.strip() or len(user.encode())>262144:raise ValueError('Invalid user input')
        if not isinstance(request_id,str) or not request_id or len(request_id)>96:raise ValueError('Invalid request id')
        if not isinstance(model_id,str) or not model_id or len(model_id)>256:raise ValueError('Invalid model label')
        prior=self.db.execute('SELECT input FROM requests WHERE id=?',(request_id,)).fetchone()
        if prior:
            if prior[0]!=user:raise ValueError('Request id reused with different input')
            return {'status':'REPLAY','request_id':request_id}
        pending=self.db.execute('SELECT raw FROM pending WHERE id=?',(request_id,)).fetchone()
        if pending:
            p=json.loads(pending[0])
            if p['user']!=user or p['model_id']!=model_id:raise ValueError('Pending request differs')
            if p.get('in_action'):raise ValueError('Interrupted action: explicit recovery review required')
            if p['head']!=self.head() or p.get('design_sha256')!=self.design_digest:raise ValueError('Stale pending request')
            return p['frame']
        payload={'schema':PROTOCOL,'stage':'ENCOUNTER','order':['PRIMER','ANCHOR_STATE','MEMORY','USER_INPUT'],
                 'primer':self._primer_frame(),'register':self.register,'memory':self._context(user),'user_input':user,
                 'request_id':request_id,'model_id':model_id,'capabilities':['body.status','engram.query'],
                 'response_contract':{'kind':'reply | action','reply_fields':['kind','reply','observation_sha256'],
                    'action_fields':['kind','capability','arguments'],
                    'rules':'Full PRIMER applies. Return one JSON proposal. No hidden reasoning. Only committed replies may be released. Tool visibility grants no permission.'}}
        if self.design:payload['anchor_design']=self.design_projection
        frame=anchor_language.make_message('BODY','MIND','frame-'+uuid.uuid4().hex,payload,register=self.register,provenance='host_verified')
        p={'design_sha256':self.design_digest,'head':self.head(),'user':user,'model_id':model_id,'frame':frame,'observation':None}
        self.db.execute('INSERT INTO pending VALUES (?,?)',(request_id,canon(p)))
        return frame

    def submit(self,request_id,proposal,*,broker=None):
        self._fresh();broker=broker or (lambda authority,name:False)
        replay=self.db.execute('SELECT record_sha256 FROM requests WHERE id=?',(request_id,)).fetchone()
        if replay:
            if not broker('release','publication.release'):raise PermissionError('Release denied')
            r=next(r for r in self.records if r['sha256']==replay[0])
            return {'reply':r['body']['reply'],'commit_head':r['sha256'],'replayed':True,'language_packets':0,'model_called':False}
        row=self.db.execute('SELECT raw FROM pending WHERE id=?',(request_id,)).fetchone()
        if row is None:raise ValueError('Unknown request')
        p=json.loads(row[0]);anchor_language.validate_message(p['frame'])
        frame=p['frame']['payload']
        if (frame.get('primer')!=self._primer_frame() or frame.get('register')!=self.register or
            frame.get('user_input')!=p['user'] or frame.get('model_id')!=p['model_id'] or
            frame.get('request_id')!=request_id or frame.get('schema')!=PROTOCOL):
            raise ValueError('Pending frame binding mismatch')
        if p['observation'] is not None and (frame.get('observation')!=p['observation'] or
            frame.get('observation_sha256')!=digest(p['observation'])):
            raise ValueError('Pending observation mismatch')
        if p.get('in_action'):raise ValueError('Interrupted action requires recovery review')
        if p['head']!=self.head() or p.get('design_sha256')!=self.design_digest or frame.get('anchor_design')!=self.design_projection:raise ValueError('Stale preparation')
        if not isinstance(proposal,dict):raise ValueError('Invalid proposal')
        if proposal.get('kind')=='action':
            if set(proposal)!={'kind','capability','arguments'} or p['observation'] is not None:raise ValueError('Only one action per encounter')
            cap=proposal['capability']
            if cap not in {'body.status','engram.query'}:raise ValueError('Unavailable journal capability')
            registry=CapabilityRegistry()
            registry.register(Capability('body.status','READ','read','mantle.journal/1',lambda a:self.status(),lambda v:v['schema']==SCHEMA))
            registry.register(Capability('engram.query','READ','read','mantle.journal/1',lambda a:self.recall(a['text']),lambda v:v['authoritative'] is False))
            p['in_action']=True;self.db.execute('UPDATE pending SET raw=? WHERE id=?',(canon(p),request_id))
            observation=CheckedActionExecutor(registry,broker,self).execute(cap,proposal['arguments'],request_id=request_id,expected_head=p['head'])
            p['head']=self.head();p['observation']=observation;p['in_action']=False
            payload=dict(p['frame']['payload']);payload.update(stage='RESPOND',observation=observation,observation_sha256=digest(observation),capabilities=[])
            p['frame']=anchor_language.make_message('BODY','MIND','frame-'+uuid.uuid4().hex,payload,register=self.register,provenance='host_verified')
            self.db.execute('UPDATE pending SET raw=? WHERE id=?',(canon(p),request_id))
            return p['frame']
        if set(proposal)!={'kind','reply','observation_sha256'} or proposal.get('kind')!='reply':raise ValueError('Invalid reply proposal')
        reply=proposal['reply']
        if not isinstance(reply,str) or not reply.strip() or len(reply.encode())>262144:raise ValueError('Invalid reply')
        expected=digest(p['observation']) if p['observation'] is not None else None
        if proposal['observation_sha256']!=expected:raise ValueError('Observation binding mismatch')
        from .checkpoint import narration_flags
        if narration_flags(reply,self._meta('persona')):raise ValueError('Third-person persona narration refused')
        if not broker('release','publication.release'):raise PermissionError('Release denied')
        message=anchor_language.make_message('MIND','BODY','reply-'+uuid.uuid4().hex,proposal,register=self.register,provenance='model_inferred')
        body={'turn_schema':PROTOCOL,'request_id':request_id,'user':p['user'],'reply':reply,
              'model_id':p['model_id'],'frame_sha256':p['frame']['sha256'],'anchor_message':message,
              'action_observation':p['observation'],'design_sha256':self.design_digest,'primer_sha256':self.founding['sha256']}
        self.db.execute('BEGIN IMMEDIATE')
        try:
            r=self._insert('turn','journal-bridge',body,p['head'])
            self.db.execute('INSERT INTO requests VALUES (?,?,?)',(request_id,p['user'],r['sha256']))
            self.db.execute('DELETE FROM pending WHERE id=?',(request_id,));self.db.commit()
        except BaseException:
            self.db.rollback();raise
        self._remember(r)
        return {'reply':reply,'commit_head':r['sha256'],'replayed':False,'language_packets':2 if p['observation'] else 1,'model_called':False,'frame_sha256':p['frame']['sha256']}

    def recover(self,request_id,*,reviewed=False):
        if reviewed is not True:raise PermissionError('Recovery requires explicit review')
        self._fresh()
        self.db.execute('DELETE FROM pending WHERE id=?',(request_id,))
        return {'status':'PENDING_DISCARDED','request_id':request_id,'effects_retained':True}

    def materialize(self,output):
        self._fresh();target=_new(output)
        with tempfile.TemporaryDirectory(prefix='journal-restore-') as td:
            raw=self.db.execute('SELECT payload FROM objects WHERE sha256=?',(self._meta('snapshot'),)).fetchone()[0]
            archive=Path(td)/'snapshot.vcw';archive.write_bytes(raw)
            cartridge.unpack(archive,target)
        (target/'ENGRAM.jsonl').write_text(''.join(canon(r)+'\n' for r in self.records),encoding='utf8',newline='\n')
        if self.design:(target/'ANCHOR-DESIGN.json').write_text(canon(self.design)+'\n',encoding='utf8')
        from .lifecycle import finalize
        from .vault_auto import sync_committed
        sync_committed(target)
        finalize(target);cartridge.verify(target)
        return {'output':str(target),'head':self.head()}

    def export(self,output,*,format='journal'):
        self._fresh();target=_new(output);head=self.head()
        with tempfile.TemporaryDirectory(prefix='journal-export-') as td:
            stage=Path(td)/('export.png' if format=='chroma' else 'export')
            if format=='journal':
                dest=sqlite3.connect(stage)
                try:
                    self.db.backup(dest)
                    dest.executemany('INSERT OR REPLACE INTO meta VALUES (?,?)',
                                     [(k,canon(v)) for k,v in {**bootstrap_metadata(),'anchor_design':self.design or journal_design()}.items()])
                    dest.execute('UPDATE meta SET value=? WHERE key=?',(canon(head),'exported_head'))
                    dest.commit()
                finally:dest.close()
                with Journal(stage) as check:
                    if check.head()!=head:raise ValueError('Export head mismatch')
            elif format in {'cartridge','chroma'}:
                body=Path(td)/'body';self.materialize(body)
                from .kernel import pack_verified_body,verify_restored_output
                pack_verified_body(body,stage,format=format)
                verify_restored_output(stage,Path(td)/'check',format=format)
            else:raise ValueError('Unsupported export format')
            from .transactions import atomic_bytes
            atomic_bytes(target,stage.read_bytes(),replace=False)
        self.db.execute('UPDATE meta SET value=? WHERE key=?',(canon(head),'exported_head'))
        return {'output':str(target),'format':format,'head':head,'verified':True}

def main(argv=None):
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(prog='mantleos journal')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('create');p.add_argument('--output',required=True);p.add_argument('--founding');p.add_argument('--body')
    for command in ('inspect','verify','recall','open','submit','recover','export','stdio'):
        p=sub.add_parser(command);p.add_argument('file')
        if command=='recall':p.add_argument('text')
        if command=='open':p.add_argument('--user',required=True);p.add_argument('--request-id',required=True);p.add_argument('--model-id',required=True)
        if command in {'submit','recover'}:p.add_argument('--request-id',required=True)
        if command=='submit':p.add_argument('--proposal');p.add_argument('--allow-release',action='store_true');p.add_argument('--allow-read',action='store_true')
        if command=='recover':p.add_argument('--reviewed',action='store_true')
        if command=='export':p.add_argument('--output',required=True);p.add_argument('--format',choices=['journal','cartridge','chroma'],default='journal')
    args=parser.parse_args(argv)
    try:
        if args.command=='create':result=from_body(args.body,args.output) if args.body else create(args.output,founding=args.founding)
        else:
            with Journal(args.file) as journal:
                if args.command=='stdio':
                    for line in sys.stdin:
                        try:
                            request=json.loads(line);op=request['op']
                            if op not in {'status','recall','open','submit','recover'}:raise ValueError('Unsupported session operation')
                            kw=request.get('arguments',{})
                            if op=='submit':
                                grants=request.get('grants',[])
                                kw['broker']=lambda authority,name:authority in grants
                            value=getattr(journal,op)(**kw)
                            print(canon({'ok':True,'result':value}),flush=True)
                        except (ValueError,KeyError,PermissionError,sqlite3.Error) as error:
                            print(canon({'ok':False,'error':str(error)}),flush=True)
                    return 0
                if args.command=='inspect':result=journal.status()
                elif args.command=='verify':result=journal.verify()
                elif args.command=='recall':result=journal.recall(args.text)
                elif args.command=='open':result=journal.open(args.user,request_id=args.request_id,model_id=args.model_id)
                elif args.command=='submit':
                    proposal=json.loads(Path(args.proposal).read_text('utf8')) if args.proposal else None
                    result=journal.submit(args.request_id,proposal,broker=lambda a,n:args.allow_release if a=='release' else args.allow_read if a=='read' else False)
                elif args.command=='recover':result=journal.recover(args.request_id,reviewed=args.reviewed)
                else:result=journal.export(args.output,format=args.format)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,sqlite3.Error) as error:
        print('FAIL: '+str(error),file=sys.stderr);return 2
