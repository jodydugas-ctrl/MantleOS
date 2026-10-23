"""One public CLI, dispatching inherited operations through their existing ports."""
import argparse
import json
from pathlib import Path
import sys

from . import __version__, cells, tissue, compiled, continuity, evolution, organism, replication


def _read(path):
    from .json_contract import loads
    path = Path(path)
    if path.stat().st_size > 1_000_000:
        raise ValueError("Input exceeds contract size limit")
    return loads(path.read_text("utf-8"))


def _write_new(path, value):
    from .transactions import atomic_bytes
    atomic_bytes(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode(), replace=False)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'kpp':
        from .kpp.cli import main as kitchen_main
        return kitchen_main(argv[1:])
    # Extract only the shared Body selector; the owning parser handles everything else.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--body", type=Path)
    shared, remaining = common.parse_known_args(argv)
    command = remaining[0] if remaining else None
    own = {"demo", "new", "cell", "program", "tissue", "evolve", "continuity"}
    try:
        if command in {'examples', 'appai', 'mission'}:
            from .example_cli import main as example_main
            return example_main(remaining)
        if command and command not in own and command not in {"--help", "-h", "--version"}:
            if command == "scan":
                from .scan.cli import main as scan_main
                scan_main(remaining[1:], body=shared.body)
            else:
                from .application import main as inherited
                inherited(remaining, body=shared.body)
            return 0
        parser = argparse.ArgumentParser(prog="mantleos", description="Build living software. Body first, optional MIND.",
            epilog="Body operations: --body PATH status | verify | run | query | save | restore | recover. "
                   "Examples: examples --help, appai --help, mission --help. "
                   "Tools: kpp --help, scan --help, anchor-code --help. Use --body before or after a command.")
        parser.add_argument("--version", action="version", version=__version__)
        sub = parser.add_subparsers(dest="command", required=True)
        p = sub.add_parser("demo", help="Run the complete synthetic offline organism loop")
        p.add_argument("--output", required=True, type=Path)
        p = sub.add_parser("new", help="Construct a notebook or supplied tissue as a new Body")
        p.add_argument("--output", required=True, type=Path)
        p.add_argument("--identity", default="notebook")
        p.add_argument("--tissue", type=Path)
        for name in ("cell", "program", "tissue"):
            p = sub.add_parser(name, help="Validate a versioned logical definition")
            p.add_argument("definition", type=Path)
        p = sub.add_parser("evolve", help="Propose, validate, explicitly admit, or roll back tissue")
        es = p.add_subparsers(dest="operation", required=True)
        p = es.add_parser("propose"); p.add_argument("--tissue", required=True); p.add_argument("--output", required=True)
        p = es.add_parser("validate"); p.add_argument("proposal")
        p = es.add_parser("apply"); p.add_argument("proposal"); p.add_argument("--approve", required=True, help="Exact reviewed proposal SHA-256")
        p = es.add_parser("rollback"); p.add_argument("--revision", required=True); p.add_argument("--approve", required=True)
        p = sub.add_parser("continuity", help="Local cloud-protocol simulation; no network")
        cs = p.add_subparsers(dest="operation", required=True)
        p = cs.add_parser("sync"); p.add_argument("--store", required=True)
        p = cs.add_parser("restore"); p.add_argument("--store", required=True); p.add_argument("--output", required=True)
        args = parser.parse_args(remaining)
        body = shared.body
        if args.command in {"evolve", "continuity"} and body is None:
            parser.error("This operation requires --body PATH")
        if args.command == "new":
            result = organism.create(args.output, identity=args.identity, tissue=_read(args.tissue) if args.tissue else None)
        elif args.command == "demo":
            from .demo import run
            result = run(args.output)
        elif args.command in {"cell", "program", "tissue"}:
            validator = {"cell": cells.validate, "program": tissue.validate_program, "tissue": tissue.validate_tissue}[args.command]
            value = validator(_read(args.definition))
            result = {"result": "VALID", "schema": value["schema"], "sha256": value["sha256"], "authorized": False}
        elif args.command == "evolve":
            if args.operation == "propose":
                result = evolution.propose(body, _read(args.tissue)); _write_new(args.output, result)
            elif args.operation == "validate":
                result = evolution.validate(body, _read(args.proposal))
            elif args.operation == "apply":
                result = evolution.apply(body, _read(args.proposal), approval=args.approve)
            else:
                result = evolution.rollback(body, expected_revision=args.revision, approval=args.approve)
        elif args.command == "continuity":
            store = continuity.LocalCASStore(args.store)
            result = replication.sync(body, store) if args.operation == "sync" else replication.restore(body, store, args.output)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 1 if result.get("result") == "FAIL" else 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2
