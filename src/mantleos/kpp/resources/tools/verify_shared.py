"""Verify the shared implementation's exact bytes; never grants approval."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(root):
    result = {}
    for path in sorted((root / 'src/mantleos').rglob('*')):
        if '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo'):
            continue
        if path.is_symlink():
            raise ValueError('Shared source symlink refused')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def verify(root, source=None):
    record = json.loads((root / 'SHARED-SOURCE.json').read_text(encoding='utf-8'))
    actual = inventory(root)
    if record.get('schema') != 'mantle.shared-source/1' or actual != record['files']:
        raise ValueError('Shared source drift; review and re-export common source')
    if source is not None and actual != inventory(source):
        raise ValueError('This build differs from the selected common source')
    if (root / 'SYSTEMS.md').read_bytes() != (root / 'src/mantleos/kpp/resources/SYSTEMS.md').read_bytes():
        raise ValueError('Common systems document drift')
    return {'result': 'PASS', 'files': len(actual), 'source_digest': record['source_digest'],
            'authenticity': 'NOT_ASSERTED', 'approval': 'NONE'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(Path(__file__).resolve().parents[1], args.source), indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, str(error) + '\n')
