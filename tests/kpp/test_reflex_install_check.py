"""Failures in release tooling must never produce a successful installation receipt."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from mantleos.kpp import core

TOOL = Path(core.__file__).parent / 'resources/tools/check_reflex_install.py'
SPEC = importlib.util.spec_from_file_location('installed_reflex_check', TOOL)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class InstalledCheckTests(unittest.TestCase):
    def setUp(self):
        # Simulate an external developer-tool location. Test hosts may place
        # their synthetic TEMP directory inside a different source checkout.
        roots = patch.object(CHECK, 'checkout_roots', return_value=[])
        roots.start(); self.addCleanup(roots.stop)

    def test_output_inside_source_is_refused_before_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); wheel = root / 'example.whl'; wheel.write_bytes(b'fixture')
            with patch.object(CHECK, 'checkout_roots', return_value=[root]):
                with self.assertRaisesRegex(ValueError, 'OUTSIDE'):
                    CHECK.check(wheel, root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); wheel = root / 'example.whl'; wheel.write_bytes(b'fixture')
            output = root / 'existing'; output.mkdir(); (output / 'marker').write_bytes(b'keep')
            with self.assertRaises(FileExistsError):
                CHECK.check(wheel, output)
            self.assertEqual((output / 'marker').read_bytes(), b'keep')
            self.assertEqual({p.name for p in output.iterdir()}, {'marker'})

    def test_failed_environment_creation_leaves_fail_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); wheel = root / 'example.whl'; wheel.write_bytes(b'fixture')
            with patch.object(CHECK.venv.EnvBuilder, 'create', side_effect=OSError('injected')):
                with self.assertRaises(OSError):
                    CHECK.check(wheel, root / 'output')
            report = json.loads((root / 'output/report.json').read_text('utf-8'))
            self.assertEqual(report['result'], 'FAIL')
            self.assertIn('injected', report['error'])

    def test_wrong_bootstrap_digest_never_creates_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); wheel = root / 'example.whl'; wheel.write_bytes(b'fixture')
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                CHECK.check(wheel, root / 'output', pip_wheel=wheel, pip_sha256='0' * 64)
            self.assertFalse((root / 'output').exists())

    def test_even_a_pinned_bootstrap_cannot_escape_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); wheel = root / 'example.whl'; wheel.write_bytes(b'fixture')
            bootstrap = root / 'pip.whl'
            with zipfile.ZipFile(bootstrap, 'w') as archive:
                archive.writestr('pip/../../escaped.txt', b'escape')
            output = root / 'output'; destination = output / 'venv/lib/site-packages'
            completed = subprocess.CompletedProcess([], 0, json.dumps(str(destination)), '')
            with patch.object(CHECK.venv.EnvBuilder, 'create'), \
                    patch.object(CHECK.subprocess, 'run', return_value=completed) as run:
                with self.assertRaisesRegex(ValueError, 'Unsafe pip'):
                    CHECK.check(wheel, output, pip_wheel=bootstrap,
                                pip_sha256=hashlib.sha256(bootstrap.read_bytes()).hexdigest())
                self.assertFalse(any('install' in call.args[0] for call in run.call_args_list))
            self.assertFalse((root / 'escaped.txt').exists())
            self.assertEqual(json.loads((output / 'report.json').read_text())['result'], 'FAIL')
