#!/usr/bin/env python3
"""Recreate and certify the local Files.AppAI nest from its generated spore."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "src"
SPORE = HERE / "Files.AppAI.spore.png"
NEST = HERE / "Files.AppAI.nest"
RECEIPT = HERE / "certification_receipt.json"

sys.path.insert(0, str(SRC))

from mantle import phenotype, spore  # noqa: E402
from mantle.audits import stage1  # noqa: E402
from mantle.core.organism import Organism  # noqa: E402
from mantle.hatchery import hatch  # noqa: E402
from mantle.lifecycle import LifecycleAction, LifecycleAuthorization  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def certify() -> dict:
    if NEST.parent != HERE or NEST.name != "Files.AppAI.nest":
        raise RuntimeError("refusing to remove an unexpected nest path")
    if NEST.exists():
        shutil.rmtree(NEST)

    carrier = spore.verify_spore(str(SPORE))
    if not carrier["ok"]:
        raise RuntimeError("spore verification failed: %s" % carrier["problems"])
    auth = LifecycleAuthorization.issue(LifecycleAction.HATCH, str(SPORE), str(NEST))
    born = hatch(str(SPORE), out_dir=str(NEST), warmup_beats=3, authorization=auth)
    organism = born["organism"]
    passed, evidence = stage1.run(organism, include_invariants=False)
    face = phenotype.open_face(organism, "origin")
    expected_source = (HERE / "index.html").read_text(encoding="utf-8")
    if face["source"] != expected_source:
        raise RuntimeError("sealed origin face differs from examples/files_appai/index.html")
    if not passed or not born["report"]["certified"]:
        raise RuntimeError("Stage-1 gate failed: %s" % evidence["fails"])

    persisted = Organism.load(str(NEST), verify_seals=True)
    source_receipts = [
        entry["content"]["sporeagent_source"]
        for entry in persisted.memory.recall("facts")
        if isinstance(entry.get("content"), dict)
        and "sporeagent_source" in entry["content"]
    ]
    required_files = ("body.json", "organism.json", "self_seal.json",
                      "face.png", "hatch_report.json")
    missing = [name for name in required_files if not (NEST / name).is_file()]
    if missing:
        raise RuntimeError("nest is missing persisted birth evidence: %s" % missing)
    if len(source_receipts) != 1:
        raise RuntimeError("persisted source lifecycle receipt is missing or duplicated")

    gate = next(stage["gate"] for stage in born["report"]["stages"] if "gate" in stage)
    receipt = {
        "appai": organism.body.identity_name(),
        "certified": True,
        "stage1_rows": gate["rows"],
        "stage1_failures": gate["fails"],
        "carrier_checks": len(carrier["checks"]),
        "carrier_parity": carrier["integrity"]["parity_status"],
        "carrier_fingerprint": carrier["integrity"]["fingerprint_status"],
        "spore_sha256": _sha256(SPORE.read_bytes()),
        "origin_face_sha256": _sha256(face["source"].encode("utf-8")),
        "origin_face_matches_source": True,
        "origin_controls": len(face["controls"]),
        "mind": "dormant",
        "model_calls": 0,
        "network_required": False,
        "host_write_limb": False,
        "persisted_files": list(required_files),
        "source_receipt_persisted": True,
        "nest": NEST.name,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    print(json.dumps(certify(), indent=2))
