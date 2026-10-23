import importlib.util
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = PROJECT_ROOT / "__init__.py"
MANIFEST_PATH = PROJECT_ROOT / "plugin.yaml"


def parse_manifest_lists(path: Path) -> dict[str, list[str]]:
    """Parse the small list-valued subset used by this plugin manifest."""
    values: dict[str, list[str]] = {}
    current_key = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not raw_line.startswith((" ", "\t")) and ":" in stripped:
            key, raw_value = stripped.split(":", 1)
            current_key = key
            raw_value = raw_value.strip()
            if raw_value == "[]":
                values[key] = []
            continue
        if stripped.startswith("- ") and current_key:
            values.setdefault(current_key, []).append(stripped[2:].strip())
    return values


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        "hermes_mantle_manifest_test",
        PLUGIN_PATH,
        submodule_search_locations=[str(PROJECT_ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RecordingContext:
    def __init__(self):
        self.tools = []
        self.hooks = []
        self.commands = []
        self.profile_name = "default"

    def register_tool(self, **registration):
        self.tools.append(registration)

    def register_hook(self, hook_name, callback):
        self.hooks.append((hook_name, callback))

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands.append(name)


class PluginManifestTests(unittest.TestCase):
    def test_manifest_matches_registered_surface(self):
        manifest = parse_manifest_lists(MANIFEST_PATH)
        plugin = load_plugin()
        context = RecordingContext()

        plugin.register(context)

        self.assertIn("provides_tools", manifest)
        self.assertIn("provides_hooks", manifest)
        self.assertEqual(
            set(manifest["provides_tools"]),
            {registration["name"] for registration in context.tools},
        )
        self.assertEqual(
            set(manifest["provides_hooks"]),
            {hook_name for hook_name, _callback in context.hooks},
        )
        self.assertEqual(["mind"], context.commands)

    def test_manifest_does_not_claim_unearned_phase2_state(self):
        manifest_text = MANIFEST_PATH.read_text(encoding="utf-8").lower()

        self.assertNotIn("stage-1 certified", manifest_text)
        self.assertNotIn("mind fused", manifest_text)
        self.assertNotIn("reproduction active", manifest_text)


if __name__ == "__main__":
    unittest.main()
