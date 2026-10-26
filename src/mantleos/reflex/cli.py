"""Offline demonstration CLI. This cannot install or authorize a REFLEX program."""
import argparse
import json
from pathlib import Path
import sys
from .errors import ReflexError, refuse
from .canonical import dumps,sha256
from .parser import parse_program
from .compiler import compile_ir
from .bytecode import encode,decode,disassemble
from .vm import run
from .evidence import make_candidate


def _read(path):
    p=Path(path)
    if not p.is_file() or p.stat().st_size>150000:
        refuse('E_SIZE','file missing or larger than 150000 bytes')
    return p.read_bytes()


def main(argv=None):
    parser=argparse.ArgumentParser(prog='python -m mantleos.reflex.cli',
                                   description='REFLEX/0.1 isolated offline prototype')
    cmds=parser.add_subparsers(dest='command',required=True)
    for command in ('validate','compile','run','verify','disassemble'):
        p=cmds.add_parser(command)
        p.add_argument('path')
        if command=='compile':
            p.add_argument('--output',required=True)
        if command=='run':
            p.add_argument('--input',required=True)
    candidate=cmds.add_parser('candidate',help='bind a compiled binary to submitted evidence; NO approval')
    candidate.add_argument('path',help='compiled .rfx file')
    candidate.add_argument('--evidence',required=True,help='existing test receipt bytes')
    candidate.add_argument('--baselines',required=True,help='JSON object of dependency digest pins')
    candidate.add_argument('--predecessor',help='optional 64-hex candidate predecessor')
    candidate.add_argument('--proposed-by',required=True,help='proposer ID (must differ from reviewer)')
    candidate.add_argument('--evidence-ref',action='append',default=[],help='synthetic: reference; repeatable')
    candidate.add_argument('--output',required=True,help='output candidate manifest path')
    for command in ('carrier-pack', 'carrier-verify', 'carrier-unpack'):
        p=cmds.add_parser(command, help='experimental data-only transport; not BODY admission')
        p.add_argument('path')
        p.add_argument('--carrier', required=True, choices=('raw', 'zip'))
        if command == 'carrier-pack':
            p.add_argument('--output', required=True)
        else:
            p.add_argument('--expected-sha256', required=True,
                           help='expected canonical IR SHA256 from trusted host metadata')
            if command == 'carrier-unpack':
                p.add_argument('--output', required=True,
                               help='new file only; no overwrite or adoption')
    for command in ('native-pack','native-verify','native-unpack'):
        p=cmds.add_parser(command,help='Data-only candidate in a verified fresh Body; never admission')
        p.add_argument('path')
        p.add_argument('--carrier',choices=('cartridge','chroma'),required=True)
        if command in ('native-pack','native-unpack'):p.add_argument('--output',required=True)
        if command!='native-pack':p.add_argument('--expected-sha256',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command in ('validate','compile'):
            ir=parse_program(_read(args.path))
            bc=compile_ir(ir)
            if args.command=='validate':
                out={'status':'VALID','program_sha256':sha256(ir),'authorized':False,
                     'instructions':len(bc['instructions'])}
            else:
                target=Path(args.output)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:stream.write(encode(bc))
                out={'status':'COMPILED','path':str(target),'program_sha256':sha256(ir),
                     'byte_size':target.stat().st_size,'authorized':False}
        elif args.command=='candidate':
            from .canonical import loads
            artifact=make_candidate(_read(args.path),_read(args.evidence),
                                    evidence_refs=args.evidence_ref,
                                    baseline_versions=loads(_read(args.baselines)),
                                    proposed_by=args.proposed_by,predecessor_sha256=args.predecessor)
            dest=Path(args.output)
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as stream:stream.write(dumps(artifact)+b'\n')
            out={'status':'CANDIDATE_ONLY','path':str(dest),
                 'candidate_sha256':artifact['candidate_sha256'],
                 'authorized':False,'installed':False}
        elif args.command in ('carrier-pack', 'carrier-verify', 'carrier-unpack'):
            import hashlib
            from .carriers import carrier, make_manifest
            from .carriers.contract import MAX_CARRIER_BYTES
            adapter = carrier(args.carrier)
            if args.command == 'carrier-pack':
                canonical = dumps(parse_program(_read(args.path)))
                manifest = make_manifest(canonical, adapter.carrier_id)
                data = adapter.encode(canonical, manifest)
                dest = Path(args.output)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as stream:
                    stream.write(data)
                out = {'status': 'PACKED_UNTRUSTED_DATA', 'path': str(dest),
                       'carrier_id': adapter.carrier_id,
                       'program_sha256': hashlib.sha256(canonical).hexdigest(),
                       'carrier_bytes': len(data), 'authorized': False, 'installed': False}
            else:
                path = Path(args.path)
                if not path.is_file() or path.stat().st_size > MAX_CARRIER_BYTES:
                    refuse('E_SIZE', 'carrier missing or exceeds byte limit')
                raw = path.read_bytes()
                out = adapter.verify(raw, args.expected_sha256)
                if args.command == 'carrier-unpack':
                    canonical, _ = adapter.decode(raw)
                    dest = Path(args.output)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with dest.open('xb') as stream:
                        stream.write(canonical)
                    out['path'] = str(dest)
        elif args.command.startswith('native-'):
            from . import native
            if args.command=='native-pack':
                out=native.pack(dumps(parse_program(_read(args.path))),args.output,args.carrier)
            elif args.command=='native-unpack':
                out=native.unpack(args.path,args.output,args.carrier,args.expected_sha256)
            else:
                _,out=native.extract(args.path,args.carrier,args.expected_sha256)
        elif args.command=='verify':
            bc=decode(_read(args.path))
            out={'status':'VERIFIED_INTEGRITY_ONLY','program_sha256':bc['program_sha256'],
                 'abi':bc['abi'],'authorized':False}
        elif args.command=='disassemble':
            out=disassemble(_read(args.path))
        else:
            out=run(_read(args.path),_read(args.input))
        print(json.dumps(out,sort_keys=True,separators=(',',':')))
        return 0
    except ReflexError as exc:
        print(json.dumps({'status':'REFUSED','code':exc.code,'detail':exc.detail},sort_keys=True),file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({'status':'REFUSED','code':'E_IO','detail':str(exc)[:160]},sort_keys=True),file=sys.stderr)
        return 2


if __name__=='__main__':
    sys.exit(main())
