"""Manual current-host qualification. Does not invoke a model API.

Prepare a frame, have the current host generate a packet, submit that exact file.
Receipts attest execution/bindings, not the identity or private reasoning of a model.
Use private output directories: frames can contain personal PRIMER and history.
"""
import argparse,hashlib,json,sys,time
from pathlib import Path

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('operation',choices=['open','advance','commit']);p.add_argument('--kind',choices=['journal','legacy'],default='journal')
 p.add_argument('--file',required=True,help='Journal file or verified legacy Body directory')
 p.add_argument('--library-path',help='Explicit reviewed legacy runtime library; used only with --reviewed-runtime')
 p.add_argument('--reviewed-runtime',action='store_true');p.add_argument('--workspace',required=True)
 p.add_argument('--request-id',required=True);p.add_argument('--model-id',default='CURRENT_HOST (declared)');p.add_argument('--user');p.add_argument('--packet')
 p.add_argument('--allow-read',action='store_true');p.add_argument('--allow-release',action='store_true')
 a=p.parse_args(argv);out=Path(a.workspace).resolve();out.mkdir(parents=True,exist_ok=True)
 # File names do not contain caller-selected request ids.
 key=hashlib.sha256(a.request_id.encode()).hexdigest();state=out/(key+'.preparation.json')
 if a.library_path:
  if a.kind!='legacy' or not a.reviewed_runtime:p.error('Explicit legacy source execution requires --kind legacy --reviewed-runtime')
  sys.path.insert(0,str(Path(a.library_path).resolve()))
 started=time.perf_counter();wall=time.time()
 def broker(authority,name):
  if authority=='release':return a.allow_release
  return a.allow_read and authority in {'read','effect.execute'} and name in {'body.status','engram.query'}
 if a.kind=='journal':
  from mantleos.journal import Journal
  with Journal(a.file) as j:
   if a.operation=='open':value=j.open(a.user,request_id=a.request_id,model_id=a.model_id)
   elif a.operation=='commit':value=j.submit(a.request_id,json.loads(Path(a.packet).read_text('utf8')) if a.packet else None,broker=broker)
   else:p.error('Journal action requests are submitted through commit; the result is a second frame')
 else:
  from mantleos.hosted import HostedBridge
  from mantleos.organs import system_registry
  root=Path(a.file);registry=system_registry(root).capability_registry()
  bridge=HostedBridge(root,model_id=a.model_id,registry=registry,broker=broker,model_action_capabilities={'body.status'})
  if a.operation=='open':value=bridge.open(a.user,request_id=a.request_id)
  elif a.operation=='advance':value=bridge.advance(json.loads(state.read_text('utf8')),json.loads(Path(a.packet).read_text('utf8')))
  else:value=bridge.commit(json.loads(state.read_text('utf8')),json.loads(Path(a.packet).read_text('utf8')) if a.packet else None)
 elapsed=time.perf_counter()-started
 encoded=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode()
 destination=out/(key+'-'+a.operation+'-'+str(time.time_ns())+'.json');destination.write_bytes(encoded)
 if a.operation in {'open','advance'}:state.write_bytes(encoded)
 receipt={'kind':a.kind,'operation':a.operation,'request_id':a.request_id,'model_id':a.model_id,
          'packet_source':'CALLER_SUPPLIED; NO_INTERNAL_MODEL_API','started_utc_epoch':wall,
          'application_seconds_including_mount':elapsed,'output':str(destination),'sha256':hashlib.sha256(encoded).hexdigest(),
          'model_generation_seconds':'NOT_MEASURED','host_scheduling_seconds':'NOT_MEASURED',
          'commit_head':value.get('commit_head'),'replayed':value.get('replayed')}
 with (out/'receipts.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(receipt)+'\n')
 print(json.dumps(receipt,indent=2))
 return 0
if __name__=='__main__':raise SystemExit(main())
