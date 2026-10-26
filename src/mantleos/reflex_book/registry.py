"""Disposable M3 SQLite registry simulation; NOT MantleOS state or admission.

All state transitions are append-only event records in a single SQLite transaction.
Host-supplied issuer credentials, trusted time, and dependency heads are mandatory.
The operator/host (including SQLite file access) remains a trusted boundary.
"""
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
import sqlite3

from .canonical import dumps,loads,sha256
from .evidence import validate_candidate,_baselines,HEX
from .admission import verify_approval
from .errors import refuse,ReflexError
from .types import timestamp
from .vm import run as vm_run

ZERO='0'*64


def _json(item):
    return dumps(item).decode('utf-8')


def _record_denials(operation):
    """Audit host-side Refusals without storing rejected payloads or secrets."""
    def decorate(fn):
        @wraps(fn)
        def checked(self,*args,**kwargs):
            try:
                return fn(self,*args,**kwargs)
            except ReflexError as exc:
                name=kwargs.get('now_utc')
                if type(name) is str:
                    try:
                        timestamp(name)
                        cid=None
                        if args:
                            candidate=args[0]
                            if type(candidate) is dict:
                                cid=candidate.get('candidate_sha256')
                            elif type(candidate) is str:
                                cid=candidate
                        if type(cid) is not str or not HEX.fullmatch(cid):
                            cid=None
                        self._log_refusal(operation,cid,exc.code,name)
                    except (ReflexError,sqlite3.DatabaseError,OSError):
                        # Never disguise the initial refusal on damaged/unwritable audit.
                        pass
                raise
        return checked
    return decorate


