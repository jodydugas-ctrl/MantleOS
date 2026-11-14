"""Transport, cold receiving, source preservation and language bridge checks."""
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import unittest
from mantleos import anchor_handoff as h
from mantleos.anchor_handoff_build import build
from mantleos.kpp.anchor import bridge_python


class HandoffTests(unittest.TestCase):
    def test_exact_roundtrip_including_embedded_markers(self):
        files = {'nested/source.py': b'print("hello")\r\n', 'notes.md': 'é🐦\n```\n<!-- END ANCHOR FILE -->'.encode()}
        self.assertEqual(h.unpack(h.pack(files))[1], files)

    def test_windows_relative_path_and_exact_source_fingerprints(self):
        source = PureWindowsPath(r'nested\module.py')
        files = {source.as_posix(): b'print("hello")\r\n'}
        packed = h.pack(files)
        self.assertEqual(h.unpack(packed)[1], {'nested/module.py': b'print("hello")\r\n'})
        self.assertEqual(packed, h.pack({'nested/module.py': files[source.as_posix()]}))
        self.assertNotEqual(packed, h.pack({'nested/module.py': b'print("hello")\n'}))
        with self.assertRaises(ValueError):
            h.pack({str(source): files[source.as_posix()]})

    def test_rejects_corruption_truncation_trailing_bytes(self):
        raw = h.pack({'a.txt': b'hello'})
        for broken in (raw.replace(b'hello', b'jello'), raw[:-1], raw + b'x'):
            with self.subTest(broken=broken[-30:]), self.assertRaises(ValueError):
                h.unpack(broken)

    def test_rejects_unsafe_and_colliding_paths(self):
        for name in ('../x', '/tmp/x', 'a/../x', 'a\\x', 'CON.txt', 'x.', 'a//b', 'a:b', '.'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                h.pack({name: b'x'})
        for files in ({'a': b'', 'a/b': b''}, {'a': b'', 'A': b''}):
            with self.assertRaises(ValueError): h.pack(files)

    def test_invalid_manifest_duplicates_and_lengths(self):
        raw = h.pack({'a': b'x'})
        for old, new in ((b'"bytes":1', b'"bytes":true'),
                         (b'"schema":"anchor.handoff/1"', b'"schema":"anchor.handoff/2"'),
                         (b'"authority":"NONE"', b'"authority":"NONE","authority":"NONE"')):
            with self.assertRaises(ValueError): h.unpack(raw.replace(old, new))

    def test_extract_validates_before_writing_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'file.md'; source.write_bytes(h.pack({'x': b'one'}))
            h.extract(source, root/'received')
            (root/'received/x').write_bytes(b'personal')
            with self.assertRaises(FileExistsError): h.extract(source, root/'received')
            self.assertEqual((root/'received/x').read_bytes(), b'personal')
            source.write_bytes(source.read_bytes()[:-1])
            with self.assertRaises(ValueError): h.extract(source, root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_repack_edits_and_parent_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d); raw = h.pack({'a.txt': b'before'})
            (r/'old.md').write_bytes(raw); h.extract(r/'old.md', r/'edit')
            (r/'edit/a.txt').write_bytes(b'after')
            h.repack(r/'old.md', r/'edit', r/'new.md')
            m, f = h.read(r/'new.md')
            self.assertEqual(f['a.txt'], b'after')
            self.assertEqual(m['metadata']['parent_handoff_sha256'], hashlib.sha256(raw).hexdigest())
            with self.assertRaises(FileExistsError): h.repack(r/'old.md', r/'edit', r/'new.md')

    def test_supplied_reference_and_implementation_conformance(self):
        from mantleos.anchor_handoff_build import ROOT
        folder = ROOT/'kpp/resources/examples/notepad-fidelity9'
        run = subprocess.run([sys.executable, '-m', 'unittest', 'test_logical_next',
                              'test_notepad_logical_contract', '-q'], cwd=folder,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_cold_receiver_and_kpp_bridge(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); raw = build(); (root/'handoff.md').write_bytes(raw)
            _, files = h.unpack(raw)
            self.assertFalse(any('blind_private' in n or 'private-key' in n for n in files))
            (root/'receiver.anchor').write_bytes(files['receiver.anchor'])
            bridge_python(root/'receiver.anchor', root/'receiver.py')
            self.assertEqual((root/'receiver.py').read_bytes(), files['receiver.py'])
            result = subprocess.run([sys.executable, '-I', '-S', str(root/'receiver.py'), 'extract', str(root/'handoff.md'), '--directory', str(root/'received')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            imported = root/'received/notepad'; manifest = json.loads((imported/'IMPORT-PROVENANCE.json').read_text())
            for name, pin in manifest['files'].items():
                self.assertEqual(hashlib.sha256((imported/name).read_bytes()).hexdigest(), pin, name)
            commands = '\n'.join(json.dumps(v) for v in [
                {'action':'insert','payload':{'offset':0,'text':'🐦é'}},
                {'action':'select-all','payload':None}, {'action':'undo','payload':None},
                {'action':'insert','payload':{'offset':True,'text':'bad'}}])+'\n'
            python = subprocess.run([sys.executable, str(imported/'bridge.py')], input=commands, capture_output=True, text=True, env={**{k:v for k,v in os.environ.items() if k!='PYTHONPATH'}, 'PYTHONIOENCODING':'cp1252'})
            self.assertEqual(python.returncode, 0, python.stderr)
            self.assertTrue(python.stdout.isascii())
            answers = [json.loads(l) for l in python.stdout.splitlines()]
            self.assertEqual(answers[1]['result']['selection'], [0,2])
            self.assertEqual(answers[2]['state']['text'], '')
            self.assertEqual(answers[3]['outcome'], 'REJECTED_BY_GATE')
            if shutil.which('node'):
                js = subprocess.run(['node', str(imported/'bridge-client.js')], input=commands, capture_output=True, text=True, env={**os.environ, 'PYTHON':sys.executable, 'PYTHONIOENCODING':'cp1252'})
                self.assertEqual(js.returncode, 0, js.stderr)
                self.assertEqual(js.stdout, python.stdout)


if __name__ == '__main__': unittest.main()
