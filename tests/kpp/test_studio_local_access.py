"""Run the dependency-free browser-session boundary tests when Node is present."""
from pathlib import Path
import shutil
import subprocess
import unittest

from mantleos import studio


class StudioLocalAccessTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is not installed; browser-session tests untested')
    def test_local_session_boundaries(self):
        specimen = Path(studio.__file__).parent / 'kpp/resources/examples/anchor-studio'
        result = subprocess.run([shutil.which('node'), '--test', '--test-reporter=tap', str(specimen / 'local-access.test.cjs')],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('# tests 9', result.stdout)
