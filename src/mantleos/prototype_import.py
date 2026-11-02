"""Explicit trusted-operator adapter for raven.sealed-records/1.

Imports data only. Never imports or executes the prototype's vendored runtime.
Native events gain canonical migration records with explicit format provenance;
the original native ciphertext and founding carrier remain encrypted origin objects.
"""
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
import uuid
from . import engram
from .skin import Skin, canon, crypto, sha

NATIVE = 'raven.sealed-records/1'

def import_native(vault, legacy_skin, output, key, *, master, selector, public_identity=None):
    from .skin_cli import import_legacy_skin
    AESGCM,HKDF,hashes=crypto()
    if not isinstance(master,bytes) or len(master)!=32:raise ValueError('Explicit native vault master required')
    def derive(label):
        return HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=b'raven-v03/'+label).derive(master)
    chain,index_manifest=derive(b'chain'),derive(b'manifest')
    cipher=AESGCM(derive(b'payload'))
    path=Path(vault).resolve(strict=True)
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,isolation_level=None)
    try:
        db.execute('PRAGMA trusted_schema=OFF')
        db.execute('BEGIN')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Native vault integrity failure')
        meta=dict(db.execute('SELECT k,v FROM meta'))
        if meta.get('schema')!=NATIVE:raise ValueError('Explicit raven.sealed-records/1 input required')
        rows=db.execute('SELECT seq,kind,prev,head,nonce,cipher FROM events ORDER BY seq').fetchall()
        manifest={'meta':db.execute('SELECT k,v FROM meta ORDER BY k').fetchall(),
            'events':[(s,k,p,h,n.hex(),sha(c)) for s,k,p,h,n,c in rows],
            'postings':[(x.hex(),s) for x,s in db.execute('SELECT term,seq FROM postings ORDER BY term,seq')],
            'requests':[(k.hex(),o,b,t) for k,o,b,t in db.execute('SELECT request_key,open_seq,observation_seq,turn_seq FROM requests ORDER BY request_key')]}
        expected=hmac.new(index_manifest,canon(manifest).encode(),hashlib.sha256).hexdigest()
        saved=db.execute('SELECT mac FROM seal WHERE id=1').fetchone()
        if saved is None or not hmac.compare_digest(saved[0],expected):raise ValueError('Native vault metadata/index authentication failure')
        previous=meta['legacy_head'];payloads=[]
        for count,(seq,kind,prev,head,nonce,encrypted) in enumerate(rows,1):
            raw=canon({'prev':prev,'seq':seq,'kind':kind,'nonce':nonce.hex(),'cipher_sha256':sha(encrypted)}).encode()
            expected=hmac.new(chain,raw,hashlib.sha256).hexdigest()
            if seq!=count or prev!=previous or not hmac.compare_digest(head,expected):
                raise ValueError('Native vault chain authentication failure')
            aad=canon({'schema':NATIVE,'identity':meta['identity'],'seq':seq,'kind':kind,'prev':prev}).encode()
            payloads.append(json.loads(cipher.decrypt(nonce,encrypted,aad)))
            previous=head
        if previous!=meta['current_head'] or len(rows)!=int(meta['event_count']):raise ValueError('Native vault head mismatch')
        # A backed-up image is consistent even when the original uses WAL.
        snapshot=sqlite3.connect(':memory:')
        try:
            db.backup(snapshot)
            origin=snapshot.serialize()
        finally:snapshot.close()
    finally:db.close()
    imported=int(meta['import_count'])
    if imported!=int(meta['legacy_records']) or imported>len(rows):raise ValueError('Native legacy count mismatch')
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    staging=output.with_name(output.name+'.migration-'+uuid.uuid4().hex+'.partial')
    import_legacy_skin(legacy_skin,staging,key,selector=selector)
    with Skin(staging,key) as skin:
        constitution=json.loads(skin.object('constitution'))
        if (constitution['identity']!=meta['identity'] or constitution['primer'].get('sha256')!=meta['primer_sha256'] or
            skin.head!=meta['legacy_head'] or skin.count!=imported):
            raise ValueError('Native vault and legacy founding/history disagree; candidate requires review')
        for i in range(imported):
            old=skin.record(i+1);value=payloads[i]
            if (rows[i][1]!='legacy.'+old['type'] or value.get('legacy_record_sha256')!=old['sha256'] or
                value.get('body')!=old['body'] or value.get('record_type')!=old['type']):
                raise ValueError('Native imported prefix differs from canonical origin')
        skin.put_object('prototype-native-origin',origin)
        if public_identity is not None:
            if public_identity.get('identity')!=constitution['identity']:raise ValueError('Native public identity mismatch')
            skin.put_object('prototype-public-identity',canon(public_identity).encode())
        for row,payload in zip(rows[imported:],payloads[imported:]):
            seq,kind,prev,native_head,nonce,encrypted=row
            provenance={'schema':NATIVE,'seq':seq,'kind':kind,'head':native_head,
                        'legacy_anchor':meta['legacy_head'],'payload':payload}
            body={'native':provenance}
            rec_type='prototype-event'
            if kind=='turn.committed':
                # This mapping is explicit; original native bytes remain retained above.
                body.update(request_id=payload['request_id'],user=payload['user'],reply=payload['reply'],
                            model_id=payload['model_id'],observation_sha256=payload['observation_sha256'])
                rec_type='turn'
            record={'schema':'mantle.engram-record/1','seq':skin.count+1,'id':uuid.uuid4().hex,
                'type':rec_type,'source':'prototype-bridge','body':body,'prev_sha256':skin.head}
            record['sha256']=engram.hash_record(record)
            skin.append_record(record,expected_head=skin.head)
        skin.put_object('prototype-migration',canon({'schema':NATIVE,'native_head':previous,
            'original_records':imported,'native_events':len(rows),'mapped_events':len(rows)-imported,
            'origin_sha256':sha(origin),'new_canonical_head':skin.head,
            'authorization':'Owner import only; old grants and approvals confer no new authority'}).encode())
        result={'format':'mantle.private-skin/1','imported_format':NATIVE,'head':skin.head,'records':skin.count}
        skin.export(output)
    staging.unlink()
    return result
