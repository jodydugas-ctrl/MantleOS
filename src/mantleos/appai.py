"""Pinned host assimilation and NEST-resident autonomic ports.

SELF is the entire host installation. The mantle directory is its system tissue.
No module import births an identity, starts a service, or invokes a provider.
"""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import time
import uuid

from . import compiled, engram, lifecycle, primer, specimens
from .transactions import atomic_bytes, body_lock, write_json


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def specification():
    return compiled.read_json(Path(__file__).parent / 'appai_assets/hermes.json')


def _git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def clone(output, *, source=None):
    """Explicit provisioning, without a configured remote or dependency installation."""
    root = lifecycle._destination(output)
    spec = specification()
    subprocess.run(['git', 'init', str(root)], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(root), 'fetch', '--depth', '1',
                    str(Path(source).resolve()) if source else spec['repository'], spec['commit']],
                   check=True, capture_output=True)
    subprocess.run(['git', '-C', str(root), 'checkout', '--detach', 'FETCH_HEAD'],
                   check=True, capture_output=True)
    return integrate(root)


def integrate(nest):
    root = Path(nest).resolve()
    spec = specification()
    if _git(root, 'rev-parse', 'HEAD') != spec['commit']:
        raise ValueError('Hermes revision differs from pinned host')
    if _git(root, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Integrate only a clean pinned host checkout')
    return _integrate(root, spec)


def _integrate(root, spec):
    root = Path(root).resolve()
    tissue = root / 'mantle'
    with body_lock(root):
        if tissue.exists():
            raise ValueError('Host already contains mantle tissue')
        changed = {}
        for relative, expected in spec['files'].items():
            path = root / relative
            if path.is_symlink() or _sha(path.read_bytes()) != expected:
                raise ValueError('Host source drift: ' + relative)
            changed[relative] = path.read_bytes().decode('utf-8')
        for item in spec['insertions']:
            text = changed[item['path']]
            if text.count(item['anchor']) != 1:
                raise ValueError('Ambiguous host connection: ' + item['semantic_event'])
            changed[item['path']] = text.replace(item['anchor'], item['source'] + item['anchor'], 1)
        for relative, text in changed.items():
            compile(text, relative, 'exec')  # Syntax validation only; host code is not run.
        ignore = root / '.gitignore'
        changed['.gitignore'] = (ignore.read_text('utf-8') if ignore.exists() else '') + '\n/mantle/\n'
        tissue.mkdir()
        original = tissue / 'original'
        inventory = {}
        patch = []
        try:
            for relative, text in changed.items():
                path = root / relative
                raw = path.read_bytes() if path.exists() else None
                if raw is not None:
                    backup = original / relative
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    backup.write_bytes(raw)
                after = text.encode('utf-8')
                patch.extend(difflib.unified_diff((raw or b'').decode('utf-8').splitlines(True),
                                                  text.splitlines(True), fromfile='a/' + relative,
                                                  tofile='b/' + relative))
                inventory[relative] = {'before': _sha(raw) if raw is not None else None,
                                       'after': _sha(after)}
            runtime = tissue / 'runtime/mantleos'
            shutil.copytree(Path(__file__).parent, runtime,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            (tissue / '__init__.py').write_text('"""NEST-local autonomic tissue; not the boundary of SELF."""\n')
            (tissue / 'runtime/__init__.py').write_text('')
            wrapper = ['from pathlib import Path', 'from .runtime.mantleos import appai',
                       'NEST = Path(__file__).resolve().parent.parent']
            for name in ('session_started', 'before_mind', 'after_mind', 'authorize_tool',
                         'tool_completed', 'turn_ended', 'session_ended'):
                wrapper.extend([f'def {name}(**kwargs):', f'    return appai.{name}(NEST, **kwargs)'])
            (tissue / 'nerves.py').write_text('\n'.join(wrapper) + '\n', encoding='utf-8', newline='\n')
            (tissue / 'host.patch').write_text(''.join(patch), encoding='utf-8', newline='\n')
            owned = {p.relative_to(tissue).as_posix(): _sha(p.read_bytes())
                     for p in tissue.rglob('*') if p.is_file()}
            receipt = {'schema': 'mantle.appai-assimilation/1', 'type': 'appai',
                       'self': '.', 'nest': '.', 'system_directory': 'mantle',
                       'upstream': {k: spec[k] for k in ('repository', 'commit')},
                       'connections': [{k: r[k] for k in ('path', 'symbol', 'semantic_event', 'direction')}
                                       for r in spec['insertions']], 'host_files': inventory, 'owned_files': owned}
            # The receipt and originals also make a partially written graft reversible.
            write_json(tissue / 'ASSIMILATION.json', receipt)
            for relative, text in changed.items():
                atomic_bytes(root / relative, text.encode('utf-8'))
            verify(root)
            return {'result': 'INTEGRATED', 'nest': str(root), 'self': str(root),
                    'connections': len(receipt['connections']), 'born': False}
        except Exception:
            # Preserve evidence if publication started; never silently overwrite drift.
            if not (tissue / 'ASSIMILATION.json').exists():
                shutil.rmtree(tissue)
            raise


def verify(nest):
    root = Path(nest).resolve()
    receipt = compiled.read_json(root / 'mantle/ASSIMILATION.json')
    if receipt.get('schema') != 'mantle.appai-assimilation/1' or receipt.get('self') != '.' or receipt.get('nest') != '.':
        raise ValueError('Invalid AppAI SELF/NEST binding')
    for relative, item in receipt['host_files'].items():
        path = compiled.relative_file(root, relative)
        if _sha(path.read_bytes()) != item['after']:
            raise ValueError('Integrated host drift: ' + relative)
    for relative, expected in receipt['owned_files'].items():
        path = compiled.relative_file(root / 'mantle', relative)
        if _sha(path.read_bytes()) != expected:
            raise ValueError('System tissue drift: ' + relative)
    return receipt


def reverse(nest):
    """Restore only declared host files. Retain private experience outside the host."""
    root = Path(nest).resolve()
    with body_lock(root):
        receipt = verify(root)
        for relative, item in receipt['host_files'].items():
            if item['before'] is None:
                (root / relative).unlink()
            else:
                raw = (root / 'mantle/original' / relative).read_bytes()
                if _sha(raw) != item['before']:
                    raise ValueError('Original source checksum mismatch')
                atomic_bytes(root / relative, raw)
        archive = root.parent / (root.name + '-detached-mantle-' + uuid.uuid4().hex[:10])
        (root / 'mantle').rename(archive)
        return {'result': 'REVERSED', 'retained_system_files': str(archive)}


def body(nest):
    return Path(nest).resolve() / 'mantle/private/body'


def _state_path(nest):
    return Path(nest).resolve() / 'mantle/private/state.json'


def status(nest):
    root = Path(nest).resolve()
    verify(root)
    state = compiled.read_json(_state_path(root)) if _state_path(root).exists() else {'phase': 'UNBORN'}
    return {**state, 'type': 'appai', 'self': str(root), 'nest': str(root),
            'system_directory': str(root / 'mantle'), 'body': str(body(root))}


def birth(nest, *, name='Hermes AppAI'):
    root = Path(nest).resolve()
    with body_lock(root):
        verify(root)
        if body(root).exists():
            raise ValueError('AppAI already born')
        specimens.fresh(body(root), name=name, expression='appai')
        write_json(_state_path(root), {'phase': 'STASIS', 'turns': {}, 'allowed_tools': [], 'heartbeats': 0})
        return status(root)


def phase(nest, active, *, allowed_tools=()):
    root = Path(nest).resolve()
    if type(active) is not bool or not all(isinstance(n, str) and 0 < len(n) <= 128 for n in allowed_tools):
        raise ValueError('Invalid physiology or operator tool grant')
    with body_lock(root):
        state = status(root)
        if state['phase'] == 'UNBORN':
            raise ValueError('Explicit birth required')
        state['phase'] = 'ACTIVE' if active else 'STASIS'
        state['allowed_tools'] = sorted(set(allowed_tools)) if active else []
        write_json(_state_path(root), state)
        return state


def record(nest, event, values, *, request_id=None):
    """Append redacted semantic events, with replay suppression under the NEST lock."""
    root = Path(nest).resolve()
    with body_lock(root):
        state = status(root)
        if state['phase'] != 'ACTIVE':
            return {'status': state['phase']}
        target = body(root)
        records = engram.read(target / 'ENGRAM.jsonl')
        if request_id and any(r['type'] == 'appai-event' and r['body'].get('request_id') == request_id for r in records):
            return {'status': 'REPLAY'}
        return lifecycle.admit(target, 'appai-event', {'event': event, 'values': values,
                               'request_id': request_id}, expected_head=engram.head(target / 'ENGRAM.jsonl'))


def _key(values):
    return _sha((str(values.get('session_id', '')) + '\0' + str(values.get('turn_id', ''))).encode())


def before_mind(nest, **values):
    root = Path(nest).resolve()
    with body_lock(root):
        state = status(root)
        message = str(values.get('user_message', ''))
        addressed = message.lstrip().lower().startswith('@appai')
        if state['phase'] == 'UNBORN':
            return {'context': '', 'status': 'UNBORN'}
        state['turns'][_key(values)] = addressed
        state['turns'] = dict(list(state['turns'].items())[-128:])
        write_json(_state_path(root), state)
        if not addressed or state['phase'] != 'ACTIVE':
            return {'context': '', 'status': state['phase']}
        record(root, 'communication.user.message', {'text': message[:4096]}, request_id='user-' + _key(values))
        return {'context': primer.load_primer(body(root))['compiled'] +
                '\nSELF is the complete host installation. NEST: ' + str(root), 'status': 'ACTIVE'}


def authorize_tool(nest, **values):
    state = status(nest)
    if not state.get('turns', {}).get(_key(values)):
        return None  # Ordinary Hermes authority remains independent.
    if state['phase'] != 'ACTIVE':
        return 'AppAI is in stasis; motor activity denied'
    name = str(values.get('tool_name', ''))
    record(nest, 'appai.limb.proposed', {'tool': name[:128]})
    if name not in state['allowed_tools']:
        return 'AppAI tool lacks an operator grant'
    return None  # Hermes still applies its own native guardrails.


def _event(nest, name, values):
    fields = ('session_id', 'turn_id', 'surface', 'status', 'reason', 'tool_name',
              'completed', 'failed', 'interrupted')
    safe = {k: str(values[k])[:160] for k in fields if k in values}
    return record(nest, name, safe)


def session_started(nest, **values):
    return _event(nest, 'body.session.started', values)


def after_mind(nest, **values):
    return _event(nest, 'appai.mind.turn', values)


def tool_completed(nest, **values):
    return _event(nest, 'body.tool.completed', values)


def turn_ended(nest, **values):
    return _event(nest, 'body.turn.ended', values)


def session_ended(nest, **values):
    return _event(nest, 'body.session.ended', values)


def tick(nest):
    root = Path(nest).resolve()
    with body_lock(root):
        state = status(root)
        if state['phase'] != 'ACTIVE':
            return state
        state['heartbeats'] += 1
        # Increment first: an interrupted tick is visible, never replayed as a fresh one.
        write_json(_state_path(root), state)
        record(root, 'heartbeat', {'number': state['heartbeats'], 'mind': 'OPTIONAL'})
        return status(root)


def run(nest, *, ticks=1, interval=1.0, policy_id=None, request_id=None):
    if type(ticks) is not int or not 1 <= ticks <= 1000 or not 0 <= interval <= 60:
        raise ValueError('Foreground activation exceeds bounds')
    if bool(policy_id) != bool(request_id):
        raise ValueError('A mission cycle requires a standing policy and durable request id')
    result = None
    for index in range(ticks):
        if index:
            time.sleep(interval)
        result = tick(nest)
        if policy_id and result['phase'] == 'ACTIVE':
            from . import missions
            mission = missions.dispatch(nest, policy_id, request_id=request_id,
                                        context={'purpose': 'Resident AppAI specimen inspection'})
            if mission['phase'] == 'READY':
                mission = missions.run(nest, mission['id'])
            result['mission'] = {'id': mission['id'], 'phase': mission['phase'],
                                 'admission': 'Explicit result review required'}
    return result
