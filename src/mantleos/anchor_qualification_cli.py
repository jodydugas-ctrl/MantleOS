"""Standalone contract/specification/conformance artifacts; no Body writes."""
import argparse
import json
from pathlib import Path
from . import anchor_qualification as aq
from .scan.cli import _output
from .scan.common import ScanError, read_json
from .scan.providers import fields, HEX

COMMANDS = {"freeze-contract", "specify", "qualify", "verify-conformance", "review", "profiles"}


def handles(argv):
    return len(argv) >= 2 and argv[0] == "anchor" and argv[1] in COMMANDS and (
        len(argv) == 2 if argv[1] == "profiles" else len(argv) > 2 and not argv[2].startswith("-"))


def source_text(path):
    with Path(path).open("rb") as stream: value = stream.read(65537)
    if len(value) > 65536: raise ScanError("Candidate source byte budget exceeded")
    return value.decode("utf-8")


def runtime_inputs(paths, authorization_path):
    runs, authorization = {}, {}
    if bool(paths) != bool(authorization_path):
        raise ScanError("Runtime evidence needs a separate operator authorization file")
    if paths:
        auth = read_json(authorization_path, limit=64_000); fields(auth, ("schema", "runs"))
        if auth["schema"] != "scan.observation-authorization/1" or not isinstance(auth["runs"], dict) or len(auth["runs"]) > 1000 or any(not isinstance(value, str) or not HEX.fullmatch(value) for value in auth["runs"].values()):
            raise ScanError("Invalid runtime authorization file")
        if len(paths) > 64: raise ScanError("Runtime observation input budget exceeded")
        for path in paths:
            run = read_json(path, limit=8_000_000)
            if run["run_id"] in runs: raise ScanError("Duplicate runtime observation")
            if Path(path).resolve() == Path(authorization_path).resolve(): raise ScanError("Run cannot authorize itself")
            runs[run["run_id"]] = run
        authorization = auth["runs"]
    return runs, authorization


