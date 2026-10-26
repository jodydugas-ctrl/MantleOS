from mantleos.reflex_book.fixtures import root as fixture_root
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from mantleos.reflex_book.canonical import loads, dumps
from mantleos.reflex_book.errors import ReflexError

ROOT = fixture_root()


@unittest.skipUnless(shutil.which('node'), 'optional Node canonicalization probe unavailable')
class CrossRuntimeTests(unittest.TestCase):
    def test_independent_node_canonicalization(self):
        vectors = json.loads((ROOT/'examples/reflex_book/cross_runtime_vectors.json').read_text('utf-8'))
        for vector in vectors:
            if vector.get('refuse'):
                with self.assertRaises(ReflexError):
                    loads(vector['source'])
            else:
                self.assertEqual(dumps(loads(vector['source'])).decode('utf-8'), vector['expected'])
        result = subprocess.run([shutil.which('node'),
                                 str(Path(__import__('mantleos.reflex_book', fromlist=['']).__file__).parent/'tools/canonical_probe.cjs'),
                                 str(ROOT/'examples/reflex_book/cross_runtime_vectors.json')],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['result'], 'PASS')
