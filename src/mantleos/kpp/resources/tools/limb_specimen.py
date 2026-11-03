"""Real optional limb specimen: zero, one, two, or eight synthetic Engrams."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
import time

from mantleos import journal, specimens
from mantleos.limbs import LimbSet, remember


def run_worker(root):
    return LimbSet(root).run_one({'remember':remember},broker=lambda limb,op:op=='remember')


def run(output,count,workers):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    members=[]
    for index in range(count):
        body=output/('body-'+str(index));specimens.fresh(body,name='Synthetic limb '+str(index))
        carrier=output/('limb-'+str(index)+'.engram');journal.from_body(body,carrier)
        members.append({'id':'L'+str(index),'journal':str(carrier),'grants':['remember']})
    runtime=LimbSet.create(output/'registry',members,worker_limit=workers,approved=True,handlers={'remember':remember})
    for index in range(count):runtime.submit('L'+str(index),'remember',{'index':index,'marker':'synthetic'},request_id='task-'+str(index))
    start=time.perf_counter()
    if count:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results=[f.result() for f in [pool.submit(run_worker,output/'registry') for _ in range(count)]]
        assert all(r['status']=='RESULT' for r in results)
        verified=runtime.results(broker=lambda limb,op:True)
        assert len(verified)==count and len({m['identity'] for m in runtime.status()['members']})==count
    else:verified=[]
    report={'schema':'mantle.limb-specimen-report/1','count':count,'workers':workers,
            'execution_ms':(time.perf_counter()-start)*1000,'model_calls':0,'python':sys.version,
            'verified_results':verified,'status':runtime.status(),'acceptance':'PENDING_BAKER',
            'limits':'Synthetic local Python processes; no OS isolation or general external-effect qualification.'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limbs',type=int,choices=(0,1,2,8),default=2);parser.add_argument('--workers',type=int,default=1)
    args=parser.parse_args()
    if not args.limbs:args.workers=0
    if args.limbs and not 1<=args.workers<=8:parser.error('Use 1..8 workers')
    print(json.dumps(run(args.output,args.limbs,args.workers),indent=2))
