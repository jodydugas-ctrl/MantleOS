"""Current skills survive compatibility removal and resource deduplication."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

from mantleos import (anchor_app_bridge, anchor_apps, anchor_language, compiled,
                      engram, lifecycle, organism, specimens)
from mantleos.anchor_engine.tools.anchor_compile import translate
from mantleos.anchor_engine.tools.notepad_blueprint import generate


class StreamlinedTests(unittest.TestCase):
    def test_generated_anchor_and_browser_are_byte_identical_to_baseline(self):
        source = generate()
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),
                         'f8b42bc6b6fb73f2a30ecb410eeeb426f6e5da1f2e4e73509a3157330e761d69')
        html = anchor_apps.browser_html(anchor_apps.notepad_program())
        self.assertEqual(hashlib.sha256(html.encode()).hexdigest(),
                         'fd8482f86dccfb9889a44a14fd0e1fe11cb13ca3c74aee918f72134eed9f18f2')
        self.assertEqual(organism.notebook_tissue()['programs'][1]['payload'], source)
        self.assertEqual(anchor_language.verify_source_pins()['result'], 'PASS')

    def test_notepad_compilation_is_self_contained_after_deduplication(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'thought.py'
            target.write_text(translate(generate()), encoding='utf-8')
            commands = [{'op': 'INSERT', 'text': 'Alpha'},
                        {'op': 'REPLACE', 'find': 'alpha', 'with': 'Beta', 'all': True, 'match_case': False},
                        {'op': 'UNDO'}]
            result = subprocess.run([sys.executable, '-I', '-S', str(target)], cwd=td,
                                    input=''.join(json.dumps(c) + '\n' for c in commands),
                                    text=True, check=True, capture_output=True)
            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([r['state']['text'] for r in records], ['Alpha', 'Beta', 'Alpha'])
            self.assertTrue(all(r['effect_claim'] == 'NONE' for r in records))

    def test_new_app_cli_and_receiver_integrity(self):
        from mantleos.console import main
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'app.html'; thought = root / 'NewApp.anchor'
            source.write_text('<!doctype html><title>New app</title><button>Ready</button>', encoding='utf-8')
            arguments = ['anchor-code', 'emit', '--name', 'NewApp', '--input', str(source), '--output', str(thought)]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(arguments + ['--permit-effect']), 0)
            parsed, _ = anchor_app_bridge.load(thought.read_bytes())
            self.assertEqual(parsed['profile'], 'EMIT_TEXT/0.2')
            anchor_app_bridge.materialize(thought.read_bytes(), root / 'received.html')
            self.assertEqual((root / 'received.html').read_bytes(), source.read_bytes())
            with self.assertRaises(ValueError):
                anchor_app_bridge.materialize(thought.read_bytes().replace(b'<button>Ready', b'<button>Alter'), root / 'bad.html')
            self.assertFalse((root / 'bad.html').exists())

    def test_current_png_founding_import_keeps_persona_not_experience(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            parent = root / 'parent'
            specimens.fresh(parent, name='Synthetic founding persona')
            lifecycle.admit(parent, 'observation', {'private_history': 'parent-only'},
                            expected_head=engram.head(parent / 'ENGRAM.jsonl'))
            image = root / 'current.png'
            lifecycle.save(parent, image, format='chroma')
            founding = specimens.founding_material(image)
            child = root / 'fresh'
            specimens.fresh(child, founding=founding)
            self.assertEqual((child / 'PRIMER/PERSONA.md').read_bytes(), (parent / 'PRIMER/PERSONA.md').read_bytes())
            self.assertEqual(engram.read(child / 'ENGRAM.jsonl'), [])
            self.assertNotEqual(compiled.read_json(child / 'BIRTH.json')['id'], compiled.read_json(parent / 'BIRTH.json')['id'])
            self.assertEqual(founding[2]['format'], 'chroma')

    def test_removed_compatibility_is_not_a_current_command(self):
        from mantleos.console import main
        from contextlib import redirect_stderr
        import io
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as rejected:
            main(['legacy', 'rgba', 'unused.vcw'])
        self.assertEqual(rejected.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
