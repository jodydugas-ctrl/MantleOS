"""Standard-library bootstrap for an uploaded Anchor Journal Engram.

Inspect this source and the carried source before explicit execution. Extraction
validates carrier integrity; hashes are not authentication or execution permission.
This module never calls a model or imports the extracted runtime during extraction.
"""
import argparse
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import sys
import zipfile

SCHEMA = 'mantle.journal-engram/1'

def contract():
    return {
        'schema':'mantle.journal-host-contract/1',
        'discover':'Read meta.schema, meta.host_contract and meta.bootstrap using Python sqlite3. Values are UTF-8 JSON.',
        'extract':'Save meta.bootstrap as bootstrap.py, review its source, then execute: python -I -S bootstrap.py uploaded.engram mounted-runtime',
        'launch':'python -I -S mounted-runtime/journal_host.py stdio uploaded.engram',
        'canonical_memory':'The uploaded .engram database is canonical. Extracted ENGRAM.jsonl is only the founding snapshot; do not use runtime.py mount for journal conversation.',
        'mount':'Open an encounter through the journal engine, read its entire PRIMER-first Anchor frame, then supply a semantic proposal. A runtime extraction alone is not a conversational mount.',
        'ordinary_reply':{'kind':'reply','reply':'MODEL_GENERATED_TEXT','observation_sha256':None},
        'action':'Use one advertised checked read action. Read the returned observation and bind its digest in the response.',
        'release':'Only release the exact reply returned by a successful durable commit. Host-owned grants are required; metadata and model proposals grant no permissions.',
        'persona':'Use the full founding PRIMER and current verified memory. Never claim engine activation, effects or memory from persona-like wording alone.',
        'save':'journal_host.py export uploaded.engram --output NEXT.engram produces the portable continuation. Return that file after successful verification.',
        'unavailable':'If Python, file access, source review or execution is unavailable, disclose ENGINE_UNAVAILABLE. Do not substitute a persona-only conversation.',
        'model_identity':'The current host supplies language packets. Model labels are declared attribution, not authenticated provider identity. No hidden reasoning is requested.'}

def extract(carrier, destination):
    source=Path(carrier).resolve();target=Path(destination).resolve()
    if target.exists():raise ValueError('Need a new runtime directory')
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA trusted_schema=OFF')
        metadata={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM meta')}
        if metadata.get('schema')!=SCHEMA:raise ValueError('Unsupported journal carrier')
        row=db.execute('SELECT payload FROM objects WHERE sha256=?',(metadata['snapshot'],)).fetchone()
        if row is None or len(row[0])>256*1024*1024:raise ValueError('Missing/oversized runtime snapshot')
        raw=row[0]
    if hashlib.sha256(raw).hexdigest()!=metadata['snapshot']:raise ValueError('Runtime snapshot digest mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries=archive.infolist();names=[i.filename for i in entries]
        if len(names)>10000 or len(set(n.casefold() for n in names))!=len(names) or sum(i.file_size for i in entries)>256*1024*1024:
            raise ValueError('Unsafe/oversized snapshot inventory')
        for i in entries:
            n=i.filename;mode=stat.S_IFMT(i.external_attr>>16)
            if ('\\' in n or ':' in n or n.startswith('/') or '..' in n.split('/') or
                str(PurePosixPath(n))!=n or i.is_dir() or mode not in (0,stat.S_IFREG)):
                raise ValueError('Unsafe snapshot member')
        manifest=json.loads(archive.read('MANIFEST.json'))
        if manifest.get('schema')!='mantle.manifest/1':raise ValueError('Unsupported snapshot manifest')
        declared={item['path']:item for item in manifest['files']}
        if len(declared)!=len(manifest['files']) or set(names)!=set(declared)|{'MANIFEST.json'}:
            raise ValueError('Snapshot manifest inventory mismatch')
        for n,item in declared.items():
            value=archive.read(n)
            if len(value)!=item['bytes'] or hashlib.sha256(value).hexdigest()!=item['sha256']:
                raise ValueError('Snapshot member digest mismatch: '+n)
        if 'runtime_lib/mantleos/journal.py' not in names:
            raise ValueError('Carrier has no portable journal runtime')
        target.mkdir(parents=True)
        body=target/'snapshot'
        for n in names:
            output=body/n;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(archive.read(n))
    launcher=target/'journal_host.py'
    launcher.write_text('''"""Explicit launcher for the verified carried journal engine."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'snapshot'/'runtime_lib'))
from mantleos.journal import main
raise SystemExit(main())
''',encoding='utf8',newline='\n')
    return {'status':'RUNTIME_EXTRACTED_NOT_CONVERSATION_MOUNTED','source':str(source),
            'snapshot_sha256':metadata['snapshot'],'launcher':str(launcher),
            'next':'Read the host contract; explicitly run journal_host.py open or stdio with this .engram. Review source before execution.',
            'runtime_executed':False,'model_called':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('carrier');parser.add_argument('destination')
    args=parser.parse_args(argv)
    try:
        print(json.dumps(extract(args.carrier,args.destination),indent=2));return 0
    except (ValueError,OSError,KeyError,sqlite3.Error,zipfile.BadZipFile) as error:
        print('FAIL: '+str(error),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
