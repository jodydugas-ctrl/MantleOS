"""Local process-death evidence for the experimental registry, not Body recovery."""
from pathlib import Path
from contextlib import closing
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from mantleos.reflex_book.registry import ExperimentalRegistry
from .test_admission import package, KEYS, NOW, BASE1

CHILD = '''
import os,sys
from mantleos.reflex_book.registry import ExperimentalRegistry
registry=ExperimentalRegistry(sys.argv[1])
conn=registry._connect()
conn.execute('BEGIN IMMEDIATE')
registry._append(conn,'DISABLE',{'candidate_sha256':None,'at_utc':'2026-10-24T12:00:00Z'})
if sys.argv[2]=='after_commit':
    conn.commit()
os._exit(73)
'''


class CrashRecoveryTests(unittest.TestCase):
    def test_process_death_before_and_after_commit_in_delete_and_wal_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ('DELETE', 'WAL'):
                for phase in ('before_commit', 'after_commit'):
                    with self.subTest(mode=mode, phase=phase):
                        path = Path(tmp) / (mode + '-' + phase + '.sqlite')
                        registry = ExperimentalRegistry(path)
                        with closing(sqlite3.connect(path)) as conn:
                            actual = conn.execute('PRAGMA journal_mode=' + mode).fetchone()[0]
                            self.assertEqual(actual.lower(), mode.lower())
                        candidate, binary, evidence, receipt = package()
                        context = {'trusted_issuers': KEYS, 'now_utc': NOW, 'current_baselines': BASE1}
                        registry.install(candidate, binary, evidence, receipt, **context)
                        registry.activate(candidate['candidate_sha256'], **context)
                        before = registry.audit()
                        completed = subprocess.run([sys.executable, '-c', CHILD, str(path), phase],
                                                   capture_output=True, text=True, timeout=20)
                        self.assertEqual(completed.returncode, 73, completed.stderr)
                        recovered = ExperimentalRegistry(path).audit()
                        if phase == 'before_commit':
                            self.assertEqual(recovered, before)
                        else:
                            self.assertEqual(recovered['event_count'], before['event_count'] + 1)
                            self.assertIsNone(recovered['active_candidate_sha256'])
                        with closing(sqlite3.connect(path)) as conn:
                            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
