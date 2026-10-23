"""One definition, one implementation, two distribution entry points."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mantleos import anchors, cells, kitchen, tissue
from mantleos.anchor_engine.tools.anchor_runtime import render_hello_world
from mantleos.kpp import anchor, core, graph, gui, scanner, systems
from mantleos.kpp import cells as kpp_cells, tissue as kpp_tissue
from mantleos.scan import discovery
from mantleos.scan.common import digest
from mantleos.scan.scanner import scan as native_scan

RESOURCE = Path(core.__file__).parent / 'resources'


class UnifiedSystemTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_same_definition_objects_and_kernel_functions(self):
        self.assertIs(systems.anchors, anchors)
        self.assertIs(kpp_cells.produce, cells.produce)
        self.assertIs(kpp_tissue.program, tissue.program)
        pixel = kpp_cells.produce('chroma.rgb/1', [12, 34, 56])
        self.assertEqual(pixel['schema'], 'mantle.cell/2')
        self.assertEqual(pixel['payload'], [12, 34, 56])
        program = kpp_tissue.program('literal', 'EMIT_TEXT/0.2', render_hello_world('Literal', 'shared'))
        self.assertEqual(program['schema'], 'mantle.program/1')

    def test_recipe_obligations_are_exact_shared_neutral_applications(self):
        recipe = core.read_json(RESOURCE / 'recipes/notepad-demo.json')
        core.validate_recipe(recipe)
        binding = kitchen.bind(recipe)
        for application in binding['applications']:
            self.assertEqual(anchors.validate(application)['singularity'], anchors.definition('Neutral').singularity)
            self.assertEqual(application['type'], 'Neutral')
        value = graph.functional_graph(recipe, {'recipe_hash': core.digest(recipe), 'accepted': {}})
        self.assertEqual(value['anchor_binding'], binding)
        self.assertTrue(all(node['application'] in binding['applications'] for node in value['nodes'] if node['kind'] == 'anchor'))
        self.assertFalse(binding['authorized'])

    def test_rehashed_new_anchor_type_or_singularity_is_refused(self):
        recipe = core.read_json(RESOURCE / 'recipes/notepad-demo.json')
        for key, value in [('type', 'Acceptance'), ('definition', 'KPP-Neutral'), ('singularity', 'invented')]:
            changed = copy.deepcopy(recipe)
            changed['anchors'][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(core.KPPError, 'cannot redefine'):
                core.validate_recipe(changed)

    def test_literal_interpreter_uses_native_function(self):
        from mantleos.anchor_engine.tools.anchor_runtime import program_stdout
        self.assertIs(anchor.program_stdout, program_stdout)
        for text in ('', 'hello', '\u2603\nline', 'print("data only")'):
            source = render_hello_world('Shared', text)
            self.assertEqual(anchor.interpret(source), text)
            with self.assertRaises(core.KPPError):
                anchor.interpret(source.replace(' -01 ', ' -99 '))

    def test_shared_notepad_profile_requires_explicit_command(self):
        from mantleos.anchor_engine.tools.notepad_blueprint import generate
        # The native template/generator is used; no KPP-only profile grammar.
        source = generate()
        path = self.root / 'notepad.anchor'
        path.write_text(source, encoding='utf-8', newline='\n')
        self.assertEqual(anchor.inspect_file(path)['profile'], 'NOTEPAD_LLM/1.3')
        with self.assertRaises(core.KPPError):
            anchor.run_file(path)
        result = json.loads(anchor.run_file(path, {'op': 'INSERT', 'text': 'one system'}))
        self.assertEqual(result['profile'], 'NOTEPAD_LLM/1.3')

    def test_scan_is_native_graph_and_tampered_projection_is_refused(self):
        source = self.root / 'source'; source.mkdir()
        (source / 'main.py').write_text('raise RuntimeError("NEVER EXECUTE")\ndef a():\n    return b()\ndef b():\n    return 3\n', encoding='utf-8')
        (source / 'main.js').write_text('function f(){return 3;}', encoding='utf-8')
        result = scanner.scan(source, 3, workspace=self.root / 'kpp-cache')
        native = native_scan(source, self.root / 'native-cache', max_files=400, max_file_bytes=1_000_000)
        self.assertEqual(result['native_report']['graph'], native['graph'])
        self.assertEqual(result['graph_digest'], native['graph_digest'])
        self.assertFalse(result['native_report']['graph']['scope']['specimen_executed'])
        result['edges'].clear()
        result['sha256'] = core.digest({k: v for k, v in result.items() if k != 'sha256'})
        with self.assertRaises(core.KPPError):
            scanner.verify_scan(result)
        with self.assertRaises(core.KPPError):
            scanner.verify_scan({'schema': 'kpp.static-scan/1'})

    def test_qt_inventory_is_identical_to_native_extractor(self):
        source = RESOURCE / 'references/synthetic-qt'
        import time
        native = discovery.scan_qt(source, 'shared', deadline=time.monotonic() + 30)
        self.assertEqual(gui.scan_qt(source, 'shared'), native)

    def test_supplemental_html_has_a_combined_record_budget(self):
        source = self.root / 'html'; source.mkdir()
        for name in ('one.html', 'two.html'):
            (source / name).write_text('<button>item</button>' * 6000, encoding='utf-8')
        with self.assertRaisesRegex(core.KPPError, 'record budget'):
            scanner.scan(source)

    def test_canonical_document_is_same_as_mantleos_published_view(self):
        root = Path(__file__).resolve().parents[2]
        if (root / 'docs/kpp.md').exists():
            self.assertEqual((root / 'docs/kpp.md').read_bytes(), (RESOURCE / 'SYSTEMS.md').read_bytes())
        else:
            # Standalone distribution has its common view at the project root.
            root = Path(__file__).resolve().parents[1]
            self.assertEqual((root / 'SYSTEMS.md').read_bytes(), (RESOURCE / 'SYSTEMS.md').read_bytes())

    def test_cell_specimen_is_generated_from_actual_canonical_source(self):
        from mantleos.kpp.specimens import kernel_cells
        self.assertEqual(kernel_cells().encode('utf-8'),
                         (RESOURCE / 'specimens/mantleos/kernel-cells.anchor').read_bytes())
        path = self.root / 'cells.py'
        anchor.bridge_python(RESOURCE / 'specimens/mantleos/kernel-cells.anchor', path)
        result = subprocess.run([sys.executable, '-I', '-S', str(path), '--kernel', 'chroma.rgb/1',
                                 '--value', '[12,34,56]'], capture_output=True, text=True, check=True, timeout=15)
        self.assertEqual(json.loads(result.stdout), cells.produce('chroma.rgb/1', [12, 34, 56]))

    def test_export_has_identical_modules_definitions_and_source_drift_gate(self):
        source = next(parent for parent in Path(__file__).resolve().parents
                      if (parent / 'tools/export_kpp.py').is_file())
        spec = importlib.util.spec_from_file_location('shared_export_test', source / 'tools/export_kpp.py')
        exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)
        output = self.root / 'standalone'
        self.assertEqual(exporter.export(output, source)['shared_source'], 'BYTE_IDENTICAL')
        command = ('import sys; sys.path.insert(0,sys.argv[1]); '
                   'import kpp.core,kpp.systems,kpp.anchors,mantleos.kpp.core,mantleos.anchors; '
                   'assert kpp.core is mantleos.kpp.core; assert kpp.anchors is mantleos.anchors; '
                   'assert kpp.systems.anchors is mantleos.anchors; print("one system")')
        result = subprocess.run([sys.executable, '-I', '-S', '-c', command, str(output / 'src')],
                                capture_output=True, text=True, check=True, timeout=20)
        self.assertEqual(result.stdout.strip(), 'one system')
        (output / 'src/mantleos/anchors.py').write_text('different source', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source drift'):
            exporter.check(output, source)
