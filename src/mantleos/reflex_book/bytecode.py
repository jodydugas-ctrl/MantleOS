"""Fixed framed binary with SHA-256 integrity, not a signature or authority."""
import hashlib
import struct
from .canonical import dumps,loads
from .compiler import compile_ir
from .errors import refuse, ReflexError

MAGIC=b'RFX1'
MAX_PAYLOAD=65536


def encode(bytecode):
    data=dumps(bytecode)
    if len(data)>MAX_PAYLOAD:
        refuse('E_SIZE','bytecode too large')
    return MAGIC+struct.pack('>I',len(data))+hashlib.sha256(data).digest()+data


def decode(raw):
    if type(raw) is not bytes or len(raw)<40 or raw[:4]!=MAGIC:
        refuse('E_BINARY','invalid binary header')
    size=struct.unpack('>I',raw[4:8])[0]
    if size>MAX_PAYLOAD or len(raw)!=size+40:
        refuse('E_BINARY','invalid framed length')
    payload=raw[40:]
    if hashlib.sha256(payload).digest()!=raw[8:40]:
        refuse('E_INTEGRITY','binary digest mismatch')
    bc=loads(payload)
    if dumps(bc) != payload:
        refuse('E_CANONICAL', 'executable payload must be exact canonical JSON')
    if type(bc) is not dict or set(bc) != {'schema','abi','program_sha256','ir','instructions'}:
        refuse('E_BINARY','incorrect bytecode structure')
    expected=compile_ir(bc['ir'])
    if dumps(expected)!=dumps(bc):
        refuse('E_INTEGRITY','bytecode and canonical IR disagree')
    return bc


def disassemble(raw):
    bc=decode(raw)
    return {'program_sha256':bc['program_sha256'],'abi':bc['abi'],
            'instructions':[{'pc':i,'op':ins[0],'args':ins[1:]}
                            for i,ins in enumerate(bc['instructions'])]}
