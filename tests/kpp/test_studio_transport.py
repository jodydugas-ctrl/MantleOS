"""The foreground host transport carries exact data and never retries effects."""
from pathlib import Path
import shutil
import subprocess
import unittest

from mantleos import studio


class StudioTransportTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node unavailable; transport runtime untested')
    def test_transport_protocol(self):
        specimen = Path(studio.__file__).parent/'kpp/resources/examples/anchor-studio/json-worker.test.cjs'
        events=specimen.with_name('committed-events.test.cjs')
        result = subprocess.run([shutil.which('node'), '--test', str(specimen),str(events)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
