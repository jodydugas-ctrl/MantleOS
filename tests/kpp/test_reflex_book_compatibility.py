"""Published entry points retain one maintained interpreter and approval validator."""
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from mantleos import console
from mantleos.kpp import cli as kpp_cli
from mantleos.reflex_book import vm, admission
from mantleos.reflex import vm as legacy_vm, admission as legacy_admission
from mantleos.reflex_book.fixtures import root


class CompatibilityTests(unittest.TestCase):
    def test_legacy_imports_are_identical_module_objects(self):
        self.assertIs(legacy_vm, vm)
        self.assertIs(legacy_admission, admission)
        from mantleos.reflex.carriers import raw as legacy_raw
        from mantleos.reflex_book.carriers import raw
        self.assertIs(legacy_raw,raw)
        self.assertTrue(hasattr(legacy_vm,'run_prepared'))

    def test_both_public_dispatchers_use_the_maintained_cli(self):
        for entry in (lambda args:console.main(['reflex-book',*args]),
                      lambda args:kpp_cli.main(['reflex-book',*args])):
            with patch('mantleos.reflex_book.cli.main',return_value=0) as main:
                self.assertEqual(entry(['inspect','synthetic.json']),0)
                main.assert_called_once_with(['inspect','synthetic.json'])

    def test_published_module_command_remains_runnable(self):
        fixture=root()/'examples/reflex_book/location_rule.json'
        result=subprocess.run([sys.executable,'-m','mantleos.reflex.cli','validate',str(fixture)],
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'VALID')
