"""Synthetic eight-limb Studio, durable bridge and local warm-turn benchmark.

No Node-RED or live model is needed. All semantic proposals are labeled fixtures.
Use --output NEW_DIRECTORY; generated Journals remain local test state.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import json
from pathlib import Path
import statistics
import time

from mantleos import studio, studio_demo, studio_project


def measured(fn):
    t=time.perf_counter();value=fn();return value,(time.perf_counter()-t)*1000


def distribution(values):
    return {'samples':len(values),'median_ms':statistics.median(values),'p95_ms':sorted(values)[max(0,int(len(values)*.95)-1)]}


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    founding=output/'synthetic-founding.txt';founding.write_text('Synthetic Studio qualification persona. Preserve source, history and independent host authority.\n',encoding='utf8')
    nest=output/'nest';_,birth_ms=measured(lambda:studio.initialize(nest,founding))
    project=studio_demo.project();studio.project_set(nest,project,None);studio.phase(nest,True)
    startup,cold_ms=measured(lambda:studio.boot(nest))
    studio.event(nest,'host.started',{'host':'synthetic specimen; Node-RED not running'},'synthetic-host')
    for role in studio.ROLES:
        value={'operation':'remember','text':'Synthetic marker amber'} if role in ('memory','communications') else {'operation':'validate','project':project} if role in ('design','contracts','verification') else {'operation':'inspect'} if role=='body-mapping' else {'operation':'diagnose'} if role=='repair' else {'operation':'plan'}
        studio.intention(nest,role,value,'task-'+role)
    started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as pool:
        results=[f.result() for f in [pool.submit(studio.work,nest) for _ in studio.ROLES]]
    worker_ms=(time.perf_counter()-started)*1000
    assert all(r['status']=='RESULT' for r in results)
    identities=[m['identity'] for m in studio.status(nest)['limbs']];assert len(set(identities))==8
    studio.intention(nest,'memory',{'operation':'remember','text':'Explicit pending-work projection'},'pending-projection')
    handoff=[];commits=[];replays=[];sizes=[]
    for i in range(20):
        rid='fixture-'+str(i)
        frame,ms=measured(lambda:studio.conversation(nest,'Synthetic warm encounter '+str(i),rid,'SYNTHETIC_FIXTURE_NO_MODEL'))
        assert 'Synthetic Studio qualification persona' in frame['frame']['payload']['primer']['content']
        memory=next(o for o in frame['limb_observations'] if o['role']=='memory')
        assert memory['pending']['READY']==1 and memory['pending_requests'][0]['id']=='pending-projection'
        handoff.append(ms);sizes.append(len(json.dumps(frame,ensure_ascii=False).encode()))
        proposal={'kind':'reply','reply':'Synthetic committed reply '+str(i),'observation_sha256':None}
        reply,ms=measured(lambda:studio.submit(nest,rid,proposal));commits.append(ms)
        replay,ms=measured(lambda:studio.committed_result(nest,rid));replays.append(ms)
        assert reply['reply']==replay['reply']==proposal['reply']
    frame=studio.conversation(nest,'Synthetic checked status','checked','SYNTHETIC_FIXTURE_NO_MODEL')
    observation=studio.submit(nest,'checked',{'kind':'action','capability':'body.status','arguments':{}})
    studio.submit(nest,'checked',{'kind':'reply','reply':'Synthetic checked response','observation_sha256':observation['frame']['payload']['observation_sha256']})
    exported=output/'Anchor-Studio-Demo.anchorstudio';studio_project.save(project,exported);assert studio_project.load(exported)==project
    report={'schema':'anchor-studio.specimen-report/1','model_calls':0,'semantic_packets':'SCRIPTED_FIXTURES_NOT_LIVE_LLM_EVIDENCE',
        'birth_ms':birth_ms,'cold_start_ms':cold_ms,'startup':startup,'worker_execution_ms':worker_ms,
        'members':8,'workers':2,'distinct_identities':len(set(identities)),
        'handoff':distribution(handoff),'commit':distribution(commits),'exact_replay':distribution(replays),
        'frame_bytes':{'minimum':min(sizes),'maximum':max(sizes)},'project_roundtrip':'PASS','checked_observation':'PASS',
        'acceptance':'PENDING_BAKER','limits':'Synthetic local Python; no actual Node-RED, provider timing, isolation or hidden-reasoning qualification.'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    for key,session in list(studio._sessions.items()):session.close();del studio._sessions[key]
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    print(json.dumps(run(p.parse_args().output),indent=2))
