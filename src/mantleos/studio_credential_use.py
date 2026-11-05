"""Reviewed credential-use grants for a saved workflow's checked effects."""
from contextlib import contextmanager
from datetime import datetime, timezone
import base64
from http.client import HTTPConnection
from pathlib import Path
import re
import socket
from threading import Timer
from urllib.parse import urlsplit
import uuid

from . import json_contract as c
from .effects import Capability, CapabilityRegistry, CheckedActionExecutor
from .storage import _protect
from .studio_credentials import CredentialStore
from .studio_workflows import WorkflowStore

SCHEMA = 'studio.workflow-credential-grant/1'
HTTP_PROFILE = 'loopback-basic-get/1'
MAX_TTL_SECONDS = 600
MAX_RESPONSE = 32*1024


def checked_http_node(workflow, node_id):
    """Return only the effect fields admitted by this explicit HTTP profile."""
    nodes = [node for node in workflow['nodes'] if node['id'] == node_id]
    c.require(len(nodes) == 1, 'Saved HTTP node is unavailable')
    node, = nodes
    c.require(node['type'] == 'n8n-nodes-base.httpRequest' and node.get('typeVersion') == 4.5
              and not node.get('disabled'), 'Unsupported credential-use node')
    values = node.get('parameters', {})
    c.require(values.keys() <= {'url', 'method', 'authentication', 'genericAuthType', 'options'}
              and values.get('method', 'GET') == 'GET'
              and values.get('authentication') == 'genericCredentialType'
              and values.get('genericAuthType') == 'httpBasicAuth'
              and values.get('options', {}) == {}, 'Unsupported checked HTTP Request settings')
    c.require(not any(node.get(flag) for flag in ('retryOnFail', 'continueOnFail', 'alwaysOutputData', 'executeOnce'))
              and node.get('onError', 'stopWorkflow') == 'stopWorkflow', 'Unsupported checked HTTP failure policy')
    raw = c.text(values.get('url'), maximum=1024)
    url = urlsplit(raw)
    c.require(url.scheme == 'http' and url.hostname == '127.0.0.1'
              and url.port is not None and 1024 <= url.port <= 65535
              and bool(re.fullmatch(r'/[a-zA-Z0-9/._~-]*', url.path))
              and all(segment not in ('.', '..') for segment in url.path.split('/'))
              and raw == f'http://127.0.0.1:{url.port}{url.path}',
              'Checked HTTP profile requires an exact literal loopback endpoint')
    refs = node.get('credentials')
    c.shape(refs, {'httpBasicAuth'})
    ref = refs['httpBasicAuth']
    c.require(type(ref) is dict and ref.keys() <= {'id', 'name'}, 'Invalid saved credential reference')
    c.identifier(ref.get('id'))
    return {'profile': HTTP_PROFILE, 'workflow': workflow['id'], 'version': workflow['versionId'],
            'node': node_id, 'credential': ref['id'], 'method': 'GET', 'url': raw}


def _time(now):
    return now if now is not None else int(datetime.now(timezone.utc).timestamp())


def _has_secret(value, protected):
    if isinstance(value, str):
        return any(secret and secret in value for secret in protected)
    if isinstance(value, dict):
        return any(_has_secret(key, protected) or _has_secret(item, protected) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_secret(item, protected) for item in value)
    return False


