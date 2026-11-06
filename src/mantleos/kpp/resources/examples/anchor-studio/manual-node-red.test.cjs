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

test('Node-RED retries the failed step with the committed prefix and rejects changed checkpoint paths',
 {skip:!process.env.STUDIO_MODULES?'Owner-provisioned Node-RED runtime absent':false,timeout:45000},async()=>{
 const nodeRed=require.resolve(path.join(process.env.STUDIO_MODULES,'node-red'));
 const runner=createManualRuntime({nodeRed,version:require(nodeRed).version(),checkActive:async()=>{}});
 const edit=(name,value)=>({name,type:'n8n-nodes-base.set',typeVersion:3.5,parameters:{
  assignments:{assignments:[{name:'value',type:'number',value}]},options:{},
 }});
 const saved=workflow();
 saved.nodes.splice(1,2,edit('Seed',42),edit('Project','invalid'));
 saved.connections={Manual:{main:[[{node:'Seed',type:'main',index:0}]]},
  Seed:{main:[[{node:'Project',type:'main',index:0}]]}};
 async function run(workflow,retry){
  const operation=await runner.admit({workflow,selection:full,retry});
  return operation({workflow,selection:full});
 }
 const failed=await run(saved);
 assert.equal(failed.status,'error');
 const checkpoint=JSON.parse(JSON.stringify(failed.data));
 assert.equal((await run(saved,checkpoint)).status,'error');
 const current=structuredClone(saved);
 current.nodes.splice(1,2,edit('Seed',999),edit('Project','={{ $json.value }}'));
 const retried=await run(current,checkpoint);
 assert.equal(retried.status,'success');
 const traces=retried.data.resultData.runData;
 assert.deepEqual(traces.Seed,checkpoint.resultData.runData.Seed);
 assert.equal(traces.Project[0].data.main[0][0].json.value,42);
 const renamed=structuredClone(current);
 renamed.nodes[2].name='Renamed';
 renamed.connections.Seed.main[0][0].node='Renamed';
 await assert.rejects(runner.admit({workflow:renamed,selection:full,retry:checkpoint}),/retry checkpoint/);
 const effect=structuredClone(current);
 effect.nodes[1].type='n8n-nodes-base.httpRequest';
 await assert.rejects(runner.admit({workflow:effect,selection:full,retry:checkpoint}),/checked HTTP profile/);
});

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
 saved.settings.saveManualExecutions='unsupported';
 await assert.rejects(runner.admit({workflow:saved,selection:full}),/workflow settings/);
 saved.settings.saveManualExecutions=false;
 assert.equal(typeof await runner.admit({workflow:saved,selection:full}),'function');
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

test('Node-RED dispatches a checked HTTP node through the trusted observer once',
 {skip:!process.env.STUDIO_MODULES?'Owner-provisioned Node-RED runtime absent':false,timeout:45000},async()=>{
 const nodeRed=require.resolve(path.join(process.env.STUDIO_MODULES,'node-red'));
 const saved=waitWorkflow();
 saved.nodes[1]={id:'checked-http',name:'Wait',type:'n8n-nodes-base.httpRequest',typeVersion:4.5};
 const calls=[];
 const checked={stage:'VERIFIED',binding_sha256:'a'.repeat(64),json:{accepted:true,value:42}};
 const runner=createManualRuntime({nodeRed,version:require(nodeRed).version(),checkActive:async()=>{},
  effects:{async check(workflow,id){calls.push(['check',workflow.versionId,id]);},
   async observe(run,id){calls.push(['observe',run.claim,id]);return checked;}}});
 const operation=await runner.admit({workflow:saved,selection:full});
 const outcome=await operation({workflow:saved,selection:full,claim:'fixture-private-claim'});
 assert.deepEqual(calls,[['check','saved','checked-http'],['observe','fixture-private-claim','checked-http']]);
 assert.equal(outcome.status,'success');
 assert.deepEqual(outcome.data.resultData.runData.Wait[0].data.main,
  [[{json:checked.json,pairedItem:{item:0}}]]);
 assert.deepEqual(outcome.data.resultData.studioCheckedEffects,
  [{nodeId:'checked-http',stage:'VERIFIED',binding_sha256:checked.binding_sha256}]);
 assert.ok(!JSON.stringify(outcome).includes('fixture-private-claim'));
});

