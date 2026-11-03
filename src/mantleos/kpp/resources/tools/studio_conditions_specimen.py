"""Actual KPP cumulative checks of the bounded IF slice; no full n8n parity claim."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from mantleos.kpp import satisfaction as s
from mantleos.kpp.core import write_json,digest
from mantleos.kpp.workshop import begin


def run(output,node,modules,reference=None):
    from studio_chase_inventory import design
    root=Path(output).resolve();root.mkdir(parents=True,exist_ok=False)
    resources=Path(__file__).resolve().parents[1];specimen=resources/'examples/anchor-studio'
    candidate=root/'candidate';candidate.mkdir();(candidate/'palette').mkdir()
    for name in ('conditions.cjs','conditions.test.cjs','conditions-runtime-probe.cjs','conditions-reference-probe.cjs','palette/nodes.js','palette/nodes.html'):
        shutil.copyfile(specimen/name,candidate/name)
    recipe=json.loads((resources/'recipes/conventional-python-v4.json').read_text('utf8'))
    recipe.update(id='studio-if-consequence-slice',goal='Verify the bounded strict IF slice on Node-RED; retain full Community chase as unfinished',tissue='mixed',anchor_design=design())
    recipe['implementation']['components'].append(dict(id='if-runtime',policy='required',languages=['javascript']))
    recipe['target'].update(description='Strict IF subset: number/string/boolean, AND/OR, pairing, branch suppression and errors. Full n8n runtime equivalence remains untested.',reference_version='n8n@2.46.4:261663556d98c9502663f6618edd8edd537e5688')
    ids=['BH-COMMAND','N-WORKFLOW','N-HOST','WH-CONTRACT']
    recipe['anchors']=[dict(id=aid,statement=statement,test=check,depth=depth,required=True,depends=deps,design_anchors=ids) for aid,statement,check,depth,deps in [
        ('direct','Route a directly matching numeric item','Execute positive equals and greater-than data paths',2,[]),
        ('branch-consequences','Preserve boundary, type, grouping, order and item-pairing consequences','Run full semantic table including negative, missing and short-circuit cases; retest direct path',5,['direct']),
        ('native-boundaries','Exercise the actual native Node-RED IF and Catch boundaries','Run a separate synthetic native runtime: true/false, empty branch and no partial output on strict error',5,['branch-consequences'])]]
    if reference:
        recipe['anchors'].append(dict(id='reference-consequences',statement='Match selected strict filter outcomes against actual pinned n8n library',test='Execute the pinned reference/candidate condition matrix; preserve the native routing and earlier cases',depth=5,required=True,depends=['native-boundaries'],design_anchors=ids))
    suite=root/'suite';suite.mkdir();(root/'observations').mkdir();scripts={
        'direct':"const assert=require('node:assert/strict'),m=require(process.argv[1]+'/conditions.cjs');const f=op=>({schema:'studio.if/1',combinator:'and',caseSensitive:true,continueOnFail:false,conditions:[{field:'score',type:'number',operation:op,value:10}]});assert.equal(m.partition(f('equals'),[{json:{score:10}}]).true.length,1);assert.equal(m.partition(f('gt'),[{json:{score:11}}]).true.length,1);",
    }
    cases=[]
    for aid in ('direct','branch-consequences','native-boundaries')+(('reference-consequences',) if reference else ()):
        if aid=='direct':args=[str(Path(node).resolve()),'-e',scripts['direct']]
        elif aid=='branch-consequences':args=[str(Path(node).resolve()),'--test','--test-reporter=tap']
        else:args=[str(Path(node).resolve())]
        suffix='conditions.test.cjs' if aid=='branch-consequences' else 'conditions-reference-probe.cjs' if aid=='reference-consequences' else 'conditions-runtime-probe.cjs'
        script='import os,subprocess,sys\nfrom pathlib import Path\n'
        script+='args='+repr(args)+'\n'
        script+=('args.append(sys.argv[1])\n' if aid=='direct' else 'args.append(str(Path(sys.argv[1])/'+repr(suffix)+'))\n')
        if aid=='reference-consequences':
            script+='import uuid\nargs.extend(['+repr(str(Path(reference).resolve()))+',str(Path('+repr(str(root/'observations'))+')/(uuid.uuid4().hex+".json"))])\n'
        script+='env=dict(os.environ,STUDIO_MODULES='+repr(str(Path(modules).resolve()))+')\n'
        script+='r=subprocess.run(args,env=env,capture_output=True,text=True,timeout=40)\nprint(r.stdout+r.stderr)\nassert r.returncode==0\n'
        (suite/(aid+'.py')).write_text(script,encoding='utf8')
        cases.append(dict(id=aid,obligations=[aid],script=aid+'.py',relationship=next(a['statement'] for a in recipe['anchors'] if a['id']==aid),requires=['node','native_node_red'] if aid=='native-boundaries' else ['node','pinned_reference_filter'] if aid=='reference-consequences' else ['node']))
    write_json(root/'recipe.json',recipe);write_json(suite/'suite.json',dict(schema=s.SUITE,recipe_sha256=digest(recipe),cases=cases))
    context=root/'context.json';write_json(context,dict(capabilities=dict(node=True,native_node_red=True,pinned_reference_filter=reference is not None),limits='Local synthetic native probes and optional pinned filter library; no full n8n instance, complete workflow parity or private isolation qualification'))
    workspace=root/'workspace';begin(workspace,recipe,resources);s.start(workspace,candidate,suite,context,reviewed=True)
    stages=[]
    def check(name):
        report=s.test(workspace,execute=True,reviewed=True,timeout=60)
        stages.append(dict(name=name,passed=report['all_passed'],cases=[dict(id=r['id'],outcome=r['outcome']) for r in report['results']],report=report['report_path']))
        return report
    assert check('direct')['all_passed']
    file=candidate/'conditions.cjs';good=file.read_bytes();bad=good.replace(b"if(c.operation==='gte')return left>=right;",b"if(c.operation==='gte')return left>right;")
    assert bad!=good;file.write_bytes(bad)
    assert not check('deliberate-boundary-regression')['all_passed']
    file.write_bytes(good);assert check('repair')['all_passed'];assert check('native')['all_passed']
    if reference:assert check('matched-reference')['all_passed']
    fresh=s.check(workspace)
    report=dict(stages=stages,verified=fresh['anchors'],acceptance='PENDING_BAKER',scope='Only the explicitly bounded IF slice; full Community command chase remains unfinished')
    write_json(root/'report.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--node',type=Path,required=True);p.add_argument('--modules',type=Path,required=True);p.add_argument('--reference',type=Path);a=p.parse_args()
    print(json.dumps(run(a.output,a.node,a.modules,a.reference),indent=2))