def main(argv):
    parser = argparse.ArgumentParser(prog="MantleOS anchor", description="Contract-first artifacts; exact fixtures confer no host authority")
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze-contract"); freeze.add_argument("contract")
    spec = sub.add_parser("specify"); spec.add_argument("report"); spec.add_argument("--source", required=True)
    spec.add_argument("--evidence", action="append", required=True); spec.add_argument("--id", required=True)
    spec.add_argument("--name", required=True); spec.add_argument("--purpose", required=True)
    spec.add_argument("--runtime-receipt", action="append", default=[]); spec.add_argument("--authorization")
    execution = sub.add_parser("qualify"); execution.add_argument("candidate"); execution.add_argument("--specification")
    execution.add_argument("--report"); execution.add_argument("--source"); execution.add_argument("--evidence", action="append", default=[])
    execution.add_argument("--runtime-receipt", action="append", default=[]); execution.add_argument("--authorization")
    execution.add_argument("--permit-profile-execution", action="store_true"); execution.add_argument("--max-seconds", type=int, default=30)
    verify = sub.add_parser("verify-conformance"); verify.add_argument("candidate"); verify.add_argument("--receipt", required=True)
    review = sub.add_parser("review"); review.add_argument("candidate"); review.add_argument("--receipt", required=True)
    review.add_argument("--human-review", required=True); review.add_argument("--trusted-run-sha", required=True)
    review.add_argument("--trusted-review-sha", required=True)
    sub.add_parser("profiles")
    for command in (spec, execution, verify, review):
        command.add_argument("--contract", required=True); command.add_argument("--contract-sha", required=True)
    for command in (freeze, spec, execution, review): command.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "profiles": result = aq.profile_catalog()
        elif args.command == "freeze-contract":
            result = aq.freeze_contract(read_json(args.contract, limit=4_000_000))
            _output(args.output, result, inputs=(args.contract,))
        else:
            contract = read_json(args.contract, limit=4_000_000)
            if args.command == "specify":
                report = read_json(args.report)
                receipts = [read_json(path, limit=8_000_000) for path in args.evidence]
                runs, authorization = runtime_inputs(args.runtime_receipt, args.authorization)
                result = aq.specification(report, args.source, receipts, contract, blueprint_id=args.id, name=args.name,
                                          purpose=args.purpose, expected_contract_sha256=args.contract_sha,
                                          runtime_receipts=runs, authorized_runs=authorization)
                inputs = [args.report, args.contract, *args.evidence, *args.runtime_receipt] + ([args.authorization] if args.authorization else [])
                _output(args.output, result, (report,), inputs)
            else:
                candidate = source_text(args.candidate)
                inputs = [args.candidate, args.contract]
                if args.command == "qualify":
                    spec_sha = None
                    runs, authorization = runtime_inputs(args.runtime_receipt, args.authorization)
                    if args.runtime_receipt and not args.specification:
                        raise ScanError("Runtime inputs require an evidence-bound specification")
                    if args.specification:
                        spec_value = read_json(args.specification, limit=8_000_000)
                        if spec_value.get("schema") != "anchor.specification/1" or spec_value.get("sha256") != aq.digest({key: value for key, value in spec_value.items() if key != "sha256"}) or spec_value.get("contract_sha256") != args.contract_sha or spec_value.get("status") != "CANDIDATE_ONLY":
                            raise ScanError("Specification/contract identity mismatch")
                        spec_sha = spec_value["sha256"]; inputs.append(args.specification)
                        if not args.report or not args.source or not args.evidence:
                            raise ScanError("Specification qualification needs its source report and evidence receipts for live verification")
                        report = read_json(args.report)
                        receipts = [read_json(path, limit=8_000_000) for path in args.evidence]
                        aq.verify_specification(spec_value, report, args.source, receipts, contract, expected_contract_sha256=args.contract_sha,
                                                runtime_receipts=runs, authorized_runs=authorization)
                        inputs.extend([args.report, *args.evidence])
                        inputs.extend(args.runtime_receipt)
                        if args.authorization: inputs.append(args.authorization)
                    # Destinations must be acceptable before bounded interpretation.
                    from .scan.common import outside
                    outside(args.output, Path(args.candidate).resolve().parent)
                    if Path(args.output).resolve() in {Path(item).resolve() for item in inputs}: raise ScanError("Conformance output cannot overwrite inputs")
                    result = aq.qualify(candidate, contract, expected_contract_sha256=args.contract_sha,
                                        permit_execution=args.permit_profile_execution, specification_sha256=spec_sha, max_seconds=args.max_seconds)
                    aq.verify_conformance(result, candidate, contract, expected_contract_sha256=args.contract_sha)
                    if args.specification:
                        aq.verify_specification(spec_value, report, args.source, receipts, contract, expected_contract_sha256=args.contract_sha,
                                                runtime_receipts=runs, authorized_runs=authorization)
                else:
                    receipt = read_json(args.receipt, limit=8_000_000); inputs.append(args.receipt)
                    if args.command == "verify-conformance":
                        result = aq.verify_conformance(receipt, candidate, contract, expected_contract_sha256=args.contract_sha)
                    else:
                        human_review = read_json(args.human_review, limit=64_000); inputs.append(args.human_review)
                        result = aq.review_program(receipt, candidate, contract, human_review, expected_contract_sha256=args.contract_sha,
                                                   trusted_run_sha256=args.trusted_run_sha, trusted_review_sha256=args.trusted_review_sha)
                if args.command != "verify-conformance":
                    _output(args.output, result, ({"source_root": str(Path(args.candidate).resolve().parent)},), inputs)
        summary = {key: result[key] for key in ("schema", "status", "sha256", "result", "scope", "promotion", "authority", "requires_human_review") if key in result}
        if args.command == "profiles": summary = result
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError, RecursionError) as error:
        print(json.dumps({"schema": "mantle.anchor-qualification-error/1", "result": "FAIL", "error": str(error)[:500]}))
        raise SystemExit(2)
