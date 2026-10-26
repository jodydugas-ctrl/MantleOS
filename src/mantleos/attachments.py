"""Versioned opaque Body attachments. Transport supplies no execution authority."""
import hashlib
from pathlib import Path
import re
import shutil
import tempfile

from . import cartridge, compiled
from .json_contract import loads
from .transactions import atomic_bytes, body_lock, ensure_clean, write_json

SCHEMA = 'mantle.attachments/1'
MAX_BYTES = 262144
MAX_ATTACHMENTS = 64
HEX = re.compile(r'[0-9a-f]{64}')
MEDIA = re.compile(r'[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]{0,127}')


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _expected(value):
    if not isinstance(value, str) or HEX.fullmatch(value) is None:
        raise ValueError('Expected attachment digest must be lowercase SHA-256')


def validate(body):
    """Validate attachment metadata and exact opaque bytes; never interpret payloads."""
    body = Path(body)
    index = body / 'ATTACHMENTS.json'
    directory = body / 'attachments'
    if not index.exists():
        if directory.exists():
            raise ValueError('Attachment directory requires ATTACHMENTS.json')
        return []
    if index.is_symlink() or index.stat().st_size > 65536:
        raise ValueError('Unsafe or oversized attachment index')
    value = loads(index.read_text('utf-8'))
    if (type(value) is not dict or set(value) != {'schema', 'attachments'}
            or value['schema'] != SCHEMA or type(value['attachments']) is not list
            or len(value['attachments']) > MAX_ATTACHMENTS):
        raise ValueError('Unsupported attachment contract')
    if directory.is_symlink() or (hasattr(directory, 'is_junction') and directory.is_junction()):
        raise ValueError('Unsafe attachment directory')
    seen = set()
    for item in value['attachments']:
        if type(item) is not dict or set(item) != {'sha256', 'bytes', 'media_type', 'path'}:
            raise ValueError('Invalid attachment record')
        pin = item['sha256']
        _expected(pin)
        if pin in seen or item['path'] != 'attachments/' + pin + '.bin':
            raise ValueError('Duplicate or unsafe attachment path')
        if (not isinstance(item['media_type'], str) or MEDIA.fullmatch(item['media_type']) is None
                or type(item['bytes']) is not int or not 1 <= item['bytes'] <= MAX_BYTES):
            raise ValueError('Invalid attachment type or size')
        path = body / item['path']
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item['bytes']:
            raise ValueError('Attachment missing or size mismatch')
        if _digest(path.read_bytes()) != pin:
            raise ValueError('Attachment digest mismatch')
        seen.add(pin)
    actual = set()
    if directory.exists():
        for path in directory.rglob('*'):
            if path.is_symlink() or not path.is_file():
                raise ValueError('Unsafe attachment member')
            actual.add(path.relative_to(body).as_posix())
    if actual != {item['path'] for item in value['attachments']}:
        raise ValueError('Attachment inventory mismatch')
    return value['attachments']


def inspect(body):
    """Inspect verified metadata without executing or authorizing attached data."""
    with body_lock(body):
        ensure_clean(body)
        cartridge.verify(body)
        return {'schema': SCHEMA, 'attachments': validate(body),
                'authorized': False, 'installed': False, 'executed': False}


def add(body, payload, *, media_type, expected_sha256, output):
    """Publish a new verified Body copy containing caller-selected opaque bytes."""
    _expected(expected_sha256)
    if type(payload) is not bytes or not 1 <= len(payload) <= MAX_BYTES:
        raise ValueError('Attachment size out of bounds')
    if not isinstance(media_type, str) or MEDIA.fullmatch(media_type) is None:
        raise ValueError('Invalid attachment media type')
    if _digest(payload) != expected_sha256:
        raise ValueError('Attachment differs from expected digest')
    body, output = Path(body).resolve(), Path(output).resolve()
    if output == body or output.is_relative_to(body) or body.is_relative_to(output):
        raise ValueError('Attachment output must be separate from source Body')
    with body_lock(body), body_lock(output):
        ensure_clean(body)
        ensure_clean(output)
        compiled.load(body)
        if output.exists():
            raise FileExistsError('Attachment output already exists')
        entries = validate(body)
        if len(entries) >= MAX_ATTACHMENTS or any(i['sha256'] == expected_sha256 for i in entries):
            raise ValueError('Duplicate attachment or attachment count exceeded')
        output.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.attachment-', dir=output.parent))
        try:
            shutil.copytree(body, stage, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            relative = 'attachments/' + expected_sha256 + '.bin'
            atomic_bytes(stage / relative, payload, replace=False)
            entry = {'sha256': expected_sha256, 'bytes': len(payload),
                     'media_type': media_type, 'path': relative}
            write_json(stage / 'ATTACHMENTS.json', {'schema': SCHEMA,
                       'attachments': sorted(entries + [entry], key=lambda i: i['sha256'])})
            cartridge.write_manifest(stage)
            compiled.compile_body(stage)
            compiled.load(stage)
            # rename is no-clobber on Windows; output lock serializes cooperating writers.
            if output.exists():
                raise FileExistsError('Attachment output appeared during preparation')
            stage.rename(output)
            return {'schema': SCHEMA, 'output': str(output), 'attachment': entry,
                    'authorized': False, 'installed': False, 'executed': False}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def extract(body, *, sha256, output):
    """Copy verified opaque bytes to an unused file outside the source Body."""
    _expected(sha256)
    body, output = Path(body).resolve(), Path(output).resolve()
    if output.is_relative_to(body):
        raise ValueError('Extraction output must be outside Body')
    with body_lock(body):
        ensure_clean(body)
        cartridge.verify(body)
        entry = next((i for i in validate(body) if i['sha256'] == sha256), None)
        if entry is None:
            raise ValueError('Unknown attachment digest')
        atomic_bytes(output, (body / entry['path']).read_bytes(), replace=False)
        return {'schema': SCHEMA, 'sha256': sha256, 'output': str(output),
                'authorized': False, 'installed': False, 'executed': False}


def main(argv=None, *, body=None):
    import argparse
    import json
    parser = argparse.ArgumentParser(prog='mantleos attachment')
    sub = parser.add_subparsers(dest='operation', required=True)
    sub.add_parser('inspect')
    p = sub.add_parser('add')
    p.add_argument('payload', type=Path)
    p.add_argument('--media-type', required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--output', required=True, type=Path)
    p = sub.add_parser('extract')
    p.add_argument('--sha256', required=True)
    p.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    if body is None:
        parser.error('--body PATH is required')
    if args.operation == 'inspect':
        result = inspect(body)
    elif args.operation == 'extract':
        result = extract(body, sha256=args.sha256, output=args.output)
    else:
        with args.payload.open('rb') as stream:
            payload = stream.read(MAX_BYTES + 1)
        result = add(body, payload, media_type=args.media_type,
                     expected_sha256=args.expected_sha256, output=args.output)
    print(json.dumps(result, indent=2))
    return 0
