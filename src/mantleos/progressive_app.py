"""Revisioned ANCHOR-emitted modules and a loopback live HTML bridge."""
from copy import deepcopy
from pathlib import Path
import json
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html.parser import HTMLParser
from .effects import digest
from .transactions import body_lock, write_json
from .anchor_language import execute_blueprint
from .anchor_canvas import outside

MAX_MODULE_BYTES = 512_000
MAX_APP_BYTES = 4_000_000
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')


def emitted(path):
    source = Path(path).read_text(encoding='utf-8')
    result = execute_blueprint(source)
    if result.get('profile') != 'EMIT_TEXT/0.2':
        raise ValueError('App modules must use native EMIT_TEXT ANCHOR')
    content = result['stdout']
    if len(content.encode('utf-8')) > MAX_MODULE_BYTES:
        raise ValueError('Module exceeds byte budget')
    return content, digest(source)


def _seal(state):
    state = deepcopy(state)
    state.pop('sha256', None)
    state['sha256'] = digest(state)
    return state


def _validate(state):
    if not isinstance(state, dict) or state.get('schema') != 'mantle.progressive-app/1':
        raise ValueError('Invalid app state schema')
    if state.get('sha256') != _seal(state)['sha256']:
        raise ValueError('App state checksum mismatch')
    if len(json.dumps(state).encode()) > MAX_APP_BYTES:
        raise ValueError('App exceeds byte budget')
    if type(state.get('revision')) is not int or state['revision'] < 1:
        raise ValueError('Invalid app revision')
    if not isinstance(state.get('app_id'), str) or not NAME.fullmatch(state['app_id']):
        raise ValueError('Invalid app id')
    if state.get('phase') not in {'BUILDING', 'COMPLETE'} or not isinstance(state.get('shell'), str):
        raise ValueError('Invalid phase or shell')
    modules = state.get('modules')
    if not isinstance(modules, list) or len(modules) > 128:
        raise ValueError('Invalid module inventory')
    ids = set()
    for module in modules:
        mid = module.get('id')
        if not isinstance(mid, str) or not NAME.fullmatch(mid) or mid in ids:
            raise ValueError('Invalid or duplicate module id')
        ids.add(mid)
        if module.get('kind') not in {'html', 'css', 'javascript'}:
            raise ValueError('Invalid module kind')
        if not isinstance(module.get('content'), str) or len(module['content'].encode()) > MAX_MODULE_BYTES:
            raise ValueError('Invalid module content')
        deps = module.get('depends')
        if not isinstance(deps, list) or len(deps) != len(set(deps)) or any(
                not isinstance(d, str) or not NAME.fullmatch(d) or d == mid for d in deps):
            raise ValueError('Invalid module dependencies')
        if module.get('content_sha256') != digest(module['content']):
            raise ValueError('Module checksum mismatch')
    edges = {m['id']: m['depends'] for m in modules}
    def visit(mid, stack, seen):
        if mid in stack:
            raise ValueError('Cyclic module dependencies')
        if mid in seen or mid not in edges:
            return
        for dep in edges[mid]:
            visit(dep, stack | {mid}, seen)
        seen.add(mid)
    seen = set()
    for mid in edges:
        visit(mid, set(), seen)
    if state['phase'] == 'COMPLETE':
        if any(d not in ids for m in modules for d in m['depends']):
            raise ValueError('Cannot finish with missing dependencies')
        class Gates(HTMLParser):
            def handle_starttag(self, tag, attrs):
                for key, value in attrs:
                    if key == 'data-mantle-requires' and value:
                        if any(dep not in ids for dep in value.split()):
                            raise ValueError('Cannot finish with missing control dependencies')
        gates = Gates()
        gates.feed(state['shell'])
        for module in modules:
            if module['kind'] == 'html': gates.feed(module['content'])
    return state


def read(workspace):
    with body_lock(workspace):
        return _validate(json.loads((Path(workspace) / 'app-state.json').read_text('utf-8')))


