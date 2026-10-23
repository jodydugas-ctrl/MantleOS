"""Refined Anchor Coding as the default Bio-Application communication language.

Protocol facts follow Anchor Coding conversational v1.1 and AC-STRUCT-001.
Mantle-specific JSON message transport is an extension, not an unapproved opcode.
No message, register, or Blueprint grants host authority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from .anchor_engine.tools.anchor_structure import check_structures, StructureError
from . import anchors as model

DIALECT = 'anchor.coding.conversation/1.1'
REGISTER_SCHEMA = 'anchor.conversation-state/2'
MESSAGE_SCHEMA = 'mantle.anchor-message/1'
CAPABILITY = 'mantle.anchor-communication/1'
TYPES = set(model.TYPES)
PROFILES = {'EMIT_TEXT/0.2', 'NOTEPAD_LLM/1.3', 'AGENTIC/0.2'}
ID = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,95}\Z')
HEX = re.compile(r'[0-9a-f]{64}\Z')
MAX_PACKET = 524288
RULE_ECONOMY_SINGULARITY = model.RULE_ECONOMY


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def source_directory():
    return Path(__file__).resolve().parent / 'anchor_engine'


def verify_source_pins():
    base = source_directory().resolve()
    catalog = json.loads((base/'SOURCE-PINS.json').read_text('utf-8'))
    for rel, expected in catalog['pins'].items():
        path = base / rel
        if not path.is_file() or not path.resolve().is_relative_to(base):
            raise ValueError('Pinned Anchor source missing: '+rel)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Pinned Anchor source changed: '+rel)
    result = {'result':'PASS','files':len(catalog['pins'])}
    if 'source' in catalog:
        result['source'] = catalog['source']
    return result


def default_register(agent_id):
    if not isinstance(agent_id, str) or not ID.fullmatch(agent_id):
        raise ValueError('Invalid Bio-Application identity for Anchor Register')
    anchor = {
        'id': 'N-RULE-ECONOMY', 'name': 'Rule Economy', 'type': 'Neutral',
        'definition_id': 'N-RULE-ECONOMY',
        'singularity': RULE_ECONOMY_SINGULARITY,
        'scope': 'design_and_revision_of_every_anchor_and_group',
        'status': 'ACTIVE', 'readiness': 'READY', 'revision': 1,
        'configuration': {
            'condition': 'Preserve all required variables, exceptions, failure cases and approved rules.',
            'action': 'Identify redundancy; report gaps; never silently delete approved rules.',
        }, 'connections': [], 'source': 'Anchor Coding v1.1 default design Anchor',
    }
    return {
        'schema': REGISTER_SCHEMA, 'project': agent_id, 'goal': 'Anchor-first Bio-Application communication',
        'state_revision': 1, 'origin': 'MantleOS Bio-Application initialization',
        'anchors': [anchor], 'groups': [], 'data_contracts': [], 'data_register': [],
        'results': [], 'change_log': [{'state_revision':1, 'event':'INITIALIZE_ANCHOR_REGISTER',
                                     'source':'Anchor Coding conversational v1.1'}], 'open_questions':[],
    }


def validate_register(value):
    if not isinstance(value, dict) or value.get('schema') != REGISTER_SCHEMA:
        raise ValueError('Invalid Anchor Register schema')
    if not isinstance(value.get('state_revision'), int) or isinstance(value['state_revision'],bool) or value['state_revision'] < 1:
        raise ValueError('Invalid Anchor Register revision')
    for key in ('anchors','groups','data_contracts','data_register','results','change_log','open_questions'):
        if not isinstance(value.get(key),list):
            raise ValueError('Invalid Anchor Register '+key)
    ids=set()
    for anchor in value['anchors']:
        if not isinstance(anchor,dict) or not isinstance(anchor.get('id'),str) or not ID.fullmatch(anchor['id']):
            raise ValueError('Invalid Anchor identity')
        if anchor['id'] in ids:raise ValueError('Duplicate Anchor identity')
        ids.add(anchor['id'])
        if anchor.get('type') not in TYPES or not isinstance(anchor.get('singularity'),str) or not anchor['singularity'].strip():
            raise ValueError('Invalid Anchor singularity or polarity')
        base = model.definition(anchor.get('definition_id'))
        if anchor['type'] != base.type or anchor['singularity'] != base.singularity:
            raise ValueError('Anchor singularity or type changed')
        if anchor['id'] == 'N-RULE-ECONOMY' and base.id != 'N-RULE-ECONOMY':
            raise ValueError('Rule Economy definition changed')
        if not isinstance(anchor.get('revision'),int) or isinstance(anchor['revision'],bool) or anchor['revision']<1:
            raise ValueError('Invalid Anchor configuration revision')
        if not isinstance(anchor.get('configuration'),dict) or not isinstance(anchor.get('connections'),list):
            raise ValueError('Invalid Anchor configuration or connections')
    if 'N-RULE-ECONOMY' not in ids and not any(c.get('event')=='REMOVE_RULE_ECONOMY_USER_APPROVED' for c in value['change_log'] if isinstance(c,dict)):
        raise ValueError('Default rule-economy Anchor missing without recorded user approval')
    if len(canonical(value).encode('utf-8')) > MAX_PACKET:
        raise ValueError('Anchor Register too large')
    return deepcopy(value)


def revise_configuration(register, anchor_id, config, *, reason, approved=False):
    if not approved:raise PermissionError('Anchor revision requires explicit approval')
    result=validate_register(register)
    if not isinstance(config,dict) or not isinstance(reason,str) or not reason.strip():
        raise ValueError('Invalid approved revision')
    if {'singularity', 'type', 'definition_id'} & config.keys():
        raise ValueError('Configuration cannot redefine an Anchor')
    for anchor in result['anchors']:
        if anchor['id']==anchor_id:
            anchor['revision'] += 1
            anchor['configuration']=deepcopy(config)
            result['state_revision']+=1
            result['change_log'].append({'state_revision':result['state_revision'], 'event':'CONFIGURATION_REVISED',
                                         'anchor_id':anchor_id, 'revision':anchor['revision'], 'reason':reason,
                                         'source':'explicit user approval'})
            return validate_register(result)
    raise ValueError('Unknown Anchor: '+str(anchor_id))


def communication_spec():
    from .anchor_apps import AUTHORING_RULE
    return {
        'schema':CAPABILITY, 'language':'Anchor Coding', 'default_for':'all Bio-Applications and packaged agents',
        'conversational_protocol':DIALECT, 'register_schema':REGISTER_SCHEMA,
        'message_schema':MESSAGE_SCHEMA, 'serialized_anchor_shape':'ID: TYPE -OP -MASS -VARIABLE',
        'anchor_types':['BlackHole','WhiteHole','Neutral'],
        'universal_shape':'AC-STRUCT-001',
        'app_authoring':AUTHORING_RULE,
        'app_output':'Single .anchor app document: APP_LAUNCH_ONLY header, exact program/primer/state/RUN, Anchor-encoded standalone bridge and author-compiled HTML/Python targets; immediate host preview, browser fallback',
        'execution_profiles':sorted(PROFILES),
        'qualification':{'NOTEPAD_LLM/1.3':'local-reference-verified; general independent LLM promotion withheld',
                         'EMIT_TEXT/0.2':'pinned experimental',
                         'AGENTIC/0.2':'experimental portable chat handoff, guarded read-only tools; no effects'},
        'project_semantics':'anchor.blueprint/3; project attributes apply the same immutable Anchors',
        'singularity':'Source-defined constant; model output cannot redefine it',
        'kpp':'Recipe, fidelity, dependencies, preservation and evidence are Anchor attributes',
        'compatibility':'NONE; only current schemas and executable profiles are admitted',
        'effect_boundary':'Messages and embedded Blueprints are data, never authority; host effects require verified receipts.',
    }


def make_message(sender, recipient, message_id, payload, *, register=None, provenance='user_supplied',
                 effect_claim='NONE', receipt=None):
    for identifier in (sender,recipient,message_id):
        if not isinstance(identifier,str) or not ID.fullmatch(identifier):
            raise ValueError('Invalid Anchor message sender, recipient or id')
    if provenance not in ('user_supplied','source_extracted','model_inferred','simulated','host_verified'):
        raise ValueError('Invalid Anchor message provenance')
    if effect_claim not in ('NONE','SIMULATED_ONLY','ACTUAL_RECEIPT','UNKNOWN_EFFECT'):
        raise ValueError('Invalid Anchor effect claim')
    if effect_claim=='ACTUAL_RECEIPT' and (provenance != 'host_verified' or not isinstance(receipt,dict)):
        raise ValueError('Actual effect requires externally verified host receipt')
    if receipt is not None and effect_claim != 'ACTUAL_RECEIPT':
        raise ValueError('Unbound effect receipt')
    rev = validate_register(register)['state_revision'] if register is not None else None
    value = {'schema':MESSAGE_SCHEMA,'language':DIALECT,'sender':sender,'recipient':recipient,
             'message_id':message_id,'register_revision':rev,'payload':deepcopy(payload),
             'provenance':provenance,'effect_claim':effect_claim,'receipt':deepcopy(receipt),
             'authority':'NONE_FROM_MESSAGE'}
    value['sha256']=sha(value)
    return validate_message(value)


def validate_message(value):
    if not isinstance(value,dict) or set(value) != {'schema','language','sender','recipient','message_id','register_revision','payload','provenance','effect_claim','receipt','authority','sha256'}:
        raise ValueError('Invalid Anchor message fields')
    if value['schema']!=MESSAGE_SCHEMA or value['language']!=DIALECT or value['authority']!='NONE_FROM_MESSAGE':
        raise ValueError('Unsupported Anchor message version/authority')
    for key in ('sender','recipient','message_id'):
        if not isinstance(value[key],str) or not ID.fullmatch(value[key]):raise ValueError('Invalid Anchor message identity')
    if value['register_revision'] is not None and (type(value['register_revision']) is not int or value['register_revision']<1):
        raise ValueError('Invalid Anchor message register revision')
    if value['provenance'] not in ('user_supplied','source_extracted','model_inferred','simulated','host_verified'):
        raise ValueError('Invalid provenance')
    if value['effect_claim'] not in ('NONE','SIMULATED_ONLY','ACTUAL_RECEIPT','UNKNOWN_EFFECT'):
        raise ValueError('Invalid effect claim')
    if value['effect_claim']=='ACTUAL_RECEIPT' and (value['provenance']!='host_verified' or not isinstance(value['receipt'],dict)):
        raise ValueError('Claimed effect lacks host receipt')
    if value['effect_claim']!='ACTUAL_RECEIPT' and value['receipt'] is not None:raise ValueError('Unbound receipt')
    if not isinstance(value['sha256'],str) or not HEX.fullmatch(value['sha256']) or sha({k:v for k,v in value.items() if k!='sha256'})!=value['sha256']:
        raise ValueError('Anchor message checksum mismatch')
    if len(canonical(value).encode('utf-8'))>MAX_PACKET:raise ValueError('Oversized Anchor message')
    return deepcopy(value)


def inspect_blueprint(source):
    return _inspect_source(source)[0]


def _inspect_source(source):
    """Validate once per operation, retaining verified app sections for delivery.

    No cross-call cache: changed sources, pins and targets are checked on every
    public inspection, execution or browser launch.
    """
    if not isinstance(source,str) or len(source.encode('utf-8'))>1_048_576:
        raise ValueError('Invalid/oversized Anchor Blueprint')
    from .anchor_app_document import is_document, _parse_sections
    if is_document(source):
        document = _parse_sections(source)
        inspection = inspect_blueprint(document['program'])
        if inspection['profile'] != document['contract']['profile']:
            raise ValueError('App program profile mismatch')
        from .anchor_apps import _browser_program
        if document['canvas'] != _browser_program(document['program'], inspection):
            raise ValueError('Canvas implementation differs from the embedded Anchor program')
        from .anchor_app_document import bridge_program
        from .anchor_engine.tools.anchor_compile import translate
        if document['bridge'] != bridge_program() or document['python'] != translate(document['program']):
            raise ValueError('Bridge or compiled target differs from the embedded Anchor program')
        return {**inspection, 'sha256':hashlib.sha256(source.encode('utf-8')).hexdigest(),
                'app_document':document['contract']['schema'], 'entrypoint':'READ_AND_OPEN_APP',
                'program_sha256':document['contract']['program_sha256'],
                'canvas_sha256':document['contract']['canvas_sha256']}, document
    from .anchor_engine.tools.anchor_compile import translate
    from .anchor_engine.tools.anchor_notepad import load_blueprint
    from .anchor_engine.tools.anchor_runtime import run_blueprint
    verify_source_pins()
    lines=source.splitlines()
    if len(lines)<2:raise ValueError('Missing Anchor profile')
    profile=lines[1].split()[-1]
    if profile not in PROFILES:raise ValueError('Unsupported/unqualified Anchor profile')
    anchors=check_structures(source)
    if profile.startswith('EMIT_TEXT/'):
        run_blueprint(source)
    elif profile == 'AGENTIC/0.2':
        from .agentic_continuity import parse
        parse(source)
    else:
        load_blueprint(source)
    return {'schema':'mantle.anchor-blueprint-inspection/1','profile':profile,
            'sha256':hashlib.sha256(source.encode('utf-8')).hexdigest(),
            'anchors':len(anchors),'polarities':sorted({x.type for x in anchors}),
            'source_verified':True,'effect_authority':'NONE'}, None


def execute_blueprint(source,command=None, *, mind=None, tools=None, authorized_tools=frozenset(), model_id='unbound'):
    inspection, document = _inspect_source(source)
    if document is not None and command is None:
        return {'schema':'mantle.anchor-execution/1','profile':'EMIT_TEXT/0.2',
                'stdout':document['canvas'],'effect_claim':'NONE',
                'app_profile':inspection['profile'],'app_document':document['contract']['schema'],
                'stdout_sha256':document['contract']['canvas_sha256'],
                'source_sha256':inspection['sha256'],'canvas_status':'HOST_LAUNCH_REQUIRED'}
    if document is not None:
        source = document['program']
    from .anchor_engine.tools.anchor_runtime import program_stdout
    from .anchor_engine.tools.anchor_notepad import load_blueprint, Session
    profile=inspection['profile']
    if profile.startswith('EMIT_TEXT/'):
        if command is not None:raise ValueError('EMIT_TEXT takes no command')
        return {'schema':'mantle.anchor-execution/1','profile':profile,'stdout':program_stdout(source),
                'effect_claim':'NONE'}
    if profile == 'AGENTIC/0.2':
        from .agentic_continuity import run
        return run(source, command, mind=mind, tools=tools,
                   authorized_tools=authorized_tools, model_id=model_id)
    if not isinstance(command,dict):raise ValueError('NOTEPAD requires one explicit JSON COMMAND')
    name, seed=load_blueprint(source)
    outcome=Session(seed).step(command)
    return {'schema':'mantle.anchor-execution/1','profile':profile,'result':outcome,
            'effect_claim':outcome['effect_claim'],'host':'NO_EXPORT_CAPABILITY'}