test('Edit Fields feeds typed input to both saved IF operands',
 {skip:!process.env.STUDIO_MODULES?'Owner-provisioned Node-RED runtime absent':false,timeout:45000},async()=>{
 const nodeRed=require.resolve(path.join(process.env.STUDIO_MODULES,'node-red'));
 const runner=createManualRuntime({nodeRed,version:require(nodeRed).version(),checkActive:async()=>{}});
 function edit(name,fields,includeOtherFields=false){
  return {name,type:'n8n-nodes-base.set',typeVersion:3.5,parameters:{
   assignments:{assignments:fields.map(([name,type,value])=>({name,type,value}))},
   includeOtherFields,options:{},
  }};
 }
 const seed=edit('Seed',[
  ['order.amount','number',42],['threshold','number','40'],['eligible','boolean','true'],
  ['codes','array',['x','y']],
 ]);
 const project=edit('Project',[
  ['value','number','={{ $json.order.amount }}'],['missing','string','={{ $json.absent }}'],
  ['fixed.label','string','Synthetic'],
 ],true);
 const saved=workflow();
 const rule=saved.nodes[1].parameters.conditions.conditions[0];
 rule.leftValue='={{ $json.value }}';
 rule.rightValue='={{ $json.threshold }}';
 saved.nodes.splice(1,0,seed,project);
 const connect=name=>({main:[[{node:name,type:'main',index:0}]]});
 saved.connections.Manual=connect('Seed');
 saved.connections.Seed=connect('Project');
 saved.connections.Project=connect('If');
 const operation=await runner.admit({workflow:saved,selection:full});
 const result=await operation({workflow:saved,selection:full});
 assert.equal(result.status,'success');
 assert.deepEqual(result.data.resultData.runData.If[0].data.main,[[{json:{
  order:{amount:42},threshold:40,eligible:true,codes:['x','y'],value:42,missing:null,
  fixed:{label:'Synthetic'},
 },pairedItem:{item:0}}],[]]);
 const forbidden=structuredClone(saved);
 forbidden.nodes[1].parameters.assignments.assignments[0].name='__proto__.unsafe';
 await assert.rejects(runner.admit({workflow:forbidden,selection:full}),/Edit Fields field path/);
 const invalid=structuredClone(saved);
 invalid.nodes[1].parameters.assignments.assignments[0].value='not a number';
 const rejected=await runner.admit({workflow:invalid,selection:full});
 const failure=await rejected({workflow:invalid,selection:full});
 assert.equal(failure.status,'error');
 assert.deepEqual(Object.keys(failure.data.resultData.runData),['Manual','Seed']);
});

test('the pinned n8n QuickJS engine evaluates real Node-RED items and previous-node data',
 {skip:!process.env.STUDIO_MODULES||!process.env.STUDIO_EXPRESSION_ROOT?'Owner-provisioned expression runtime absent':false,
  timeout:240000},async()=>{
 const moduleRoot=process.env.STUDIO_MODULES;
 const root=process.env.STUDIO_EXPRESSION_ROOT;
 const nodeRed=require.resolve(path.join(moduleRoot,'node-red'));
 const expression={root,...require('./expression-runtime.cjs').inspect(root)};
 const runner=createManualRuntime({nodeRed,version:require(nodeRed).version(),expression,checkActive:async()=>{}});
 const saved=workflow();
 saved.id='synthetic-workflow';
 const seed={id:'seed',name:'Seed',position:[240,0],type:'n8n-nodes-base.set',typeVersion:3.5,parameters:{
  assignments:{assignments:[{name:'value',type:'number',value:40}]},
 }};
 const edit={id:'edit',name:'Project',position:[480,0],type:'n8n-nodes-base.set',typeVersion:3.5,parameters:{
  assignments:{assignments:[
   {name:'value',type:'number',value:'={{ $json.value + 2 }}'},
   {name:'fromSeed',type:'number',value:'={{ $("Seed").first().json.value }}'},
   {name:'label',type:'string',value:'=total {{ $input.first().json.value }}'},
   {name:'private',type:'string',value:'={{ process.env.STUDIO_EXPRESSION_TEST_CANARY }}'},
  ]},
 }};
 saved.nodes.splice(1,0,seed,edit);
 const edge=node=>({main:[[{node,type:'main',index:0}]]});
 saved.connections.Manual=edge('Seed');
 saved.connections.Seed=edge('Project');
 saved.connections.Project=edge('If');
 const filter=saved.nodes[3].parameters.conditions.conditions[0];
 filter.leftValue='={{ $json.value }}';
 filter.rightValue='={{ $json.fromSeed + 2 }}';
 process.env.STUDIO_EXPRESSION_TEST_CANARY='owner-private-test-value';
 try{
  const operation=await runner.admit({workflow:saved,selection:full});
  const result=await operation({id:'synthetic-run',workflow:saved,selection:full});
  assert.equal(result.status,'success',JSON.stringify(result));
  assert.deepEqual(result.data.resultData.runData.If[0].data.main,[[{
   json:{value:42,fromSeed:40,label:'total 40',private:null},pairedItem:{item:0},
  }],[]]);
 }finally{delete process.env.STUDIO_EXPRESSION_TEST_CANARY;await runner.close();}
});

test('expression source drift fails admission before Node-RED can start',
 {skip:!process.allowedNodeEnvironmentFlags.has('--permission')?'Node file permissions unavailable':false},async()=>{
 const parent=fs.realpathSync(os.tmpdir());
 const root=fs.mkdtempSync(path.join(parent,'studio-expression-drift-'));
 const packageDir=path.join(root,'node_modules','n8n-workflow');
 const lock={lockfileVersion:3,packages:{'node_modules/n8n-workflow':{version:'2.46.4'}}};
 fs.mkdirSync(packageDir,{recursive:true});
 fs.writeFileSync(path.join(root,'package-lock.json'),JSON.stringify(lock));
 fs.writeFileSync(path.join(packageDir,'package.json'),JSON.stringify({name:'n8n-workflow',version:'2.46.4'}));
 const selected={root,...require('./expression-runtime.cjs').inspect(root)};
 fs.writeFileSync(path.join(packageDir,'index.js'),'throw Error("unreviewed code");');
 const runner=createManualRuntime({expression:selected,checkActive:async()=>{}});
 try{
  await assert.rejects(runner.admit({workflow:workflow('={{ $json.score + 1 }}'),selection:full}),
   /reviewed expression runtime unavailable/);
  assert.equal(runner.expressionStatus(),'UNAVAILABLE');
 }finally{
  await runner.close();
  if(path.dirname(fs.realpathSync(root))===parent)fs.rmSync(root,{recursive:true,force:true});
 }
});
