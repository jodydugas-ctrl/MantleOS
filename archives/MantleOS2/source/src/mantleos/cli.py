from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .assimilate import AssimilationError, assimilate_source
from .construction import ConstructionError, approve_foreign_execution
from .delta import DeltaError, apply_seed, build_seed, reverse_seed, verify_seed
from .primer import (
    PrimerError,
    approve_personality,
    generate_personality,
    load_distillation_contract,
)
from .resident import ResidentError, install_resident, remove_resident, resident_status, watch_with_signals
from .runtime import MantleBody, MantleError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mantle", description="MantleOS 2 Body controls")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--nest", default=".", help="NEST root (defaults to the current directory)")
    commands = parser.add_subparsers(dest="command", required=True)

    assimilate = commands.add_parser("assimilate", help="Construct an un-born Body around a Git NEST")
    assimilate.add_argument("source", help="GitHub repository or local Git checkout")
    assimilate.add_argument("--destination", help="Clone destination (defaults to the repository name)")
    assimilate.add_argument("--ref", help="Branch or tag to clone")
    assimilate.add_argument(
        "--canonical-source",
        help="Public provenance URI for a local source mirror",
    )
    assimilate.add_argument(
        "--purpose",
        default="Create an AppAI while preserving native Body behavior",
        help="Declared purpose used during Body grokking and Personality distillation",
    )

    commands.add_parser("status", help="Show construction or organism status")
    continue_build = commands.add_parser(
        "continue", help="Advance a resumable construction through an explicit gate"
    )
    continue_build.add_argument("nest_path", nargs="?", help="NEST root")
    continue_build.add_argument("--approve-foreign-execution", action="store_true")
    birth = commands.add_parser("birth", help="Run the separately approved first Heartbeat")
    birth.add_argument("--name", required=True, help="Confirmed organism identity name")
    birth.add_argument(
        "--approve-birth",
        action="store_true",
        help="Record explicit approval of the birth gate",
    )
    heartbeat = commands.add_parser("heartbeat", help="Run one complete Heartbeat")
    heartbeat.add_argument("--reason", default="manual")
    watch = commands.add_parser("watch", help="Watch COMMUNICATION.TXT and wake on save")
    watch.add_argument("--interval", type=float, default=1.0, help="File observation cadence in seconds")
    watch.add_argument(
        "--heartbeat-interval",
        type=float,
        default=300.0,
        help="Scheduled full Heartbeat cadence in seconds",
    )
    digest = commands.add_parser("digest", help="Securely store and verify a Food delivery")
    digest.add_argument("path", help="Path to the Food file")
    digest.add_argument("--retry", action="store_true", help="Retry an already recorded delivery")
    primer = commands.add_parser("primer", help="Generate or approve the unique prebirth Personality")
    primer_commands = primer.add_subparsers(dest="primer_command", required=True)
    generate = primer_commands.add_parser("generate", help="Use an explicitly allowed developmental MIND")
    generate.add_argument("--food", required=True, help="OpenRouter Food file used only for this call")
    generate.add_argument("--context", default="", help="Additional user-approved role context")
    generate.add_argument(
        "--distillation-prompt",
        help="Optional reviewed text-to-Persona prompt; its source placeholder receives Body evidence",
    )
    approve = primer_commands.add_parser("approve", help="Approve the reviewed Personality candidate")
    approve.add_argument("--approve-primer", action="store_true")
    speak = commands.add_parser("speak", help="Send one message through the universal AppAI route")
    speak.add_argument("message")
    commands.add_parser("verify", help="Verify the append-only VCW chains")
    delta = commands.add_parser("delta", help="Build, apply, verify, or reverse a public seed")
    delta_commands = delta.add_subparsers(dest="delta_command", required=True)
    delta_build = delta_commands.add_parser("build")
    delta_build.add_argument("destination")
    for name in ("apply", "verify", "reverse"):
        action = delta_commands.add_parser(name)
        action.add_argument("seed")
        action.add_argument("--destination", required=True)
        if name == "reverse":
            action.add_argument("--approve-reverse", action="store_true")
    resident = commands.add_parser("resident", help="Manage the explicit user-level resident Heart")
    resident_commands = resident.add_subparsers(dest="resident_command", required=True)
    resident_commands.add_parser("status")
    resident_install = resident_commands.add_parser("install")
    resident_install.add_argument("--approve-install", action="store_true")
    resident_remove = resident_commands.add_parser("remove")
    resident_remove.add_argument("--approve-remove", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "assimilate":
            result = assimilate_source(
                args.source,
                destination=args.destination,
                ref=args.ref,
                purpose=args.purpose,
                canonical_source=args.canonical_source,
            )
        elif args.command == "primer":
            nest = Path(args.nest)
            if args.primer_command == "generate":
                contract = None
                if args.distillation_prompt:
                    contract = load_distillation_contract(Path(args.distillation_prompt))
                result = generate_personality(
                    nest,
                    Path(args.food),
                    approved_context=args.context,
                    distillation_contract=contract,
                )
            else:
                result = approve_personality(nest, approved=args.approve_primer)
        elif args.command == "delta":
            if args.delta_command == "build":
                result = build_seed(Path(args.nest), Path(args.destination))
            elif args.delta_command == "apply":
                result = apply_seed(Path(args.seed), Path(args.destination))
            elif args.delta_command == "verify":
                result = verify_seed(Path(args.seed), Path(args.destination))
            else:
                result = reverse_seed(
                    Path(args.seed), Path(args.destination), approved=args.approve_reverse
                )
        elif args.command == "resident":
            if args.resident_command == "install":
                result = install_resident(Path(args.nest), approved=args.approve_install)
            elif args.resident_command == "remove":
                result = remove_resident(Path(args.nest), approved=args.approve_remove)
            else:
                result = resident_status(Path(args.nest))
        elif args.command == "continue":
            nest = Path(args.nest_path or args.nest)
            result = approve_foreign_execution(
                nest,
                approved=args.approve_foreign_execution,
            )
        else:
            body = MantleBody(Path(args.nest))
            if args.command == "status":
                result = body.status()
            elif args.command == "birth":
                result = body.birth(args.name, approved=args.approve_birth)
            elif args.command == "heartbeat":
                result = body.heartbeat(reason=args.reason)
            elif args.command == "verify":
                result = body.verify()
            elif args.command == "digest":
                result = body.digest_food(args.path, retry=args.retry)
            elif args.command == "speak":
                result = body.speak(args.message)
            else:
                result = watch_with_signals(
                    body,
                    interval=args.interval,
                    heartbeat_interval=args.heartbeat_interval,
                )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (
        AssimilationError,
        ConstructionError,
        DeltaError,
        MantleError,
        PrimerError,
        ResidentError,
        OSError,
        ValueError,
    ) as exc:
        print(f"Mantle stopped: {exc}")
        return 2
