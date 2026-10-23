import tempfile
import unittest
from pathlib import Path
from mantleos.kpp.core import KPPError
from mantleos.kpp.ingest import catalog_source

class Ingest(unittest.TestCase):
    def test_cataloging_does_not_execute_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            src=root/'danger';src.mkdir()
            (src/'unexpected.py').write_text("raise Exception('must never run!')\n")
            out=root/'manifest.json'
            obj=catalog_source(src,'external-prototype',out)
            self.assertTrue(out.is_file())
            self.assertEqual(obj['status'],'reference')
            self.assertEqual(obj['source']['scanned_files'],1)
            with self.assertRaises(KPPError):catalog_source(src,'external-prototype',out)
