"""CLI handlers for Organize.AppAI commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from typing import cast

from organize.config import Config
from organize.find_config import find_config

from .assist import (
    answer_existing,
    create_proposal,
    discover_workspace,
    proposal_human,
)
from .bridge import MantleBridge
from .events import EvaluationEvent
from .explain import explain_config, explain_human, explain_json
from .why import diagnose_path, diagnose_trace, report_events, why_human, why_json


def _format(value: str) -> str:
    normalized = value.lower()
    if normalized not in {"human", "json"}:
        raise argparse.ArgumentTypeError("format must be human or json")
    return normalized


def _root(value: str | None) -> Path:
    if value:
        return Path(value).resolve(strict=True)
    discovered = discover_workspace()
    if discovered is None:
        raise SystemExit(
            "Refusing without an approved root. Pass --safe-root or run inside an "
            "Organize.AppAI workspace containing WORKSPACE.txt."
        )
    return discovered


def _config(value: str | None) -> Config:
    path = find_config(value)
    return Config.from_path(path)


def _resident() -> MantleBridge:
    return MantleBridge(Path(__file__).resolve().parents[2])


def _sense(question: str) -> MantleBridge | None:
    bridge = _resident()
    if not bridge.available():
        return None
    try:
        bridge.sense_question(question)
        return bridge
    except Exception:  # noqa: BLE001 - optional resident is fail-open
        return None


def _try_resident_write(operation) -> bool:
    try:
        operation()
        return True
    except Exception:  # noqa: BLE001 - optional resident is fail-open
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="organize")
    commands = parser.add_subparsers(dest="command", required=True)

    explain = commands.add_parser("explain", help="explain a parsed configuration")
    explain.add_argument("config", nargs="?")
    explain.add_argument("--format", type=_format, default="human")
    explain.add_argument("--tags", default="")
    explain.add_argument("--skip-tags", default="")
    explain.add_argument("--working-dir", default=".")

    why = commands.add_parser(
        "why", help="diagnose one resource from real filter traces"
    )
    why.add_argument("resource")
    why.add_argument("--config")
    why.add_argument("--trace-file")
    why.add_argument("--run-id")
    why.add_argument("--safe-root")
    why.add_argument("--format", type=_format, default="human")
    why.add_argument("--tags", default="")
    why.add_argument("--skip-tags", default="")

    assist = commands.add_parser(
        "assist", help="answer questions or create safe proposals"
    )
    assist.add_argument("request")
    assist.add_argument("--config")
    assist.add_argument("--safe-root")
    assist.add_argument("--location")
    assist.add_argument("--proposal-dir")
    assist.add_argument("--format", type=_format, default="human")

    status = commands.add_parser("mantle-status", help="show the resident Body status")
    status.add_argument("--product-root", default=".")
    status.add_argument("--format", type=_format, default="human")
    return parser


def main(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "explain":
        report = explain_config(
            _config(args.config),
            tags=_tags(args.tags),
            skip_tags=_tags(args.skip_tags),
            working_dir=args.working_dir,
        )
        print(explain_json(report) if args.format == "json" else explain_human(report))
        return

    if args.command == "why":
        bridge = _sense(f"Why did {args.resource} receive this outcome?")
        root = _root(args.safe_root)
        if args.trace_file:
            report = diagnose_trace(
                args.trace_file,
                args.resource,
                approved_root=root,
                run_id=args.run_id,
            )
        elif args.config:
            report = diagnose_path(
                _config(args.config),
                args.resource,
                approved_root=root,
                tags=_tags(args.tags),
                skip_tags=_tags(args.skip_tags),
            )
        else:
            raise SystemExit("why requires either --config or --trace-file")
        if bridge is not None:
            _try_resident_write(
                lambda: bridge.remember_events(
                    [
                        EvaluationEvent(**cast("dict", item))
                        for item in report_events(report)
                    ],
                    verified_simulation=True,
                )
            )
        print(why_json(report) if args.format == "json" else why_human(report))
        return

    if args.command == "assist":
        bridge = _sense(args.request)
        question = args.request.strip().lower()
        asks_about_existing = args.config and question.startswith(
            ("what", "why", "which", "will", "does", "is", "are", "explain")
        )
        if asks_about_existing:
            config = _config(args.config)
            report = answer_existing(
                config,
                args.request,
                safe_root=_root(args.safe_root),
            )
            if bridge is not None:
                _try_resident_write(
                    lambda: bridge.remember_configuration(explain_config(config))
                )
                if report["source"] != "deterministic":
                    _try_resident_write(
                        lambda: bridge.remember_inference(
                            str(report["answer"]),
                            [item["ref"] for item in report["citations"]],
                        )
                    )
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(report["answer"])
                if report["citations"]:
                    print("\nCitations:")
                    for citation in report["citations"]:
                        print(f"  [{citation['ref']}] {citation['claim']}")
                print(f"\nUncertainty: {report['uncertainty']}")
                if report["provider_error"]:
                    print(f"MIND fallback: {report['provider_error']}")
            return
        report = create_proposal(
            args.request,
            safe_root=_root(args.safe_root),
            location=args.location,
            existing_config=args.config,
            proposal_dir=args.proposal_dir,
        )
        if bridge is not None:
            _try_resident_write(
                lambda: bridge.remember_proposal(
                    {
                        "proposal_path": report["proposal_path"],
                        "source": report["source"],
                        "assumptions": report["assumptions"],
                        "simulation_run_id": report["simulation"]["run_id"],
                        "execution": report["execution"],
                    }
                )
            )
        print(
            json.dumps(report, indent=2, sort_keys=True)
            if args.format == "json"
            else proposal_human(report)
        )
        return

    if args.command == "mantle-status":
        status = MantleBridge(Path(args.product_root).resolve()).status()
        try:
            import mantle
            status["mantle_version"] = mantle.__version__
        except Exception:
            status["mantle_version"] = "unavailable"
        status.update({
            "resident_protocol": "mantle-resident-v2",
            "historical_certification_receipt": status.get("persisted_stage1_certified"),
            "current_runtime_authority": status.get("runtime_stage1_certified", False),
            "requested_model": "openrouter/free",
            "resolved_model": None,
            "model_evidence": "not_requested",
            "energy_state": "host-ledger",
            "provider_state": "offline-unless-session-configured",
            "command_contract_drift": False,
        })
        if args.format == "json":
            print(json.dumps(status, indent=2, sort_keys=True))
        else:
            print(
                "Mantle resident: "
                + ("available" if status["available"] else "unavailable")
            )
            for key, value in status.items():
                if key != "available":
                    print(f"  {key}: {value}")


def _tags(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}
