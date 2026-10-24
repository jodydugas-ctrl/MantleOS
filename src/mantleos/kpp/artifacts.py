"""Explicit reviewed carrier samples outside the runtime; integrity is not authority."""
import hashlib
import json
from pathlib import Path

DIRECTORY='examples/engrams/artifacts'
MANIFEST=DIRECTORY+'/MANIFEST.json'
NAMES={'raven-fresh.vcw','raven-fresh.vcw.png'}

def inventory(root):
    root=Path(root).resolve(); folder=root/DIRECTORY
    if not folder.exists(): return {}
    for p in (folder,*folder.parents):
        if p==root.parent: break
        if p.is_symlink() or (p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400):
            raise ValueError('Unsafe reviewed artifact directory')
    manifest=root/MANIFEST
    if manifest.is_symlink() or getattr(manifest.lstat(),'st_file_attributes',0)&0x400:
        raise ValueError('Unsafe artifact manifest')
    value=json.loads((root/MANIFEST).read_text(encoding='utf-8'))
    if value.get('schema')!='kpp.reviewed-engram-examples/1' or value.get('review')!='PUBLIC_REVIEWED' or set(value.get('files',{}))!=NAMES:
        raise ValueError('Invalid reviewed Engram artifact inventory')
    if {p.name for p in folder.iterdir()} != NAMES|{'MANIFEST.json'}:
        raise ValueError('Unlisted Engram example artifacts')
    result={}
    for name,pin in value['files'].items():
        p=folder/name
        if p.is_symlink() or not p.is_file() or getattr(p.lstat(),'st_file_attributes',0)&0x400:
            raise ValueError('Unsafe example artifact')
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if actual!=pin: raise ValueError('Engram example artifact drift: '+name)
        result[DIRECTORY+'/'+name]=actual
    result[MANIFEST]=hashlib.sha256((root/MANIFEST).read_bytes()).hexdigest()
    return result
