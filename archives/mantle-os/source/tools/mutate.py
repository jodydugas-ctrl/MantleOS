#!/usr/bin/env python3
"""Targeted mutation sweep for Mantle's load-bearing security guards.

Each mutant is applied to an isolated copy of ``src/`` and challenged by the smallest
live invariant that should kill it.  A surviving mutant is a test failure.  This is not a
general-purpose mutation engine; it is a deterministic catalogue of doctrine-critical
guard deletions.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import List


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Mutant:
    id: str
    file: str
    old: str
    new: str
    catcher: str


MUTANTS = [
    Mutant(
        "primer-rebirth",
        "src/mantle/core/body.py",
        "        if self._primer_sealed:\n"
        "            raise PermissionError(\"Primer is immutable post-birth\")",
        "        if False and self._primer_sealed:\n"
        "            raise PermissionError(\"Primer is immutable post-birth\")",
        "t_primer_immutable",
    ),
    Mutant(
        "senses-redaction",
        "src/mantle/organs/senses.py",
        "        entry = make_entry(redact({\"signal\": signal, \"class\": cls}),",
        "        entry = make_entry({\"signal\": signal, \"class\": cls},",
        "t_secret_boundary_sense",
    ),
    Mutant(
        "immune-redaction",
        "src/mantle/organs/immune.py",
        "        evt = {\"kind\": kind, \"detail\": redact(detail)}",
        "        evt = {\"kind\": kind, \"detail\": detail}",
        "t_secret_boundary_immune",
    ),
    Mutant(
        "ancestor-append",
        "src/mantle/vcw/cube.py",
        "    def append(self, band: str, value: Any) -> Any:\n"
        "        if self.sealed:",
        "    def append(self, band: str, value: Any) -> Any:\n"
        "        if False and self.sealed:",
        "t_ancestral_readonly",
    ),
    Mutant(
        "entry-hash-verify",
        "src/mantle/vcw/cube.py",
        "                for idx in self.band_layers.get(band, []):\n"
        "                    for e in self.layer_content(idx):\n"
        "                        if isinstance(e, dict) and \"hash\" in e and entry_hash(e) != e[\"hash\"]:",
        "                for idx in self.band_layers.get(band, []):\n"
        "                    for e in self.layer_content(idx):\n"
        "                        if isinstance(e, dict) and \"hash\" in e and False and entry_hash(e) != e[\"hash\"]:",
        "t_authorship_in_hash",
    ),
    Mutant(
        "self-mac-verify",
        "src/mantle/core/body.py",
        "        return hmac.compare_digest(self.sign(data), mac)",
        "        return True",
        "t_self_verify_and_reject_foreign",
    ),
    Mutant(
        "exec-integrity",
        "src/mantle/vcw/drivers.py",
        "        if code_hash(content[\"code\"]) != content[\"code_hash\"]:",
        "        if False and code_hash(content[\"code\"]) != content[\"code_hash\"]:",
        "t_exec_integrity",
    ),
    Mutant(
        "exec-capability",
        "src/mantle/vcw/drivers.py",
        "            if not asked <= allowed:",
        "            if False and not asked <= allowed:",
        "t_exec_capability",
    ),
    Mutant(
        "exec-provenance",
        "src/mantle/vcw/drivers.py",
        "                and not provenance_is_trusted(content.get(\"provenance\", {}))",
        "                and False and not provenance_is_trusted(content.get(\"provenance\", {}))",
        "t_exec_trust_foreign",
    ),
    Mutant(
        "public-trust-grant",
        "src/mantle/vcw/drivers.py",
        "    if unknown:\n"
        "        raise CapabilityError(\"unknown/reserved exec grant key(s): %s\"",
        "    if False and unknown:\n"
        "        raise CapabilityError(\"unknown/reserved exec grant key(s): %s\"",
        "t_public_grant_cannot_mint_trust",
    ),
    Mutant(
        "mind-write-surface",
        "src/mantle/mind/containment.py",
        "WRITE_SURFACE = (\"thoughts\", \"brain\")",
        "WRITE_SURFACE = (\"thoughts\", \"brain\", \"facts\")",
        "t_mind_write_surface",
    ),
    Mutant(
        "grimoire-zero-head",
        "src/mantle/vcw/grimoire_editions/v010.py",
        "    procedure = not heads",
        "    procedure = False",
        "t_grimoire_v010_step_only",
    ),
    Mutant(
        "grimoire-any-zero-head",
        "src/mantle/vcw/grimoire_editions/v010.py",
        "    if procedure and any(role not in STEP_ROLES for role in lead_roles):",
        "    if False and any(role not in STEP_ROLES for role in lead_roles):",
        "t_grimoire_v010_step_only",
    ),
    Mutant(
        "grimoire-default-force-law",
        "src/mantle/vcw/grimoire_editions/v010.py",
        "        effective_force = \"INHERIT\"",
        "        effective_force = \"LAW\"",
        "t_grimoire_v010_missing_container",
    ),
    Mutant(
        "grimoire-assumed-inferred",
        "src/mantle/vcw/grimoire_editions/v010.py",
        "EVIDENCE = legacy.EVIDENCE\nFORCE = legacy.FORCE",
        "EVIDENCE = dict(legacy.EVIDENCE)\nEVIDENCE[0x07] = \"INFERRED\"\nFORCE = legacy.FORCE",
        "t_grimoire_v010_evidence_label",
    ),
    Mutant(
        "grimoire-placement-adoption",
        "src/mantle/vcw/grimoire_editions/v010.py",
        "    governing = adoption_policy == \"adopted\" and not unknowns",
        "    governing = True",
        "t_grimoire_v010_quote_inert",
    ),
    Mutant(
        "grimoire-v09-current-default",
        "src/mantle/vcw/grimoire_editions/registry.py",
        "    edition = get_edition(profile)",
        "    edition = get_edition(\"grimoire-v0.10\")",
        "t_grimoire_v010_v09_frozen",
    ),
    Mutant(
        "grimoire-measured-without-fingerprint",
        "src/mantle/vcw/grimoire_editions/v010.py",
        "    elif claim_tamper_evidence:\n        fingerprint_status = \"missing\"\n        full_lane_integrity = \"unmeasured\"",
        "    elif claim_tamper_evidence:\n        fingerprint_status = \"missing\"\n        full_lane_integrity = \"measured\"",
        "t_grimoire_v010_integrity",
    ),
    Mutant(
        "grimoire-skip-independent-compare",
        "tools/grimoire_tool.py",
        "    production = json.loads(proc.stdout)",
        "    production = []",
        "t_grimoire_v010_independent_compare",
    ),
    Mutant(
        "grimoire-book-parity-byte",
        "documents/grimoire/editions/grimoire-v0.10.md",
        "76010808 30210000 85400000 5b2c0000 da7f2b0a",
        "76010808 30210000 85400000 5b2c0000 da7f2b0b",
        "t_grimoire_v010_independent_compare",
    ),
    Mutant(
        "grimoire-composition-count",
        "documents/grimoire/editions/grimoire-v0.10.md",
        "This edition composes 295 named concept rows.",
        "This edition composes 296 named concept rows.",
        "t_grimoire_v010_counts",
    ),
    Mutant(
        "spore-png-filter-zero",
        "src/mantle/spore.py",
        "        if filt == 0:\n            pass",
        "        if filt == 0:\n            row[0] ^= 1",
        "t_spore_png_filter_decoder",
    ),
    Mutant(
        "spore-png-filter-sub",
        "src/mantle/spore.py",
        "                row[i] = (row[i] + row[i - bpp]) & 0xff",
        "                row[i] = row[i]",
        "t_spore_png_filter_decoder",
    ),
    Mutant(
        "spore-png-filter-up",
        "src/mantle/spore.py",
        "                row[i] = (row[i] + prev[i]) & 0xff\n        elif filt == 3:",
        "                row[i] = row[i]\n        elif filt == 3:",
        "t_spore_png_filter_decoder",
    ),
    Mutant(
        "spore-png-filter-average",
        "src/mantle/spore.py",
        "                row[i] = (row[i] + ((row[i - bpp] + prev[i]) // 2)) & 0xff",
        "                row[i] = (row[i] + row[i - bpp]) & 0xff",
        "t_spore_png_filter_decoder",
    ),
    Mutant(
        "spore-png-filter-paeth",
        "src/mantle/spore.py",
        "                predictor = a if pa <= pb and pa <= pc else (b if pb <= pc else c)",
        "                predictor = a",
        "t_spore_png_filter_decoder",
    ),
    Mutant(
        "spore-png-decoded-length",
        "src/mantle/spore.py",
        "    if len(raw) != expected:\n        raise ValueError(\"PNG decoded data length %d != expected %d\" % (len(raw), expected))",
        "    if False and len(raw) != expected:\n        raise ValueError(\"PNG decoded data length %d != expected %d\" % (len(raw), expected))",
        "t_spore_png_filter_decoder",
    ),
    Mutant(
        "spore-png-unknown-filter",
        "src/mantle/spore.py",
        "        else:\n            raise ValueError(\"unsupported PNG filter %d\" % filt)",
        "        else:\n            pass",
        "t_spore_png_filter_decoder",
    ),
    Mutant(
        "cert-receipt-replay",
        "src/mantle/check.py",
        "    if payload.get(\"run_nonce\") != run_nonce:\n        return False, \"invariant receipt nonce is missing, stale, or replayed\"",
        "    if False and payload.get(\"run_nonce\") != run_nonce:\n        return False, \"invariant receipt nonce is missing, stale, or replayed\"",
        "t_certification_invariant_receipt",
    ),
    Mutant(
        "cert-receipt-source",
        "src/mantle/check.py",
        "    if payload.get(\"source_identity\") != source_identity:\n        return False, \"invariant receipt source identity is stale\"",
        "    if False and payload.get(\"source_identity\") != source_identity:\n        return False, \"invariant receipt source identity is stale\"",
        "t_certification_invariant_receipt",
    ),
    Mutant(
        "cert-receipt-red-row",
        "src/mantle/check.py",
        "    if not all(row.get(\"ok\") is True for row in rows):",
        "    if False and not all(row.get(\"ok\") is True for row in rows):",
        "t_certification_invariant_receipt",
    ),
]


def _apply(mutant: Mutant, root: Path) -> None:
    target = root / mutant.file
    text = target.read_text(encoding="utf-8")
    count = text.count(mutant.old)
    if count != 1:
        raise RuntimeError(
            "%s expected one mutation site in %s, found %d"
            % (mutant.id, mutant.file, count)
        )
    target.write_text(text.replace(mutant.old, mutant.new, 1), encoding="utf-8")


def _challenge(mutant: Mutant, scratch: Path, timeout: int) -> dict:
    _apply(mutant, scratch)
    probe = (
        "from mantle.audits.invariants import {0}\n"
        "ok, detail = {0}()\n"
        "print(detail)\n"
        "raise SystemExit(0 if ok else 1)\n"
    ).format(mutant.catcher)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(scratch / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            cwd=scratch,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        killed = proc.returncode != 0
        detail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        return {
            **asdict(mutant),
            "status": "KILLED" if killed else "SURVIVED",
            "returncode": proc.returncode,
            "detail": detail[-500:],
        }
    except subprocess.TimeoutExpired:
        return {
            **asdict(mutant),
            "status": "KILLED",
            "returncode": None,
            "detail": "catcher timed out",
        }


def run(selected: List[Mutant], timeout: int) -> List[dict]:
    results = []
    for mutant in selected:
        with tempfile.TemporaryDirectory(prefix="mantle-mutant-") as td:
            scratch = Path(td)
            shutil.copytree(ROOT / "src", scratch / "src")
            for name in ("tools", "documents"):
                source = ROOT / name
                if source.exists():
                    shutil.copytree(source, scratch / name)
            try:
                result = _challenge(mutant, scratch, timeout)
            except Exception as exc:  # configuration errors are not killed mutants
                result = {
                    **asdict(mutant),
                    "status": "HARNESS_ERROR",
                    "returncode": None,
                    "detail": "%s: %s" % (type(exc).__name__, exc),
                }
            results.append(result)
            print("  [%-13s] %-22s %s" % (
                result["status"], mutant.id, result["catcher"]
            ))
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list mutation IDs and exit")
    parser.add_argument("--only", action="append", default=[],
                        help="run one mutation ID (repeatable)")
    parser.add_argument("--timeout", type=int, default=30,
                        help="seconds allowed per catcher")
    parser.add_argument("--report", help="write the JSON report to this path")
    args = parser.parse_args(argv)

    if args.list:
        for mutant in MUTANTS:
            print("%s\t%s\t%s" % (mutant.id, mutant.file, mutant.catcher))
        return 0
    wanted = set(args.only)
    selected = [m for m in MUTANTS if not wanted or m.id in wanted]
    missing = wanted - {m.id for m in selected}
    if missing:
        parser.error("unknown mutation ID(s): %s" % ", ".join(sorted(missing)))

    print("MANTLE TARGETED MUTATION SWEEP (%d mutants)" % len(selected))
    results = run(selected, max(1, args.timeout))
    report = {
        "schema": "mantle-mutation-report-v1",
        "mutants": results,
        "killed": sum(r["status"] == "KILLED" for r in results),
        "survived": sum(r["status"] == "SURVIVED" for r in results),
        "harness_errors": sum(r["status"] == "HARNESS_ERROR" for r in results),
    }
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("report: %s" % path)
    print("RESULT: {killed}/{total} killed; {survived} survived; "
          "{harness_errors} harness errors".format(total=len(results), **report))
    return 0 if report["killed"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
