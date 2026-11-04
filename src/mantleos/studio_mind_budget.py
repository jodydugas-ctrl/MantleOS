"""Trusted-host provider attempt accounting; never a model authority interface.

Reservations survive process failure and owner-file/key changes. Unknown network
outcomes retain their entire reservation. This is a local spending guard, not an
independent witness or protection against administrator rollback/tampering.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time

APP_ID = 0x414D4247
SCHEMA = 2
MAX_RESULT_BYTES = 262144


def _canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canon(value).encode('utf8')).hexdigest()


def _amount(value):
    if type(value) is not int or not 0 <= value <= 2**53-1:
        raise ValueError('Exact nonnegative microdollar amount required')
    return value


def _text(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        raise ValueError('Bounded nonempty identifier required')
    return value


class AttemptConflict(ValueError):
    pass


class MindBudget:
    """One owner-selected operational database, shared by NESTs and limb workers.

    Caller methods are trusted controller interfaces, never public JSON commands.
    A claim token only prevents cooperating workers from mixing attempts; it is
    not an owner approval, a capability grant, or an isolation boundary.
    """

    def __init__(self, path, *, create=False):
        self.path = Path(path).absolute()
        self._paths()
        if not self.path.exists() and not create:
            raise FileNotFoundError('MIND accounting requires explicit initialization')
        with self._db(create=create) as db:
            if create and db.execute('PRAGMA application_id').fetchone()[0] == 0:
                if db.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]:
                    raise ValueError('Refusing unrelated accounting database')
                db.executescript('''
                    BEGIN IMMEDIATE;
                    PRAGMA application_id=1095582279;
                    PRAGMA user_version=1;
                    CREATE TABLE attempts (
                      purpose TEXT NOT NULL, request_id TEXT NOT NULL,
                      binding TEXT NOT NULL, token TEXT NOT NULL,
                      state TEXT NOT NULL, reserved INTEGER NOT NULL,
                      charged INTEGER, result TEXT, result_sha256 TEXT,
                      created_ns INTEGER NOT NULL, updated_ns INTEGER NOT NULL,
                      PRIMARY KEY(purpose, request_id),
                      CHECK(purpose IN ('mind','limbs')),
                      CHECK(state IN ('RESERVED','SENT','RESULT','ADMITTED','UNKNOWN')),
                      CHECK(reserved>=0), CHECK(charged IS NULL OR charged>=0));
                    COMMIT;
                ''')
            # Only explicit initialization/configuration may upgrade the old
            # accounting schema. Attempts and their conservative holds survive.
            if create and db.execute('PRAGMA user_version').fetchone()[0] == 1:
                if db.execute('PRAGMA application_id').fetchone()[0] != APP_ID:
                    raise ValueError('Unsupported MIND accounting database')
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE accounting_identity (id TEXT PRIMARY KEY)')
                db.execute('INSERT INTO accounting_identity VALUES(?)', (secrets.token_hex(32),))
                db.execute('PRAGMA user_version=2')
                db.commit()
            self._schema(db)

    def identity(self):
        """Opaque local account binding; neither a key nor authentication."""
        with self._db() as db:
            self._schema(db)
            rows = db.execute('SELECT id FROM accounting_identity').fetchall()
            if (len(rows) != 1 or not isinstance(rows[0][0], str) or
                    len(rows[0][0]) != 64 or any(c not in '0123456789abcdef' for c in rows[0][0])):
                raise ValueError('Invalid MIND accounting identity')
            return rows[0][0]

    def _paths(self):
        for candidate in (self.path, *self.path.parents):
            if candidate.is_symlink() or (candidate.exists() and
                    getattr(candidate, 'is_junction', lambda: False)()):
                raise PermissionError('MIND accounting cannot use linked storage')
        for suffix in ('-wal', '-shm', '-journal'):
            candidate = Path(str(self.path)+suffix)
            if candidate.is_symlink() or getattr(candidate, 'is_junction', lambda: False)():
                raise PermissionError('MIND accounting cannot use linked sidecars')

    @contextmanager
    def _db(self, *, create=False):
        self._paths()
        db = sqlite3.connect(self.path.as_uri()+('?mode=rwc' if create else '?mode=rw'),
                             uri=True, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA busy_timeout=10000')
            if create:
                db.execute('PRAGMA journal_mode=WAL')
            yield db
        finally:
            if db.in_transaction:
                db.rollback()
            db.close()

    def _schema(self, db):
        if (db.execute('PRAGMA application_id').fetchone()[0] != APP_ID or
                db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA):
            raise ValueError('Unsupported MIND accounting database')

    @contextmanager
    def _write(self):
        with self._db() as db:
            self._schema(db)
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()

    @staticmethod
    def _exposure(db, purpose):
        return db.execute('''SELECT COALESCE(SUM(CASE WHEN charged IS NULL
            THEN reserved ELSE MAX(reserved,charged) END),0) FROM attempts
            WHERE purpose=?''', (purpose,)).fetchone()[0]

    def status(self, caps):
        """No keys, route fingerprints, frame content, or proposals in status."""
        if set(caps) != {'mind', 'limbs'}:
            raise ValueError('Separate MIND and combined limb caps required')
        with self._db() as db:
            self._schema(db)
            output = {}
            for purpose, cap in caps.items():
                _amount(cap)
                exposure = self._exposure(db, purpose)
                states = {r[0]: r[1] for r in db.execute(
                    'SELECT state,count(*) FROM attempts WHERE purpose=? GROUP BY state', (purpose,))}
                output[purpose] = dict(cap_micro_usd=cap, encumbered_micro_usd=exposure,
                    remaining_micro_usd=max(0,cap-exposure), attempts=states)
            return dict(period='TOTAL_NO_AUTOMATIC_RESET', accounts=output)

    def reserve(self, *, purpose, request_id, binding, maximum_micro_usd, cap_micro_usd):
        """Reserve before any network effect; a duplicate never grants a new send.

        Binding must cover frame, controller source, owner configuration, route
        and policy. Budget account identity deliberately excludes all of those,
        so changing them never resets accumulated exposure.
        """
        if purpose not in ('mind', 'limbs'):
            raise ValueError('Unknown MIND budget account')
        _text(request_id)
        if not isinstance(binding, dict) or set(binding) != {
                'frame_sha256','source_sha256','config_sha256','route_sha256','policy_sha256'}:
            raise ValueError('Complete source, frame, configuration, route and policy binding required')
        if any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v)
               for v in binding.values()):
            raise ValueError('Canonical digest bindings required')
        _amount(maximum_micro_usd); _amount(cap_micro_usd)
        bound = _digest(binding)
        with self._write() as db:
            old = db.execute('SELECT * FROM attempts WHERE purpose=? AND request_id=?',
                             (purpose,request_id)).fetchone()
            if old:
                if old['binding'] != bound:
                    raise AttemptConflict('Request has a different provider preparation')
                return {'status':old['state'], 'new':False}
            if self._exposure(db,purpose)+maximum_micro_usd > cap_micro_usd:
                raise PermissionError('Persistent MIND spending cap exhausted')
            token = secrets.token_hex(32)
            now = time.time_ns()
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (purpose,request_id,bound,token,'RESERVED',maximum_micro_usd,
                        None,None,None,now,now))
            return {'status':'RESERVED','new':True,'claim':token}

    def sent(self, *, purpose, request_id, claim):
        """Persist SENT before transport; failure leaves an uncertain held claim."""
        with self._write() as db:
            cursor = db.execute('''UPDATE attempts SET state='SENT',updated_ns=?
                WHERE purpose=? AND request_id=? AND token=? AND state='RESERVED' ''',
                (time.time_ns(),purpose,request_id,claim))
            if cursor.rowcount != 1:
                raise AttemptConflict('Provider attempt cannot be sent again')

    def result(self, *, purpose, request_id, claim, value, cost_micro_usd=None):
        """Record transport result BEFORE Journal admission, without freeing reserve.

        Provider cost is telemetry, not trusted permission to release credit.
        The conservative maximum remains encumbered even for a zero-cost result;
        missing or over-limit billing blocks further spending as appropriate.
        """
        encoded = _canon(value)
        if not isinstance(value,dict) or len(encoded.encode('utf8')) > MAX_RESULT_BYTES:
            raise ValueError('Bounded provider result object required')
        if cost_micro_usd is not None:
            _amount(cost_micro_usd)
        with self._write() as db:
            cursor = db.execute('''UPDATE attempts SET state='RESULT',result=?,result_sha256=?,
                charged=?,updated_ns=? WHERE purpose=? AND request_id=? AND token=? AND state='SENT' ''',
                (encoded,hashlib.sha256(encoded.encode('utf8')).hexdigest(),cost_micro_usd,
                 time.time_ns(),purpose,request_id,claim))
            if cursor.rowcount != 1:
                raise AttemptConflict('Provider result does not match an in-flight claim')

    def retained_result(self, *, purpose, request_id, binding):
        """Trusted-host recovery only. A retained result never causes another call."""
        with self._db() as db:
            self._schema(db)
            row=db.execute('SELECT * FROM attempts WHERE purpose=? AND request_id=?',
                           (purpose,request_id)).fetchone()
            if row is None:
                raise KeyError('Unknown provider attempt')
            if row['binding'] != _digest(binding):
                raise AttemptConflict('Provider result preparation changed')
            if row['state'] not in ('RESULT','ADMITTED'):
                return {'status':'NEEDS_REVIEW','attempt_state':row['state']}
            if (not row['result'] or hashlib.sha256(row['result'].encode('utf8')).hexdigest()
                    != row['result_sha256']):
                raise ValueError('Corrupt retained provider result')
            return {'status':row['state'],'value':json.loads(row['result']),'claim':row['token']}

    def admitted(self, *, purpose, request_id, claim):
        """Call only after Body admission; this flag itself never authorizes release."""
        with self._write() as db:
            cursor=db.execute('''UPDATE attempts SET state='ADMITTED',updated_ns=?
                WHERE purpose=? AND request_id=? AND token=? AND state='RESULT' ''',
                (time.time_ns(),purpose,request_id,claim))
            if cursor.rowcount != 1:
                raise AttemptConflict('No matching retained result to mark admitted')
