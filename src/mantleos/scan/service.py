"""One native Metabolism service over the shared SCAN implementation.

Kernel dispatch binds these operations to existing checked actions. Diagnostic
invocations produce evidence/artifacts, never implicit Engram retention.
"""
from pathlib import Path
from .common import ScanError, atomic_text, outside, read_json, sha, write_json

CAPABILITIES = {
    'scan.capabilities':'READ', 'scan.lenses':'READ', 'scan.providers':'READ',
    'scan.inspection':'COMPUTE', 'scan.snapshot':'EXTERNAL', 'scan.discover':'EXTERNAL', 'scan.trace':'COMPUTE',
    'scan.diff':'COMPUTE', 'scan.view':'COMPUTE', 'scan.plan':'COMPUTE',
    'scan.work-order':'COMPUTE', 'scan.evidence':'COMPUTE',
    'scan.verify-evidence':'COMPUTE', 'scan.dossier':'COMPUTE',
    'scan.observe':'EXTERNAL', 'scan.export':'EXTERNAL',
    'scan.chase.targets':'READ', 'scan.chase.add':'EXTERNAL',
    'scan.chase.qualify':'EXTERNAL', 'scan.chase.assess':'EXTERNAL',
    'scan.chase.catalog.read':'READ', 'scan.chase.catalog.seed':'EXTERNAL',
    'scan.chase.catalog.observe':'EXTERNAL', 'scan.chase.catalog.scorecard':'READ',
    'scan.chase.catalog.propose':'EXTERNAL', 'scan.chase.catalog.transition':'EXTERNAL',
    'scan.chase.catalog.link':'EXTERNAL', 'scan.chase.catalog.learning':'READ',
    'scan.chase.catalog.refresh':'EXTERNAL', 'scan.chase.catalog.dashboard':'EXTERNAL',
}


def fields(value, required=(), optional=()):
    if not isinstance(value,dict) or set(required) - value.keys() or value.keys() - set(required) - set(optional):
        raise ScanError('Invalid native SCAN capability arguments')


def document(value, limit=64000000):
    return read_json(value,limit=limit) if isinstance(value,(str,Path)) else value


def destination(value, body=None):
    path = Path(value).resolve()
    if body is not None: outside(path,body)
    return path


def capabilities():
    from .registry import DEFAULTS, FILTERS
    return {'schema':'scan.native-capabilities/1','owner':'system.metabolism','coordinator':'mantle.kernel',
            'implementation':'shared src/mantleos/scan','runtime':'bundled Python standard library',
            'mandatory_external_dependencies':[], 'specimen_execution_default':False,
            'interfaces':sorted([*CAPABILITIES,'scan.inspect','scan.compact','scan.experiment']),
            'extensions':DEFAULTS,'filters':list(FILTERS),'native_language_coverage':{
                'python':'STRUCTURE_AND_PARTIAL_FLOW','anchor':'STRUCTURE_ONLY',
                'interface':'STRUCTURE_ONLY','json':'STRUCTURE_ONLY','toml':'STRUCTURE_ONLY',
                'typescript':'BOUNDED_LEXICAL_STRUCTURE','pe':'BOUNDED_BINARY_METADATA'},
            'inspection_engine':{'owner':'NATIVE_SCAN','available':True,
                'views':['all','application','artifact','members','boundaries'],
                'detail':['summary','full'],'shared_graph_and_cache':True},
            'optional_specialists':['typescript-static'],
            'discovery':{'operation':'scan.discover','workers':2,'engine':'mantleos.scan','parallelism':'captured-file extraction',
                         'shared_source_pins':True,'gui_required':True,'automatic_acceptance':False},
            'retention':'Separate authorized memory/checked-action admission; diagnostic dispatch has no ledger',
            'limitations':['Static findings do not prove runtime behavior','No OS sandbox or decompilation is claimed']}


