"""Pluggable app output bridges. Canvas providers are supplied by the host."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from .effects import digest
from .transactions import atomic_bytes


@dataclass(frozen=True)
class Bridge:
    name: str
    accepts: frozenset[str]
    progressive: bool
    state_preserving: bool
    provider: Callable[[dict], dict]
    authority: str = 'effect.execute'


class BridgeRegistry:
    def __init__(self):
        self._bridges = {}

    def register(self, bridge):
        if bridge.name in self._bridges:
            raise ValueError('Duplicate bridge')
        self._bridges[bridge.name] = bridge

    def catalog(self):
        return [dict(name=b.name, accepts=sorted(b.accepts), progressive=b.progressive,
                     state_preserving=b.state_preserving, authority=b.authority,
                     binding='BOUND') for b in self._bridges.values()] + ([] if 'html.canvas' in self._bridges else [
            dict(name='html.canvas', accepts=['html-app'], progressive=False,
                 state_preserving=False, binding='HOST_BOUND', authority='release')])

    def select(self, kind, *, preferred=None, progressive=False, preserve_state=False):
        candidates = list(self._bridges.values())
        if preferred:
            candidates = [b for b in candidates if b.name == preferred]
        candidates = [b for b in candidates if kind in b.accepts and
                      (not progressive or b.progressive) and
                      (not preserve_state or b.state_preserving)]
        if not candidates:
            raise ValueError('No bound bridge meets the task requirements')
        return candidates[0]

    def deliver(self, payload, *, broker, preferred=None, progressive=False, preserve_state=False):
        bridge = self.select(payload['kind'], preferred=preferred,
                             progressive=progressive, preserve_state=preserve_state)
        if not broker(bridge.authority, bridge.name):
            raise PermissionError('Bridge delivery authority denied')
        result = bridge.provider(payload)
        if not isinstance(result, dict):
            raise ValueError('Bridge provider must return a receipt object')
        return {'schema': 'mantle.bridge-delivery/1', 'bridge': bridge.name,
                'payload_sha256': digest(payload), 'receipt': result}


def file_provider(body):
    def publish(payload):
        from .anchor_canvas import outside
        target = outside(body, payload['output'])
        data = payload['html'].encode('utf-8')
        atomic_bytes(target, data, replace=False)
        return {'status': 'FILE_CREATED', 'output': str(target),
                'render_status': 'NOT_OBSERVED'}
    return publish


def python_provider(payload):
    from .anchor_language import inspect_blueprint
    from .anchor_engine.tools.anchor_compile import translate
    source = payload['source']
    inspect_blueprint(source)
    return {'status': 'TRANSLATED_NOT_EXECUTED', 'python': translate(source)}


class LocalLiveHost:
    """Embedding host owns this bridge's lifetime; close it when finished."""
    def __init__(self, body, *, port=0):
        self.body, self.port = body, port
        self.server = None
        self.thread = None
        self.workspace = None
        self.bridge = Bridge('html.live', frozenset({'html-app'}), True, True, self.publish)

    def publish(self, payload):
        import threading
        from .progressive_app import live_server, read
        workspace = str(Path(payload['workspace']).resolve())
        current = read(workspace)
        if digest(current) != digest(payload['snapshot']):
            raise ValueError('Stale live delivery snapshot')
        if self.server is not None and workspace != self.workspace:
            raise ValueError('Live host already belongs to another app workspace')
        if self.server is None:
            self.server = live_server(workspace, body=self.body, port=self.port)
            self.workspace = workspace
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
        return {'status': 'LISTENING', 'url': self.server.app_url,
                'revision': current['revision'], 'render_status': 'NOT_OBSERVED'}

    def close(self):
        if self.server is not None:
            self.server.shutdown(); self.server.server_close()
            self.thread.join(timeout=3)
            self.server = self.thread = None


def canvas_bridge(publisher, *, progressive=False, state_preserving=False):
    """publisher(packet) must acknowledge the exact app/revision/content digest.

    Progressive hosts apply snapshot modules to the mounted MantleCanvas runtime,
    rather than replacing its iframe. Register only capabilities the host supports.
    """
    if state_preserving and not progressive:
        raise ValueError('State preservation requires progressive canvas support')
    acknowledged = {}
    import threading
    lock = threading.RLock()
    def publish(payload):
        from .progressive_app import _validate, render
        from copy import deepcopy
        with lock:
            snapshot = _validate(deepcopy(payload['snapshot']))
            html = render(snapshot)
            packet = {'schema': 'mantle.canvas-request/1', 'app_id': snapshot['app_id'],
                      'revision': snapshot['revision'], 'snapshot_sha256': digest(snapshot),
                      'html_sha256': digest(html),
                      'operation': 'mount-or-apply' if progressive else 'replace-document',
                      'html': html, 'snapshot': snapshot}
            previous = acknowledged.get(packet['app_id'])
            if previous:
                if packet['revision'] < previous['revision']:
                    raise ValueError('Stale canvas revision')
                if packet['revision'] == previous['revision']:
                    if packet['snapshot_sha256'] != previous['snapshot_sha256']:
                        raise ValueError('Conflicting canvas revision')
                    if packet['html_sha256'] != previous['html_sha256']:
                        raise ValueError('Canvas runtime changed; remount required')
                    return deepcopy(previous)
            receipt = publisher(deepcopy(packet))
            required = {'schema': 'mantle.canvas-receipt/1', 'app_id': packet['app_id'],
                        'revision': packet['revision'], 'snapshot_sha256': packet['snapshot_sha256'],
                        'html_sha256': packet['html_sha256'],
                        'status': 'APPLIED'}
            if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in required.items()):
                raise ValueError('Missing or mismatched host canvas acknowledgement')
            acknowledged[packet['app_id']] = deepcopy(receipt)
            return receipt
    return Bridge('html.canvas', frozenset({'html-app'}), progressive,
                  state_preserving, publish, 'release')


def default_registry(body, *, canvas=None, live=None):
    reg = BridgeRegistry()
    if canvas is not None:
        reg.register(canvas)
    if live is not None:
        reg.register(live)
    reg.register(Bridge('html.file', frozenset({'html-app'}), False, False, file_provider(body)))
    reg.register(Bridge('python.translate', frozenset({'anchor-source'}), False, False, python_provider))
    return reg
