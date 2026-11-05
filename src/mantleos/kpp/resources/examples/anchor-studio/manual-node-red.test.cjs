'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const os=require('node:os');
const {setTimeout:delay}=require('node:timers/promises');
const {createManualRuntime}=require('./manual-node-red.cjs');

function workflow(value=42){
 const filter={options:{caseSensitive:true,leftValue:'',typeValidation:'strict',version:4},
  conditions:[{id:'numeric',leftValue:value,rightValue:50,operator:{type:'number',operation:'gte'}}],combinator:'and'};
 const conditional=name=>({name,type:'n8n-nodes-base.if',typeVersion:2.4,parameters:{conditions:filter,options:{}}});
 return {id:'w1',versionId:'saved',nodes:[
  {name:'Manual',type:'n8n-nodes-base.manualTrigger',typeVersion:1,parameters:{}},
  conditional('If'),conditional('False continuation'),
 ],connections:{
  Manual:{main:[[{node:'If',type:'main',index:0}]]},
  If:{main:[[],[{node:'False continuation',type:'main',index:0}]]},
 },pinData:{},settings:{executionOrder:'v1',binaryMode:'separate'}};
}
const full={trigger:'Manual',destination:null};

function waitWorkflow(amount=1){
 const saved=workflow();
 saved.nodes[1]={name:'Wait',type:'n8n-nodes-base.wait',typeVersion:1.1,
  parameters:{resume:'timeInterval',amount,unit:'seconds'}};
 saved.nodes.pop();
 delete saved.connections.If;
 saved.connections.Manual.main[0][0].node='Wait';
 return saved;
}

test('manual admission refuses unknown node types, arbitrary expressions, and unsafe connections',async()=>{
 const runner=createManualRuntime({checkActive:async()=>{}});
 await assert.rejects(runner.admit({workflow:workflow('={{ process.env.KEY }}'),selection:full}),/Unsupported execution: expression/);
 const credential=workflow();credential.nodes[1].credentials={test:{id:'example'}};
 await assert.rejects(runner.admit({workflow:credential,selection:full}),/node configuration/);
 const code=workflow();code.nodes[1].type='n8n-nodes-base.code';
 await assert.rejects(runner.admit({workflow:code,selection:full}),/node type/);
 const cycle=workflow();cycle.connections['False continuation']={main:[[{node:'If',type:'main',index:0}]]};
 await assert.rejects(runner.admit({workflow:cycle,selection:full}),/connection or fan-in/);
 const disabled=createManualRuntime({checkActive:async()=>{throw Error('STALE_CONFIGURATION');}});
 await assert.rejects(disabled.admit({workflow:workflow(),selection:full}),/STALE_CONFIGURATION/);
});

test('Wait and execution timeout require the reviewed bounded settings',async()=>{
 const runner=createManualRuntime({checkActive:async()=>{}});
 for(const amount of [0,21,1.5,'1']){
  await assert.rejects(runner.admit({workflow:waitWorkflow(amount),selection:full}),/Wait profile/);
 }
 for(const value of ['1',21,-2,1.5,null]){
  const saved=waitWorkflow();
  saved.settings.executionTimeout=value;
  await assert.rejects(runner.admit({workflow:saved,selection:full}),/workflow settings/);
 }
 const saved=waitWorkflow();
 saved.settings.saveManualExecutions=false;
 await assert.rejects(runner.admit({workflow:saved,selection:full}),/workflow settings/);
 saved.settings.saveManualExecutions='DEFAULT';
 assert.equal(typeof await runner.admit({workflow:saved,selection:full}),'function');
});

test('Node-RED completes a bounded Wait and reports a timed-out manual run as canceled',
 {skip:!process.env.STUDIO_MODULES?'Owner-provisioned Node-RED runtime absent':false,timeout:90000},async()=>{
 const nodeRed=require.resolve(path.join(process.env.STUDIO_MODULES,'node-red'));
 const runner=createManualRuntime({nodeRed,version:require(nodeRed).version(),checkActive:async()=>{}});
 async function run(amount,timeout){
  const saved=waitWorkflow(amount);
  saved.settings.executionTimeout=timeout;
  const dispatch=await runner.admit({workflow:saved,selection:full});
  return dispatch({workflow:saved,selection:full});
 }
 const completed=await run(1,-1);
 assert.equal(completed.status,'success');
 assert.ok(completed.data.resultData.runData.Wait[0].executionTime>=950);
 assert.deepEqual(completed.data.resultData.runData.Wait[0].data.main,[[{json:{},pairedItem:{item:0}}]]);
 const canceled=await run(6,1);
 assert.equal(canceled.status,'canceled');
 assert.equal(canceled.data.resultData.error.name,'ManualExecutionCancelledError');
 assert.deepEqual(Object.keys(canceled.data.resultData.runData),['Manual']);
});

test('actual Node-RED worker dispatches the selected saved branch and records node data',
 {skip:!process.env.STUDIO_MODULES?'Owner-provisioned Node-RED runtime absent':false,timeout:90000},async()=>{
 const nodeRed=require.resolve(path.join(process.env.STUDIO_MODULES,'node-red'));
 const runner=createManualRuntime({nodeRed,version:require(nodeRed).version(),checkActive:async()=>{}});
 async function run(value,selection=full){
  const saved=workflow(value);
  const dispatch=await runner.admit({workflow:saved,selection});
  const response=await dispatch({workflow:saved,selection});
  assert.equal(response.status,'success');
  return response.data.resultData.runData;
 }
 const [no,yes]=await Promise.all([run(42),run(60)]);
 assert.deepEqual(Object.keys(no),['Manual','If','False continuation']);
 assert.deepEqual(no.If[0].data.main.map(port=>port.length),[0,1]);
 assert.deepEqual(no['False continuation'][0].source,[{previousNode:'If',previousNodeOutput:1,previousNodeRun:0}]);
 assert.equal(no.If[0].data.main[1][0].pairedItem.item,0);
 assert.deepEqual(Object.keys(yes),['Manual','If']);
 assert.deepEqual(yes.If[0].data.main.map(port=>port.length),[1,0]);
 const partial=await run('={{ $json.score }}',{...full,destination:'If'});
 assert.deepEqual(Object.keys(partial),['Manual','If']);
 assert.deepEqual(partial.If[0].data.main.map(port=>port.length),[0,1]);
});

test('Stop observes a real child exit and removes its isolated runtime directory',
 {skip:!process.env.STUDIO_MODULES?'Owner-provisioned Node-RED runtime absent':false,timeout:45000},async()=>{
 const nodeRed=require.resolve(path.join(process.env.STUDIO_MODULES,'node-red'));
 const runner=createManualRuntime({nodeRed,version:require(nodeRed).version(),checkActive:async()=>{}});
 const controller=new AbortController(),saved=workflow();
 const dispatch=await runner.admit({workflow:saved,selection:full});
 const root=os.tmpdir();
 const before=new Set(fs.readdirSync(root));
 const outcome=dispatch({workflow:saved,selection:full,signal:controller.signal});
 let created;
 for(let attempts=0;attempts<50&&!created;attempts++){
  created=fs.readdirSync(root).find(name=>name.startsWith('mantle-studio-manual-')&&!before.has(name));
  if(!created)await delay(5);
 }
 try{assert.ok(created,'A worker must start before cancellation');}
 finally{controller.abort();}
 const result=await outcome;
 assert.equal(result.status,'canceled');
 assert.equal(fs.existsSync(path.join(root,created)),false);
});
