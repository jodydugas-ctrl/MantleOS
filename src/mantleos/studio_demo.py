"""Packaged, reviewed local calculator bake. Imported fixtures never execute.

This small demonstrator exercises real KPP regression gates, not code synthesis.
"""
import hashlib
from pathlib import Path
import time
import uuid

from . import anchors, anchor_design, studio_project, json_contract as c
from .transactions import atomic_bytes, body_lock
from .kpp import satisfaction as s, workshop, testing
from .kpp.core import write_json, read_json, digest

CALCULATOR='''def normalize(value):
    if type(value) not in (int, float): raise ValueError('Numeric input required')
    return value
def add(a,b): return normalize(a)+normalize(b)
def undo(history): return history[-2]
def guarded(value,allowed):
    if not allowed: raise PermissionError('Denied')
    return value
'''


def project():
    resources=Path(__file__).parent/'kpp/resources'
    recipe=read_json(resources/'recipes/conventional-python-v4.json')
    recipe.update(id='studio-calculator-demo',goal='Preserve calculator input, arithmetic, history and guarded release')
    recipe['target']={'description':'Synthetic calculator with numeric input, addition, undo history and explicitly guarded publication',
        'source':'Packaged synthetic behavioral contract','reference_version':'studio-calculator/1',
        'fidelity_semantics':'Direct arithmetic, retained history consequences and denied publication cases'}
    roles=[('BH-INPUT','BlackHole','Receive numeric input'),('N-CALC','Neutral','Own arithmetic result'),('N-HISTORY','Neutral','Own undo history'),('WH-BOUNDARY','WhiteHole','Guard result publication')]
    recipe['anchor_design']={'schema':anchor_design.SCHEMA,'id':'Studio-Calculator','purpose':recipe['goal'],
        'applications':[anchors.application(i,definition_id=t,attributes={'responsibility':r}) for i,t,r in roles],
        'flows':[{'from':a,'to':b,'relationship':r} for a,b,r in [('BH-INPUT','N-CALC','Normalized numbers'),('N-CALC','N-HISTORY','Append arithmetic consequence'),('N-HISTORY','WH-BOUNDARY','Request guarded release')]],
        'state':[{'id':'result','owner':'N-CALC'},{'id':'undo-history','owner':'N-HISTORY'}],
        'effects':[{'id':'publication','requester':'N-HISTORY','guard':'WH-BOUNDARY','confirmation':'Explicit independent release grant'}]}
    ids=['input','calculation','history','integrity']
    recipe['anchors']=[{'id':n,'statement':r,'test':'Execute '+n+' consequence and preserve earlier cases','required':True,'depth':i+1,'depends':ids[i-1:i],'design_anchors':[roles[i][0]]} for i,(n,(_,_,r)) in enumerate(zip(ids,roles))]
    checks=['assert m.normalize(2)==2\ntry: m.normalize("x")\nexcept ValueError: pass\nelse: raise AssertionError("Invalid input accepted")',
            'assert m.add(2,3)==5', 'assert m.undo([2,5])==2',
            'try: m.guarded(5,False)\nexcept PermissionError: pass\nelse: raise AssertionError("Missing guard")\nassert m.guarded(5,True)==5']
    fixtures={};cases=[]
    for name,check in zip(ids,checks):
        script='case_'+name+'.py'
        content='import runpy,sys,types\nfrom pathlib import Path\nm=types.SimpleNamespace(**runpy.run_path(str(Path(sys.argv[1])/"calculator.py")))\n'+check+'\n'
        fixtures[script]={'content':content,'sha256':hashlib.sha256(content.encode()).hexdigest()}
        cases.append({'id':name,'obligations':[name],'script':script,'relationship':name+' state/authority consequence','requires':[]})
    content=c.canonical({'schema':s.SUITE,'recipe_sha256':digest(recipe),'cases':cases})
    fixtures['suite.json']={'content':content,'sha256':hashlib.sha256(content.encode()).hexdigest()}
    return studio_project.validate({'schema':studio_project.SCHEMA,'id':'Anchor-Studio-Demo','recipe':recipe,
        'layout':{r[0]:[160+i*180,180] for i,r in enumerate(roles)},'unresolved':[],
        'provenance':[{'kind':'packaged-synthetic-calculator','sha256':hashlib.sha256(CALCULATOR.encode()).hexdigest()}],'evidence':[],'fixtures':fixtures})


def qualify(nest):
    from .studio import project_get
    selected=project_get(nest)
    if selected.get('project')!=project():raise ValueError('Only the unchanged packaged demonstrator is authorized here; imported code never executes')
    root=Path(nest)/'evaluations'/('calculator-'+uuid.uuid4().hex)
    candidate=root/'candidate';suite=root/'suite';candidate.mkdir(parents=True);suite.mkdir()
    (candidate/'calculator.py').write_text(CALCULATOR,encoding='utf8')
    for name,item in project()['fixtures'].items():(suite/name).write_text(item['content'],encoding='utf8')
    context=root/'context.json';write_json(context,{'capabilities':{}})
    ws=root/'workspace';workshop.begin(ws,project()['recipe'],Path(__file__).parent/'kpp/resources')
    s.start(ws,candidate,suite,context,reviewed=True)
    stages=[];started=time.perf_counter()
    for _ in range(3):
        report=s.test(ws,execute=True,reviewed=True);stages.append(report)
        if not report['all_passed']:raise ValueError('Packaged baseline failed')
    (candidate/'calculator.py').write_text(CALCULATOR.replace('history[-2]','history[-1]'),encoding='utf8')
    rejected=s.test(ws,execute=True,reviewed=True);stages.append(rejected)
    if rejected['all_passed'] or not any(r['id']=='history' and r['outcome']=='FAIL' for r in rejected['results']):raise ValueError('Regression was not rejected')
    (candidate/'calculator.py').write_text(CALCULATOR,encoding='utf8')
    final=s.test(ws,execute=True,reviewed=True);stages.append(final)
    s.completion_guard(ws)
    record={'project_sha256':selected['revision'],'workspace':str(ws.resolve()),'candidate':str(candidate.resolve()),'suite':str(suite.resolve()),
        'report_path':final['report_path'],'stages':[{'targets':r['targets'],'all_passed':r['all_passed'],'results':r['results'],'report_path':r['report_path']} for r in stages],
        'elapsed_ms':(time.perf_counter()-started)*1000,'acceptance':'PENDING_BAKER','scope':'Packaged calculator consequences only'}
    write_json(root/'qualification.json',record)
    with body_lock(Path(nest)):atomic_bytes(Path(nest)/'current-evaluation.json',c.canonical(record).encode(),replace=True)
    return record


def accept(nest,*,baker,confirmed=False):
    """Authenticated operator action, separate from testing and MIND proposals."""
    from .studio import project_get
    if confirmed is not True:raise PermissionError('Explicit Baker action required')
    with body_lock(Path(nest)):
        record=read_json(Path(nest)/'current-evaluation.json')
        if project_get(nest)['revision']!=record['project_sha256']:raise ValueError('Project changed after qualification')
        root=(Path(nest)/'evaluations').resolve()
        for key in ('workspace','candidate','suite','report_path'):
            if not Path(record[key]).resolve().is_relative_to(root):raise ValueError('Evaluation escaped managed directory')
        s.completion_guard(record['workspace'])
        testing.accept_tested(record['workspace'],record['report_path'],record['candidate'],record['suite'],baker)
        return workshop.finish(record['workspace'])
