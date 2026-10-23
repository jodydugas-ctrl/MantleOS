"""Plug-and-play local installer for the Hermes Mantle addon."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = PROJECT_ROOT / "scripts" / "install.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("mantle_addon_installer", INSTALLER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallerTests(unittest.TestCase):
    def test_install_copies_plugin_without_runtime_debris(self):
        installer = load_installer()
        with tempfile.TemporaryDirectory(prefix="mantle-install-test-") as directory:
            home = Path(directory) / "hermes-home"

            target = installer.install_addon(PROJECT_ROOT, home)

            self.assertEqual(home / "plugins" / "mantle-os", target)
            self.assertTrue((target / "plugin.yaml").is_file())
            self.assertTrue((target / "mantle_addon" / "runtime.py").is_file())
            self.assertFalse((target / ".runtime").exists())
            self.assertFalse(any(target.rglob("__pycache__")))

    def test_existing_install_requires_explicit_force(self):
        installer = load_installer()
        with tempfile.TemporaryDirectory(prefix="mantle-install-test-") as directory:
            home = Path(directory) / "hermes-home"
            target = home / "plugins" / "mantle-os"
            target.mkdir(parents=True)
            marker = target / "keep-me"
            marker.write_text("existing", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                installer.install_addon(PROJECT_ROOT, home)

            self.assertEqual("existing", marker.read_text(encoding="utf-8"))
            replaced = installer.install_addon(PROJECT_ROOT, home, force=True)
            self.assertEqual(target, replaced)
            self.assertFalse(marker.exists())
            self.assertTrue((target / "plugin.yaml").is_file())

    def test_cli_enables_without_requesting_builtin_tool_override(self):
        installer = load_installer()
        with tempfile.TemporaryDirectory(prefix="mantle-install-test-") as directory:
            home = Path(directory) / "hermes-home"
            with patch.object(installer.subprocess, "run") as run:
                result = installer.main(["--hermes-home", str(home)])

            self.assertEqual(0, result)
            command = run.call_args.args[0]
            self.assertEqual(
                [
                    "hermes",
                    "plugins",
                    "enable",
                    "mantle-os",
                    "--no-allow-tool-override",
                ],
                command,
            )


if __name__ == "__main__":
    unittest.main()
