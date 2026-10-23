#!/usr/bin/env python3
"""Bounded, non-authoritative timing harness for Mantle certification paths.

This tool measures existing commands.  It never skips, reorders, certifies, or grants
authority.  Results are append-only JSON Lines intended for local comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LABEL = "NON-AUTHORITATIVE PERFORMANCE EVIDENCE"


def _run_text(argv: Sequence[str]) -> str:
    return subprocess.check_output(
        list(argv), cwd=ROOT, stderr=subprocess.STDOUT, text=True, encoding="utf-8"
    ).strip()


def _tracked_identity() -> Dict[str, Any]:
    head = _run_text(["git", "rev-parse", "HEAD"])
    status = _run_text(["git", "status", "--porcelain=v1"])
    tracked = _run_text(["git", "ls-files", "-z"]).split("\0")
    digest = hashlib.sha256()
    count = 0
    for relative in sorted(path for path in tracked if path):
        path = ROOT / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        encoded = relative.replace("\\", "/").encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        count += 1
    return {
        "head": head,
        "clean": not bool(status),
        "status": status.splitlines(),
        "tracked_file_count": count,
        "tracked_tree_sha256": "sha256:" + digest.hexdigest(),
    }


def _environment() -> Dict[str, Any]:
    return {
        "python": sys.version,
        "executable": sys.executable,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
    }


def _env() -> Dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["MANTLE_REQUIRE_NO_SKIPS"] = "1"
    return env


def _cases(suites: Iterable[str]) -> List[Tuple[str, List[str], Path, bool]]:
    py = sys.executable
    selected = list(suites)
    cases: List[Tuple[str, List[str], Path, bool]] = []
    if "strict" in selected:
        cases.append(("strict", [py, "-m", "mantle", "check", "--strict"], ROOT, False))
    if "steps" in selected:
        sys.path.insert(0, str(SRC))
        try:
            from mantle.check import _steps

            for name, argv, cwd, expect_fail, skip_reason in _steps(False):
                if skip_reason:
                    raise RuntimeError("required benchmark step unavailable: %s" % skip_reason)
                cases.append(("step:" + name, list(argv), Path(cwd or ROOT), expect_fail))
        finally:
            sys.path.pop(0)
    if "invariants" in selected:
        cases.append(("invariants", [py, "-m", "mantle", "prove"], ROOT, False))
    if "grimoire" in selected:
        bundle = (
            "from mantle.audits.invariants import _grimoire_v010_checks as f; "
            "r=f(); assert r and all(ok for ok, _ in r.values())"
        )
        wrappers = (
            "from mantle.audits.invariants import _run_grimoire_v010_invariants as f; "
            "r=f(); assert r and all(row['ok'] for row in r)"
        )
        cases.append(("grimoire:bundle", [py, "-c", bundle], ROOT, False))
        cases.append(("grimoire:wrappers", [py, "-c", wrappers], ROOT, False))
    if "spore" in selected:
        cases.append(("spore:purity", [py, str(ROOT / "examples" / "spore" /
                                               "audit_spore.py")], ROOT, False))
        cases.append(("spore:vcw-conformance",
                      [py, str(ROOT / "examples" / "spore" / "vcw_conformance.py")],
                      ROOT, False))
    return cases


def _measure(name: str, argv: Sequence[str], cwd: Path, expect_fail: bool,
             timeout: int) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            list(argv), cwd=cwd, env=_env(), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=timeout, check=False,
        )
        elapsed = time.perf_counter() - started
        output = proc.stdout.decode("utf-8", errors="replace")
        passed = (proc.returncode != 0) if expect_fail else (proc.returncode == 0)
        return {
            "name": name,
            "seconds": elapsed,
            "status": "PASS" if passed else "FAIL",
            "returncode": proc.returncode,
            "expected_failure": expect_fail,
            "output_sha256": "sha256:" + hashlib.sha256(proc.stdout).hexdigest(),
            "output_tail": output.splitlines()[-12:],
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        return {
            "name": name,
            "seconds": elapsed,
            "status": "TIMEOUT",
            "returncode": None,
            "expected_failure": expect_fail,
            "output_sha256": None,
            "output_tail": [str(exc)],
        }


def _summaries(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    names = sorted({sample["name"] for sample in samples})
    results = []
    for name in names:
        values = [float(sample["seconds"]) for sample in samples if sample["name"] == name]
        median = statistics.median(values)
        deviations = [abs(value - median) for value in values]
        results.append({
            "name": name,
            "samples": values,
            "median_seconds": median,
            "median_absolute_deviation": statistics.median(deviations),
            "minimum_seconds": min(values),
            "maximum_seconds": max(values),
        })
    return results


def _args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite", action="append",
        choices=("strict", "steps", "invariants", "grimoire", "spore"),
        help="suite to measure; repeat for multiple suites (default: invariants)",
    )
    parser.add_argument("--repeat", type=int, default=1, help="measured runs per case")
    parser.add_argument("--warmup", type=int, default=0, help="unrecorded warm-ups per case")
    parser.add_argument("--timeout", type=int, default=900, help="seconds allowed per command")
    parser.add_argument(
        "--output", default=str(ROOT / ".artifacts" / "efficiency" / "benchmarks.jsonl"),
        help="append-only JSON Lines destination",
    )
    parser.add_argument("--require-clean", action="store_true",
                        help="refuse a dirty tracked worktree")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _args(argv)
    if args.repeat < 1 or args.warmup < 0 or args.timeout < 1:
        raise SystemExit("repeat and timeout must be positive; warmup cannot be negative")
    identity = _tracked_identity()
    if args.require_clean and not identity["clean"]:
        raise SystemExit("tracked worktree is dirty; refusing a clean-baseline claim")
    cases = _cases(args.suite or ["invariants"])
    if not cases:
        raise SystemExit("no benchmark cases selected")
    for name, command, cwd, expect_fail in cases:
        for _ in range(args.warmup):
            warmup = _measure(name, command, cwd, expect_fail, args.timeout)
            if warmup["status"] != "PASS":
                raise SystemExit("warm-up failed for %s: %s" % (name, warmup["status"]))
    samples = []
    for _ in range(args.repeat):
        for name, command, cwd, expect_fail in cases:
            sample = _measure(name, command, cwd, expect_fail, args.timeout)
            samples.append(sample)
            print("[%s] %-48s %8.3fs" %
                  (sample["status"], sample["name"], sample["seconds"]))
    record = {
        "schema": "mantle-certification-benchmark-v1",
        "label": LABEL,
        "recorded_at_epoch_seconds": time.time(),
        "source_identity": identity,
        "environment": _environment(),
        "configuration": {
            "suites": args.suite or ["invariants"],
            "repeat": args.repeat,
            "warmup": args.warmup,
            "timeout_seconds": args.timeout,
            "serial": True,
            "network": False,
        },
        "samples": samples,
        "summaries": _summaries(samples),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    print("%s: %s" % (LABEL, output))
    return 0 if all(sample["status"] == "PASS" for sample in samples) else 1


if __name__ == "__main__":
    raise SystemExit(main())
