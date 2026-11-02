"""Matched synthetic timing: no model invocation. Outputs remain private."""
import argparse,json,os,statistics,tempfile,time,uuid
from pathlib import Path
from mantleos import engram,journal,lifecycle,specimens
from mantleos.hosted import HostedBridge,digest

def run(output,samples=20):
 root=Path(output).resolve();root.mkdir(parents=True,exist_ok=False);tempfile.tempdir=str(root)
 results=[]
 for count in (0,100,1000):
  for cold in (0,20*1024*1024):
   case=root/f'{count}-{cold}';case.mkdir();body=case/'body';specimens.fresh(body,name='Synthetic Benchmark')
   rows=[];prev=engram.ZERO
   for seq in range(1,count+1):
    r={'schema':'mantle.engram-record/1','seq':seq,'id':uuid.uuid4().hex,'type':'turn','source':'synthetic',
       'body':{'user':f'Synthetic reference {seq}','reply':f'Recorded sample {seq}.'},'prev_sha256':prev}
    r['sha256']=engram.hash_record(r);prev=r['sha256'];rows.append(r)
   (body/'ENGRAM.jsonl').write_text(''.join(engram.canonical(r)+'\n' for r in rows),encoding='utf8')
   if cold:(body/'COLD.bin').write_bytes(os.urandom(cold))
   lifecycle.finalize(body)
   carrier=case/'journal.engram';journal.from_body(body,carrier)
   start=time.perf_counter();j=journal.Journal(carrier);cold_j=time.perf_counter()-start
   start=time.perf_counter();b=HostedBridge(body,model_id='SCRIPTED_FIXTURE',broker=lambda a,n:True);cold_b=time.perf_counter()-start
   times={'baseline':[],'journal':[]};commits={'baseline':[],'journal':[]};frames={'baseline':[],'journal':[]}
   for sample in range(samples):
    for mode in ('baseline','journal') if sample%2==0 else ('journal','baseline'):
     rid=f'benchmark-{mode}-{sample}';start=time.perf_counter()
     if mode=='baseline':
      p=b.open('Remember the synthetic observation: the specimen is ready.',request_id=rid)
      o={'schema':'mantle.orientation/1','mode':'TARGETED','percepts':[],'unknowns':[],'goals':[],'options':[],'predictions':[],'action_request':None}
      advanced=b.advance(p,o)
      frames[mode].append(len(engram.canonical(p['frame']).encode())+len(engram.canonical(advanced['frame']).encode()))
      reply={'schema':'mantle.response-proposal/1','orientation_sha256':digest(o),'reply':'The synthetic observation has been recorded.','candidates':[],
             'cognition':{'schema':'mantle.respond-cognition/1','observation_sha256':None,'delta':[],'revision':[],'intent':{'kind':'synthetic-benchmark'}}}
      cs=time.perf_counter();b.commit(advanced,reply)
     else:
      p=j.open('Remember the synthetic observation: the specimen is ready.',request_id=rid,model_id='SCRIPTED_FIXTURE');frames[mode].append(len(engram.canonical(p).encode()))
      cs=time.perf_counter();j.submit(rid,{'kind':'reply','reply':'The synthetic observation has been recorded.','observation_sha256':None},broker=lambda a,n:True)
     end=time.perf_counter();commits[mode].append(end-cs);times[mode].append(end-start)
    print(json.dumps({'progress':[count,cold,sample+1]}),flush=True)
   exp=time.perf_counter();j.export(case/'saved.engram');export=time.perf_counter()-exp;j.close()
   summary={'records':count,'cold_bytes':cold,'samples':samples,'cold_start_seconds':{'baseline':cold_b,'journal':cold_j},'journal_export_seconds':export,'live_model_calls':0}
   for mode in times:
    ordered=sorted(times[mode]);summary[mode]={'median_seconds':statistics.median(ordered),'p95_seconds':ordered[max(0,(95*len(ordered)+99)//100-1)],
     'commit_median_seconds':statistics.median(commits[mode]),'frame_bytes_median':statistics.median(frames[mode]),'required_model_generations':2 if mode=='baseline' else 1,'samples_seconds':times[mode]}
   summary['median_reduction']=1-summary['journal']['median_seconds']/summary['baseline']['median_seconds'];results.append(summary)
   (root/'benchmark.json').write_text(json.dumps({'synthetic':True,'cases':results},indent=2),encoding='utf8')
 return results
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--samples',type=int,default=20);a=p.parse_args();run(a.output,a.samples)
