"""A first usable preview precedes Chase, which retains every open obligation."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mantleos import anchor_apps
from mantleos.kpp.build import BUILD_RULE, run, step
from mantleos.kpp.core import KPPError, digest, read_json, write_json
from mantleos.kpp.workshop import begin, accept, finish, inspection, handoff

ROOT = Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent / 'resources'


class BuildLoopTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.workspace = Path(temp.name) / 'app'
        self.recipe = read_json(ROOT / 'recipes/progressive-calculator.json')
        begin(self.workspace, self.recipe, ROOT)

    def test_first_preview_precedes_all_refinement_and_loop_retains_every_anchor(self):
        events = []
        def preview(current):
            events.append(('preview', current['phase']))
            self.assertTrue((self.workspace / 'app/index.html').is_file())
            return {'status': 'OPENED', 'scope': 'synthetic host-order fixture, not a rendering receipt'}
        def refine(current):
            self.assertEqual(events[0], ('preview', 'BUILDING'))
            events.append(('refine', current['next']['id']))
            # Explicit synthetic Baker fixture; the driver never calls accept.
            accept(self.workspace, current['next']['id'], 'Synthetic loop test only', 'synthetic-test-baker')
            return 'CONTINUE'
        result = run(self.workspace, open_preview=preview, refine=refine, max_cycles=3)
        self.assertEqual(result['status'], 'READY_FOR_COMPLETION')
        self.assertEqual({event[1] for event in events[1:]}, {a['id'] for a in self.recipe['anchors']})
        self.assertEqual(result['step']['phase'], 'BUILDING')
        self.assertFalse((self.workspace / 'completion-receipt.json').exists())
        finish(self.workspace)  # separate explicit completion
        self.assertEqual(step(self.workspace)['decision'], 'COMPLETE')

    def test_failed_checks_do_not_disappear_when_the_preview_is_usable(self):
        seen = []
        result = run(self.workspace, open_preview=lambda _: {'status': 'OPENED'},
                     refine=lambda current: seen.append(current['next']['id']) or 'CONTINUE', max_cycles=2)
        self.assertEqual(result['status'], 'BUDGET_EXHAUSTED')
        self.assertEqual(seen, ['usable-surface', 'usable-surface'])
        self.assertEqual(len(result['step']['unmet_anchors']), 3)
        self.assertEqual(inspection(self.workspace)['accepted'], 0)
        with self.assertRaisesRegex(KPPError, 'unmet'): finish(self.workspace)

    def test_missing_preview_and_pending_review_stop_with_resume_point(self):
        def forbidden(_): raise AssertionError('Refinement started without a preview')
        result = run(self.workspace, open_preview=lambda _: {'status': 'HOST_PREVIEW_UNAVAILABLE'}, refine=forbidden)
        self.assertEqual(result['status'], 'PREVIEW_UNAVAILABLE')
        self.assertEqual(result['cycles'], [])
        result = run(self.workspace, open_preview=lambda _: {'status': 'APPLIED'},
                     refine=lambda _: 'AWAITING_REVIEW')
        self.assertEqual(result['status'], 'AWAITING_REVIEW')
        self.assertEqual(result['step']['next']['id'], 'usable-surface')
        self.assertEqual(result['step']['accepted'], 0)

    def test_required_optional_prerequisite_is_pursued_without_unrequested_work(self):
        recipe = copy.deepcopy(self.recipe)
        recipe['anchors'].append({'id': 'prerequisite', 'statement': 'Needed by required behavior',
            'depth': 1, 'required': False, 'test': 'Synthetic prerequisite check'})
        recipe['anchors'].append({'id': 'unrequested', 'statement': 'Optional extra',
            'depth': 1, 'required': False, 'test': 'Synthetic optional check'})
        for anchor in recipe['anchors'][:3]: anchor['depends'] = ['prerequisite']
        other = self.workspace.parent / 'dependencies'
        begin(other, recipe, ROOT)
        current = step(other)
        self.assertEqual(current['next']['id'], 'prerequisite')
        self.assertNotIn('unrequested', [item['id'] for item in current['waiting']])

    def test_recipe_scope_cannot_change_even_during_the_last_budgeted_cycle(self):
        def refine(_):
            recipe = read_json(self.workspace / 'recipe.json')
            recipe['goal'] = 'Changed scope'
            write_json(self.workspace / 'recipe.json', recipe)
            state = read_json(self.workspace / 'state.json')
            state['recipe_hash'] = digest(recipe)
            write_json(self.workspace / 'state.json', state)
            return 'CONTINUE'
        with self.assertRaisesRegex(KPPError, 'Recipe changed during Chase'):
            run(self.workspace, open_preview=lambda _: {'status': 'OPENED'}, refine=refine, max_cycles=1)

    def test_unknown_effect_is_not_retried_and_invalid_budgets_are_rejected(self):
        calls = []
        def refine(_):
            calls.append(1)
            raise OSError('Host must reconcile the effect')
        with self.assertRaisesRegex(OSError, 'reconcile'):
            run(self.workspace, open_preview=lambda _: {'status': 'OPENED'}, refine=refine)
        self.assertEqual(calls, [1])
        for limit in (True, 0, 257, '16'):
            with self.subTest(limit=limit), self.assertRaises(KPPError):
                run(self.workspace, open_preview=lambda _: {'status': 'OPENED'}, refine=refine, max_cycles=limit)

    def test_host_context_is_small_and_kpp_handoff_uses_the_same_build_rule(self):
        contract = anchor_apps.request_contract('Build a Notepad app in Canvas')
        self.assertNotIn('complete_profile_example', contract)
        self.assertLess(len(json.dumps(contract).encode()), 5000)
        self.assertEqual(contract['delivery_order'][0], 'MOUNT_FIRST_USABLE_SLICE')
        self.assertIn(BUILD_RULE, contract['authoring_rule'])
        self.assertIn(BUILD_RULE, handoff(self.workspace))
        self.assertIsNone(anchor_apps.request_contract('Please review this imported document'))
        example = anchor_apps.request_contract('Build a Notepad app', include_example=True)
        self.assertEqual(example['complete_profile_example'], anchor_apps.notepad_source())

    def test_standalone_body_carries_usable_kpp_tools_and_preview_assets(self):
        from mantleos.builder import _install_runtime_library
        body = self.workspace.parent / 'synthetic-body-runtime'
        _install_runtime_library(body)
        result = subprocess.run([sys.executable, '-I', '-S', str(body / 'runtime.py'), 'kpp', 'doctor'],
                                cwd=body, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
        self.assertTrue(json.loads(result.stdout)['ready'])
        for name in ('assets/progressive.js', 'resources/recipes/progressive-calculator.json',
                     'resources/previews/calculator/base.js'):
            self.assertEqual((body / 'runtime_lib/mantleos/kpp' / name).read_bytes(),
                             (ROOT.parent / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
