import tempfile
import unittest
from pathlib import Path
from mantleos import studio, studio_demo as d


class StudioDemoTests(unittest.TestCase):
    def test_regression_repair_and_separate_baker(self):
        with tempfile.TemporaryDirectory() as td:
            nest=Path(td)/'nest';studio.initialize_heart(nest,b'Synthetic founding')
            studio.project_set(nest,d.project(),None)
            r=d.qualify(nest)
            self.assertEqual([s['all_passed'] for s in r['stages']],[True,True,True,False,True])
            self.assertEqual(r['acceptance'],'PENDING_BAKER')
            with self.assertRaises(PermissionError):d.accept(nest,baker='Synthetic Baker')
            receipt=d.accept(nest,baker='Synthetic Baker',confirmed=True)
            self.assertEqual(receipt['required_anchors'],4)

    def test_imported_fixture_never_executes(self):
        with tempfile.TemporaryDirectory() as td:
            nest=Path(td)/'nest';studio.initialize_heart(nest,b'Synthetic founding')
            value=d.project();value['provenance']=[]
            studio.project_set(nest,value,None)
            with self.assertRaises(ValueError):d.qualify(nest)
