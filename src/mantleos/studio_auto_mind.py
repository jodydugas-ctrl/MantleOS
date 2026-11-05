"""Owner-configured foreground cognition worker, independent of Node-RED work.

Configuration is local operator data. Portable Studio projects never include it.
The worker reads the pending Body frame; JSON callers cannot supply a substitute
PRIMER, change a route, authorize effects, or grant Baker acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid

from . import json_contract as c
from .transactions import atomic_bytes, body_lock
from .studio_mind_config import load_owner_file
from .studio_mind_budget import MindBudget
from .studio_mind_provider import StudioProvider

SCHEMA='studio.openrouter-route/2'


def _account_location(path):
    # Compare lexical owner path spellings consistently. Keep the original
    # path for MindBudget's link/sidecar checks before opening storage; resolving
    # symlinks here would hide a forbidden alias. Hard-link aliases stay distinct.
    return os.path.normcase(os.path.abspath(path))


def configure(nest, *, owner_file, catalog, accounting_file=None, reviewed=False):
    from . import studio
    if reviewed is not True:
        raise PermissionError('Explicit owner route review required')
    nest=Path(nest)
    owner=load_owner_file(owner_file)
    # A catalog is source-bound public model/provider metadata, not executable
    # callbacks or instructions. Its exact routing projection is reviewed here.
    if (not isinstance(catalog,dict) or set(catalog)!={'allowed','provider_slugs','free_models','provenance'}
            or not isinstance(catalog['provenance'],dict) or not catalog['provenance']):
        raise ValueError('Reviewed public catalog with provenance required')
    with body_lock(nest), studio.database(nest) as db:
        if studio._setting(db,'phase')!='STASIS':
            raise PermissionError('Configure automatic cognition while Studio is in stasis')
        if db.execute("SELECT 1 FROM mind WHERE phase='AWAITING_MIND'").fetchone():
            raise PermissionError('Existing supervised preparation requires explicit recovery')
        # The default belongs to the owner configuration, not a newly born
        # NEST. Explicit paths allow several owner files to share one account.
        # Never silently discard historical per-NEST spending on upgrade.
        previous_path=nest/'mind-route.json'
        previous=c.loads(previous_path.read_text('utf8')) if previous_path.exists() else None
        selected=accounting_file
        if selected is None and previous and previous.get('schema')==SCHEMA:
            selected=previous.get('accounting_file')
        accounting_path=Path(selected) if selected is not None else Path(
            str(owner.source)+'.studio-budget.sqlite')
        accounting_path=accounting_path.absolute()
        legacy_path=(nest/'mind-accounting.sqlite').absolute()
        if legacy_path.exists() and _account_location(accounting_path)!=_account_location(legacy_path):
            raise PermissionError('Retain existing accounting with --accounting-file; spending cannot reset')
        if previous and previous.get('schema')==SCHEMA:
            if _account_location(accounting_path)!=_account_location(previous.get('accounting_file')):
                raise PermissionError('Existing accounting cannot be replaced through route configuration')
            accounting=MindBudget(accounting_path)
            if accounting.identity()!=previous.get('accounting_identity'):
                raise PermissionError('MIND accounting identity changed; recovery review required')
        else:
            accounting=MindBudget(accounting_path,create=True)
        pin=studio.controller_pin()
        policy=c.digest({'ordinary':'reply-proposal-only','actions':'existing-body-broker',
                         'release':'exact-committed-body-result','budget':'persistent-reservations'})
        StudioProvider(config=owner,accounting=accounting,source_sha256=pin,
            policy_sha256=policy,allowed=catalog['allowed'],provider_slugs=catalog['provider_slugs'],
            free_models=catalog['free_models'],source_check=lambda:None)
        document={'schema':SCHEMA,'owner_file':str(owner.source),
                  'owner_sha256':owner.source_sha256,'controller_pin':pin,
                  'policy_sha256':policy,'catalog':catalog,'revision':uuid.uuid4().hex,
                  'accounting_file':str(accounting_path),'accounting_identity':accounting.identity()}
        atomic_bytes(nest/'mind-route.json',c.canonical(document).encode('utf8'),replace=True)
    return public_status(nest)


def _load(nest):
    from . import studio
    nest=Path(nest)
    path=nest/'mind-route.json'
    if path.is_symlink() or getattr(path,'is_junction',lambda:False)():
        raise PermissionError('Linked provider configuration unavailable')
    try:
        with path.open('rb') as stream:
            raw=stream.read(1048577)
    except OSError:
        raise PermissionError('Private provider configuration unavailable; review required') from None
    if len(raw)>1048576:
        raise ValueError('Provider catalog budget exceeded')
    route=c.loads(raw.decode('utf8'))
    if route.get('schema')!=SCHEMA or route.get('controller_pin')!=studio.controller_pin():
        raise PermissionError('Provider source configuration requires owner review')
    try:
        owner=load_owner_file(route['owner_file'])
    except (OSError,ValueError):
        raise PermissionError('Private owner configuration unavailable; review required') from None
    if owner.source_sha256!=route['owner_sha256']:
        raise PermissionError('Owner provider configuration changed; review required')
    _accounting(route)
    return route,owner


def _accounting(route):
    """Opening a route never creates or substitutes its spending database."""
    try:
        accounting=MindBudget(route['accounting_file'])
        if accounting.identity()!=route['accounting_identity']:
            raise ValueError('Account identity changed')
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):
        raise PermissionError('MIND accounting unavailable or changed; recovery review required') from None
    return accounting


def public_status(nest):
    if not (Path(nest)/'mind-route.json').exists():
        return {'route':'SUPERVISED_HOST_ONLY'}
    route,owner=_load(nest)
    status=_accounting(route).status(
        {'mind':owner.mind_budget_micro_usd,'limbs':owner.limbs_budget_micro_usd})
    return {'route':'OPENROUTER_OWNER_CONFIGURED','models':list(owner.models),
            'budget':status,'accounting_scope':'OWNER_SELECTED_SHARED_DATABASE',
            'provider_calls_on_status':0,'isolation':'SAME_OWNER_PROCESS_BOUNDARY_UNQUALIFIED'}


def generate(nest, request_id, *, transport=None):
    from . import studio
    c.identifier(request_id)
    nest=Path(nest)
    route,owner=_load(nest)
    def check_source():
        with studio.database(nest) as db:
            if studio._setting(db,'phase')!='ACTIVE':
                raise PermissionError('Automatic cognition requires an active Body')
            pending=db.execute('SELECT phase,frame FROM mind WHERE id=?',(request_id,)).fetchone()
            if pending is not None and pending[0]=='AWAITING_MIND':
                studio.check_preparation(db,c.loads(pending[1]))
        # A route edit, even to different valid settings, invalidates this worker.
        current,_=_load(nest)
        if current!=route:
            raise PermissionError('Provider route changed during preparation')
    check_source()
    with studio.database(nest) as db:
        row=db.execute('SELECT phase,frame FROM mind WHERE id=?',(request_id,)).fetchone()
        if row is None:
            raise KeyError('Unknown Body cognition request')
        if row[0]=='COMMITTED':
            return {'status':'ALREADY_COMMITTED'}
        if row[0]!='AWAITING_MIND':
            raise PermissionError('Body cognition requires recovery review')
        wrapper=c.loads(row[1])
        studio.check_preparation(db,wrapper)
    if wrapper.get('mind_route_revision')!=route['revision']:
        raise PermissionError('Body cognition route requires recovery review')
    # An action's checked observation creates a different frame and one subsequent
    # attempt. Replaying the same pending frame never makes another API call.
    attempt_id=c.digest({'request_id':request_id,'frame':wrapper['frame']})
    catalog=route['catalog']
    provider=StudioProvider(config=owner,accounting=_accounting(route),
        source_sha256=route['controller_pin'],policy_sha256=route['policy_sha256'],
        allowed=catalog['allowed'],provider_slugs=catalog['provider_slugs'],
        free_models=catalog['free_models'],source_check=check_source,transport=transport)
    result=provider.generate(wrapper=wrapper,request_id=attempt_id)
    # Neither a claim token nor a private source path belongs in the courier RPC.
    result.pop('claim',None)
    return {**result,'attempt_id':attempt_id}


def validate_result(nest, request_id, wrapper, proposal):
    """Body admission checks its retained result, independently of the courier."""
    route,owner=_load(nest)
    if wrapper.get('mind_route_revision')!=route['revision']:
        raise PermissionError('Body cognition route changed')
    catalog=route['catalog']
    accounting=_accounting(route)
    provider=StudioProvider(config=owner,accounting=accounting,
        source_sha256=route['controller_pin'],policy_sha256=route['policy_sha256'],
        allowed=catalog['allowed'],provider_slugs=catalog['provider_slugs'],
        free_models=catalog['free_models'],source_check=lambda:None)
    attempt_id=c.digest({'request_id':request_id,'frame':wrapper['frame']})
    result=accounting.retained_result(purpose='mind',request_id=attempt_id,
                                     binding=provider.binding(wrapper))
    if (result['status'] not in ('RESULT','ADMITTED')
            or 'proposal' not in result['value']
            or c.canonical(result['value']['proposal'])!=c.canonical(proposal)):
        raise PermissionError('Proposal does not match the retained provider result')


def serve(nest):
    """Trusted foreground pipe. No provider request occurs before generate."""
    for raw in iter(lambda:sys.stdin.buffer.readline(65537),b''):
        request={}
        try:
            if len(raw)>65536:
                raise ValueError('Cognition command budget exceeded')
            request=c.loads(raw.decode('utf8'))
            c.shape(request,{'id','op','args'})
            if request['op']=='status':
                c.shape(request['args'],set())
                result=public_status(nest)
            elif request['op']=='generate':
                c.shape(request['args'],{'request_id'})
                result=generate(nest,request['args']['request_id'])
            else:
                raise ValueError('Unsupported cognition operation')
            output={'id':request.get('id'),'ok':True,'result':result}
        except Exception as exc:
            # No raw network/parser/filesystem diagnostics, paths, or secrets.
            output={'id':request.get('id'),'ok':False,'error':'MIND_'+type(exc).__name__}
        print(json.dumps(output,ensure_ascii=False,separators=(',',':')),flush=True)
        if len(raw)>65536:
            return 1
    return 0
