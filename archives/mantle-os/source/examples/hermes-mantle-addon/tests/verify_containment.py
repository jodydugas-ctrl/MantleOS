#!/usr/bin/env python3
"""Run the reproducible containment audit against an isolated resident."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.config import ResidentConfig  # noqa: E402
from mantle_addon.containment import run_containment  # noqa: E402
from mantle_addon.runtime import ResidentRuntime  # noqa: E402
from schemas import MANTLE_RECORD_DISCOVERY  # noqa: E402


def _load_tool_handler():
    path = PROJECT_ROOT / "tools.py"
    spec = importlib.util.spec_from_file_location(
        "hermes_mantle_containment_verifier_tools", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.mantle_record_discovery


def main() -> int:
    mantle_record_discovery = _load_tool_handler()
    with tempfile.TemporaryDirectory(
        prefix="hermes-containment-verify-"
    ) as scratch:
        scope = Path(scratch)
        sentinel = scope / "host-sentinel.txt"
        sentinel.write_text("must remain unchanged", encoding="utf-8")
        config = ResidentConfig.from_mapping(
            {"storage_root": str(scope / "resident-storage")}
        )
        runtime = ResidentRuntime(config, profile_id="containment-audit")
        receipt = run_containment(
            runtime,
            MANTLE_RECORD_DISCOVERY,
            lambda args: mantle_record_discovery(args, runtime=runtime),
            scope_root=scope,
        )
        assert sentinel.read_text(encoding="utf-8") == "must remain unchanged"
        print(json.dumps(receipt.to_dict(), sort_keys=True))
        return 0 if receipt.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
