"""Optional editor admission is source integrity, never execution permission."""
from pathlib import Path
import shutil
import subprocess
import unittest

from mantleos import studio


class StudioEditorTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node unavailable; editor snapshot untested')
    def test_source_snapshot(self):
        specimen = Path(studio.__file__).parent/'kpp/resources/examples/anchor-studio/editor-assets.test.cjs'
        result = subprocess.run([shutil.which('node'), '--test', str(specimen)],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
