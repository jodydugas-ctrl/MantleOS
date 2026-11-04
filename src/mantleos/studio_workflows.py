"""Operational workflow drafts and retained versions, owned by N-WORKFLOW.

These are application documents, not Engram records or Anchor instructions.
Import/save never deploys a flow. Runtime publication is a separate checked
effect; a saved document cannot declare itself active or supply authority.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote
import uuid

from . import json_contract as c

APPLICATION = 0x41575346
VERSION = 1
MAX_BYTES = 16 * 1024 * 1024
SERVER_FIELDS = {'id', 'revision', 'versionId', 'activeVersionId', 'active',
                 'isArchived', 'createdAt', 'updatedAt', 'versionCounter', 'triggerCount'}


class Conflict(ValueError):
    """The caller must retain its draft and deliberately reconcile newer state."""


def _token():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def _encoded(value, limit=MAX_BYTES):
    return c.canonical(value, limit=limit)


def _digest(value, limit=MAX_BYTES):
    return hashlib.sha256(_encoded(value, limit).encode('utf-8')).hexdigest()


def _id(value):
    c.text(value, maximum=128)
    c.require(all(x.isalnum() or x in '_.:-' for x in value), 'Invalid workflow/node identifier')
    return value


def document(value):
    """Validate graph references; node-type admission belongs to the runtime.

    Unknown node types/parameters are retained for review, never executed here.
    n8n-shaped item links, AI connection types and cycles remain representable.
    """
    c.require(type(value) is dict, 'Workflow must be an object')
    _encoded(value)
    result = {key: item for key, item in value.items() if key not in SERVER_FIELDS}
    c.text(result.get('name'), maximum=512)
    c.require(len(result['name']) <= 128, 'Workflow name exceeds 128 characters')
    nodes = result.setdefault('nodes', [])
    connections = result.setdefault('connections', {})
    c.require(type(nodes) is list and len(nodes) <= 10000, 'Invalid workflow nodes')
    c.require(type(connections) is dict, 'Invalid workflow connections')
    names, identifiers = set(), set()
    for node in nodes:
        c.require(type(node) is dict, 'Node must be an object')
        _id(node.get('id')); c.text(node.get('name'), maximum=512)
        c.text(node.get('type'), maximum=256)
        c.require(node['id'] not in identifiers and node['name'] not in names, 'Duplicate node id/name')
        identifiers.add(node['id']); names.add(node['name'])
        position = node.get('position')
        c.require(type(position) is list and len(position) == 2 and
                  all(type(n) in (int, float) and math.isfinite(n) for n in position), 'Invalid node position')
        c.require(type(node.get('parameters', {})) is dict, 'Invalid node parameters')
        version = node.get('typeVersion', 1)
        c.require(type(version) in (int, float) and math.isfinite(version) and version > 0, 'Invalid node type version')
        if 'disabled' in node:
            c.require(type(node['disabled']) is bool, 'Invalid node disabled flag')
        if 'credentials' in node:
            c.require(type(node['credentials']) is dict, 'Credentials must be references')
            for ref in node['credentials'].values():
                c.require(type(ref) is dict and set(ref) <= {'id', 'name'} and bool(ref), 'Only credential references belong in workflows')
                for entry in ref.values():
                    c.require(entry is None or type(entry) is str, 'Invalid credential reference')
    for source, ports in connections.items():
        c.require(source in names and type(ports) is dict, 'Unknown connection source')
        for port, outputs in ports.items():
            c.text(port, maximum=128)
            c.require(type(outputs) is list, 'Invalid output ports')
            for targets in outputs:
                c.require(type(targets) is list, 'Invalid output connections')
                for target in targets:
                    c.shape(target, {'node', 'type', 'index'})
                    c.require(target['node'] in names, 'Unknown connection destination')
                    c.text(target['type'], maximum=128)
                    c.require(type(target['index']) is int and 0 <= target['index'] <= 10000, 'Invalid destination port')
    for key in ('settings', 'pinData'):
        c.require(type(result.setdefault(key, {})) is dict, 'Invalid workflow '+key)
    c.require(set(result['pinData']) <= names, 'Unknown pinned node')
    # A JSON copy prevents the caller from mutating an already validated document.
    return json.loads(_encoded(result))


class WorkflowStore:
    """Durable drafts. A trusted host must independently authorize mutations."""
    def __init__(self, directory):
        directory = Path(directory)
        for path in (directory, directory/'workflows.sqlite'):
            if path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
                raise ValueError('Workflow storage may not be a reparse point')
        self.directory = directory.resolve()
        self.path = self.directory/'workflows.sqlite'

    @contextmanager
    def _db(self, write=False):
        for path in (self.directory, self.path):
            if path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
                raise ValueError('Workflow storage may not be a reparse point')
        if not self.path.exists() and not write:
            yield None
            return
        if write:
            self.directory.mkdir(parents=True, exist_ok=True)
        uri = 'file:'+quote(self.path.as_posix(), safe='/:')+'?mode='+('rwc' if write else 'ro')
        db = sqlite3.connect(uri, uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON')
            if write:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            app = db.execute('PRAGMA application_id').fetchone()[0]
            version = db.execute('PRAGMA user_version').fetchone()[0]
            empty = not db.execute("SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone()
            if write and app == version == 0 and empty:
                for sql in (
                    'CREATE TABLE workflows(id TEXT PRIMARY KEY,revision TEXT NOT NULL,version TEXT NOT NULL,active_version TEXT,archived INTEGER NOT NULL DEFAULT 0,deleted INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL)',
                    'CREATE TABLE versions(id TEXT PRIMARY KEY,workflow TEXT NOT NULL REFERENCES workflows(id),parent TEXT,content TEXT NOT NULL,sha256 TEXT NOT NULL,created TEXT NOT NULL)',
                    'CREATE TABLE requests(id TEXT PRIMARY KEY,sha256 TEXT NOT NULL,reply TEXT NOT NULL)',
                    'CREATE INDEX workflow_versions ON versions(workflow,created)',
                ):
                    db.execute(sql)
                db.execute('PRAGMA application_id='+str(APPLICATION))
                db.execute('PRAGMA user_version='+str(VERSION))
                # Bootstrap must remain a usable empty store if the first request
                # fails or is interrupted. The request itself has its own atomic
                # transaction and never partially advances a workflow version.
                db.commit()
                db.execute('BEGIN IMMEDIATE')
            else:
                c.require(app == APPLICATION and version == VERSION, 'Unsupported workflow store; explicit recovery/migration required')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _row(self, db, workflow_id, include_deleted=False):
        _id(workflow_id)
        row = db.execute('SELECT * FROM workflows WHERE id=?', (workflow_id,)).fetchone() if db else None
        if row is None or (row['deleted'] and not include_deleted):
            raise KeyError('Workflow not found')
        return row

    def _version(self, db, workflow_id, version_id):
        record = db.execute('SELECT * FROM versions WHERE id=? AND workflow=?', (version_id, workflow_id)).fetchone()
        c.require(record is not None, 'Missing workflow version')
        value = json.loads(record['content'])
        c.require(_digest(value) == record['sha256'], 'Workflow version integrity failed')
        return value

    def _view(self, db, row):
        value = self._version(db, row['id'], row['version'])
        return {**value, 'id': row['id'], 'revision': row['revision'], 'versionId': row['version'],
                'activeVersionId': row['active_version'], 'active': row['active_version'] is not None,
                'isArchived': bool(row['archived']), 'createdAt': row['created'], 'updatedAt': row['updated']}

    def get(self, workflow_id):
        with self._db() as db:
            return self._view(db, self._row(db, workflow_id))

    def list(self, *, search='', archived=False, offset=0, limit=100):
        c.text(search, maximum=512, blank=True)
        c.require(archived is None or type(archived) is bool, 'Invalid archive filter')
        c.require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= 200, 'Invalid pagination')
        with self._db() as db:
            rows = db.execute('SELECT * FROM workflows WHERE deleted=0 ORDER BY updated DESC,id').fetchall() if db else []
            values = [self._view(db, row) for row in rows if archived is None or bool(row['archived']) == archived]
            values = [v for v in values if search.casefold() in v['name'].casefold()]
            return {'data': values[offset:offset+limit], 'count': len(values)}

    def history(self, workflow_id):
        with self._db() as db:
            self._row(db, workflow_id)
            rows = db.execute('SELECT id,parent,sha256,created FROM versions WHERE workflow=? ORDER BY rowid DESC', (workflow_id,)).fetchall()
            # Check every retained snapshot before reporting it as usable history.
            for row in rows:
                self._version(db, workflow_id, row['id'])
            for index, row in enumerate(rows):
                parent = rows[index+1]['id'] if index+1 < len(rows) else None
                c.require(row['parent'] == parent, 'Workflow version ancestry failed')
            return [dict(row) for row in rows]

    def mutate(self, request, *, owner=False):
        # Authority is host-supplied, not a field in the request or an Anchor digest.
        if owner is not True:
            raise PermissionError('Independent owner workflow authority required')
        c.require(type(request) is dict, 'Invalid workflow request')
        c.identifier(request.get('request_id'))
        action = request.get('action')
        fields = {'create': {'value'}, 'update': {'id', 'revision', 'value'},
                  'duplicate': {'id', 'revision', 'name'}, 'archive': {'id', 'revision'},
                  'unarchive': {'id', 'revision'}, 'delete': {'id', 'revision'},
                  'restore': {'id', 'revision', 'versionId'}}
        c.require(action in fields, 'Unsupported workflow mutation; save is not deployment')
        expected = {'action', 'request_id'} | fields[action]
        if action == 'create' and 'id' in request:
            expected.add('id')
            _id(request['id'])
        c.shape(request, expected)
        binding = _digest(request, MAX_BYTES+65536)
        with self._db(write=True) as db:
            prior = db.execute('SELECT sha256,reply FROM requests WHERE id=?', (request['request_id'],)).fetchone()
            if prior:
                if prior['sha256'] != binding:
                    raise Conflict('Duplicate request changed')
                reply = json.loads(prior['reply'])
                if reply.get('removed_reply') is True:
                    raise KeyError('Workflow was permanently deleted; its earlier result is unavailable')
                return reply
            now = _now()
            if action == 'create':
                c.require(type(request['value']) is dict, 'Workflow must be an object')
                c.require(request['value'].get('active') is not True and not request['value'].get('activeVersionId'), 'Import cannot activate workflows')
                payload = document(request['value'])
                # Some editors allocate the URL identity before the first save.
                # This is an explicit host request, not adoption of an imported
                # document's identity. Existing and removed IDs are never reused.
                workflow_id = request.get('id', 'w'+uuid.uuid4().hex)
                if db.execute('SELECT 1 FROM workflows WHERE id=?', (workflow_id,)).fetchone():
                    raise Conflict('Workflow identifier already exists')
                version, revision = _token(), _token()
                db.execute('INSERT INTO workflows(id,revision,version,created,updated) VALUES (?,?,?,?,?)', (workflow_id, revision, version, now, now))
                db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?)', (version, workflow_id, None, _encoded(payload), _digest(payload), now))
            else:
                row = self._row(db, request['id'])
                if row['revision'] != request['revision']:
                    raise Conflict('Workflow changed; retain your draft and reconcile')
                workflow_id = row['id']
                if action in ('update', 'restore', 'duplicate'):
                    c.require(not row['archived'], 'Unarchive workflow before editing')
                    payload = (document(request['value']) if action == 'update' else
                               self._version(db, workflow_id, request['versionId']) if action == 'restore' else
                               self._version(db, workflow_id, row['version']))
                    if action == 'duplicate':
                        c.text(request['name'], maximum=512)
                        payload = document({**payload, 'name': request['name']})
                        workflow_id = 'w'+uuid.uuid4().hex
                        version = _token()
                        db.execute('INSERT INTO workflows(id,revision,version,created,updated) VALUES (?,?,?,?,?)', (workflow_id, _token(), version, now, now))
                        parent = None
                    else:
                        version, parent = _token(), row['version']
                        db.execute('UPDATE workflows SET revision=?,version=?,updated=? WHERE id=?', (_token(), version, now, workflow_id))
                    db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?)', (version, workflow_id, parent, _encoded(payload), _digest(payload), now))
                else:
                    c.require(row['active_version'] is None, 'Unpublish through the checked runtime before archiving/deleting')
                    if action == 'delete':
                        c.require(row['archived'], 'Archive workflow before permanent removal')
                        # Operational workflow data is not append-only Engram
                        # experience. Permanent removal must also discard old
                        # replies that would otherwise retain/resurrect the graph.
                        request_ids = [r[0] for r in db.execute('SELECT id FROM requests')]
                        for old_id in request_ids:
                            old_reply = json.loads(db.execute('SELECT reply FROM requests WHERE id=?', (old_id,)).fetchone()[0])
                            if old_reply.get('id') == workflow_id:
                                db.execute('UPDATE requests SET reply=? WHERE id=?',
                                           (_encoded({'id': workflow_id, 'deleted': True, 'removed_reply': True}), old_id))
                        db.execute('DELETE FROM versions WHERE workflow=?', (workflow_id,))
                        db.execute('UPDATE workflows SET revision=?,deleted=1,updated=? WHERE id=?', (_token(), now, workflow_id))
                    else:
                        c.require(bool(row['archived']) != (action == 'archive'), 'Workflow is already in the requested archive state')
                        payload = self._version(db, workflow_id, row['version'])
                        version = _token()
                        db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?)', (version, workflow_id, row['version'], _encoded(payload), _digest(payload), now))
                        db.execute('UPDATE workflows SET revision=?,version=?,archived=?,updated=? WHERE id=?',
                                   (_token(), version, int(action == 'archive'), now, workflow_id))
            result = ({'id': workflow_id, 'deleted': True} if action == 'delete' else
                      self._view(db, self._row(db, workflow_id)))
            db.execute('INSERT INTO requests VALUES (?,?,?)', (request['request_id'], binding, _encoded(result, MAX_BYTES+65536)))
            return result


def serve(store, input_stream=None, output_stream=None, *, check_source=None):
    """Trusted foreground controller pipe, never a network/model RPC listener.

    Operational documents have a separate budget from cognition frames. The
    launcher admits this channel only behind its owner-local HTTP boundary.
    """
    input_stream = input_stream or sys.stdin.buffer
    output_stream = output_stream or sys.stdout
    while True:
        line = input_stream.readline(MAX_BYTES+65537)
        if not line:
            return 0
        if len(line) > MAX_BYTES+65536:
            return 2
        envelope = {}
        try:
            envelope = json.loads(line)
            c.shape(envelope, {'id', 'op', 'args'})
            c.identifier(envelope['id'])
            c.require(type(envelope['args']) is dict, 'Invalid workflow arguments')
            if check_source is not None:
                check_source()
            op, args = envelope['op'], envelope['args']
            if op == 'list':
                result = store.list(**args)
            elif op in ('get', 'history'):
                c.shape(args, {'id'})
                result = getattr(store, op)(args['id'])
            elif op == 'mutate':
                result = store.mutate(args, owner=True)
            else:
                raise ValueError('Unsupported workflow operation')
            reply = {'id': envelope['id'], 'ok': True, 'result': result}
        except Exception as error:
            reply = {'id': envelope.get('id') if type(envelope) is dict else None,
                     'ok': False, 'error': type(error).__name__+': '+str(error)}
        output_stream.write(_encoded(reply, MAX_BYTES+65536)+'\n')
        output_stream.flush()
