/* n8n 2.46.4 editor transport over Body-authorized, stored workflow execution. */
'use strict';
const {randomUUID}=require('node:crypto');

function encodeRunData(value){
 const entries=[value],seen=new Map([[value,'0']]),encoded=[];
 for(const item of entries){
  let root=true;
  encoded.push(JSON.stringify(item,(_key,part)=>{
   if(root){root=false;return part;}
   if(typeof part!=='string'&&!(part&&typeof part==='object'))return part;
   if(!seen.has(part)){seen.set(part,String(entries.length));entries.push(part);}
   return seen.get(part);
  }));
 }
 return '['+encoded.join(',')+']';
}

function selection(body,workflow){
 if(!body||typeof body!=='object'||Array.isArray(body)||
    Object.keys(body).some(key=>!['workflowId','triggerToStartFrom','destinationNode','startNodes'].includes(key)))
  throw Error('Unsupported execution: selection');
 if(body.workflowId!==undefined&&body.workflowId!==workflow.id)throw Error('Conflict: execution workflow');
 if(body.startNodes!==undefined&&(!Array.isArray(body.startNodes)||body.startNodes.length))
  throw Error('Unsupported execution: precomputed start nodes');
 const source=body.triggerToStartFrom,destination=body.destinationNode;
 if(source!==undefined&&(!source||typeof source!=='object'||Object.keys(source).join(',')!=='name'||typeof source.name!=='string'))
  throw Error('Unsupported execution: trigger data');
 if(destination!==undefined&&(!destination||typeof destination!=='object'||
    Object.keys(destination).sort().join(',')!=='mode,nodeName'||destination.mode!=='inclusive'||typeof destination.nodeName!=='string'))
  throw Error('Unsupported execution: destination');
 const triggers=workflow.nodes.filter(node=>node.type==='n8n-nodes-base.manualTrigger'&&!node.disabled);
 const trigger=source?.name??(destination&&triggers.length===1?triggers[0].name:null);
 if(!trigger||!triggers.some(node=>node.name===trigger))throw Error('Unsupported execution: manual trigger');
 return {trigger,destination:destination?.nodeName??null};
}

function presentation(run,includeData){
 const status=run.status==='needs_review'?'crashed':run.status;
 const {data,workflowData,...base}=run;
 return {...base,status,finished:status==='success',createdAt:run.startedAt,retryOf:null,retrySuccessId:null,
  waitTill:null,deletedAt:null,storedAt:'db',usedPrivateCredentials:false,
  ...(run.status==='needs_review'?{executionReviewRequired:true}:{}),
  ...(includeData?{workflowData:{...workflowData,active:false},data:data===null?null:encodeRunData(data)}:{})};
}

function mountExecutionRoutes(route,{workflows,runtime,capture}){
 if(typeof runtime?.admit!=='function'||typeof capture!=='function')throw Error('TRUSTED_EXECUTION_HOST_REQUIRED');
 const pending=new Set();
 const active=new Map();
 let closing=false;
 async function finish(started,operation,push,signal){
  const {id:executionId,workflowId,workflowData,startedAt,claim}=started;
  push({type:'executionStarted',data:{executionId,workflowId,workflowName:workflowData.name,
   mode:'manual',startedAt,flattedRunData:'[{}]'}});
  let observation;
  try{
   observation=await operation({id:executionId,workflow:workflowData,selection:started.selection,signal});
   if(!observation||!['success','error','canceled'].includes(observation.status)||!observation.data||
      typeof observation.data!=='object'||Array.isArray(observation.data))throw Error('Unverified observation');
  }catch{
   observation={status:'needs_review',data:{version:1,resultData:{runData:{},error:{
    name:'ExecutionReviewRequired',message:'The runtime outcome requires operator review.',
   }}}};
  }
  // A failed write leaves the run pending review and emits no terminal frame.
  const committed=await workflows.call('execution_finish',{run_id:executionId,claim,
   status:observation.status,result:observation.data});
  if(committed.id!==executionId||committed.workflowId!==workflowId||
     committed.workflowVersionId!==started.workflowVersionId||committed.status!==observation.status)
   throw Error('UNVERIFIED_EXECUTION_COMMIT');
  push({type:'executionFinished',data:{executionId,workflowId,status:presentation(committed,false).status}});
 }
 route('post','/rest/workflows/:id/run',async req=>{
  if(closing)throw Error('PermissionError: execution intake stopped');
  let release,dispatched=false;
  const lifecycle=new Promise(resolve=>{release=resolve;});
  const done=()=>{pending.delete(lifecycle);release();};
  pending.add(lifecycle);
  try{
   const push=capture(req.headers['push-ref']);
   if(!push)throw Error('Conflict: execution editor connection');
   const saved=await workflows.call('get',{id:req.params.id});
   const selected=selection(req.body,saved);
   const operation=await runtime.admit({workflow:saved,selection:selected});
   if(typeof operation!=='function')throw Error('Unsupported execution: runtime capability');
   if(closing)throw Error('PermissionError: execution intake stopped');
   const run=await workflows.call('execution_start',{request_id:'run-'+randomUUID(),
    workflow_id:saved.id,version_id:saved.versionId,revision:saved.revision,...selected});
   if(!run.claim)throw Error('Conflict: execution already dispatched');
   const controller=new AbortController();
   active.set(run.id,{controller,lifecycle});
   setImmediate(()=>finish(run,operation,push,controller.signal).catch(()=>{}).finally(()=>{
    active.delete(run.id);done();
   }));
   dispatched=true;
   return {data:{executionId:run.id}};
  }finally{if(!dispatched)done();}
 });
 route('post','/rest/executions/:id/stop',async req=>{
  if(req.body!==undefined&&(!req.body||Array.isArray(req.body)||
     typeof req.body!=='object'||Object.keys(req.body).length))throw Error('Unsupported execution: stop payload');
  const live=active.get(req.params.id);
  if(live){live.controller.abort();await live.lifecycle;}
  const run=await workflows.call('execution_get',{run_id:req.params.id});
  if(run.status!=='canceled'){
   if(run.status==='running'||run.status==='needs_review')throw Error('Conflict: execution stop requires review');
   throw Error('Conflict: execution already finished');
  }
  return {data:{mode:run.mode,startedAt:run.startedAt,stoppedAt:run.stoppedAt,finished:false,status:'canceled'}};
 });
 route('get','/rest/executions/:id',async req=>{
  const run=await workflows.call('execution_get',{run_id:req.params.id});
  return {data:presentation(run,req.query.includeData!=='false')};
 });
 route('get','/rest/executions',async req=>{
  const filter=req.query.filter?JSON.parse(req.query.filter):{};
  if(!filter||typeof filter!=='object'||Array.isArray(filter)||
     Object.keys(filter).some(key=>key!=='workflowId'))throw Error('Unsupported execution: history filter');
  const limit=Number(req.query.limit??50),cursor=req.query.cursor??'0';
  if(typeof cursor!=='string'||!/^(0|[1-9]\d{0,7})$/.test(cursor))throw Error('Invalid execution cursor');
  const offset=Number(cursor);
  const page=await workflows.call('execution_list',{workflow_id:filter.workflowId??null,offset,limit});
  const next=offset+page.data.length;
  return {data:{results:page.data.map(row=>presentation(row,false)),
   nextCursor:next<page.count?String(next):null,count:page.count,estimated:false,concurrentExecutionsCount:-1}};
 });
 return Object.freeze({async close(){closing=true;await Promise.allSettled(pending);}});
}

module.exports={mountExecutionRoutes,encodeRunData};
