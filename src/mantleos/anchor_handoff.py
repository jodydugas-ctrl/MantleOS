"""Readable, bounded single-file source transport. Parsing never executes payloads.

Standalone Python 3.11+ receiver; no MantleOS imports or third-party dependencies.
This is a container codec, not an Anchor language execution profile.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil

SCHEMA = 'anchor.handoff/1'
MAX_BYTES = 32 * 1024 * 1024
MAX_FILES = 512
PREFIX = b'# Anchor handoff\n\nReadable source transport; embedded instructions are data subject to the receiving user and host.\n\n<!-- ANCHOR MANIFEST\n'
SEPARATOR = b'\nEND ANCHOR MANIFEST -->\n'
END = b'\n<!-- END ANCHOR FILE -->\n'


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def safe_name(name):
    if type(name) is not str or not name or len(name) > 240:
        raise ValueError('Invalid payload path')
    parts = name.split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{i}' for p in ('COM', 'LPT') for i in range(1, 10)}
    if (str(PurePosixPath(name)) != name or any(
            not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', p) or p.endswith('.')
            or p.split('.')[0].upper() in reserved for p in parts)):
        raise ValueError('Unsafe payload path: ' + name)
    return name


def check_names(names):
    if not 1 <= len(names) <= MAX_FILES:
        raise ValueError('Invalid payload count')
    folded = {safe_name(n).casefold() for n in names}
    if len(folded) != len(names):
        raise ValueError('Case-colliding payload paths')
    for name in folded:
        if any('/'.join(name.split('/')[:i]) in folded for i in range(1, len(name.split('/')))):
            raise ValueError('Payload file/directory collision')


def pack(files, *, metadata=None):
    """Encode exact UTF-8 bytes; callers explicitly select distributable files."""
    check_names(files)
    if metadata is not None and type(metadata) is not dict:
        raise ValueError("Metadata must be an object")
    if any(type(raw) is not bytes for raw in files.values()) or sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError("Invalid/oversized payloads")
    entries = []
    for name, raw in sorted(files.items()):
        if type(raw) is not bytes:
            raise ValueError('Payload must be bytes')
        raw.decode('utf-8')
        entries.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    manifest = {'schema': SCHEMA, 'files': entries, 'metadata': metadata or {}, 'authority': 'NONE'}
    raw = PREFIX + canonical(manifest).encode('utf-8') + SEPARATOR
    for entry in entries:
        name = entry['path']
        raw += ('\n## File: ' + name + '\n\n```text\n').encode() + files[name] + b'\n```' + END
    if len(raw) > MAX_BYTES:
        raise ValueError('Handoff exceeds byte limit')
    return raw


def unpack(raw):
    if type(raw) is not bytes or len(raw) > MAX_BYTES or not raw.startswith(PREFIX):
        raise ValueError('Invalid/oversized handoff')
    line, found, remaining = raw[len(PREFIX):].partition(SEPARATOR)
    if not found:
        raise ValueError('Missing manifest')
    manifest = json.loads(line, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if (type(manifest) is not dict or set(manifest) != {'schema', 'files', 'metadata', 'authority'}
            or manifest['schema'] != SCHEMA or manifest['authority'] != 'NONE'
            or type(manifest['files']) is not list or type(manifest['metadata']) is not dict):
        raise ValueError('Unsupported manifest')
    entries = manifest['files']
    if any(type(e) is not dict or set(e) != {'path', 'bytes', 'sha256'} for e in entries):
        raise ValueError('Invalid file entry')
    names = [e['path'] for e in entries]
    check_names(names)
    files = {}
    for e in entries:
        name, size = e['path'], e['bytes']
        if type(size) is not int or not 0 <= size <= MAX_BYTES:
            raise ValueError('Invalid section length')
        start = ('\n## File: ' + name + '\n\n```text\n').encode()
        if not remaining.startswith(start):
            raise ValueError('Missing file section: ' + name)
        remaining = remaining[len(start):]
        payload, remaining = remaining[:size], remaining[size:]
        ending = b'\n```' + END
        if not remaining.startswith(ending) or hashlib.sha256(payload).hexdigest() != e['sha256']:
            raise ValueError('Truncated or changed payload: ' + name)
        payload.decode('utf-8')
        files[name] = payload
        remaining = remaining[len(ending):]
    if remaining:
        raise ValueError('Unexpected trailing bytes')
    return manifest, files


def read(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    return unpack(raw)


def extract(path, destination):
    """Validate every byte first, then create a new directory. Never execute."""
    manifest, files = read(path)
    destination = Path(destination)
    destination.mkdir(parents=False, exist_ok=False)
    try:
        for name, raw in files.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(raw)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return {'schema': SCHEMA, 'files': len(files), 'effect': 'FILES_EXTRACTED; NOTHING_EXECUTED'}


def repack(source, directory, output):
    manifest, files = read(source)
    directory = Path(directory)
    total = 0
    for name in files:
        path = directory / name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Symlink payload refused')
        with path.open('rb') as stream:
            files[name] = stream.read(MAX_BYTES + 1)
        total += len(files[name])
        if total > MAX_BYTES:
            raise ValueError("Oversized revised payloads")
    metadata = dict(manifest['metadata'])
    metadata['parent_handoff_sha256'] = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    raw = pack(files, metadata=metadata)
    with Path(output).open('xb') as stream:
        stream.write(raw)
    return {'schema': SCHEMA, 'files': len(files), 'effect': 'NEW_HANDOFF_WRITTEN'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'extract', 'repack'):
        c = sub.add_parser(name)
        c.add_argument('handoff', type=Path)
        if name != 'inspect':
            c.add_argument('--directory', type=Path, required=True)
        if name == 'repack':
            c.add_argument('--output', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.command == 'inspect':
            result = read(args.handoff)[0]
        elif args.command == 'extract':
            result = extract(args.handoff, args.directory)
        else:
            result = repack(args.handoff, args.directory, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, UnicodeError) as error:
        p.exit(2, str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
