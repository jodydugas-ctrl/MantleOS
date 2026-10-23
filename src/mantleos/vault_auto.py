"""Hosted turn-end local-media mirroring for a paired Raven vault cartridge.

No credentials or network. A failed sidecar mirror NEVER rolls back the already
committed canonical local turn; the result explicitly reports unsynced status.
"""
from __future__ import annotations
import json
from pathlib import Path
from . import birth, cartridge, engram, primer, vault_store


def mounted_identity(body):
    root=Path(body)
    b=birth.validate_birth(json.loads((root/'BIRTH.json').read_text(encoding='utf-8')))
    p=primer.load_primer(root)
    return {'birth_sha256':b['birth_sha256'], 'primer_sha256':p['sha256'],
        'cartridge_id':json.loads((root/'CARTRIDGE.json').read_text(encoding='utf-8'))['bio_software']['id']}


def sync_committed(body):
    root=Path(body).resolve()
    config=root/'VAULT-REF.json'
    if not config.exists():return {'status':'NO_PAIRED_VAULT'}
    try:
        ref=json.loads(config.read_text(encoding='utf-8'))
        if ref.get('schema')!='raven.vault-binding/1':raise ValueError('Unsupported binding')
        filename=ref['file_name']
        if filename != Path(filename).name or not filename.endswith('.rvcar'):raise ValueError('Unsafe cartridge filename')
        vault=(root/filename) if ref.get('location')=='embedded' else (root.parent/filename)
        if not vault.is_file():raise FileNotFoundError('Paired vault not mounted beside Engram')
        identity=mounted_identity(root)
        if ref['identity']!=identity:raise ValueError('Identity mismatch')
        before=vault_store.verify(vault,identity,anchor=ref['root_sha256'],deep=False)
        records=engram.read(root/'ENGRAM.jsonl')
        after=vault_store.mirror_ledger(vault,records,identity,anchor=ref['root_sha256'])
        if ref.get('location')=='embedded':
            from . import single_media
            publication=single_media.commit_extracted(root)
        else:
            publication={'status':'SIDE_CAR_ONLY','handoff_updated':False}
        return {'status':'SINGLE_CARRIER_VERIFIED' if publication.get('handoff_updated') else
                     'EMBEDDED_CARTRIDGE_LOCAL_ONLY' if ref.get('location')=='embedded' else 'LOCAL_CARTRIDGE_VERIFIED',
           'records':len(records), 'generation':after['generation'], 'index_sha256':after['sha256'],
           'changed':before['sha256']!=after['sha256'], 'publication':publication,
           'cloud_uploaded':False}
    except (OSError,ValueError,KeyError,RuntimeError) as e:
        return {'status':'LOCAL_TURN_COMMITTED_VAULT_NOT_SYNCED','error':str(e),'cloud_uploaded':False}


def recover_startup(body):
    """Recover the missing working-epoch suffix from an updated vault.

    Does not touch the original archived epoch, silently merge divergent records,
    or claim cloud authority. A missing sidecar leaves the boot checkpoint intact.
    """
    import zipfile
    root=Path(body).resolve()
    config=root/'VAULT-REF.json'
    if not config.exists():return {'status':'NO_PAIRED_VAULT'}
    try:
        ref=json.loads(config.read_text('utf-8'))
        name=ref['file_name']
        if name!=Path(name).name or not name.endswith('.rvcar'):raise ValueError('Unsafe vault filename')
        source=(root/name) if ref.get('location')=='embedded' else (root.parent/name)
        if not source.is_file():return {'status':'VAULT_UNAVAILABLE_LOCAL_BOOT_ONLY'}
        identity=mounted_identity(root)
        if ref['identity']!=identity:raise ValueError('Mismatched boot identity')
        head=vault_store.verify(source,identity,anchor=ref['root_sha256'])
        prefix='ledger/working-epoch/record-'
        logical=sorted(k for k in head['entries'] if k.startswith(prefix))
        restored=[]
        with zipfile.ZipFile(source,'r') as z:
            for i,key in enumerate(logical,1):
                info=head['entries'][key]
                data=z.read('blobs/'+info['sha256'])
                if len(data)!=info['bytes'] or vault_store.digest(data)!=info['sha256']:
                    raise ValueError('Corrupted working epoch')
                rec=json.loads(data.decode('utf-8'))
                expected_prev=engram.ZERO if i==1 else restored[-1]['sha256']
                if rec['seq']!=i or rec.get('prev_sha256')!=expected_prev or rec['sha256']!=engram.hash_record(rec):
                    raise ValueError('Corrupted or diverged archived record chain')
                if key!=f'ledger/working-epoch/record-{i:07d}-{rec["sha256"][:16]}.json':
                    raise ValueError('Noncanonical working record ID')
                restored.append(rec)
        current=engram.read(root/'ENGRAM.jsonl')
        if len(current)>len(restored):
            return {'status':'LOCAL_AHEAD_OF_ARCHIVE','local':len(current),'archived':len(restored)}
        if current!=restored[:len(current)]:
            raise ValueError('Divergent local archive branch')
        if len(restored)==len(current):return {'status':'ARCHIVE_ALREADY_LOADED','records':len(current),'generation':head['generation']}
        original=(root/'ENGRAM.jsonl').read_bytes()
        try:
            from .transactions import atomic_bytes
            from .lifecycle import finalize
            new=''.join(engram.canonical(rec)+'\n' for rec in restored).encode('utf-8')
            atomic_bytes(root/'ENGRAM.jsonl',new)
            finalize(root)
            cartridge.verify(root)
        except Exception:
            from .transactions import atomic_bytes
            from .lifecycle import finalize
            atomic_bytes(root/'ENGRAM.jsonl',original)
            finalize(root)
            raise
        return {'status':'ARCHIVE_RECOVERED_AT_BOOT','records':len(restored),'new_records':len(restored)-len(current),'generation':head['generation']}
    except (OSError,ValueError,KeyError,RuntimeError,zipfile.BadZipFile) as e:
        return {'status':'VAULT_RECOVERY_BLOCKED','error':str(e)}