def inspect(arguments, body=None):
    from .scanner import scan
    from .planner import plan
    from .registry import Registry
    from .html_report import render_report
    fields(arguments,('source','workspace'),('objective','max_files','max_bytes','max_file_bytes','max_seconds','max_nodes','provider_policy','allow_external','filters','execution','settings'))
    from .inspection import inspect as inspection, settings as inspection_settings
    selected = inspection_settings(arguments.get('settings'))
    folder = destination(arguments['workspace'],body)
    options = {key:arguments[key] for key in ('max_files','max_bytes','max_file_bytes','max_seconds','max_nodes','provider_policy','allow_external','filters','execution') if key in arguments}
    report = scan(arguments['source'],folder,**options)
    view = inspection(report,selected,source=arguments['source'])
    write_json(folder / 'inspection.json',view)
    proposal = plan(report,arguments.get('objective','Reduce repeated work while preserving behavior'))
    write_json(folder / 'optimization-plan.json',proposal)
    render_report(report,Registry(folder),folder / 'report.html')
    artifacts = {name:{'path':str(folder / name),'sha256':sha((folder / name).read_bytes())}
                 for name in ('latest-scan.json','inspection.json','optimization-plan.json','report.html')}
    receipt = {'schema':'mantle.scan-receipt/1','graph_digest':report['graph_digest'],
               'status':proposal['status'],'hypotheses':len(proposal['opportunities']),
               'coverage_gaps':len(report['graph']['gaps']),'artifacts':artifacts,
               'cache':report['run'],'evidence':'STATIC_ANALYSIS_NOT_BEHAVIORAL_PROOF'}
    return {'schema':'mantle.native-scan/1','report':report,'inspection':view,'receipt':receipt,
            'owner':'system.metabolism','specimen_executed':False}


def export(arguments,body=None):
    import json
    from .investigator import _report
    fields(arguments,('output','value'),('reports','inputs','source_roots'))
    target = destination(arguments['output'],body)
    reports,inputs,roots = arguments.get('reports',[]),arguments.get('inputs',[]),arguments.get('source_roots',[])
    if not all(isinstance(items,(list,tuple)) and len(items) <= 128 for items in (reports,inputs,roots)):
        raise ScanError('SCAN export path/reference budget exceeded')
    if target in {Path(item).resolve() for item in inputs}: raise ScanError('Output cannot overwrite an input report')
    for report in reports:
        _report(report); outside(target,report['source_root'])
    for root in roots: outside(target,root)
    value = arguments['value']
    encoded = value.encode('utf-8') if isinstance(value,str) else json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8')
    if len(encoded) > 64000000: raise ScanError('SCAN export byte budget exceeded')
    if isinstance(value,str): atomic_text(target,value)
    else: write_json(target,value)
    return {'schema':'scan.export/1','output':str(target),'sha256':sha(target.read_bytes()),'body_mutated':False}


