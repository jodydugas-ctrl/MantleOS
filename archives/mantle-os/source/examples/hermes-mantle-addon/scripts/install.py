#!/usr/bin/env python3
"""Install this example as a user-scoped Hermes plugin."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Sequence


ADDON_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "mantle-os"


def _ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {".git", ".runtime", "__pycache__", ".pytest_cache"}
    return {name for name in names if name in ignored or name.endswith(".pyc")}


def install_addon(source: Path, hermes_home: Path, *, force: bool = False) -> Path:
    """Copy ``source`` into ``HERMES_HOME/plugins/mantle-os`` safely."""
    source = source.resolve(strict=True)
    plugins = hermes_home.expanduser().resolve() / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    target = plugins / PLUGIN_NAME
    if target.exists() and not force:
        raise FileExistsError(
            f"{target} already exists; pass --force to replace this plugin"
        )

    staging = Path(tempfile.mkdtemp(prefix=f".{PLUGIN_NAME}-install-", dir=plugins))
    backup: Path | None = None
    try:
        shutil.copytree(source, staging, dirs_exist_ok=True, ignore=_ignore)
        runtime = staging / "runtime" / "mantle"
        if not runtime.is_dir():
            repo_runtime = source.parents[1] / "src" / "mantle"
            if not repo_runtime.is_dir():
                raise FileNotFoundError(
                    "cannot stage the Mantle runtime: neither "
                    f"{runtime} nor {repo_runtime} exists"
                )
            shutil.copytree(repo_runtime, runtime, ignore=_ignore)
        if target.exists():
            backup = Path(
                tempfile.mkdtemp(prefix=f".{PLUGIN_NAME}-backup-", dir=plugins)
            )
            backup.rmdir()
            os.replace(target, backup)
        os.replace(staging, target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            os.replace(backup, target)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
    return target


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install and enable the local Hermes Mantle addon demo."
    )
    parser.add_argument(
        "--hermes-home",
        type=Path,
        default=None,
        help="target Hermes home (default: HERMES_HOME or ~/.hermes)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing mantle-os plugin installation",
    )
    parser.add_argument(
        "--no-enable",
        action="store_true",
        help="install without enabling the plugin in Hermes config",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    home = args.hermes_home or Path(
        os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
    )
    target = install_addon(ADDON_ROOT, home, force=args.force)
    if not args.no_enable:
        environment = os.environ.copy()
        environment["HERMES_HOME"] = str(home.expanduser().resolve())
        subprocess.run(
            [
                "hermes",
                "plugins",
                "enable",
                PLUGIN_NAME,
                "--no-allow-tool-override",
            ],
            env=environment,
            check=True,
        )
    print(f"Installed {PLUGIN_NAME} at {target}")
    if args.no_enable:
        print(f"Enable it with: hermes plugins enable {PLUGIN_NAME}")
    else:
        print("Start Hermes and run: /mind <prompt>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