def _get_json(url, secret):
    """One direct loopback request. No proxies, redirects or response headers escape."""
    target = urlsplit(url)
    encoded = base64.b64encode((secret['user']+':'+secret['password']).encode('utf-8')).decode('ascii')
    connection = HTTPConnection('127.0.0.1', target.port, timeout=2)
    timer = None
    try:
        connection.connect()
        peer = connection.sock

        def expire():
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        timer = Timer(2, expire)
        timer.daemon = True
        timer.start()
        connection.request('GET', target.path, headers={'Authorization': 'Basic '+encoded,
                           'Accept': 'application/json', 'Connection': 'close'})
        with connection.getresponse() as response:
            if response.status != 200:
                return {'status': response.status, 'json': None}
            if response.getheader('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/json':
                raise ValueError('Checked HTTP response must be JSON')
            raw = response.read(MAX_RESPONSE+1)
        c.require(len(raw) <= MAX_RESPONSE, 'Checked HTTP response exceeds its size limit')
        value = c.loads(raw)
        c.require(type(value) is dict and not _has_secret(value, (secret['password'], encoded)),
                  'Checked HTTP output violates the response policy')
        return {'status': 200, 'json': value}
    finally:
        if timer is not None:
            timer.cancel()
        connection.close()


class CredentialUse:
    """Sealed grants retain no raw secrets and are scoped to a single saved version."""
    def __init__(self, nest):
        self.nest = Path(nest)

    @contextmanager
    def _authority(self, *, write=False, active=False):
        from .studio import database, _setting, controller_pin
        from .studio_editor import from_database
        with database(self.nest) as db:
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            config = from_database(db)
            if (not config or config.get('credential_editor') is not True or
                    config.get('manual_execution') is not True or
                    (active and _setting(db, 'phase') != 'ACTIVE')):
                raise PermissionError('Checked credential use requires reviewed Studio editor and manual execution')
            identity = _setting(db, 'identity')
            owner = {'identity': identity, 'configuration': config['sha256'], 'controller': controller_pin()}
            yield db, owner, CredentialStore(self.nest, identity)

    @staticmethod
    def _review(reviewed):
        if reviewed is not True:
            raise PermissionError('Explicit operator review required for credential use')

    @staticmethod
    def _secret(vault, binding):
        with vault._db() as db:
            row = vault._row(db, binding['credential'])
            if row['type'] != 'httpBasicAuth' or row['revision'] != binding['credential_revision']:
                raise PermissionError('Credential revision changed')
            value = vault._unseal(row)
        if value.get('allowedHttpRequestDomains', 'all') != 'all':
            raise PermissionError('Credential domain settings do not admit this profile')
        c.require(':' not in value['user'] and value['password'] and all(
            character not in value['user']+value['password'] for character in '\r\n'
        ), 'Invalid literal Basic Auth values')
        return value

    def grant(self, workflow_id, node_id, *, ttl=MAX_TTL_SECONDS, reviewed=False, now=None):
        self._review(reviewed)
        c.require(type(ttl) is int and 1 <= ttl <= MAX_TTL_SECONDS, 'Invalid checked credential grant lifetime')
        now = _time(now)
        with self._authority(write=True) as (db, owner, vault):
            workflow = WorkflowStore(self.nest/'operational-workflows').get(workflow_id)
            c.require(not workflow['isArchived'], 'Archived workflow cannot receive a grant')
            request = checked_http_node(workflow, node_id)
            credential = vault.get(request['credential'], reviewed=True)
            binding = {**request, 'credential_revision': credential['revision']}
            self._secret(vault, binding)
            identifier = 'grant-'+uuid.uuid4().hex
            record = {'schema': SCHEMA, 'id': identifier, 'owner': owner, 'binding': binding,
                      'expires': now+ttl}
            seal = _protect(c.canonical(record).encode('utf-8'))
            db.execute('CREATE TABLE IF NOT EXISTS credential_use_grants('
                       'workflow TEXT, node TEXT, id TEXT UNIQUE NOT NULL, expires INTEGER NOT NULL,'
                       'seal BLOB NOT NULL, PRIMARY KEY(workflow,node))')
            db.execute('DELETE FROM credential_use_grants WHERE expires<=? OR (workflow=? AND node=?)',
                       (now, workflow_id, node_id))
            c.require(db.execute('SELECT count(*) FROM credential_use_grants').fetchone()[0] < 128,
                      'Credential use grant capacity reached')
            db.execute('INSERT INTO credential_use_grants VALUES (?,?,?,?,?)',
                       (workflow_id, node_id, identifier, record['expires'], seal))
            return {'id': identifier, 'binding': binding, 'expires': record['expires']}

    @staticmethod
    def _available(db):
        return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='credential_use_grants'").fetchone()

    def revoke(self, identifier, *, reviewed=False):
        self._review(reviewed)
        c.identifier(identifier)
        with self._authority(write=True) as (db, _, _vault):
            if not self._available(db) or not db.execute(
                    'DELETE FROM credential_use_grants WHERE id=?', (identifier,)).rowcount:
                raise KeyError('Credential use grant not found')
        return {'id': identifier, 'status': 'REVOKED'}

    def _checked(self, db, owner, vault, workflow_id, node_id, version_id, now):
        workflow = WorkflowStore(self.nest/'operational-workflows').get(workflow_id)
        if workflow['versionId'] != version_id or workflow['isArchived']:
            raise PermissionError('Saved workflow version changed')
        request = checked_http_node(workflow, node_id)
        row = db.execute('SELECT id,expires,seal FROM credential_use_grants WHERE workflow=? AND node=?',
                         (request['workflow'], request['node'])).fetchone() if self._available(db) else None
        if row is None or row[1] <= _time(now):
            raise PermissionError('Checked HTTP request has no current credential grant')
        try:
            record = c.loads(_protect(row[2], decrypt=True))
            c.shape(record, {'schema', 'id', 'owner', 'binding', 'expires'})
            c.shape(record['binding'], request.keys() | {'credential_revision'})
            c.require(record['schema'] == SCHEMA and record['id'] == row[0] and record['owner'] == owner
                      and record['expires'] == row[1]
                      and all(record['binding'][key] == value for key, value in request.items()),
                      'Credential use grant binding changed')
        except (ValueError, OSError, TypeError) as error:
            raise PermissionError('Credential use grant verification failed') from error
        secret = self._secret(vault, record['binding'])
        return {'id': record['id'], 'binding': record['binding'], 'expires': record['expires']}, secret

    def check(self, workflow_id, node_id, version_id, *, configuration=None, now=None):
        """Check a saved version and its current grant without releasing credentials."""
        with self._authority(active=True) as (db, owner, vault):
            if configuration is not None and owner['configuration'] != configuration:
                raise PermissionError('Editor configuration changed')
            grant, _ = self._checked(db, owner, vault, workflow_id, node_id, version_id, now)
            return grant

    def observe(self, run_id, node_id, *, claim, configuration):
        """Admit one checked request for this run and return a verified observation."""
        with self._authority(write=True, active=True) as (db, owner, vault):
            if owner['configuration'] != configuration:
                raise PermissionError('Editor configuration changed')
            store = WorkflowStore(self.nest/'operational-workflows')
            run = store.execution_authorize(run_id, claim=claim, source_pin=owner['controller'])
            grant, secret = self._checked(db, owner, vault, run['workflowId'], node_id,
                                          run['workflowVersionId'], None)
            binding = {'execution': run_id, 'grant': grant['id'], 'request': grant['binding']}
            binding_sha = c.digest(binding)
            db.execute('CREATE TABLE IF NOT EXISTS credential_effect_attempts('
                       'execution TEXT,node TEXT,binding_sha256 TEXT NOT NULL,stage TEXT NOT NULL,'
                       'result_sha256 TEXT,PRIMARY KEY(execution,node))')
            c.require(db.execute('SELECT count(*) FROM credential_effect_attempts').fetchone()[0] < 4096,
                      'Checked credential effect capacity reached')
            inserted = db.execute('INSERT OR IGNORE INTO credential_effect_attempts VALUES (?,?,?,\'ATTEMPTED\',NULL)',
                                  (run_id, node_id, binding_sha)).rowcount
            if not inserted:
                raise PermissionError('Checked HTTP attempt already recorded')
        registry = CapabilityRegistry()
        registry.register(Capability('studio.http.read', 'READ', 'checked-http-grant', HTTP_PROFILE,
                                     lambda args: _get_json(args['request']['url'], secret),
                                     lambda value: value['status'] == 200 and type(value['json']) is dict))
        checked = CheckedActionExecutor(registry, lambda authority, _name: authority == 'checked-http-grant').execute(
            'studio.http.read', binding, request_id=run_id)
        from .studio import database
        with database(self.nest) as db:
            changed = db.execute('UPDATE credential_effect_attempts SET stage=?,result_sha256=? '
                                 'WHERE execution=? AND node=? AND binding_sha256=? AND stage=\'ATTEMPTED\'',
                                 (checked['stage'], c.digest(checked), run_id, node_id, binding_sha)).rowcount
            c.require(changed == 1, 'Checked HTTP observation could not commit')
        if checked['stage'] != 'VERIFIED':
            return {'stage': checked['stage'], 'binding_sha256': binding_sha}
        return {'stage': 'VERIFIED', 'binding_sha256': binding_sha, 'json': checked['observation']['result']['json']}