def execute(name, arguments, *, body=None):
    if name not in CAPABILITIES: raise ScanError('Unknown native SCAN capability')
    if name == 'scan.capabilities': fields(arguments); return capabilities()
    if name == 'scan.lenses':
        from .registry import Registry
        fields(arguments); return {'schema':'scan.lenses/1','lenses':Registry('.').lenses()}
    if name == 'scan.providers':
        from .providers import CATALOG
        fields(arguments); return CATALOG
    if name == 'scan.inspection':
        from .inspection import inspect as inspection
        fields(arguments,('report',),('settings','source'))
        return inspection(document(arguments['report']),arguments.get('settings'),source=arguments.get('source'))
    if name == 'scan.snapshot': return inspect(arguments,body)
    if name == 'scan.discover':
        from .discovery import discover
        fields(arguments,('source','output','identity'),('gui_root','execution','max_files','max_bytes','max_file_bytes','max_seconds','max_nodes'))
        options = {key:value for key,value in arguments.items() if key not in ('source','output','identity')}
        return discover(arguments['source'],destination(arguments['output'],body),arguments['identity'],**options)
    if name == 'scan.export': return export(arguments,body)
    if name == 'scan.trace':
        from .investigator import trace,verify_trace
        fields(arguments,('report','selector'),('direction','max_depth','max_nodes','max_edges','edge_kinds'))
        report = document(arguments['report'])
        value = trace(report,arguments['selector'],**{k:v for k,v in arguments.items() if k not in ('report','selector')})
        verify_trace(value,report); return value
    if name == 'scan.diff':
        from .investigator import snapshot_diff,verify_diff
        fields(arguments,('before','after'),('max_items','max_candidates','impact_nodes'))
        before,after = document(arguments['before']),document(arguments['after'])
        value = snapshot_diff(before,after,**{k:v for k,v in arguments.items() if k not in ('before','after')})
        verify_diff(value,before,after); return value
    if name == 'scan.view':
        from .views import view
        from .registry import Registry
        fields(arguments,('report',),('workspace','lens'))
        return view(document(arguments['report']),Registry(arguments.get('workspace','.')).lens(arguments.get('lens','structure')))
    if name in ('scan.plan','scan.work-order'):
        from .planner import plan,work_order
        fields(arguments,('report',),('objective',))
        report,objective = document(arguments['report']),arguments.get('objective','Investigate source-bound static hypotheses')
        return plan(report,objective) if name == 'scan.plan' else {'schema':'scan.work-order/1','text':work_order(report,objective)}
    if name == 'scan.evidence':
        from .evidence import static_evidence,verify_evidence
        from .observations import runtime_evidence
        fields(arguments,('report',),('node_ids','edge_ids','runtime_receipt','authorized_runs'))
        report = document(arguments['report']); source = report['source_root']
        runs,authorized = {},arguments.get('authorized_runs',{})
        if 'runtime_receipt' in arguments:
            run = document(arguments['runtime_receipt'],8000000); runs = {run['run_id']:run}
            if arguments.get('node_ids') or arguments.get('edge_ids'): raise ScanError('Static and runtime assertions need separate envelopes')
            value = runtime_evidence(report,run,authorized_sha256=authorized.get(run['run_id']),source_root=source)
        else: value = static_evidence(report,arguments.get('node_ids',[]),arguments.get('edge_ids',[]))
        verify_evidence(value,report,source,runtime_receipts=runs,authorized_runs=authorized); return value
    if name == 'scan.verify-evidence':
        from .evidence import verify_evidence
        fields(arguments,('receipt','report','source'),('parent_ids','runtime_receipts','authorized_runs'))
        return verify_evidence(document(arguments['receipt'],8000000),document(arguments['report']),arguments['source'],
                              **{k:v for k,v in arguments.items() if k not in ('receipt','report','source')})
    if name == 'scan.dossier':
        from .dossier import build
        fields(arguments,('report','source','receipts'),('feature_trace','specification','contract','expected_contract_sha256',
               'candidate','conformance','runtime_receipts','authorized_runs'))
        return build(document(arguments['report']),arguments['source'],arguments['receipts'],
                     **{k:v for k,v in arguments.items() if k not in ('report','source','receipts')})
    if name == 'scan.observe':
        from .observations import observe
        fields(arguments,('report','command','permit_execution'),('timeout','output_limit'))
        report = document(arguments['report'])
        return observe(report,report['source_root'],arguments['command'],permit_execution=arguments['permit_execution'],
                       **{k:v for k,v in arguments.items() if k not in ('report','command','permit_execution')})
    if name.startswith('scan.chase.catalog.'):
        from . import chase_v2, chase_pipeline, chase_optional
        operation = name.split('.')[-1]
        required = {
            'read':('workspace',), 'seed':('workspace','catalog'),
            'observe':('workspace','challenge_id','observation','expected_revision'),
            'scorecard':('workspace',), 'propose':('workspace','proposal','expected_revision'),
            'transition':('workspace','proposal_id','status','expected_revision'),
            'link':('workspace','proposal_id','receipt','expected_revision','expected_receipt_sha256','baseline','candidate'),
            'learning':('workspace',), 'refresh':('workspace','target_id','expected_revision','permit_fetch'),
            'dashboard':('workspace','app_workspace','expected_revision'),
        }[operation]
        optional = {'scorecard':('challenge_ids',), 'transition':('binding',),
                    'refresh':('declared_revision','license')}.get(operation,())
        fields(arguments,required,optional)
        # Check un-resolved workspace links before destination() canonicalizes them.
        chase_v2._path(arguments['workspace'],body)
        workspace = destination(arguments['workspace'],body)
        if operation == 'read': return chase_v2.list_catalog(workspace,body=body)
        if operation == 'seed': return chase_v2.seed_catalog(workspace,document(arguments['catalog'],chase_v2.INPUT_LIMIT),body=body)
        if operation == 'observe':
            return chase_v2.record_observation(workspace,arguments['challenge_id'],document(arguments['observation'],chase_v2.INPUT_LIMIT),arguments['expected_revision'],body=body)
        if operation == 'scorecard': return chase_v2.build_scorecard(workspace,challenge_ids=arguments.get('challenge_ids'),body=body)
        if operation == 'propose': return chase_pipeline.create_proposal(workspace,document(arguments['proposal'],chase_v2.INPUT_LIMIT),arguments['expected_revision'],body=body)
        if operation == 'transition':
            return chase_pipeline.transition_proposal(workspace,arguments['proposal_id'],arguments['status'],arguments['expected_revision'],binding=document(arguments['binding'],chase_v2.INPUT_LIMIT) if 'binding' in arguments else None,body=body)
        if operation == 'link':
            return chase_pipeline.link_experiment(workspace,arguments['proposal_id'],arguments['receipt'],arguments['expected_revision'],
                       **{k:arguments[k] for k in ('expected_receipt_sha256','baseline','candidate')},body=body)
        if operation == 'learning': return chase_pipeline.learning_summary(workspace,body=body)
        if operation == 'refresh':
            return chase_optional.refresh_reference(workspace,arguments['target_id'],arguments['expected_revision'],
                **{k:v for k,v in arguments.items() if k not in ('workspace','target_id','expected_revision')},body=body)
        if operation == 'dashboard':
            return chase_optional.publish_dashboard(workspace,arguments['app_workspace'],expected_revision=arguments['expected_revision'],body=body)
    if name.startswith('scan.chase.'):
        from . import chase
        operation = name.split('.')[-1]
        if operation == 'targets':
            fields(arguments,('workspace',)); return {'schema':'mantle.chase-targets/1','targets':chase.targets(destination(arguments['workspace'],body))}
        if operation == 'add':
            fields(arguments,('workspace','record')); return chase.add_target(destination(arguments['workspace'],body),document(arguments['record'],64000))
        fields(arguments,('workspace','target_id','receipt'))
        return getattr(chase,operation)(destination(arguments['workspace'],body),arguments['target_id'],arguments['receipt'])
    raise ScanError('Unimplemented native SCAN capability')


