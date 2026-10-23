"""Read-only, bounded specimen observation; source is never imported or executed."""
from pathlib import Path
import hashlib
import json
import sys

from . import json_contract as contract
from .scan.common import source_paths
from .scan.service import inspect
from .transactions import write_json


def snapshot(source):
    root = Path(source)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Specimen must be a real directory')
    root = root.resolve()
    files, total = {}, 0
    for path in source_paths(root):
        before = path.stat()
        if len(files) >= 256 or before.st_size > 2_000_000:
            raise ValueError('Specimen exceeds observation budget')
        data = path.read_bytes()
        total += len(data)
        after = path.stat()
        if total > 8_000_000 or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Specimen changed during observation or exceeds byte budget')
        files[path.relative_to(root).as_posix()] = hashlib.sha256(data).hexdigest()
    return {'files': files, 'sha256': contract.digest(files), 'bytes': total}


def observe(source, workspace, *, previous=None):
    root, output = Path(source).resolve(), Path(workspace).resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError('Observation workspace must be separate from specimen')
    before = snapshot(source)
    report = inspect({'source': str(root), 'workspace': str(output), 'max_files': 256,
                      'max_bytes': 8_000_000, 'max_file_bytes': 2_000_000,
                      'max_seconds': 20, 'allow_external': False})
    after = snapshot(source)
    if before != after:
        raise ValueError('Specimen changed during analysis; no stable finding')
    old = previous['files'] if previous else {}
    changes = sorted(k for k in set(old) | set(before['files']) if old.get(k) != before['files'].get(k))
    plan = json.loads((output / 'optimization-plan.json').read_text('utf-8'))
    result = {'schema': 'mantle.observation/1', 'source': str(root), 'snapshot': before,
              'changed_paths': changes, 'graph_digest': report['receipt']['graph_digest'],
              'proposals': plan.get('opportunities', [])[:16],
              'evidence': 'STATIC_ANALYSIS_NOT_BEHAVIORAL_PROOF', 'specimen_executed': False,
              'specimen_modified': False, 'authorized': False}
    contract.canonical(result)
    write_json(output / 'observation.json', result)
    return result


if __name__ == '__main__':
    try:
        observe(sys.argv[1], sys.argv[2])
    except Exception as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        raise SystemExit(2)
