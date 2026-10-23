"""Raven Cloud Continuity / proof-of-concept protocol v0.1.

Provider-neutral, stdlib-only, per-record append and verified restore.
Storage adapters operate on immutable named blobs plus a mutable HEAD with CAS.
The Google Drive/Docs host adapter is deliberately controlled by the host;
its OAuth credentials never enter this module.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import tempfile

ZERO = '0' * 64
MANIFEST = 'raven.cloud-head/1'
SEGMENT = 'raven.cloud-segment/1'

def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def hash_object(value):
    return sha(canon({k:v for k,v in value.items() if k != 'sha256'}).encode())

def require(ok, why):
    if not ok: raise ValueError(why)

def make_head(identity):
    require(isinstance(identity, dict) and set(identity) == {'birth_sha256','primer_sha256','cartridge_id'}, 'Bad identity')
    require(all(isinstance(identity[k],str) and identity[k] for k in identity), 'Empty identity field')
    obj={'schema':MANIFEST,'identity':identity,'seq':0,'ledger_head':ZERO,'segments':[]}
    obj['sha256']=hash_object(obj)
    return obj

def verify_record(record, n, previous):
    require(type(record) is dict and record.get('seq')==n, 'Sequence gap or duplicate')
    require(record.get('schema') in {'mantle.engram-record/1','raven.engram-record/1'}, 'Unknown record schema')
    pk='prev' if record['schema']=='raven.engram-record/1' else 'prev_sha256'
    require(record.get(pk)==previous,'Broken ledger link')
    require(record.get('sha256')==hash_object(record),'Tampered ledger record')

def verify_head(head):
    require(type(head) is dict and set(head)=={'schema','identity','seq','ledger_head','segments','sha256'},'Bad HEAD shape')
    require(head['schema']==MANIFEST and head['sha256']==hash_object(head),'Tampered HEAD')
    require(head['identity']==make_head(head['identity'])['identity'],'Invalid identity')
    require(type(head['seq']) is int and 0<=head['seq']<=100000,'Invalid seq')
    require(type(head['segments']) is list and len(head['segments'])==head['seq'],'Invalid segments size')
    prev=ZERO
    for i, meta in enumerate(head['segments'],1):
        require(type(meta) is dict and set(meta)=={'seq','prev','record_sha256','blob_sha256','blob_id'},'Bad segment metadata')
        require(meta['seq']==i and meta['prev']==prev,'Broken manifest sequence')
        require(isinstance(meta['blob_id'],str) and meta['blob_id'],'Missing blob ID')
        for k in ('prev','record_sha256','blob_sha256'):
            require(isinstance(meta[k],str) and len(meta[k])==64 and all(c in '0123456789abcdef' for c in meta[k]),'Bad hash '+k)
        prev=meta['record_sha256']
    require(head['ledger_head']==prev,'Manifest HEAD does not match last record')
    return head

def encode_segment(record,identity,prev):
    verify_record(record,record['seq'],prev)
    payload=(canon(record)+'\n').encode('utf-8')
    segment={'schema':SEGMENT,'identity':identity,'seq':record['seq'],'prev':prev,
             'record_sha256':record['sha256'],'payload_b64':base64.b64encode(payload).decode('ascii'),
             'payload_sha256':sha(payload)}
    segment['sha256']=hash_object(segment)
    return segment

def decode_segment(seg, identity, previous, n):
    require(type(seg) is dict and set(seg)=={'schema','identity','seq','prev','record_sha256','payload_b64','payload_sha256','sha256'},'Bad segment shape')
    require(seg['schema']==SEGMENT and seg['sha256']==hash_object(seg),'Tampered segment envelope')
    require(seg['identity']==identity,'Wrong Raven identity')
    require(seg['seq']==n and seg['prev']==previous, 'Wrong segment order')
    try: payload=base64.b64decode(seg['payload_b64'], validate=True)
    except Exception as e:raise ValueError('Malformed segment payload') from e
    require(sha(payload)==seg['payload_sha256'],'Payload hash mismatch')
    require(payload.endswith(b'\n') and payload.count(b'\n')==1,'Segment must contain one JSON record')
    rec=json.loads(payload)
    verify_record(rec,n,previous)
    require(seg['record_sha256']==rec['sha256'],'Record digest mismatch')
    require(payload==(canon(rec)+'\n').encode('utf-8'),'Noncanonical record payload')
    return rec

def advance_head(head, segment, blob_id, *, blob_readback):
    verify_head(head)
    record=decode_segment(segment,head['identity'],head['ledger_head'],head['seq']+1)
    require(canon(segment)==canon(blob_readback),'Blob readback mismatch')
    digest=sha(canon(segment).encode())
    next_head={**head,'seq':record['seq'],'ledger_head':record['sha256'],
        'segments':head['segments']+[{'seq':record['seq'],'prev':head['ledger_head'],
           'record_sha256':record['sha256'],'blob_sha256':digest,'blob_id':blob_id}]}
    next_head['sha256']=hash_object(next_head)
    return next_head

def recover(head, blobs):
    verify_head(head)
    records=[]; prev=ZERO
    for meta in head['segments']:
        require(meta['blob_id'] in blobs,'Missing cloud blob')
        seg=blobs[meta['blob_id']]
        require(sha(canon(seg).encode())==meta['blob_sha256'],'Cloud blob digest mismatch')
        record=decode_segment(seg,head['identity'],prev,meta['seq'])
        require(record['sha256']==meta['record_sha256'],'Manifest record mismatch')
        records.append(record);prev=record['sha256']
    require(prev==head['ledger_head'],'Recovered head mismatch')
    return records

def as_document(value):
    """Single ASCII transport token survives Google Docs text normalization."""
    raw=canon(value).encode('utf-8')
    return 'RAVEN-CLOUD-V1:'+base64.urlsafe_b64encode(raw).decode('ascii')

def from_document(text):
    tokens=[line.strip() for line in text.splitlines() if line.strip().startswith('RAVEN-CLOUD-V1:')]
    require(len(tokens)==1,'Expected exactly one document token')
    try:return json.loads(base64.b64decode(tokens[0].split(':',1)[1],altchars=b'-_',validate=True))
    except Exception as e:raise ValueError('Invalid document token') from e

class Conflict(ValueError):pass

class LocalCASStore:
    """Filesystem reference implementation for crash/replay/branch tests."""
    def __init__(self,root):
        self.root=Path(root);(self.root/'blobs').mkdir(parents=True,exist_ok=True)
    def put_blob(self,name,value):
        dest=self.root/'blobs'/name
        require(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,160}',name) is not None,'Unsafe blob name')
        raw=canon(value).encode()
        if dest.exists():
            require(dest.read_bytes()==raw,'Blob ID collision')
        else:
            from .transactions import atomic_bytes
            try:
                atomic_bytes(dest, raw, replace=False)
            except FileExistsError:
                require(dest.read_bytes()==raw,'Blob ID collision')
        return name
    def get_blob(self,name):
        require(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,160}',name) is not None,'Unsafe blob name')
        path=self.root/'blobs'/name
        require(not path.is_symlink(),'Unsafe blob symlink')
        return json.loads(path.read_bytes())
    def load_head(self):
        p=self.root/'HEAD.json'; return json.loads(p.read_text()) if p.exists() else None
    def cas_head(self,expected,new):
        lock=self.root/'head.lock'
        with lock.open('a+b') as f:
            if os.name=='nt':
                import msvcrt
                f.seek(0)
                if not f.read(1):
                    f.write(b'\0');f.flush()
                f.seek(0)
                msvcrt.locking(f.fileno(),msvcrt.LK_LOCK,1)
            else:
                import fcntl
                fcntl.flock(f,fcntl.LOCK_EX)
            try:
                old=self.load_head(); current=old['sha256'] if old else None
                if expected!=current:raise Conflict('Stale cloud HEAD: branch required')
                verify_head(new)
                fd,temp=tempfile.mkstemp(dir=self.root,prefix='.head.')
                try:
                    with os.fdopen(fd,'wb') as w:
                        w.write((canon(new)+'\n').encode());w.flush();os.fsync(w.fileno())
                    os.replace(temp,self.root/'HEAD.json')
                finally:
                    if os.path.exists(temp):os.unlink(temp)
            finally:
                if os.name=='nt': msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
                else: fcntl.flock(f,fcntl.LOCK_UN)

# Simulated one-turn driver. In hosted Drive, create immutable segment Doc,
# read it back, then CAS update the HEAD Doc using requiredRevisionId.
def commit(store,rec):
    old=store.load_head();verify_head(old)
    seg=encode_segment(rec,old['identity'],old['ledger_head'])
    blob_name=f"seg-{rec['seq']:06d}-{rec['sha256'][:16]}"
    store.put_blob(blob_name,seg)
    candidate=advance_head(old,seg,blob_name,blob_readback=store.get_blob(blob_name))
    store.cas_head(old['sha256'],candidate)
    return candidate
