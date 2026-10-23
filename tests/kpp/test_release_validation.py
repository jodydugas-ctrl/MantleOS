"""No actual browser is implied by these helper unit tests."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
SPEC=importlib.util.spec_from_file_location('kpp_validate_release',ROOT/'tools/validate_release.py')
M=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ReleaseValidationTests(unittest.TestCase):
    def test_pass_all_local_does_not_accept_one_zero_or_claim_sandbox(self):
        checks={name:{'status':'PASS'} for name in ('unittests','doctor','task_agent_smoke','release_inventory')}
        result=M.assess(checks)
        self.assertEqual(result['local_functional_checks'],'PASS')
        self.assertEqual(result['baker_acceptance'],'NOT_GRANTED')
        self.assertEqual(result['browser_notepad'],'NOT_RUN')

    def test_missing_or_failed_required_local_check_keeps_gate_open(self):
        self.assertEqual(M.assess({})['local_functional_checks'],'OPEN')
        checks={name:{'status':'PASS'} for name in ('unittests','doctor','task_agent_smoke','release_inventory')}
        checks['doctor']={'status':'FAIL'}
        self.assertEqual(M.assess(checks)['local_functional_checks'],'OPEN')

    def test_browser_observation_never_supplies_acceptance(self):
        result=M.assess({'browser_preview':{'status':'PASS'}})
        self.assertEqual(result['browser_notepad'],'PASS')
        self.assertEqual(result['baker_acceptance'],'NOT_GRANTED')
        self.assertEqual(result['local_functional_checks'],'OPEN')

    def test_subprocess_check_captures_actual_fail_and_counts(self):
        passed=M.command_check('sample',[sys.executable,'-c',"import sys;sys.stderr.write('Ran 12 tests in 0.1s\\nOK\\n')"])
        self.assertEqual(passed['status'],'PASS');self.assertEqual(passed['tests_run'],12)
        bad=M.command_check('sample',[sys.executable,'-c','raise SystemExit(8)'])
        self.assertEqual(bad['status'],'FAIL');self.assertEqual(bad['exit_code'],8)
        missing=M.command_check('sample',['/nonexistent/kpp-absent-python'])
        self.assertEqual(missing['status'],'BLOCKED')

    def test_report_cannot_be_written_within_release(self):
        import argparse
        with self.assertRaisesRegex(ValueError,'OUTSIDE'):
            M.validate(argparse.Namespace(json_out=ROOT/'checked.json',python=sys.executable,
                       browser=False,chromium=None))

    def test_browser_admin_block_is_separately_classified(self):
        from subprocess import CompletedProcess
        with patch.object(M.subprocess,'run',return_value=CompletedProcess([],1,'{"result": "BLOCKED"}','')):
            found=M.command_check('browser',['fake'])
        self.assertEqual(found['status'],'BLOCKED')

if __name__=='__main__':unittest.main()
