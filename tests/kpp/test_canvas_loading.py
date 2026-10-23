"""Shared Canvas loading retains source checks, exact targets and host boundaries."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mantleos import anchor_apps, anchor_app_document as document, anchor_language
from mantleos.app_bridges import canvas_bridge, default_registry


def repack(source, section, replacement):
    """Change a declared target and its digest: integrity alone is insufficient."""
    parsed = document.parse(source)
    contract = parsed['contract']
    old_line = json.dumps(contract, sort_keys=True, separators=(',', ':'))
    contract[section + '_bytes'] = len(replacement.encode('utf-8'))
    contract[section + '_sha256'] = hashlib.sha256(replacement.encode('utf-8')).hexdigest()
    return source.replace(old_line, json.dumps(contract, sort_keys=True, separators=(',', ':')), 1).replace(
        parsed[section], replacement, 1)


class CanvasLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = anchor_apps.notepad_source()

    def test_launch_and_command_keep_exact_browser_and_native_behavior(self):
        expected = document.parse(self.source)['canvas']
        self.assertEqual(anchor_apps.browser_html(self.source), expected)
        result = anchor_language.execute_blueprint(self.source)
        self.assertEqual(result['stdout'], expected)
        self.assertEqual(result['effect_claim'], 'NONE')
        self.assertEqual(result['canvas_status'], 'HOST_LAUNCH_REQUIRED')
        command = anchor_language.execute_blueprint(self.source, {'op': 'INSERT', 'text': 'Synthetic'})
        self.assertEqual(command['result']['state']['text'], 'Synthetic')
        self.assertEqual(command['effect_claim'], 'NONE')

    def test_rehashed_changed_targets_are_refused_before_launch(self):
        parts = document.parse(self.source)
        for section in ('canvas', 'python', 'bridge'):
            changed = repack(self.source, section, parts[section] + '\n# Changed target')
            for launch in (anchor_apps.browser_html, anchor_language.execute_blueprint):
                with self.subTest(section=section, launch=launch.__name__), self.assertRaises(ValueError):
                    launch(changed)

    def test_source_pins_are_reread_after_successful_launch(self):
        anchor_apps.browser_html(self.source)
        original = anchor_language.source_directory()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            catalog = json.loads((original / 'SOURCE-PINS.json').read_text('utf-8'))
            for relative in catalog['pins']:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((original / relative).read_bytes())
            (root / 'SOURCE-PINS.json').write_text(json.dumps(catalog), encoding='utf-8')
            with patch.object(anchor_language, 'source_directory', return_value=root):
                self.assertEqual(anchor_apps.browser_html(self.source), document.parse(self.source)['canvas'])
                path.write_bytes(path.read_bytes() + b'\n# Modified after successful load\n')
                for launch in (anchor_apps.browser_html, anchor_language.execute_blueprint):
                    with self.subTest(launch=launch.__name__), self.assertRaisesRegex(ValueError, 'Pinned Anchor source changed'):
                        launch(self.source)

    def test_canvas_delivery_requires_actual_matching_host_acknowledgement(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            observed = []
            def host(packet):
                observed.append(packet)
                return {key: packet[key] for key in ('app_id', 'revision', 'snapshot_sha256', 'html_sha256')} | {
                    'schema': 'mantle.canvas-receipt/1', 'status': 'APPLIED'}
            registry = default_registry(root / 'body', canvas=canvas_bridge(host))
            receipt = anchor_apps.deliver(self.source, root / 'app', body=root / 'body',
                                         registry=registry, broker=lambda *_: True)
            self.assertEqual(receipt['preview_status'], 'HOST_ACKNOWLEDGED')
            self.assertEqual(len(observed), 1)
            self.assertIn('sandbox="allow-scripts allow-downloads"', observed[0]['snapshot']['shell'])
            self.assertEqual(observed[0]['snapshot']['phase'], 'COMPLETE')
            bad_registry = default_registry(root / 'body', canvas=canvas_bridge(lambda _: {'status': 'APPLIED'}))
            with self.assertRaisesRegex(ValueError, 'acknowledgement'):
                anchor_apps.deliver(self.source, root / 'bad', body=root / 'body',
                                    registry=bad_registry, broker=lambda *_: True)


if __name__ == '__main__':
    unittest.main()
