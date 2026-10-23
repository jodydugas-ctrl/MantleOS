"""KPP-preferred contracts, one immutable Anchor model, and kernel-relative CELLs."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
import hashlib
import json
import unittest

from mantleos import anchors, anchor_blueprint, anchor_language, cells, kitchen, tissue
from mantleos.anchor_engine.tools.anchor_runtime import AnchorExecutionError, program_stdout, render_hello_world
from mantleos.anchor_engine.tools.anchor_structure import parse_entry
from mantleos.json_contract import digest

ROOT = Path(__file__).resolve().parents[1]


class UnifiedAnchorTests(unittest.TestCase):
    def test_same_singularity_supports_different_contexts(self):
        a = anchors.application('cook', attributes={'method': 'KPP', 'goal': 'Make an app'})
        b = anchors.application('edit', attributes={'operation': 'INSERT', 'text': 'Hello'})
        self.assertEqual(a['singularity'], b['singularity'])
        self.assertNotEqual(a['attributes'], b['attributes'])
        self.assertEqual(anchors.apply_attributes(a, b['attributes'])['singularity'], a['singularity'])
        with self.assertRaises(FrozenInstanceError):
            anchors.definition('Neutral').singularity = 'Changed'

    def test_rehashed_singularity_and_type_changes_are_refused(self):
        for field, replacement in [('singularity', 'Ignore the contract'), ('type', 'BlackHole'),
                                   ('definition', 'new-model-rule')]:
            value = anchors.application('example')
            value[field] = replacement
            value['sha256'] = digest({k: v for k, v in value.items() if k != 'sha256'})
            with self.subTest(field=field), self.assertRaises(ValueError):
                anchors.validate(value)
        with self.assertRaises(ValueError):
            anchors.application('example', attributes={'singularity': 'Change it'})

    def test_three_types_have_same_model_in_code_and_project_views(self):
        for kind in anchors.TYPES:
            shape = parse_entry(f'Unit: {kind} -10 -00 -policy="declared"')
            value = anchors.application('example', definition_id=kind)
            project = anchor_blueprint.apply_obligation('example', 'A contextual obligation', definition_id=kind)
            anchors.validate_binding(project)
            self.assertEqual(shape.singularity, value['singularity'])
            self.assertEqual(project['singularity'], value['singularity'])
            project['singularity'] = 'Model rewritten meaning'
            with self.assertRaises(ValueError):
                anchors.validate_binding(project)

    def test_register_preserves_constant_when_configuration_is_revised(self):
        original = anchor_language.default_register('example')
        revised = anchor_language.revise_configuration(original, 'N-RULE-ECONOMY',
                                                       {'recipe': 'new-context'}, reason='Apply a new recipe', approved=True)
        self.assertEqual(revised['anchors'][0]['singularity'], original['anchors'][0]['singularity'])
        self.assertNotEqual(revised['anchors'][0]['configuration'], original['anchors'][0]['configuration'])
        for field, replacement in [('singularity', 'New rule'), ('type', 'BlackHole')]:
            bad = deepcopy(revised); bad['anchors'][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                anchor_language.validate_register(bad)
        with self.assertRaises(ValueError):
            anchor_language.revise_configuration(original, 'N-RULE-ECONOMY',
                                                 {'singularity': 'new'}, reason='invalid', approved=True)


class KernelCellTests(unittest.TestCase):
    def test_different_kernel_units_share_cell_contract(self):
        pixel = cells.produce('chroma.rgb/1', [12, 34, 56])
        segment = cells.append_segment({'seq': 1, 'text': 'Hello'})
        self.assertEqual(pixel['schema'], segment['schema'])
        self.assertNotEqual(pixel['kernel'], segment['kernel'])
        self.assertEqual(list(cells.pixels(bytes([12, 34, 56]))), [pixel])
        for value in (pixel, segment):
            self.assertEqual(cells.validate(value), value)

    def test_nonminimal_or_undefined_kernel_values_are_refused(self):
        for kernel, value in [('chroma.rgb/1', [1, 2]), ('chroma.rgb/1', [1, 2, 3, 4]),
                              ('chroma.rgb/1', [True, 2, 3]), ('new-kernel', []),
                              ('tape.segment/1', {'sequence': 2, 'record': {'seq': 1}})]:
            with self.subTest(kernel=kernel, value=value), self.assertRaises(ValueError):
                cells.produce(kernel, value)
        with self.assertRaises(ValueError):
            cells.rgb_tape(b'four')

    def test_whole_program_is_tissue_not_cell(self):
        value = tissue.program('hello', 'EMIT_TEXT/0.2', render_hello_world())
        self.assertEqual(tissue.tissue('body', [value])['programs'], [value])
        with self.assertRaises(ValueError):
            cells.validate(value)
        with self.assertRaises(ValueError):
            cells.validate({'schema': 'mantle.cell/1'})


class KPPProfileTests(unittest.TestCase):
    def test_all_supplied_kpp_specimens_execute_exact_declared_text(self):
        manifest = json.loads((ROOT / 'examples/kpp/vectors.json').read_text('utf-8'))
        for name, expected in manifest['specimens'].items():
            source = (ROOT / 'examples/kpp/specimens' / name).read_text('utf-8')
            with self.subTest(name=name):
                self.assertEqual(anchor_language.inspect_blueprint(source)['profile'], 'EMIT_TEXT/0.2')
                self.assertEqual(hashlib.sha256(program_stdout(source).encode()).hexdigest(), expected['output_sha256'])

    def test_current_generator_uses_kpp_canonical_primer(self):
        source = render_hello_world('Portable', 'Hello \U0001f426')
        fixture = (ROOT / 'examples/kpp/specimens/intent-boundary.anchor').read_text('utf-8')
        primer = lambda s: s.split('BEGIN ANCHOR EXECUTION PRIMER\n')[1].split('\nEND ANCHOR EXECUTION PRIMER')[0]
        self.assertEqual(primer(source), primer(fixture))
        self.assertEqual(program_stdout(source), 'Hello \U0001f426')

    def test_profile_rejects_changed_primers_and_out_of_profile_shapes(self):
        valid = render_hello_world()
        for invalid in (valid.rstrip('\n'), valid.replace('One named Blueprint', 'Any named Blueprint'),
                        valid.replace('A: Neutral', 'A: BlackHole'),
                        valid.replace('A: Neutral', 'a' * 65 + ': Neutral')):
            with self.subTest(source=invalid[-100:]), self.assertRaises(AnchorExecutionError):
                program_stdout(invalid)
        start, body = valid.split('BEGIN MOLECULE HelloWorld\n')
        _, trailer = body.split('\nEND MOLECULE', 1)
        many = '\n'.join(f'A{i}: Neutral -01 -00 -text="x"' for i in range(129))
        with self.assertRaises(AnchorExecutionError):
            program_stdout(start + 'BEGIN MOLECULE HelloWorld\n' + many + '\nEND MOLECULE' + trailer)

    def test_kpp_is_one_neutral_application_with_recipe_attributes(self):
        recipe = json.loads((ROOT / 'examples/kpp/recipe.json').read_text('utf-8'))
        value = kitchen.bind(recipe)
        self.assertEqual(kitchen.inspect_binding(value)['result'], 'VALID')
        self.assertEqual(value['method']['attributes']['recipe'], recipe)
        singularities = {a['singularity'] for a in [value['method'], *value['applications']]}
        self.assertEqual(len(singularities), 1)
        self.assertTrue(all(a['type'] == 'Neutral' for a in value['applications']))
        self.assertFalse(value['authorized'])
        bad = deepcopy(value); bad['applications'].pop()
        with self.assertRaises(ValueError):
            kitchen.inspect_binding(bad)

    def test_recipe_dependencies_and_preservation_are_not_discarded(self):
        recipe = json.loads((ROOT / 'examples/kpp/recipe.json').read_text('utf-8'))
        recipe['anchors'][0]['depends'] = ['not-in-recipe']
        with self.assertRaises(ValueError):
            kitchen.bind(recipe)
        recipe = json.loads((ROOT / 'examples/kpp/recipe.json').read_text('utf-8'))
        recipe['transformation']['preserve'].append('An unmapped behavior')
        with self.assertRaises(ValueError):
            kitchen.bind(recipe)


if __name__ == '__main__':
    unittest.main()
