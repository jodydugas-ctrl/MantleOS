"""Offline KPP alignment and reviewed updates. Never fetches, pulls or configures remotes."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from project_files import (ProjectError, MANIFEST, allowed, atomic_bytes, copy_project, digest,
                           json_bytes, read_json, refresh, relative, safe_path, sha, verify, write_json)

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'upstream/kpp.lock.json'
OFFICIAL = 'https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol'
WORK = '.work/kpp-updates'
HEX = re.compile(r'^[a-f0-9]{64}$')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _git(source, *args):
    # Metadata reads only. Disable optional index writes and executable fsmonitor hooks.
    command = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C', str(source), *args]
    result = subprocess.run(command, capture_output=True, timeout=20,
                            env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    if result.returncode:
        raise ProjectError('Cannot read local KPP Git metadata: ' + result.stderr.decode(errors='replace')[:300])
    return result.stdout.decode('utf-8').strip()


def snapshot(source):
    """Read data and local Git metadata; never import or run the supplied source."""
    source = Path(source).resolve()
    record = read_json(safe_path(source, 'SHARED-SOURCE.json'))
    files = record.get('files')
    if (record.get('schema') != 'mantle.shared-source/1' or not isinstance(files, dict)
            or record.get('source_digest') != digest(files)):
        raise ProjectError('Invalid KPP shared-source inventory')
    entries = {}
    def add(src, dest, group):
        if not allowed(dest):
            raise ProjectError('Undistributable KPP path: ' + dest)
        blob = safe_path(source, src).read_bytes()
        if dest in entries:
            raise ProjectError('Duplicate upstream destination')
        entries[dest] = {'source': src, 'sha256': sha(blob), 'group': group}
    for name, pin in sorted(files.items()):
        if not name.startswith('src/mantleos/') or not isinstance(pin, str) or not HEX.fullmatch(pin):
            raise ProjectError('Invalid KPP implementation path/pin')
        add(name, name, 'implementation')
        if entries[name]['sha256'] != pin:
            raise ProjectError('KPP source pin mismatch: ' + name)
    observed = set()
    folder = safe_path(source, 'src/mantleos')
    for parent, directories, names in os.walk(folder, followlinks=False):
        directories[:] = sorted(n for n in directories if n != '__pycache__')
        for name in directories:
            safe_path(source, (Path(parent)/name).relative_to(source).as_posix())
        for name in names:
            if name.endswith(('.pyc', '.pyo')):
                continue
            path = (Path(parent)/name).relative_to(source).as_posix()
            safe_path(source, path); observed.add(path)
    if observed != set(files):
        raise ProjectError('KPP has missing or unpinned implementation files')
    for required in ('src/mantleos/anchors.py', 'src/mantleos/cells.py', 'src/mantleos/tissue.py',
                     'src/mantleos/kpp/resources/SYSTEMS.md'):
        if required not in files:
            raise ProjectError('KPP is missing required common definitions')
    test_root = safe_path(source, 'tests')
    tests = []
    for parent, directories, names in os.walk(test_root, followlinks=False):
        directories[:] = sorted(n for n in directories if n != '__pycache__')
        for name in directories:
            safe_path(source, (Path(parent)/name).relative_to(source).as_posix())
        tests.extend(Path(parent)/name for name in sorted(names) if name.endswith('.py'))
    if not tests:
        raise ProjectError('A complete KPP source export must include its tests')
    for path in tests:
        name = path.relative_to(source).as_posix()
        add(name, 'tests/kpp/' + path.relative_to(test_root).as_posix(), 'tests')
    add('src/mantleos/kpp/resources/SYSTEMS.md', 'docs/kpp.md', 'generated-view')
    notices = {'LICENSE': 'upstream/kpp-notices/LICENSE',
               'THIRD-PARTY-NOTICES.md': 'upstream/kpp-notices/THIRD-PARTY-NOTICES.md'}
    for origin, destination in notices.items():
        add(origin, destination, 'notice')
    metadata = {'official_url': OFFICIAL, 'base_commit': None,
                'snapshot_kind': 'local-source-export', 'dirty': None, 'version': None,
                'published_revision_verified': False}
    if (source/'.git').exists():
        metadata['base_commit'] = _git(source, 'rev-parse', 'HEAD')
        metadata['dirty'] = bool(_git(source, 'status', '--porcelain', '--untracked-files=normal'))
        metadata['snapshot_kind'] = 'local-working-snapshot' if metadata['dirty'] else 'local-committed-snapshot'
    if (source/'pyproject.toml').is_file():
        import tomllib
        metadata['version'] = tomllib.loads((source/'pyproject.toml').read_text(encoding='utf-8')).get('project', {}).get('version')
    return {'schema': 'mantle.kpp-upstream/1', 'upstream': metadata,
            'shared_source_digest': record['source_digest'], 'files': dict(sorted(entries.items())),
            'selection_digest': digest(entries), 'required_notices': sorted(notices.values()),
            'authority': 'Local source selection and integrity only; no authentication or execution grant'}


def _lock(root):
    value = read_json(safe_path(root, LOCK))
    if (value.get('schema') != 'mantle.kpp-upstream/1' or value.get('upstream', {}).get('official_url') != OFFICIAL
            or not isinstance(value.get('files'), dict) or value.get('selection_digest') != digest(value['files'])):
        raise ProjectError('Invalid KPP upstream lock')
    for name, entry in value['files'].items():
        if not allowed(name) or not isinstance(entry, dict) or set(entry) != {'source', 'sha256', 'group'}:
            raise ProjectError('Invalid upstream ownership entry')
        relative(entry['source'])
        group = entry['group']
        valid = ((group == 'implementation' and name == entry['source'] and name.startswith('src/mantleos/'))
                 or (group == 'tests' and name.startswith('tests/kpp/') and entry['source'].startswith('tests/'))
                 or (group == 'generated-view' and name == 'docs/kpp.md'
                     and entry['source'] == 'src/mantleos/kpp/resources/SYSTEMS.md')
                 or (group == 'notice' and name in value.get('required_notices', [])
                     and (entry['source'], name) in (
                         ('LICENSE', 'upstream/kpp-notices/LICENSE'),
                         ('THIRD-PARTY-NOTICES.md', 'upstream/kpp-notices/THIRD-PARTY-NOTICES.md'))))
        if not valid or not isinstance(entry['sha256'], str) or not HEX.fullmatch(entry['sha256']):
            raise ProjectError('Upstream ownership exceeds the shared boundary')
    return value


def check(root=ROOT, source=None):
    root = Path(root).resolve()
    if (root/WORK/'pending.json').exists():
        raise ProjectError('An interrupted KPP update requires reviewed recovery')
    lock = _lock(root)
    for name, entry in lock['files'].items():
        path = safe_path(root, name)
        if not path.is_file() or sha(path.read_bytes()) != entry['sha256']:
            raise ProjectError('Local conflict in KPP-owned source: ' + name)
    if source is not None and snapshot(source) != lock:
        raise ProjectError('Selected KPP snapshot differs; create a reviewed update plan')
    return {'result': 'PASS', 'owned_files': len(lock['files']), 'selection_digest': lock['selection_digest'],
            'upstream': lock['upstream'], 'network': 'NONE'}


def seed(root, source):
    """Handoff preparation only. Do not replace an existing upstream lock."""
    root = Path(root).resolve()
    if (root/LOCK).exists():
        raise ProjectError('KPP upstream lock already exists')
    lock = snapshot(source)
    for name, entry in lock['files'].items():
        content = safe_path(source, entry['source']).read_bytes()
        destination = safe_path(root, name)
        if destination.exists() and destination.read_bytes() != content:
            raise ProjectError('Initial shared source mismatch: ' + name)
        atomic_bytes(destination, content)
    write_json(root/LOCK, lock)
    return check(root)


def plan(root, source, output):
    root, source, output = Path(root).resolve(), Path(source).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(source):
        raise ProjectError('Plan output must be new and outside the KPP source')
    check(root); baseline = verify(root); previous = _lock(root); incoming = snapshot(source)
    changes = []
    for name in sorted(set(previous['files']) | set(incoming['files'])):
        before = previous['files'].get(name, {}).get('sha256')
        after = incoming['files'].get(name, {}).get('sha256')
        if before is None and safe_path(root, name).exists():
            raise ProjectError('Upstream addition conflicts with a MantleOS-owned file: ' + name)
        if before != after:
            changes.append({'path': name, 'before': before, 'after': after,
                            'operation': 'add' if before is None else 'delete' if after is None else 'replace'})
    output.mkdir(parents=True)
    for name, entry in incoming['files'].items():
        target = output/'payload'/name; target.parent.mkdir(parents=True, exist_ok=True)
        content = safe_path(source, entry['source']).read_bytes()
        if sha(content) != entry['sha256']:
            raise ProjectError('KPP source changed while preparing plan')
        target.write_bytes(content)
    value = {'schema': 'mantle.kpp-update-plan/1', 'id': uuid.uuid4().hex,
             'baseline_source_digest': baseline['source_digest'], 'baseline_lock_digest': digest(previous),
             'source_root': str(source), 'incoming': incoming, 'changes': changes,
             'execution': 'NONE', 'approval': 'NOT_GRANTED'}
    value['sha256'] = digest(value)
    write_json(output/'plan.json', value)
    (output/'REVIEW.md').write_text('# Local KPP update proposal\n\n'
        + '\n'.join('- '+entry['operation']+': '+entry['path'] for entry in changes)
        + '\n\nNo source was executed or applied. Review the exact payload before --reviewed application.\n', encoding='utf-8')
    return value


@contextmanager
def writer(root):
    folder = Path(root)/WORK; folder.mkdir(parents=True, exist_ok=True)
    path = folder/'writer.lock'
    if path.is_symlink():
        raise ProjectError('Unsafe updater lock')
    with path.open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ProjectError('Another KPP update writer is active') from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _validate(candidate, logs):
    checks = []
    env = {**os.environ, 'PYTHONPATH': str(candidate/'src'), 'PYTHONUTF8': '1'}
    for name, command in [('combined-suite', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q']),
                          ('kpp-doctor', [sys.executable, '-m', 'mantleos', 'kpp', 'doctor'])]:
        result = subprocess.run(command, cwd=candidate, env=env, capture_output=True, timeout=1200)
        content = result.stdout + result.stderr
        (logs/(name+'.log')).write_bytes(content)
        checks.append({'name': name, 'result': 'PASS' if result.returncode == 0 else 'FAIL',
                       'log_sha256': sha(content), 'exit_code': result.returncode})
        if result.returncode:
            break
    return checks


def _write_target(root, name, content):
    if name != MANIFEST and not allowed(name):
        raise ProjectError('Update target is not distributable source')
    path = safe_path(root, name)
    if content is None:
        if path.exists():
            path.unlink()
    else:
        atomic_bytes(path, content)


def _transaction(root, changes, kind):
    identifier = uuid.uuid4().hex
    folder = Path(root)/WORK/identifier; folder.mkdir()
    before, after = {}, {}
    for name, content in changes.items():
        path = safe_path(root, name)
        old = path.read_bytes() if path.exists() else None
        before[name], after[name] = sha(old) if old is not None else None, sha(content) if content is not None else None
        for section, data in [('before', old), ('after', content)]:
            if data is not None:
                target = folder/section/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    journal = {'schema': 'mantle.kpp-update-transaction/1', 'id': identifier, 'kind': kind,
               'before': before, 'after': after, 'created': now(), 'status': 'PREPARED'}
    write_json(folder/'transaction.json', journal)
    write_json(Path(root)/WORK/'pending.json', {'id': identifier})
    try:
        # Code first, then selected lock/provenance, and the exact inventory last.
        for name, content in changes.items():
            if name != MANIFEST:
                _write_target(root, name, content)
        _write_target(root, MANIFEST, changes[MANIFEST])
        journal['status'] = 'COMMITTED'; write_json(folder/'transaction.json', journal)
        write_json(Path(root)/WORK/'latest.json', {'id': identifier})
        (Path(root)/WORK/'pending.json').unlink()
    except Exception:
        # Never silently overwrite an external edit. Recovery rechecks all affected pins.
        _restore_transaction(root, identifier, 'FAILED_PUBLICATION_RECOVERED')
        raise
    return journal


def _journal(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch('[a-f0-9]{32}', identifier):
        raise ProjectError('Invalid update transaction identity')
    folder = safe_path(root, WORK+'/'+identifier)
    journal = read_json(folder/'transaction.json')
    if journal.get('schema') != 'mantle.kpp-update-transaction/1' or journal.get('id') != identifier:
        raise ProjectError('Unsupported update transaction')
    if not isinstance(journal.get('before'), dict) or set(journal['before']) != set(journal.get('after', {})):
        raise ProjectError('Invalid transaction source inventory')
    for name, pin in journal['before'].items():
        if name != MANIFEST and not allowed(name):
            raise ProjectError('Unsafe recovery target')
        if pin is not None:
            path = safe_path(folder, 'before/'+name)
            if not isinstance(pin, str) or not HEX.fullmatch(pin) or not path.is_file() or sha(path.read_bytes()) != pin:
                raise ProjectError('Recovery backup is missing or changed')
        after = journal['after'][name]
        if after is not None:
            retained = safe_path(folder, 'after/'+name)
            if not isinstance(after, str) or not HEX.fullmatch(after) or not retained.is_file() or sha(retained.read_bytes()) != after:
                raise ProjectError('Retained candidate is missing or changed')
        path = safe_path(root, name)
        current = sha(path.read_bytes()) if path.exists() else None
        if current not in (pin, journal['after'][name]):
            raise ProjectError('Recovery conflict; retain the journal and inspect local edits: ' + name)
    return folder, journal


def _restore_transaction(root, identifier, reason):
    folder, journal = _journal(root, identifier)
    for name, pin in journal['before'].items():
        if name == MANIFEST or name.startswith('upstream/history/'):
            continue
        _write_target(root, name, (folder/'before'/name).read_bytes() if pin is not None else None)
    receipt = {'schema': 'mantle.kpp-update-event/1', 'event': reason, 'transaction': identifier,
               'at': now(), 'selection_digest': _lock(root)['selection_digest'], 'authority': 'Explicit local review'}
    write_json(Path(root)/'upstream/history'/('recovery-'+uuid.uuid4().hex+'.json'), receipt)
    refresh(root)
    journal['status'] = 'RESTORED'; write_json(folder/'transaction.json', journal)
    pending = Path(root)/WORK/'pending.json'
    if pending.exists():
        pending.unlink()
    return {'result': 'RESTORED', 'transaction': identifier, 'network': 'NONE'}


def recover(root=ROOT, *, reviewed=False):
    if reviewed is not True:
        raise ProjectError('Recovery requires explicit --reviewed')
    with writer(root):
        pending = Path(root)/WORK/'pending.json'
        if not pending.exists():
            raise ProjectError('No interrupted update requires recovery')
        identifier = read_json(pending)['id']
        return _restore_transaction(root, identifier, 'INTERRUPTED_UPDATE_RECOVERED')


def restore(root=ROOT, *, reviewed=False):
    if reviewed is not True:
        raise ProjectError('Restoration requires explicit --reviewed')
    with writer(root):
        check(root); verify(root)
        latest = Path(root)/WORK/'latest.json'
        if not latest.exists():
            raise ProjectError('No retained local update to restore')
        identifier = read_json(latest)['id']
        _, journal = _journal(root, identifier)
        if journal['status'] != 'COMMITTED':
            raise ProjectError('Latest update is already restored or incomplete')
        return _restore_transaction(root, identifier, 'UPDATE_RESTORED')


def apply(root, plan_dir, source, *, reviewed=False, validator=None):
    """Execute a reviewed candidate's tests, then publish only its owned source.

    validator is an internal test seam; the CLI always uses the fixed full suite.
    Reviewed Python tests run with the user's ordinary privileges, not in a sandbox.
    """
    if reviewed is not True:
        raise ProjectError('Applying and executing a KPP update requires explicit --reviewed')
    root, plan_dir, source = Path(root).resolve(), Path(plan_dir).resolve(), Path(source).resolve()
    with writer(root):
        check(root); baseline = verify(root); previous = _lock(root)
        value = read_json(plan_dir/'plan.json')
        if (value.get('schema') != 'mantle.kpp-update-plan/1'
                or value.get('sha256') != digest({k: v for k, v in value.items() if k != 'sha256'})
                or value.get('baseline_source_digest') != baseline['source_digest']
                or value.get('baseline_lock_digest') != digest(previous)):
            raise ProjectError('Stale or modified KPP update plan')
        incoming = snapshot(source)
        if incoming != value['incoming']:
            raise ProjectError('Upstream source changed after planning')
        expected = []
        for name in sorted(set(previous['files']) | set(incoming['files'])):
            before = previous['files'].get(name, {}).get('sha256')
            after = incoming['files'].get(name, {}).get('sha256')
            if before is None and safe_path(root, name).exists():
                raise ProjectError('New upstream source conflicts with a MantleOS file')
            if before != after:
                expected.append({'path': name, 'before': before, 'after': after,
                                 'operation': 'add' if before is None else 'delete' if after is None else 'replace'})
        if value['changes'] != expected:
            raise ProjectError('Plan changes disagree with selected source')
        actual_payload = {p.relative_to(plan_dir/'payload').as_posix() for p in (plan_dir/'payload').rglob('*') if p.is_file()}
        if actual_payload != set(incoming['files']):
            raise ProjectError('Update payload has missing or unpinned files')
        blobs = {}
        for name, entry in incoming['files'].items():
            data = safe_path(plan_dir, 'payload/'+name).read_bytes()
            if sha(data) != entry['sha256']:
                raise ProjectError('Update payload was modified')
            blobs[name] = data
        work = root/WORK/('validation-'+uuid.uuid4().hex);work.mkdir()
        candidate = work/'candidate';copy_project(root, candidate)
        for change in expected:
            _write_target(candidate, change['path'], blobs.get(change['path']))
        write_json(candidate/LOCK, incoming);candidate_pin = refresh(candidate)['source_digest']
        checks = (validator or _validate)(candidate, work)
        if not checks or any(c.get('result') != 'PASS' for c in checks):
            raise ProjectError('Candidate validation failed; baseline source was not changed')
        if verify(candidate)['source_digest'] != candidate_pin:
            raise ProjectError('Validation modified the staged candidate')
        if verify(root)['source_digest'] != baseline['source_digest'] or snapshot(source) != incoming:
            raise ProjectError('Source or destination changed during validation')
        event_id = uuid.uuid4().hex
        receipt = {'schema': 'mantle.kpp-update-event/1', 'event': 'VALIDATED_UPDATE_APPLIED', 'id': event_id,
                   'at': now(), 'previous_selection': previous['selection_digest'],
                   'selected_snapshot': incoming['upstream'], 'selection_digest': incoming['selection_digest'],
                   'plan_sha256': value['sha256'], 'checks': checks, 'authority': 'Explicit local review'}
        history_path = 'upstream/history/'+event_id+'.json'
        write_json(candidate/history_path, receipt);manifest = refresh(candidate)
        changes = {change['path']: blobs.get(change['path']) for change in expected}
        changes[LOCK] = json_bytes(incoming);changes[history_path] = json_bytes(receipt)
        changes[MANIFEST] = json_bytes(manifest)
        result = _transaction(root, changes, 'KPP_UPDATE')
        check(root);verify(root)
        return {'result': 'APPLIED', 'transaction': result['id'], 'changes': len(expected),
                'selection_digest': incoming['selection_digest'], 'checks': checks, 'network': 'NONE'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('check'); command.add_argument('--source', type=Path)
    command = commands.add_parser('plan');command.add_argument('--source', type=Path, required=True);command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('apply');command.add_argument('--source', type=Path, required=True);command.add_argument('--plan', type=Path, required=True);command.add_argument('--reviewed', action='store_true')
    for name in ('recover', 'restore'):
        command = commands.add_parser(name);command.add_argument('--reviewed', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            value = check(args.project, args.source)
        elif args.command == 'plan':
            value = plan(args.project, args.source, args.output)
            value = {'result': 'PLANNED', 'changes': value['changes'], 'plan_sha256': value['sha256'], 'execution': 'NONE'}
        elif args.command == 'apply':
            value = apply(args.project, args.plan, args.source, reviewed=args.reviewed)
        elif args.command == 'recover':
            value = recover(args.project, reviewed=args.reviewed)
        else:
            value = restore(args.project, reviewed=args.reviewed)
        print(json.dumps(value, indent=2));return 0
    except (ProjectError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('KPP upstream error: '+str(error), file=sys.stderr);return 2


if __name__ == '__main__':
    raise SystemExit(main())
