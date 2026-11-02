"""Trusted operator tooling. Run outside courier tools and model-visible storage."""
import argparse
import json
import os
from pathlib import Path
from .skin import Skin, canon, sha

def import_legacy_skin(source, output, key, *, selector):
    """Explicit historical raven-skin/1 import, never selected by filename alone.

    Entire decrypted SQLite image stays in trusted Body memory. Carried source
    verification can use the controller's protected TEMP area. No carried code runs.
    Native v0.3 post-migration vaults require their own adapter and are refused.
    """
    import base64
    import sqlite3
    import struct
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from .skin import crypto
    from .journal import Journal
    raw=Path(source).read_bytes()
    magic=b'RAVEN-SKIN\x00\x01'
    if len(raw)>128*1024*1024 or not raw.startswith(magic) or len(raw)<len(magic)+4:
        raise ValueError('Explicit raven-skin/1 input required')
    size=struct.unpack('>I',raw[len(magic):len(magic)+4])[0]
    end=len(magic)+4+size
    if size>4096 or len(raw)<end+16:raise ValueError('Malformed historical Skin')
    header=json.loads(raw[len(magic)+4:end])
    if (set(header)!={'format','cipher','kdf','nonce','salt'} or
        (header['format'],header['cipher'],header['kdf'])!=('raven-skin/1','AES-256-GCM','scrypt')):
        raise ValueError('Unsupported historical Skin format')
    nonce=base64.b64decode(header['nonce'],altchars=b'-_',validate=True)
    salt=base64.b64decode(header['salt'],altchars=b'-_',validate=True)
    if len(nonce)!=12 or len(salt)!=16:raise ValueError('Invalid historical Skin parameters')
    legacy_key=Scrypt(salt=salt,length=32,n=2**17,r=8,p=1).derive(selector.encode())
    plain=crypto()[0](legacy_key).decrypt(nonce,raw[end:],raw[:end])
    if not plain.startswith(b'SQLite format 3\x00'):raise ValueError('Historical payload is not SQLite')
    # Use current trusted Journal verification, with no historical runtime import.
    journal=Journal.__new__(Journal)
    journal.path=Path('/private-in-memory-legacy-journal')
    journal.db=sqlite3.connect(':memory:',isolation_level=None)
    try:
        journal.db.execute('PRAGMA trusted_schema=OFF')
        journal.db.execute('PRAGMA temp_store=MEMORY')
        journal.db.deserialize(plain)
        journal.verify()
        if journal.db.execute('SELECT COUNT(*) FROM pending').fetchone()[0]:
            raise ValueError('Resolve historical pending encounters before import')
        with Skin.create(output,key,journal._meta('primer'),identity=journal._meta('identity'),
                         persona=journal._meta('persona')) as skin:
            skin.put_object('journal-origin',plain)
            skin.put_object('historical-skin-origin',raw)
            skin.put_object('origin-provenance',canon({'format':'raven-skin/1',
                'sha256':sha(raw),'journal_sha256':sha(plain),'history_mapping':'exact canonical Journal records'}).encode())
            for record in journal.records:skin.append_record(record,expected_head=skin.head)
            return {'format':'mantle.private-skin/1','imported_format':'raven-skin/1',
                    'head':skin.head,'records':skin.count}
    finally:journal.close()

def import_journal(source, output, key):
    from .journal import Journal
    with Journal(source) as journal:
        if journal.db.execute('PRAGMA journal_mode').fetchone()[0].lower() != 'delete':
            raise ValueError('Import requires a closed single-file Journal export without WAL sidecars')
        journal.db.execute('BEGIN IMMEDIATE')
        journal.verify()  # Pin exact history and bytes while cooperating writers are excluded.
        if journal.db.execute('SELECT COUNT(*) FROM pending').fetchone()[0]:
            raise ValueError('Resolve pending Journal encounters before import')
        origin=Path(source).read_bytes()
        with Skin.create(output,key,journal._meta('primer'),identity=journal._meta('identity'),
                         persona=journal._meta('persona')) as skin:
            # Preserve the entire verified source carrier, including all executable snapshots,
            # founding bytes, bindings, attachments and bootstrap. No carried code is executed.
            skin.put_object('journal-origin',origin)
            skin.put_object('origin-provenance',canon({'format':'mantle.journal-engram/1',
                'sha256':sha(origin)}).encode())
            for r in journal.records: skin.append_record(r,expected_head=skin.head)
            return {'format':'mantle.private-skin/1','head':skin.head,'records':skin.count}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='op',required=True)
    for op in ('verify','export','import-journal','import-legacy-skin','import-native-prototype','recover'):
        p=sub.add_parser(op)
        p.add_argument('--key-file',required=True,help='Owner-protected 32-byte key, outside courier access')
        p.add_argument('--input',required=True)
        if op in {'export','import-journal','import-legacy-skin','import-native-prototype'}: p.add_argument('--output',required=True)
        if op in {'import-legacy-skin','import-native-prototype'}:p.add_argument('--legacy-selector-file',required=True)
        if op=='import-native-prototype':
            p.add_argument('--legacy-skin',required=True)
            p.add_argument('--native-key-file',required=True)
    args=parser.parse_args(argv)
    key=Path(args.key_file).read_bytes()
    if args.op=='import-journal': result=import_journal(args.input,args.output,key)
    elif args.op=='import-legacy-skin':
        result=import_legacy_skin(args.input,args.output,key,
                                 selector=Path(args.legacy_selector_file).read_text('utf8').strip())
    elif args.op=='import-native-prototype':
        from .prototype_import import import_native
        result=import_native(args.input,args.legacy_skin,args.output,key,
            master=Path(args.native_key_file).read_bytes(),
            selector=Path(args.legacy_selector_file).read_text('utf8').strip())
    else:
        with Skin(args.input,key) as skin:
            if args.op=='export': result=skin.export(args.output)
            else:
                # Operator verification checks every encrypted object and canonical record.
                for name, in skin.db.execute('SELECT id FROM objects'): skin.object(name)
                for seq in range(1,skin.count+1): skin.record(seq)
                result={'result':'VERIFIED',**skin.checkpoint()}
    print(canon(result))
    return 0
