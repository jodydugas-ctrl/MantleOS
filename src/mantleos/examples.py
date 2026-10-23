"""Small recipes over one runtime; generated examples and identities stay local."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import json

from . import anchor_app_document, anchor_apps, appai, compiled, engram, lifecycle, observer, specimens
from .hosted import HostedBridge
from .transactions import atomic_bytes, write_json

CATALOG = {
    'raven': {'type': 'engram', 'description': 'Fresh founding persona, new identity, blank memory; cartridge and PNG.'},
    'hermes': {'type': 'appai', 'description': 'Pinned GitHub host with resident autonomic tissue; SELF is its NEST.'},
    'notepad': {'type': 'bio-software', 'description': 'Interactive, qualified Anchor Notepad; no AppAI classification.'},
    'observer': {'type': 'bio-agent', 'description': 'Read-only specimen observation and change proposals.'},
}


def build(name, output, *, source=None):
    if name not in CATALOG:
        raise ValueError('Unknown example')
    if name == 'hermes':
        return appai.clone(output, source=source)
    root = lifecycle._destination(output)
    root.mkdir()
    if name == 'notepad':
        if source:
            document = anchor_app_document.parse(Path(source).read_bytes().decode('utf-8'))
            if document['contract']['profile'] != 'NOTEPAD_LLM/1.3':
                raise ValueError('Notepad example requires its supported profile')
            program = document['program']
        else:
            program = anchor_apps.notepad_program()
        # Recompile trusted qualified semantics; do not execute supplied target code.
        document = anchor_apps.app_document(program, name='Notepad')
        parsed = anchor_app_document.parse(document)
        (root / 'Notepad.anchor').write_text(document, encoding='utf-8', newline='\n')
        (root / 'index.html').write_text(parsed['canvas'], encoding='utf-8', newline='\n')
        result = {'result': 'BUILT', 'type': 'bio-software', 'profile': 'NOTEPAD_LLM/1.3',
                  'document': str(root / 'Notepad.anchor'), 'interface': str(root / 'index.html')}
    else:
        founding = specimens.founding_material(source) if name == 'raven' and source else None
        result = specimens.fresh(root / 'body', name='Raven' if founding else 'Synthetic ' + name.title(),
                                 expression='engram' if name == 'raven' else 'bio-agent', founding=founding)
        if name == 'raven':
            for fmt, extension in [('cartridge', 'vcw'), ('chroma', 'png')]:
                lifecycle.save(root / 'body', root / ('engram.' + extension), format=fmt)
            result['carriers'] = ['engram.vcw', 'engram.png']
            result['founding'] = 'selected-private-source' if founding else 'synthetic-fixture'
    write_json(root / 'EXAMPLE.json', {'schema': 'mantle.example/1', 'name': name, **result})
    return result


def observe(directory, source, *, request_id):
    from .json_contract import identifier
    identifier(request_id)
    root = Path(directory).resolve()
    target = root / 'body'
    descriptor = compiled.read_json(target / 'EXPRESSION.json')
    if descriptor['type'] != 'bio-agent':
        raise ValueError('Not an Observer Bio-Agent')
    state_path = root / 'observer-state.json'
    previous = compiled.read_json(state_path) if state_path.exists() else None
    output = root / 'observations' / request_id
    if output.exists():
        raise ValueError('Observation request already exists; choose a new request id')
    report = observer.observe(source, output, previous=previous)
    lifecycle.admit(target, 'observation', report, expected_head=engram.head(target / 'ENGRAM.jsonl'))
    write_json(state_path, report['snapshot'])
    return report


def handoff(directory, message, *, request_id, model_id='CURRENT_HOST'):
    from .json_contract import identifier
    identifier(request_id)
    root = Path(directory).resolve()
    bridge = HostedBridge(root / 'body', model_id=model_id)
    packet = bridge.open(message, request_id=request_id)
    destination = root / 'handoffs' / (request_id + '-open.json')
    atomic_bytes(destination, (json.dumps(packet, indent=2) + '\n').encode(), replace=False)
    return {'status': 'WAITING_FOR_HOST', 'preparation': str(destination), 'model_called': False,
            'next': 'Provide the frame to the current host; use bridge-advance and bridge-commit for checked admission.'}


def scripted_encounter(body, *, request_id='scripted-first'):
    """An explicitly labeled test fixture using the real hosted transaction protocol."""
    from .hosted import digest
    bridge = HostedBridge(body, model_id='SCRIPTED_FIXTURE', broker=lambda authority, name: authority == 'release')
    opened = bridge.open('Remember the synthetic observation: the specimen is ready.', request_id=request_id)
    if opened['status'] == 'replay':
        return bridge.commit(opened)
    orientation = {'schema': 'mantle.orientation/1', 'mode': 'TARGETED', 'percepts': [],
                   'unknowns': [], 'goals': [], 'options': [], 'predictions': [], 'action_request': None}
    advanced = bridge.advance(opened, orientation)
    reply = {'schema': 'mantle.response-proposal/1', 'orientation_sha256': digest(orientation),
             'reply': 'Scripted fixture: the synthetic observation has been recorded.',
             'candidates': [], 'cognition': {'schema': 'mantle.respond-cognition/1',
             'observation_sha256': None, 'delta': [], 'revision': [], 'intent': {'kind': 'scripted-demonstration'}}}
    return bridge.commit(advanced, reply)


def serve_notepad(directory, *, port=0):
    root = Path(directory).resolve()
    document = anchor_app_document.parse((root / 'Notepad.anchor').read_text('utf-8'))
    data = (root / 'index.html').read_bytes()
    if hashlib.sha256(data).hexdigest() != document['contract']['canvas_sha256']:
        raise ValueError('Notepad browser artifact differs from its contract')

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/', '/index.html'):
                self.send_error(404); return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers(); self.wfile.write(data)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(('127.0.0.1', port), Handler) as server:
        print(json.dumps({'status': 'SERVING', 'url': f'http://127.0.0.1:{server.server_port}',
                          'stop': 'Ctrl+C', 'type': 'bio-software'}), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def demo(output):
    """Synthetic portable-Engram, Anchor, and Observer walkthrough, entirely offline."""
    root = lifecycle._destination(output); root.mkdir()
    build('raven', root / 'engram')
    target = root / 'engram/body'
    assert engram.read(target / 'ENGRAM.jsonl') == []
    scripted_encounter(target)
    for fmt, ext in [('cartridge', 'vcw'), ('chroma', 'png')]:
        lifecycle.save(target, root / ('experienced.' + ext), format=fmt)
        restored = root / (fmt + '-restored')
        lifecycle.restore(root / ('experienced.' + ext), restored)
        assert compiled.load(restored)['sha256'] == compiled.load(target)['sha256']
    build('notepad', root / 'notepad')
    specimen = root / 'specimen'; specimen.mkdir()
    (specimen / 'sample.py').write_text('def answer():\n    return 42\n', encoding='utf-8')
    build('observer', root / 'observer')
    first = observe(root / 'observer', specimen, request_id='first')
    second = observe(root / 'observer', specimen, request_id='second')
    assert first['changed_paths'] == ['sample.py'] and not second['changed_paths']
    result = {'result': 'PASS', 'engram': 'blank -> scripted encounter -> two verified carriers',
              'notepad': 'qualified interactive artifact; use run notepad to open',
              'observer': 'stable read-only change detection', 'model': 'SCRIPTED_FIXTURE',
              'network_calls': 0, 'hermes': 'separate pinned-host qualification'}
    write_json(root / 'report.json', result)
    return result
