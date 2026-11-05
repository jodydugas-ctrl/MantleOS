/* Reviewed pure manual execution on an isolated Node-RED runtime. */
'use strict';
const fs=require('node:fs'),http=require('node:http'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process');
const {setTimeout:delay}=require('node:timers/promises');
const conditions=require('./conditions.cjs');
const MAX_INPUT=256*1024;
const triggerType='n8n-nodes-base.manualTrigger',ifType='n8n-nodes-base.if',waitType='n8n-nodes-base.wait';
const MAX_WAIT_SECONDS=20;
const own=(value,key)=>value!=null&&Object.hasOwn(value,key);
const object=value=>value&&typeof value==='object'&&!Array.isArray(value);
const only=(value,keys)=>object(value)&&Object.keys(value).every(key=>keys.includes(key));
function demand(ok,message){if(!ok)throw Error('Unsupported execution: '+message);}

function operand(value){
 if(typeof value!=='string'||!value.startsWith('='))return ()=>value;
 const match=/^=\{\{\s*\$json\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\}\}$/.exec(value);
 demand(match&&match[1].split('.').every(key=>!['constructor','prototype','__proto__'].includes(key)),'expression');
 return item=>match[1].split('.').reduce((current,key)=>own(current,key)?current[key]:undefined,item);
}

function prepareIf(node){
 const {parameters={}}=node;
 demand(node.typeVersion===2.4&&only(parameters,['conditions','options'])&&
  (!parameters.options||only(parameters.options,[])),'IF profile');
 const filter=parameters.conditions,options=filter?.options;
 demand(only(filter,['options','conditions','combinator'])&&only(options,['caseSensitive','leftValue','typeValidation','version'])&&
  typeof options.caseSensitive==='boolean'&&options.typeValidation==='strict'&&options.version===4&&
  (!own(options,'leftValue')||options.leftValue==='')&&Array.isArray(filter.conditions),'IF filter options');
 const clauses=filter.conditions.map((clause,index)=>{
  demand(only(clause,['id','leftValue','rightValue','operator'])&&only(clause.operator,['type','operation','singleValue'])&&
   !(typeof clause.rightValue==='string'&&clause.rightValue.startsWith('=')),'IF operand');
  const {type,operation}=clause.operator;
  return {read:operand(clause.leftValue),comparison:{field:'value'+index,type,operation,
   ...(own(clause,'rightValue')?{value:clause.rightValue}:{})}};
 });
 const spec={schema:'studio.if/1',combinator:filter.combinator,caseSensitive:options.caseSensitive,
  continueOnFail:node.continueOnFail===true,conditions:clauses.map(clause=>clause.comparison)};
 try{conditions.validate(spec);}catch{demand(false,'IF operator');}
 return items=>{
  const projected=items.map((item,index)=>({
   json:Object.fromEntries(clauses.map(({read,comparison})=>[comparison.field,read(item.json)]).filter(([,value])=>value!==undefined)),
   pairedItem:{item:index},
  }));
  const output=conditions.partition(spec,projected);
  return [output.true,output.false].map(port=>port.map(({pairedItem})=>({...items[pairedItem.item],pairedItem})));
 };
}

function prepareWait(node){
 const {parameters={}}=node;
 demand(node.typeVersion===1.1&&only(parameters,['resume','amount','unit'])&&
  parameters.resume==='timeInterval'&&parameters.unit==='seconds'&&
  Number.isInteger(parameters.amount)&&parameters.amount>=1&&parameters.amount<=MAX_WAIT_SECONDS,'Wait profile');
 return async (items,signal)=>{
  await delay(parameters.amount*1000,undefined,{signal});
  return [items.map((item,index)=>({...item,pairedItem:{item:index}}))];
 };
}

function compile(workflow,selection){
 demand(Buffer.byteLength(JSON.stringify(workflow))<=MAX_INPUT&&
  Array.isArray(workflow.nodes)&&workflow.nodes.length>0&&workflow.nodes.length<=64&&
  object(workflow.connections),'graph size');
 const settings=workflow.settings??{};
 demand(only(settings,['executionOrder','binaryMode','saveManualExecutions','executionTimeout'])&&
  (!own(settings,'executionOrder')||settings.executionOrder==='v1')&&
  (!own(settings,'binaryMode')||settings.binaryMode==='separate')&&
  (!own(settings,'saveManualExecutions')||[true,'DEFAULT'].includes(settings.saveManualExecutions))&&
  (!own(settings,'executionTimeout')||(Number.isInteger(settings.executionTimeout)&&
   settings.executionTimeout>=-1&&settings.executionTimeout<=MAX_WAIT_SECONDS))&&
  (!workflow.pinData||only(workflow.pinData,[]))&&!workflow.staticData,'workflow settings or pinned data');
 const steps=new Map();
 for(const [index,node] of workflow.nodes.entries()){
  demand(!steps.has(node.name)&&!node.disabled&&(!node.credentials||only(node.credentials,[]))&&
   !node.executeOnce&&!node.retryOnFail&&!node.alwaysOutputData&&(!node.onError||node.onError==='stopWorkflow'),'node configuration');
  let execute,outputs;
  if(node.type===triggerType){
   demand(node.name===selection.trigger&&(node.typeVersion??1)===1&&(!node.parameters||only(node.parameters,[])),'manual trigger');
   execute=()=>[[{json:{},pairedItem:{item:0}}]];outputs=1;
  }else if(node.type===waitType){
   demand(!node.continueOnFail,'Wait error policy');
   execute=prepareWait(node);outputs=1;
  }else{
   demand(node.type===ifType,'node type');
   execute=prepareIf(node);outputs=2;
  }
  steps.set(node.name,{id:'studio-step-'+index,name:node.name,execute,outputs,wires:Array.from({length:outputs},()=>[])});
 }
 const entry=steps.get(selection.trigger);
 demand(entry&&workflow.nodes.find(node=>node.name===entry.name)?.type===triggerType,'trigger selection');
 const parents=new Map();
 for(const [name,ports] of Object.entries(workflow.connections)){
  const step=steps.get(name);
  demand(step&&only(ports,['main'])&&Array.isArray(ports.main)&&ports.main.length<=step.outputs,'connection port');
  for(const [index,edges] of ports.main.entries()){
   demand(Array.isArray(edges),'connection list');
   for(const edge of edges){
    demand(only(edge,['node','type','index'])&&edge.type==='main'&&edge.index===0&&
     steps.has(edge.node)&&edge.node!==entry.name&&!parents.has(edge.node),'connection or fan-in');
    parents.set(edge.node,name);
    step.wires[index].push(steps.get(edge.node).id);
   }
  }
 }
 const byId=new Map(Array.from(steps.values(),step=>[step.id,step]));
 const reachable=new Set();
 function visit(step){
  demand(!reachable.has(step.id),'cycle');reachable.add(step.id);
  for(const id of step.wires.flat())visit(byId.get(id));
 }
 visit(entry);
 demand(reachable.size===steps.size,'disconnected graph');
 if(selection.destination!==null){
  const keep=new Set();
  demand(steps.has(selection.destination),'destination');
  for(let name=selection.destination;name!==undefined;name=parents.get(name))keep.add(steps.get(name).id);
  for(const id of byId.keys())if(!keep.has(id))byId.delete(id);
  for(const step of byId.values())step.wires=step.wires.map(port=>port.filter(id=>keep.has(id)));
 }
 return {entry,byId,timeout:settings.executionTimeout};
}

async function dispatch({nodeRed,version,workflow,selection,userDir}){
 const plan=compile(workflow,selection),RED=require(nodeRed);
 demand(RED.version()===version,'Node-RED runtime version changed');
 const tab='studio-execution',flows=[{id:tab,type:'tab',label:'Studio manual execution'}];
 for(const [index,step] of Array.from(plan.byId.values()).entries()){
  flows.push({id:step.id,z:tab,type:'studio-execution-step',x:120+index*80,y:120,wires:step.wires});
 }
 const storage={init:async()=>{},getFlows:async()=>flows,saveFlows:async()=>{throw Error('Read-only graph');},
  getCredentials:async()=>({}),saveCredentials:async()=>{},getSettings:async()=>({}),saveSettings:async()=>{},
  getSessions:async()=>({}),saveSessions:async()=>{}};
 const resultData={runData:Object.create(null)};
 let outstanding=1,sequence=0,resolveComplete,failed=false,initialized=false,deadline;
 const complete=new Promise(resolve=>{resolveComplete=resolve;});
 try{
  fs.writeFileSync(path.join(userDir,'package.json'),JSON.stringify({name:'mantle-studio-manual',version:'1.0.0',private:true}));
  RED.init(http.createServer(),{userDir,storageModule:storage,httpAdminRoot:false,httpNodeRoot:false,
   externalModules:{autoInstall:false,palette:{allowInstall:false},modules:{allowInstall:false}},
   logging:{console:{level:'off'}}});
  initialized=true;
  RED.nodes.registerType('studio-execution-step',function(config){
   RED.nodes.createNode(this,config);
   const step=plan.byId.get(config.id);
   this.on('input',async (msg,send,done)=>{
    const startTime=Date.now(),executionIndex=sequence++;
    try{
     if(failed||deadline?.aborted)return;
     const ports=await step.execute(msg.items,deadline);
     if(failed||deadline?.aborted)return;
     resultData.lastNodeExecuted=step.name;
     resultData.runData[step.name]=[{startTime,executionIndex,source:msg.source,executionTime:Date.now()-startTime,
      executionStatus:'success',data:{main:ports}}];
     const outgoing=ports.map((items,index)=>{
      if(!items.length||!step.wires[index].length)return null;
      outstanding+=step.wires[index].length;
      return {items,source:[{previousNode:step.name,previousNodeOutput:index,previousNodeRun:0}]};
     });
     send(outgoing);
    }catch(error){
     if(error.name==='AbortError'&&deadline?.aborted)return;
     failed=true;
     resultData.lastNodeExecuted=step.name;
     resultData.error={name:'NodeOperationError',message:'The admitted IF condition rejected an input item.'};
     resultData.runData[step.name]=[{startTime,executionIndex,source:msg.source,executionTime:Date.now()-startTime,
      executionStatus:'error',error:resultData.error}];
    }finally{done();if(--outstanding===0)resolveComplete();}
   });
  });
  await RED.start();
  for(let attempt=0;attempt<500&&!RED.nodes.getNode(plan.entry.id);attempt++)await delay(20);
  const entry=RED.nodes.getNode(plan.entry.id);
  if(!entry)throw Error('Node-RED startup timed out');
  if(plan.timeout>0)deadline=AbortSignal.timeout(plan.timeout*1000);
  entry.receive({items:[],source:[]});
  await complete;
  if(deadline?.aborted){
   resultData.error={name:'ManualExecutionCancelledError',message:'The execution was cancelled manually'};
   return {status:'canceled',data:{version:1,resultData}};
  }
  return {status:failed?'error':'success',data:{version:1,startData:{},resultData,executionData:{
   contextData:{},nodeExecutionStack:[],metadata:{},waitingExecution:{},waitingExecutionSource:{},
  }}};
 }finally{
  if(initialized)await RED.stop();
 }
}

function canceled(){
 return {status:'canceled',data:{version:1,resultData:{runData:{}}}};
}

function runWorker(frame,signal){
 return new Promise((resolve,reject)=>{
  const child=spawn(process.execPath,[__filename,'--worker'],{windowsHide:true,stdio:['pipe','pipe','ignore']});
  const output=[];
  let bytes=0,termination=null,failed=false;
  const terminate=reason=>{
   if(termination||child.exitCode!==null||child.signalCode!==null)return;
   try{if(child.kill('SIGTERM'))termination=reason;}catch{failed=true;}
  };
  const stop=()=>terminate('stop');
  const timeout=setTimeout(()=>terminate('timeout'),30000);
  child.on('error',()=>{failed=true;});
  child.stdin.on('error',()=>{});
  child.stdout.on('data',chunk=>{
   bytes+=chunk.length;
   if(bytes>4*1024*1024){failed=true;terminate('output limit');}
   else output.push(chunk);
  });
  child.once('close',(code,exitSignal)=>{
   clearTimeout(timeout);
   signal?.removeEventListener('abort',stop);
   if(termination==='stop'&&exitSignal==='SIGTERM')return resolve(canceled());
   if(failed||code!==0||termination)return reject(Error('Node-RED manual worker unavailable'));
   try{resolve(JSON.parse(Buffer.concat(output).toString('utf8')));}
   catch{reject(Error('Invalid manual worker result'));}
  });
  signal?.addEventListener('abort',stop,{once:true});
  child.stdin.end(JSON.stringify(frame));
 });
}

function createManualRuntime({nodeRed,version,checkActive}){
 let running=0;
 return {async admit({workflow,selection}){
  await checkActive();
  compile(workflow,selection);
  return async input=>{
   if(input.signal?.aborted)return canceled();
   await checkActive();
   if(input.signal?.aborted)return canceled();
   if(running>=2)return {status:'error',data:{version:1,resultData:{runData:{},
    error:{name:'ExecutionCapacity',message:'Manual execution capacity reached.'}}}};
   const parent=fs.realpathSync(os.tmpdir());
   running++;
   let userDir;
   try{
    userDir=fs.mkdtempSync(path.join(parent,'mantle-studio-manual-'));
    return await runWorker({nodeRed,version,workflow:input.workflow,selection:input.selection,userDir},input.signal);
   }finally{
    running--;
    if(userDir&&path.dirname(fs.realpathSync(userDir))===parent)fs.rmSync(userDir,{recursive:true,force:true});
   }
  };
 }};
}

async function main(){
 const chunks=[];
 let size=0;
 for await(const bytes of process.stdin){
  size+=bytes.length;
  if(size>MAX_INPUT+65536)throw Error('Manual worker input too large');
  chunks.push(bytes);
 }
 const result=await dispatch(JSON.parse(Buffer.concat(chunks).toString('utf8')));
 process.stdout.write(JSON.stringify(result));
}
if(require.main===module&&process.argv[2]==='--worker')main().catch(()=>{process.exitCode=1;});
module.exports={createManualRuntime};
