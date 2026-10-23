"""Create a sanitized local Git handoff. No network or remote operations."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from project_files import (MANIFEST, ProjectError, copy_project, read_json, refresh,
                           sha, verify, write_json)

ROOT = Path(__file__).resolve().parents[1]


def git(root, *arguments):
    # Do not inherit machine hooks, signing, filters or credential configuration.
    env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
           'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'}
    for key in tuple(env):
        if key.startswith(('GIT_CONFIG_KEY_', 'GIT_CONFIG_VALUE_')) or key in (
                'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_CONFIG_COUNT',
                'GIT_CONFIG_PARAMETERS', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
            env.pop(key, None)
    result = subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                             '-C', str(root), *arguments], env=env, capture_output=True, timeout=120)
    if result.returncode:
        raise ProjectError('Local Git operation failed: ' + result.stderr.decode(errors='replace')[:1000])
    return result.stdout.decode('utf-8').strip()


def repository_check(root):
    root = Path(root).resolve()
    inventory = verify(root)
    if git(root, 'branch', '--show-current') != 'main' or git(root, 'rev-list', '--count', 'HEAD') != '1':
        raise ProjectError('Handoff requires main with exactly one initial commit')
    if git(root, 'remote') or git(root, 'status', '--porcelain', '--untracked-files=all'):
        raise ProjectError('Handoff repository has remotes or uncommitted files')
    expected = set(inventory['files']) | {MANIFEST}
    if set(git(root, 'ls-files').splitlines()) != expected:
        raise ProjectError('Git source inventory differs from the reviewed inventory')
    git(root, 'fsck', '--full', '--strict')
    return {'result': 'PASS', 'commit': git(root, 'rev-parse', 'HEAD'),
            'source_digest': inventory['source_digest'], 'files': len(expected), 'remotes': []}


def package(root, output, archive=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or output == root or (output.is_relative_to(root)
            and output.relative_to(root).parts[0] not in ('.work', 'dist')):
        raise ProjectError('Container output requires a new directory outside source trees')
    if archive is not None and Path(archive).exists():
        raise ProjectError('Refusing to overwrite an existing archive')
    verify(root)
    from kpp_upstream import check
    check(root)
    output.mkdir(parents=True)
    project = output/'MantleOS'
    copy_project(root, project)
    template = output/'.empty-git-template'; template.mkdir()
    git(project, 'init', '--template='+str(template), '-b', 'main')
    template.rmdir()
    for key, value in [('user.name', 'MantleOS Local Snapshot'), ('user.email', 'mantleos-local@invalid'),
                       ('core.autocrlf', 'false'), ('commit.gpgsign', 'false'),
                       ('core.hooksPath', '.git/disabled-hooks')]:
        git(project, 'config', '--local', key, value)
    git(project, 'add', '--all')
    git(project, 'commit', '-m', 'Initial reviewed MantleOS local handoff')
    result = repository_check(project)
    bundle = output/'MantleOS.bundle'
    git(project, 'bundle', 'create', str(bundle), 'main', 'HEAD')
    git(project, 'bundle', 'verify', str(bundle))
    text = (root/'docs/LOCAL-HANDOFF.md').read_text(encoding='utf-8')
    (output/'HANDOFF.md').write_text('# MantleOS local handoff\n\n'
        + 'Initial commit: `'+result['commit']+'`\n\nSource inventory digest: `'
        + result['source_digest']+'`\n\n'+text, encoding='utf-8')
    sums = {p.relative_to(output).as_posix(): sha(p.read_bytes())
            for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output/'CHECKSUMS.json', {'schema': 'mantle.container-checksums/1', 'files': sums,
               'scope': 'Every delivered file except this checksum index; integrity, not authentication'})
    verify_container(output)
    if archive is not None:
        archive = Path(archive).resolve()
        if archive.is_relative_to(output):
            raise ProjectError('ZIP must be outside the packaged directory')
        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
            for path in sorted(output.rglob('*')):
                if path.is_file():
                    stream.write(path, path.relative_to(output).as_posix())
        archive.with_suffix(archive.suffix+'.sha256').write_text(sha(archive.read_bytes())+'  '+archive.name+'\n', encoding='ascii')
    return {**result, 'bundle': str(bundle), 'zip': str(archive) if archive else None, 'network': 'NONE'}


def verify_container(folder):
    folder = Path(folder).resolve()
    record = read_json(folder/'CHECKSUMS.json')
    if record.get('schema') != 'mantle.container-checksums/1':
        raise ProjectError('Unsupported container checksum index')
    files = {p.relative_to(folder).as_posix(): sha(p.read_bytes()) for p in folder.rglob('*')
             if p.is_file() and p != folder/'CHECKSUMS.json'}
    if files != record['files']:
        raise ProjectError('Container has missing, added or modified contents')
    return {'result': 'PASS', 'files': len(files)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check')
    commands.add_parser('refresh')
    command = commands.add_parser('export');command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('package');command.add_argument('--output', type=Path, required=True);command.add_argument('--zip', type=Path)
    command = commands.add_parser('verify-container');command.add_argument('directory', type=Path)
    try:
        args = parser.parse_args(argv)
        if args.command == 'check':
            value = verify(args.project);value = {'result': 'PASS', 'source_digest': value['source_digest'], 'files': len(value['files'])}
        elif args.command == 'refresh':
            value = refresh(args.project);value = {'result': 'REFRESHED', 'source_digest': value['source_digest']}
        elif args.command == 'export':
            value = copy_project(args.project, args.output)
        elif args.command == 'package':
            value = package(args.project, args.output, args.zip)
        else:
            value = verify_container(args.directory)
        print(json.dumps(value, indent=2));return 0
    except (ProjectError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('Project container error: '+str(error), file=sys.stderr);return 2


if __name__ == '__main__':
    raise SystemExit(main())
