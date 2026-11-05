'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {setImmediate:turn}=require('node:timers/promises');
const {mountExecutionRoutes,encodeRunData}=require('./editor-executions.cjs');

function setup({rejectCommit=false,stopAware=false,discard=false}={}){
 const handlers=new Map(),calls=[],frames=[];
 const saved={id:'w1',name:'Workflow',versionId:'saved',revision:'rev',
  nodes:[{name:'Manual',type:'n8n-nodes-base.manualTrigger'}],
  settings:{saveManualExecutions:!discard}};
 let result={id:'e1',workflowId:'w1',workflowVersionId:'saved',startedAt:'2026-11-05T12:00:00Z',
  status:'running',workflowData:saved,mode:'manual',data:null};
 mountExecutionRoutes((method,path,handler)=>handlers.set(method+' '+path,handler),{
  capture:ref=>ref==='origin'?frame=>frames.push(frame):null,
  projectId:'personal',
  runtime:{async admit(value){
   calls.push(['admit',value]);
   return async input=>{
    calls.push(['dispatch',input]);
    if(stopAware){
     if(!input.signal.aborted)await new Promise(resolve=>input.signal.addEventListener('abort',resolve,{once:true}));
     return {status:'canceled',data:{version:1,resultData:{runData:{}}}};
    }
    return {status:'success',data:{version:1,resultData:{lastNodeExecuted:'Manual',runData:{Manual:[{
     executionIndex:0,startTime:0,source:[],executionTime:1,executionStatus:'success',
     data:{main:[[{json:{value:'ephemeral'}}]]},
    }]}}}};
   };
  }},
  workflows:{async call(op,args){
   calls.push([op,args]);
   if(op==='get')return saved;
   if(op==='execution_start')return {...result,claim:'private-claim',
    selection:{trigger:args.trigger,destination:args.destination}};
   if(op==='execution_finish'){
    if(rejectCommit)throw Error('WORKFLOW_UNAVAILABLE');
    result={...result,status:args.status,data:args.result,stoppedAt:'2026-11-05T12:00:01Z'};
    return discard?{...result,discarded:true}:result;
   }
   if(op==='execution_stop_state')return result;
   if(op==='execution_get'){
    if(discard&&result.status!=='running')throw Error("KeyError: 'Execution not found'");
    return result;
   }
   if(op==='execution_page')return discard?{count:0,data:[],next_cursor:null}:{count:1,data:[result],next_cursor:null};
   if(op==='execution_versions')return [{versionId:'saved',name:null,createdAt:result.startedAt}];
   throw Error('unexpected call');
  }},
 });
 const run=(body,ref='origin')=>handlers.get('post /rest/workflows/:id/run')({
  headers:{'push-ref':ref},params:{id:'w1'},body,
 });
 const detail=()=>handlers.get('get /rest/executions/:id')({params:{id:'e1'},query:{}});
 const listing=(filter={workflowId:'w1'},cursor)=>handlers.get('get /rest/executions')({
  query:{filter:JSON.stringify(filter),cursor},
 });
 const versions=()=>handlers.get('get /rest/executions/versions/:id')({params:{id:'w1'}});
 const stop=body=>handlers.get('post /rest/executions/:id/stop')({params:{id:'e1'},body});
 return {run,detail,listing,versions,stop,calls,frames};
}

test('native run transport binds selected saved version and publishes only a committed finish',async()=>{
 const server=setup();
 const request={workflowId:'w1',triggerToStartFrom:{name:'Manual'},startNodes:[]};
 assert.deepEqual(await server.run(request),{data:{executionId:'e1'}});
 assert.deepEqual(server.frames,[]);
 await turn();
 assert.deepEqual(server.frames.map(frame=>frame.type),['executionStarted','executionFinished']);
 assert.deepEqual(server.calls.map(([op])=>op),['get','admit','execution_start','dispatch','execution_finish']);
 assert.equal(server.calls[2][1].version_id,'saved');
 assert.equal(server.calls[4][1].claim,'private-claim');
 const detail=(await server.detail()).data;
 assert.equal(detail.workflowVersionId,'saved');
 assert.equal(detail.status,'success');
 assert.equal(typeof detail.data,'string');
 assert.ok(!JSON.stringify(detail).includes('private-claim'));
 const page=(await server.listing()).data;
 assert.equal(page.count,1);
 assert.equal(page.results[0].id,'e1');
 assert.ok(!('data' in page.results[0]));
});

