"""Read-only investigator commands; no operational Body or ledger mutation."""
import argparse
import json
from pathlib import Path
from .common import ScanError, outside, read_json

COMMANDS = {"capabilities", "inspect", "discover", "inspection", "trace", "diff", "view", "plan", "work-order", "lenses", "providers", "evidence", "verify-evidence", "observe", "dossier", "compact", "experiment", "chase"}


def handles(argv):
    if len(argv) < 2 or argv[0] != "scan" or argv[1] not in COMMANDS:
        return False
    return True


def _output(path, value, reports=(), inputs=(), *, body=None):
    if path is None:
        return
    from ..kernel import scan as dispatch
    # Anchor qualification also uses this helper with a source-root guard only.
    roots = [report['source_root'] for report in reports if isinstance(report,dict) and set(report) == {'source_root'}]
    snapshots = [report for report in reports if not isinstance(report,dict) or set(report) != {'source_root'}]
    dispatch('scan.export',{'output':str(path),'value':value,'reports':snapshots,'source_roots':roots,'inputs':list(inputs)},body=body,permit=True)


def main(argv=None, *, body=None):
    from ..kernel import scan as dispatch
    def native(operation,arguments,permit=True):
        return dispatch('scan.' + operation,arguments,body=body,permit=permit)['observation']['result']
    def output(path,value,reports=(),inputs=()):
        return _output(path,value,reports,inputs,body=body)
    parser = argparse.ArgumentParser(prog="MantleOS scan", description="Bounded static evidence; specimen code is never executed")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Read source and write an offline scan dossier outside it")
    inspect.add_argument("source"); inspect.add_argument("--workspace", required=True)
    inspect.add_argument("--max-files", type=int, default=1000)
    inspect.add_argument("--max-bytes", type=int, default=16_000_000)
    inspect.add_argument("--max-file-bytes", type=int, default=512_000)
    inspect.add_argument("--max-seconds", type=int, default=60)
    inspect.add_argument("--max-nodes", type=int, default=100000)
    inspect.add_argument("--provider-policy", help="Explicit optional provider policy outside source")
    inspect.add_argument("--allow-external", action="store_true", help="Permit a policy-pinned optional host parser for this invocation")
    inspect.add_argument('--filter', dest='filters', action='append', choices=('code','interface','data'))
    inspect.add_argument('--execution', choices=('serial','parallel'), default='serial')
    from .inspection import VIEWS
    inspect.add_argument('--view', choices=tuple(VIEWS), default='all')
    inspect.add_argument('--detail', choices=('summary','full'), default='summary')
    inspect.add_argument('--target', default='.')
    inspect.add_argument('--max-items', type=int, default=2000)
    discovery = sub.add_parser('discover', help='Pinned code and interface views from one scan on one checked source revision')
    discovery.add_argument('source'); discovery.add_argument('--output', required=True)
    discovery.add_argument('--identity', required=True); discovery.add_argument('--gui-root')
    discovery.add_argument('--execution', choices=('parallel','serial'), default='parallel', help='Serial provides an equivalent-scope timing baseline')
    for name, default in (('files',1000),('bytes',16_000_000),('file-bytes',512_000),('seconds',60),('nodes',100_000)):
        discovery.add_argument('--max-' + name, type=int, default=default)
    inspection = sub.add_parser('inspection', help='Select inspection settings over an existing verified SCAN snapshot')
    inspection.add_argument('report')
    inspection.add_argument('--view', choices=tuple(VIEWS), default='all')
    inspection.add_argument('--detail', choices=('summary','full'), default='summary')
    inspection.add_argument('--target', default='.')
    inspection.add_argument('--max-items', type=int, default=2000)
    inspection.add_argument('--output')
    tracing = sub.add_parser("trace", help="Follow labeled possible static paths from a symbol or keyword question")
    tracing.add_argument("report"); tracing.add_argument("selector")
    tracing.add_argument("--direction", choices=("dependencies", "impact"), default="dependencies")
    tracing.add_argument("--max-depth", type=int, default=6)
    tracing.add_argument("--max-nodes", type=int, default=256)
    tracing.add_argument("--max-edges", type=int, default=512)
    tracing.add_argument("--edge-kind", action="append")
    comparison = sub.add_parser("diff", help="Compare snapshots and export a bounded static change-impact dossier")
    comparison.add_argument("before"); comparison.add_argument("after")
    comparison.add_argument("--max-items", type=int, default=5000)
    comparison.add_argument("--max-candidates", type=int, default=1000)
    comparison.add_argument("--impact-nodes", type=int, default=256)
    filtered = sub.add_parser("view", help="Filter one snapshot using an existing lens")
    filtered.add_argument("report"); filtered.add_argument("--lens", default="structure")
    filtered.add_argument("--workspace", default=".")
    order = sub.add_parser("work-order", help="Export static hypotheses and the versioned candidate-work contract")
    order.add_argument("report"); order.add_argument("--objective", default="Investigate source-bound static hypotheses")
    planning = sub.add_parser('plan',help='Native optimization hypotheses; no specimen execution')
    planning.add_argument('report'); planning.add_argument('--objective',default='Reduce repeated work while preserving behavior')
    sub.add_parser('capabilities',help='Native interfaces and explicit coverage limits')
    compact = sub.add_parser('compact',help='Create a separately authorized compact analysis artifact')
    compact.add_argument('source'); compact.add_argument('--output',required=True); compact.add_argument('--permit-effect',action='store_true')
    experiment = sub.add_parser('experiment',help='Explicit bounded comparison in disposable copies')
    experiment.add_argument('specification'); experiment.add_argument('--baseline',required=True); experiment.add_argument('--candidate',required=True); experiment.add_argument('--output',required=True); experiment.add_argument('--permit-effect',action='store_true')
    chase = sub.add_parser('chase',help='Pinned targets and scoped fixture qualification')
    chase_sub = chase.add_subparsers(dest='chase_command',required=True)
    for operation in ('add','list','qualify','assess'):
        command = chase_sub.add_parser(operation); command.add_argument('--workspace',required=True)
        if operation == 'add': command.add_argument('--record',required=True)
        elif operation != 'list': command.add_argument('target_id'); command.add_argument('receipt')
    catalog = chase_sub.add_parser('catalog',help='External revisioned Capability Chase; proposals have no integration authority')
    catalog_sub = catalog.add_subparsers(dest='catalog_command',required=True)
    for operation in ('seed','list','observe','scorecard','propose','transition','link','learning','refresh','dashboard'):
        command = catalog_sub.add_parser(operation); command.add_argument('--workspace',required=True)
        if operation not in ('list','scorecard','learning'):
            command.add_argument('--permit-effect',action='store_true')
        if operation in ('seed','observe','propose'): command.add_argument('--file',required=True)
        if operation == 'observe': command.add_argument('--challenge-id',required=True)
        if operation not in ('seed','list','scorecard','learning'):
            command.add_argument('--expected-revision',type=int,required=True)
        if operation in ('transition','link'): command.add_argument('--proposal-id',required=True)
        if operation == 'transition':
            command.add_argument('--status',choices=('READY_FOR_EXPERIMENT','REJECTED'),required=True)
            command.add_argument('--binding')
        if operation == 'link':
            command.add_argument('--receipt',required=True); command.add_argument('--receipt-sha256',required=True)
            command.add_argument('--baseline',required=True); command.add_argument('--candidate',required=True)
        if operation == 'refresh':
            command.add_argument('--target-id',required=True); command.add_argument('--permit-fetch',action='store_true')
            command.add_argument('--declared-revision',default='UNVERIFIED'); command.add_argument('--license',default='UNVERIFIED')
        if operation == 'dashboard': command.add_argument('--app-workspace',required=True); command.add_argument('--output',required=True)
    sub.add_parser("lenses", help="List the built-in read-only filters")
    sub.add_parser("providers", help="List versioned optional capabilities without probing or enabling tools")
    dossier = sub.add_parser("dossier", help="Verify and summarize evidence → DRAFT Blueprint → declared fixture gates")
    dossier.add_argument("report"); dossier.add_argument("--source", required=True)
    dossier.add_argument("--evidence", action="append", required=True); dossier.add_argument("--trace")
    dossier.add_argument("--specification"); dossier.add_argument("--contract"); dossier.add_argument("--contract-sha")
    dossier.add_argument("--candidate"); dossier.add_argument("--conformance")
    dossier.add_argument("--runtime-receipt", action="append", default=[]); dossier.add_argument("--authorization")
    dossier.add_argument("--output", required=True); dossier.add_argument("--html")
    evidence = sub.add_parser("evidence", help="Export verified byte-bound evidence; references confer no promotion authority")
    evidence.add_argument("report"); evidence.add_argument("--node", action="append", default=[])
    evidence.add_argument("--edge", action="append", default=[])
    evidence.add_argument("--runtime-receipt"); evidence.add_argument("--authorization")
    evidence.add_argument("--output", required=True)
    verification = sub.add_parser("verify-evidence", help="Check receipt identity, context, bytes, expiry and independently authorized run")
    verification.add_argument("receipt"); verification.add_argument("report")
    verification.add_argument("--source", required=True)
    verification.add_argument("--parent-id", action="append", default=[])
    verification.add_argument("--runtime-receipt"); verification.add_argument("--authorization")
    observation = sub.add_parser("observe", help="Explicit trusted command in a disposable copy; this is not an OS sandbox")
    observation.add_argument("report"); observation.add_argument("--command-json", required=True)
    observation.add_argument("--permit-execution", action="store_true")
    observation.add_argument("--output", required=True); observation.add_argument("--authorization-output", required=True)
    for command in (tracing, comparison, filtered, order, planning):
        command.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == 'discover':
            result = native('discover', {'source':args.source,'output':args.output,'identity':args.identity,
                            'gui_root':args.gui_root,'execution':args.execution,'max_files':args.max_files,
                            'max_bytes':args.max_bytes,'max_file_bytes':args.max_file_bytes,
                            'max_seconds':args.max_seconds,'max_nodes':args.max_nodes})
        elif args.command == "inspect":
            report = native('snapshot',{'source':args.source,'workspace':args.workspace,'max_files':args.max_files,'max_bytes':args.max_bytes,
                            'max_file_bytes':args.max_file_bytes,'max_seconds':args.max_seconds,'max_nodes':args.max_nodes,'filters':args.filters,'execution':args.execution,
                            'provider_policy':args.provider_policy,'allow_external':args.allow_external,
                            'settings':{'view':args.view,'detail':args.detail,'target':args.target,'max_items':args.max_items}})['report']
            result = {"schema": "mantle.scan-inspect/1", "result": "PASS", "graph_digest": report["graph_digest"],
                      "workspace": str(Path(args.workspace).resolve()), "files": len(report["graph"]["files"]),
                      "coverage_gaps": len(report["graph"]["gaps"]), "specimen_executed": False}
        elif args.command == "dossier":
            from .dossier import render
            from ..anchor_qualification_cli import runtime_inputs, source_text
            inputs = [args.report, *args.evidence, *args.runtime_receipt] + [item for item in (
                args.trace, args.specification, args.contract, args.candidate, args.conformance, args.authorization) if item]
            if len(args.evidence) > 64: raise ScanError("Dossier evidence input budget exceeded")
            report = read_json(args.report)
            if args.html and Path(args.html).resolve() == Path(args.output).resolve(): raise ScanError("Dossier JSON and HTML need distinct outputs")
            for target in (args.output, args.html):
                if target:
                    outside(target, args.source); outside(target, report["source_root"])
                    if Path(target).resolve() in {Path(item).resolve() for item in inputs}: raise ScanError("Dossier output cannot overwrite an input")
            runs, authorization = runtime_inputs(args.runtime_receipt, args.authorization)
            result = native('dossier',{'report':report,'source':args.source,'receipts':[read_json(path,limit=8_000_000) for path in args.evidence],
                           'feature_trace':read_json(args.trace) if args.trace else None,
                           'specification':read_json(args.specification,limit=8_000_000) if args.specification else None,
                           'contract':read_json(args.contract,limit=4_000_000) if args.contract else None,'expected_contract_sha256':args.contract_sha,
                           'candidate':source_text(args.candidate) if args.candidate else None,
                           'conformance':read_json(args.conformance,limit=8_000_000) if args.conformance else None,
                           'runtime_receipts':runs,'authorized_runs':authorization})
            output(args.output, result, (report,), inputs)
            if args.html: output(args.html, render(result), (report,), inputs)
        elif args.command == "inspection":
            report = read_json(args.report)
            result = native('inspection',{'report':report,'settings':{'view':args.view,
                'detail':args.detail,'target':args.target,'max_items':args.max_items}})
            output(args.output, result, (report,), (args.report,))
        elif args.command in ('capabilities','providers','lenses'):
            result = native(args.command,{})
        elif args.command == 'compact':
            result = native('compact',{'source':args.source,'output':args.output},args.permit_effect)
        elif args.command == 'experiment':
            result = native('experiment',{'baseline':args.baseline,'candidate':args.candidate,'specification':read_json(args.specification),'output':args.output},args.permit_effect)
        elif args.command == 'chase':
            if args.chase_command == 'catalog':
                operation = 'read' if args.catalog_command == 'list' else args.catalog_command
                values = {'workspace':args.workspace}
                if operation in ('seed','observe','propose'):
                    values[{'seed':'catalog','observe':'observation','propose':'proposal'}[operation]] = args.file
                if operation == 'observe': values['challenge_id'] = args.challenge_id
                if operation not in ('seed','read','scorecard','learning'): values['expected_revision'] = args.expected_revision
                if operation in ('transition','link'): values['proposal_id'] = args.proposal_id
                if operation == 'transition':
                    values['status'] = args.status
                    if args.binding: values['binding'] = args.binding
                if operation == 'link': values.update(receipt=args.receipt,expected_receipt_sha256=args.receipt_sha256,baseline=args.baseline,candidate=args.candidate)
                if operation == 'refresh': values.update(target_id=args.target_id,permit_fetch=args.permit_fetch,declared_revision=args.declared_revision,license=args.license)
                if operation == 'dashboard':
                    outside(args.output,args.workspace); outside(args.output,args.app_workspace)
                    values['app_workspace'] = args.app_workspace
                result = native('chase.catalog.' + operation,values,getattr(args,'permit_effect',True))
                if operation == 'dashboard':
                    output(args.output,result['html'])
                    result = {'schema':'mantle.chase.dashboard-export/2','output':args.output,
                              'app_revision':result['snapshot']['revision'],'authority':'NONE','render_status':'NOT_OBSERVED'}
            else:
                operation = 'targets' if args.chase_command == 'list' else args.chase_command
                values = {'workspace':args.workspace}
                if operation == 'add': values['record'] = args.record
                elif operation != 'targets': values.update(target_id=args.target_id,receipt=args.receipt)
                result = native('chase.' + operation,values)
        elif args.command == "diff":
            reports = [read_json(args.before), read_json(args.after)]
            result = native('diff',{'before':reports[0],'after':reports[1],'max_items':args.max_items,'max_candidates':args.max_candidates,'impact_nodes':args.impact_nodes})
            output(args.output, result, reports, (args.before, args.after))
        elif args.command in ("evidence", "verify-evidence", "observe"):
            from .common import digest
            from .providers import fields, HEX
            report = read_json(args.report)
            source = report["source_root"]
            if args.command == "observe":
                if Path(args.output).resolve() == Path(args.authorization_output).resolve():
                    raise ScanError("Observation and its trusted authorization record need distinct output paths")
                inputs = (args.report, args.command_json)
                # Validate destinations before executing the operator's command.
                for target in (args.output, args.authorization_output):
                    outside(target, source)
                    if Path(target).resolve() in {Path(item).resolve() for item in inputs}:
                        raise ScanError("Observation output cannot overwrite its inputs")
                command = read_json(args.command_json, limit=64_000)
                fields(command, ("command",), ("timeout_seconds", "output_bytes"))
                if body:
                    outside(args.output,body); outside(args.authorization_output,body)
                result = native('observe',{'report':report,'command':command['command'],'permit_execution':args.permit_execution,
                                 'timeout':command.get('timeout_seconds',20),'output_limit':command.get('output_bytes',1_000_000)})
                authorization = {"schema": "scan.observation-authorization/1", "runs": {result["run_id"]: digest(result)}}
                output(args.output, result, (report,), inputs)
                output(args.authorization_output, authorization, (report,), inputs)
            else:
                runs, authorization = {}, {}
                if bool(args.runtime_receipt) != bool(args.authorization):
                    raise ScanError("Runtime verification needs both a receipt and a separately trusted authorization file")
                if args.runtime_receipt:
                    if Path(args.runtime_receipt).resolve() == Path(args.authorization).resolve():
                        raise ScanError("Authorization cannot be supplied by the runtime receipt itself")
                    run = read_json(args.runtime_receipt, limit=8_000_000)
                    auth = read_json(args.authorization, limit=64_000)
                    fields(auth, ("schema", "runs"))
                    if auth["schema"] != "scan.observation-authorization/1" or not isinstance(auth["runs"], dict) or len(auth["runs"]) > 1000 or any(
                            not isinstance(key, str) or not isinstance(value, str) or not HEX.fullmatch(value) for key, value in auth["runs"].items()):
                        raise ScanError("Invalid independently trusted observation authorization file")
                    runs, authorization = {run["run_id"]: run}, auth["runs"]
                if args.command == "evidence":
                    if runs:
                        if args.node or args.edge: raise ScanError("Export static and runtime assertions in separate envelopes")
                        result = native('evidence',{'report':report,'runtime_receipt':run,'authorized_runs':authorization})
                    else: result = native('evidence',{'report':report,'node_ids':args.node,'edge_ids':args.edge})
                    inputs = [args.report] + ([args.runtime_receipt, args.authorization] if runs else [])
                    output(args.output, result, (report,), inputs)
                else:
                    receipt = read_json(args.receipt, limit=8_000_000)
                    result = native('verify-evidence',{'receipt':receipt,'report':report,'source':args.source,'parent_ids':args.parent_id,
                                             'runtime_receipts':runs,'authorized_runs':authorization})
        else:
            report = read_json(args.report)
            if args.command == "trace":
                result = native('trace',{'report':report,'selector':args.selector,'direction':args.direction,'max_depth':args.max_depth,
                               'max_nodes':args.max_nodes,'max_edges':args.max_edges,'edge_kinds':args.edge_kind})
            elif args.command == "view":
                result = native('view',{'report':report,'workspace':args.workspace,'lens':args.lens})
            elif args.command == 'plan':
                result = native('plan',{'report':report,'objective':args.objective})
            else:
                result = native('work-order',{'report':report,'objective':args.objective})['text']
            output(args.output, result, (report,), (args.report,))
        display = result
        if args.command == "dossier":
            display = {"schema": result["schema"], "sha256": result["sha256"], "artifacts": len(result["artifacts"]),
                       "qualification": result["qualification"], "promotion_authority": False, "release_authority": False}
        print(json.dumps(display, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError) as error:
        print(json.dumps({"schema": "mantle.scan-cli-error/1", "result": "FAIL", "error": str(error)[:500]}))
        raise SystemExit(2)
