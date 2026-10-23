"""Examples, AppAI construction, and operator mission controls on the main CLI."""
import argparse
import json

from . import appai, examples, missions


def main(argv):
    parser = argparse.ArgumentParser(prog='mantleos ' + argv[0])
    sub = parser.add_subparsers(dest='operation', required=True)
    group = argv[0]
    if group == 'examples':
        sub.add_parser('list')
        p = sub.add_parser('build'); p.add_argument('name', choices=examples.CATALOG)
        p.add_argument('--output', required=True); p.add_argument('--source')
        p = sub.add_parser('run'); p.add_argument('name', choices=examples.CATALOG)
        p.add_argument('--directory', required=True); p.add_argument('--source'); p.add_argument('--message')
        p.add_argument('--request-id'); p.add_argument('--model-id', default='CURRENT_HOST')
        p.add_argument('--port', type=int, default=0); p.add_argument('--ticks', type=int, default=1)
        p = sub.add_parser('demo'); p.add_argument('--output', required=True)
    elif group == 'appai':
        for op in ('inspect', 'verify', 'birth', 'activate', 'stasis', 'tick', 'run', 'reverse'):
            p = sub.add_parser(op); p.add_argument('--nest', required=True)
            if op == 'activate': p.add_argument('--allow-tool', action='append', default=[])
            if op == 'run':
                p.add_argument('--ticks', type=int, default=1); p.add_argument('--interval', type=float, default=1)
                p.add_argument('--policy'); p.add_argument('--request-id')
    elif group == 'mission':
        p = sub.add_parser('authorize'); p.add_argument('--nest', required=True)
        p.add_argument('--source', required=True); p.add_argument('--representatives', required=True)
        p.add_argument('--approve', action='store_true'); p.add_argument('--ttl', type=int, default=3600)
        p.add_argument('--duration', type=int, default=60)
        p = sub.add_parser('dispatch'); p.add_argument('--nest', required=True)
        p.add_argument('--policy', required=True); p.add_argument('--request-id', required=True)
        p = sub.add_parser('revoke'); p.add_argument('--nest', required=True); p.add_argument('--policy', required=True)
        for op in ('inspect', 'run', 'review', 'admit', 'recover'):
            p = sub.add_parser(op); p.add_argument('--nest', required=True); p.add_argument('mission_id')
            if op == 'admit': p.add_argument('--approve', required=True)
    args = parser.parse_args(argv[1:])
    op = args.operation
    if group == 'examples':
        if op == 'list': result = examples.CATALOG
        elif op == 'build': result = examples.build(args.name, args.output, source=args.source)
        elif op == 'demo': result = examples.demo(args.output)
        elif args.name == 'notepad': return examples.serve_notepad(args.directory, port=args.port)
        elif args.name == 'hermes': result = appai.run(args.directory, ticks=args.ticks)
        elif args.name == 'observer':
            if not args.source or not args.request_id: parser.error('Observer needs --source and --request-id')
            result = examples.observe(args.directory, args.source, request_id=args.request_id)
        else:
            if not args.message or not args.request_id: parser.error('Engram needs --message and --request-id')
            result = examples.handoff(args.directory, args.message, request_id=args.request_id, model_id=args.model_id)
    elif group == 'appai':
        if op == 'inspect': result = appai.status(args.nest)
        elif op == 'activate': result = appai.phase(args.nest, True, allowed_tools=args.allow_tool)
        elif op == 'stasis': result = appai.phase(args.nest, False)
        elif op == 'run': result = appai.run(args.nest, ticks=args.ticks, interval=args.interval,
                                             policy_id=args.policy, request_id=args.request_id)
        else: result = getattr(appai, op)(args.nest)
    else:
        if op == 'authorize':
            result = missions.authorize(args.nest, args.source, args.representatives,
                                        approved=args.approve, ttl=args.ttl, duration=args.duration)
        elif op == 'dispatch': result = missions.dispatch(args.nest, args.policy, request_id=args.request_id)
        elif op == 'revoke': result = missions.revoke(args.nest, args.policy)
        elif op == 'admit': result = missions.admit(args.nest, args.mission_id, approval=args.approve)
        else: result = getattr(missions, op)(args.nest, args.mission_id)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0
