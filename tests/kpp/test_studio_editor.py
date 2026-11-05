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

    @unittest.skipUnless(shutil.which('node'), 'Node unavailable; editor host protocols untested')
    def test_shared_host_protocols(self):
        root = Path(studio.__file__).parent/'kpp/resources/examples/anchor-studio'
        names = ('editor-catalog.test.cjs', 'editor-installation.test.cjs',
                 'editor-local-context.test.cjs', 'editor-sockets.test.cjs',
                 'workflow-checksum.test.cjs', 'resident-view.test.cjs',
                 'community-editor.test.cjs', 'editor-executions.test.cjs', 'manual-node-red.test.cjs')
        result = subprocess.run([shutil.which('node'), '--test', *(str(root/name) for name in names)],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        # The HTTP integration case explicitly reports an internal skip unless
        # the host supplies STUDIO_MODULES. This wrapper is not browser evidence.


if __name__ == '__main__':
    unittest.main()
