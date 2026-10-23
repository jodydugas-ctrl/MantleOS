#!/usr/bin/env python3
"""Deterministic certification receipts for an actual persisted Mantle nest."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from typing import Any, Dict, List

from . import __version__
from . import paths
from .audits import invariants as _inv
from .audits import stage1 as _stage1
from .core.audit import FAIL
from .core.organism import Organism
from .core.persist import atomic_write_json


SCHEMA = "mantle-application-certificate-v1"


class CertificationError(Exception):
    """The requested nest could not produce a valid application certificate."""


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    ).encode("utf-8")


def _source_commit() -> str:
    explicit = os.environ.get("MANTLE_SOURCE_COMMIT", "").strip()
    if explicit:
        return explicit
    try:
        proc = subprocess.run(
            ["git", "-C", paths.REPO_ROOT, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    value = (proc.stdout or "").strip().lower()
    return value if proc.returncode == 0 and len(value) == 40 else "unavailable"


def _target_files(directory: str) -> List[Dict[str, Any]]:
    names = ["body.json", "organism.json", "self_seal.json", "resident_protocol.json"]
    names.extend(sorted(
        name for name in os.listdir(directory)
        if name.startswith("gen") and name.endswith(".vcw")
    ))
    rows = []
    for name in names:
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as stream:
            data = stream.read()
        rows.append({"path": name.replace("\\", "/"),
                     "bytes": len(data), "sha256": _sha256(data)})
    return rows


def invariant_registry_fingerprint() -> str:
    """Fingerprint the executable registry without hard-coding its population."""
    rows = [
        {
            "code": spec.code,
            "title": spec.title,
            "guarantee_id": spec.guarantee_id,
            "added": spec.added,
            "concern": spec.concern,
        }
        for spec in _inv.REGISTRY
    ]
    return _sha256(_canonical(rows))


def certify_nest(directory: str, *, include_invariants: bool = True) -> Dict[str, Any]:
    """Load and certify one real nest; return a deterministic signed receipt."""
    directory = os.path.abspath(directory)
    required = ("body.json", "organism.json")
    missing = [name for name in required
               if not os.path.isfile(os.path.join(directory, name))]
    if missing:
        raise CertificationError("not a Mantle nest; missing %s"
                                 % ", ".join(missing))
    target_files = _target_files(directory)
    protocol_path = os.path.join(directory, "resident_protocol.json")
    try:
        with open(protocol_path, "r", encoding="utf-8") as handle:
            protocol = json.load(handle).get("protocol")
    except (OSError, ValueError, AttributeError):
        protocol = None
    if protocol != "mantle-resident-v2":
        raise CertificationError(
            "resident protocol drift: explicit mantle-resident-v2 declaration required"
        )
    try:
        org = Organism.load(directory, verify_seals=True)
    except Exception as exc:
        raise CertificationError("nest load/integrity check failed: %s: %s"
                                 % (type(exc).__name__, exc))

    preexisting_integrity_events = [
        event for event in org.immune.log
        if event.get("kind") in ("autoimmune_risk", "ancestor_tamper")
    ]
    passed, evidence = _stage1.run(org, include_invariants=False)
    stage1_rows = evidence["substrate_rows"] + evidence["mesh_rows"]
    invariant_rows = _inv.run_all() if include_invariants else []
    invariant_ok = all(row["ok"] for row in invariant_rows)
    invariant_failures = []
    for row in invariant_rows:
        if row.get("ok"):
            continue
        name = str(row.get("name") or row.get("code") or "unknown")
        detail = " ".join(str(row.get("detail") or "no detail").split())[:320]
        invariant_failures.append("%s [%s]" % (name, detail))
    verify_problems = org.prime.verify()
    failed_codes = [row["code"] for row in stage1_rows if row["result"] == FAIL]
    if preexisting_integrity_events:
        failed_codes.append("identity/seal-integrity")
    if verify_problems:
        failed_codes.append("prime-verify")
    if include_invariants and not invariant_ok:
        failed_codes.extend("repository-invariant:%s" % name
                            for name in invariant_failures)

    unsigned = {
        "schema": SCHEMA,
        "subject": {
            "identity": org.body.identity_name(),
            "prime_generation": org.prime.generation,
            "ancestral_generations": [cube.generation for cube in org.ancestral],
            "key_fingerprint": org.body.key_fingerprint,
        },
        "implementation": {
            "mantle_version": __version__,
            "source_commit": _source_commit(),
            "invariant_registry": invariant_registry_fingerprint(),
        },
        "target": {
            "files": target_files,
            "fingerprint": _sha256(_canonical(target_files)),
        },
        "stage1": {
            "passed": bool(passed and not failed_codes),
            "rows": stage1_rows,
            "failed_codes": failed_codes,
            "prime_verify": verify_problems,
        },
        "repository_invariants": {
            "executed": bool(include_invariants),
            "passed": bool(invariant_ok),
            "results": invariant_rows,
        },
        "authority": {
            "technical_evidence_only": True,
            "mind_fusion_authorized": False,
        },
    }
    receipt_hash = _sha256(_canonical(unsigned))
    signature = org.body.sign(_canonical(unsigned)) if org.body.has_key else None
    receipt = {
        **unsigned,
        "receipt": {
            "sha256": receipt_hash,
            "signature": signature,
            "signature_algorithm": "HMAC-SHA256" if signature else None,
            "signed_by": org.body.key_fingerprint if signature else None,
        },
    }
    if failed_codes:
        raise CertificationError("application certification blocked: %s"
                                 % ", ".join(failed_codes))
    return receipt


def write_certificate(receipt: Dict[str, Any], path: str) -> str:
    path = os.path.abspath(path)
    atomic_write_json(path, receipt)
    return path
