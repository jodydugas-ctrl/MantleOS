import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mantleos import attachments, cartridge, chromamem, compiled, organism, lifecycle


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.body = self.root / 'body'
        organism.create(self.body, identity='attachment-test')
        self.data = b'opaque candidate, never executable'
        self.pin = hashlib.sha256(self.data).hexdigest()

    def add(self, source=None, output=None, data=None):
        data = self.data if data is None else data
        return attachments.add(source or self.body, data, media_type='application/octet-stream',
                               expected_sha256=hashlib.sha256(data).hexdigest(),
                               output=output or self.root / 'attached')

    def snapshot(self, body):
        return {n: p.read_bytes() for p, n in cartridge.tracked_paths(body)}

    def test_native_roundtrips_preserve_body_and_multiple_attachments(self):
        # Commit real notebook state before transport, and compare all original files.
        lifecycle.run(self.body, 'notepad', {'action': 'insert', 'text': 'kept'},
                      commit=True, request_id='attachment-memory')
        before = self.snapshot(self.body)
        first = self.root / 'attached'
        second = self.root / 'second'
        self.add(output=first)
        self.add(source=first, output=second, data=b'second candidate')
        self.assertEqual(before, self.snapshot(self.body))
        for name, data in before.items():
            if name != 'COMPILED.json':
                self.assertEqual(data, (second / name).read_bytes(), name)
        compiled.load(second)
        for kind in ('cartridge', 'chroma'):
            archive = self.root / (kind + ('.png' if kind == 'chroma' else '.vcw'))
            restored = self.root / (kind + '-restored')
            if kind == 'cartridge':
                cartridge.pack(second, archive)
                cartridge.unpack(archive, restored)
            else:
                chromamem.export_body(second, archive)
                chromamem.extract_body(archive, restored)
            self.assertEqual(self.snapshot(second), self.snapshot(restored))
            self.assertEqual(len(attachments.inspect(restored)['attachments']), 2)
            self.assertEqual(compiled.load(second), compiled.load(restored))
            self.assertEqual(lifecycle.run(second, 'greeting'), lifecycle.run(restored, 'greeting'))
            target = self.root / (kind + '.raw')
            attachments.extract(restored, sha256=self.pin, output=target)
            self.assertEqual(target.read_bytes(), self.data)

    def test_legacy_body(self):
        self.assertEqual(attachments.inspect(self.body)['attachments'], [])
        compiled.load(self.body)

    def test_refusals_and_source_preservation(self):
        before = self.snapshot(self.body)
        for data, pin, media in ((b'', self.pin, 'application/octet-stream'),
                                 (b'x' * (attachments.MAX_BYTES + 1), self.pin, 'application/octet-stream'),
                                 (self.data, '0' * 64, 'application/octet-stream'),
                                 (self.data, self.pin, '../unsafe')):
            with self.assertRaises(ValueError):
                attachments.add(self.body, data, media_type=media,
                                expected_sha256=pin, output=self.root / 'failed')
            self.assertFalse((self.root / 'failed').exists())
        self.add()
        with self.assertRaises(FileExistsError):
            self.add()
        with self.assertRaises(ValueError):
            self.add(source=self.root / 'attached', output=self.root / 'duplicate')
        with self.assertRaises(ValueError):
            self.add(output=self.body / 'nested')
        target = self.root / 'existing'
        target.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            attachments.extract(self.root / 'attached', sha256=self.pin, output=target)
        self.assertEqual(target.read_bytes(), b'keep')
        self.assertEqual(before, self.snapshot(self.body))

    def test_contract_tampering_even_with_rebuilt_body_manifest(self):
        self.add()
        body = self.root / 'attached'
        index = body / 'ATTACHMENTS.json'
        original = json.loads(index.read_text())
        mutations = []
        for field, value in [('path', '../escape'), ('bytes', True), ('media_type', 'bad'),
                             ('sha256', 'f' * 64)]:
            obj = json.loads(json.dumps(original))
            obj['attachments'][0][field] = value
            mutations.append(obj)
        mutations.extend([{'schema': 'mantle.attachments/999', 'attachments': []},
                          {**original, 'attachments': original['attachments'] * 2}])
        for obj in mutations:
            index.write_text(json.dumps(obj))
            cartridge.write_manifest(body)
            with self.assertRaises(ValueError):
                cartridge.verify(body)
        index.write_text(json.dumps(original))
        (body / original['attachments'][0]['path']).write_bytes(b'X' * len(self.data))
        cartridge.write_manifest(body)
        with self.assertRaises(ValueError):
            cartridge.verify(body)

    def test_incomplete_transaction_and_failed_publication(self):
        before = self.snapshot(self.body)
        from mantleos.transactions import journal_path
        journal_path(self.body).write_text('{}')
        with self.assertRaises(ValueError):
            self.add()
        journal_path(self.body).unlink()
        with patch.object(compiled, 'compile_body', side_effect=ValueError('injected failure')):
            with self.assertRaises(ValueError):
                self.add()
        self.assertFalse((self.root / 'attached').exists())
        self.assertFalse(list(self.root.glob('.attachment-*')))
        self.assertEqual(before, self.snapshot(self.body))

    def test_cli(self):
        from mantleos.console import main
        self.assertEqual(main(['--body', str(self.body), 'attachment', 'inspect']), 0)


if __name__ == '__main__':
    unittest.main()
