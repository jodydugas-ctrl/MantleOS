"""Opt-in encrypted storage of shared Engram records. No model or service starts here.

Keys and this API belong to a trusted Body principal. Encryption is not a sandbox.
Authenticated index deltas are storage metadata, never a second memory language.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid
from . import engram

SCHEMA = 'mantle.private-skin/1'
canon = engram.canonical

def crypto():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
    except ImportError as exc:
        raise RuntimeError('Private Skin requires the optional cryptography dependency') from exc
    return AESGCM, HKDF, hashes

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def terms(text):
    return sorted(set(re.findall(r'\w+', text.casefold(), re.UNICODE)))

def source_files():
    names = ('skin.py', 'private_mind.py', 'private_appai.py', 'engram.py',
             'anchors.py', 'anchor_design.py', 'anchor_language.py', 'effects.py', 'immune.py', 'skin_cli.py', 'prototype_import.py')
    root = Path(__file__).parent
    return {n:(root/n).read_bytes() for n in sorted(names)}

def source_pin():
    """Platform-independent, explicit trusted implementation inventory."""
    return sha(canon([[n,sha(raw)] for n,raw in source_files().items()]).encode())

class Skin:
    def __init__(self, path, key):
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError('Skin key must contain 32 random bytes')
        AESGCM, HKDF, hashes = crypto()
        self.aead = AESGCM(HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                              info=b'mantle-skin-payload/1').derive(key))
        self.index_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                             info=b'mantle-skin-index/1').derive(key)
        if Path(path).is_symlink():
            raise ValueError('Symlink Skin refused')
        self.path = Path(path).resolve(strict=True)
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=5)
        self.db.execute('PRAGMA trusted_schema=OFF')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.decryptions = 0
        try:
            self.verify()
        except BaseException:
            self.db.close()
            raise

    @classmethod
    def create(cls, path, key, founding, *, identity=None, persona='Raven'):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb'):
            pass
        db = sqlite3.connect(path)
        try:
            db.executescript('''
              CREATE TABLE meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
              CREATE TABLE objects(id TEXT PRIMARY KEY,nonce BLOB NOT NULL,cipher BLOB NOT NULL);
              CREATE TABLE events(seq INTEGER PRIMARY KEY,head TEXT NOT NULL UNIQUE,
                prev TEXT NOT NULL,nonce BLOB NOT NULL,cipher BLOB NOT NULL,tokens TEXT NOT NULL,mac TEXT NOT NULL);
            ''')
            db.execute('INSERT INTO meta VALUES (?,?)', ('schema', SCHEMA))
            db.commit()
        finally:
            db.close()
        skin = cls(path, key)
        try:
            skin.put_object('constitution', canon({'identity':identity or uuid.uuid4().hex,
                'persona':persona, 'primer':founding, 'source_pin':source_pin()}).encode())
            for name,raw in source_files().items():
                skin.put_object('source:'+name,raw)
            return skin
        except BaseException:
            skin.close()
            raise

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def close(self): self.db.close()

    def _token(self, value):
        return hmac.digest(self.index_key, value.encode(), 'sha256').hex()

    def _mac(self, row):
        seq, head, prev, nonce, cipher, tokens = row
        return self._token(canon([seq,head,prev,nonce.hex(),sha(cipher),tokens]))

    def verify(self):
        if self.db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Skin SQLite integrity failure')
        if self.db.execute('SELECT v FROM meta WHERE k=?', ('schema',)).fetchone() != (SCHEMA,):
            raise ValueError('Unsupported Skin schema')
        self.head = engram.ZERO
        self.count = 0
        self.index = {}
        self.heads = {0:engram.ZERO}
        objects = self.db.execute('SELECT id,nonce,cipher FROM objects ORDER BY id').fetchall()
        seal = self.db.execute("SELECT v FROM meta WHERE k='objects_seal'").fetchone()
        if objects or seal:
            expected = self._token(canon([[n,x.hex(),sha(c)] for n,x,c in objects]))
            if seal is None or not hmac.compare_digest(seal[0],expected):
                raise ValueError('Skin source/founding object authentication failure')
        for row in self.db.execute('SELECT seq,head,prev,nonce,cipher,tokens,mac FROM events ORDER BY seq'):
            seq, head, prev, nonce, cipher, tokens, mac = row
            if seq != self.count+1 or prev != self.head or not hmac.compare_digest(mac, self._mac(row[:6])):
                raise ValueError('Skin record/index authentication failure')
            self.count = seq
            self.head = head
            self.heads[seq] = head
            for token in json.loads(tokens):
                self.index.setdefault(token, set()).add(seq)
        self.version = self.db.execute('PRAGMA data_version').fetchone()[0]

    def _fresh(self):
        if self.db.execute('PRAGMA data_version').fetchone()[0] != self.version:
            raise ValueError('Skin changed outside pinned session; reopen required')

    def put_object(self, name, raw):
        """Immutable encrypted source, founding material or attachment."""
        nonce = os.urandom(12)
        cipher = self.aead.encrypt(nonce, raw, (SCHEMA+':object:'+name).encode())
        self._fresh()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute('INSERT INTO objects VALUES (?,?,?)', (name,nonce,cipher))
            objects = self.db.execute('SELECT id,nonce,cipher FROM objects ORDER BY id').fetchall()
            seal = self._token(canon([[n,x.hex(),sha(c)] for n,x,c in objects]))
            self.db.execute("INSERT INTO meta VALUES ('objects_seal',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",(seal,))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def object(self, name):
        self._fresh()
        row = self.db.execute('SELECT nonce,cipher FROM objects WHERE id=?', (name,)).fetchone()
        if row is None: raise KeyError(name)
        self.decryptions += 1
        return self.aead.decrypt(row[0],row[1],(SCHEMA+':object:'+name).encode())

    def record(self, seq):
        self._fresh()
        row = self.db.execute('SELECT nonce,cipher,head,prev FROM events WHERE seq=?',(seq,)).fetchone()
        if row is None: raise KeyError(seq)
        self.decryptions += 1
        r = json.loads(self.aead.decrypt(row[0], row[1], (SCHEMA+':record:'+str(seq)).encode()))
        if (r['seq'] != seq or r['sha256'] != row[2] or
            r.get('prev_sha256',r.get('prev')) != row[3] or engram.hash_record(r) != row[2]):
            raise ValueError('Invalid canonical Engram record')
        return r

    def append(self, kind, body, *, expected_head, source='private-appai'):
        r = {'schema':'mantle.engram-record/1','seq':self.count+1,'id':uuid.uuid4().hex,
             'type':kind,'source':source,'body':body,'prev_sha256':self.head}
        r['sha256'] = engram.hash_record(r)
        return self.append_record(r, expected_head=expected_head)

    def append_record(self, record, *, expected_head):
        """Preserve exact historical canonical bytes/semantics through imports."""
        self._fresh()
        seq = self.count+1
        if (expected_head != self.head or record['seq'] != seq or
            record.get('prev_sha256',record.get('prev')) != self.head or
            record['sha256'] != engram.hash_record(record)):
            raise ValueError('Stale or invalid canonical record')
        from .cells import append_segment
        append_segment(record)
        index_terms = terms(canon(record['body'])) + ['kind:'+record['type']]
        if record['type']=='private-turn' or (record['source'] in {'journal-bridge','prototype-bridge'} and record['type']=='turn'):
            index_terms.append('request:'+record['body']['request_id'])
        if record['type']=='private-observation':
            index_terms.append('observation:'+record['body']['request_id'])
        if record['type']=='private-action-binding':
            index_terms.append('action-user:'+record['body']['request_id'])
        if record['type']=='effect' and record['body'].get('stage')=='INTENDED':
            index_terms.append('action:'+record['body']['request_id'])
        tokens = canon(sorted({self._token(t) for t in index_terms}))
        nonce = os.urandom(12)
        cipher = self.aead.encrypt(nonce,canon(record).encode(),(SCHEMA+':record:'+str(seq)).encode())
        row = (seq,record['sha256'],self.head,nonce,cipher,tokens)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            # SQLite serializes cooperating processes; reject preparations made before another commit.
            actual = self.db.execute('SELECT head FROM events ORDER BY seq DESC LIMIT 1').fetchone()
            if (actual[0] if actual else engram.ZERO) != expected_head:
                raise ValueError('Stale Skin writer')
            self.db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',(*row,self._mac(row)))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        self.count = seq
        self.head = record['sha256']
        self.heads[seq] = self.head
        for token in json.loads(tokens): self.index.setdefault(token,set()).add(seq)
        return record

    def recall(self, text, *, limit=6):
        self._fresh()
        if type(limit) is not int or not 1 <= limit <= 6: raise ValueError('Recall limit')
        words = terms(text)[:40]
        sets = [self.index.get(self._token(t),set()) for t in words]
        candidates = set.intersection(*sets) if sets else set()
        return [self.record(s) for s in sorted(candidates,reverse=True)[:limit]]

    def export(self, output):
        self._fresh()
        path = Path(output)
        with path.open('xb'): pass
        dest = sqlite3.connect(path)
        try:
            self.db.backup(dest)
            # Verify the actual consistent backup, including authenticated objects
            # and index deltas. It can be newer than this session if another
            # cooperating writer committed between freshness check and backup.
            check=Skin.__new__(Skin)
            check.db=dest
            check.index_key=self.index_key
            check.verify()
            exported_head=check.head
        finally: dest.close()
        return {'format':SCHEMA,'head':exported_head,'working_head':self.head,
                'sha256':sha(path.read_bytes()),'keys_included':False}

    def checkpoint(self):
        return {'seq':self.count,'head':self.head}

    def require_checkpoint(self, checkpoint):
        if self.heads.get(checkpoint['seq']) != checkpoint['head']:
            raise ValueError('Skin behind or divergent from trusted checkpoint')
