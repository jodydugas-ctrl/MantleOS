"""KPP-bound Bio-Software delivery without making Node a core dependency."""
from pathlib import Path
import json
import runpy
import tempfile
import unittest

from mantleos import kitchen

SOURCE = Path(__file__).resolve().parents[1] / 'examples' / 'paint'


class PaintTests(unittest.TestCase):
    def test_recipe_keeps_native_parity_and_operator_acceptance_open(self):
        recipe = json.loads((SOURCE / 'recipe.json').read_text(encoding='utf-8'))
        binding = kitchen.bind(recipe)
        self.assertEqual(kitchen.inspect_binding(binding)['result'], 'VALID')
        self.assertFalse(binding['authorized'])
        self.assertEqual(recipe['product_kind'], 'biosoftware')
        self.assertFalse(any(recipe['capabilities'].values()))
        native = next(a for a in recipe['anchors'] if a['id'] == 'native-xp-parity')
        self.assertTrue(native['required'])
        self.assertTrue(all(a['type'] == 'Neutral' for a in binding['applications']))

    def test_portable_bake_receives_exact_utf8_and_refuses_changed_thought(self):
        builder = runpy.run_path(str(SOURCE / 'build.py'))['build']
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'bake'
            result = builder(root)
            self.assertEqual(result['result'], 'PASS')
            self.assertTrue(result['isolated_receiver_html_equal'])
            self.assertTrue(result['isolated_python_utf8_equal'])
            self.assertTrue(result['changed_thought_rejected'])
            self.assertEqual(result['baker_acceptance'], 'NOT_GRANTED')
            self.assertEqual((root / 'Mantle-Paint.html').read_bytes(), (root / 'receiver' / 'paint.html').read_bytes())
            self.assertNotIn(b'<script src=', (root / 'Mantle-Paint.html').read_bytes())


if __name__ == '__main__':
    unittest.main()
