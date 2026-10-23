#!/usr/bin/env python3
"""
mantle.check -- closed-world repository certification (Mantle OS)

    python -m mantle check
    python -m mantle check --strict
    python -m mantle check --fast [--strict]

Only the full, no-skip run is a certification. ``--strict`` turns every top-level or
internally reported skip/N/A into a failure. ``--fast`` is a useful gates-only diagnostic
and is never labeled a certification because it deliberately omits the narrated demos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time

from .paths import EXAMPLES_DIR, REPO_ROOT, SAMPLE_APP_DIR, SRC_DIR

_LINE = "=" * 74
_INTERNAL_GAP = re.compile(
    r"(?im)^\s*(?:\[SKIP\].*|.*\bN/A\b.*|OK\s+\(skipped=\d+\).*)$"
)
_INVARIANT_EVIDENCE_MARKER = "MANTLE_INVARIANT_EVIDENCE_JSON:"


def _repository_identity() -> str:
    """Hash every tracked byte plus the interpreter used by this closed-world run."""
    proc = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError("cannot enumerate tracked certification surface: %s" % detail)
    digest = hashlib.sha256()
    count = 0
    for encoded in sorted(item for item in proc.stdout.split(b"\0") if item):
        relative = encoded.decode("utf-8")
        filename = os.path.join(REPO_ROOT, relative)
        if not os.path.isfile(filename):
            raise RuntimeError("tracked certification input is missing: %s" % relative)
        with open(filename, "rb") as stream:
            data = stream.read()
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        count += 1
    runtime = "%s|%s|%d" % (sys.executable, sys.version, count)
    digest.update(runtime.encode("utf-8"))
    return "sha256:" + digest.hexdigest()


def _invariant_evidence(output: str):
    for line in reversed(output.splitlines()):
        if line.startswith(_INVARIANT_EVIDENCE_MARKER):
            try:
                return json.loads(line[len(_INVARIANT_EVIDENCE_MARKER):])
            except (TypeError, ValueError):
                return None
    return None


def _validate_invariant_receipt(payload, expected_codes, run_nonce, source_identity):
    if not isinstance(payload, dict):
        return False, "missing or malformed invariant receipt"
    if payload.get("schema") != "mantle-invariant-evidence-v1":
        return False, "unknown invariant receipt schema"
    if payload.get("run_nonce") != run_nonce:
        return False, "invariant receipt nonce is missing, stale, or replayed"
    if payload.get("source_identity") != source_identity:
        return False, "invariant receipt source identity is stale"
    rows = payload.get("results")
    if not isinstance(rows, list):
        return False, "invariant receipt has no result list"
    codes = [row.get("code") for row in rows if isinstance(row, dict)]
    if codes != list(expected_codes):
        return False, "invariant receipt rows are missing, duplicated, or reordered"
    if not all(row.get("ok") is True for row in rows):
        return False, "invariant receipt contains a red or malformed result"
    return True, "complete content-bound invariant receipt"


def _has_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _has_multilang() -> bool:
    try:
        from .assimilator import scanner_ts
        return bool(scanner_ts.available())
    except (ImportError, OSError):
        return False


def _steps(fast: bool):
    """Yield ``(name, argv, cwd, expect_fail, skip_reason)`` in gate order."""
    py = sys.executable
    mantle = [py, "-m", "mantle"]
    repo = os.path.isdir(EXAMPLES_DIR)
    no_repo = None if repo else "examples/ not present (installed without repository gates)"
    no_pil = None if _has_pillow() else \
        "Pillow not installed (pip install 'mantle-os[spore]')"
    no_multilang = None if _has_multilang() else \
        "tree-sitter stack not installed (pip install 'mantle-os[multilang]')"

    yield ("Stage-1 Zombie Body gate", mantle + ["audit", "--rows-only"],
           None, False, None)
    for flag in ("--break-hash", "--break-primer", "--break-seal"):
        yield ("tamper proof %s (must be CAUGHT)" % flag,
               mantle + ["audit", flag, "--fast"], None, True, None)
    yield ("security invariants", mantle + ["prove", "--json"], None, False, None)
    yield ("Stage-2 MIND gate", mantle + ["audit-mind", "--rows-only"],
           None, False, None)
    if not fast:
        yield ("narrated Phase-1 demo", mantle + ["demo"], None, False, None)
        yield ("narrated Phase-2 fusion", mantle + ["mind"], None, False, None)
    yield ("assimilation dry-run", mantle + ["assimilate", SAMPLE_APP_DIR, "--dry-run"],
           None, False, no_repo)
    vcw_dir = os.path.join(EXAMPLES_DIR, "vcw")
    yield ("standalone cube codec selftest", [py, "vcw_cube.py", "selftest"],
           vcw_dir, False, no_repo)
    yield ("cube interop (standalone <-> engine)",
           [py, os.path.join(vcw_dir, "interop.py")], None, False, no_repo)
    spore_dir = os.path.join(EXAMPLES_DIR, "spore")
    yield ("SPORE purity gate", [py, os.path.join(spore_dir, "audit_spore.py")],
           None, False, no_repo or no_pil)
    yield ("SPORE VCW conformance", [py, os.path.join(spore_dir, "vcw_conformance.py")],
           None, False, no_repo or no_pil)
    yield ("multi-language parity",
           [py, os.path.join(EXAMPLES_DIR, "tests", "test_multilang_parity.py")],
           None, False, no_repo or no_multilang)


def _args(argv):
    parser = argparse.ArgumentParser(
        prog="python -m mantle check",
        description="Run Mantle repository gates. Only a complete full run certifies.",
    )
    parser.add_argument("--fast", action="store_true",
                        help="omit narrated demos; always diagnostic, never certification")
    parser.add_argument("--strict", action="store_true",
                        help="treat every skip or N/A as a failure")
    parser.add_argument("--json", action="store_true",
                        help="also emit a machine-readable terminal gate result")
    return parser.parse_args(list(argv or []))


def _internal_gap(output: str) -> str | None:
    match = _INTERNAL_GAP.search(output)
    return match.group(0).strip() if match else None


def main(argv=None):
    args = _args(argv)
    try:
        source_identity = _repository_identity()
    except (OSError, RuntimeError) as exc:
        print("CERTIFICATION BLOCKED: %s" % exc)
        return 1
    run_nonce = secrets.token_hex(24)
    from .audits.invariants import REGISTRY
    expected_invariant_codes = tuple(spec.code for spec in REGISTRY)
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    # Child output is parsed as UTF-8 on every platform. Force that encoding so a Windows
    # locale cannot turn an internal skip line into undecodable bytes (or crash reporting).
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["MANTLE_REQUIRE_NO_SKIPS"] = "1" if args.strict else "0"
    env["MANTLE_CERTIFICATION_RUN_NONCE"] = run_nonce
    env["MANTLE_CERTIFICATION_SOURCE_IDENTITY"] = source_identity

    labels = []
    if args.fast:
        labels.append("fast / gates-only")
    if args.strict:
        labels.append("strict")
    suffix = "  (%s)" % ", ".join(labels) if labels else ""
    print(_LINE)
    print("MANTLE OS CHECK  ·  repository certification%s" % suffix)
    print(_LINE)

    results = []
    for name, cmd, cwd, expect_fail, skip_reason in _steps(args.fast):
        if skip_reason:
            print("  [SKIP] %-45s %s" % (name, skip_reason))
            results.append({"name": name, "status": "SKIP", "detail": skip_reason})
            continue
        try:
            step_identity = _repository_identity()
        except (OSError, RuntimeError) as exc:
            step_identity = None
            identity_detail = str(exc)
        else:
            identity_detail = "tracked certification surface changed before this gate"
        if step_identity != source_identity:
            print("  [FAIL] %-45s %s" % (name, identity_detail))
            results.append({"name": name, "status": "FAIL", "detail": identity_detail})
            break
        t0 = time.time()
        proc = subprocess.run(
            cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        output = proc.stdout.decode("utf-8", errors="replace")
        failed = (proc.returncode == 0) if expect_fail else (proc.returncode != 0)
        receipt_detail = ""
        if name == "security invariants" and not failed:
            receipt_ok, receipt_detail = _validate_invariant_receipt(
                _invariant_evidence(output), expected_invariant_codes,
                run_nonce, source_identity,
            )
            failed = not receipt_ok
        try:
            gate_identity = _repository_identity()
        except (OSError, RuntimeError) as exc:
            gate_identity = None
            receipt_detail = str(exc)
        if gate_identity != source_identity:
            failed = True
            receipt_detail = "tracked certification surface changed during this gate"
        gap = None if expect_fail else _internal_gap(output)
        status = "FAIL" if failed else ("SKIP" if gap else "PASS")
        print("  [%s] %-45s %5.1fs%s" % (
            status, name, time.time() - t0,
            "  " + (gap or receipt_detail) if (gap or receipt_detail) else ""))
        if failed:
            for line in output.splitlines()[-12:]:
                print("         | " + line)
        results.append({"name": name, "status": status,
                        "detail": gap or receipt_detail or ""})

    try:
        final_identity = _repository_identity()
    except (OSError, RuntimeError) as exc:
        final_identity = None
        drift_detail = str(exc)
    else:
        drift_detail = "tracked certification surface changed during the run"
    if final_identity != source_identity:
        print("  [FAIL] %-45s %s" % ("closed-world source identity", drift_detail))
        results.append({"name": "closed-world source identity", "status": "FAIL",
                        "detail": drift_detail})

    passed = sum(item["status"] == "PASS" for item in results)
    skipped = [item for item in results if item["status"] == "SKIP"]
    failures = [item for item in results if item["status"] == "FAIL"]
    print(_LINE)
    print("RESULT: %d passed, %d skipped%s, %d failed" % (
        passed, len(skipped),
        " (STRICT: failures)" if args.strict and skipped else "",
        len(failures),
    ))
    for item in failures:
        print("  FAILED: %s" % item["name"])
    if args.strict:
        for item in skipped:
            print("  DID NOT EXECUTE: %s — %s" % (item["name"], item["detail"]))

    if failures or (args.strict and skipped):
        if args.json:
            print(json.dumps({"result": "FAIL", "passed": passed,
                              "partial": len(skipped), "failed": len(failures),
                              "steps": results}, sort_keys=True))
        print("CERTIFICATION BLOCKED.")
        print(_LINE)
        return 1
    if args.fast:
        if args.json:
            print(json.dumps({"result": "PASS", "scope": "gates-only",
                              "passed": passed, "partial": 0, "failed": 0,
                              "steps": results}, sort_keys=True))
        print("GATES-ONLY DIAGNOSTIC GREEN — NOT A CERTIFICATION.")
        print(_LINE)
        return 0
    if skipped:
        if args.json:
            print(json.dumps({"result": "PARTIAL", "passed": passed,
                              "partial": len(skipped), "failed": 0,
                              "steps": results}, sort_keys=True))
        print("PARTIAL: required work did not execute — NOT A CERTIFICATION.")
        print("Re-run with --strict to make every gap fail closed.")
        print(_LINE)
        return 3
    if args.json:
        print(json.dumps({"result": "PASS", "scope": "repository-certification",
                          "passed": passed, "partial": 0, "failed": 0,
                          "steps": results}, sort_keys=True))
    print("EVERY REQUIRED GATE EXECUTED AND GREEN. The reference organism is certified.")
    print(_LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
