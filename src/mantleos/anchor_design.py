"""Compact responsibility contracts using the authoritative Anchor applications.
Design is data. Validation grants neither execution nor acceptance.
"""
from copy import deepcopy
from . import anchors, json_contract as c

SCHEMA = 'anchor.design/1'

def validate(value):
    c.shape(value, {'schema','id','purpose','applications','flows','state','effects'})
    c.require(value['schema']==SCHEMA, 'Unsupported Anchor design')
    c.identifier(value['id']);c.text(value['purpose'])
    for key in ('applications','flows','state','effects'):
        c.require(type(value[key]) is list and len(value[key])<=256, 'Invalid design collection: '+key)
    c.require(bool(value['applications']), 'Design needs applications')
    apps={}
    for raw in value['applications']:
        app=anchors.validate(raw);aid=app['id']
        c.require(aid not in apps, 'Duplicate design application')
        c.text(app['attributes'].get('responsibility'))
        apps[aid]=app
    seen=set()
    for edge in value['flows']:
        c.shape(edge, {'from','to','relationship'})
        c.identifier(edge['from']);c.identifier(edge['to'])
        c.require(edge['from'] in apps and edge['to'] in apps, 'Unknown flow endpoint')
        c.text(edge['relationship'])
        pair=(edge['from'],edge['to'],edge['relationship'])
        c.require(pair not in seen, 'Duplicate flow');seen.add(pair)
    states=set()
    for state in value['state']:
        c.shape(state, {'id','owner'})
        c.identifier(state['id'])
        c.require(state['id'] not in states, 'Conflicting state ownership')
        c.identifier(state['owner'])
        c.require(state['owner'] in apps and apps[state['owner']]['type']=='Neutral', 'State needs a Neutral owner')
        states.add(state['id'])
    effects=set()
    for effect in value['effects']:
        c.shape(effect, {'id','requester','guard','confirmation'})
        c.identifier(effect['id']);c.text(effect['confirmation'])
        c.require(effect['id'] not in effects, 'Duplicate effect');effects.add(effect['id'])
        c.identifier(effect['requester']);c.identifier(effect['guard'])
        c.require(effect['requester'] in apps, 'Unknown effect requester')
        c.require(effect['guard'] in apps and apps[effect['guard']]['type']=='WhiteHole', 'Effect needs a WhiteHole guard')
    c.canonical(value,limit=32768)
    return deepcopy(value)

def recipe_design(recipe):
    design=recipe.get('anchor_design')
    refs=[a.get('design_anchors',[]) for a in recipe['anchors']]
    if design is None:
        c.require(not any(refs), 'Design references require a design')
        return None
    c.require(recipe['schema']=='kpp.recipe/4', 'Anchor design requires recipe/4')
    design=validate(design);ids={a['id'] for a in design['applications']};covered=set()
    for obligation,targets in zip(recipe['anchors'],refs):
        c.require(type(targets) is list and all(type(t) is str and t in ids for t in targets)
                  and len(targets)==len(set(targets)), 'Invalid obligation design references')
        if obligation['required']:
            c.require(bool(targets), 'Mandatory obligation needs design coverage');covered.update(targets)
    c.require(covered==ids, 'Every design application needs mandatory acceptance coverage')
    return design

def projection(value, ids=None):
    value=validate(value);selected=set(ids) if ids is not None else {a['id'] for a in value['applications']}
    return {'schema':SCHEMA,'id':value['id'],'sha256':c.digest(value),'purpose':value['purpose'],
            'responsibilities':[{'id':a['id'],'type':a['type'],'responsibility':a['attributes']['responsibility']}
                                for a in value['applications'] if a['id'] in selected],
            'state':value['state'],'effects':value['effects'], 'authority':'DESIGN_ONLY'}

def review(value):
    value=validate(value);groups={};owned={s['owner'] for s in value['state']}
    for a in value['applications']:
        groups.setdefault(a['attributes']['responsibility'].strip().casefold(),[]).append(a['id'])
    return {'duplicate_responsibilities':[v for v in groups.values() if len(v)>1],
            'neutrals_without_declared_state':[a['id'] for a in value['applications'] if a['type']=='Neutral' and a['id'] not in owned],
            'boundary_limits':'Only declared effects and state are checked; omitted real behavior requires tests and review.',
            'decision':'ADVISORY_ONLY','authority':'NONE'}

def render(value):
    value=validate(value)
    lines=['ANCHOR DESIGN: '+value['id'],'STATUS: DESIGN CONTRACT ONLY — NOT AN EXECUTABLE ANCHOR PROFILE','',value['purpose'],'',
           'ANCHORS (ID | canonical type | canonical singularity | responsibility)']
    for a in value['applications']:
        lines.extend([a['id']+' | '+a['type']+' | '+a['singularity'],'  '+a['attributes']['responsibility']])
    lines+=['','FLOW:']+[e['from']+' -> '+e['to']+': '+e['relationship'] for e in value['flows']]
    lines+=['','STATE OWNERSHIP:']+[s['id']+' -> '+s['owner'] for s in value['state']]
    lines+=['','GUARDED EFFECTS:']+[e['id']+': '+e['requester']+' -> '+e['guard']+'; '+e['confirmation'] for e in value['effects']]
    return '\n'.join(lines+['','N-RULE-ECONOMY: '+anchors.RULE_ECONOMY,'Acceptance requires current behavioral evidence and explicit Baker review.',''])

def journal_design():
    responsibilities=[('BH-ENCOUNTER','BlackHole','Receive user input, semantic proposals and checked observations; normalize without changing canonical experience.'),
      ('N-CONTINUITY','Neutral','Own identity bindings, append-only experience, recall and committed request/reply continuity.'),
      ('N-HOST','Neutral','Coordinate PRIMER-first model frames, authorized host operations and verified portable handoff.'),
      ('WH-INTEGRITY','WhiteHole','Enforce source, PRIMER, state, authority, observation, commit and release boundaries.')]
    return validate({'schema':SCHEMA,'id':'Anchor-Journal','purpose':'Portable continuity with compact responsibilities and durable exact replies.',
      'applications':[anchors.application(i,definition_id=t,attributes={'responsibility':r}) for i,t,r in responsibilities],
      'flows':[{'from':a,'to':b,'relationship':r} for a,b,r in [('BH-ENCOUNTER','WH-INTEGRITY','Validate input and bindings'),('WH-INTEGRITY','N-CONTINUITY','Admit checked records atomically'),('N-CONTINUITY','N-HOST','Project relevant committed memory'),('N-HOST','BH-ENCOUNTER','Receive semantic proposals and verified observations')]],
      'state':[{'id':i,'owner':o} for i,o in [('identity-bindings','N-CONTINUITY'),('experience','N-CONTINUITY'),('encounter-preparation','N-HOST')]],
      'effects':[{'id':i,'requester':'N-HOST','guard':'WH-INTEGRITY','confirmation':text} for i,text in [('checked-read','Host broker grants capability; verified observation binds reply.'),('reply-release','Release broker grants permission; release exact durable committed reply.'),('portable-export','Consistent verified export succeeds before reporting Save.')]]})
