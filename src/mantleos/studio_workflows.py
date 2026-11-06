"""Operational workflow drafts and retained versions, owned by N-WORKFLOW.

These are application documents, not Engram records or Anchor instructions.
Import/save never deploys a flow. Runtime publication is a separate checked
effect; a saved document cannot declare itself active or supply authority.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import quote
import uuid

from . import json_contract as c

APPLICATION = 0x41575346
VERSION = 1
HISTORY_POLICY_VERSION = 2
RETRY_VERSION = 3
MAX_BYTES = 16 * 1024 * 1024
MAX_EXECUTION_RESULT = 4 * 1024 * 1024
TERMINAL_EXECUTIONS = {'success', 'error', 'canceled', 'needs_review'}
HISTORY_STATUSES = {
    'running': 'running', 'success': 'success', 'error': 'error',
    'canceled': 'canceled', 'crashed': 'needs_review',
    'new': None, 'waiting': None, 'unknown': None,
}
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


def _execution_table(db):
    return db is not None and db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='workflow_executions'"
    ).fetchone() is not None


def _has_history_policy(db):
    return db.execute('PRAGMA user_version').fetchone()[0] >= HISTORY_POLICY_VERSION


def _has_retry(db):
    return db.execute('PRAGMA user_version').fetchone()[0] == RETRY_VERSION


def _add_history_policy(db):
    db.execute('ALTER TABLE workflow_executions ADD COLUMN discarded INTEGER NOT NULL DEFAULT 0 CHECK(discarded IN (0,1))')
    db.execute('PRAGMA user_version='+str(HISTORY_POLICY_VERSION))


def _retained_condition(db, prefix=''):
    return prefix+'discarded=0' if _has_history_policy(db) else '1'


def _execution_result_digest(row, status, stopped, result):
    binding = {'execution': row['id'], 'request': row['request_sha256'],
               'graph': row['graph_sha256'], 'status': status, 'stopped': stopped, 'result': result}
    if 'retry_of' in row.keys() and row['retry_of'] is not None:
        binding['retry_of'] = row['retry_of']
    return _digest(binding, MAX_EXECUTION_RESULT + 4096)


def _execution_time(value):
    c.require(type(value) is str and bool(re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value)),
        'Invalid execution time bound')
    return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat(timespec='microseconds')


def _execution_filter(query, *, retry):
    c.require(type(query) is dict and query.keys() <= {
        'workflowId', 'workflowVersionId', 'status', 'startedAfter', 'startedBefore', 'mode',
    }, 'Unsupported execution history filter')
    conditions, values = [], []
    for key, column in (('workflowId', 'workflow'), ('workflowVersionId', 'version')):
        if key in query:
            conditions.append(column+'=?')
            values.append(_id(query[key]))
    for key, operator in (('startedAfter', '>='), ('startedBefore', '<=')):
        if key in query:
            conditions.append('started'+operator+'?')
            values.append(_execution_time(query[key]))
    if 'mode' in query:
        mode = c.text(query['mode'], maximum=64)
        modes = {'manual': 'retry_of IS NULL', 'retry': 'retry_of IS NOT NULL'} if retry else {'manual': '1'}
        conditions.append(modes.get(mode, '0'))
    statuses = query.get('status', [])
    c.require(type(statuses) is list and len(statuses) <= len(HISTORY_STATUSES)
              and all(type(status) is str and status in HISTORY_STATUSES for status in statuses),
              'Invalid execution status filter')
    if statuses:
        matches = sorted({HISTORY_STATUSES[status] for status in statuses} - {None})
        conditions.append('status IN (' + ','.join('?' for _ in matches) + ')' if matches else '0')
        values.extend(matches)
    return conditions, values


def _history_cursor(value):
    if value is None:
        return None
    c.require(type(value) is str and bool(re.fullmatch(r'[A-Za-z0-9_-]{1,512}', value)),
              'Invalid execution cursor')
    packet = c.loads(base64.urlsafe_b64decode(value + '='*(-len(value) % 4)))
    c.shape(packet, {'version', 'v1'})
    c.require(type(packet['version']) is int and packet['version'] == 1, 'Unsupported execution cursor')
    position = packet['v1']
    c.shape(position, {'id', 'timestamp'})
    key = position['id']
    c.require(type(key) is str and bool(re.fullmatch(r'[1-9][0-9]{0,18}', key)) and int(key) < 2**63,
              'Invalid execution cursor position')
    return _execution_time(position['timestamp']), int(key)


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

    def health(self):
        """Read-only storage connectivity, not historical or execution certification."""
        with self._db():pass
        return {'status':'ok','workflow_execution':'UNAVAILABLE'}

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
                c.require(app == APPLICATION and version in (VERSION, HISTORY_POLICY_VERSION, RETRY_VERSION),
                          'Unsupported workflow store; explicit recovery/migration required')
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

    def _execution_view(self, db, row, *, detail=False):
        status = row['status']
        has_result = all(row[key] is not None for key in ('result', 'result_sha256', 'stopped'))
        pending = all(row[key] is None for key in ('result', 'result_sha256', 'stopped'))
        c.require(row['version'] is not None and
                  (status == 'running' and pending or status in TERMINAL_EXECUTIONS and has_result),
                  'Invalid execution state')
        value = {'id': row['id'], 'workflowId': row['workflow'],
                 'workflowVersionId': row['version'], 'mode': 'manual',
                 'status': status, 'startedAt': row['started'], 'stoppedAt': row['stopped']}
        if 'retry_of' in row.keys() and row['retry_of'] is not None:
            value.update(mode='retry', retryOf=row['retry_of'])
        if detail:
            graph = self._version(db, row['workflow'], row['version'])
            c.require(_digest(graph) == row['graph_sha256'], 'Execution graph binding failed')
            result = json.loads(row['result']) if row['result'] is not None else None
            if has_result:
                if 'discarded' in row.keys():
                    c.require(bool(row['discarded']) == (graph['settings'].get('saveManualExecutions') is False),
                              'Execution retention binding failed')
                c.require(_execution_result_digest(row, status, row['stopped'], result) == row['result_sha256'],
                          'Execution result integrity failed')
            value.update(workflowData={**graph, 'id': row['workflow'], 'versionId': row['version']},
                         data=result)
        return value

    def _retry_context(self, db, run_id, load_workflow, source_pin):
        row = self._execution_row(db, run_id)
        if _has_history_policy(db) and row['discarded']:
            raise KeyError('Execution not found')
        if row['status'] != 'error':
            raise Conflict('Retry requires a retained failed execution')
        if row['source_pin'] != source_pin:
            raise Conflict('Retry checkpoint was produced by a different runtime')
        failed = self._execution_view(db, row, detail=True)
        current = self._row(db, row['workflow'])
        c.require(not current['archived'], 'Archived workflow cannot run')
        workflow = self._view(db, current) if load_workflow else failed['workflowData']
        c.require(workflow['settings'].get('saveManualExecutions') is not False,
                  'Retry requires a saved version that retains execution history')
        for graph in (failed['workflowData'], workflow):
            c.require(all(node['type'] in {'n8n-nodes-base.manualTrigger', 'n8n-nodes-base.set',
                                         'n8n-nodes-base.if', 'n8n-nodes-base.wait'}
                          for node in graph['nodes']), 'Retry is limited to workflows without external effects')
        data = failed['data']
        result = data.get('resultData')
        error = result.get('error') if isinstance(result, dict) else None
        c.require(isinstance(error, dict) and error.get('name') == 'NodeOperationError' and
                  not result.get('studioCheckedEffects'), 'Retry requires a verified node failure')
        start = data.get('startData')
        selection = start.get('studioSelection') if isinstance(start, dict) else None
        c.shape(selection, {'trigger', 'destination'})
        c.text(selection['trigger'], maximum=512)
        c.require(selection['destination'] is None, 'Retry requires a full execution checkpoint')
        binding = c.digest({'run': run_id, 'result': row['result_sha256'], 'load': load_workflow,
                            'version': workflow['versionId'], 'revision': current['revision']})
        return {'workflow': workflow, 'selection': selection, 'observation': data,
                'binding': binding, 'revision': current['revision']}

    def execution_retry_prepare(self, *, run_id, load_workflow, source_pin, owner=False):
        if owner is not True:
            raise PermissionError('Independent owner execution authority required')
        c.require(type(load_workflow) is bool, 'Invalid retry mode')
        with self._db() as db:
            return self._retry_context(db, run_id, load_workflow, source_pin)

    def execution_start(self, request, *, source_pin, owner=False):
        """Reserve one dispatch of a saved version, from an independently authorized host."""
        if owner is not True:
            raise PermissionError('Independent owner execution authority required')
        c.require(type(source_pin) is str and re.fullmatch(r'[a-f0-9]{64}', source_pin),
                  'Verified execution source required')
        retry_keys = {'retry_of', 'retry_current', 'retry_binding'}
        base_keys = {'request_id', 'workflow_id', 'version_id', 'revision', 'trigger', 'destination'}
        c.require(type(request) is dict, 'Invalid execution request')
        retry = 'retry_of' in request
        c.shape(request, base_keys | (retry_keys if retry else set()))
        if retry:
            _id(request['retry_of'])
            c.require(type(request['retry_current']) is bool, 'Invalid retry mode')
        c.identifier(request['request_id'])
        for key in ('workflow_id', 'version_id', 'revision'):
            _id(request[key])
        c.text(request['trigger'], maximum=512)
        if request['destination'] is not None:
            c.text(request['destination'], maximum=512)
        binding = c.digest({'request': request, 'source_pin': source_pin})
        with self._db(write=True) as db:
            current = self._row(db, request['workflow_id'])
            if _execution_table(db):
                prior = db.execute('SELECT * FROM workflow_executions WHERE request_id=?',
                                   (request['request_id'],)).fetchone()
                if prior:
                    if prior['request_sha256'] != binding:
                        raise Conflict('Duplicate execution request changed')
                    if prior['version'] is None:
                        raise Conflict('Execution history was removed')
                    return self._execution_view(db, prior)
            target = current['version']
            if retry:
                checkpoint = self._retry_context(db, request['retry_of'], request['retry_current'], source_pin)
                target = checkpoint['workflow']['versionId']
                if (checkpoint['binding'] != request['retry_binding'] or
                    checkpoint['workflow']['id'] != current['id'] or
                    checkpoint['selection'] != {key: request[key] for key in ('trigger', 'destination')}):
                    raise Conflict('Retry checkpoint changed before admission')
            if (target, current['revision']) != (request['version_id'], request['revision']):
                raise Conflict('Workflow changed before execution admission')
            c.require(not current['archived'], 'Archived workflow cannot run')
            graph = self._version(db, current['id'], target)
            names = {node['name'] for node in graph['nodes']}
            c.require(request['trigger'] in names and
                      (request['destination'] is None or request['destination'] in names),
                      'Execution selection must reference saved nodes')
            db.execute("""CREATE TABLE IF NOT EXISTS workflow_executions(
                id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, request_sha256 TEXT NOT NULL,
                workflow TEXT NOT NULL REFERENCES workflows(id),
                version TEXT REFERENCES versions(id) ON DELETE SET NULL,
                graph_sha256 TEXT, source_pin TEXT, claim TEXT,
                status TEXT NOT NULL, started TEXT NOT NULL, stopped TEXT,
                result TEXT, result_sha256 TEXT)""")
            db.execute('CREATE INDEX IF NOT EXISTS execution_workflow ON workflow_executions(workflow, started)')
            active = db.execute("SELECT count(*) FROM workflow_executions WHERE status='running'").fetchone()[0]
            c.require(active < 8, 'Execution capacity reached; review interrupted runs before retrying')
            run_id, claim = _token(), _token()
            if retry and not _has_retry(db):
                if not _has_history_policy(db):
                    _add_history_policy(db)
                db.execute('ALTER TABLE workflow_executions ADD COLUMN retry_of TEXT REFERENCES workflow_executions(id)')
                db.execute('CREATE INDEX execution_retry ON workflow_executions(retry_of)')
                db.execute('PRAGMA user_version='+str(RETRY_VERSION))
            db.execute("""INSERT INTO workflow_executions
                (id,request_id,request_sha256,workflow,version,graph_sha256,source_pin,claim,status,started)
                VALUES (?,?,?,?,?,?,?,?,'running',?)""",
                (run_id, request['request_id'], binding, current['id'], target,
                 _digest(graph), source_pin, claim, _now()))
            if retry:
                db.execute('UPDATE workflow_executions SET retry_of=? WHERE id=?', (request['retry_of'], run_id))
            run = self._execution_view(db, self._execution_row(db, run_id), detail=True)
            return {**run, 'claim': claim,
                    'selection': {'trigger': request['trigger'], 'destination': request['destination']}}

    def _execution_row(self, db, run_id):
        _id(run_id)
        row = (db.execute('SELECT * FROM workflow_executions WHERE id=? AND version IS NOT NULL', (run_id,)).fetchone()
               if _execution_table(db) else None)
        if row is None:
            raise KeyError('Execution not found')
        return row

    def execution_finish(self, run_id, *, claim, status, result, source_pin, owner=False):
        """Admit a terminal runtime observation through the original dispatch claim."""
        if owner is not True:
            raise PermissionError('Independent owner execution authority required')
        c.require(type(status) is str and status in TERMINAL_EXECUTIONS, 'Invalid terminal execution status')
        c.require(type(result) is dict, 'Execution observation must be a JSON object')
        observation = _encoded(result, MAX_EXECUTION_RESULT)
        with self._db(write=True) as db:
            row = self._execution_row(db, run_id)
            if (row['claim'], row['source_pin']) != (claim, source_pin):
                raise PermissionError('Execution claim or source does not match')
            prior = self._execution_view(db, row, detail=True)
            discard = prior['workflowData']['settings'].get('saveManualExecutions') is False
            stored = {'discarded_result_sha256': hashlib.sha256(observation.encode('utf-8')).hexdigest()} if discard else result
            content = _encoded(stored) if discard else observation
            stopped = _now() if row['status'] == 'running' else row['stopped']
            digest = _execution_result_digest(row, status, stopped, stored)
            if row['status'] == 'running':
                if discard and not _has_history_policy(db):
                    _add_history_policy(db)
                if discard:
                    db.execute('UPDATE workflow_executions SET status=?,stopped=?,result=?,result_sha256=?,discarded=1 WHERE id=?',
                               (status, stopped, content, digest, run_id))
                else:
                    db.execute('UPDATE workflow_executions SET status=?,stopped=?,result=?,result_sha256=? WHERE id=?',
                               (status, stopped, content, digest, run_id))
            elif (row['status'], row['result_sha256']) != (status, digest):
                raise Conflict('Committed execution result changed')
            value = self._execution_view(db, self._execution_row(db, run_id), detail=True)
            if discard:
                value.update(discarded=True, data=result)
            _encoded(value, MAX_BYTES + 32768)
            return value

    def execution_get(self, run_id, *, stop_state=False):
        c.require(type(stop_state) is bool, 'Invalid execution detail mode')
        with self._db() as db:
            row = self._execution_row(db, run_id)
            if _has_history_policy(db) and row['discarded'] and not stop_state:
                raise KeyError('Execution not found')
            value = self._execution_view(db, row, detail=True)
            if stop_state:
                del value['data'], value['workflowData']
            return value

    def execution_authorize(self, run_id, *, claim, source_pin):
        """Read a verified saved execution for a trusted host effect adapter."""
        with self._db() as db:
            row = self._execution_row(db, run_id)
            if row['status'] != 'running' or (row['claim'], row['source_pin']) != (claim, source_pin):
                raise PermissionError('Execution effect claim or source does not match')
            return self._execution_view(db, row, detail=True)

    def execution_list(self, *, workflow_id=None, limit=50, offset=0):
        c.require(type(limit) is int and 1 <= limit <= 200 and type(offset) is int and offset >= 0,
                  'Invalid execution pagination')
        with self._db() as db:
            if workflow_id is not None:
                self._row(db, workflow_id)
            if not _execution_table(db):
                return {'data': [], 'count': 0}
            where = ' WHERE version IS NOT NULL AND '+_retained_condition(db)
            values = ()
            if workflow_id is not None:
                where += ' AND workflow=?'
                values = (workflow_id,)
            rows = db.execute('SELECT * FROM workflow_executions' + where + ' ORDER BY rowid DESC LIMIT ? OFFSET ?',
                              (*values, limit, offset)).fetchall()
            count = db.execute('SELECT count(*) FROM workflow_executions' + where, values).fetchone()[0]
            return {'data': [self._execution_view(db, row) for row in rows], 'count': count}

    def execution_page(self, *, query, limit=50, cursor=None):
        """Read a stable page of owner-local execution summaries."""
        c.require(type(limit) is int and 1 <= limit <= 200, 'Invalid execution history limit')
        position = _history_cursor(cursor)

        def fetch(db, where, arguments, *, after=None):
            if after is not None:
                timestamp, row_id = after
                where = [*where, '(started<? OR (started=? AND rowid<?))']
                arguments = [*arguments, timestamp, timestamp, row_id]
            projection = ('id,workflow,version,status,started,stopped,result_sha256,rowid AS page_id,'
                          "CASE WHEN result IS NULL THEN NULL ELSE '' END AS result,"
                          'length(CAST(result AS BLOB)) AS result_size')
            if _has_retry(db):
                projection += ',retry_of'
            return db.execute('SELECT '+projection+' FROM workflow_executions WHERE ' +
                              ' AND '.join(where) + ' ORDER BY started DESC,rowid DESC LIMIT ?',
                              (*arguments, limit)).fetchall()

        with self._db() as db:
            filtered, values = _execution_filter(query, retry=db is not None and _has_retry(db))
            if not _execution_table(db):
                return {'data': [], 'count': 0, 'next_cursor': None}
            statuses = query.get('status')
            base = ['version IS NOT NULL', _retained_condition(db), *filtered]
            conditions = base if statuses else [*base, "status<>'running'"]
            rows = fetch(db, conditions, values, after=position)
            count = db.execute('SELECT count(*) FROM workflow_executions WHERE ' +
                               ' AND '.join(conditions), values).fetchone()[0]
            next_cursor = None
            if len(rows) == limit:
                last = rows[-1]
                packet = c.canonical({'version': 1, 'v1': {
                    'id': str(last['page_id']), 'timestamp': last['started'],
                }})
                next_cursor = base64.urlsafe_b64encode(packet.encode('utf-8')).decode('ascii').rstrip('=')
            if not statuses and position is None:
                rows = fetch(db, [*base, "status='running'"], values) + rows
            names = {}
            summaries = []
            for row in rows:
                workflow_id = row['workflow']
                if workflow_id not in names:
                    workflow = self._row(db, workflow_id)
                    names[workflow_id] = self._version(db, workflow_id, workflow['version'])['name']
                summaries.append({**self._execution_view(db, row), 'workflowName': names[workflow_id],
                                  'jsonSizeBytes': row['result_size'] or 0,
                                  'binaryDataSizeBytes': 0})
            return {'data': summaries, 'count': count, 'next_cursor': next_cursor}

    def execution_delete(self, *, ids, before, query, owner=False):
        """Remove selected settled history, keeping dispatch tombstones."""
        if owner is not True:
            raise PermissionError('Independent owner execution-history authority required')
        c.require((ids is None) != (before is None), 'Select execution IDs or a cutoff')
        if ids is not None:
            c.require(type(ids) is list and len(ids) <= 500, 'Invalid execution deletion selection')
            selected = list(dict.fromkeys(_id(identifier) for identifier in ids))
        else:
            cutoff = _execution_time(before)
        with self._db(write=True) as db:
            filtered, values = _execution_filter(query, retry=_has_retry(db))
            if not _execution_table(db):
                return
            conditions = ['version IS NOT NULL', _retained_condition(db), "status IN ('success','error','canceled')"]
            if ids is not None:
                if not selected:
                    return
                # The pinned client treats explicitly selected IDs as authoritative.
                selector = 'id IN ('+','.join('?' for _ in selected)+')'
                if db.execute("SELECT 1 FROM workflow_executions WHERE status IN ('running','needs_review') AND "+
                              selector+' LIMIT 1', selected).fetchone():
                    raise Conflict('Resolve selected executions before deleting their history')
                conditions.append(selector)
                values = selected
            else:
                conditions += [*filtered, 'started<?']
                values.append(cutoff)
            db.execute("""UPDATE workflow_executions SET version=NULL,graph_sha256=NULL,source_pin=NULL,
                       claim=NULL,status='removed',result=NULL,result_sha256=NULL WHERE """ +
                       ' AND '.join(conditions), values)

    def execution_versions(self, workflow_id):
        _id(workflow_id)
        with self._db() as db:
            if not _execution_table(db):
                return []
            retained = _retained_condition(db, 'e.')
            rows = db.execute("""SELECT v.id,v.created FROM versions v WHERE v.workflow=?
                AND EXISTS(SELECT 1 FROM workflow_executions e WHERE e.workflow=v.workflow AND e.version=v.id
                AND """+retained+""") ORDER BY v.created DESC,v.rowid DESC""", (workflow_id,))
            return [{'versionId': row['id'], 'createdAt': row['created'], 'name': None} for row in rows]

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
                        if _execution_table(db) and db.execute(
                            "SELECT 1 FROM workflow_executions WHERE workflow=? AND status='running'", (workflow_id,),
                        ).fetchone():
                            raise Conflict('Resolve running executions before permanent removal')
                        if _execution_table(db):
                            db.execute("""UPDATE workflow_executions SET version=NULL,graph_sha256=NULL,
                                source_pin=NULL,claim=NULL,status='removed',result=NULL,result_sha256=NULL
                                WHERE workflow=?""", (workflow_id,))
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


def serve(store, input_stream=None, output_stream=None, *, check_source=None, execution_source=None,
          execution_history_authority=None,
          credential_store=None, credential_use=None):
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
            if op == 'health':
                c.shape(args,set())
                result=store.health()
            elif op == 'list':
                result = store.list(**args)
            elif op in ('get', 'history'):
                c.shape(args, {'id'})
                result = getattr(store, op)(args['id'])
            elif op == 'mutate':
                result = store.mutate(args, owner=True)
            elif op == 'inventory':
                c.shape(args,{'collection'})
                from .studio_inventory import EditorInventory
                result=EditorInventory(store.directory.parent).list(args['collection'])
            elif op in ('credential_list', 'credential_get', 'credential_save', 'credential_remove') and credential_store:
                keys = {'credential_list': set(), 'credential_get': {'identifier', 'include_data'},
                        'credential_save': {'value', 'identifier', 'revision'},
                        'credential_remove': {'identifier', 'revision'}}[op]
                c.shape(args, keys | {'configuration'})
                with credential_store(args['configuration']) as vault:
                    result = getattr(vault, op.removeprefix('credential_'))(
                        **{key: args[key] for key in keys}, reviewed=True)
            elif op == 'credential_effect_check' and credential_use:
                c.shape(args, {'workflow_id', 'node_id', 'version_id', 'configuration'})
                result = credential_use.check(**args)
            elif op == 'credential_effect_observe' and credential_use:
                c.shape(args, {'run_id', 'node_id', 'claim', 'configuration'})
                result = credential_use.observe(**args)
            elif op == 'execution_start' and execution_source:
                result = store.execution_start(args, source_pin=execution_source, owner=True)
            elif op == 'execution_retry_prepare' and execution_source:
                c.shape(args, {'run_id', 'load_workflow'})
                result = store.execution_retry_prepare(**args, source_pin=execution_source, owner=True)
            elif op == 'execution_finish' and execution_source:
                c.shape(args, {'run_id', 'claim', 'status', 'result'})
                result = store.execution_finish(**args, source_pin=execution_source, owner=True)
            elif op == 'execution_get' and execution_source:
                c.shape(args, {'run_id'})
                result = store.execution_get(**args)
            elif op == 'execution_stop_state' and execution_source:
                c.shape(args, {'run_id'})
                result = store.execution_get(**args, stop_state=True)
            elif op == 'execution_list' and execution_source:
                result = store.execution_list(**args)
            elif op == 'execution_page' and execution_source:
                result = store.execution_page(**args)
            elif op == 'execution_delete' and execution_history_authority:
                c.shape(args, {'ids', 'before', 'query', 'configuration'})
                with execution_history_authority(args['configuration']):
                    result = store.execution_delete(ids=args['ids'], before=args['before'],
                                                    query=args['query'], owner=True)
            elif op == 'execution_versions' and execution_source:
                c.shape(args, {'workflow_id'})
                result = store.execution_versions(**args)
            else:
                raise ValueError('Unsupported workflow operation')
            reply = {'id': envelope['id'], 'ok': True, 'result': result}
        except Exception as error:
            reply = {'id': envelope.get('id') if type(envelope) is dict else None,
                     'ok': False, 'error': type(error).__name__+': '+str(error)}
        output_stream.write(_encoded(reply, MAX_BYTES+65536)+'\n')
        output_stream.flush()
