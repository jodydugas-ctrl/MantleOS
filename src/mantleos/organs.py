"""One provider binding for platform tools and Engram organs; stdlib only."""
from pathlib import Path
import json
import uuid
from . import engram, json_contract, anchor_language, chromamem, cartridge, kernel, projects
from .effects import Capability, CapabilityRegistry, CheckedActionExecutor
from .primer import load_primer
from .transactions import locked_body


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def fields(value, required=(), optional=()):
    if not isinstance(value, dict) or set(value)-set(required)-set(optional) or set(required)-set(value):
        raise ValueError('Invalid capability arguments')


def external(body, value):
    target = Path(value).resolve()
    if target == body.resolve() or target.is_relative_to(body.resolve()):
        raise ValueError('Output must be outside the Body')
    return target


def status(body, arguments):
    fields(arguments)
    birth = load(body/'BIRTH.json')
    primer = load_primer(body)
    records = engram.read(body/'ENGRAM.jsonl')
    return {'schema':'mantle.body-status/1','status':'READY','bio_software':birth['id'],
            'kind':birth['kind'],'persona':birth['primer']['persona_name'],
            'primer_sha256':primer['sha256'],'primer_loaded_first':True,
            'cartridge':load(body/'CARTRIDGE.json')['cartridge_id'],
            'records':len(records),'ledger_head':engram.head(body/'ENGRAM.jsonl'),
            'distribution':birth['distribution'],'skin':'UNAVAILABLE: integrity-only core',
            'default_language':anchor_language.DIALECT,
            'kernel_default':'cartridge','kernel_outputs':list(kernel.FORMATS),
            'anchor_register_revision':anchor_language.validate_register(load(body/'ANCHOR-REGISTER.json'))['state_revision'] if (body/'ANCHOR-REGISTER.json').is_file() else None}




def anchor_message(arguments):
    fields(arguments, ('sender','recipient','message_id','payload'), ('register',))
    return anchor_language.make_message(arguments['sender'],arguments['recipient'],
                    arguments['message_id'],arguments['payload'],register=arguments.get('register'))


def anchor_message_verify(arguments):
    fields(arguments, ('packet',))
    packet=anchor_language.validate_message(arguments['packet'])
    return {'schema':'mantle.anchor-message-verification/1','result':'PASS','sha256':packet['sha256']}


def anchor_profile_inspect(arguments):
    fields(arguments, ('source',))
    return anchor_language.inspect_blueprint(arguments['source'])


def anchor_profile_run(arguments):
    fields(arguments, ('source',), ('command',))
    return anchor_language.execute_blueprint(arguments['source'],arguments.get('command'))


def engram_image_inspect(arguments):
    fields(arguments, ('path',), ('manifest',))
    return chromamem.inspect(arguments['path'],manifest_id=arguments.get('manifest',chromamem.ACTIVE_MANIFEST))


def inspect_source(body, arguments):
    """The Engram's SCAN organ: one graph feeds hypotheses and a report."""
    from .scan.service import inspect
    return inspect(arguments,body)['receipt']


def compact(body, arguments):
    from .scan.planner import compact_project
    fields(arguments,('source','output'))
    return compact_project(arguments['source'],external(body,arguments['output']))


def experiment(body, arguments):
    from .scan.experiments import experiment as measure
    fields(arguments,('baseline','candidate','specification','output'))
    destination=external(body,arguments['output'])
    if destination.exists(): raise ValueError('Output already exists')
    spec=arguments['specification']
    if isinstance(spec,str): spec=load(spec)
    return measure(arguments['baseline'],arguments['candidate'],spec,destination)


def query(body, arguments):
    fields(arguments,('text',),('limit','types','head'))
    limit=arguments.get('limit',8)
    if type(limit) is not int or not 1 <= limit <= 100: raise ValueError('Invalid query limit')
    head=arguments.get('head',engram.head(body/'ENGRAM.jsonl'))
    return {'ledger_head':head,'matches':engram.query_at_head(body/'ENGRAM.jsonl',arguments['text'],
            ledger_head=head,limit=limit,types=arguments.get('types'))}


def memory(body, arguments):
    fields(arguments,('text',))
    if not isinstance(arguments['text'],str) or not 0 < len(arguments['text']) <= 16000: raise ValueError('Invalid memory')
    return engram.append(body/'ENGRAM.jsonl','memory','operator-admitted',{'text':arguments['text'],'evidence':'REPORTED'})


