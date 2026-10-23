"""Raven Cartridge Vault 1: writable, single-file cold cartridge.

Store is append-only logically (objects and names), updated atomically after a
verified content-addressed commit. Never executes any archived material.

This is a local-media adapter, NOT a cloud upload client; host authorization
and cloud readback are separate requirements.
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path

SCHEMA='raven.archive-cartridge/1'
ZERO='0'*64
MAX_BLOB=128*1024*1024
MAX_TOTAL=256*1024*1024
MAX_FILES=20000
ID_RE=re.compile(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,180}')
HASH_RE=re.compile(r'[0-9a-f]{64}')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def object_digest(obj):
    return digest(canonical({k:v for k,v in obj.items() if k!='sha256'}).encode('utf-8'))


def insist(condition, msg):
    if not condition: raise ValueError(msg)


def new_index(identity):
    insist(isinstance(identity,dict) and set(identity)=={'birth_sha256','primer_sha256','cartridge_id'},'Identity keys')
    insist(all(isinstance(identity[k],str) and identity[k] for k in identity),'Identity values')
    insist(HASH_RE.fullmatch(identity['birth_sha256']) and HASH_RE.fullmatch(identity['primer_sha256']),'Identity hash')
    head={'schema':SCHEMA,'identity':identity,'generation':0,'previous':None,'entries':{}}
    head['sha256']=object_digest(head)
    return head


def validate_index(index):
    insist(type(index) is dict and set(index)=={'schema','identity','generation','previous','entries','sha256'},'Index shape')
    insist(index['schema']==SCHEMA and index['sha256']==object_digest(index),'Index tampered')
    insist(new_index(index['identity'])['identity']==index['identity'],'Identity mismatch')
    n=index['generation']
    insist(type(n) is int and n>=0,'Generation invalid')
    insist(index['previous'] is None if n==0 else bool(HASH_RE.fullmatch(index['previous'])),'Previous digest invalid')
    insist(type(index['entries']) is dict and len(index['entries'])<MAX_FILES,'Entries invalid')
    for id,info in index['entries'].items():
        insist(ID_RE.fullmatch(id) and '..' not in id.split('/') and '//' not in id,'Unsafe logical id')
        insist(type(info) is dict and set(info)=={'sha256','bytes','mime','kind','tags','description'},'Entry shape')
        insist(HASH_RE.fullmatch(info['sha256']),'Blob digest invalid')
        insist(type(info['bytes']) is int and 0<=info['bytes']<=MAX_BLOB,'Blob length invalid')
        insist(type(info['mime']) is str and len(info['mime'])<100,'Mime invalid')
        insist(type(info['kind']) is str and len(info['kind'])<80,'Kind invalid')
        insist(type(info['description']) is str and len(info['description'])<=300,'Description invalid')
        insist(type(info['tags']) is list and len(info['tags'])<=16 and all(type(t) is str and len(t)<80 for t in info['tags']),'Tags invalid')
    working=[x for x in index['entries'] if x.startswith('ledger/working-epoch/record-')]
    sequence=[]
    for x in working:
        m=re.fullmatch(r'ledger/working-epoch/record-([0-9]{7})-([0-9a-f]{16})\.json',x)
        insist(m is not None,'Malformed working-epoch record ID')
        sequence.append(int(m.group(1)))
    insist(sorted(sequence)==list(range(1,len(sequence)+1)),'Duplicate or non-contiguous working epoch')
    return index


def _history_name(old):
    return f"history/{old['generation']:08d}-{old['sha256']}.json"


def verify(path, expected_identity=None, anchor=None, deep=True):
    """Check all blobs, all retained revisions, and a (possibly old) boot anchor."""
    path=Path(path)
    with zipfile.ZipFile(path,'r') as z:
        infos=z.infolist()
        insist(len(infos)<=MAX_FILES,'Too many ZIP members')
        insist(sum(i.file_size for i in infos)<=MAX_TOTAL,'Decompression bound exceeded')
        names=[i.filename for i in infos]
        insist(len(set(names))==len(names),'Duplicate ZIP member')
        insist(all(x=='INDEX.json' or re.fullmatch(r'blobs/[0-9a-f]{64}',x) or re.fullmatch(r'history/[0-9]{8}-[0-9a-f]{64}\.json',x) for x in names),'Unsafe cartridge member')
        h=validate_index(json.loads(z.read('INDEX.json')))
        if expected_identity is not None: insist(h['identity']==expected_identity,'Different Raven identity')
        all_versions=[h];previous=h['previous']
        for generation in range(h['generation']-1,-1,-1):
            name=f'history/{generation:08d}-{previous}.json'
            insist(name in names,'Missing revision history')
            old=validate_index(json.loads(z.read(name)))
            insist(old['generation']==generation and old['sha256']==previous,'Broken version chain')
            insist(all(k in h['entries'] and h['entries'][k]==v for k,v in old['entries'].items()),'Historical entries rewritten')
            all_versions.append(old);previous=old['previous']
        insist(previous is None,'Genesis not found')
        insist(set(names)=={'INDEX.json'}|{'blobs/'+v['sha256'] for v in h['entries'].values()}|{_history_name(x) for x in all_versions[1:]},'Orphan or missing ZIP members')
        if anchor:insist(anchor in [v['sha256'] for v in all_versions],'Boot root not in cartridge ancestry')
        if deep:
            for info in h['entries'].values():
                payload=z.read('blobs/'+info['sha256'])
                insist(len(payload)==info['bytes'] and digest(payload)==info['sha256'],'Stored blob corruption')
        return h


@contextlib.contextmanager
def file_lock(p):
    p=Path(str(p)+'.lock')
    with p.open('a+b') as file:
        if os.name=='nt':
            import msvcrt
            file.seek(0)
            if not file.read(1):file.write(b'0');file.flush()
            file.seek(0);msvcrt.locking(file.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(file, fcntl.LOCK_EX)
        try:yield
        finally:
            if os.name=='nt':
                file.seek(0);msvcrt.locking(file.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(file,fcntl.LOCK_UN)


def initialize(path,identity):
    path=Path(path).resolve()
    insist(not path.exists(),'Cartridge already exists')
    path.parent.mkdir(parents=True,exist_ok=True)
    index=new_index(identity)
    with file_lock(path):
        insist(not path.exists(),'Cartridge appeared during init')
        with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('INDEX.json',canonical(index))
        verify(path,identity)
    return index


def commit(path,items,expected=None,anchor=None):
    """items: sequence of (id, bytes, mime, kind, tags, description)."""
    path=Path(path).resolve()
    with file_lock(path):
        old=verify(path,anchor=anchor)
        if expected is not None:insist(old['sha256']==expected,'Stale vault index: refuse overwrite')
        entries=dict(old['entries']); payloads={};changes=0
        for id,data,mime,kind,tags,description in items:
            insist(isinstance(id,str) and ID_RE.fullmatch(id) and '..' not in id.split('/') and '//' not in id,'Unsafe id')
            insist(isinstance(data,bytes) and len(data)<=MAX_BLOB,'Invalid or oversized payload')
            hash_value=digest(data)
            info={'sha256':hash_value,'bytes':len(data),'mime':mime,'kind':kind,'tags':list(tags),'description':description}
            if id in entries:
                insist(entries[id]==info,'Immutable id conflict: branch/version required')
                continue
            if id.startswith('ledger/working-epoch/record-'):
                sequence_key=id.rsplit('-',1)[0]+'-'
                insist(not any(x.startswith(sequence_key) for x in entries),
                       'Competing working-epoch record: branch required')
            entries[id]=info;payloads[hash_value]=data;changes+=1
        if not changes:return old
        new={'schema':SCHEMA,'identity':old['identity'],'generation':old['generation']+1,'previous':old['sha256'],'entries':entries}
        new['sha256']=object_digest(new)
        fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name+'.stage-')
        os.close(fd)
        try:
            with zipfile.ZipFile(path,'r') as src, zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
                for name in src.namelist():
                    if name!='INDEX.json':dst.writestr(name,src.read(name))
                dst.writestr(_history_name(old),canonical(old))
                for h,raw in payloads.items():
                    if 'blobs/'+h not in src.namelist():dst.writestr('blobs/'+h,raw)
                dst.writestr('INDEX.json',canonical(new))
            verify(tmp,old['identity'],anchor=anchor)
            with open(tmp,'r+b') as f:os.fsync(f.fileno())
            os.replace(tmp,path)
            if os.name!='nt':
                f=os.open(path.parent,os.O_RDONLY)
                try:os.fsync(f)
                finally:os.close(f)
            return new
        finally:
            if os.path.exists(tmp):os.unlink(tmp)


def retrieve(path,id,anchor=None):
    h=verify(path,anchor=anchor,deep=False)
    insist(id in h['entries'],'Unknown archive item')
    info=h['entries'][id]
    with zipfile.ZipFile(path,'r') as z: data=z.read('blobs/'+info['sha256'])
    insist(len(data)==info['bytes'] and digest(data)==info['sha256'],'Corrupted requested blob')
    return data


def search(path,text,kind=None):
    h=verify(path,deep=False)
    q=text.lower()
    return [{'id':k,**v} for k,v in h['entries'].items() if (kind is None or v['kind']==kind) and q in (k+' '+v['description']+' '+' '.join(v['tags'])).lower()]


def mirror_ledger(path,records,identity,anchor=None):
    """Idempotent repairable per-turn mirror of current (possibly compacted) epoch."""
    from . import engram
    previous=engram.ZERO
    items=[]
    for n,record in enumerate(records,1):
        insist(record['seq']==n,'Ledger sequence invalid')
        insist(record['prev_sha256']==previous,'Ledger prev invalid')
        insist(record['sha256']==engram.hash_record(record),'Ledger record tampered')
        name=f'ledger/working-epoch/record-{n:07d}-{record["sha256"][:16]}.json'
        items.append((name,(canonical(record)+'\n').encode(),'application/json','engram-record',['working','append-only'],f'Working Engram record {n}'))
        previous=record['sha256']
    base=verify(path,identity,anchor=anchor,deep=False)
    return commit(path,items,expected=base['sha256'],anchor=anchor)
