import json
import importlib.util
from pathlib import Path
import shutil
import sys
from types import ModuleType
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PATH = PROJECT_ROOT / "tools.py"
PLUGIN_PATH = PROJECT_ROOT / "__init__.py"


def load_module(name: str, path: Path):
    assert path.exists(), f"{path.name} production module does not exist yet"
    package_locations = [str(path.parent)] if path.name == "__init__.py" else None
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=package_locations
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
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
        self.commands.append(
            {
                "name": name,
                "handler": handler,
                "description": description,
                "args_hint": args_hint,
            }
        )


def shipped_mantle_version() -> str:
    """The version literal of the runtime the addon actually loads (never hardcoded)."""
    import re
    tools = load_module("hermes_mantle_tools_version_probe", TOOLS_PATH)
    source = (tools._MANTLE_PACKAGE / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', source).group(1)


class MantleStatusTests(unittest.TestCase):
    def test_status_reports_vendored_mantle_capabilities(self):
        tools = load_module("hermes_mantle_tools", TOOLS_PATH)

        result = json.loads(tools.mantle_status({}))

        self.assertTrue(result["success"])
        self.assertEqual(shipped_mantle_version(), result["mantle_version"])
        self.assertEqual("true", result["mantle_scope"])
        self.assertEqual("vendored", result["source"])
        self.assertTrue({"audit", "prove", "check", "assimilate"}.issubset(result["commands"]))

    def test_status_ignores_preloaded_nonvendored_mantle_modules(self):
        tools = load_module("hermes_mantle_tools_isolation", TOOLS_PATH)
        sentinel_mantle = ModuleType("mantle")
        setattr(sentinel_mantle, "__version__", "999.0-fake")
        sentinel_cli = ModuleType("mantle.cli")
        setattr(sentinel_cli, "known_commands", lambda: ["fake-command"])
        originals = {
            name: sys.modules.get(name)
            for name in ("mantle", "mantle.cli")
        }
        sys.modules["mantle"] = sentinel_mantle
        sys.modules["mantle.cli"] = sentinel_cli
        try:
            result = json.loads(tools.mantle_status({}))
        finally:
            for name, original in originals.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original

        self.assertTrue(result["success"])
        self.assertEqual(shipped_mantle_version(), result["mantle_version"])
        self.assertNotIn("fake-command", result["commands"])
        self.assertIn("audit", result["commands"])


class MantleDiscoveryToolTests(unittest.TestCase):
    runtime_root = PROJECT_ROOT / ".runtime" / "test-discovery-tool"

    def setUp(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)
        sys.path.insert(0, str(PROJECT_ROOT))
        from mantle_addon.config import ResidentConfig
        from mantle_addon.runtime import (
            DISCOVERY_CONTROL_ID,
            MAX_DISCOVERY_CHARS,
            ResidentRuntime,
        )

        self.control_id = DISCOVERY_CONTROL_ID
        self.max_chars = MAX_DISCOVERY_CHARS
        config = ResidentConfig.from_mapping(
            {"storage_root": str(self.runtime_root)}
        )
        self.runtime = ResidentRuntime(config, profile_id="default")
        self.tools = load_module("hermes_mantle_mutating_tools", TOOLS_PATH)

    def tearDown(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)
        if sys.path and sys.path[0] == str(PROJECT_ROOT):
            sys.path.pop(0)

    def _call(self, idea):
        return json.loads(
            self.tools.mantle_record_discovery(
                {"idea": idea}, runtime=self.runtime
            )
        )

    def test_records_only_an_inferred_discovery_through_limbs(self):
        idea = "The host may benefit from a bounded maintenance window."
        organism = self.runtime.organism
        facts_before = organism.memory.recall("facts")
        special_before = list(organism.body.category("special"))

        result = self._call(idea)

        self.assertTrue(result["success"])
        self.assertTrue(result["attempted"])
        self.assertTrue(result["durable"])
        self.assertFalse(result["verified"])
        self.assertEqual("inferred", result["classification"])
        discoveries = organism.memory.recall("discoveries")
        self.assertEqual(idea, discoveries[-1]["content"]["idea"])
        self.assertFalse(discoveries[-1]["verified"])
        self.assertEqual("inferred", discoveries[-1]["confidence"])
        self.assertEqual(facts_before, organism.memory.recall("facts"))
        self.assertEqual(special_before, organism.body.category("special"))
        self.assertNotIn(idea, json.dumps(result, sort_keys=True))

    def test_control_is_mapped_on_both_senses_and_limbs(self):
        organism = self.runtime.organism

        self.assertIn(self.control_id, organism.senses.surface_map)
        self.assertIn(self.control_id, organism.limbs.bridges)
        descriptor = organism.senses.surface_map[self.control_id]
        self.assertEqual("discoveries", descriptor["band"])
        self.assertFalse(descriptor["verified"])
        self.assertTrue(organism.limbs.surface_covered())

    def test_rejects_empty_oversize_and_control_character_inputs(self):
        for idea in ("   ", "x" * (self.max_chars + 1), "bad\x00idea"):
            with self.subTest(idea=repr(idea[:20])):
                result = self._call(idea)
                self.assertFalse(result["success"])
                self.assertTrue(result["attempted"])
                self.assertEqual("ValueError", result["reason"])

        self.assertEqual([], self.runtime.organism.memory.recall("discoveries"))

    def test_success_survives_verified_reload_with_body_authored_proof(self):
        idea = "Reconstruction should retain this inferred discovery."
        self.assertTrue(self._call(idea)["success"])

        from mantle_addon.config import ResidentConfig
        from mantle_addon.runtime import ResidentRuntime

        reloaded = ResidentRuntime(
            ResidentConfig.from_mapping(
                {"storage_root": str(self.runtime_root)}
            ),
            profile_id="default",
        ).organism
        discoveries = reloaded.memory.recall("discoveries")
        self.assertEqual(idea, discoveries[-1]["content"]["idea"])
        proof_entries = [
            entry
            for entry in reloaded.prime.read("brain")
            if isinstance(entry.get("content"), dict)
            and isinstance(entry["content"].get("action_proof"), dict)
        ]
        proof_entry = next(
            entry
            for entry in proof_entries
            if entry["content"]["action_proof"].get("control")
            == self.control_id
        )
        proof = proof_entry["content"]["action_proof"]
        self.assertEqual("BODY", proof_entry["author"])
        self.assertEqual("BODY", proof_entry["authorship"])
        self.assertTrue(proof["ok"])
        self.assertEqual("ControlBridge", proof["method"])


class PluginRegistrationTests(unittest.TestCase):
    @staticmethod
    def _load_plugin():
        sys.path.insert(0, str(PROJECT_ROOT))
        try:
            return load_module("hermes_mantle_addon", PLUGIN_PATH)
        finally:
            sys.path.remove(str(PROJECT_ROOT))

    def test_register_exposes_bounded_mantle_tools(self):
        plugin = self._load_plugin()
        context = RecordingContext()

        plugin.register(context)

        self.assertEqual(2, len(context.tools))
        registrations = {row["name"]: row for row in context.tools}
        status = registrations["mantle_status"]
        discovery = registrations["mantle_record_discovery"]
        self.assertEqual("mantle", status["toolset"])
        self.assertEqual("mantle_status", status["schema"]["name"])
        self.assertIs(status["handler"], plugin.mantle_status)
        self.assertEqual("mantle", discovery["toolset"])
        self.assertEqual(
            "mantle_record_discovery", discovery["schema"]["name"]
        )
        self.assertIs(
            discovery["handler"].func,
            plugin.mantle_record_discovery,
        )
        self.assertEqual(
            set(plugin.OBSERVER_HOOKS),
            {name for name, _callback in context.hooks},
        )
        registry_ids = {
            id(callback.func.__self__) for _name, callback in context.hooks
        }
        self.assertEqual(1, len(registry_ids))
        self.assertIn(
            id(discovery["handler"].keywords["runtime_provider"].__self__),
            registry_ids,
        )

    def test_register_exposes_interactive_mind_command(self):
        plugin = self._load_plugin()
        context = RecordingContext()

        plugin.register(context)

        self.assertEqual(1, len(context.commands))
        command = context.commands[0]
        self.assertEqual("mind", command["name"])
        self.assertEqual("<prompt>", command["args_hint"])
        self.assertIn("AppAI", command["description"])
        registry = context.hooks[0][1].func.__self__
        runtime = registry.current()
        with patch.object(runtime, "ask_mind", return_value="resident answer") as ask:
            result = command["handler"]("  user question  ")

        self.assertEqual("AppAI MIND › resident answer", result)
        ask.assert_called_once_with("user question")
        self.assertEqual("Usage: /mind <prompt>", command["handler"]("   "))
        with patch.object(
            runtime,
            "ask_mind",
            side_effect=RuntimeError("private provider detail"),
        ):
            unavailable = command["handler"]("hello")
        self.assertIn("AppAI MIND is unavailable", unavailable)
        self.assertNotIn("private provider detail", unavailable)

    def test_register_loads_active_profile_resident_config(self):
        plugin = self._load_plugin()
        context = RecordingContext()
        configured = {
            "plugins": {
                "entries": {
                    "mantle-os": {
                        "config": {
                            "max_event_chars": 777,
                            "checkpoint_each_turn": False,
                        },
                        "llm": {"allowed_models": ["ignored-by-body-config"]},
                    }
                }
            }
        }

        with patch("hermes_cli.config.load_config", return_value=configured):
            plugin.register(context)
            registry = context.hooks[0][1].func.__self__
            runtime = registry.current()

        self.assertEqual(777, runtime.config.max_event_chars)
        self.assertFalse(runtime.config.checkpoint_each_turn)


if __name__ == "__main__":
    unittest.main()
