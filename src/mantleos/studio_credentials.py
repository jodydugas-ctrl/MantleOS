"""Owner-local credential lifecycle. The vault grants no workflow effects."""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote
import uuid

from . import json_contract as c
from .storage import _protect

APPLICATION = 0x41534352
MASK = '__n8n_BLANK_VALUE_e5362baf-c777-4d57-a609-6eaf1f9e87f6'
# Only literal HTTP credentials described by the pinned editor catalog.
PROFILES = {
    'httpBasicAuth': ({'user'}, 'password'),
    'httpDigestAuth': ({'user'}, 'password'),
    'httpBearerAuth': (set(), 'token'),
    'httpHeaderAuth': ({'name'}, 'value'),
    'httpQueryAuth': ({'name'}, 'value'),
}
LIMIT = 2048


class Conflict(ValueError):
    """A credential edit was prepared against a different saved revision."""


def _data(kind, values, previous=None):
    c.require(type(kind) is str and kind in PROFILES, 'Unsupported credential type')
    fields, secret = PROFILES[kind]
    c.require(type(values) is dict and fields | {secret} <= values.keys() <=
              fields | {secret, 'allowedHttpRequestDomains', 'allowedDomains'},
              'Unsupported credential fields')
    result = {key: c.text(value, maximum=4096, blank=True) for key, value in values.items()}
    if result[secret] == MASK:
        c.require(previous is not None, 'Mask can only retain an existing secret')
        result[secret] = previous[secret]
    c.require(all(not value.lstrip().startswith('=') and '\x00' not in value for value in result.values()),
              'Credential expressions and NUL are unavailable')
    return result


class CredentialStore:
    def __init__(self, nest, identity):
        c.identifier(identity)
        self.identity = identity
        self.nest = Path(nest).absolute()
        self.path = self.nest/'editor-credentials.sqlite'

    @contextmanager
    def _db(self, *, write=False, initialize=False):
        # storage._protect intentionally passes through on other platforms.
        # A credential vault must fail closed without its reviewed protector.
        c.require(os.name == 'nt', 'Studio credential protection requires Windows DPAPI')
        for path in (self.nest, self.path):
            c.require(not path.is_symlink() and
                      not (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400),
                      'Linked credential storage unavailable')
        c.require(self.nest.is_dir() and (initialize or self.path.is_file()), 'Credential store unavailable')
        mode = 'rwc' if initialize else 'rw' if write else 'ro'
        uri = 'file:'+quote(self.path.as_posix(), safe='/:')+'?mode='+mode
        db = sqlite3.connect(uri, uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            if write:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('PRAGMA secure_delete=ON')
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            app = db.execute('PRAGMA application_id').fetchone()[0]
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if initialize and app == version == 0 and not db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone():
                db.execute('CREATE TABLE owner(identity TEXT PRIMARY KEY)')
                db.execute('INSERT INTO owner VALUES (?)', (self.identity,))
                db.execute('CREATE TABLE credentials(id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,'
                           'revision TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL, sealed BLOB NOT NULL)')
                db.execute('PRAGMA application_id='+str(APPLICATION))
                db.execute('PRAGMA user_version=1')
            else:
                c.require(app == APPLICATION and version == 1, 'Unsupported credential store')
            owners = db.execute('SELECT identity FROM owner').fetchall()
            c.require([row['identity'] for row in owners] == [self.identity], 'Credential store identity changed')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def initialize(self, *, reviewed=False):
        self._review(reviewed)
        with self._db(write=True, initialize=True):
            pass

    @staticmethod
    def _review(reviewed):
        if reviewed is not True:
            raise PermissionError('Independent credential editor authority required')

    @staticmethod
    def _row(db, identifier):
        c.identifier(identifier)
        row = db.execute('SELECT * FROM credentials WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise KeyError('Credential not found')
        return row

    @staticmethod
    def _view(row):
        return {key: row[key] for key in ('id', 'name', 'type', 'revision')} | {
            'createdAt': row['created'], 'updatedAt': row['updated'],
        }

    def _binding(self, row):
        return {'schema': 'studio.credential/1', 'identity': self.identity, 'credential': self._view(row)}

    def _unseal(self, row):
        try:
            packet = c.loads(_protect(row['sealed'], decrypt=True))
            c.shape(packet, {'binding', 'data'})
            c.require(packet['binding'] == self._binding(row), 'Credential binding changed')
            return _data(row['type'], packet['data'])
        except (ValueError, OSError, TypeError) as error:
            raise ValueError('Credential seal verification failed') from error

    def list(self, *, reviewed=False):
        self._review(reviewed)
        with self._db() as db:
            rows = db.execute('SELECT id,name,type,revision,created,updated FROM credentials ORDER BY name,id LIMIT ?',
                              (LIMIT+1,)).fetchall()
            c.require(len(rows) <= LIMIT, 'Credential store limit exceeded')
            return [self._view(row) for row in rows]

    def get(self, identifier, *, include_data=False, reviewed=False):
        self._review(reviewed)
        c.require(type(include_data) is bool, 'Invalid credential projection')
        with self._db() as db:
            row = self._row(db, identifier)
            value = self._view(row)
            if include_data:
                data = self._unseal(row)
                data[PROFILES[row['type']][1]] = MASK
                value['data'] = data
            return value

    def save(self, value, *, identifier=None, revision=None, reviewed=False):
        self._review(reviewed)
        c.shape(value, {'name', 'type', 'data'})
        name = c.text(value['name'], maximum=128)
        now = datetime.now(timezone.utc).isoformat(timespec='microseconds')
        with self._db(write=True) as db:
            if identifier is None:
                c.require(revision is None, 'New credential cannot claim a revision')
                c.require(db.execute('SELECT count(*) FROM credentials').fetchone()[0] < LIMIT,
                          'Credential store limit exceeded')
                identifier = 'credential-'+uuid.uuid4().hex
                created, previous = now, None
            else:
                row = self._row(db, identifier)
                if row['revision'] != revision:
                    raise Conflict('Credential revision changed')
                c.require(row['type'] == value['type'], 'Credential type change requires a fresh record')
                created, previous = row['created'], self._unseal(row)
            record = {'id': identifier, 'name': name, 'type': value['type'], 'revision': uuid.uuid4().hex,
                      'created': created, 'updated': now}
            payload = c.canonical({'binding': self._binding(record),
                                   'data': _data(value['type'], value['data'], previous)})
            sealed = _protect(payload.encode('utf-8'))
            db.execute('INSERT INTO credentials VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                       'name=excluded.name,revision=excluded.revision,updated=excluded.updated,sealed=excluded.sealed',
                       (identifier, name, record['type'], record['revision'], created, now, sealed))
            return self._view(record)

    def remove(self, identifier, *, revision, reviewed=False):
        self._review(reviewed)
        with self._db(write=True) as db:
            row = self._row(db, identifier)
            if row['revision'] != revision:
                raise Conflict('Credential revision changed')
            self._unseal(row)
            db.execute('DELETE FROM credentials WHERE id=?', (identifier,))
        return True
