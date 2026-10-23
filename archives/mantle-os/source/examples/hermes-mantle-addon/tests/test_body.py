from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import os
import shutil
import sys
import time
from threading import Barrier
from types import ModuleType
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.body import (
    BodyDisabledError,
    ResidencyError,
    ResidentBodyFactory,
    save_resident,
)
from mantle_addon.config import ResidentConfig
from mantle_addon.storage import StorageBoundaryError
from mantle_addon.vendor import vendored_symbol


EXPECTED_ORGANS = {
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


class ResidentBodyFactoryTests(unittest.TestCase):
    runtime_root = PROJECT_ROOT / ".runtime" / "test-body"

    def setUp(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)
        self.runtime_root.mkdir(parents=True)
        self.config = ResidentConfig.from_mapping(
            {"storage_root": str(self.runtime_root)}
        )

    def tearDown(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)

    def test_birth_creates_body_with_nine_organs_and_dormant_uncertified_brain(self):
        factory = ResidentBodyFactory(self.config)

        handle = factory.get_or_create("default")

        self.assertTrue(handle.created)
        self.assertEqual(EXPECTED_ORGANS, set(handle.organism.organs()))
        self.assertTrue(handle.organism.body.primer_sealed)
        self.assertTrue(handle.organism.body.has_key)
        self.assertFalse(handle.organism.stage1_certified)
        self.assertFalse(self.config.mind_enabled)
        self.assertTrue((handle.path / "body.json").is_file())
        self.assertTrue((handle.path / "organism.json").is_file())

    def test_existing_residency_loads_without_rebirth_or_identity_change(self):
        factory = ResidentBodyFactory(self.config)
        born = factory.get_or_create("default")
        fingerprint = born.organism.body.key_fingerprint

        loaded = factory.get_or_create("default")

        self.assertFalse(loaded.created)
        self.assertEqual(fingerprint, loaded.organism.body.key_fingerprint)
        self.assertEqual(0, loaded.organism.prime.generation)
        self.assertEqual([0], sorted(loaded.organism.body.lineage_index))

    def test_separate_profiles_mint_distinct_body_identity(self):
        factory = ResidentBodyFactory(self.config)

        first = factory.get_or_create("alpha")
        second = factory.get_or_create("beta")

        self.assertNotEqual(
            first.organism.body.key_fingerprint,
            second.organism.body.key_fingerprint,
        )

    def test_resident_identity_and_vcw_files_are_owner_only(self):
        handle = ResidentBodyFactory(self.config).get_or_create("private")

        self.assertEqual(0, handle.path.stat().st_mode & 0o077)
        for artifact in handle.path.rglob("*"):
            with self.subTest(artifact=artifact.name):
                self.assertEqual(0, artifact.stat().st_mode & 0o077)

    def test_sensitive_files_are_owner_only_before_vendored_save_returns(self):
        organism_type = vendored_symbol("core.organism", "Organism")
        original_save = organism_type.save
        observed_modes = []

        def inspect_save(instance, directory, *args, **kwargs):
            result = original_save(instance, directory, *args, **kwargs)
            observed_modes.extend(
                artifact.stat().st_mode & 0o777
                for artifact in Path(directory).rglob("*")
                if artifact.is_file()
            )
            return result

        previous_umask = os.umask(0)
        try:
            with patch.object(organism_type, "save", inspect_save):
                ResidentBodyFactory(self.config).get_or_create("umask-zero")
        finally:
            os.umask(previous_umask)

        self.assertTrue(observed_modes)
        self.assertTrue(all(mode & 0o077 == 0 for mode in observed_modes))

    def test_concurrent_birth_mints_exactly_one_identity(self):
        factory = ResidentBodyFactory(self.config)
        barrier = Barrier(4)
        organism_type = vendored_symbol("core.organism", "Organism")
        original_birth = organism_type.birth

        def slow_birth(*args, **kwargs):
            time.sleep(0.1)
            return original_birth(*args, **kwargs)

        def load_or_birth(_):
            barrier.wait(timeout=5)
            return factory.get_or_create("racing")

        with patch.object(organism_type, "birth", side_effect=slow_birth):
            with ThreadPoolExecutor(max_workers=4) as pool:
                handles = list(pool.map(load_or_birth, range(4)))

        self.assertEqual(1, sum(handle.created for handle in handles))
        self.assertEqual(
            1,
            len({handle.organism.body.key_fingerprint for handle in handles}),
        )

    def test_missing_or_invalid_self_seal_refuses_reload(self):
        factory = ResidentBodyFactory(self.config)
        missing = factory.get_or_create("missing-seal").path
        (missing / "self_seal.json").unlink()
        with self.assertRaisesRegex(ResidencyError, "self seal"):
            factory.get_or_create("missing-seal")

        invalid = factory.get_or_create("invalid-seal").path
        seal_path = invalid / "self_seal.json"
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        seal["mac"] = "0" * 64
        seal_path.write_text(json.dumps(seal), encoding="utf-8")
        with self.assertRaisesRegex(ResidencyError, "self seal"):
            factory.get_or_create("invalid-seal")

        fingerprint = factory.get_or_create("fingerprint-seal").path
        seal_path = fingerprint / "self_seal.json"
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        seal["fingerprint"] = "0" * 16
        seal_path.write_text(json.dumps(seal), encoding="utf-8")
        with self.assertRaisesRegex(ResidencyError, "self seal"):
            factory.get_or_create("fingerprint-seal")

    def test_repeated_atomic_save_reload_preserves_identity_modes_and_descriptors(self):
        factory = ResidentBodyFactory(self.config)
        handle = factory.get_or_create("repeated")
        fingerprint = handle.organism.body.key_fingerprint
        before_fds = len(list(Path("/proc/self/fd").iterdir()))

        for sequence in range(6):
            handle.organism.senses.inhale(
                {
                    "action_id": f"repeat:{sequence}",
                    "event_type": "repeat",
                    "source": "test",
                    "metadata": {"sequence": sequence},
                }
            )
            handle.organism.heart.beat(assemble=False)
            save_resident(handle.organism, handle.path)
            handle = factory.get_or_create("repeated")
            self.assertEqual(fingerprint, handle.organism.body.key_fingerprint)
            for node in [handle.path, *handle.path.rglob("*")]:
                self.assertEqual(0, node.lstat().st_mode & 0o077)

        after_fds = len(list(Path("/proc/self/fd").iterdir()))
        self.assertLessEqual(after_fds, before_fds + 1)

    def test_profile_identifier_cannot_escape_storage_root(self):
        factory = ResidentBodyFactory(self.config)

        for profile in ("", "../escape", "a/b", "/absolute", ".", ".."):
            with self.subTest(profile=profile):
                with self.assertRaises(StorageBoundaryError):
                    factory.get_or_create(profile)

        self.assertFalse((self.runtime_root.parent / "escape").exists())

    def test_profile_path_symlink_cannot_alias_another_resident(self):
        factory = ResidentBodyFactory(self.config)
        target = factory.get_or_create("target").path
        alias = self.runtime_root / "organisms" / "alias"
        alias.symlink_to(target, target_is_directory=True)

        with self.assertRaisesRegex(StorageBoundaryError, "symbolic link"):
            factory.get_or_create("alias")

    def test_existing_resident_tree_rejects_symbolic_links_before_load(self):
        resident = self.runtime_root / "organisms" / "linked"
        resident.mkdir(parents=True, mode=0o700)
        os.chmod(resident, 0o700)
        target = self.runtime_root / "outside.json"
        target.write_text("{}", encoding="utf-8")
        (resident / "organism.json").symlink_to(target)

        with self.assertRaisesRegex(ResidencyError, "symbolic link"):
            ResidentBodyFactory(self.config).get_or_create("linked")

    def test_birth_and_load_do_not_use_model_network_or_subprocess(self):
        factory = ResidentBodyFactory(self.config)
        blocked = AssertionError("external capability used during deterministic Body boot")

        with (
            patch("socket.create_connection", side_effect=blocked),
            patch("urllib.request.urlopen", side_effect=blocked),
            patch("subprocess.run", side_effect=blocked),
            patch("subprocess.Popen", side_effect=blocked),
        ):
            born = factory.get_or_create("offline")
            loaded = factory.get_or_create("offline")

        self.assertTrue(born.created)
        self.assertFalse(loaded.created)

    def test_vendored_runtime_ignores_preloaded_global_mantle_module(self):
        original = sys.modules.get("mantle")
        fake = ModuleType("mantle")
        setattr(fake, "__version__", "999.0-fake")
        sys.modules["mantle"] = fake
        try:
            handle = ResidentBodyFactory(self.config).get_or_create("isolated")
        finally:
            if original is None:
                sys.modules.pop("mantle", None)
            else:
                sys.modules["mantle"] = original

        self.assertEqual(
            "Hermes.Mantle.AppAI", handle.organism.body.identity_name()
        )
        self.assertIs(sys.modules.get("mantle"), original)

    def test_disabled_body_refuses_birth(self):
        config = ResidentConfig.from_mapping(
            {"body_enabled": False, "storage_root": str(self.runtime_root)}
        )

        with self.assertRaises(BodyDisabledError):
            ResidentBodyFactory(config).get_or_create("default")

    def test_default_storage_uses_active_hermes_home(self):
        config = ResidentConfig.from_mapping({})
        hermes_home = self.runtime_root / "active-hermes"

        with patch.dict(os.environ, {"HERMES_HOME": str(hermes_home)}):
            factory = ResidentBodyFactory(config)

        self.assertEqual((hermes_home / "mantle").resolve(), factory.storage.root)


if __name__ == "__main__":
    unittest.main()