test('unsupported or detached requests never reserve work and failed commit never sends finish',async()=>{
 const server=setup({rejectCommit:true});
 const request={triggerToStartFrom:{name:'Manual'}};
 await assert.rejects(server.run(request,'unrelated'),/editor connection/);
 await assert.rejects(server.run({...request,workflowData:{nodes:[]}}),/Unsupported execution/);
 assert.ok(!server.calls.some(([op])=>op==='execution_start'));
 await server.run(request);
 await turn();
 assert.deepEqual(server.frames.map(frame=>frame.type),['executionStarted']);
 assert.equal((await server.detail()).data.status,'running');
});

test('a history-disabled result releases node output only through the initiating push after commit',async()=>{
 const request={triggerToStartFrom:{name:'Manual'}};
 const server=setup({discard:true});
 await server.run(request);
 await turn();
 assert.deepEqual(server.frames.map(frame=>frame.type),[
  'executionStarted','nodeExecuteBefore','nodeExecuteAfter','nodeExecuteAfterData','executionFinished',
 ]);
 assert.deepEqual(server.frames[3].data.itemCountByConnectionType,{main:[1]});
 assert.deepEqual(server.frames[3].data.data.data.main,[[{json:{value:'ephemeral'}}]]);
 assert.deepEqual(await server.detail(),{});
 assert.equal((await server.listing()).data.count,0);
 const failed=setup({discard:true,rejectCommit:true});
 await failed.run(request);
 await turn();
 assert.deepEqual(failed.frames.map(frame=>frame.type),['executionStarted']);
});

test('Stop waits for the committed cancellation and repeated Stop reads the same record',async()=>{
 const server=setup({stopAware:true});
 await server.run({triggerToStartFrom:{name:'Manual'}});
 await turn();
 await assert.rejects(server.stop({state:'canceled'}),/Unsupported execution/);
 const first=await server.stop({});
 assert.deepEqual(first.data,{status:'canceled',mode:'manual',finished:false,
  startedAt:'2026-11-05T12:00:00Z',stoppedAt:'2026-11-05T12:00:01Z'});
 assert.deepEqual(await server.stop(),first);
 assert.equal(server.calls.filter(([op])=>op==='execution_finish').length,1);
 assert.equal(server.frames.at(-1).data.status,'canceled');
});

test('Stop preserves a run that finishes first and a failed cancellation commit stays unresolved',async()=>{
 const intent={triggerToStartFrom:{name:'Manual'}};
 const completed=setup();
 await completed.run(intent);
 await assert.rejects(completed.stop(),/already finished/);
 assert.equal((await completed.detail()).data.status,'success');
 const unresolved=setup({rejectCommit:true,stopAware:true});
 await unresolved.run(intent);
 await assert.rejects(unresolved.stop(),/stop requires review/);
 assert.equal((await unresolved.detail()).data.status,'running');
 assert.deepEqual(unresolved.frames.map(frame=>frame.type),['executionStarted']);
});

test('execution history binds personal project, status, dates and saved version to the stored query',async()=>{
 const server=setup();
 const query={workflowId:'w1',status:['canceled'],startedAfter:'2026-01-01T00:00:00Z',workflowVersionId:'saved'};
 await assert.rejects(server.listing({...query,projectId:'unavailable'}),/execution project/);
 const page=(await server.listing({...query,projectId:'personal'},'cursor')).data;
 assert.deepEqual(server.calls.at(-1),['execution_page',{query,cursor:'cursor',limit:50}]);
 assert.deepEqual(page.results[0].scopes,['execution:list','execution:read','workflow:read','workflow:execute']);
 assert.equal(page.nextCursor,null);
 assert.equal((await server.versions()).data[0].versionId,'saved');
});

test('run-data encoding retains numeric text and nested item shape for Flatted consumers',()=>{
 const item={json:{text:'0',n:1}};
 const table=JSON.parse(encodeRunData({items:[item,item]}));
 const items=table[Number(table[0].items)];
 assert.equal(items[0],items[1]);
 const json=table[Number(table[Number(items[0])].json)];
 assert.equal(table[Number(json.text)],'0');
 assert.equal(json.n,1);
});
