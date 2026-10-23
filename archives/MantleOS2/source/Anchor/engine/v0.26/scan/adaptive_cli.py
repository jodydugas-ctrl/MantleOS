from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .assimilation import prepare_assimilation_workbench
from .assimilation_candidate import validate_assimilation_candidate
from .assimilation_context import files_for_assimilation_detection
from .cli import main as canonical_main


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


def main(argv=None):
    """Run canonical SCAN plus the post-scan adaptive-assimilation engineering layer.

    Canonical scanning remains deterministic and LLM-free. Ordinary scanning never executes generated
    candidate code. `validate-assimilation` is an explicit engineering command that loads candidate scanner
    code and mechanically compares it with the trusted baseline without promoting it.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "validate-assimilation":
        return _validate_assimilation_command(args)

    result = canonical_main(args)
    status = _post_scan_assimilation(args)
    if status is not None:
        print(json.dumps({"adaptive_assimilation": status}, indent=2, ensure_ascii=False))
    return result
