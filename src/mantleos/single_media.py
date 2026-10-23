"""Raven single-physical-file VCW carrier binding and atomic republishing.

Embedded ARCHIVE.rvcar contains cold artifacts; every verified hosted commit can
atomically replace the original handed-off VCW when the extracted Body is bound
explicitly to a writable carrier. An unbound Body remains useful but MUST report
that its source VCW was not updated.

No credentials, network operations, or user-private data leave this file.
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from . import cartridge, vault_store
from .transactions import atomic_bytes

SCHEMA='raven.single-carrier-binding/1'

def digest_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def path_for_binding(body):
    root=Path(body).resolve()
    return root.parent/('.'+root.name+'.carrier-binding.json')

def embedded_path(body):
    root=Path(body).resolve()
    ref=json.loads((root/'VAULT-REF.json').read_text('utf-8'))
    if ref.get('schema')!='raven.vault-binding/1':raise ValueError('Unsupported VAULT-REF')
    name=ref['file_name']
    if name!=Path(name).name or not name.endswith('.rvcar'):raise ValueError('Unsafe vault filename')
    if ref.get('location')!='embedded':raise ValueError('Not single-carrier embedded storage')
    return root/name

def _matches_exact_carrier(root,carrier):
    root=Path(root).resolve()
    if not Path(carrier).is_file():raise FileNotFoundError('Carrier file absent')
    actual={p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    with zipfile.ZipFile(carrier) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate carrier member')
        if set(z.namelist())!=set(actual):raise ValueError('Carrier/body inventory mismatch')
        for name,p in actual.items():
            if vault_store.digest(z.read(name)) != digest_file(p):
                raise ValueError('Carrier and extracted Body differ: '+name)
    return True

def bind(body,carrier):
    """Explicitly connect a freshly extracted, identical Body to its VCW file."""
    root=Path(body).resolve(); path=Path(carrier).resolve()
    if path.is_relative_to(root):raise ValueError('Carrier cannot be inside the unpacked Body')
    from . import vault_auto
    cartridge.verify(root)
    ref=json.loads((root/'VAULT-REF.json').read_text('utf-8'))
    vault_store.verify(embedded_path(root),vault_auto.mounted_identity(root),anchor=ref['root_sha256'])
    _matches_exact_carrier(root,path)
    entry={'schema':SCHEMA,'carrier_path':str(path),'carrier_sha256':digest_file(path),
           'identity':vault_auto.mounted_identity(root)}
    dest=path_for_binding(root)
    if dest.exists():
        old=json.loads(dest.read_text('utf-8'))
        if old!=entry:raise ValueError('Existing binding differs; use a clean mount')
    atomic_bytes(dest,(json.dumps(entry,sort_keys=True,indent=2)+'\n').encode('utf-8'))
    return {'status':'BOUND','cartridge':str(path),'sha256':entry['carrier_sha256']}

def commit_extracted(body):
    """Track embedded vault in Body manifest and publish to bound VCW, if any."""
    root=Path(body).resolve()
    from .lifecycle import finalize
    finalize(root)
    cartridge.verify(root)
    binding=path_for_binding(root)
    if not binding.is_file():
        return {'status':'EMBEDDED_WORKDIR_UPDATED_EXPORT_REQUIRED','handoff_updated':False}
    import time
    from .vault_store import file_lock
    entry=json.loads(binding.read_text('utf-8'))
    if entry.get('schema')!=SCHEMA or entry.get('identity')!=_mounted_identity(root):
        raise ValueError('Carrier binding identity invalid')
    carrier=Path(entry['carrier_path']).resolve()
    if carrier.is_relative_to(root) or carrier.suffix.lower()!='.vcw':raise ValueError('Unsafe carrier destination')
    # Separate lock serializes competing publishers. The SHA check refuses stale replicas.
    with file_lock(carrier):
        if not carrier.exists() or digest_file(carrier)!=entry['carrier_sha256']:
            raise ValueError('STALENESS: another session changed the single carrier')
        fd,stage=tempfile.mkstemp(prefix='.'+carrier.name+'.stage-',suffix='.vcw',dir=carrier.parent)
        os.close(fd);os.unlink(stage)
        try:
            cartridge.pack(root,stage)
            # Independent actual unzip/verify, not merely a digest of the new ZIP.
            with tempfile.TemporaryDirectory(prefix='raven-single-check-',dir=carrier.parent) as td:
                restored=Path(td)/'body'
                cartridge.unpack(stage,restored)
                rr=json.loads((restored/'VAULT-REF.json').read_text('utf-8'))
                vault_store.verify(embedded_path(restored),_mounted_identity(restored),anchor=rr['root_sha256'])
            new_hash=digest_file(stage)
            with open(stage,'r+b') as f:os.fsync(f.fileno())
            os.replace(stage,carrier)
            if os.name!='nt':
                descriptor=os.open(carrier.parent,os.O_RDONLY)
                try:os.fsync(descriptor)
                finally:os.close(descriptor)
            entry['carrier_sha256']=new_hash
            atomic_bytes(binding,(json.dumps(entry,sort_keys=True,indent=2)+'\n').encode('utf-8'))
            return {'status':'SINGLE_CARRIER_UPDATED_VERIFIED','handoff_updated':True,
                    'carrier_sha256':new_hash,'cartridge':str(carrier)}
        finally:
            Path(stage).unlink(missing_ok=True)

def _mounted_identity(root):
    from . import vault_auto
    return vault_auto.mounted_identity(root)
