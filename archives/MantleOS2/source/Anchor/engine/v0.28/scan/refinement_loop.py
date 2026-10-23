from __future__ import annotations

"""Bounded Blueprint-driven reconstruction refinement orchestration.

SCAN remains the mechanical verifier. This module may optionally invoke an
explicit external patch command supplied by the operator, but it never embeds
or selects an LLM provider and never executes the candidate application.

The loop is deliberately bounded and fail-closed:

    candidate -> static conformance -> patch task -> external patch command
              -> static conformance -> ... -> PASS / bounded stop

Every iteration is retained as an auditable directory. Previously satisfied
contracts are protected by the conformance regression detector.
"""

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from typing import Any, Sequence

from .conformance import evaluate_candidate
from .conformance_contract import parse_blueprint_manifest

LOOP_SCHEMA = "scan-anchor-refinement-loop/0.1"
TASK_SCHEMA = "scan-anchor-refinement-task/0.1"

TERMINAL_STATES = {
    "COMPLETE",
    "WAITING_FOR_PATCH",
    "REGRESSION_BLOCKED",
    "NO_CHANGE",
    "NO_PROGRESS",
    "OSCILLATION",
    "AGENT_ERROR",
    "MAX_ITERATIONS",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _candidate_fingerprint(candidate_scan: Path) -> str | None:
    body_map = Path(candidate_scan) / "machine_body_map.json"
    try:
        payload = json.loads(body_map.read_text(encoding="utf-8"))
        fingerprint = ((payload.get("specimen") or {}).get("fingerprint") or {})
        if isinstance(fingerprint, dict):
            return fingerprint.get("value")
        return str(fingerprint) if fingerprint else None
    except Exception:
        return None


def _conformance_fingerprint(report: dict[str, Any]) -> str:
    rows = [
        {
            "contract_id": row.get("contract_id"),
            "status": row.get("status"),
            "exact_candidate_count": row.get("exact_candidate_count"),
        }
        for row in report.get("contracts") or []
    ]
    return _hash_json(rows)


def _required_score(report: dict[str, Any]) -> dict[str, int]:
    required = [row for row in report.get("contracts") or [] if row.get("enforcement") == "REQUIRED"]
    counts = Counter(str(row.get("status") or "UNKNOWN") for row in required)
    return {
        "required_total": len(required),
        "satisfied": counts.get("SATISFIED", 0),
        "hard_failures": counts.get("MISSING", 0) + counts.get("CONTRADICTED", 0),
        "unresolved": counts.get("PARTIAL", 0) + counts.get("UNVERIFIABLE", 0),
        "regressions": len(report.get("regressions") or []),
    }


def _made_progress(before: dict[str, int], after: dict[str, int]) -> bool:
    """Count progress only when movement is toward the Blueprint contract."""
    if after.get("regressions", 0) > 0:
        return False
    return (
        after.get("satisfied", 0) > before.get("satisfied", 0)
        or after.get("hard_failures", 0) < before.get("hard_failures", 0)
        or after.get("unresolved", 0) < before.get("unresolved", 0)
    )


def _task_payload(
    report: dict[str, Any],
    *,
    iteration: int,
    blueprint_path: Path,
    candidate_root: Path,
    refinement_path: Path,
    conformance_path: Path,
    report_path: Path,
    iteration_dir: Path,
) -> dict[str, Any]:
    unresolved = [
        row for row in report.get("contracts") or []
        if row.get("enforcement") == "REQUIRED"
        and row.get("status") in {"MISSING", "CONTRADICTED", "PARTIAL", "UNVERIFIABLE"}
    ]
    satisfied_ids = sorted(
        str(row.get("contract_id"))
        for row in report.get("contracts") or []
        if row.get("status") == "SATISFIED" and row.get("contract_id")
    )
    return {
        "schema_version": TASK_SCHEMA,
        "iteration": iteration,
        "application": (report.get("baseline") or {}).get("app_name"),
        "directive": "PATCH THE EXISTING IMPLEMENTATION. DO NOT REBUILD IT FROM SCRATCH.",
        "candidate_root": str(candidate_root),
        "blueprint": str(blueprint_path),
        "refinement_instructions": str(refinement_path),
        "conformance_report": str(conformance_path),
        "conformance_json": str(report_path),
        "iteration_dir": str(iteration_dir),
        "required_unresolved_contract_ids": [str(row.get("contract_id")) for row in unresolved],
        "regression_contract_ids": [str(row.get("contract_id")) for row in report.get("regressions") or []],
        "preserve_satisfied_contract_count": len(satisfied_ids),
        "preserve_satisfied_contract_set_sha256": sha256("\n".join(satisfied_ids).encode("utf-8")).hexdigest(),
        "rules": [
            "modify the existing candidate in place; do not replace it wholesale",
            "resolve listed required contracts before advisory differences",
            "preserve every currently SATISFIED contract",
            "do not claim success; SCAN will rescan and decide mechanically",
            "do not execute the original specimen as evidence for static conformance",
        ],
    }


def _write_task(task: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(task, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _command_argv(command: str | Sequence[str], replacements: dict[str, str]) -> list[str]:
    raw = shlex.split(command) if isinstance(command, str) else [str(part) for part in command]
    if not raw:
        raise ValueError("patch command is empty")
    out: list[str] = []
    for part in raw:
        for key, value in replacements.items():
            part = part.replace("{" + key + "}", value)
        out.append(part)
    return out


def _run_patch_command(
    command: str | Sequence[str],
    *,
    task: dict[str, Any],
    timeout_seconds: float,
    log_path: Path,
) -> dict[str, Any]:
    replacements = {
        "candidate": task["candidate_root"],
        "blueprint": task["blueprint"],
        "refinement": task["refinement_instructions"],
        "conformance": task["conformance_report"],
        "report": task["conformance_json"],
        "task": str(log_path.parent / "agent_task.json"),
        "iteration": str(task["iteration"]),
        "iteration_dir": task["iteration_dir"],
    }
    argv = _command_argv(command, replacements)
    env = os.environ.copy()
    env.update({
        "SCAN_REFINEMENT_CANDIDATE_ROOT": task["candidate_root"],
        "SCAN_REFINEMENT_BLUEPRINT": task["blueprint"],
        "SCAN_REFINEMENT_INSTRUCTIONS": task["refinement_instructions"],
        "SCAN_REFINEMENT_CONFORMANCE": task["conformance_report"],
        "SCAN_REFINEMENT_REPORT_JSON": task["conformance_json"],
        "SCAN_REFINEMENT_TASK_JSON": str(log_path.parent / "agent_task.json"),
        "SCAN_REFINEMENT_ITERATION": str(task["iteration"]),
        "SCAN_REFINEMENT_ITERATION_DIR": task["iteration_dir"],
        "SCAN_REFINEMENT_MODE": "PATCH_EXISTING_ONLY",
    })
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=task["candidate_root"],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=None if timeout_seconds <= 0 else timeout_seconds,
            check=False,
        )
        timed_out = False
        output = proc.stdout or ""
        return_code = int(proc.returncode)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        if exc.stderr:
            output += ("\n" if output else "") + (exc.stderr if isinstance(exc.stderr, str) else "")
        return_code = 124
    elapsed = time.monotonic() - started
    log_path.write_text(output, encoding="utf-8")
    return {
        "argv": argv,
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 6),
        "log": str(log_path),
    }


def render_loop_report(receipt: dict[str, Any]) -> str:
    app = receipt.get("application") or "application"
    lines = [
        f"# {app} Anchor Refinement Loop",
        "",
        f"**State:** `{receipt.get('state')}`",
        f"**Stop reason:** `{receipt.get('stop_reason')}`",
        "",
        "This is a bounded orchestration receipt. SCAN remains the mechanical verifier; an external patch command, when explicitly supplied, is only the code-changing worker.",
        "",
        "## Bounds",
        "",
        f"- Maximum iterations: {receipt.get('policy', {}).get('max_iterations')}",
        f"- Maximum stalled iterations: {receipt.get('policy', {}).get('max_stalled_iterations')}",
        f"- Regression policy: `{receipt.get('policy', {}).get('regression_policy')}`",
        f"- Patch command enabled: {bool(receipt.get('policy', {}).get('patch_command_enabled'))}",
        "",
        "## Iterations",
        "",
        "| Iteration | Conformance | Required satisfied | Hard failures | Unresolved | Regressions | Candidate fingerprint | Action |",
        "|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for row in receipt.get("iterations") or []:
        score = row.get("score") or {}
        fingerprint = str(row.get("candidate_fingerprint") or "unknown")
        if len(fingerprint) > 16:
            fingerprint = fingerprint[:16] + "…"
        action = row.get("action") or "none"
        lines.append(
            f"| {row.get('iteration')} | `{row.get('conformance_state')}` | {score.get('satisfied', 0)} | "
            f"{score.get('hard_failures', 0)} | {score.get('unresolved', 0)} | {score.get('regressions', 0)} | "
            f"`{fingerprint}` | `{action}` |"
        )
    lines += [
        "",
        "## Stop semantics",
        "",
        "- `COMPLETE`: all required static contracts passed with no regressions.",
        "- `WAITING_FOR_PATCH`: no external patch command was supplied; use the emitted refinement task with a coding agent, then resume with a new loop run or `conform`.",
        "- `REGRESSION_BLOCKED`: a patch broke a previously satisfied contract and the loop is configured to stop on regressions.",
        "- `NO_CHANGE`: the patch worker returned successfully but the next SCAN fingerprint was unchanged.",
        "- `NO_PROGRESS`: the candidate changed, but required conformance did not improve for the configured stall budget.",
        "- `OSCILLATION`: a previous conformance state reappeared, indicating cycling rather than convergence.",
        "- `AGENT_ERROR`: the external patch command failed or timed out.",
        "- `MAX_ITERATIONS`: the explicit iteration budget was exhausted.",
        "",
    ]
    return "\n".join(lines)


def run_refinement_loop(
    blueprint_path: Path,
    candidate_root: Path,
    output: Path,
    *,
    engine_version: str,
    specimen_id: str | None = None,
    patch_command: str | Sequence[str] | None = None,
    max_iterations: int = 4,
    max_stalled_iterations: int = 1,
    regression_policy: str = "stop",
    patch_timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """Run a bounded static refinement loop over an existing candidate.

    Without a patch command, perform one conformance pass and emit a
    machine-readable task, then stop with WAITING_FOR_PATCH. With a command, the
    worker may edit the candidate in place; SCAN rescans after every edit and
    remains the only authority for convergence.
    """
    blueprint_path = Path(blueprint_path).resolve(strict=True)
    candidate_root = Path(candidate_root).resolve(strict=True)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    if not candidate_root.is_dir():
        raise ValueError("candidate_root must be a directory")
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")
    if max_stalled_iterations < 0:
        raise ValueError("max_stalled_iterations must be >= 0")
    if regression_policy not in {"stop", "repair"}:
        raise ValueError("regression_policy must be 'stop' or 'repair'")
    if patch_timeout_seconds < 0:
        raise ValueError("patch_timeout_seconds must be >= 0")

    baseline = parse_blueprint_manifest(blueprint_path)
    app = str(baseline.get("app_name") or "application")
    blueprint_sha = sha256(blueprint_path.read_bytes()).hexdigest()
    iterations: list[dict[str, Any]] = []
    seen_conformance: dict[str, int] = {}
    previous_report_path: Path | None = None
    previous_candidate_fingerprint: str | None = None
    previous_score: dict[str, int] | None = None
    stalled = 0
    state = "MAX_ITERATIONS"
    stop_reason = "iteration budget exhausted before conformance PASS"

    for iteration in range(1, max_iterations + 1):
        iteration_dir = output / f"iteration-{iteration:03d}"
        result = evaluate_candidate(
            blueprint_path,
            candidate_root,
            iteration_dir,
            engine_version=engine_version,
            specimen_id=specimen_id or f"{app}-candidate",
            previous_report_path=previous_report_path,
        )
        report = result["report"]
        report_path = Path(result["paths"]["json"])
        refinement_path = Path(result["paths"]["refinement"])
        conformance_path = Path(result["paths"]["conformance"])
        candidate_scan = Path(result["paths"]["candidate_scan"])
        candidate_fp = _candidate_fingerprint(candidate_scan)
        conformance_fp = _conformance_fingerprint(report)
        score = _required_score(report)

        task = _task_payload(
            report,
            iteration=iteration,
            blueprint_path=blueprint_path,
            candidate_root=candidate_root,
            refinement_path=refinement_path,
            conformance_path=conformance_path,
            report_path=report_path,
            iteration_dir=iteration_dir,
        )
        task_path = iteration_dir / "agent_task.json"
        _write_task(task, task_path)

        row: dict[str, Any] = {
            "iteration": iteration,
            "conformance_state": result["state"],
            "score": score,
            "candidate_fingerprint": candidate_fp,
            "conformance_fingerprint": conformance_fp,
            "paths": {**result["paths"], "agent_task": str(task_path)},
            "action": "evaluated",
        }
        iterations.append(row)

        if result["state"] == "PASS":
            row["action"] = "complete"
            state = "COMPLETE"
            stop_reason = "all required static Blueprint contracts are satisfied with no regressions"
            break

        if iteration > 1 and previous_candidate_fingerprint and candidate_fp == previous_candidate_fingerprint:
            row["action"] = "stopped_no_change"
            state = "NO_CHANGE"
            stop_reason = "patch worker returned but the candidate scan fingerprint did not change"
            break

        if score.get("regressions", 0) > 0 and regression_policy == "stop":
            row["action"] = "stopped_regression"
            state = "REGRESSION_BLOCKED"
            stop_reason = "a previously satisfied contract regressed; automatic patching stopped before further edits"
            break

        if conformance_fp in seen_conformance:
            row["action"] = "stopped_oscillation"
            state = "OSCILLATION"
            stop_reason = f"conformance state repeated iteration {seen_conformance[conformance_fp]}"
            break
        seen_conformance[conformance_fp] = iteration

        if previous_score is not None:
            if _made_progress(previous_score, score):
                stalled = 0
            else:
                stalled += 1
                if stalled > max_stalled_iterations:
                    row["action"] = "stopped_no_progress"
                    state = "NO_PROGRESS"
                    stop_reason = "candidate changed but required Blueprint conformance did not improve within the stall budget"
                    break

        if patch_command is None:
            row["action"] = "waiting_for_patch"
            state = "WAITING_FOR_PATCH"
            stop_reason = "no external patch command supplied; refinement task emitted for a coding agent"
            break

        log_path = iteration_dir / "patch_command.log"
        command_result = _run_patch_command(
            patch_command,
            task=task,
            timeout_seconds=patch_timeout_seconds,
            log_path=log_path,
        )
        row["patch_command"] = command_result
        if command_result["return_code"] != 0:
            row["action"] = "patch_error"
            state = "AGENT_ERROR"
            stop_reason = (
                "external patch command timed out" if command_result.get("timed_out")
                else f"external patch command exited with status {command_result['return_code']}"
            )
            break

        row["action"] = "patched_rescan_pending"
        previous_report_path = report_path
        previous_candidate_fingerprint = candidate_fp
        previous_score = score
    else:
        state = "MAX_ITERATIONS"
        stop_reason = "iteration budget exhausted before conformance PASS"

    receipt = {
        "schema_version": LOOP_SCHEMA,
        "engine_version": engine_version,
        "application": app,
        "state": state,
        "stop_reason": stop_reason,
        "source_blueprint": {"path": str(blueprint_path), "sha256": blueprint_sha},
        "candidate_root": str(candidate_root),
        "policy": {
            "max_iterations": max_iterations,
            "max_stalled_iterations": max_stalled_iterations,
            "regression_policy": regression_policy,
            "patch_timeout_seconds": patch_timeout_seconds,
            "patch_command_enabled": patch_command is not None,
            "candidate_execution": "NOT_PERFORMED_BY_REFINEMENT_LOOP",
            "verifier": "SCAN static Blueprint conformance",
        },
        "iteration_count": len(iterations),
        "iterations": iterations,
    }
    receipt_path = output / "anchor_refinement_loop.json"
    report_path = output / f"{app} Anchor Refinement Loop.md"
    receipt["paths"] = {"receipt": str(receipt_path), "report": str(report_path)}
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_loop_report(receipt), encoding="utf-8")
    return receipt
