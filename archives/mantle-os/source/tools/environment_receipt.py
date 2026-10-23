#!/usr/bin/env python3
"""Write a non-secret environment receipt for certification evidence."""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


PACKAGES = (
    "mantle-os",
    "cryptography",
    "pillow",
    "pyyaml",
    "tree-sitter-language-pack",
)


def _commit() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    value = (proc.stdout or "").strip()
    return value if proc.returncode == 0 else "unavailable"


def build_receipt() -> dict:
    from mantle.certify import invariant_registry_fingerprint

    versions = {}
    for package in PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return {
        "schema": "mantle-environment-receipt-v1",
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": Path(sys.executable).name,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "source_commit": _commit(),
        "invariant_registry": invariant_registry_fingerprint(),
        "packages": versions,
        "ci": {
            "provider": "github-actions" if os.environ.get("GITHUB_ACTIONS") else "local",
            "runner_os": os.environ.get("RUNNER_OS", ""),
            "runner_arch": os.environ.get("RUNNER_ARCH", ""),
        },
    }


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python tools/environment_receipt.py <output.json>")
        return 2
    path = Path(args[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_receipt(), indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
