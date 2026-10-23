"""Publish shell and module revisions during construction through a chosen bridge."""
from . import progressive_app as app


class ProgressiveBuild:
    def __init__(self, body, workspace, registry, broker, *, bridge=None,
                 progressive=True, preserve_state=True):
        self.body, self.workspace = body, workspace
        self.registry, self.broker = registry, broker
        self.bridge = registry.select('html-app', preferred=bridge,
            progressive=progressive, preserve_state=preserve_state).name
        self.progressive, self.preserve_state = progressive, preserve_state

    def _authorize_build(self, capability):
        if not self.broker('effect.execute', capability):
            raise PermissionError('Build mutation authority denied')
        bridge = self.registry.select('html-app', preferred=self.bridge,
            progressive=self.progressive, preserve_state=self.preserve_state)
        if not self.broker(bridge.authority, bridge.name):
            raise PermissionError('Bridge publication authority denied')

    def sync(self):
        """Retry publication of the current revision after a host delivery failure."""
        return self.registry.deliver(app.payload(self.workspace), broker=self.broker,
            preferred=self.bridge, progressive=self.progressive, preserve_state=self.preserve_state)

    def start(self, shell, app_id):
        self._authorize_build('app.build.start')
        app.start(self.workspace, shell, app_id, body=self.body)
        return self.sync()

    def add(self, source, module_id, kind, depends, *, expected_revision):
        self._authorize_build('app.build.add')
        app.add(self.workspace, source, module_id, kind, depends,
            expected_revision=expected_revision, body=self.body)
        return self.sync()

    def finish(self, *, expected_revision):
        self._authorize_build('app.build.finish')
        app.finish(self.workspace, expected_revision=expected_revision, body=self.body)
        return self.sync()
