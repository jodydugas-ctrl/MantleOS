"""Run synthetic cumulative construction and actual native continuity checks.

Usage: PYTHONPATH=src python tools/satisfaction_specimen.py --output NEW_DIRECTORY
No provider, private state or browser is used.
"""
import argparse
import copy
import json
import statistics
import time
from pathlib import Path
from mantleos import anchors, cells, engram, anchor_design
from mantleos.kpp import satisfaction as s
from mantleos.kpp.core import digest, write_json
from mantleos.kpp.workshop import begin


def run(output):
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    resources = Path(s.__file__).parent/'resources'
    recipe = json.loads((resources/'recipes/conventional-python-v4.json').read_text())
    recipe.update(id='satisfaction-calculator',goal='Preserve direct and deeper calculator state consequences')
    design = dict(schema=anchor_design.SCHEMA,id='calculator-contract',purpose=recipe['goal'],
                  applications=[anchors.application('N-CALCULATOR',definition_id='Neutral',attributes={'responsibility':'Own calculator result and undo state'})],
                  flows=[],state=[dict(id='calculator-state',owner='N-CALCULATOR')],effects=[])
    recipe['anchor_design']=design
    recipe['anchors']=[dict(id=n,statement=n,test='Execute '+n+' and its declared state consequences',required=True,depth=i+1,
                            depends=[] if i<2 else ['direct','history'],design_anchors=['N-CALCULATOR'])
                       for i,n in enumerate(['direct','history','integration'])]
    def scenario(name,batch):
        root=output/name;root.mkdir();candidate=root/'candidate';candidate.mkdir();suite=root/'suite';suite.mkdir()
        (candidate/'calculator.py').write_text('def add(a,b): return a+b\ndef undo(history): return history[-2]\n')
        cases=[]
        for cid,aid,assertion in [('addition','direct','assert m.add(2,3)==5'),('undo','history','assert m.undo([3,5])==3'),('combined','integration','assert m.add(m.undo([3,5]),2)==5')]:
            script='import runpy,sys,types\nfrom pathlib import Path\nm=types.SimpleNamespace(**runpy.run_path(str(Path(sys.argv[1])/"calculator.py")))\n'+assertion+'\n'
            (suite/(cid+'.py')).write_text(script)
            cases.append(dict(id=cid,obligations=[aid],script=cid+'.py',relationship=aid+' consequence',requires=[]))
        write_json(suite/'suite.json',dict(schema=s.SUITE,recipe_sha256=digest(recipe),cases=cases))
        context=root/'context.json';write_json(context,dict(capabilities={}))
        workspace=root/'workspace';begin(workspace,recipe,resources)
        s.start(workspace,candidate,suite,context,reviewed=True)
        reports=[]
        def check():
            t=time.perf_counter();r=s.test(workspace,execute=True,reviewed=True,batch_size=batch)
            reports.append(dict(targets=r['targets'],outcomes=r['results'],passed=r['all_passed'],milliseconds=(time.perf_counter()-t)*1000))
            return r
        check()
        if batch==1:check()  # Deeper history obligation, same single application.
        original=(candidate/'calculator.py').read_text()
        (candidate/'calculator.py').write_text(original.replace('history[-2]','history[-1]'))
        assert check()['all_passed'] is False
        (candidate/'calculator.py').write_text(original)
        assert check()['all_passed'] is True
        samples=[]
        for _ in range(20):
            t=time.perf_counter();s.plan(workspace);samples.append((time.perf_counter()-t)*1000)
        return dict(stages=reports,planning_median_ms=statistics.median(samples),planning_p95_ms=sorted(samples)[18],applications=1,acceptance='PENDING_BAKER')
    result={'single':scenario('single',1),'batch':scenario('batch',2)}
    # Actual kernel-relative append semantics, exact head and stale writer boundary.
    ledger=output/'native'/'ENGRAM.jsonl';ledger.parent.mkdir()
    first=engram.append(ledger,'observation','synthetic-specimen',{'text':'Preserve amber'},expected_head=engram.ZERO)
    cell=cells.append_segment(first);assert cell['payload']['record']==first
    try:engram.append(ledger,'observation','synthetic-specimen',{'text':'stale'},expected_head=engram.ZERO)
    except ValueError:pass
    else:raise AssertionError('Stale native append accepted')
    assert engram.read(ledger)==[first]
    result['native']={'record_head':first['sha256'],'append_cell_and_stale_boundary':'PASS','scope':'Native tape append, not complete Body/AppAI qualification'}
    result['limits']='Synthetic local execution; no model, browser, OS isolation or full product parity qualification.'
    write_json(output/'report.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    print(json.dumps(run(parser.parse_args().output),indent=2))
