"""Pinned captures and numeric comparison; observation never supplies acceptance."""
import hashlib
from pathlib import Path

from .core import KPPError, canonical, digest, read_json, write_json
from . import png
from .workshop import load, log, stamp, mutating, preview_fingerprint


def _hash(data):return hashlib.sha256(data).hexdigest()


def _artifact(workspace,relative):
    if not isinstance(relative,str) or not relative.startswith('artifacts/gui/') or '\\' in relative or '..' in relative.split('/'):
        raise KPPError('Invalid GUI evidence artifact path')
    root=Path(workspace).resolve();path=root/relative
    if path.is_symlink() or not path.resolve().is_relative_to(root):raise KPPError('Unsafe GUI evidence artifact')
    return path


def _store(workspace,data,suffix):
    checksum=_hash(data);relative='artifacts/gui/'+checksum+suffix;path=_artifact(workspace,relative)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if _hash(path.read_bytes())!=checksum:raise KPPError('GUI evidence store changed')
    else:
        with path.open('xb') as fp:fp.write(data)
    return {'path':relative,'sha256':checksum}


def _publish(workspace,state,record):
    if len(state['gui_evidence'])>=2048:raise KPPError('GUI evidence index is full; export retained evidence and start a reviewed new workspace')
    record['sequence']=len(state['gui_evidence'])+1
    encoded=(canonical(record)+'\n').encode('utf-8')
    reference=_store(workspace,encoded,'.json');reference['id']=digest(record)
    state['gui_evidence'].append(reference);state['revision']+=1
    write_json(Path(workspace)/'state.json',state)
    log(workspace,'GUI_EVIDENCE_RECORDED',{'id':reference['id'],'schema':record['schema'],'acceptance':'NOT_GRANTED'})
    return {'id':reference['id'],**record,'acceptance':'NOT_GRANTED'}


def _bounded_text(value):return isinstance(value,str) and bool(value.strip()) and len(value)<=2048

def _reference_fingerprint(recipe):
    return digest({'recipe':digest(recipe),'target':recipe['target'],
                   'reference_gui':recipe.get('reference_gui')})


@mutating
def record_capture(workspace,capture,surface,method,actor,mode,ui_state,entries=(),action=None,expected=None,observed=None,entry_observations=()):
    recipe,state=load(workspace)
    if surface not in ('reference','candidate') or method not in ('screenshot','runtime'):
        raise KPPError('GUI observation requires reference/candidate and screenshot/runtime method')
    if not all(_bounded_text(value) for value in (actor,mode,ui_state)):
        raise KPPError('GUI observation needs actor, operating mode and UI state')
    known={e['id'] for e in state.get('gui_inventory',{}).get('entries',[])}
    if not isinstance(entries,(list,tuple)) or any(not isinstance(value,str) or value not in known for value in entries) or len(set(entries))!=len(entries):
        raise KPPError('GUI evidence entries must link to the pinned inventory')
    if method=='runtime' and not all(_bounded_text(value) for value in (action,expected,observed)):
        raise KPPError('Runtime observation needs actual action, expected and observed result')
    source=Path(capture)
    if source.is_symlink() or not source.is_file() or source.stat().st_size>png.MAX_BYTES:raise KPPError('Missing, unsafe or oversized PNG capture')
    data=source.read_bytes();width,height,_=png.decode(data)
    if not isinstance(entry_observations,(list,tuple)) or len(entry_observations)>10000:
        raise KPPError('Invalid per-entry GUI observations')
    observed_ids=set()
    for observation in entry_observations:
        if not isinstance(observation,dict) or set(observation)!={'entry_id','locator','represented','functional','tested'}:
            raise KPPError('Entry observation needs identity, locator and independent stage booleans')
        entry_id=observation['entry_id']
        if not isinstance(entry_id,str) or entry_id not in entries or entry_id in observed_ids or surface!='candidate':
            raise KPPError('Entry observations require distinct linked candidate inventory entries')
        observed_ids.add(entry_id)
        if any(type(observation[stage]) is not bool for stage in ('represented','functional','tested')):
            raise KPPError('Entry stage observations must be explicit independent booleans')
        locator=observation['locator']
        if not isinstance(locator,dict) or set(locator)!={'region'}:
            raise KPPError('Entry locator needs an explicit screenshot region')
        region=locator['region']
        if not isinstance(region,list) or len(region)!=4 or any(type(value) is not int for value in region):
            raise KPPError('GUI region requires integer x, y, width, height')
        x,y,w,h=region
        if x<0 or y<0 or w<1 or h<1 or x+w>width or y+h>height:
            raise KPPError('GUI entry region is outside the captured viewport')
        if method!='runtime' and (observation['functional'] or observation['tested']):
            raise KPPError('A screenshot cannot establish functional or tested behavior')
    image=_store(workspace,data,'.png')
    image.update({'width':width,'height':height})
    record={'schema':'kpp.gui-observation/1','at':stamp(),'recipe_sha256':digest(recipe),
            'workspace_id':state['workspace_id'],'fingerprint':_reference_fingerprint(recipe) if surface=='reference' else preview_fingerprint(recipe,state),
            'target':recipe['target'],'surface':surface,'method':method,'actor':actor,
            'context':{'viewport':[width,height],'mode':mode,'ui_state':ui_state},
            'capture':image,'inventory_entries':list(entries),'entry_observations':list(entry_observations),
            'evidence_kind':'MANUAL_SCREENSHOT' if method=='screenshot' else 'MANUAL_RUNTIME_OBSERVATION',
            'limitations':'Capture integrity and operator-reported context; not authenticated origin, exhaustive discovery or independent interaction proof'}
    if method=='runtime':record['interaction']={'action':action,'expected':expected,'observed':observed,'matches':expected==observed}
    return _publish(workspace,state,record)


