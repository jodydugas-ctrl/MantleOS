"""Shared command surface for repository and standalone Engram Body."""
from pathlib import Path
import argparse
import json
import sys
from . import organs, cartridge
from .hosted import HostedBridge


def main(argv=None, *, body=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'kpp':
        from .kpp.cli import main as kpp_main
        return kpp_main(argv[1:])
    repo=Path(__file__).resolve().parents[2]
    body=Path(body) if body else repo/'agents/engram'
    from .scan import cli as scan_cli
    scan_arguments,scan_body=argv,body
    if len(argv)>=2 and argv[0]=='--body':
        scan_arguments,scan_body=argv[2:],Path(argv[1])
    elif argv and argv[0].startswith('--body='):
        scan_arguments,scan_body=argv[1:],Path(argv[0].split('=',1)[1])
    if scan_cli.handles(scan_arguments):
        return scan_cli.main(scan_arguments[1:],body=scan_body)
    from . import anchor_qualification_cli
    if anchor_qualification_cli.handles(argv):
        return anchor_qualification_cli.main(argv[1:])
    from . import unified_cli
    if unified_cli.handles(argv):
        return unified_cli.main(argv,body=body)
    if argv and argv[0] in {'blueprint','birth','new','restore','anchor-code','engram-image'}:
        from .cli import main as compiler
        return compiler(argv,body=body)
    parser=argparse.ArgumentParser(prog='MantleOS',epilog='Unified commands: new, clone, compile, inspect, run, query, save, restore, rebuild, recover, session, cloud. Use COMMAND --help for options.')
    parser.add_argument('--body',type=Path,default=body)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('status','systems','verify','primer'): sub.add_parser(name)
    sync=sub.add_parser('sync');sync.add_argument('--check',action='store_true');sync.add_argument('--recover',action='store_true')
    cp=sub.add_parser('engram');cs=cp.add_subparsers(dest='operation',required=True)
    ci=cs.add_parser('import');ci.add_argument('checkpoint',type=Path)
    ce=cs.add_parser('export');ce.add_argument('--output',type=Path)
    call=sub.add_parser('call');call.add_argument('capability');call.add_argument('--arguments',default='{}');call.add_argument('--arguments-file',type=Path);call.add_argument('--permit-effect',action='store_true')
    save=sub.add_parser('save');save.add_argument('--output',required=True);save.add_argument('--format',choices=('cartridge','chroma'),default='cartridge');save.add_argument('--permit-effect',action='store_true')
    package=sub.add_parser('package');package.add_argument('--output',required=True)
    for name in ('mount','bridge-open'):
        op=sub.add_parser(name);op.add_argument('--model-id',required=True);op.add_argument('--request-id',required=True);op.add_argument('--user',required=True)
    ad=sub.add_parser('bridge-advance');ad.add_argument('--model-id',required=True);ad.add_argument('--preparation',required=True);ad.add_argument('--orientation',required=True);ad.add_argument('--allow-effect',action='store_true')
    cm=sub.add_parser('bridge-commit');cm.add_argument('--model-id',required=True);cm.add_argument('--preparation',required=True);cm.add_argument('--proposal',required=True);cm.add_argument('--allow-release',action='store_true')
    args=parser.parse_args(argv);body=args.body.resolve()
    try:
        result=dispatch(args,body,repo)
    except (ValueError,PermissionError,OSError,KeyError) as exc:
        print(json.dumps({'result':'FAIL','error':str(exc)},ensure_ascii=True));raise SystemExit(2)
    print(json.dumps(result,ensure_ascii=True,indent=2))
    if isinstance(result,dict) and result.get('stage') in {'FAILED','UNKNOWN'}: raise SystemExit(3)


def dispatch(args,body,repo):
    from . import synchronization as sync, checkpoint
    command=args.command
    if command=='sync':
        if sync.repository_for(body) is None:
            from . import compiled, lifecycle, transactions
            if args.recover:
                return transactions.recover(body)
            if args.check:
                return {'result':'PASS','body':compiled.inspect(body)}
            return lifecycle.compile_existing(body)
        if args.recover: return sync.recover(sync.repository_for(body) or body)
        return sync.check(repo) if args.check else sync.synchronize(repo)
    if command=='status': return organs.status(body,{})
    if command=='systems': return organs.system_registry(body).catalog()
    if command=='verify': return cartridge.verify(body)
    if command=='primer': return organs.load_primer(body)
    if command=='package':
        if sync.repository_for(body) is None:
            from . import lifecycle
            return lifecycle.save(body,Path(args.output),format='cartridge')
        return sync.package(repo,Path(args.output))
    if command=='engram':
        if args.operation=='import':
            value=checkpoint.parse(args.checkpoint)
            return sync.synchronize(repo,checkpoint_value=value,body=body) if sync.repository_for(body) else checkpoint.import_body(body,value)
        if sync.repository_for(body): sync.check(repo)
        if args.output:
            if args.output.exists(): raise ValueError('Output already exists')
            args.output.write_text(checkpoint.render(body),encoding='utf-8')
            return {'output':str(args.output),'base':checkpoint.identity(body)}
        return {'document':checkpoint.render(body),'base':checkpoint.identity(body)}
    if command=='mount' or command.startswith('bridge-'):
        if command=='mount':
            from . import compiled
            compiled.load(body)
        reg=organs.system_registry(body).capability_registry()
        bridge=HostedBridge(body,model_id=args.model_id,registry=reg,
            broker=lambda authority,name: (authority=='release' and getattr(args,'allow_release',False)) or
                                         (authority=='effect.execute' and getattr(args,'allow_effect',False)),
            model_action_capabilities={'body.status','body.verify','engram.query','anchor.blueprint.run','project.list','project.inspect','project.verify'})
        if command in {'mount','bridge-open'}: return bridge.open(args.user,request_id=args.request_id)
        if command=='bridge-advance': result=bridge.advance(organs.load(args.preparation),organs.load(args.orientation))
        else: result=bridge.commit(organs.load(args.preparation),organs.load(args.proposal))
        if sync.repository_for(body): sync.synchronize(repo)
        return result
    if command=='call':
        name=args.capability;arguments=organs.load(args.arguments_file) if args.arguments_file else json.loads(args.arguments)
    elif command=='save': name='body.save';arguments={'output':args.output,'format':args.format}
    else: raise ValueError('Unknown command')
    result=organs.invoke(body,name,arguments,permit=args.permit_effect)
    if sync.repository_for(body): sync.synchronize(repo)
    return result
