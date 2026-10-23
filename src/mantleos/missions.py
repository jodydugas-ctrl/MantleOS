"""Operator-owned standing policies and durable, bounded representative missions.

The database belongs to the resident host, never to a portable representative.
This is a cooperating-local-process boundary, not a sandbox or remote scheduler.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid

from . import appai, compiled, engram, json_contract as contract, lifecycle, specimens
from .transactions import body_lock

ACTIVE = {'CREATING', 'READY', 'RUNNING', 'RETURNED'}


class _ExpiredOrRevoked(PermissionError):
    """Only these policy failures retire a pending mission during recovery."""


@contextmanager
def _db(nest):
    path = Path(nest).resolve() / 'mantle/private/missions.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5, isolation_level=None)
    db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE IF NOT EXISTS policy (id TEXT PRIMARY KEY, value TEXT NOT NULL, revoked INTEGER NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS mission (id TEXT PRIMARY KEY, request TEXT UNIQUE NOT NULL, value TEXT NOT NULL)')
    try:
        yield db
    finally:
        db.close()


def _put(db, value):
    db.execute('INSERT OR REPLACE INTO mission VALUES (?,?,?)',
               (value['id'], value['request_id'], contract.canonical(value)))


def _get(db, mission_id):
    contract.identifier(mission_id)
    row = db.execute('SELECT value FROM mission WHERE id=?', (mission_id,)).fetchone()
    if not row:
        raise ValueError('Unknown mission')
    return contract.loads(row[0])


def _policy(db, policy_id, *, now):
    row = db.execute('SELECT value,revoked FROM policy WHERE id=?', (policy_id,)).fetchone()
    if not row or row[1]:
        raise _ExpiredOrRevoked('Mission policy revoked or absent')
    value = contract.loads(row[0])
    if now >= value['expires_at']:
        raise _ExpiredOrRevoked('Mission policy expired')
    return value


def authorize(nest, source, representatives, *, approved=False, ttl=3600, duration=60, now=None):
    if approved is not True:
        raise PermissionError('Standing policy requires operator authorization')
    if type(ttl) is not int or not 1 <= ttl <= 86400 or type(duration) is not int or not 1 <= duration <= 300:
        raise ValueError('Policy time limits exceed bounds')
    root, target, work = Path(nest).resolve(), Path(source).resolve(), Path(representatives).resolve()
    if not target.is_dir() or Path(source).is_symlink():
        raise ValueError('Invalid specimen directory')
    private = root / 'mantle/private'
    if any(a.is_relative_to(b) or b.is_relative_to(a) for a, b in ((target, private), (work, root), (work, target))):
        raise ValueError('Specimen and representative NESTs must not expose or overlap resident private state')
    with body_lock(root):
        state = appai.status(root)
        if state['phase'] == 'UNBORN':
            raise ValueError('Birth required before mission policy')
        if compiled.read_json(appai.body(root) / 'EXPRESSION.json').get('mission'):
            raise PermissionError('Recursive delegation is forbidden')
        value = {'schema': 'mantle.mission-policy/1', 'id': 'policy-' + uuid.uuid4().hex,
                 'parent': compiled.read_json(appai.body(root) / 'BIRTH.json')['id'],
                 'source': str(target), 'representatives': str(work), 'capability': 'specimen.inspect',
                 'max_active': 1, 'recursive': False, 'duration': duration,
                 'expires_at': (time.time() if now is None else now) + ttl}
        with _db(root) as db:
            db.execute('INSERT INTO policy VALUES (?,?,0)', (value['id'], contract.canonical(value)))
        return value


def revoke(nest, policy_id):
    with body_lock(nest), _db(nest) as db:
        if not db.execute('SELECT id FROM policy WHERE id=?', (policy_id,)).fetchone():
            raise ValueError('Unknown policy')
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE policy SET revoked=1 WHERE id=?', (policy_id,))
        for row in db.execute('SELECT value FROM mission').fetchall():
            value = contract.loads(row[0])
            if value['policy_id'] == policy_id and value['phase'] in ACTIVE:
                value['phase'] = 'REVOKED'; _put(db, value)
        db.execute('COMMIT')
        return {'result': 'REVOKED', 'policy_id': policy_id, 'remote_cancellation_claimed': False}


def inspect(nest, mission_id):
    with _db(nest) as db:
        return _get(db, mission_id)


def dispatch(nest, policy_id, *, request_id, context=None, now=None):
    contract.identifier(request_id)
    context = context or {}
    contract.canonical(context, limit=16384)
    root = Path(nest).resolve()
    with body_lock(root), _db(root) as db:
        if appai.status(root)['phase'] != 'ACTIVE':
            raise PermissionError('Resident AppAI must be active')
        at = time.time() if now is None else now
        policy = _policy(db, policy_id, now=at)
        request_digest = contract.digest({'policy': policy_id, 'context': context})
        existing = db.execute('SELECT value FROM mission WHERE request=?', (request_id,)).fetchone()
        if existing:
            value = contract.loads(existing[0])
            if value['request_sha256'] != request_digest:
                raise ValueError('Duplicate request has different content')
            return value
        for row in db.execute('SELECT value FROM mission').fetchall():
            if contract.loads(row[0])['phase'] in ACTIVE:
                raise PermissionError('One active representative at a time; recover or finish the existing mission')
        mid = 'm-' + uuid.uuid4().hex[:24]
        child = Path(policy['representatives']) / mid / 'body'
        value = {'schema': 'mantle.mission/1', 'id': mid, 'request_id': request_id,
                 'request_sha256': request_digest, 'policy_id': policy_id, 'phase': 'CREATING',
                 'body': str(child), 'source': policy['source'], 'context': context,
                 'deadline': min(policy['expires_at'], at + policy['duration'])}
        _put(db, value)  # Durable intent before construction; never silently dispatch twice.
        specimens.representative(appai.body(root), child, mid, context=context, policy_id=policy_id)
        value['phase'] = 'READY'; _put(db, value)
        return value


def _live(nest, db, value, now, *, require_active=True):
    state = appai.status(nest)  # Verify the resident host even for offline recovery.
    if require_active and state['phase'] != 'ACTIVE':
        raise PermissionError('Resident AppAI is not active')
    policy = _policy(db, value['policy_id'], now=now)
    if now >= value['deadline']:
        raise _ExpiredOrRevoked('Mission expired')
    if policy['source'] != value['source']:
        raise PermissionError('Mission target differs from standing policy')
    return policy


def run(nest, mission_id):
    root = Path(nest).resolve()
    with body_lock(root), _db(root) as db:
        value = _get(db, mission_id)
        _live(root, db, value, time.time())
        if value['phase'] == 'RETURNED':
            return value
        if value['phase'] != 'READY':
            raise ValueError('Mission is not dispatchable; inspect or recover it')
        value['phase'] = 'RUNNING'; _put(db, value)
    output = Path(value['body']).parent / 'observation'
    # Only the scanner executes. Specimen content is data, never subprocess code.
    environment = {k: os.environ[k] for k in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP') if k in os.environ}
    environment['PYTHONPATH'] = str(Path(__file__).resolve().parent.parent)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        remaining = value['deadline'] - time.time()
        if remaining <= 0:
            raise TimeoutError('Mission expired before worker start')
        result = subprocess.run([sys.executable, '-S', '-m', 'mantleos.observer', value['source'], str(output)],
                                env=environment, timeout=remaining, capture_output=True, text=True)
        if result.returncode:
            raise ValueError('Observation failed: ' + result.stderr[-1000:])
        report = contract.loads((output / 'observation.json').read_text('utf-8'))
        report_hash = contract.digest(report)
        with body_lock(root), _db(root) as db:
            current = _get(db, mission_id)
            _live(root, db, current, time.time())
            if current['phase'] != 'RUNNING':
                raise PermissionError('Mission was revoked or recovered while worker ran')
            compiled.load(current['body'])
            lifecycle.admit(current['body'], 'mission-observation', {'mission': mission_id, 'report': report},
                            expected_head=engram.head(Path(current['body']) / 'ENGRAM.jsonl'))
            current.update(phase='RETURNED', report=report, report_sha256=report_hash)
            _put(db, current)
            return current
    except Exception as exc:
        with body_lock(root), _db(root) as db:
            current = _get(db, mission_id)
            if current['phase'] == 'RUNNING':
                current.update(phase='FAILED', error=str(exc)[:1024]); _put(db, current)
        raise


def review(nest, mission_id):
    value = inspect(nest, mission_id)
    if value['phase'] not in {'RETURNED', 'ADMITTED'}:
        raise ValueError('Mission has no admissible result')
    if contract.digest(value['report']) != value['report_sha256']:
        raise ValueError('Mission result digest mismatch')
    return {'mission': mission_id, 'report': value['report'], 'sha256': value['report_sha256'], 'authorized': False}


def admit(nest, mission_id, *, approval):
    root = Path(nest).resolve()
    with body_lock(root), _db(root) as db:
        value = _get(db, mission_id)
        _live(root, db, value, time.time())
        report = review(root, mission_id)
        if approval != report['sha256']:
            raise PermissionError('Admission requires the exact reviewed result digest')
        target = appai.body(root)
        records = engram.read(target / 'ENGRAM.jsonl')
        previous = [r for r in records if r['type'] == 'mission-return' and r['body']['mission'] == mission_id]
        if previous:
            if previous[-1]['body']['report_sha256'] != approval:
                raise ValueError('Conflicting result already admitted')
        else:
            compiled.load(value['body'])
            payload = {'mission': mission_id, 'representative': compiled.read_json(Path(value['body']) / 'BIRTH.json')['id'],
                       'report_sha256': approval, 'source': value['source'],
                       'snapshot_sha256': report['report']['snapshot']['sha256'],
                       'changed_paths': report['report']['changed_paths'],
                       'evidence': report['report']['evidence']}
            lifecycle.admit(target, 'mission-return', payload, expected_head=engram.head(target / 'ENGRAM.jsonl'))
        value['phase'] = 'ADMITTED'; _put(db, value)
        return {'result': 'ADMITTED', 'mission': mission_id, 'replay': bool(previous)}


def recover(nest, mission_id):
    """Explicit recovery never starts another worker or guesses an external result."""
    with body_lock(nest), _db(nest) as db:
        value = _get(db, mission_id)
        try:
            # Stasis prevents execution/admission, but does not revoke evidence.
            _live(nest, db, value, time.time(), require_active=False)
        except _ExpiredOrRevoked:
            if value['phase'] in ACTIVE:
                value['phase'] = 'EXPIRED_OR_REVOKED'
        else:
            if value['phase'] == 'CREATING':
                if Path(value['body']).is_dir():
                    compiled.load(value['body']); value['phase'] = 'READY'
                else:
                    value['phase'] = 'INTERRUPTED'
            elif value['phase'] == 'RUNNING':
                value['phase'] = 'INTERRUPTED'
        _put(db, value)
        return value