def read_evidence(workspace,evidence_id,require_current=True,_visited=None):
    visited=set() if _visited is None else _visited
    if evidence_id in visited or len(visited)>16:raise KPPError('Cyclic or oversized GUI evidence references')
    visited=visited|{evidence_id}
    recipe,state=load(workspace)
    matches=[ref for ref in state['gui_evidence'] if isinstance(ref,dict) and ref.get('id')==evidence_id]
    if len(matches)!=1:raise KPPError('GUI evidence not found or ambiguous')
    reference=matches[0];path=_artifact(workspace,reference['path'])
    if not path.is_file() or path.stat().st_size>2_000_000 or _hash(path.read_bytes())!=reference['sha256']:
        raise KPPError('GUI evidence record is missing or changed')
    record=read_json(path)
    if digest(record)!=evidence_id:raise KPPError('GUI evidence identity changed')
    if record.get('schema') not in ('kpp.gui-observation/1','kpp.gui-comparison/1'):
        raise KPPError('Unsupported GUI evidence schema')
    for key in ('capture','difference'):
        if key in record:
            item=record[key];image=_artifact(workspace,item['path'])
            if not image.is_file() or image.stat().st_size>png.MAX_BYTES or _hash(image.read_bytes())!=item['sha256']:
                raise KPPError('GUI capture/difference is missing or changed')
    expected_pin=_reference_fingerprint(recipe) if record.get('surface')=='reference' else preview_fingerprint(recipe,state)
    if require_current and (record.get('recipe_sha256')!=digest(recipe) or record.get('workspace_id')!=state['workspace_id'] or record.get('fingerprint')!=expected_pin):
        raise KPPError('GUI evidence source/workspace pin is stale')
    if record['schema']=='kpp.gui-comparison/1':
        for key in ('reference','candidate'):
            child=read_evidence(workspace,record[key],require_current,visited)
            if child['schema']!='kpp.gui-observation/1':raise KPPError('Comparison must refer directly to observations')
    return record


@mutating
def compare_captures(workspace,reference_id,candidate_id,actor):
    recipe,state=load(workspace)
    if not _bounded_text(actor):raise KPPError('GUI comparison needs an actor label')
    reference=read_evidence(workspace,reference_id);candidate=read_evidence(workspace,candidate_id)
    if reference['schema']!='kpp.gui-observation/1' or candidate['schema']!='kpp.gui-observation/1' or reference['surface']!='reference' or candidate['surface']!='candidate':
        raise KPPError('Comparison needs reference and candidate observations')
    if reference['context']!=candidate['context'] or reference['target']!=candidate['target']:
        raise KPPError('Compare matching target, viewport, operating mode and UI state')
    width,height,left=png.read(_artifact(workspace,reference['capture']['path']))
    other_width,other_height,right=png.read(_artifact(workspace,candidate['capture']['path']))
    if (width,height)!=(other_width,other_height):raise KPPError('Capture viewport mismatch')
    changed=0;absolute=0;maximum=0;heat=bytearray(len(left))
    for offset in range(0,len(left),4):
        delta=[abs(left[offset+channel]-right[offset+channel]) for channel in range(4)]
        strongest=max(delta);changed+=bool(strongest);absolute+=sum(delta);maximum=max(maximum,strongest)
        heat[offset:offset+4]=bytes((strongest,0,0,255))
    difference=_store(workspace,png.encode(width,height,bytes(heat)),'.png')
    record={'schema':'kpp.gui-comparison/1','at':stamp(),'recipe_sha256':digest(recipe),
            'workspace_id':state['workspace_id'],'fingerprint':preview_fingerprint(recipe,state),
            'actor':actor,'reference':reference_id,'candidate':candidate_id,'target':recipe['target'],
            'context':reference['context'],'difference':difference,
            'metrics':{'pixels':width*height,'changed_pixels':changed,'changed_fraction':changed/(width*height),
                       'mean_absolute_rgba_error':absolute/len(left),'maximum_channel_error':maximum},
            'visual_conformance':'PIXEL_MEASURED_REVIEW_REQUIRED','behavioral_conformance':'NOT_ESTABLISHED',
            'limitations':'Raw RGBA differences supplement human review; equality is not behavioral parity or exhaustive GUI coverage'}
    return _publish(workspace,state,record)


