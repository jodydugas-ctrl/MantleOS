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

function pushTransientNodes(push,executionId,runData){
 const tasks=Object.entries(runData??{}).flatMap(([name,runs])=>runs.map(run=>({name,run})));
 tasks.sort((left,right)=>left.run.executionIndex-right.run.executionIndex);
 let sequenceNumber=0;
 for(const {name:nodeName,run} of tasks){
  const {data:output,...task}=run;
  const {executionIndex,source,startTime}=task;
  const fields={executionId,nodeName};
  const itemCountByConnectionType=output?.main?{main:output.main.map(items=>items?.length??0)}:{};
  const hints=[];
  push({type:'nodeExecuteBefore',data:{...fields,sequenceNumber:sequenceNumber++,
   data:{executionIndex,hints,source,startTime}}});
  push({type:'nodeExecuteAfter',data:{...fields,sequenceNumber:sequenceNumber++,itemCountByConnectionType,
   data:{...task,hints}}});
  push({type:'nodeExecuteAfterData',data:{...fields,itemCountByConnectionType,data:{...run,hints}}});
 }
}

function mountExecutionRoutes(route,{workflows,runtime,capture,projectId}){
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
   observation=await operation({id:executionId,claim,workflow:workflowData,selection:started.selection,signal});
   if(!observation||!['success','error','canceled','needs_review'].includes(observation.status)||!observation.data||
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
     committed.workflowVersionId!==started.workflowVersionId||committed.status!==observation.status||
     (committed.discarded===true)!==(workflowData.settings?.saveManualExecutions===false))
   throw Error('UNVERIFIED_EXECUTION_COMMIT');
  if(committed.discarded)pushTransientNodes(push,executionId,committed.data.resultData?.runData);
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
  const run=await workflows.call('execution_stop_state',{run_id:req.params.id});
  if(run.status!=='canceled'){
   if(run.status==='running'||run.status==='needs_review')throw Error('Conflict: execution stop requires review');
   throw Error('Conflict: execution already finished');
  }
  return {data:{mode:run.mode,startedAt:run.startedAt,stoppedAt:run.stoppedAt,finished:false,status:'canceled'}};
 });
 route('get','/rest/executions/:id',async req=>{
  try{
   const run=await workflows.call('execution_get',{run_id:req.params.id});
   return {data:presentation(run,req.query.includeData!=='false')};
  }catch(error){
   if(error.message==='KeyError: \'Execution not found\'')return {};
   throw error;
  }
 });
 route('get','/rest/executions/versions/:id',async req=>({
  data:await workflows.call('execution_versions',{workflow_id:req.params.id}),
 }));
 route('get','/rest/executions',async req=>{
  const filter=req.query.filter?JSON.parse(req.query.filter):{};
  if(!filter||typeof filter!=='object'||Array.isArray(filter))throw Error('Unsupported execution: history filter');
  const {projectId:requestedProject,...query}=filter;
  if(requestedProject!==undefined&&requestedProject!==projectId)throw Error('PermissionError: execution project');
  const limit=Number(req.query.limit??50),cursor=req.query.cursor??null;
  const page=await workflows.call('execution_page',{query,cursor,limit});
  const scopes=['execution:list','execution:read','workflow:read','workflow:execute'];
  return {data:{results:page.data.map(row=>({...presentation(row,false),scopes})),
   nextCursor:page.next_cursor,count:page.count,estimated:false,concurrentExecutionsCount:-1}};
 });
 return Object.freeze({async close(){closing=true;await Promise.allSettled(pending);}});
}

module.exports={mountExecutionRoutes,encodeRunData};
