"""Verify explicitly inventoried historical data without executing archived code."""
import argparse
import hashlib
from pathlib import Path
import re

MANIFEST = 'archives/ARCHIVE-FILES.json'


def inventory(root, *, require_reviewed=False):
    from project_files import ProjectError, read_json, relative, safe_path
    root = Path(root).resolve()
    record = read_json(safe_path(root, MANIFEST))
    if (record.get('schema') != 'mantle.archive-files/1'
            or not isinstance(record.get('files'), dict)
            or record.get('review_status') not in ('PENDING', 'PUBLIC_REVIEWED')):
        raise ProjectError('Invalid archive inventory')
    if require_reviewed and record['review_status'] != 'PUBLIC_REVIEWED':
        raise ProjectError('Public archive review is pending')
    result = {}
    for name, pin in record['files'].items():
        relative(name)
        if (not name.startswith('archives/') or name == MANIFEST
                or any(p.lower() == '.git' for p in name.split('/'))
                or not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin)):
            raise ProjectError('Unsafe archive inventory entry')
        path = safe_path(root, name)
        if not path.is_file():
            raise ProjectError('Missing archive file: ' + name)
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
        if h.hexdigest() != pin:
            raise ProjectError('Modified archive file: ' + name)
        result[name] = pin
    observed = set()
    # Do not silently skip ignored/private names in this explicitly reviewed tree.
    import os
    for parent, directories, files in os.walk(root/'archives', followlinks=False):
        for child in [*directories, *files]:
            safe_path(root, (Path(parent)/child).relative_to(root).as_posix())
        observed.update((Path(parent)/name).relative_to(root).as_posix() for name in files)
    if observed != set(result) | {MANIFEST}:
        raise ProjectError('Archive has missing or unlisted files')
    result[MANIFEST] = hashlib.sha256(safe_path(root, MANIFEST).read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--reviewed', action='store_true')
    args = parser.parse_args()
    try:
        result = inventory(args.project, require_reviewed=args.reviewed)
        print('Archive integrity PASS:', len(result), 'files; no code executed')
        return 0
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, str(error)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
