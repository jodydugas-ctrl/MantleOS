"""Newly executed integration checks, not inherited patch test receipts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from mantleos import kernel
from mantleos.scan import discovery as d
from mantleos.scan.common import ScanError, digest, sha


class ParallelDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / 'specimen'
        self.gui = self.source / 'ui'
        self.gui.mkdir(parents=True)
        (self.source / 'main.cpp').write_text('int main() { return 0; }\n', encoding='utf-8')
        (self.source / 'helpers.py').write_text('raise RuntimeError("NEVER EXECUTE")\ndef operate():\n    return True\n', encoding='utf-8')
        (self.gui / 'Main.ui').write_text('<ui><widget class="QMainWindow" name="Main"><action name="save"><property name="text"><string>Save</string></property></action><addaction name="save"/></widget><connections><connection><sender>save</sender><signal>triggered()</signal><receiver>Main</receiver><slot>save()</slot></connection></connections><tabstops><tabstop>Main</tabstop></tabstops></ui>', encoding='utf-8')
        self.output = self.base / 'discovery'

    def collect(self, **options):
        return d.collect(self.source, self.base / 'worker', 'synthetic-pinned-source', gui_root=self.gui, **options)

    def discover(self, **options):
        return d.discover(self.source, self.output, 'synthetic-pinned-source', gui_root=self.gui, **options)

    def test_bundle_hashes_and_native_report_remain_usable(self):
        report = self.discover()
        self.assertEqual(set(p.name for p in self.output.iterdir()), {'code-scan.json','gui-inventory.json','discovery.json'})
        for name, pins in report['artifacts'].items():
            data = (self.output / name).read_bytes()
            self.assertEqual(sha(data), pins['sha256'])
            self.assertEqual(digest(json.loads(data)), pins['canonical_sha256'])
        self.assertEqual(json.loads((self.output / 'discovery.json').read_text()), report)
        self.assertEqual(report['cross_links']['interface_files'], ['ui/Main.ui'])
        code = json.loads((self.output / 'code-scan.json').read_text())
        from mantleos.scan.scanner import verify_report
        verify_report(code)
        self.assertFalse(code['graph']['scope']['specimen_executed'])
        cpp = next(f for f in code['graph']['files'] if f['path'] == 'main.cpp')
        self.assertEqual(cpp['status'], 'UNSUPPORTED')
        self.assertTrue(any(n['name'] == 'operate' for n in code['graph']['nodes']))
        gui = json.loads((self.output / 'gui-inventory.json').read_text())
        self.assertEqual({e['kind'] for e in gui['entries']}, {'widget','action','action-placement','connection','tab-order'})
        self.assertTrue(all(not e['anchor_ids'] for e in gui['entries']))

    def test_barrier_proves_captured_file_extraction_overlap(self):
        from mantleos.scan import scanner as native
        barrier = Barrier(2, timeout=5)
        original = native.extract
        def worker(path, *args, **kwargs):
            if path in ('helpers.py', 'ui/Main.ui'):
                barrier.wait()
            return original(path, *args, **kwargs)
        with patch.object(native, 'extract', side_effect=worker):
            self.assertTrue(self.discover()['cross_links']['reference_snapshot_consistent'])

    def test_serial_and_parallel_evidence_equal(self):
        serial = self.collect(execution='serial')
        parallel = self.collect()
        self.assertEqual(serial['code']['graph'], parallel['code']['graph'])
        self.assertEqual(serial['gui'], parallel['gui'])
        self.assertEqual(serial['report']['source'], parallel['report']['source'])

    def test_source_mutation_fails_without_publication(self):
        gui = d.interface_inventory
        def change(*args, **kwargs):
            result = gui(*args, **kwargs)
            (self.source / 'main.cpp').write_text('CHANGED', encoding='utf-8')
            return result
        with patch.object(d, 'interface_inventory', side_effect=change):
            with self.assertRaises(ScanError):
                self.discover()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.base.glob('.discovery-*')))

    def test_worker_failures_publish_nothing(self):
        for worker in ('scan','interface_inventory'):
            with self.subTest(worker=worker), patch.object(d, worker, side_effect=ValueError('synthetic failure')):
                with self.assertRaisesRegex(ScanError, 'no merged evidence'):
                    self.discover()
                self.assertFalse(self.output.exists())

    def test_omitted_or_unpinned_reads_rejected(self):
        code, gui = d.scan, d.interface_inventory
        def code_lies(*args, **kwargs):
            result = code(*args, **kwargs)
            result['graph']['files'].pop()
            result['graph_digest'] = digest(result['graph'])
            return result
        def gui_lies(*args, **kwargs):
            result = gui(*args, **kwargs)
            result['source']['files']['Other.ui'] = '0' * 64
            return result
        for worker, fake in (('scan',code_lies),('interface_inventory',gui_lies)):
            with self.subTest(worker=worker), patch.object(d, worker, side_effect=fake):
                with self.assertRaisesRegex(ScanError, 'unpinned'):
                    self.discover()
                self.assertFalse(self.output.exists())

    def test_missing_or_unsupported_gui_is_explicit(self):
        (self.gui / 'Main.ui').unlink()
        with self.assertRaisesRegex(ScanError, 'No .ui'):
            self.discover()
        self.assertFalse(self.output.exists())

    def test_malformed_xml_and_encoded_entity_refused(self):
        for data in (b'<ui><widget>', '<!DOCTYPE ui [<!ENTITY x "unsafe">]><ui><widget name="x"/></ui>'.encode('utf-16')):
            (self.gui / 'Main.ui').write_bytes(data)
            with self.assertRaises(ScanError):
                self.discover()
            self.assertFalse(self.output.exists())

    def test_budgets_fail_before_workers(self):
        for options in ({'max_files':1},{'max_bytes':1},{'max_file_bytes':1},{'max_files':1001},{'max_seconds':True},{'execution':'swarm'}):
            with self.subTest(options=options), patch.object(d, 'scan') as worker:
                with self.assertRaises(ScanError):
                    self.discover(**options)
                worker.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_traversal_is_bounded_before_sorting(self):
        with patch.object(d, 'MAX_TRAVERSAL', 1), patch.object(d, 'scan') as worker:
            with self.assertRaisesRegex(ScanError, 'traversal budget'):
                self.discover()
            worker.assert_not_called()

    def test_source_and_output_containment(self):
        with self.assertRaisesRegex(ScanError, 'outside'):
            d.discover(self.source, self.source / 'output', 'test')
        with self.assertRaisesRegex(ScanError, 'same source'):
            d.discover(self.source, self.output, 'test', gui_root=self.base)
        self.output.mkdir()
        sentinel = self.output / 'keep'; sentinel.write_text('keep')
        with self.assertRaisesRegex(ScanError, 'new directory'):
            self.discover()
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_publication_failure_leaves_no_bundle(self):
        original = d.write_json
        def interrupted(path, value):
            if Path(path).name == 'discovery.json':
                raise OSError('simulated interruption')
            original(path, value)
        with patch.object(d, 'write_json', side_effect=interrupted):
            with self.assertRaises(OSError):
                self.discover()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.base.glob('.discovery-*')))

    def test_symlinks_or_windows_junctions_refused(self):
        link = self.source / 'redirect'
        try:
            link.symlink_to(self.gui, target_is_directory=True)
        except OSError:
            if os.name != 'nt':
                self.skipTest('Directory links unavailable')
            result = subprocess.run(['cmd','/c','mklink','/J',str(link),str(self.gui)], capture_output=True)
            if result.returncode:
                self.skipTest('Directory links unavailable')
        def remove_link():
            if link.is_symlink():
                link.unlink()
            elif link.exists():
                os.rmdir(link)
        self.addCleanup(remove_link)
        with self.assertRaisesRegex(ScanError, 'symlinks and reparse'):
            self.discover()

    def test_checked_authority_and_cli(self):
        args = {'source':str(self.source),'output':str(self.output),'identity':'test','gui_root':str(self.gui)}
        with self.assertRaises(PermissionError):
            kernel.scan('scan.discover', args)
        self.assertFalse(self.output.exists())
        result = subprocess.run([sys.executable,'-S','-m','mantleos','scan','discover',str(self.source),
                                 '--gui-root',str(self.gui),'--identity','test','--output',str(self.output)],
                                capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['execution'], 'parallel-read-only')


if __name__ == '__main__':
    unittest.main()
