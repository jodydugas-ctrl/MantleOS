from pathlib import Path
import sys
from types import ModuleType
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.vendor import vendored_symbol


class VendorIsolationTests(unittest.TestCase):
    def test_private_alias_and_submodule_preloads_cannot_spoof_runtime(self):
        alias = "_hermes_mantle_vendor"
        module_name = alias + ".core.organism"
        originals = {
            name: sys.modules.get(name)
            for name in (alias, alias + ".core", module_name)
        }
        sentinel = object()
        fake_package = ModuleType(alias)
        fake_package.__path__ = []
        fake_core = ModuleType(alias + ".core")
        fake_core.__path__ = []
        fake_organism = ModuleType(module_name)
        setattr(fake_organism, "Organism", sentinel)
        sys.modules[alias] = fake_package
        sys.modules[alias + ".core"] = fake_core
        sys.modules[module_name] = fake_organism
        try:
            resolved = vendored_symbol("core.organism", "Organism")
            resolved_module = sys.modules[resolved.__module__]
            origin = getattr(resolved_module, "__file__", None)
        finally:
            for name, original in originals.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original

        self.assertIsNot(sentinel, resolved)
        self.assertIsInstance(origin, str)
        self.assertTrue(
            Path(str(origin)).resolve().is_relative_to(
                PROJECT_ROOT.parents[1] / "src" / "mantle"
            )
        )

    def test_private_vendor_namespace_runs_applet5(self):
        """The loader must preserve relative imports in executable invariants."""
        check = vendored_symbol("audits.invariants", "t_applet_secret_boundary_and_bands")
        passed, note = check()
        self.assertTrue(passed, note)

    def test_stage1_language_separates_evidence_from_authority(self):
        stage1 = (PROJECT_ROOT.parents[1] / "src" / "mantle" / "audits" / "stage1.py")
        text = stage1.read_text(encoding="utf-8")
        self.assertNotIn("authorizes Phase 2", text)
        self.assertNotIn("Phase 2 authorized", text)
        self.assertIn("separate readiness and dual authorization", text)


if __name__ == "__main__":
    unittest.main()
