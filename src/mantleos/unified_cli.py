"""Unified lifecycle commands over the same providers used by Bio-Software."""
import argparse
import json
import sqlite3
import zipfile
from pathlib import Path

from . import compiled, lifecycle, sessions, storage, transactions

COMMANDS={'new','create','clone','compile','inspect','run','query','save','restore','rebuild','recover','session','cloud'}


def handles(argv):
    args=list(argv)
    if args[:1]==['--body'] and len(args)>2:args=args[2:]
    return bool(args and args[0] in COMMANDS)


def main(argv,*,body):
    parser=argparse.ArgumentParser(prog='MantleOS',description='Unified Bio-Software lifecycle')
    parser.add_argument('--body',type=Path,default=body)
    sub=parser.add_subparsers(dest='command',required=True)
    def command(name):
        p=sub.add_parser(name);p.add_argument('--body',type=Path,default=argparse.SUPPRESS);return p
    for name in ('new','create','clone'):
        p=command(name);spec=p.add_mutually_exclusive_group(required=True)
        spec.add_argument('--birth');spec.add_argument('--template')
        p.add_argument('--output',required=True);p.add_argument('--programs');p.add_argument('--blueprint')
        p.add_argument('--cartridge-id');p.add_argument('--parent');p.add_argument('--inherit-memory',action='store_true')
        p.add_argument('--format',choices=['cartridge','chroma']);p.add_argument('--nest')
    command('compile');command('inspect');command('recover')
    p=command('run');p.add_argument('program');p.add_argument('--inputs',default='{}');p.add_argument('--inputs-file')
    p.add_argument('--commit',action='store_true');p.add_argument('--request-id');p.add_argument('--expected-head')
    p=command('query');p.add_argument('text',nargs='?',default='');p.add_argument('--record-id');p.add_argument('--limit',type=int,default=8)
    p.add_argument('--type',action='append',dest='types');p.add_argument('--include-superseded',action='store_true');p.add_argument('--head');p.add_argument('--evidence',action='store_true')
    p=command('save');p.add_argument('--output',required=True);p.add_argument('--format',choices=['cartridge','chroma'],default='cartridge')
    p.add_argument('--nest');p.add_argument('--permit-effect',action='store_true',help='Explicitly authorize snapshot publication')
    p=command('restore');p.add_argument('archive');p.add_argument('--output',required=True);p.add_argument('--nest');p.add_argument('--sha256')
    p=command('rebuild');p.add_argument('--programs');p.add_argument('--birth');p.add_argument('--allow-identity-change',action='store_true');p.add_argument('--expected-head')
    p=command('cloud');p.add_argument('operation',choices=['login']);p.add_argument('--nest',required=True)
    client=p.add_mutually_exclusive_group(required=True);client.add_argument('--client-id');client.add_argument('--client-config')
    p=command('session');ss=p.add_subparsers(dest='operation',required=True)
    for name in ('start','show','advance','cancel','export','import','accept','dispatch','recover'):
        s=ss.add_parser(name);s.add_argument('--nest',required=True)
        if name not in {'start','import'}:s.add_argument('session_id')
        if name in {'start','import'}:s.add_argument('--program',required=True);s.add_argument('--timeout',type=int,default=300)
        if name=='start':s.add_argument('--task',required=True);s.add_argument('--model-id',default='unbound');s.add_argument('--max-attempts',type=int,default=3)
        if name=='import':s.add_argument('--input',required=True)
        if name=='advance':s.add_argument('--reply',required=True)
        if name in {'advance','dispatch'}:s.add_argument('--allow-lookup',action='store_true')
        if name=='export':s.add_argument('--output',required=True)
        if name=='accept':s.add_argument('--evidence',required=True)
        if name=='dispatch':
            s.add_argument('--runner',required=True,help='JSON file containing an operator-controlled executable argument list')
            s.add_argument('--timeout',type=int,default=30);s.add_argument('--max-bytes',type=int,default=262144)
    args=parser.parse_args(argv)
    try:
        result=dispatch(args)
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error,zipfile.BadZipFile) as exc:
        print(json.dumps({'result':'FAIL','error':str(exc)},ensure_ascii=True));raise SystemExit(2)
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return result


def dispatch(args):
    body=Path(args.body).resolve();cmd=args.command
    if cmd in {'new','create','clone'}:
        birth=compiled.read_json(args.birth or args.template)
        bp=compiled.read_json(args.blueprint) if args.blueprint else None
        parent=args.parent or (body if cmd=='clone' else None)
        if args.inherit_memory and parent is None:raise ValueError('Memory inheritance requires a parent')
        return lifecycle.create(birth,args.output,blueprint=bp,cartridge_id=args.cartridge_id,programs=args.programs,
                                parent=parent,inherit_memory=args.inherit_memory,nest=args.nest,
                                format=args.format)
    if cmd=='compile':return lifecycle.compile_existing(body)
    if cmd=='inspect':
        with transactions.body_lock(body):return compiled.inspect(body)
    if cmd=='query':
        with transactions.body_lock(body):
            return compiled.query(body,args.text,record_id=args.record_id,limit=args.limit,types=args.types,include_superseded=args.include_superseded,head=args.head,evidence=args.evidence)
    if cmd=='run':return lifecycle.run(body,args.program,compiled.read_json(args.inputs_file) if args.inputs_file else compiled.json_contract.loads(args.inputs),
                                      commit=args.commit,request_id=args.request_id,expected_head=args.expected_head)
    if cmd=='save':
        if not args.permit_effect:raise PermissionError('Explicit --permit-effect required')
        return lifecycle.save(body,args.output,format=args.format,nest=args.nest)
    if cmd=='restore':return lifecycle.restore(args.archive,args.output,nest=args.nest,expected_sha256=args.sha256)
    if cmd=='rebuild':return lifecycle.rebuild(body,programs=args.programs,birth=compiled.read_json(args.birth) if args.birth else None,
                                             allow_identity_change=args.allow_identity_change,expected_head=args.expected_head)
    if cmd=='recover':return transactions.recover(body)
    if cmd=='cloud':
        if Path(args.nest).resolve().is_relative_to(body):raise ValueError('NEST must be outside portable Body')
        config=compiled.read_json(args.client_config).get('installed',{}) if args.client_config else {'client_id':args.client_id}
        if not config.get('client_id'):raise ValueError('Expected a Google desktop installed-client configuration')
        return storage.authorize(args.nest,config['client_id'],client_secret=config.get('client_secret'))
    if cmd=='session':
        op=args.operation
        if op=='start':return sessions.start(body,args.program,args.task,nest=args.nest,timeout=args.timeout,max_attempts=args.max_attempts,model_id=args.model_id)
        if op=='import':return sessions.import_handoff(body,args.program,args.input,nest=args.nest,timeout=args.timeout)
        if op=='show':return sessions.inspect(args.nest,args.session_id)
        if op=='advance':return sessions.advance(args.nest,args.session_id,compiled.read_json(args.reply),allow_lookup=args.allow_lookup)
        if op=='cancel':return sessions.cancel(args.nest,args.session_id)
        if op=='export':return sessions.export(args.nest,args.session_id,args.output)
        if op=='accept':return sessions.accept(args.nest,args.session_id,evidence=args.evidence)
        if op=='recover':return sessions.recover(args.nest,args.session_id)
        if op=='dispatch':return sessions.run_transport(args.nest,args.session_id,compiled.read_json(args.runner),timeout=args.timeout,max_bytes=args.max_bytes,allow_lookup=args.allow_lookup)
    raise ValueError('Unknown unified command')
