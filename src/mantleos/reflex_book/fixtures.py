"""Packaged synthetic vectors; binary files materialize only in disposable storage."""
import hashlib
import json
from importlib.resources import files
from pathlib import Path
import tempfile

_temporary = None


def materialize(destination):
    """Write pinned fixtures to a new directory; no compilation or evaluation."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    vectors = json.loads(files(__package__).joinpath('resources/fixtures.json').read_text('utf-8'))
    for name, spec in vectors['files'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError('Unsafe packaged fixture path')
        raw = bytes.fromhex(spec['hex'])
        if len(raw) != spec['bytes'] or hashlib.sha256(raw).hexdigest() != spec['sha256']:
            raise ValueError('Packaged fixture integrity mismatch')
        target = destination/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return destination


def root():
    """Process-lifetime fixture tree for migrated tests and synthetic helpers."""
    global _temporary
    if _temporary is None:
        _temporary = tempfile.TemporaryDirectory(prefix='reflex-vectors-')
        materialize(Path(_temporary.name)/'vectors')
    return Path(_temporary.name)/'vectors'
