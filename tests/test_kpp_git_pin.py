"""A clean commit identity and shared bytes must both match the selected KPP."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import verify_kpp_pin as pins
from project_files import ProjectError


class GitPinTests(unittest.TestCase):
    def record(self,**changes):
        value={'official_url':'https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol',
               'dirty':False,'base_commit':'a'*40}
        value.update(changes)
        return {'upstream':value}

    def test_requires_exact_clean_official_commit(self):
        for changes in ({'dirty':True},{'base_commit':'main'},{'base_commit':None},
                        {'official_url':'https://github.com/other/project'}):
            with self.subTest(changes=changes),patch.object(pins,'read_json',return_value=self.record(**changes)):
                with self.assertRaises(ProjectError):pins.pin('.')
        with patch.object(pins,'read_json',return_value=self.record()):self.assertEqual(pins.pin('.'),'a'*40)

    def test_wrong_checkout_revision_refused_before_reading_source(self):
        result=type('Result',(),{'stdout':'b'*40})()
        with patch.object(pins,'pin',return_value='a'*40),patch.object(pins,'check'), \
             patch.object(pins.subprocess,'run',return_value=result):
            with self.assertRaisesRegex(ProjectError,'checkout differs'):pins.verify('.', '.')


if __name__=='__main__':unittest.main()
