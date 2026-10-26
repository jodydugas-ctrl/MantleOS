"""Command line kitchen; recipe-based orchestration with no vendor API."""
import argparse
import json
import sys
from pathlib import Path
from .core import KPPError, read_json, write_json, validate_recipe, find_repo_root, ingredient_catalog, validate_pantry
from .workshop import begin, load, inspection, priorities, install_module, set_module_enabled, recover_writer, accept, finish, handoff
from .scanner import scan
from .graph import functional_graph, coverage as graph_coverage, load_scan
from .economy import evaluate as evaluate_economy
from .anchor import inspect_file as inspect_anchor, run_file as run_anchor, bridge_python
from .pantry import discover as discover_ingredients, view as ingredient_view
from .adaptation import fit as assess_fit, reflex_plan
from .reflex import stage as reflex_stage, audit as reflex_audit, approval_template
from .testing import run_suite, accept_tested, verify_report
from .portability import export_bundle, import_bundle, review_candidate, export_preview, import_preview
from .gui import read_inventory
from .conformance import record_capture, compare_captures, read_evidence, coverage_matrix

def print_json(obj):
    print(json.dumps(obj,indent=2,ensure_ascii=False))

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0]=='reflex-book':
        from ..reflex_book.cli import main as reflex_book_main
        return reflex_book_main(argv[1:])
    if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr,"reconfigure"):sys.stderr.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser(prog="kpp",description="Kitchen Party Protocol / local developer tools")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser('reflex-book',help='Experimental REFLEX language/VM and data-only carriers; no Body adoption')
    a=sub.add_parser('engram', help='Construct a fresh Engram with a recipe-selected carrier')
    commands=a.add_subparsers(dest='engram_cmd',required=True)
    c=commands.add_parser('create')
    c.add_argument('--recipe',type=Path,required=True)
    c.add_argument('--output',type=Path,required=True)
    c.add_argument('--persona',type=Path)
    c.add_argument('--persona-name')
    sub.add_parser('systems', help='Describe the one shared MantleOS/KPP system')
    a=sub.add_parser('language-plan', help='Report recipe implementation choices without execution')
    a.add_argument('--recipe', type=Path, required=True)
    a=sub.add_parser('bind', help='Inspect a recipe as applications of the shared Neutral Anchor')
    a.add_argument('--recipe', type=Path, required=True)
    a=sub.add_parser('cell', help='Produce a kernel-relative CELL using the shared kernel')
    a.add_argument('--kernel', choices=('chroma.rgb/1', 'tape.segment/1'), required=True)
    a.add_argument('--payload', type=Path, required=True)
    a=sub.add_parser('discover', help='Shared concurrent code/Qt discovery; no approval')
    a.add_argument('source', type=Path)
    a.add_argument('--gui-root', type=Path)
    a.add_argument('--identity', required=True)
    a.add_argument('--output', type=Path, required=True)
    a.add_argument('--execution', choices=('parallel', 'serial'), default='parallel')
    a=sub.add_parser("doctor",help="Check KPP tooling and manifests")
    a.add_argument("--repo",type=Path)
    a=sub.add_parser("pantry",help="Discover ingredients by label; expand only when needed")
    a.add_argument("--repo",type=Path)
    a.add_argument("--query",default="", help="Search label text without reading source")
    a.add_argument("--context",help="Preferred environment hint; not a compatibility guarantee")
    a.add_argument("--tissue",help="Implementation tissue filter")
    a.add_argument("--limit",type=int,default=20)
    a.add_argument("--id",help="Select exactly one ingredient")
    a.add_argument("--level",choices=("label","contract","source"),default="label")
    a.add_argument("--check-source",action="store_true",help="Explicitly recheck bounded external inventory")
    a=sub.add_parser("fit",help="Review new capability versus declared baseline and Pantry labels; read-only")
    a.add_argument("--request",type=Path,required=True)
    a.add_argument("--repo",type=Path)
    a.add_argument("--limit",type=int,default=8)
    a.add_argument("--out",type=Path)
    a=sub.add_parser("reflex-plan",help="Read-only, source-pinned candidate reflex connection points")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--request",type=Path,required=True)
    a.add_argument("--source",type=Path,required=True)
    a.add_argument("--repo",type=Path)
    a.add_argument("--depth",type=int,default=2)
    a.add_argument("--out",type=Path)
    a=sub.add_parser("reflex-approval-template",help="Create an incomplete Baker staging approval template")
    a.add_argument("--plan",type=Path,required=True)
    a.add_argument("--out",type=Path)
    a=sub.add_parser("reflex-stage",help="Stage an approved source-pinned Python adapter; no execution")
    a.add_argument("--repo",type=Path)
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--request",type=Path,required=True)
    a.add_argument("--plan",type=Path,required=True)
    a.add_argument("--approval",type=Path,required=True)
    a.add_argument("--source",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    a=sub.add_parser("reflex-audit",help="Verify candidate file pins; not runtime behavior")
    a.add_argument("--candidate",type=Path,required=True)
    a=sub.add_parser("reflex-export",help="Pack a staged candidate and pinned tests for portable review (no acceptance transfer)")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--candidate",type=Path,required=True)
    a.add_argument("--suite",type=Path,required=True)
    a.add_argument("--request",type=Path,required=True)
    a.add_argument("--plan",type=Path,required=True)
    a.add_argument("--approval",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    a=sub.add_parser("reflex-review",help="Show candidate addition and verify copied original against unchanged source")
    a.add_argument("--candidate",type=Path,required=True)
    a.add_argument("--source",type=Path,required=True)
    a=sub.add_parser("reflex-import",help="Recover a portable reflex bundle into a NEW directory; never execute it")
    a.add_argument("--bundle",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    a=sub.add_parser("test", help="Execute reviewed pinned Anchor scripts locally")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--candidate",type=Path,required=True)
    a.add_argument("--suite",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    a.add_argument("--timeout",type=int,default=15)
    a.add_argument("--execute",action="store_true",help="Explicitly authorize executable Anchor fixtures")
    a.add_argument("--reviewed",action="store_true",help="Attest review of scripts for local execution")
    a=sub.add_parser("test-check",help="Check source freshness of a PASS report without executing")
    a.add_argument("--report",type=Path,required=True)
    a.add_argument("--candidate",type=Path,required=True)
    a.add_argument("--suite",type=Path,required=True)
    a=sub.add_parser("test-accept",help="Baker accepts fresh executed Anchor evidence")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--report",type=Path,required=True)
    a.add_argument("--candidate",type=Path,required=True)
    a.add_argument("--suite",type=Path,required=True)
    a.add_argument("--baker",required=True)
    a=sub.add_parser("new",help="Create progressive workspace from recipe")
    a.add_argument("--recipe",type=Path,required=True)
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--repo",type=Path)
    for cmd in ["plan","status","next","build-step","check","handoff","complete"]:
        a=sub.add_parser(cmd)
        a.add_argument("--workspace",type=Path,required=True)
        if cmd=="handoff":a.add_argument("--out",type=Path)
    a=sub.add_parser("graph",help="Derive one functional graph (optionally incorporating static Scan evidence)")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--scan",type=Path,help="Optional saved output from kpp scan; treated as untrusted observations")
    a.add_argument("--out",type=Path)
    a=sub.add_parser("coverage",help="Audit mandatory and preserved-property Anchor coverage")
    a.add_argument("--workspace",type=Path,required=True)
    a=sub.add_parser("economy",help="Non-destructive review of a proposed Anchor consolidation")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--proposal",type=Path,required=True)
    a.add_argument("--out",type=Path)
    for command in ('organ-project', 'organ-evidence'):
        a=sub.add_parser(command, help='Read-only recipe-owned organ projection/evidence; no approval')
        a.add_argument('--recipe', type=Path, required=True)
        a.add_argument('--organs', type=Path, required=True)
        a.add_argument('--out', type=Path)
        if command=='organ-evidence':
            a.add_argument('--bindings', type=Path, required=True)
            a.add_argument('--scan', type=Path, required=True)
            a.add_argument('--source', type=Path, required=True)
    a=sub.add_parser('module-test', help='Execute reviewed Notepad Save behavior in real local Chromium')
    a.add_argument('--workspace', type=Path, required=True)
    a.add_argument('--id', required=True)
    a.add_argument('--source', type=Path, required=True)
    a.add_argument('--organs', type=Path, required=True)
    a.add_argument('--output', type=Path, required=True)
    a.add_argument('--execute', action='store_true')
    a.add_argument('--reviewed', action='store_true')
    a.add_argument('--chromium')
    for command in ('module-replace', 'module-restore'):
        a=sub.add_parser(command, help='Explicitly reviewed revision selection; invalidates acceptance')
        a.add_argument('--workspace', type=Path, required=True)
        a.add_argument('--id', required=True)
        a.add_argument('--expected-revision', type=int, required=True)
        a.add_argument('--reviewed', action='store_true')
        if command=='module-replace':
            a.add_argument('--source', type=Path, required=True)
            a.add_argument('--evidence', type=Path, required=True)
    a=sub.add_parser("install",help="Install an append-only JavaScript module")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--id",required=True)
    a.add_argument("--source",type=Path,required=True)
    a.add_argument("--depends",nargs="*",default=[])
    for command in ("module-enable", "module-disable"):
        a=sub.add_parser(command,help="Change reviewed module activation without rewriting its source")
        a.add_argument("--workspace",type=Path,required=True)
        a.add_argument("--id",required=True)
        if command=="module-disable":a.add_argument("--cascade",action="store_true")
    a=sub.add_parser("recover-writer",help="Recover verified state after a proven stopped writer")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--reviewed",action="store_true")
    a=sub.add_parser("preview-export",help="Export exact preview sources and optional user checkpoint; no acceptance transfer")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    a.add_argument("--browser-state",type=Path)
    a=sub.add_parser("preview-import",help="Restore a preview into a new unused workspace; no execution")
    a.add_argument("--bundle",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    a=sub.add_parser("accept",help="Record Baker's explicit evidence for one Anchor")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--anchor",required=True)
    a.add_argument("--evidence",required=True)
    a.add_argument("--baker",default="operator")
    a=sub.add_parser("catalog-source",help="Register a local source checkout as a reference ingredient; no execution")
    a.add_argument("path",type=Path)
    a.add_argument("--id",required=True)
    a.add_argument("--out",type=Path,required=True)
    a.add_argument("--preferred",nargs="*",default=[])
    a=sub.add_parser("scan",help="Bounded read-only static source inspector")
    a.add_argument("path",type=Path)
    a.add_argument("--depth",type=int,default=1)
    a.add_argument("--workspace", type=Path, help="External SCAN cache; defaults to a disposable workspace")
    a.add_argument("--out",type=Path)
    a.add_argument('--filter', dest='filters', action='append', choices=('code', 'interface', 'data'))
    a.add_argument('--identity', help='Source identity for the derived interface inventory')
    a.add_argument('--execution', choices=('serial', 'parallel'), default='serial')
    a=sub.add_parser("serve",help="Local progressive browser preview; loopback only")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--port",type=int,default=8765)
    a=sub.add_parser("gui-record",help="Record a pinned screenshot or explicitly labeled manual runtime observation")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--capture",type=Path,required=True)
    a.add_argument("--surface",choices=("reference","candidate"),required=True)
    a.add_argument("--method",choices=("screenshot","runtime"),required=True)
    a.add_argument("--actor",required=True)
    a.add_argument("--mode",required=True)
    a.add_argument("--ui-state",required=True)
    a.add_argument("--entries",nargs="*",default=[])
    a.add_argument("--entry-observations",type=Path,help="JSON array of independently observed entry stages and screenshot regions")
    for flag in ("action","expected","observed"):a.add_argument("--"+flag)
    a=sub.add_parser("gui-compare",help="Compare matching pinned captures; no automatic parity or acceptance")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--reference",required=True)
    a.add_argument("--candidate",required=True)
    a.add_argument("--actor",required=True)
    a=sub.add_parser("gui-evidence",help="Recheck source/capture freshness for recorded GUI evidence")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--id",required=True)
    a=sub.add_parser("gui-accept",help="Baker reviews exact source-bound GUI evidence for an Anchor")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--id",required=True)
    a.add_argument("--anchor",required=True)
    a.add_argument("--evidence",required=True)
    a.add_argument("--baker",required=True)
    a=sub.add_parser("gui-matrix",help="Independent discovered/represented/functional/tested/accepted coverage")
    a.add_argument("--workspace",type=Path,required=True)
    a=sub.add_parser("anchor", help="Inspect, run, or bridge one portable Anchor specimen")
    anchor_cmd=a.add_subparsers(dest="anchor_cmd",required=True)
    for option in ("inspect","run","bridge-python"):
        c=anchor_cmd.add_parser(option)
        c.add_argument("source",type=Path)
        if option=="bridge-python":c.add_argument("--out",type=Path,required=True)
        if option=='run':c.add_argument('--input', type=Path, help='Explicit JSON command for NOTEPAD/hosted profiles')
    a=sub.add_parser("observe",help="Record a potential emergent capability for Baker review (not acceptance)")
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--feature",required=True)
    a.add_argument("--evidence",required=True)
    args=p.parse_args(argv)
    try:
        if args.cmd in ("doctor","pantry","new","fit","reflex-plan"):
            repo=args.repo or find_repo_root()
        if args.cmd=='engram':
            from .engram_carriers import create
            print_json(create(read_json(args.recipe),args.output,
                persona=args.persona.read_text(encoding='utf-8') if args.persona else None,
                persona_name=args.persona_name))
        elif args.cmd=='systems':
            from .systems import describe
            print_json(describe())
        elif args.cmd=='language-plan':
            from .language import implementation_plan
            print_json(implementation_plan(read_json(args.recipe)))
        elif args.cmd=='bind':
            from ..kitchen import bind
            print_json(bind(validate_recipe(read_json(args.recipe))))
        elif args.cmd=='cell':
            from ..cells import produce
            print_json(produce(args.kernel, read_json(args.payload)))
        elif args.cmd=='discover':
            from ..scan.discovery import discover
            print_json(discover(args.source, args.output, args.identity,
                                gui_root=args.gui_root, execution=args.execution))
        elif args.cmd=="doctor":
            catalog=ingredient_catalog(repo)
            recipes=[validate_recipe(read_json(r)) for r in sorted((repo/"recipes").glob("*.json"))]
            for recipe in recipes:validate_pantry(recipe,catalog)
            for recipe in recipes:read_inventory(recipe,repo)
            for item in catalog.values():
                ingredient_view(repo,item["id"],catalog=catalog)
            print_json({"ready":True,"repo":str(repo),"ingredients":len(catalog),"recipes":len(recipes),
                        "ingredient_disclosure":"label -> contract -> source on explicit need",
                        "executable_anchor_specimens":sum("specimen" in i for i in catalog.values()),
                        "anchor_profile":"EMIT_TEXT/0.2", "shared_systems":__import__("mantleos.kpp.systems", fromlist=["describe"]).describe(), "model_api_required":False})
        elif args.cmd=="pantry":
            if args.id:
                print_json(ingredient_view(repo,args.id,level=args.level,check_external=args.check_source))
            else:
                if args.level!="label" or args.check_source:
                    raise KPPError("--level/--check-source require --id; discovery uses labels only")
                print_json(discover_ingredients(repo,args.query,args.tissue,args.context,args.limit))
        elif args.cmd=="fit":
            result=assess_fit(repo,read_json(args.request),args.limit)
            if args.out:write_json(args.out,result);print(args.out)
            else:print_json(result)
        elif args.cmd=="reflex-plan":
            recipe,state=load(args.workspace)
            result=reflex_plan(repo,recipe,state,read_json(args.request),args.source,args.depth)
            if args.out:write_json(args.out,result);print(args.out)
            else:print_json(result)
        elif args.cmd=="reflex-approval-template":
            result=approval_template(read_json(args.plan))
            if args.out:write_json(args.out,result);print(args.out)
            else:print_json(result)
        elif args.cmd=="reflex-stage":
            result=reflex_stage(args.workspace,read_json(args.request),read_json(args.plan),
                                read_json(args.approval),args.source,args.output,repo=args.repo)
            print_json(result)
        elif args.cmd=="reflex-audit":
            print_json(reflex_audit(args.candidate))
        elif args.cmd=="reflex-export":
            print_json(export_bundle(args.workspace,args.candidate,args.suite,args.request,args.plan,args.approval,args.out))
        elif args.cmd=="reflex-review":
            print_json(review_candidate(args.candidate,args.source))
        elif args.cmd=="reflex-import":
            print_json(import_bundle(args.bundle,args.output))
        elif args.cmd=="test":
            report=run_suite(args.workspace,args.candidate,args.suite,args.out,execute=args.execute,timeout=args.timeout,
                             reviewed=args.reviewed)
            print_json(report)
            return 0 if report["all_passed"] else 3
        elif args.cmd=="test-check":
            print_json(verify_report(read_json(args.report),args.candidate,args.suite))
        elif args.cmd=="test-accept":
            print_json(accept_tested(args.workspace,args.report,args.candidate,args.suite,args.baker))
        elif args.cmd=="new":
            print_json(begin(args.workspace,read_json(args.recipe),repo))
        elif args.cmd=="build-step":
            from .build import step
            print_json(step(args.workspace))
        elif args.cmd=="status":print_json(inspection(args.workspace))
        elif args.cmd=="plan":
            recipe,state=load(args.workspace)
            labels=read_json(args.workspace/"ingredient-labels.json")
            from .construction import construction_plan
            print_json({"construction":construction_plan(recipe), "recipe":recipe["id"],"goal":recipe["goal"],"target":recipe["target"],"tissue":recipe["tissue"],
                        "ingredient_labels":labels["ingredients"],
                        "mode":recipe["mode"],"product_kind":recipe.get("product_kind","unspecified"),
                        "delivery_mode":recipe.get("delivery_mode","artifact"),"preview_kind":state.get("preview_kind"),
                        "capabilities":recipe.get("capabilities",{}),"fidelity":recipe["fidelity"],"anchors":recipe["anchors"],"transformation":recipe.get("transformation"),"installed":state["modules"]})
        elif args.cmd=="next":print_json(priorities(args.workspace))
        elif args.cmd=="graph":
            recipe,state=load(args.workspace)
            activity_path=Path(args.workspace)/"activity.json"
            activity=read_json(activity_path) if activity_path.is_file() else state.get("activity",{})
            result=functional_graph(recipe,state,load_scan(args.scan) if args.scan else None,activity=activity,workspace=args.workspace)
            if args.out:write_json(args.out,result);print(args.out)
            else:print_json(result)
        elif args.cmd=="coverage":
            recipe,state=load(args.workspace)
            report=graph_coverage(recipe,state)
            if "gui_inventory" in state:report["gui_matrix"]=coverage_matrix(args.workspace)
            print_json(report)
        elif args.cmd=="economy":
            recipe,state=load(args.workspace)
            result=evaluate_economy(recipe,read_json(args.proposal))
            if args.out:write_json(args.out,result);print(args.out)
            else:print_json(result)
        elif args.cmd=="check":
            report=inspection(args.workspace)
            print_json({"structural_integrity":"PASS","acceptance":report,"scope":"Manifest and installed file hashes; not browser behavior"})
        elif args.cmd in ('organ-project','organ-evidence'):
            from .organs import project, evidence
            recipe=read_json(args.recipe);mapping=read_json(args.organs)
            result=project(recipe,mapping) if args.cmd=='organ-project' else evidence(
                recipe,mapping,read_json(args.bindings),read_json(args.scan),args.source)
            if args.out:write_json(args.out,result);print(args.out)
            else:print_json(result)
        elif args.cmd=='module-test':
            from .organ_testing import run_module_tests
            result=run_module_tests(args.workspace,args.id,args.source,read_json(args.organs),args.output,
                                    execute=args.execute,reviewed=args.reviewed,chromium=args.chromium)
            print_json({'result':result['result'],'report':str(args.output/'report.json'),
                        'runtime':result['runtime'],'acceptance':'NOT_GRANTED'})
            return 0 if result['result']=='PASS' else 3
        elif args.cmd=='module-replace':
            from .module_revisions import replace_module
            print_json(replace_module(args.workspace,args.id,args.source,args.evidence,
                                     expected_revision=args.expected_revision,reviewed=args.reviewed))
        elif args.cmd=='module-restore':
            from .module_revisions import restore_module
            print_json(restore_module(args.workspace,args.id,expected_revision=args.expected_revision,reviewed=args.reviewed))
        elif args.cmd=="install":print_json(install_module(args.workspace,args.id,args.source,args.depends))
        elif args.cmd in ("module-enable","module-disable"):
            print_json(set_module_enabled(args.workspace,args.id,args.cmd=="module-enable",getattr(args,"cascade",False)))
        elif args.cmd=="recover-writer":print_json(recover_writer(args.workspace,args.reviewed))
        elif args.cmd=="preview-export":print_json(export_preview(args.workspace,args.out,args.browser_state))
        elif args.cmd=="preview-import":print_json(import_preview(args.bundle,args.output))
        elif args.cmd=="accept":print_json(accept(args.workspace,args.anchor,args.evidence,args.baker))
        elif args.cmd=="complete":print_json(finish(args.workspace))
        elif args.cmd=="handoff":
            text=handoff(args.workspace)
            if args.out:
                args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(text,encoding="utf-8");print(args.out)
            else:print(text)
        elif args.cmd=="catalog-source":
            from .ingest import catalog_source
            print_json(catalog_source(args.path,args.id,args.out,args.preferred))
        elif args.cmd=="anchor":
            if args.anchor_cmd=="inspect":print_json(inspect_anchor(args.source))
            elif args.anchor_cmd=="run":sys.stdout.write(run_anchor(args.source, read_json(args.input) if args.input else None))
            elif args.anchor_cmd=="bridge-python":print_json(bridge_python(args.source,args.out))
        elif args.cmd=="observe":
            from .workshop import report_observation
            print_json(report_observation(args.workspace,args.feature,args.evidence))
        elif args.cmd=="scan":
            result=scan(args.path,args.depth,workspace=args.workspace,filters=args.filters,identity=args.identity,execution=args.execution)
            if args.out:write_json(args.out,result);print(args.out)
            else:print_json(result)
        elif args.cmd=="gui-record":
            print_json(record_capture(args.workspace,args.capture,args.surface,args.method,args.actor,args.mode,args.ui_state,args.entries,args.action,args.expected,args.observed,
                                      read_json(args.entry_observations) if args.entry_observations else ()))
        elif args.cmd=="gui-compare":print_json(compare_captures(args.workspace,args.reference,args.candidate,args.actor))
        elif args.cmd=="gui-evidence":print_json(read_evidence(args.workspace,args.id))
        elif args.cmd=="gui-accept":print_json(accept(args.workspace,args.anchor,args.evidence,args.baker,kind="gui-reviewed",evidence_id=args.id))
        elif args.cmd=="gui-matrix":print_json(coverage_matrix(args.workspace))
        elif args.cmd=="serve":
            from .server import serve
            serve(args.workspace,port=args.port)
        return 0
    except (KPPError,OSError,ValueError,KeyError) as exc:
        print("KPP error: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":raise SystemExit(main())
