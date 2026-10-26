from mantleos.reflex_book.fixtures import root as fixture_root
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mantleos.reflex_book import cli

FIX = fixture_root() / 'examples/reflex_book'


class ArtifactPublicationTests(unittest.TestCase):
    def test_compile_preserves_existing_source_and_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.json'
            original = (FIX/'counter_rule.json').read_bytes()
            source.write_bytes(original)
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(['compile', str(source), '--output', str(source)]), 2)
                self.assertEqual(source.read_bytes(), original)
                executable = Path(tmp) / 'program.rfx'
                self.assertEqual(cli.main(['compile', str(source), '--output', str(executable)]), 0)
                before = executable.read_bytes()
                self.assertEqual(cli.main(['compile', str(source), '--output', str(executable)]), 2)
                self.assertEqual(executable.read_bytes(), before)
            self.assertFalse(list(Path(tmp).glob('.reflex-*')))

    def test_failed_write_never_publishes_partial_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'candidate.json'
            with patch.object(cli.os, 'fsync', side_effect=OSError('injected flush failure')):
                with self.assertRaises(OSError):
                    cli._write_new(target, b'complete candidate')
            self.assertFalse(target.exists())
            self.assertFalse(list(Path(tmp).iterdir()))
