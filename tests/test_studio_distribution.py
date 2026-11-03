"""Public project format is distributable; private carriers remain excluded."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import project_files


class StudioDistributionTests(unittest.TestCase):
    def test_public_project_extension_and_private_exclusions(self):
        self.assertTrue(project_files.allowed('src/mantleos/kpp/resources/examples/anchor-studio/Anchor-Studio-Demo.anchorstudio'))
        self.assertFalse(project_files.allowed('docs/private.engram'))
        self.assertFalse(project_files.allowed('docs/credentials.json'))
