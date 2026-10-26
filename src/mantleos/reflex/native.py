"""REFLEX candidates as data in existing verified Bodies; no executable profile.

Use maintained lifecycle/Cartridge/Chroma ports, never import carried runtime.
Only fresh Bodies can be packed here; no mutation of an existing organism.
"""
import hashlib
from pathlib import Path
import tempfile
import zipfile

from .canonical import dumps
from .carriers.contract import checked_program, make_manifest, decode_manifest, verify_digest, report
from .errors import ReflexError, refuse

ATTACHMENT='REFLEX-DATA'
FILES={'program.json','manifest.json'}
SCHEMA='mantle.reflex-body-attachment/0.1-experimental'
ID='reflex-native-body/0.1-experimental'
MAX_NATIVE_BYTES=16*1024*1024


def manifest(payload):
    value=make_manifest(payload,'reflex-raw/0.1-experimental')
    return {**value,'schema':SCHEMA,'carrier_id':ID}


def make_body(payload, output, *, identity=None):
    """Construct a new Body, with data-only IR and no inherited identity/history."""
    checked_program(payload)
    from ..kpp.engram_carriers import fresh_body
    from .. import lifecycle
    fresh_body(output,identity=identity)
    folder=Path(output)/ATTACHMENT
    folder.mkdir()
    (folder/'program.json').write_bytes(payload)
    (folder/'manifest.json').write_bytes(dumps(manifest(payload)))
    lifecycle.finalize(output)


def pack(payload, output, carrier):
    from ..kpp.engram_carriers import encode
    if carrier not in ('cartridge','chroma'):
        refuse('E_CARRIER','unsupported native carrier')
    output=Path(output)
    if output.exists() or output.is_symlink():
        refuse('E_IO','output already exists')
    if output.suffix.lower()!=('.vcw' if carrier=='cartridge' else '.png'):
        refuse('E_CARRIER','native output extension does not match carrier')
    with tempfile.TemporaryDirectory(prefix='reflex-native-pack-') as temporary:
        body=Path(temporary)/'body'
        make_body(payload,body)
        encode(body,output,'vcw' if carrier=='cartridge' else 'chroma')
    return {'status':'PACKED_UNTRUSTED_DATA','carrier_id':ID,'carrier':carrier,
            'program_sha256':hashlib.sha256(payload).hexdigest(),
            'authorized':False,'installed':False,'executed':False}


def extract(path, carrier, expected_digest):
    """Verify native transport using local trusted code; return only inert IR bytes."""
    from .. import cartridge,chromamem
    path=Path(path)
    if carrier not in ('cartridge','chroma'):
        refuse('E_CARRIER','unsupported native carrier')
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_NATIVE_BYTES:
        refuse('E_SIZE','native carrier missing, unsafe or over byte budget')
    try:
        with tempfile.TemporaryDirectory(prefix='reflex-native-read-') as temporary:
            body=Path(temporary)/'body'
            if carrier=='cartridge':cartridge.unpack(path,body)
            else:chromamem.extract_body(path,body)
            # Both maintained restore ports verify the complete Body before return.
            folder=body/ATTACHMENT
            if not folder.is_dir() or {p.name for p in folder.iterdir()}!=FILES:
                refuse('E_CARRIER','native attachment must contain exactly two data files')
            if any(not p.is_file() or p.is_symlink() for p in folder.iterdir()):
                refuse('E_CARRIER','unsafe native attachment member')
            if (folder/'program.json').stat().st_size>65536 or (folder/'manifest.json').stat().st_size>4096:
                refuse('E_SIZE','native attachment exceeds byte bounds')
            payload=(folder/'program.json').read_bytes()
            checked_program(payload)
            declaration=decode_manifest((folder/'manifest.json').read_bytes())
            if dumps(declaration)!=dumps(manifest(payload)):
                refuse('E_INTEGRITY','native attachment is not the exact data-only manifest')
            verify_digest(payload,expected_digest)
            return payload,report(ID,payload,declaration)
    except ReflexError:
        raise
    except (ValueError,KeyError,TypeError,OSError,zipfile.BadZipFile,RuntimeError) as error:
        refuse('E_CARRIER','invalid native Body or attachment: '+type(error).__name__)


def unpack(path, output, carrier, expected_digest):
    output=Path(output)
    if output.exists() or output.is_symlink():
        refuse('E_IO','output already exists')
    payload,result=extract(path,carrier,expected_digest)
    output.parent.mkdir(parents=True,exist_ok=True)
    from ..reflex_book.cli import _write_new
    _write_new(output,payload)
    return {**result,'path':str(output)}
