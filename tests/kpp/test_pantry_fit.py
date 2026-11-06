import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mantleos.kpp.cli import main
from mantleos.kpp.core import digest, ingredient_catalog, read_json
from mantleos.kpp.pantry import discover, view
from mantleos.kpp.pantry_index import fit
from mantleos.kpp.workshop import begin, load


RESOURCES = Path(__import__("mantleos.kpp", fromlist=["x"]).__file__).parent / "resources"


def row(report, name):
    return next(item for item in report["ingredients"] if item["id"] == name)


class PantryFitTests(unittest.TestCase):
    def setUp(self):
        self.catalog = ingredient_catalog(RESOURCES, check_sources=False)
        self.sleep_recipe = read_json(RESOURCES / "recipes/sleep-memory-composition.json")

    def test_discovery_and_contract_share_manifest_classification(self):
        for organ in ("heart", "memory"):
            result = discover(RESOURCES, organ=organ)
            self.assertIn("sleep-memory-consolidation", {item["id"] for item in result["matches"]})
        contract = view(RESOURCES, "sleep-memory-consolidation", "contract")
        self.assertEqual(contract["organs"], ["heart", "memory"])
        self.assertEqual(contract["provides"], ["memory-retrieval-view/1"])
        self.assertIsNone(view(RESOURCES, "text-editor", "contract")["requires"])
        self.assertIn("text-editor", {item["id"] for item in discover(RESOURCES, "text-editor")["matches"]})

    def test_selected_chain_and_omitted_provider(self):
        report = fit(self.catalog, recipe=self.sleep_recipe)
        self.assertEqual(report["recipe_sha256"], digest(self.sleep_recipe))
        self.assertTrue(all(item["declared_inputs_satisfied"] for item in report["ingredients"]))
        sleep = row(report, "sleep-memory-consolidation")
        self.assertEqual(sleep["inputs"]["verified-engram-prefix/1"]["ids"], ["engram-continuity"])
        self.assertEqual(row(report, "engram-continuity")["inputs"]["engram-ledger-source/1"]["ids"],
                         ["appai-heart"])

        selection = ["sleep-memory-consolidation", "appai-heart"]
        gap = fit(self.catalog, ingredients=selection, host_capabilities=["verified-engram-prefix/2"])
        self.assertEqual(gap, fit(self.catalog, ingredients=selection[::-1],
                                 host_capabilities=["verified-engram-prefix/2"]))
        missing, = row(gap, "sleep-memory-consolidation")["missing_inputs"]
        self.assertEqual(missing["capability"], "verified-engram-prefix/1")
        self.assertEqual([item["id"] for item in missing["suggestions"]], ["engram-continuity"])
        reused = fit(self.catalog, recipe=self.sleep_recipe, host_capabilities=["verified-engram-prefix/1"])
        self.assertEqual(row(reused, "sleep-memory-consolidation")["inputs"]["verified-engram-prefix/1"],
                         {"kind": "host"})

    def test_legacy_dependencies_and_unknown_interface_metadata(self):
        report = fit(self.catalog, ingredients=["chroma-png-memory"])
        carrier = row(report, "chroma-png-memory")
        self.assertEqual(carrier["missing_dependencies"], ["engram-continuity"])
        self.assertEqual(carrier["interface_metadata"], "unknown")
        self.assertIsNone(carrier["declared_inputs_satisfied"])

    def test_incompatible_providers_and_wait_cycles(self):
        catalog = {
            "left": {"id": "left", "provides": ["a/1"], "requires": ["b/1"], "compatible_tissues": ["python"]},
            "right": {"id": "right", "provides": ["b/1"], "requires": ["a/1"], "compatible_tissues": ["python"]},
            "other": {"id": "other", "provides": ["b/1"], "requires": [], "compatible_tissues": ["javascript"]},
        }
        recipe = dict(self.sleep_recipe, ingredients=["left", "right"])
        report = fit(catalog, recipe=recipe)
        self.assertEqual(report["possible_wait_cycles"], [["left", "right"]])
        self.assertEqual(row(report, "left")["missing_inputs"][0]["suggestions"], [])
        report = fit(catalog, recipe=recipe, ingredients=["other"], host_capabilities=["b/1"])
        self.assertEqual(report["possible_wait_cycles"], [])
        self.assertEqual(row(report, "other")["tissue"], "incompatible")
        self.assertEqual(row(report, "left")["inputs"]["b/1"], {"kind": "host"})

    def test_cli_is_advisory_and_keeps_existing_workspace_pins(self):
        path = RESOURCES / "recipes/appai-heart-notes-trial.json"
        recipe = read_json(path)
        args = ["pantry-fit", "--repo", str(RESOURCES), "--recipe", str(path)]
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "notes"
            begin(workspace, recipe, RESOURCES)
            before = {p.relative_to(workspace): p.read_bytes()
                      for p in workspace.rglob("*") if p.is_file()}
            with patch("mantleos.kpp.pantry.source_identity", side_effect=AssertionError("source access")):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(args), 0)
                self.assertEqual(row(json.loads(output.getvalue()), "heart-notes-export")
                                 ["missing_inputs"][0]["capability"], "notes-rows/1")
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(args + ["--host-capability", "notes-rows/1"]), 0)
                self.assertTrue(row(json.loads(output.getvalue()), "heart-notes-export")
                                ["declared_inputs_satisfied"])
            self.assertEqual({p.relative_to(workspace): p.read_bytes()
                              for p in workspace.rglob("*") if p.is_file()}, before)
            self.assertEqual(load(workspace)[0], recipe)

    def test_invalid_cli_arguments_and_metadata_fail(self):
        for arguments in ([], ["--ingredient", "missing"],
                          ["--ingredient", "appai-heart", "--host-capability", "unversioned"]):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                self.assertNotEqual(main(["pantry-fit", "--repo", str(RESOURCES), *arguments]), 0)
        invalid = {"appai-heart": dict(self.catalog["appai-heart"], organs=["brain"])}
        with self.assertRaisesRegex(ValueError, "Invalid organs"):
            fit(invalid, ingredients=["appai-heart"])
