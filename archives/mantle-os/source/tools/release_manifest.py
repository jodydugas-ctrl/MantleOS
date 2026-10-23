"""Generate a non-self-referential Mantle 2 release manifest."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--receipt", action="append", default=[])
    args = parser.parse_args(argv)
    dist = args.dist.resolve()
    out = args.out.resolve()
    if out == dist or dist in out.parents:
        raise ValueError("release manifest must live outside the distributions it hashes")
    artifacts = []
    for path in sorted(item for item in dist.iterdir() if item.is_file()):
        artifacts.append({"name": path.name, "bytes": path.stat().st_size,
                          "sha256": sha256(path)})
    if not artifacts:
        raise ValueError("no distribution artifacts found")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    receipts = []
    for value in args.receipt:
        path = Path(value).resolve()
        receipts.append({"name": path.name, "sha256": sha256(path)})
    manifest = {
        "schema": "mantle-release-manifest-v1",
        "release": "2.0.0rc1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": commit,
        "schemas": {
            "spore_carrier": "spore-png-v2",
            "germ": "mantle-germ-v2",
            "host_evidence": "mantle-host-evidence-v3",
            "gui_nerve_coverage": "mantle-gui-nerve-coverage-v3",
            "resident_protocol": "mantle-resident-v2",
            "lifecycle_authorization": "mantle-lifecycle-authorization-v1",
        },
        "artifacts": artifacts,
        "test_receipts": receipts,
        "authority": "repository and artifact evidence only; not current runtime authority",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
