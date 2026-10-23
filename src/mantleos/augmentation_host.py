"""Synthetic established host: useful without any cognition or sensory adapter."""
from pathlib import Path
import uuid
from . import compiled, lifecycle
from .transactions import atomic_bytes, body_lock


class Notebook:
    def __init__(self, body, destination):
        self.body = Path(body)
        self.destination = Path(destination)

    def read(self):
        with body_lock(self.body):
            compiled.load(self.body)
            path = self.body/'PROGRAM-STATE.json'
            states = compiled.read_json(path) if path.exists() else {}
            return {'text': states.get('notepad', {}).get('text', '')}

    def edit(self, text):
        if not isinstance(text, str):
            raise ValueError('Text must be a string')
        lifecycle.run(self.body, 'notepad', {'op': 'INSERT', 'text': text},
                      commit=True, request_id='native-'+uuid.uuid4().hex)
        return self.read()

    def save(self):
        with body_lock(self.body):
            raw = self.read()['text'].encode('utf-8')
            atomic_bytes(self.destination, raw)
            return {'bytes': len(raw), 'filename': self.destination.name}
