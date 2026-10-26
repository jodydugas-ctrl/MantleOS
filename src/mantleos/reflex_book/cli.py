"""Offline demonstration CLI. This cannot install or authorize a REFLEX program."""
import argparse
import json
from pathlib import Path
import sys
import os
import tempfile
from .errors import ReflexError, refuse
from .canonical import dumps,sha256
from .parser import parse_program
from .compiler import compile_ir
from .bytecode import encode,decode,disassemble
from .vm import run, prepare, run_prepared
from .evidence import make_candidate


def _read(path):
    p=Path(path)
    if not p.is_file() or p.stat().st_size>150000:
        refuse('E_SIZE','file missing or larger than 150000 bytes')
    return p.read_bytes()


def _write_new(path, data):
    """Publish complete artifacts exclusively; preserve prior source and receipts."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.reflex-', dir=target.parent)
    staged = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == 'nt':
            os.rename(staged, target)
        else:
            os.link(staged, target)
    finally:
        staged.unlink(missing_ok=True)


def main(argv=None):
    parser=argparse.ArgumentParser(prog='python -m mantleos reflex-book',
                                   description='REFLEX/0.1 bundled experimental reference toolkit')
    cmds=parser.add_subparsers(dest='command',required=True)
    for command in ('validate','compile','run','verify','disassemble'):
        p=cmds.add_parser(command)
        p.add_argument('path')
        if command=='compile':
            p.add_argument('--output',required=True)
        if command=='run':
            p.add_argument('--input',required=True)
            p.add_argument('--explain', action='store_true',
                           help='opt into experimental trace/0.2 UNKNOWN reasons')
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
        p=cmds.add_parser(command,help='Compatibility fresh-Body data-only transport; never admission')
        p.add_argument('path')
        p.add_argument('--carrier',choices=('cartridge','chroma'),required=True)
        if command in ('native-pack','native-unpack'):p.add_argument('--output',required=True)
        if command!='native-pack':p.add_argument('--expected-sha256',required=True)
    for command in ('demo', 'evaluate', 'inspect', 'compare', 'reproduce'):
        p=cmds.add_parser(command)
        if command in ('evaluate','inspect','reproduce'):
            p.add_argument('path')
        if command=='compare':
            p.add_argument('left'); p.add_argument('right')
        if command in ('demo','evaluate'):
            p.add_argument('--output',required=True)
        if command=='evaluate':
            p.add_argument('--input',required=True)
        if command in ('inspect','compare'):
            p.add_argument('--format', choices=('text','json'), default='text')
    args=parser.parse_args(argv)
    try:
        if args.command in ('demo','evaluate','inspect','compare','reproduce'):
            from . import evaluation
            if args.command=='demo':
                out=evaluation.demo(args.output)
            elif args.command=='evaluate':
                record=evaluation.evaluate(_read(args.path), _read(args.input))
                _write_new(args.output, dumps(record)+b'\n')
                out=evaluation.inspect_record(record)
            elif args.command=='inspect':
                out=evaluation.inspect_record(evaluation.read(args.path))
            elif args.command=='compare':
                out=evaluation.compare(evaluation.read(args.left),evaluation.read(args.right))
            else:
                out=evaluation.reproduce(evaluation.read(args.path))
            if getattr(args,'format',None)=='text':
                print(evaluation.render(out))
            else:
                print(json.dumps(out,sort_keys=True,ensure_ascii=True))
            return 0 if out.get('status') not in ('MISMATCH','INCOMPATIBLE') else 2
        if args.command in ('validate','compile'):
            ir=parse_program(_read(args.path))
            bc=compile_ir(ir)
            if args.command=='validate':
                out={'status':'VALID','program_sha256':sha256(ir),'authorized':False,
                     'instructions':len(bc['instructions'])}
            else:
                target=Path(args.output)
                _write_new(target, encode(bc))
                out={'status':'COMPILED','path':str(target),'program_sha256':sha256(ir),
                     'byte_size':target.stat().st_size,'authorized':False}
        elif args.command=='candidate':
            from .canonical import loads
            artifact=make_candidate(_read(args.path),_read(args.evidence),
                                    evidence_refs=args.evidence_ref,
                                    baseline_versions=loads(_read(args.baselines)),
                                    proposed_by=args.proposed_by,predecessor_sha256=args.predecessor)
            dest=Path(args.output)
            _write_new(dest, dumps(artifact)+b'\n')
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
                _write_new(dest, data)
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
                    _write_new(dest, canonical)
                    out['path'] = str(dest)
        elif args.command.startswith('native-'):
            from ..reflex import native
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
            raw, inputs = _read(args.path), _read(args.input)
            out = run_prepared(prepare(raw), inputs, explain=True) if args.explain else run(raw, inputs)
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
