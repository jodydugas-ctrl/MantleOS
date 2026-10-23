import hashlib
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "docs" / "assimilation"
INVENTORY_PATH = ARTIFACT_ROOT / "APP_INVENTORY.md"
ORGAN_MAP_PATH = ARTIFACT_ROOT / "hermes_organ_map.json"
CENSUS_PATH = ARTIFACT_ROOT / "host_census.json"

FULL_ORGANS = {
    "heart",
    "genome",
    "nervous",
    "senses",
    "immune",
    "limbs",
    "memory",
    "brain",
    "reproduction",
}


class HermesInventoryTests(unittest.TestCase):
    def test_phase_zero_artifacts_exist(self):
        self.assertTrue(INVENTORY_PATH.is_file(), "APP_INVENTORY.md is missing")
        self.assertTrue(ORGAN_MAP_PATH.is_file(), "hermes_organ_map.json is missing")
        self.assertTrue(CENSUS_PATH.is_file(), "host_census.json is missing")

    def test_inventory_has_required_doctrine_sections(self):
        inventory = INVENTORY_PATH.read_text(encoding="utf-8")
        required_sections = {
            "## A.1 Host identity",
            "## A.2 Preserved host behavior",
            "## A.3 Observable surfaces",
            "## A.4 Secret boundaries",
            "## A.5 Proposed organ map",
            "## A.6 Proposed VCW bands",
            "## A.7 Controls and effect boundaries",
            "## A.8 Explicit gaps",
            "## A.9 READ-ONLY sign-off",
        }

        for section in required_sections:
            self.assertIn(section, inventory)
        self.assertIn("files_modified=0", inventory)
        self.assertIn("Approved to instrument: true", inventory)
        self.assertIn("Excluded: MIND fusion, mutating tools, reproduction activation", inventory)

    def test_organ_map_is_read_only_and_covers_all_nine_organs(self):
        organ_map = json.loads(ORGAN_MAP_PATH.read_text(encoding="utf-8"))

        self.assertTrue(organ_map["read_only"])
        self.assertEqual(0, organ_map["files_modified"])
        self.assertEqual(FULL_ORGANS, set(organ_map["organs"]))
        self.assertTrue(organ_map["signoff"]["approved_to_instrument"])
        self.assertIn("excludes MIND fusion", organ_map["signoff"]["approved_scope"])
        self.assertIn("observable_surfaces", organ_map)
        self.assertIn("secret_boundaries", organ_map)
        self.assertIn("controls", organ_map)
        self.assertIn("gaps", organ_map)

    def test_host_census_proves_no_change(self):
        census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))

        self.assertEqual("sha256", census["algorithm"])
        self.assertGreater(census["tracked_file_count"], 0)
        self.assertEqual(census["tracked_file_count"], len(census["file_hashes"]))
        manifest = "".join(
            f"{digest}  {path}\n"
            for path, digest in sorted(census["file_hashes"].items())
        ).encode("utf-8")
        recomputed_digest = hashlib.sha256(manifest).hexdigest()
        self.assertEqual(census["before_digest"], recomputed_digest)
        self.assertEqual(census["before_digest"], census["after_digest"])
        self.assertEqual([], census["modified_files"])
        self.assertEqual(0, census["files_modified"])


if __name__ == "__main__":
    unittest.main()
