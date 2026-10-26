import json
from pathlib import Path
import tempfile
import unittest

from mantleos.kpp import core, pantry, workshop

RESOURCES = Path(core.__file__).resolve().parent / 'resources'


class ReflexBookReferenceTests(unittest.TestCase):
    def test_bundled_label_is_data_only_and_exposes_limits(self):
        label = pantry.view(RESOURCES, 'reflex-book')
        self.assertEqual(label['status'], 'experimental')
        self.assertEqual(label['source']['kind'], 'bundled-module')
        self.assertEqual(label['source']['source_access'], 'EXPLICIT_ONLY')
        self.assertEqual(label['integration'], 'REQUIRES_RECIPE_SPECIFIC_TESTS')
        self.assertIn('no native execution profile', label['limits'])

    def test_recipe_is_unbound_and_new_bake_never_inherits_acceptance(self):
        recipe = json.loads((RESOURCES/'recipes/reflex-book-review.json').read_text())
        core.validate_recipe(recipe)
        core.validate_pantry(recipe, core.ingredient_catalog(RESOURCES))
        self.assertEqual(recipe['anchor_binding'], 'none')
        self.assertEqual(recipe['schema'], 'kpp.recipe/4')
        self.assertFalse(recipe['capabilities'].get('mind', False))
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / 'review'
            workshop.begin(workspace, recipe, RESOURCES)
            report = workshop.inspection(workspace)
            self.assertEqual(report['phase'], 'BUILDING')
            self.assertFalse(report['all_required_satisfied'])
            self.assertEqual(len(report['unmet']), 8)
            self.assertFalse(workshop.load(workspace)[1]['accepted'])
            with self.assertRaises(core.KPPError):
                workshop.finish(workspace)
