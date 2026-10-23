from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from . import __version__
from .anchor_code import export_anchor_code
from .agent_blueprint import blueprint_filename, export_agent_blueprint
from .assimilation import prepare_assimilation_workbench
from .assimilation_candidate import validate_assimilation_candidate
from .assimilation_context import files_for_assimilation_detection
from .cli import main as canonical_main
from .conformance import evaluate_candidate
from .refinement_loop import run_refinement_loop
from .store import Store


def _option(args: Sequence[str], name: str, default: str | None = None) -> str | None:
    prefix = name + "="
    for index, value in enumerate(args):
        if value.startswith(prefix):
            return value[len(prefix):]
        if value == name and index + 1 < len(args):
            return args[index + 1]
    return default


def _post_scan_assimilation(args: list[str]) -> dict | None:
    if not args or args[0] not in {"scan", "scan-manifest"}:
        return None

    command = args[0]
    output = Path(_option(args, "--out", ".scan") or ".scan")
    body_path = output / "machine_body_map.json"
    if not body_path.exists():
        return None
    body = json.loads(body_path.read_text(encoding="utf-8"))

    if command == "scan":
        if len(args) < 2:
            return None
        content_root = Path(args[1]).resolve()
    else:
        raw_root = _option(args, "--content-root")
        content_root = Path(raw_root).resolve() if raw_root else None

    status = prepare_assimilation_workbench(
        output=output,
        specimen=body.get("specimen") or {},
        files=files_for_assimilation_detection(body.get("files") or []),
        nodes=body.get("nodes") or [],
        findings=body.get("findings") or [],
        evidence=body.get("evidence") or [],
        adapter_runs=(body.get("extraction") or {}).get("adapter_runs") or {},
        content_root=content_root,
    )
    (output / "assimilation_status.json").write_text(json.dumps({
        "schema_version": "scan-adaptive-assimilation-status/0.1",
        **status,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return status


def _validate_assimilation_command(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scan-body validate-assimilation",
        description="mechanically compare one explicit candidate scanner adapter against the trusted baseline",
    )
    parser.add_argument("specimen_root", type=Path)
    parser.add_argument("candidate_adapter", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--specimen-id", default=None)
    ns = parser.parse_args(args[1:])
    report = validate_assimilation_candidate(
        specimen_root=ns.specimen_root,
        candidate_path=ns.candidate_adapter,
        output=ns.out,
        specimen_id=ns.specimen_id,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("mechanical_gate") == "PASS" else 2


def _specimen_from_store(store: Store) -> dict:
    rows = [row for row in store.semantic_objects() if row.get("object_type") == "SPECIMEN"]
    return dict(rows[0].get("attributes") or {}) if rows else {}


def _anchor_code_command(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scan-body anchor-code",
        description="project canonical SCAN evidence into deterministic Anchor Code 0.9",
    )
    parser.add_argument("db", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    ns = parser.parse_args(args[1:])
    ns.out_dir.mkdir(parents=True, exist_ok=True)
    store = Store(ns.db.resolve(strict=True), readonly=True)
    try:
        specimen = _specimen_from_store(store)
        result = export_anchor_code(
            store,
            specimen,
            ns.out_dir / "anchor_code.txt",
            ns.out_dir / "anchor_blueprint.json",
            engine_version=__version__
        )
    finally:
        store.close()
    print(json.dumps({"state": "PASS", **result}, indent=2, ensure_ascii=False))
    return 0


def _anchor_blueprint_command(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scan-body anchor-blueprint",
        description="export one self-contained, evidence-bound coding-agent Anchor Blueprint",
    )
    parser.add_argument("db", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    ns = parser.parse_args(args[1:])
    store = Store(ns.db.resolve(strict=True), readonly=True)
    try:
        specimen = _specimen_from_store(store)
        out = ns.out or (ns.db.parent / blueprint_filename(specimen))
        result = export_agent_blueprint(
            store, specimen, out, engine_version=__version__,
        )
    finally:
        store.close()
    print(json.dumps({"state": "PASS", **result, "path": str(out)}, indent=2, ensure_ascii=False))
    return 0


def _conform_command(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scan-body conform",
        description="rescan a reconstruction read-only and compare it with an Anchor Blueprint",
    )
    parser.add_argument("blueprint", type=Path)
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--specimen-id", default=None)
    parser.add_argument("--previous-report", type=Path, default=None)
    ns = parser.parse_args(args[1:])
    result = evaluate_candidate(
        ns.blueprint,
        ns.candidate_root,
        ns.out,
        engine_version=__version__,
        specimen_id=ns.specimen_id,
        previous_report_path=ns.previous_report,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("state") == "PASS" else 12


def _refine_command(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scan-body refine",
        description="run a bounded SCAN-verified reconstruction refinement loop",
    )
    parser.add_argument("blueprint", type=Path)
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--specimen-id", default=None)
    parser.add_argument(
        "--patch-command",
        default=None,
        help=(
            "optional external patch command. Placeholders: {candidate}, {blueprint}, {refinement}, "
            "{conformance}, {report}, {task}, {iteration}, {iteration_dir}"
        ),
    )
    parser.add_argument("--max-iterations", type=int, default=4)
    parser.add_argument("--max-stalled-iterations", type=int, default=1)
    parser.add_argument("--regression-policy", choices=["stop", "repair"], default="stop")
    parser.add_argument("--patch-timeout-seconds", type=float, default=900.0)
    ns = parser.parse_args(args[1:])
    result = run_refinement_loop(
        ns.blueprint,
        ns.candidate_root,
        ns.out,
        engine_version=__version__,
        specimen_id=ns.specimen_id,
        patch_command=ns.patch_command,
        max_iterations=ns.max_iterations,
        max_stalled_iterations=ns.max_stalled_iterations,
        regression_policy=ns.regression_policy,
        patch_timeout_seconds=ns.patch_timeout_seconds,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("state") in {"COMPLETE", "WAITING_FOR_PATCH"} else 13


def main(argv=None):
    """Run canonical SCAN plus explicit downstream engineering layers.

    Stage 1 remains deterministic and LLM-free. Anchor Code and Anchor Blueprint
    are derived projections of canonical evidence. Conformance and refinement
    always rescan the candidate; a coding worker's self-report is not evidence.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "validate-assimilation":
        return _validate_assimilation_command(args)
    if args and args[0] == "anchor-code":
        return _anchor_code_command(args)
    if args and args[0] == "anchor-blueprint":
        return _anchor_blueprint_command(args)
    if args and args[0] == "conform":
        return _conform_command(args)
    if args and args[0] == "refine":
        return _refine_command(args)

    result = canonical_main(args)
    status = _post_scan_assimilation(args)
    if status is not None:
        print(json.dumps({"adaptive_assimilation": status}, indent=2, ensure_ascii=False))
    return result