class ExperimentalRegistry:
    """Host-only API; never provided to programs, carriers or model-created IR."""
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        conn=self._connect()
        try:
            conn.executescript('''
            CREATE TABLE IF NOT EXISTS artifacts (
              candidate_sha256 TEXT PRIMARY KEY,
              manifest TEXT NOT NULL,
              binary BLOB NOT NULL,
              evidence BLOB NOT NULL,
              approval TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              prev_sha256 TEXT NOT NULL,
              event_sha256 TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS no_event_update BEFORE UPDATE ON events
              BEGIN SELECT RAISE(ABORT, 'audit rows are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS no_event_delete BEFORE DELETE ON events
              BEGIN SELECT RAISE(ABORT, 'audit rows are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS no_artifact_update BEFORE UPDATE ON artifacts
              BEGIN SELECT RAISE(ABORT, 'artifact rows are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS no_artifact_delete BEFORE DELETE ON artifacts
              BEGIN SELECT RAISE(ABORT, 'artifact rows are immutable'); END;
            ''')
            conn.commit()
        finally:
            conn.close()

    def _connect(self):
        conn=sqlite3.connect(str(self.path),timeout=10)
        conn.execute('PRAGMA busy_timeout=10000')
        conn.execute('PRAGMA synchronous=FULL')
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    @contextmanager
    def _tx(self,write=False):
        conn=self._connect()
        try:
            conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _events(self,conn):
        records=conn.execute('SELECT seq,kind,payload,prev_sha256,event_sha256 FROM events ORDER BY seq').fetchall()
        prev=ZERO
        for index,(seq,kind,payload,ph,digest) in enumerate(records,1):
            if seq!=index or ph!=prev:
                refuse('E_AUDIT','audit ledger sequence or parent mismatch')
            obj=loads(payload)
            if _json(obj)!=payload:
                refuse('E_AUDIT','noncanonical event payload')
            expected=sha256({'seq':seq,'kind':kind,'payload':obj,'prev_sha256':prev})
            if expected!=digest:
                refuse('E_AUDIT','audit event content digest mismatch')
            prev=digest
        return records,prev

    def _append(self,conn,kind,payload):
        records,prev=self._events(conn)
        seq=len(records)+1
        digest=sha256({'seq':seq,'kind':kind,'payload':payload,'prev_sha256':prev})
        conn.execute('INSERT INTO events(seq,kind,payload,prev_sha256,event_sha256) VALUES(?,?,?,?,?)',
                     (seq,kind,_json(payload),prev,digest))
        return digest

    def _project(self,conn):
        records,head=self._events(conn)
        installed=set();revoked=set();stale=set();active=None;history=[]
        for _,kind,payload,_,_ in records:
            item=loads(payload)
            cid=item.get('candidate_sha256')
            if kind=='INSTALL':
                if cid in installed: refuse('E_AUDIT','duplicate install in audit')
                installed.add(cid)
            elif kind in ('ACTIVATE','ROLLBACK'):
                if cid not in installed or cid in revoked or cid in stale:
                    refuse('E_AUDIT','audit activates missing or prohibited artifact')
                active=cid
                history.append(cid)
            elif kind=='DISABLE':
                active=None
            elif kind=='REVOKE':
                if cid not in installed or cid in revoked: refuse('E_AUDIT','invalid revocation event')
                revoked.add(cid)
                if active==cid: active=None
            elif kind=='STALE':
                if cid not in installed: refuse('E_AUDIT','stale unknown candidate')
                stale.add(cid)
                if active==cid: active=None
            elif kind in ('EXECUTE','REFUSED'):
                pass
            else:
                refuse('E_AUDIT','unsupported recorded event')
        ids={r[0] for r in conn.execute('SELECT candidate_sha256 FROM artifacts')}
        if ids!=installed:
            refuse('E_AUDIT','installed artifact records do not match event log')
        return {'installed':installed,'revoked':revoked,'stale':stale,
                'active':active,'history':history,'head':head,'events':len(records)}

    def _artifact(self,conn,cid):
        row=conn.execute('SELECT manifest,binary,evidence,approval FROM artifacts WHERE candidate_sha256=?',(cid,)).fetchone()
        if row is None: refuse('E_NOT_INSTALLED','candidate has not been installed in local simulation')
        candidate=loads(row[0]); binary=bytes(row[1]); evidence=bytes(row[2]); receipt=loads(row[3])
        validate_candidate(candidate,binary,evidence)
        if candidate['candidate_sha256']!=cid: refuse('E_INTEGRITY','artifact identifier mismatch')
        return candidate,binary,evidence,receipt

    def _live(self,conn,cid,trusted_issuers,now_utc,current_baselines):
        candidate,binary,_,approval=self._artifact(conn,cid)
        verify_approval(candidate,approval,trusted_issuers,now_utc)
        _baselines(current_baselines)
        if candidate['baseline_versions']!=current_baselines:
            refuse('E_STALE','host baseline versions differ from signed candidate; review required')
        return candidate,binary

    def _log_refusal(self,operation,cid,code,now_utc):
        with self._tx(write=True) as conn:
            self._project(conn)
            self._append(conn,'REFUSED',{'operation':operation,'candidate_sha256':cid,
                                       'refusal_code':code,'at_utc':now_utc})

    @_record_denials('INSTALL')
    def install(self,candidate,binary,evidence,receipt,*,trusted_issuers,now_utc,current_baselines):
        timestamp(now_utc)
        validate_candidate(candidate,binary,evidence)
        verify_approval(candidate,receipt,trusted_issuers,now_utc)
        _baselines(current_baselines)
        if candidate['baseline_versions']!=current_baselines:
            refuse('E_STALE','install refused for changed source baseline')
        cid=candidate['candidate_sha256']
        with self._tx(write=True) as conn:
            state=self._project(conn)
            if cid in state['installed']: refuse('E_DUPLICATE','candidate already installed')
            conn.execute('INSERT INTO artifacts VALUES(?,?,?,?,?)',
                         (cid,_json(candidate),binary,evidence,_json(receipt)))
            head=self._append(conn,'INSTALL',{'candidate_sha256':cid,'at_utc':now_utc,
                                               'scope':candidate['scope']})
        return {'state':'INSTALLED_IN_SIMULATION','candidate_sha256':cid,'audit_head':head,
                'production_body_authorized':False}

    @_record_denials('ACTIVATE')
    def activate(self,cid,*,trusted_issuers,now_utc,current_baselines):
        timestamp(now_utc)
        with self._tx(write=True) as conn:
            state=self._project(conn)
            if cid not in state['installed']: refuse('E_NOT_INSTALLED','candidate not installed')
            if cid in state['revoked']: refuse('E_REVOKED','candidate revoked')
            if cid in state['stale']: refuse('E_STALE','candidate quarantined for review')
            self._live(conn,cid,trusted_issuers,now_utc,current_baselines)
            if state['active']==cid: refuse('E_DUPLICATE','candidate already active')
            head=self._append(conn,'ACTIVATE',{'candidate_sha256':cid,'at_utc':now_utc})
        return {'state':'ACTIVE_IN_SIMULATION','candidate_sha256':cid,'audit_head':head,
                'production_body_authorized':False}

    @_record_denials('DISABLE')
    def disable(self,*,now_utc):
        timestamp(now_utc)
        with self._tx(write=True) as conn:
            state=self._project(conn)
            if state['active'] is None: refuse('E_NOT_ACTIVE','nothing to disable')
            head=self._append(conn,'DISABLE',{'candidate_sha256':state['active'],'at_utc':now_utc})
        return {'state':'DISABLED','audit_head':head}

    @_record_denials('REVOKE')
    def revoke(self,cid,*,now_utc):
        timestamp(now_utc)
        with self._tx(write=True) as conn:
            state=self._project(conn)
            if cid not in state['installed']: refuse('E_NOT_INSTALLED','cannot revoke absent candidate')
            if cid in state['revoked']: refuse('E_REVOKED','already revoked')
            head=self._append(conn,'REVOKE',{'candidate_sha256':cid,'at_utc':now_utc})
        return {'state':'REVOKED','audit_head':head}

    @_record_denials('ROLLBACK')
    def rollback(self,target,*,trusted_issuers,now_utc,current_baselines):
        timestamp(now_utc)
        with self._tx(write=True) as conn:
            state=self._project(conn)
            if target not in state['history'] or target==state['active']:
                refuse('E_ROLLBACK','target must be a previously activated different revision')
            if target in state['revoked']: refuse('E_REVOKED','cannot roll back to revoked revision')
            if target in state['stale']: refuse('E_STALE','cannot roll back to stale revision')
            self._live(conn,target,trusted_issuers,now_utc,current_baselines)
            head=self._append(conn,'ROLLBACK',{'candidate_sha256':target,'at_utc':now_utc})
        return {'state':'ROLLED_BACK_IN_SIMULATION','candidate_sha256':target,
                'audit_head':head,'production_body_authorized':False}

    def _quarantine(self,cid,at_utc):
        with self._tx(write=True) as conn:
            state=self._project(conn)
            if cid in state['installed'] and cid not in state['stale']:
                self._append(conn,'STALE',{'candidate_sha256':cid,'at_utc':at_utc,
                                           'reason_code':'E_STALE'})

    @_record_denials('RUN')
    def run_active(self,input_source,*,trusted_issuers,now_utc,current_baselines):
        timestamp(now_utc)
        with self._tx() as conn:
            state=self._project(conn)
            cid=state['active']
            if cid is None: refuse('E_NOT_ACTIVE','no active local revision')
            if cid in state['revoked']: refuse('E_REVOKED','revision revoked')
            if cid in state['stale']: refuse('E_STALE','revision quarantined')
            try:
                candidate,binary=self._live(conn,cid,trusted_issuers,now_utc,current_baselines)
            except ReflexError as exc:
                if exc.code=='E_STALE':
                    # End read transaction before writing permanent stale event.
                    quarantine=True
                else:
                    raise
            else:
                quarantine=False
        if quarantine:
            self._quarantine(cid,now_utc)
            refuse('E_STALE','active revision quarantined pending fresh review')
        trace=vm_run(binary,input_source)
        with self._tx(write=True) as conn:
            current=self._project(conn)
            if current['active']!=cid: refuse('E_NOT_ACTIVE','active revision changed during evaluation')
            self._live(conn,cid,trusted_issuers,now_utc,current_baselines)
            self._append(conn,'EXECUTE',{'candidate_sha256':cid,'at_utc':now_utc,
                                        'input_sha256':trace['input_sha256'],
                                        'trace_sha256':sha256(trace)})
        return {'schema':'mantle.reflex-simulated-run/0.1','state':'EXECUTED_IN_SIMULATION',
                'candidate_sha256':cid,'trace':trace,'production_body_authorized':False}

    def audit(self):
        with self._tx() as conn:
            state=self._project(conn)
            for cid in state['installed']:
                self._artifact(conn,cid)
        return {'schema':'mantle.reflex-registry-audit/0.1','status':'VERIFIED_LOCAL_CHAIN',
                'event_count':state['events'],'head_sha256':state['head'],
                'active_candidate_sha256':state['active'],
                'installed_count':len(state['installed']),
                'revoked_count':len(state['revoked']),
                'stale_count':len(state['stale']),
                'production_body_authorized':False}
