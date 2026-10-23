"""Refresh the developmental registry from the current source hashes."""
from __future__ import annotations

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from daemon.development import RUNTIME_CONTRACT, file_hash


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "genome/organ_registry.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["runtime"] = RUNTIME_CONTRACT
    for record in registry["organs"].values():
        record["sha256"] = file_hash(root / record["path"])
    path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
