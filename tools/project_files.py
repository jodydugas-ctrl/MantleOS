"""Explicit distributable source inventory; no credentials, state or Git history."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import uuid

MANIFEST = 'PROJECT-FILES.json'
ROOT_FILES = {'.gitattributes', '.gitignore', 'AGENTS.md', 'CONTRIBUTING.md', 'LICENSE',
              'MANIFEST.in', 'MANTLE.md', 'README.md', 'SECURITY.md',
              'THIRD_PARTY_NOTICES.md', 'pyproject.toml', 'requirements-dev.txt'}
TREES = {'src', 'tests', 'examples', 'docs', 'tools', 'licenses', '.github', 'archives', 'upstream'}
SKIP = {'.git', '.work', '.heritage', '.venv', 'venv', 'build', 'dist', '__pycache__',
        '.pytest_cache', '.ruff_cache', 'node_modules', '.mantle', '.nest', 'agents', 'workspaces'}
PRIVATE = {'credentials.json', 'oauth-token.bin', 'engram.jsonl', 'primer.txt',
           'birth.json', 'cartridge.json', 'state.json', 'anatomy.json'}
EXTENSIONS = {'.py', '.md', '.txt', '.json', '.toml', '.anchor', '.html', '.js', '.cjs',
              '.css', '.ui', '.png', '.svg', '.yml', '.yaml', '.in'}


class ProjectError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ProjectError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ProjectError('Non-finite JSON value: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique, parse_constant=invalid)


def atomic_bytes(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '-' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def write_json(path, value):
    atomic_bytes(path, json_bytes(value))


def relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or PurePosixPath(value).is_absolute() or any(p in ('', '.', '..') for p in value.split('/'))):
        raise ProjectError('Unsafe relative project path')
    return value


def allowed(name):
    relative(name)
    parts = name.split('/')
    if any(p in SKIP or p.endswith('.egg-info') for p in parts):
        return False
    lowered = parts[-1].lower()
    if lowered in PRIVATE or lowered.startswith('.env') or lowered.endswith(('.vcw', '.rvcar', '.zip', '.jsonl', '.pyc', '.pyo')):
        return False
    if len(parts) == 1:
        return name in ROOT_FILES
    return parts[0] in TREES and (Path(name).suffix.lower() in EXTENSIONS
                                  or parts[-1] in ('LICENSE', '.gitignore', '.gitattributes'))


def safe_path(root, name):
    relative(name)
    root = Path(root).resolve()
    path = root.joinpath(*name.split('/'))
    for part in (path, *path.parents):
        if part == root.parent:
            break
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ProjectError('Source symlinks/reparse points are refused: ' + name)
    if not path.resolve().is_relative_to(root):
        raise ProjectError('Project path escaped root')
    return path


def collect(root):
    root = Path(root).resolve()
    result = {}
    explicit_archives = (root/'archives/ARCHIVE-FILES.json').is_file()
    archive_root = root/'archives'
    if (not explicit_archives and archive_root.is_dir()
            and any(p.name not in ('README.md','index.json') for p in archive_root.iterdir())):
        raise ProjectError('Historical archive payloads require archives/ARCHIVE-FILES.json')
    if explicit_archives:
        from archive_inventory import inventory
        result.update(inventory(root))
    for name in sorted(ROOT_FILES):
        path = safe_path(root, name)
        if not path.is_file():
            raise ProjectError('Missing required project file: ' + name)
        result[name] = sha(path.read_bytes())
    for tree in sorted(TREES):
        if tree == 'archives' and explicit_archives:
            continue
        folder = root / tree
        if not folder.exists():
            continue
        safe_path(root, tree)
        for parent, directories, files in os.walk(folder, followlinks=False):
            directories[:] = sorted(n for n in directories if n not in SKIP and not n.endswith('.egg-info'))
            for directory in directories:
                safe_path(root, (Path(parent) / directory).relative_to(root).as_posix())
            for filename in sorted(files):
                name = (Path(parent) / filename).relative_to(root).as_posix()
                if allowed(name):
                    result[name] = sha(safe_path(root, name).read_bytes())
    return dict(sorted(result.items()))


def refresh(root):
    files = collect(root)
    value = {'schema': 'mantle.project-files/1', 'files': files, 'source_digest': digest(files),
             'scope': 'Reviewed distributable source; excludes Git metadata and private/generated state',
             'authority': 'Integrity only, not authentication or permission'}
    write_json(Path(root) / MANIFEST, value)
    return value


def verify(root):
    value = read_json(Path(root) / MANIFEST)
    if value.get('schema') != 'mantle.project-files/1' or not isinstance(value.get('files'), dict):
        raise ProjectError('Unsupported project inventory')
    archive_files = {}
    if (Path(root)/'archives/ARCHIVE-FILES.json').is_file():
        from archive_inventory import inventory
        archive_files = inventory(root)
    if any(not allowed(name) and name not in archive_files for name in value['files']):
        raise ProjectError('Undistributable path in project inventory')
    if value.get('source_digest') != digest(value['files']) or collect(root) != value['files']:
        raise ProjectError('Project source drift; review changes and refresh the inventory')
    return value


def copy_project(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or (output.is_relative_to(root) and output.relative_to(root).parts[0] not in ('.work', 'dist')):
        raise ProjectError('Source export requires a new directory outside the project')
    value = verify(root)
    output.mkdir(parents=True)
    for name in (*value['files'], MANIFEST):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(safe_path(root, name).read_bytes())
    verify(output)
    return {'result': 'PASS', 'files': len(value['files']) + 1, 'source_digest': value['source_digest']}
