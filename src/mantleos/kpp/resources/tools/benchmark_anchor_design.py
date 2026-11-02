import argparse,importlib.util,json,statistics,time,tempfile,uuid
from pathlib import Path
from mantleos import journal,specimens
parser=argparse.ArgumentParser(description='Synthetic before/after Journal measurement; baseline Python executes with host privileges.')
parser.add_argument('--baseline-journal',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
if args.output.exists():parser.error('Output already exists')
args.output.parent.mkdir(parents=True,exist_ok=True)
base=args.output.parent
spec=importlib.util.spec_from_file_location('mantleos.journal_before_design',args.baseline_journal.resolve())
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
old.bootstrap_metadata=journal.bootstrap_metadata
def timed(fn):
 start=time.perf_counter();v=fn();return v,(time.perf_counter()-start)*1000
def stats(v):return {'median_ms':statistics.median(v),'p95_ms':sorted(v)[(95*len(v)+99)//100-1]}
results=[]
with tempfile.TemporaryDirectory() as td:
 root=Path(td);body=root/'body';specimens.fresh(body,name='Synthetic Finch')
 for cold in [False,True]:
  for count in [0,100,1000]:
   for label,module in [('baseline',old),('design',journal)]:
    file=root/(uuid.uuid4().hex+'.engram');module.from_body(body,file)
    with module.Journal(file) as j:
     if cold:
      raw=b'C'*(20*1024*1024);j.db.execute('INSERT INTO objects VALUES (?,?)',(module.sha(raw),raw))
     for n in range(count):j.append_record('note','synthetic',{'text':str(n)+' synthetic history'},expected_head=j.head())
    j,startup=timed(lambda:module.Journal(file));turns=[];opens=[];commits=[];sizes=[]
    try:
     for n in range(20):
      rid=str(n);f,op=timed(lambda:j.open('Remember amber',request_id=rid,model_id='SYNTHETIC_NO_MODEL'))
      _,commit=timed(lambda:j.submit(rid,{'kind':'reply','reply':'Amber remembered.','observation_sha256':None},broker=lambda a,n:True))
      opens.append(op);commits.append(commit);turns.append(op+commit);sizes.append(len(module.canon(f).encode()))
     _,export=timed(lambda:j.export(root/(uuid.uuid4().hex+'.engram')))
     results.append({'variant':label,'records':count,'cold_bytes':20*1024*1024 if cold else 0,'samples':20,'warm':stats(turns),'open':stats(opens),'commit':stats(commits),'frame_bytes':statistics.median(sizes),'cold_start_ms':startup,'export_ms':export,'model_calls':0})
     (args.output).write_text(json.dumps(results,indent=2))
     print(results[-1],flush=True)
    finally:j.close()
