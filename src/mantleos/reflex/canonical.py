"""Strict I-JSON subset: integer-only numbers, NFC strings, no duplicates."""
import hashlib
import json
import unicodedata
from .errors import refuse

MAX_SOURCE_BYTES = 65536


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            refuse('E_DUPLICATE_KEY', f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _not_number(text):
    refuse('E_NUMBER', f'non-integer JSON number is not supported: {text[:32]}')


def _check(value, depth=0):
    if depth > 64:
        refuse('E_DEPTH', 'JSON nesting too deep')
    if value is None or type(value) in (bool,):
        return
    if type(value) is int:
        if not -(2**63) <= value < 2**63:
            refuse('E_NUMBER', 'integer outside signed 64-bit range')
        return
    if type(value) is str:
        try:
            value.encode('utf-8', errors='strict')
        except UnicodeEncodeError:
            refuse('E_TEXT', 'unpaired Unicode surrogate')
        if unicodedata.normalize('NFC', value) != value:
            refuse('E_TEXT', 'strings must be Unicode NFC')
        return
    if type(value) is list:
        for item in value:
            _check(item, depth + 1)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                refuse('E_SHAPE', 'object keys must be strings')
            _check(key, depth + 1)
            _check(item, depth + 1)
        return
    refuse('E_TYPE', 'only JSON values with integer numbers are supported')


def loads(raw: bytes | str):
    if type(raw) is bytes:
        if len(raw) > MAX_SOURCE_BYTES:
            refuse('E_SIZE', 'JSON input too large')
        try:
            source = raw.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            refuse('E_TEXT', 'invalid UTF-8')
    elif type(raw) is str:
        source = raw
        try:
            encoded = source.encode('utf-8', errors='strict')
        except UnicodeEncodeError:
            refuse('E_TEXT', 'unpaired Unicode surrogate in source')
        if len(encoded) > MAX_SOURCE_BYTES:
            refuse('E_SIZE', 'JSON input too large')
    else:
        refuse('E_TYPE', 'JSON source must be bytes or str')
    try:
        value = json.loads(source, object_pairs_hook=_pairs, parse_float=_not_number,
                           parse_constant=_not_number)
    except (ValueError, RecursionError) as exc:
        if hasattr(exc, 'code'):
            raise
        refuse('E_JSON', str(exc)[:120])
    _check(value)
    return value


def dumps(value) -> bytes:
    _check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha256(value) -> str:
    return hashlib.sha256(dumps(value)).hexdigest()
