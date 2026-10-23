"""Export/check the KPP project from the shared implementation in either checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def files(directory):
    for path in sorted(directory.rglob('*')):
        relative = path.relative_to(directory)
        if '__pycache__' in relative.parts or path.suffix in ('.pyc', '.pyo'):
            continue
        if path.is_symlink():
            raise ValueError('Source symlink is not distributable: ' + str(relative))
        if path.is_file():
            yield relative.as_posix(), path.read_bytes()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def source_map(source=ROOT):
    source = Path(source).resolve()
    package = source / 'src/mantleos'
    if not (package / 'kpp/resources/SYSTEMS.md').is_file():
        raise ValueError('Select a unified MantleOS source root')
    published = source / 'docs/kpp.md'
    if published.is_file() and published.read_bytes() != (package / 'kpp/resources/SYSTEMS.md').read_bytes():
        raise ValueError('Common systems document drift; reconcile the published view')
    result = {'src/mantleos/' + name: blob for name, blob in files(package)}
    result.update(dict(files(package / 'kpp/resources')))
    test_root = source / 'tests/kpp'
    if not test_root.is_dir():
        test_root = source / 'tests'
    result.update({'tests/' + name: blob for name, blob in files(test_root)})
    modules = sorted(p.stem for p in (package / 'kpp').glob('*.py')
                     if p.stem not in ('__init__', '__main__')) + ['anchors']
    facade = '''"""Standalone entry point to the SAME canonical MantleOS KPP modules."""
import importlib as _importlib
import sys as _sys
if not (3, 11) <= _sys.version_info[:2] < (3, 15):
    raise RuntimeError('KPP/MantleOS requires Python 3.11 through 3.14')
from mantleos.kpp import __version__, implementation_plan
for _name in MODULES:
    _module = _importlib.import_module('mantleos.kpp.' + _name)
    _sys.modules[__name__ + '.' + _name] = _module
    globals()[_name] = _module
'''.replace('MODULES', repr(modules))
    result['src/kpp/__init__.py'] = facade.encode('utf-8')
    result['src/kpp/__main__.py'] = b'from mantleos.kpp.cli import main\nraise SystemExit(main())\n'
    result['.gitignore'] = b'__pycache__/\n*.py[cod]\n*.egg-info/\n.venv/\n.work/\nworkspaces/\nbuild/\ndist/\n.env*\n*.zip\n'
    notice_root = source / 'shared/licenses/MantleOS'
    if not notice_root.is_dir():
        notice_root = source
    for origin in [notice_root / 'LICENSE', notice_root / 'THIRD_PARTY_NOTICES.md',
                   *sorted((notice_root / 'licenses').glob('*'))]:
        if origin.is_file():
            result['shared/licenses/MantleOS/' + origin.relative_to(notice_root).as_posix()] = origin.read_bytes()
    exporter = source / 'tools/export_kpp.py'
    result['tools/export_kpp.py'] = exporter.read_bytes()
    result['tools/benchmark_canvas.py'] = (source / 'tools/benchmark_canvas.py').read_bytes()
    # Keep project scaffolding reproducible without another runtime tree.
    templates = source / 'tools/kpp_project'
    if templates.is_dir():
        for name, blob in files(templates):
            result[name] = blob
            result['tools/kpp_project/' + name] = blob
    import importlib.util
    spec=importlib.util.spec_from_file_location('reviewed_examples',package/'kpp/artifacts.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for name in module.inventory(source):
        result[name]=(source/name).read_bytes()
    shared = {name: sha(blob) for name, blob in result.items() if name.startswith('src/mantleos/')}
    result['SHARED-SOURCE.json'] = json_bytes({
        'schema': 'mantle.shared-source/1', 'implementation': 'mantleos',
        'canonical_kpp': 'mantleos.kpp', 'files': shared,
        'source_digest': sha(json.dumps(shared, sort_keys=True, separators=(',', ':')).encode()),
        'authority': 'Integrity only; hashes are not authentication or approval',
        'development': 'Maintain common source in the KPP project; promote reviewed changes to MantleOS; kpp is an entry-point facade'})
    result['SHA256SUMS.json'] = json_bytes({'schema': 'kpp.release-files/1',
                                          'files': {name: sha(blob) for name, blob in result.items()}})
    return result


def export(output, source=ROOT):
    output, source = Path(output).resolve(), Path(source).resolve()
    if output == source or any(output.is_relative_to(source / item) for item in ('src', 'tests', 'docs', 'tools')):
        raise ValueError('Export to a separate new directory')
    expected = source_map(source)
    output.mkdir(parents=True, exist_ok=False)
    for name, blob in expected.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    return check(output, source)


def check(output, source=ROOT):
    expected = source_map(source)
    actual = dict(files(Path(output)))
    # Workspaces are local user state and never part of the source export.
    actual = {name: blob for name, blob in actual.items()
              if not name.startswith(('workspaces/', '.work/', '.git/', '.venv/', 'build/', 'dist/'))
              and not any(part.endswith('.egg-info') for part in Path(name).parts)}
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name])
    if missing or extra or changed:
        raise ValueError('Standalone source drift: ' + json.dumps(dict(missing=missing, extra=extra, changed=changed)))
    return {'result': 'PASS', 'files': len(expected), 'shared_source': 'BYTE_IDENTICAL',
            'systems_document': 'BYTE_IDENTICAL', 'authenticity': 'NOT_ASSERTED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--check', type=Path)
    args = parser.parse_args()
    try:
        result = check(args.check, args.source) if args.check else export(args.output, args.source)
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
