from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import json_contract, anchor_language, chromamem
from .builder import build
from .birth import validate_birth, bind_blueprint
from .anchor_blueprint import draft_from_scan, completion_report, render_runner_guide, write_blueprint
from .semantic_discovery import (
    build_discovery_request, ingest_discovery_proposal, build_critique_request,
    finalize_discovery, discovery_report,
)
from .cartridge import verify, unpack
from .primer import load_primer, verify_lock


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None, *, body=None):
    from .kernel import scan as dispatch_scan
    def native(name,arguments):
        return dispatch_scan(name,arguments,body=body,permit=True)['observation']['result']
    ap=argparse.ArgumentParser(prog="mantleos",description="MantleOS platform reference CLI")
    sub=ap.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("new",help="Build a Bio-Software Cartridge from an explicit birth contract, optionally bound to a READY Anchor Blueprint")
    b.add_argument("--birth",required=True)
    b.add_argument("--blueprint",help="READY anchor.blueprint/3 project semantic contract; requires a matching birth binding")
    b.add_argument("--output",required=True); b.add_argument("--cartridge-id")
    bt=sub.add_parser("birth",help="Validate or bind Bio-Software birth contracts")
    bts=bt.add_subparsers(dest="birth_cmd",required=True)
    btv=bts.add_parser("verify"); btv.add_argument("birth")
    btb=bts.add_parser("bind",help="Bind a birth contract explicitly to one READY Anchor Blueprint")
    btb.add_argument("birth"); btb.add_argument("blueprint"); btb.add_argument("--output",required=True)
    bp=sub.add_parser("blueprint",help="Create/validate self-describing Anchor Blueprints")
    bps=bp.add_subparsers(dest="blueprint_cmd",required=True)
    bpd=bps.add_parser("draft",help="Create an evidence-grounded DRAFT Anchor Blueprint from a SCAN report")
    bpd.add_argument("--scan",required=True); bpd.add_argument("--output",required=True); bpd.add_argument("--id",required=True); bpd.add_argument("--name",required=True); bpd.add_argument("--purpose",required=True); bpd.add_argument("--version",default="0.1.0")
    bpv=bps.add_parser("verify",help="Validate an Anchor Blueprint and report synthesis readiness")
    bpv.add_argument("blueprint")
    bpdr=bps.add_parser("discovery-request",help="Emit a bounded, source-bound semantic discovery request for any strong LLM/agent")
    bpdr.add_argument("blueprint"); bpdr.add_argument("--source",required=True); bpdr.add_argument("--output",required=True)
    bpdr.add_argument("--max-total-bytes",type=int,default=1500000); bpdr.add_argument("--max-file-bytes",type=int,default=96000); bpdr.add_argument("--context-lines",type=int,default=8)
    bpdi=bps.add_parser("discovery-ingest",help="Verify a strict semantic proposal against exact source evidence and create a DRAFT candidate")
    bpdi.add_argument("blueprint"); bpdi.add_argument("--request",required=True); bpdi.add_argument("--proposal",required=True); bpdi.add_argument("--source",required=True); bpdi.add_argument("--output",required=True)
    bpcr=bps.add_parser("critique-request",help="Emit an independent semantic critique request for a verified DRAFT candidate")
    bpcr.add_argument("blueprint"); bpcr.add_argument("--output",required=True)
    bpp=bps.add_parser("promote",help="Promote a critiqued DRAFT candidate to READY only after all gates pass")
    bpp.add_argument("blueprint"); bpp.add_argument("--critique-request",required=True); bpp.add_argument("--critique",required=True); bpp.add_argument("--output",required=True)
    bpg=bps.add_parser("guide",help="Render the cold-start runner guide for a READY Anchor Blueprint")
    bpg.add_argument("blueprint"); bpg.add_argument("--output",required=True)
    v=sub.add_parser("verify",help="Verify a Cartridge directory"); v.add_argument("root")
    p=sub.add_parser("primer",help="Verify/show the birth-locked PRIMER"); p.add_argument("root"); p.add_argument("--show",action="store_true")
    # Anchor Coding v1.1 is the default communication and self-contained Blueprint language.
    ac=sub.add_parser("anchor-code",help="Refined Anchor Coding default-language tools")
    ac_sub=ac.add_subparsers(dest="ac_cmd",required=True)
    ac_sub.add_parser("source-verify",help="Check pinned Anchor Coding reference source")
    ac_sub.add_parser("language",help="Display default Bio-Application language contract")
    ak=ac_sub.add_parser('kpp',help='Apply a KPP recipe as attributes on the shared Neutral Anchor')
    ak.add_argument('--recipe',required=True);ak.add_argument('--output')
    ak.add_argument('--permit-effect',action='store_true')
    am=ac_sub.add_parser("message",help="Build a validated typed Anchor Code message")
    am.add_argument("--from-agent",required=True);am.add_argument("--to-agent",required=True)
    am.add_argument("--id",required=True);am.add_argument("--payload",required=True)
    av=ac_sub.add_parser("message-verify");av.add_argument("packet")
    ai=ac_sub.add_parser("inspect");ai.add_argument("blueprint")
    ar=ac_sub.add_parser("run");ar.add_argument("blueprint");ar.add_argument("--command")
    ar.add_argument('--output');ar.add_argument('--permit-effect',action='store_true')
    aa=ac_sub.add_parser('app',help='Return self-contained Anchor source; optionally create its browser view')
    aa.add_argument('name',choices=['notepad']);aa.add_argument('--output');aa.add_argument('--canvas-output')
    aa.add_argument('--workspace');aa.add_argument('--permit-effect',action='store_true')
    al=ac_sub.add_parser('launch',help='Materialize an author-compiled app target without rebuilding it')
    al.add_argument('blueprint');al.add_argument('--output',required=True)
    al.add_argument('--target',choices=['html','python'],default='html')
    al.add_argument('--permit-effect',action='store_true')
    ae=ac_sub.add_parser('emit',help='Encode a browser app as executable literal Anchor source')
    ae.add_argument('--input',required=True);ae.add_argument('--output',required=True);ae.add_argument('--name',default='App')
    ae.add_argument('--permit-effect',action='store_true')
    acomp=ac_sub.add_parser("compile");acomp.add_argument("blueprint");acomp.add_argument("--output",required=True)
    ep=sub.add_parser("engram-image",help="Inspect or explicitly reconstruct a ChromaMem v5 image Engram; never auto-executes it")
    eps=ep.add_subparsers(dest="image_cmd",required=True)
    ei=eps.add_parser("inspect");ei.add_argument("image");ei.add_argument("--manifest",default=chromamem.ACTIVE_MANIFEST)
    ee=eps.add_parser("extract-ledger");ee.add_argument("image");ee.add_argument("--output",required=True)
    ee.add_argument("--expected-prefix");ee.add_argument("--manifest",default=chromamem.ACTIVE_MANIFEST)
    eb=eps.add_parser("extract-body",help="Explicitly reconstruct a verified native Chroma Body, no code execution")
    eb.add_argument("image");eb.add_argument("--output",required=True);eb.add_argument("--manifest",default=chromamem.ACTIVE_MANIFEST)
    el=eps.add_parser('extract-bootstrap',help='Extract pinned, standalone Chroma image reader without executing it')
    el.add_argument('image');el.add_argument('--output',required=True)
    ev=eps.add_parser('evolve',help='Use a Chroma image as an append-only generation template')
    ev.add_argument('image');ev.add_argument('--body',required=True);ev.add_argument('--output',required=True)
    c=sub.add_parser("compact",help="Create a separate compacted candidate"); c.add_argument("source"); c.add_argument("--output",required=True)
    e=sub.add_parser("experiment",help="Run explicit checks/measurements in disposable copies; not an OS sandbox"); e.add_argument("--baseline",required=True); e.add_argument("--candidate",required=True); e.add_argument("--specification",required=True); e.add_argument("--output",required=True)
    r=sub.add_parser("restore",help="Safely restore and verify a .vcw"); r.add_argument("archive"); r.add_argument("--output",required=True)
    args=ap.parse_args(argv)
    if args.cmd=="new":
        spec=_load(args.birth)
        blueprint=_load(args.blueprint) if args.blueprint else None
        result=build(spec,args.output,cartridge_id=args.cartridge_id,blueprint=blueprint)
    elif args.cmd=="birth":
        if args.birth_cmd=="verify":
            value=validate_birth(_load(args.birth)); result={"schema":"mantle.bio-software-birth-validation/1","result":"PASS","id":value["id"],"persona":value["primer"]["persona_name"],"birth_sha256":value["birth_sha256"],"blueprint":value["blueprint"],"distribution":value["distribution"]}
        else:
            value=bind_blueprint(_load(args.birth),_load(args.blueprint)); target=Path(args.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); result={"schema":"mantle.bio-software-birth/1","id":value["id"],"output":str(target.resolve())}
    elif args.cmd=="blueprint":
        if args.blueprint_cmd=="draft":
            value=draft_from_scan(_load(args.scan),blueprint_id=args.id,name=args.name,purpose=args.purpose,version=args.version)
            result=write_blueprint(args.output,value)
            result["output"]=str(Path(args.output).resolve())
        elif args.blueprint_cmd=="verify":
            result=discovery_report(_load(args.blueprint))
        elif args.blueprint_cmd=="discovery-request":
            value=build_discovery_request(_load(args.blueprint),args.source,max_total_bytes=args.max_total_bytes,max_file_bytes=args.max_file_bytes,context_lines=args.context_lines)
            target=Path(args.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            result={"schema":value["schema"],"request_sha256":value["request_sha256"],"output":str(target.resolve()),"excerpt_bytes":value["request_limits"]["excerpt_bytes"]}
        elif args.blueprint_cmd=="discovery-ingest":
            value=ingest_discovery_proposal(_load(args.blueprint),_load(args.request),_load(args.proposal),args.source)
            result=write_blueprint(args.output,value); result["output"]=str(Path(args.output).resolve())
        elif args.blueprint_cmd=="critique-request":
            value=build_critique_request(_load(args.blueprint)); target=Path(args.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            result={"schema":value["schema"],"critique_request_sha256":value["critique_request_sha256"],"blocking_findings":sum(1 for f in value["deterministic_findings"] if f.get("severity")=="BLOCKING"),"output":str(target.resolve())}
        elif args.blueprint_cmd=="promote":
            value=finalize_discovery(_load(args.blueprint),_load(args.critique_request),_load(args.critique)); result=write_blueprint(args.output,value); result["output"]=str(Path(args.output).resolve())
        else:
            guide=render_runner_guide(_load(args.blueprint)); target=Path(args.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(guide,encoding="utf-8")
            result={"schema":"anchor.runner-guide/1","output":str(target.resolve()),"bytes":target.stat().st_size}
    elif args.cmd=="verify": result=verify(args.root)
    elif args.cmd=="primer":
        result=load_primer(args.root) if args.show else verify_lock(args.root)
        if args.show: result={k:v for k,v in result.items() if k!="parts"}
    elif args.cmd=="anchor-code":
        if args.ac_cmd=='kpp':
            from .kitchen import bind, inspect_binding
            result=bind(_load(args.recipe))
            inspect_binding(result)
            if args.output:
                if not args.permit_effect:raise PermissionError('Explicit --permit-effect required')
                from .anchor_canvas import outside
                from .transactions import atomic_bytes
                target=outside(body or Path(__file__).resolve().parents[2]/'agents/engram',args.output)
                atomic_bytes(target,(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode(),replace=False)
        elif args.ac_cmd=='app':
            import sys
            from . import anchor_apps
            from .anchor_canvas import outside
            from .app_bridges import default_registry
            source=anchor_apps.notepad_source()
            guarded=body or Path(__file__).resolve().parents[2]/'agents/engram'
            if (args.output or args.canvas_output) and not args.permit_effect:
                raise PermissionError('Explicit --permit-effect required for app output files')
            if args.canvas_output and not args.workspace:
                raise ValueError('--canvas-output requires --workspace outside the Body')
            if args.output:
                target=outside(guarded,args.output);guide=target.with_suffix('.RUN.md')
                if target.suffix.lower()!='.anchor' or target.exists() or guide.exists():
                    raise ValueError('Use a new .anchor output and handoff guide')
                if args.canvas_output and Path(args.canvas_output).resolve() in (target,guide):
                    raise ValueError('Source, guide and browser output must be distinct')
                with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
                with guide.open('x',encoding='utf-8',newline='\n') as stream:stream.write(anchor_apps.GUIDE)
            if args.canvas_output:
                delivery=anchor_apps.deliver(source,args.workspace,body=guarded,registry=default_registry(guarded),
                    broker=lambda authority,name:args.permit_effect,output=args.canvas_output)
                print(json.dumps(delivery,ensure_ascii=True),file=sys.stderr)
            sys.stdout.write(source)
            return source
        elif args.ac_cmd=='launch':
            if not args.permit_effect:raise PermissionError('Explicit --permit-effect required for app materialization')
            from .anchor_canvas import outside
            from .anchor_app_document import read_source, parse
            from .anchor_app_bridge import materialize
            source=read_source(args.blueprint)
            anchor_language.inspect_blueprint(source)
            if parse(source)['contract']['schema']!='mantle.anchor-app-document/2':
                raise ValueError('Legacy app has no author-compiled bridge targets')
            output=outside(body or Path(__file__).resolve().parents[2]/'agents/engram',args.output)
            result=materialize(source.encode('utf-8'),output,args.target)
        elif args.ac_cmd=='emit':
            if not args.permit_effect:raise PermissionError('Explicit --permit-effect required')
            from .anchor_canvas import emit
            result=emit(args.input,args.output,args.name,body=body or Path(__file__).resolve().parents[2]/'agents/engram')
        elif args.ac_cmd=="source-verify":result=anchor_language.verify_source_pins()
        elif args.ac_cmd=="language":result=anchor_language.communication_spec()
        elif args.ac_cmd=="message":result=anchor_language.make_message(args.from_agent,args.to_agent,args.id,_load(args.payload))
        elif args.ac_cmd=="message-verify":
            result=anchor_language.validate_message(_load(args.packet))
            result={"schema":"mantle.anchor-message-verification/1","result":"PASS","sha256":result["sha256"]}
        elif args.ac_cmd=="inspect":
            from .anchor_app_document import read_source
            result=anchor_language.inspect_blueprint(read_source(args.blueprint))
        elif args.ac_cmd=="run":
            from .anchor_app_document import read_source
            result=anchor_language.execute_blueprint(read_source(args.blueprint),_load(args.command) if args.command else None)
            if args.output:
                if not args.permit_effect:raise PermissionError('Explicit --permit-effect required')
                from .anchor_canvas import write_output
                result=write_output(result,args.output,body=body or Path(__file__).resolve().parents[2]/'agents/engram')
        elif args.ac_cmd=="compile":
            from .anchor_engine.tools.anchor_compile import translate
            from .anchor_app_document import read_source, is_document, parse
            source=read_source(args.blueprint)
            anchor_language.inspect_blueprint(source)
            output=Path(args.output)
            document=parse(source) if is_document(source) else None
            compiled=document['python'] if document else translate(source)
            with output.open('x',encoding='utf-8',newline='\n') as out:out.write(compiled)
            result={"schema":"mantle.anchor-compile/1","result":"CREATED","bytes":len(compiled.encode('utf-8')),"output":str(output.resolve())}
    elif args.cmd=="engram-image":
        if args.image_cmd=="inspect":result=chromamem.inspect(args.image,manifest_id=args.manifest)
        elif args.image_cmd=="extract-ledger":result=chromamem.extract_ledger(args.image,args.output,manifest_id=args.manifest,expected_prefix=args.expected_prefix)
        elif args.image_cmd=='extract-bootstrap':result=chromamem.extract_bootstrap(args.image,args.output)
        elif args.image_cmd=='evolve':result=chromamem.evolve(args.image,args.body,args.output)
        else:result=chromamem.extract_body(args.image,args.output,manifest_id=args.manifest)
    elif args.cmd=="compact": result=native('scan.compact',{'source':args.source,'output':args.output})
    elif args.cmd=="experiment": result=native('scan.experiment',{'baseline':args.baseline,'candidate':args.candidate,'specification':args.specification,'output':args.output})
    else: result=unpack(args.archive,args.output)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
