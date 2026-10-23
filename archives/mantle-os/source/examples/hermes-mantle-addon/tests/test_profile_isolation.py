import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = PROJECT_ROOT / "__init__.py"


def load_plugin(name: str):
    spec = importlib.util.spec_from_file_location(
        name, PLUGIN_PATH, submodule_search_locations=[str(PROJECT_ROOT)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class DynamicContext:
    def __init__(self):
        self.profile_name = "bootstrap"
        self.tools = []
        self.hooks = []
        self.commands = []

    def register_tool(self, **registration):
        self.tools.append(registration)

    def register_hook(self, name, callback):
        self.hooks.append((name, callback))

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands.append((name, handler))


class ProfileIsolationTests(unittest.TestCase):
    def test_hooks_and_mutation_resolve_home_and_profile_at_invocation_time(self):
        from hermes_constants import reset_hermes_home_override, set_hermes_home_override

        with tempfile.TemporaryDirectory(prefix="hermes-verify-profile-isolation-") as raw:
            root = Path(raw)
            bootstrap = root / "bootstrap"
            home_a = root / "profiles" / "alpha"
            home_b = root / "profiles" / "beta"
            for home in (bootstrap, home_a, home_b):
                home.mkdir(parents=True, exist_ok=True)
            context = DynamicContext()
            with patch.dict(os.environ, {"HERMES_HOME": str(bootstrap)}):
                plugin = load_plugin("hermes_mantle_profile_plugin")
                plugin.register(context)
                hooks = dict(context.hooks)
                discovery = next(
                    row["handler"]
                    for row in context.tools
                    if row["name"] == "mantle_record_discovery"
                )

                token = set_hermes_home_override(home_a)
                try:
                    context.profile_name = "alpha"
                    self.assertIsNone(hooks["on_session_start"](session_id="a-session"))
                    result_a = json.loads(discovery({"idea": "alpha-only"}))
                finally:
                    reset_hermes_home_override(token)

                token = set_hermes_home_override(home_b)
                try:
                    context.profile_name = "beta"
                    self.assertIsNone(hooks["on_session_start"](session_id="b-session"))
                    result_b = json.loads(discovery({"idea": "beta-only"}))
                finally:
                    reset_hermes_home_override(token)

            self.assertTrue(result_a["success"])
            self.assertTrue(result_b["success"])
            path_a = home_a / "mantle" / "organisms" / "alpha"
            path_b = home_b / "mantle" / "organisms" / "beta"
            self.assertTrue((path_a / "organism.json").is_file())
            self.assertTrue((path_b / "organism.json").is_file())
            self.assertFalse((bootstrap / "mantle" / "organisms" / "bootstrap").exists())

            from hermes_mantle_profile_plugin.mantle_addon.body import ResidentBodyFactory
            from hermes_mantle_profile_plugin.mantle_addon.config import ResidentConfig

            config = ResidentConfig.from_mapping({})
            alpha = ResidentBodyFactory(config, hermes_home=home_a).get_or_create("alpha").organism
            beta = ResidentBodyFactory(config, hermes_home=home_b).get_or_create("beta").organism
            alpha_text = json.dumps(alpha.memory.recall("discoveries"))
            beta_text = json.dumps(beta.memory.recall("discoveries"))
            self.assertIn("alpha-only", alpha_text)
            self.assertNotIn("beta-only", alpha_text)
            self.assertIn("beta-only", beta_text)
            self.assertNotIn("alpha-only", beta_text)


if __name__ == "__main__":
    unittest.main()
