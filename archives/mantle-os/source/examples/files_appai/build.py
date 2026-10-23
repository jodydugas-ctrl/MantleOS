#!/usr/bin/env python3
"""Regenerate Files.AppAI artifacts from declarative local inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "src"
OUTPUT = ROOT / "examples" / "files_appai" / "Files.AppAI.spore.png"
RECEIPT = HERE / "build_receipt.json"
STALE_GENERATED = (
    HERE / "carrier-smoke.png",
    HERE / "embedded_spore_min.py",
    HERE / "legacy-spore-state.json",
)

sys.path.insert(0, str(SRC))

from mantle import spore  # noqa: E402
from mantle.hatchery import validate_germ  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    germ = json.loads((HERE / "germ.json").read_text(encoding="utf-8"))
    germ["face"] = {
        "name": "origin",
        "kind": "html",
        "entry": "index.html",
        "source": (HERE / "index.html").read_text(encoding="utf-8"),
        "controls": list(germ.get("controls", [])),
        "capabilities": {
            "network": False,
            "model": False,
            "host_source_write": False,
            "clipboard_write": True,
            "local_append_only_ledger": True,
        },
    }
    germ = validate_germ(germ)

    if OUTPUT.exists():
        OUTPUT.unlink()
    spore.pack_germ(
        germ,
        str(OUTPUT),
        source={
            "kind": "git",
            "url": "https://github.com/files-community/Files",
            "ref": "7aa516aca1a97e08ffd74a5cc79a91d00e828a2c",
            "notes": "commit-bound source evidence; no network access during regeneration",
        },
    )

    verification = spore.verify_spore(str(OUTPUT))
    if not verification["ok"]:
        OUTPUT.unlink(missing_ok=True)
        raise RuntimeError("generated spore failed verification: %s"
                           % verification["problems"])
    decoded = spore.read_spore(str(OUTPUT))
    receipt = {
        "artifact": OUTPUT.name,
        "spore_format": decoded["metadata"]["Spore-Format"],
        "sha256": _sha256(OUTPUT),
        "full_lane_fingerprint": decoded["header"]["payload_fingerprint"],
        "statement_count": decoded["integrity"]["statement_count"],
        "parity_status": decoded["integrity"]["parity_status"],
        "fingerprint_status": decoded["integrity"]["fingerprint_status"],
        "verification_checks": len(verification["checks"]),
        "verification_passed": verification["ok"],
        "source_commit": "7aa516aca1a97e08ffd74a5cc79a91d00e828a2c",
        "generated_from": ["examples/files_appai/germ.json",
                           "examples/files_appai/index.html"],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    for path in STALE_GENERATED:
        path.unlink(missing_ok=True)
    return receipt


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
