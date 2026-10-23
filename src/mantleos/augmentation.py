"""Bounded synthetic host augmentation. Run with --output UNUSED_DIRECTORY."""
from pathlib import Path
import argparse
import hashlib
import uuid
from . import engram, lifecycle, organism
from .augmentation_host import Notebook
from .effects import Capability, CapabilityRegistry, CheckedActionExecutor
from .transactions import body_lock, write_json


class Adapter:
    """Explicit host grants, same native functions, optional fallible observation."""
    def __init__(self, host, *, allowed=(), observer=None):
        self.host = host
        self.observer = observer
        self.allowed = frozenset(allowed)
        if self.allowed - {'read', 'edit', 'save'}:
            raise ValueError('Unknown host operation')
        registry = CapabilityRegistry()
        for name in ('read', 'edit', 'save'):
            registry.register(Capability(name, 'native-host-operation', 'host-grant',
                'synthetic-notebook/'+name,
                lambda args, op=name: self.user(op, **args),
                lambda result: isinstance(result, dict) and 'native' in result))
        self.executor = CheckedActionExecutor(registry, lambda authority, name: name in self.allowed)

    def user(self, operation, **arguments):
        if operation not in ('read', 'edit', 'save'):
            raise ValueError('Unknown host operation')
        result = getattr(self.host, operation)(**arguments)
        # Observation must never disable an already completed native operation.
        try:
            if self.observer is not None:
                self.observer(operation, result)
            with body_lock(self.host.body):
                lifecycle.admit(self.host.body, 'host-observation',
                    {'operation': operation, 'result': result},
                    expected_head=engram.head(self.host.body/'ENGRAM.jsonl'))
            observation = 'RECORDED'
        except Exception as exc:
            observation = 'UNAVAILABLE:'+type(exc).__name__
        return {'native': result, 'observation': observation}

    def motor(self, proposal):
        if not isinstance(proposal, dict) or set(proposal) != {'operation', 'arguments'}:
            raise ValueError('Proposal needs operation and arguments; it conveys no grant')
        with body_lock(self.host.body):
            result = self.executor.execute(proposal['operation'], proposal['arguments'],
                                           request_id=uuid.uuid4().hex)
            lifecycle.admit(self.host.body, 'host-action-evidence', result,
                expected_head=engram.head(self.host.body/'ENGRAM.jsonl'))
            return result


def demonstrate(output):
    from .kpp import core, workshop
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Use an unused output directory')
    output.mkdir(parents=True)
    body = output/'body'; organism.create(body, identity='synthetic-augmentation')
    host = Notebook(body, output/'draft.txt')
    adapter = Adapter(host, allowed=('read', 'edit', 'save'))
    pins = {}
    for name in ('augmentation_host.py', 'augmentation.py'):
        raw = (Path(__file__).parent/name).read_bytes()
        path = output/'retained-source'/name; path.parent.mkdir(exist_ok=True); path.write_bytes(raw)
        pins[name] = hashlib.sha256(raw).hexdigest()
    rows = []
    def observe(action, expected, actual, scenario):
        rows.append({'operation': action, 'source': 'augmentation_host.py:Notebook.'+action,
            'source_sha256': pins['augmentation_host.py'], 'action': action,
            'observation': actual, 'expected': expected, 'scenario': scenario,
            'passed': expected == actual})
    absent = organism.consult(body)['status']
    def fail(_): raise ConnectionError('Synthetic unavailable MIND')
    failed = organism.consult(body, fail)['status']
    text = 'Synthetic draft\nUnicode: café 🌱'
    observe('edit', text, adapter.user('edit', text=text)['native']['text'], absent)
    observe('read', text, adapter.user('read')['native']['text'], failed)
    prefix = (body/'ENGRAM.jsonl').read_bytes()
    proposed = organism.consult(body, lambda _: {'operation':'save', 'arguments':{}})
    saved = adapter.motor(proposed['candidate'])
    observe('save', text.encode('utf-8').hex(), host.destination.read_bytes().hex(), 'FAKE_MIND')
    assert saved['stage'] == 'VERIFIED'
    denied = Adapter(host).motor({'operation':'edit', 'arguments':{'text':'DENIED'}})
    assert denied['stage'] == 'FAILED' and host.read()['text'] == text
    def bad_sensor(*_): raise OSError('Synthetic sensor failure')
    broken = Adapter(host, observer=bad_sensor)
    sensed = broken.user('edit', text='!')
    observe('edit', text+'!', sensed['native']['text'], 'SENSOR_FAILED')
    assert sensed['observation'] == 'UNAVAILABLE:OSError'
    assert (body/'ENGRAM.jsonl').read_bytes().startswith(prefix)
    resources = Path(core.__file__).parent/'resources'
    recipe = core.read_json(resources/'recipes/augmentation-v4.json')
    workshop.begin(output/'workspace', recipe, resources)
    result = {'schema':'mantle.augmentation-demonstration/1', 'phase':'BUILDING',
        'acceptance':'NOT_GRANTED', 'recipe_sha256':core.digest(recipe), 'source_pins':pins, 'connections':rows,
        'mind_absent':absent, 'mind_failed':failed, 'denied_action':denied['stage'],
        'sensor_failure':sensed['observation'], 'history_prefix_preserved':True,
        'result':'PASS' if all(row['passed'] for row in rows) else 'FAIL',
        'scope':'Synthetic notebook only; no complete Hermes parity or live-model measurement'}
    write_json(output/'report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = demonstrate(args.output)
    print(__import__('json').dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['result'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