def start(workspace, shell, app_id, *, body):
    workspace = outside(body, workspace)
    if not NAME.fullmatch(app_id):
        raise ValueError('Invalid app id')
    content, source_sha = emitted(shell)
    state = _seal({'schema': 'mantle.progressive-app/1', 'app_id': app_id,
                   'revision': 1, 'phase': 'BUILDING', 'shell': content,
                   'shell_source_sha256': source_sha, 'modules': []})
    _validate(state)
    with body_lock(workspace):
        if workspace.exists():
            raise ValueError('App workspace already exists')
        workspace.mkdir(parents=True)
        write_json(workspace / 'app-state.json', state)
    return state


def add(workspace, source, module_id, kind, depends, *, expected_revision, body):
    workspace = outside(body, workspace)
    content, source_sha = emitted(source)
    with body_lock(workspace):
        state = read(workspace)
        if state['revision'] != expected_revision:
            raise ValueError('Stale app revision')
        if state['phase'] != 'BUILDING':
            raise ValueError('App is complete; start a new build for revisions')
        state['modules'].append({'id': module_id, 'kind': kind, 'depends': depends,
                                 'content': content, 'content_sha256': digest(content),
                                 'anchor_source_sha256': source_sha})
        state['revision'] += 1
        state = _seal(state)
        _validate(state)
        write_json(workspace / 'app-state.json', state)
        return state


def finish(workspace, *, expected_revision, body):
    workspace = outside(body, workspace)
    with body_lock(workspace):
        state = read(workspace)
        if state['revision'] != expected_revision:
            raise ValueError('Stale app revision')
        if state['phase'] != 'BUILDING':
            raise ValueError('App is already complete')
        state.update(phase='COMPLETE', revision=state['revision'] + 1)
        state = _seal(state)
        _validate(state)
        write_json(workspace / 'app-state.json', state)
        return state


def runtime_source():
    return (Path(__file__).parent / 'progressive_runtime.js').read_text('utf-8')


def render(state, *, snapshot_url=None):
    _validate(state)
    # JSON script text must never allow emitted content to terminate its carrier.
    encoded = json.dumps(state, ensure_ascii=True).replace('<', '\\u003c')
    url = json.dumps(snapshot_url)
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Bio-App</title><style>body{font-family:system-ui;margin:24px}'
            '#mantle-status{font-size:13px;color:#555;margin-top:20px}'
            '[data-mantle-pending]{opacity:.55}</style></head><body>'
            '<main id="mantle-root"></main><aside id="mantle-status" aria-live="polite"></aside>'
            '<script type="application/json" id="mantle-initial">' + encoded + '</script>'
            '<script>' + runtime_source() + '</script><script>'
            'MantleCanvas.apply(JSON.parse(document.getElementById("mantle-initial").textContent));'
            'MantleCanvas.poll(' + url + ');</script></body></html>')


def payload(workspace, *, output=None):
    state = read(workspace)
    return {'kind': 'html-app', 'snapshot': state, 'html': render(state),
            'workspace': str(Path(workspace).resolve()), 'output': output}


def live_server(workspace, *, body, port=0):
    workspace = outside(body, workspace)
    read(workspace)
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('Invalid local port')
    token = uuid.uuid4().hex
    prefix = '/' + token
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            allowed_hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in allowed_hosts:
                self.send_error(403)
                return
            if self.path not in {prefix + '/app', prefix + '/snapshot'}:
                self.send_error(404)
                return
            try:
                state = read(workspace)
                is_app = self.path.endswith('/app')
                data = (render(state, snapshot_url=prefix + '/snapshot') if is_app else
                        json.dumps(state, ensure_ascii=True)).encode('utf-8')
            except (ValueError, OSError) as exc:
                self.send_error(503, 'App snapshot unavailable')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8' if is_app else 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.app_url = f'http://127.0.0.1:{server.server_port}{prefix}/app'
    return server