def install_interfaces(body):
    """Explicit maintenance upgrade, never called by diagnostic scan/invocation.

    Preserve five systems and existing contracts. Only add missing native SCAN
    declarations; lifecycle tooling recompiles/manifests after this operation.
    """
    from ..systems import validate_systems_contract
    body = Path(body); target = body / 'SYSTEMS.json'
    value = validate_systems_contract(read_json(target))
    metabolism = next(system for system in value['systems'] if system['id'] == 'system.metabolism')
    declared = {item['name']:(system['id'],item) for system in value['systems'] for item in system['interfaces']}
    for name,effect in CAPABILITIES.items():
        if name in declared:
            owner,current = declared[name]
            if owner != 'system.metabolism' or current['authority'] != 'effect.execute' or current['effect'] != effect or current.get('provider') != 'mantle.core/3' or current['binding'] != 'BOUND':
                raise ScanError('Existing SCAN interface conflicts with native maintenance upgrade')
            continue
        metabolism['interfaces'].append({'name':name,'effect':effect,'authority':'effect.execute','provider':'mantle.core/3','binding':'BOUND','replaceable':False})
    validate_systems_contract(value); write_json(target,value)
    return {'schema':'scan.interface-maintenance/1','added_or_present':sorted(CAPABILITIES),'identity_changed':False}
