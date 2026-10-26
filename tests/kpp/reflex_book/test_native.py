from mantleos.reflex_book.fixtures import root as fixture_root
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mantleos import organism, cartridge, chromamem, compiled
from mantleos.reflex_book.carriers import native
from mantleos.reflex_book.errors import ReflexError

ROOT = fixture_root()
PIN = 'fd1edf144fed8b097f5a63b17415e33361bd8a3b0023f57295cf44165e13f207'


class NativeTests(unittest.TestCase):
    def test_native_roundtrips_do_not_compile_execute_or_admit_reflex(self):
        envelope = (ROOT / 'examples/reflex_book/m4_location.rfc').read_bytes()
        pin = hashlib.sha256(envelope).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body, attached = root / 'body', root / 'attached'
            organism.create(body, identity='reflex-native')
            with patch('mantleos.reflex_book.compiler.compile_ir', side_effect=AssertionError('REFLEX compiler called')), \
                 patch('mantleos.reflex_book.vm.run', side_effect=AssertionError('REFLEX VM called')), \
                 patch('mantleos.reflex_book.registry.ExperimentalRegistry.install', side_effect=AssertionError('REFLEX install called')):
                report = native.attach(body, envelope, expected_program_sha256=PIN, output=attached)
                self.assertFalse(report['authorized'])
                self.assertNotEqual(pin, PIN)
                with self.assertRaises(ReflexError):
                    native.attach(body, envelope, expected_program_sha256='0' * 64, output=root / 'bad')
                self.assertFalse((root / 'bad').exists())
                for kind in ('cartridge', 'chroma'):
                    archive, restored = root / (kind + ('.png' if kind == 'chroma' else '.vcw')), root / kind
                    if kind == 'cartridge':
                        cartridge.pack(attached, archive)
                        cartridge.unpack(archive, restored)
                    else:
                        chromamem.export_body(attached, archive)
                        chromamem.extract_body(archive, restored)
                    compiled.load(restored)
                    out = root / (kind + '.rfc')
                    with self.assertRaises(ReflexError):
                        native.extract(restored, attachment_sha256=pin,
                                       expected_program_sha256='0' * 64, output=out)
                    self.assertFalse(out.exists())
                    report = native.extract(restored, attachment_sha256=pin,
                                            expected_program_sha256=PIN, output=out)
                    self.assertEqual(out.read_bytes(), envelope)
                    self.assertFalse(report['executed'])
                    self.assertFalse(report['installed'])
                    self.assertFalse(report['authorized'])
