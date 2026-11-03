"""Executable IF semantics; native Node-RED qualification is a separate probe."""
from pathlib import Path
import shutil
import subprocess
import unittest
from mantleos import studio


class StudioConditionsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node unavailable; IF JavaScript tests untested')
    def test_strict_if_semantics(self):
        root=Path(studio.__file__).parent/'kpp/resources/examples/anchor-studio'
        result=subprocess.run([shutil.which('node'),'--test','--test-reporter=tap',str(root/'conditions.test.cjs')],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('# tests 10',result.stdout)
