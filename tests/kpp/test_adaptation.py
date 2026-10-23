"""Unit, negative, freshness, CLI and fixed-oracle integration example checks."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from mantleos.kpp.adaptation import fit, reflex_plan
from mantleos.kpp.core import KPPError, read_json
from mantleos.kpp.workshop import begin, load

ROOT = Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
REQ = ROOT / "examples/adaptive-reflex/request.json"
RECIPE = ROOT / "recipes/adaptive-reflex-demo.json"
SOURCE = ROOT / "examples/adaptive-reflex"


class AdaptationTests(unittest.TestCase):
    def request(self):
        return read_json(REQ)

    def test_fit_does_not_auto_admit(self):
        result = fit(ROOT, self.request())
        self.assertEqual(result["recommendation"], "REVIEW_REUSE_BEFORE_NEW_CONSTRUCTION")
        self.assertEqual(result["schema"], "kpp.functional-fit/1")
        ids = [i["id"] for i in result["matches"]]
        self.assertIn("engram-continuity", ids)
        self.assertTrue(all(m["disposition"] == "REVIEW_ONLY_NOT_ADMITTED" for m in result["matches"]))

    def test_noop_when_baseline_exact_claim(self):
        r = self.request()
        r["existing_capabilities"].append(r["capability"])
        self.assertEqual(fit(ROOT, r)["recommendation"], "NO_CHANGE_PROPOSED_USER_ASSERTED_COVERAGE")

    def test_contract_validation(self):
        r = self.request()
        r["anchors"] = {"original": "original-commands"}
        with self.assertRaises(KPPError):fit(ROOT, r)
        r = self.request()
        r["trigger"]["timing"] = "unknown"
        with self.assertRaises(KPPError):fit(ROOT, r)
        r = self.request()
        r["ingredient_id"] = "unknown-ingredient"
        with self.assertRaises(KPPError):fit(ROOT, r)

    def test_proposal_is_source_bound_and_nonmutating(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            begin(ws, read_json(RECIPE), ROOT)
            recipe, state = load(ws)
            original = [(p.name, p.read_bytes()) for p in SOURCE.glob('*.py')]
            proposal = reflex_plan(ROOT, recipe, state, self.request(), SOURCE)
            self.assertEqual(proposal["decision"], "PROPOSAL_REQUIRES_BAKER_REVIEW")
            self.assertEqual(proposal["tentative_point"]["function"], "run_command")
            self.assertFalse(proposal["tentative_point"]["insertion_point_verified"])
            self.assertEqual(proposal["execution"], "NONE")
            self.assertEqual(proposal["verification"], "NONE")
            self.assertEqual(proposal["admission"], "NOT_AUTHORIZED")
            self.assertEqual(proposal["preservation"]["required_anchors"], 3)
            self.assertEqual(original, [(p.name, p.read_bytes()) for p in SOURCE.glob('*.py')])
            self.assertEqual(read_json(ws / 'state.json'), state)
            self.assertEqual(read_json(ws / 'recipe.json'), recipe)

    def test_changes_make_old_proposal_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / 'source'; d.mkdir()
            (d / 'body.py').write_text('def run_command():\n    return True\n')
            ws = Path(tmp) / 'ws'
            begin(ws, read_json(RECIPE), ROOT)
            recipe, state = load(ws)
            first = reflex_plan(ROOT, recipe, state, self.request(), d)
            (d / 'body.py').write_text('def run_command():\n    return False\n')
            second = reflex_plan(ROOT, recipe, state, self.request(), d)
            self.assertNotEqual(first["source_inventory_sha256"], second["source_inventory_sha256"])
            self.assertNotEqual(first["tentative_point"]["source_sha256"],second["tentative_point"]["source_sha256"])

    def test_ambiguous_duplicate_function_names_are_not_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / 'source'; d.mkdir()
            (d / 'one.py').write_text('def run_command():\n    return 1\n')
            (d / 'two.py').write_text('def run_command():\n    return 2\n')
            ws = Path(tmp) / 'ws'
            begin(ws, read_json(RECIPE), ROOT)
            recipe, state = load(ws)
            proposal = reflex_plan(ROOT, recipe, state, self.request(), d)
            self.assertEqual(proposal["decision"], "AMBIGUOUS_REVIEW_MANUALLY")
            self.assertIsNone(proposal["tentative_point"])

    def test_reject_unanchored_recipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / 'ws'
            r = read_json(RECIPE)
            r["anchors"] = [a for a in r["anchors"] if a["id"] != 'optional-organ-absent']
            r.pop("reflexes", None)  # isolate planner rejection from recipe-level reflex validation
            begin(ws, r, ROOT)
            recipe, state = load(ws)
            with self.assertRaises(KPPError):reflex_plan(ROOT, recipe, state, self.request(), SOURCE)

    def test_original_body_and_fixed_oracle_are_pinned(self):
        import hashlib
        pins = read_json(SOURCE / 'baseline-pins.json')
        self.assertEqual(pins['schema'], 'kpp.example-baseline-pins/1')
        for filename, wanted in pins['sha256'].items():
            self.assertEqual(hashlib.sha256((SOURCE / filename).read_bytes()).hexdigest(), wanted)

    def test_fixed_oracle_demo_runs(self):
        run = subprocess.run([sys.executable, str(SOURCE/'smoke.py')], capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('PASS:', run.stdout)

    def test_cli_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / 'ws'
            env={**os.environ, 'PYTHONPATH':str(Path(__import__('mantleos').__file__).parent.parent)}
            def cli(*args):
                return subprocess.run([sys.executable,'-m','mantleos','kpp',*args],cwd=ROOT,env=env,
                                      text=True,capture_output=True,timeout=20)
            self.assertEqual(cli('new','--recipe',str(RECIPE),'--workspace',str(ws)).returncode,0)
            fit_run=cli('fit','--request',str(REQ))
            self.assertEqual(fit_run.returncode,0,fit_run.stderr)
            plan=cli('reflex-plan','--workspace',str(ws),'--request',str(REQ),'--source',str(SOURCE))
            self.assertEqual(plan.returncode,0,plan.stderr)
            self.assertEqual(json.loads(plan.stdout)['status'],'REVIEW_REQUIRED_NO_MUTATION')


if __name__=='__main__': unittest.main()