def export(body, arguments):
    from .checkpoint import render
    fields(arguments,('output',))
    output=external(body,arguments['output'])
    if output.exists(): raise ValueError('Output already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(render(body),encoding='utf-8')
    return {'output':str(output),'kind':'chat-projection'}


def save(body, arguments, *, sync_required=True):
    from .lifecycle import save as snapshot
    from .synchronization import repository_for, check
    fields(arguments,('output',),('format','nest'))
    repo=repository_for(body)
    if repo and sync_required: check(repo)
    return snapshot(body,arguments['output'],format=arguments.get('format','cartridge'),nest=arguments.get('nest'))


def construct(body, arguments):
    from .lifecycle import create
    fields(arguments,('birth','output'),('blueprint','child_id','programs','inherit_memory','format','nest'))
    birth=load(arguments['birth']) if isinstance(arguments['birth'],str) else arguments['birth']
    blueprint=arguments.get('blueprint')
    if isinstance(blueprint,str):blueprint=load(blueprint)
    result=create(birth,arguments['output'],parent=body,blueprint=blueprint,
                  cartridge_id=arguments.get('child_id'),programs=arguments.get('programs'),
                  inherit_memory=arguments.get('inherit_memory',False),format=arguments.get('format'),nest=arguments.get('nest'))
    if result['result']=='CREATED':
        # Preserve the directory constructor's public verification receipt.
        return {**result,**cartridge.verify(result['output'])}
    return result


def project_operation(body, operation, arguments):
    if operation=='list': fields(arguments); return projects.list_projects(body)
    if operation=='create':
        fields(arguments,('name',),('slug',)); result=projects.create_project(body,arguments['name'],slug=arguments.get('slug'))
    elif operation=='add':
        fields(arguments,('source',),('name','slug')); result=projects.add_project(body,Path(arguments['source']),name=arguments.get('name'),slug=arguments.get('slug'))
    else:
        fields(arguments,('selector',))
        target=projects.resolve_project(body,arguments['selector'])
        return projects.inspect_project(target) if operation=='inspect' else projects.verify_project(target)
    cartridge.write_manifest(body)
    return result


def registry(body, *, constructing=False):
    """Shared tissue: each capability binds one concrete provider and authority."""
    body=Path(body).resolve(); reg=CapabilityRegistry()
    def bind(name, effect, provider, authority='effect.execute'):
        reg.register(Capability(name,effect,authority,'mantle.core/3',provider,lambda r:isinstance(r,(dict,list))))
    from . import lifecycle, compiled
    def rebuild_provider(arguments):
        fields(arguments,(),('programs','birth','allow_identity_change','expected_head'))
        return lifecycle.rebuild(body,**arguments)
    additions=[('body.compile','MUTATE',lambda a:(fields(a),lifecycle.compile_existing(body))[1]),
               ('body.rebuild','MUTATE',rebuild_provider),
               ('engram.compiled.query','READ',lambda a:compiled.query(body,**a))]
    for name,effect,provider in additions:
        bind(name,effect,provider,'lifecycle.rebuild' if name=='body.rebuild' else 'effect.execute')
    bind('body.status','READ',lambda a:status(body,a))
    bind('body.verify','COMPUTE',lambda a:(fields(a),cartridge.verify(body))[1])
    bind('body.kernel.formats','READ',lambda a:(fields(a),kernel.formats())[1])
    bind('context.bootstrap','READ',lambda a:{'primer':load_primer(body),'status':status(body,a)})
    bind('anchor.language','READ',lambda a:(fields(a),anchor_language.communication_spec())[1])
    bind('anchor.message','COMPUTE',lambda a:anchor_message(a))
    bind('anchor.message.verify','COMPUTE',lambda a:anchor_message_verify(a))
    bind('anchor.blueprint.inspect','COMPUTE',lambda a:anchor_profile_inspect(a))
    bind('anchor.blueprint.run','COMPUTE',lambda a:anchor_profile_run(a))
    bind('engram.image.inspect','READ',lambda a:engram_image_inspect(a))

    bind('engram.query','READ',lambda a:query(body,a))
    bind('memory.engram','MUTATE',lambda a:memory(body,a),'memory.admit')
    bind('engram.export','EXTERNAL',lambda a:export(body,a))
    bind('scan.inspect','EXTERNAL',lambda a:inspect_source(None if constructing else body,a))
    bind('scan.compact','EXTERNAL',lambda a:compact(body,a))
    bind('scan.experiment','EXTERNAL',lambda a:experiment(body,a))
    from .scan.service import CAPABILITIES,execute as native_scan
    for name,effect in CAPABILITIES.items():
        bind(name,effect,lambda a,operation=name:native_scan(operation,a,body=None if constructing else body))
    bind('body.save','EXTERNAL',lambda a:save(body,a,sync_required=False))
    bind('cartridge.builder','EXTERNAL',lambda a:construct(body,a))
    for operation in ('list','create','add','inspect','verify'):
        bind('project.'+operation,'MUTATE' if operation in {'create','add'} else 'READ',
             lambda a,op=operation:project_operation(body,op,a))
    return reg


@locked_body
def invoke(body, name, arguments, *, permit=False):
    body=Path(body)
    if load(body/'BIRTH.json')['distribution']['role']=='reference': raise PermissionError('Clone the reference before operation')
    if not permit: raise PermissionError('Explicit --permit-effect required')
    cartridge.verify(body)
    if name == 'body.save':
        from .synchronization import repository_for, check
        repo=repository_for(body)
        if repo: check(repo)
    executor=CheckedActionExecutor(system_registry(body).capability_registry(),lambda authority,capability:permit,body/'ENGRAM.jsonl')
    return executor.execute(name,arguments,request_id=uuid.uuid4().hex,expected_head=engram.head(body/'ENGRAM.jsonl'))


def system_registry(body):
    from .systems import SystemRegistry
    result=SystemRegistry(load(Path(body)/'SYSTEMS.json'))
    providers=registry(body)
    for item in providers.catalog(): result.bind(providers.get(item['name']))
    return result