def evidence_current(record):
    try:
        evidence=read_evidence(record['gui_workspace'],record['gui_evidence_id'])
        if digest(evidence)!=record['gui_evidence_sha256']:return False
        if evidence['schema']=='kpp.gui-observation/1' and evidence.get('interaction',{}).get('matches') is False:return False
        return True
    except (KPPError,OSError,KeyError,TypeError,ValueError):return False


def summary(workspace):
    _,state=load(workspace);current=[];stale=[]
    for reference in state['gui_evidence']:
        try:
            record=read_evidence(workspace,reference['id']);current.append({'id':reference['id'],'schema':record['schema'],'method':record.get('method'),'surface':record.get('surface')})
        except (KPPError,OSError,KeyError,TypeError,ValueError):stale.append(reference.get('id'))
    return {'current':current,'stale':stale,'acceptance':'SEPARATE_BAKER_REVIEW','scope':'Source-bound recorded observations; not automatic parity'}

def coverage_matrix(workspace):
    """Independent evidence axes; mapping, appearance and acceptance never promote each other."""
    recipe,state=load(workspace)
    from .graph import accepted_ids
    accepted=accepted_ids(recipe,state)
    inventory=state.get('gui_inventory',{'entries':[]})
    observations={entry['id']:{stage:[] for stage in ('represented','functional','tested')} for entry in inventory['entries']}
    stale=[]
    for reference in state['gui_evidence']:
        try:record=read_evidence(workspace,reference['id'])
        except (KPPError,OSError,KeyError,TypeError,ValueError):stale.append(reference['id']);continue
        if record['schema']!='kpp.gui-observation/1' or record['surface']!='candidate':continue
        for item in record.get('entry_observations',[]):
            if item['entry_id'] not in observations:continue
            for stage in observations[item['entry_id']]:
                observations[item['entry_id']][stage].append({'id':reference['id'],'supported':item[stage],
                    'context':record['context'],'locator':item['locator'],'kind':record['evidence_kind'],
                    'interaction_matches':record.get('interaction',{}).get('matches')})
    rows=[]
    for entry in inventory['entries']:
        excluded=entry['disposition']=='excluded'
        row={'id':entry['id'],'label':entry['label'],'anchor_ids':entry['anchor_ids'],
             'excluded':{'baker':entry['scope_approval']['baker'],'reason':entry['scope_approval']['evidence']} if excluded else None,
             'accounted_for':excluded or bool(entry['anchor_ids']),
             'discovered':{'supported':True,'basis':'pinned reference declaration','file':entry['file'],'path':entry['path']}}
        for stage,items in observations[entry['id']].items():
            grouped={}
            for item in items:grouped.setdefault(digest(item['context']),set()).add(item['supported'])
            conflict=any(len(values)>1 for values in grouped.values())
            row[stage]={'supported':any(item['supported'] for item in items) and not conflict,
                        'conflicted':conflict,'observations':items}
        links=entry['anchor_ids']
        row['accepted']={'supported':not excluded and bool(links) and all(a in accepted for a in links),
                         'basis':'Baker-approved mapped obligations only; no inference of representation or behavior',
                         'anchor_ids':[a for a in links if a in accepted]}
        rows.append(row)
    count=len(rows)
    counts={'discovered':count,'accounted_for':sum(row['accounted_for'] for row in rows),
            **{stage:sum(row[stage]['supported'] for row in rows) for stage in ('represented','functional','tested','accepted')},
            'excluded':sum(row['excluded'] is not None for row in rows)}
    return {'schema':'kpp.gui-coverage-matrix/1','recipe_sha256':digest(recipe),'rows':rows,'counts':counts,
            'percent_of_discovered':{stage:(100*value/count if count else None) for stage,value in counts.items()},
            'stale_evidence':stale,'scope':'Independent source-bound observations across explicitly reported UI contexts; tested means exercised, not necessarily passed; acceptance approves obligations only'}
