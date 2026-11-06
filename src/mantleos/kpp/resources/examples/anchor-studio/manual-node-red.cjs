/* Reviewed pure manual execution on an isolated Node-RED runtime. */
'use strict';
const fs=require('node:fs'),http=require('node:http'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process');
const {setTimeout:delay}=require('node:timers/promises');
const conditions=require('./conditions.cjs');
const {prepareEditFields}=require('./edit-fields.cjs');
const expressionRuntime=require('./expression-runtime.cjs');
const MAX_INPUT=256*1024;
const triggerType='n8n-nodes-base.manualTrigger',ifType='n8n-nodes-base.if',waitType='n8n-nodes-base.wait';
const httpType='n8n-nodes-base.httpRequest';
const editType='n8n-nodes-base.set';
const MAX_WAIT_SECONDS=20;
const own=(value,key)=>value!=null&&Object.hasOwn(value,key);
const object=value=>value&&typeof value==='object'&&!Array.isArray(value);
const only=(value,keys)=>object(value)&&Object.keys(value).every(key=>keys.includes(key));
function demand(ok,message){if(!ok)throw Error('Unsupported execution: '+message);}

function operand(value,native=false){
 if(typeof value!=='string'||!value.startsWith('='))return ()=>value;
 if(native)return (_item,evaluate)=>evaluate(value);
 if(/^=\{\{\s*\$json\s*\}\}$/.test(value))return item=>item;
 const match=/^=\{\{\s*\$json\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\}\}$/.exec(value);
 demand(match&&match[1].split('.').every(key=>!['constructor','prototype','__proto__'].includes(key)),'expression');
 return item=>match[1].split('.').reduce((current,key)=>own(current,key)?current[key]:undefined,item);
}

function hasExpression(value){
 if(typeof value==='string')return value.startsWith('=');
 return value!==null&&typeof value==='object'&&Object.values(value).some(hasExpression);
}

function assignmentValue(value,depth=0){
 demand(depth<=32,'assignment nesting');
 if(Array.isArray(value)){
  const parts=value.map(entry=>assignmentValue(entry,depth+1));
  return item=>parts.map(read=>read(item)??null);
 }
 if(object(value)){
  const parts=Object.entries(value).map(([key,entry])=>[key,assignmentValue(entry,depth+1)]);
  return item=>Object.fromEntries(parts.map(([key,read])=>[key,read(item)??null]));
 }
 return operand(value);
}

function prepareIf(node,native){
 const {parameters={}}=node;
 demand(node.typeVersion===2.4&&only(parameters,['conditions','options'])&&
  (!parameters.options||only(parameters.options,[])),'IF profile');
 const filter=parameters.conditions,options=filter?.options;
 demand(only(filter,['options','conditions','combinator'])&&only(options,['caseSensitive','leftValue','typeValidation','version'])&&
  typeof options.caseSensitive==='boolean'&&options.typeValidation==='strict'&&options.version===4&&
  (!own(options,'leftValue')||options.leftValue==='')&&Array.isArray(filter.conditions),'IF filter options');
 const clauses=filter.conditions.map((clause,index)=>{
  demand(only(clause,['id','leftValue','rightValue','operator'])&&only(clause.operator,['type','operation','singleValue']),'IF operand');
  const {type,operation}=clause.operator;
  const readRight=typeof clause.rightValue==='string'&&clause.rightValue.startsWith('=')?operand(clause.rightValue,native):null;
  return {read:operand(clause.leftValue,native),readRight,comparison:{field:'value'+index,type,operation,
   ...(own(clause,'rightValue')?{value:readRight?null:clause.rightValue}:{})}};
 });
 const spec={schema:'studio.if/1',combinator:filter.combinator,caseSensitive:options.caseSensitive,
  continueOnFail:node.continueOnFail===true,conditions:clauses.map(clause=>clause.comparison)};
 try{conditions.validate(spec);}catch{demand(false,'IF operator');}
 return async (items,_signal,_observe,evaluate)=>{
  const ports=[[],[]];
  for(const [index,item] of items.entries()){
   const projected={json:{},pairedItem:{item:index}},comparisons=[];
   let pass=false;
   try{
    for(const {read,readRight,comparison} of clauses){
     const evaluateItem=value=>evaluate(value,index);
     const left=await read(item.json,evaluateItem);
     if(left!==undefined)projected.json[comparison.field]=left;
     comparisons.push(readRight?{...comparison,value:(await readRight(item.json,evaluateItem))??null}:comparison);
    }
    pass=conditions.partition({...spec,conditions:comparisons},[projected]).true.length===1;
   }catch(error){if(!spec.continueOnFail)throw error;}
   ports[pass?0:1].push({...item,pairedItem:{item:index}});
  }
  return ports;
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

function validatePins(pinData,names){
 const index=value=>Number.isSafeInteger(value)&&value>=0;
 const source=value=>only(value,['previousNode','previousNodeOutput','previousNodeRun'])&&
  names.has(value.previousNode)&&['previousNodeOutput','previousNodeRun'].every(key=>!own(value,key)||index(value[key]));
 const pair=value=>only(value,['item','input','sourceOverwrite'])&&index(value.item)&&
  (!own(value,'input')||value.input===0)&&(!own(value,'sourceOverwrite')||source(value.sourceOverwrite));
 demand(object(pinData),'pinned data must be keyed by node name');
 for(const [name,items] of Object.entries(pinData)){
  demand(names.has(name)&&Array.isArray(items)&&items.length<=256,'pinned node or item count');
  for(const item of items){
   demand(only(item,['json','pairedItem'])&&object(item.json),'pinned item must contain JSON output');
   if(own(item,'pairedItem')){
    const link=item.pairedItem;
    demand(index(link)||pair(link)||(Array.isArray(link)&&link.every(pair)),'pinned item pairing');
   }
  }
 }
}

function compile(workflow,selection,allowEffects=false,native=false,checkpoint=null){
 demand(Buffer.byteLength(JSON.stringify(workflow))<=MAX_INPUT&&
  Array.isArray(workflow.nodes)&&workflow.nodes.length>0&&workflow.nodes.length<=64&&
  object(workflow.connections),'graph size');
 const settings=workflow.settings??{};
 demand(only(settings,['executionOrder','binaryMode','saveManualExecutions','executionTimeout',...(native?['timezone']:[])])&&
  (!own(settings,'executionOrder')||settings.executionOrder==='v1')&&
  (!own(settings,'binaryMode')||settings.binaryMode==='separate')&&
  (!own(settings,'saveManualExecutions')||[true,false,'DEFAULT'].includes(settings.saveManualExecutions))&&
  (!own(settings,'executionTimeout')||(Number.isInteger(settings.executionTimeout)&&
   settings.executionTimeout>=-1&&settings.executionTimeout<=MAX_WAIT_SECONDS))&&
  !workflow.staticData,'workflow settings or static data');
 const savedPins=checkpoint?checkpoint.resultData?.pinData:workflow.pinData;
 const pinData=savedPins===undefined?{}:savedPins;
 validatePins(pinData,new Set(workflow.nodes.map(node=>node.name)));
 const steps=new Map();
 for(const [index,node] of workflow.nodes.entries()){
  demand(!steps.has(node.name)&&!node.disabled&&(node.type===httpType||!node.credentials||only(node.credentials,[]))&&
   !node.executeOnce&&!node.retryOnFail&&!node.alwaysOutputData&&(!node.onError||node.onError==='stopWorkflow'),'node configuration');
  let execute,outputs,effectNode;
  const pinned=own(pinData,node.name);
  const expressions=native&&[editType,ifType].includes(node.type)&&hasExpression(node.parameters??{});
  if(node.type===triggerType){
   demand(node.name===selection.trigger&&(node.typeVersion??1)===1&&(!node.parameters||only(node.parameters,[])),'manual trigger');
   execute=()=>[[{json:{},pairedItem:{item:0}}]];outputs=1;
  }else if(node.type===waitType){
   demand(!node.continueOnFail,'Wait error policy');
   execute=prepareWait(node);outputs=1;
  }else if(node.type===editType){
   const read=value=>expressions&&hasExpression(value)?(_item,evaluate)=>evaluate(value):assignmentValue(value);
   execute=prepareEditFields(node,read);outputs=1;
  }else if(node.type===httpType){
   demand(allowEffects&&node.typeVersion===4.5&&typeof node.id==='string'&&!node.continueOnFail,'checked HTTP profile');
   effectNode=node.id;outputs=1;
   execute=async (items,_signal,observe)=>{
    demand(items.length===1,'checked HTTP input count');
    return [[{json:await observe(effectNode),pairedItem:{item:0}}]];
   };
  }else{
   demand(node.type===ifType,'node type');
   execute=prepareIf(node,expressions);outputs=2;
  }
  demand(!pinned||(outputs===1&&!effectNode),'pinned node must have one output and no external effect');
  steps.set(node.name,{id:'studio-step-'+index,name:node.name,execute,outputs,effectNode,pinned,
   expressions:expressions&&!pinned,
   wires:Array.from({length:outputs},()=>[])});
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
 const effectNodes=Array.from(byId.values()).flatMap(step=>step.effectNode?[step.effectNode]:[]);
 demand(effectNodes.length<=1,'checked HTTP node count');
 return {entry,byId,effectNodes,pinData,expressionNodes:Array.from(byId.values()).filter(step=>step.expressions).map(step=>step.name),
  timeout:settings.executionTimeout};
}

let requestQueue=Promise.resolve(),requestSequence=0;
function requestHost(kind,args){
 const result=requestQueue.then(()=>new Promise((resolve,reject)=>{
  if(!process.connected)return reject(Error('Execution bridge unavailable'));
  const ticket=++requestSequence;
  process.once('message',message=>{
   if(message?.ticket!==ticket||!message.result)return reject(Error('Execution bridge rejected the request'));
   resolve(message.result);
  });
  process.send({kind,args,ticket});
 }));
 requestQueue=result.catch(()=>{});
 return result;
}

// The reviewed retry subset resumes a single pure path. Prior outputs become
// context for expressions but never generate new Node-RED messages.
function resumePoint(plan,selection,observation){
 const prior=observation?.resultData;
 const history=prior?.runData;
 demand(selection.destination===null&&observation?.version===1&&object(history)&&
  prior.error?.name==='NodeOperationError'&&!prior.studioCheckedEffects&&
  observation.startData?.studioSelection?.trigger===selection.trigger&&
  observation.startData.studioSelection.destination===null,'retry has no eligible checkpoint');
 for(const step of plan.byId.values())demand(step.wires.flat().length<=1,'retry requires a single path');
 const prefix=Object.create(null);
 let step=plan.entry,source=[],items=[],index=0;
 while(step){
  const attempts=own(history,step.name)?history[step.name]:null;
  const task=attempts?.[0];
  demand(Array.isArray(attempts)&&attempts.length===1&&task?.executionIndex===index&&
   JSON.stringify(task.source)===JSON.stringify(source),'retry checkpoint path changed');
  if(step.name===prior.lastNodeExecuted){
   demand(index>0&&task.executionStatus==='error'&&Object.keys(history).length===index+1,
    'retry checkpoint is incomplete');
   return {entry:step,prefix,source,items,index};
  }
  const port=step.wires.findIndex(edges=>edges.length);
  items=task.data?.main?.[port];
  demand(task.executionStatus==='success'&&Array.isArray(items)&&items.length>0,'retry input is unavailable');
  prefix[step.name]=attempts;
  source=[{previousNode:step.name,previousNodeOutput:port,previousNodeRun:0}];
  index++;
  step=plan.byId.get(step.wires[port][0]);
 }
 throw Error('Unsupported execution: retry checkpoint is unreachable');
}

function partialPoint(plan,partial){
 const checkpoint=partial?.checkpoint;
 if(!checkpoint)return null;
 const prefix=Object.create(null);
 let entry=plan.entry,source=[],items=[],index=0;
 while(own(checkpoint.prefix,entry.name)){
  const task=checkpoint.prefix[entry.name][0];
  const port=entry.wires.findIndex(edges=>edges.length);
  demand(port>=0&&JSON.stringify(task.source)===JSON.stringify(source)&&
   Number.isSafeInteger(task.executionIndex)&&task.executionIndex>=index,'partial execution checkpoint changed');
  const output=task.data?.main?.[port];
  if(!Array.isArray(output)||!output.length)break;
  prefix[entry.name]=[task];
  source=[{previousNode:entry.name,previousNodeOutput:port,previousNodeRun:0}];
  items=output;
  index=task.executionIndex+1;
  entry=plan.byId.get(entry.wires[port][0]);
 }
 return {entry,prefix,source,items,index};
}

async function dispatch({nodeRed,version,workflow,selection,userDir,allowEffects,native,retry,partial}){
 const plan=compile(workflow,selection,allowEffects&&!retry,native,retry),RED=require(nodeRed);
 const resume=retry?resumePoint(plan,selection,retry):partialPoint(plan,partial);
 const reused=partial&&resume?Object.keys(resume.prefix):[];
 demand(RED.version()===version,'Node-RED runtime version changed');
 const tab='studio-execution',flows=[{id:tab,type:'tab',label:'Studio manual execution'}];
 for(const [index,step] of Array.from(plan.byId.values()).entries()){
  flows.push({id:step.id,z:tab,type:'studio-execution-step',x:120+index*80,y:120,wires:step.wires});
 }
 const storage={init:async()=>{},getFlows:async()=>flows,saveFlows:async()=>{throw Error('Read-only graph');},
  getCredentials:async()=>({}),saveCredentials:async()=>{},getSettings:async()=>({}),saveSettings:async()=>{},
  getSessions:async()=>({}),saveSessions:async()=>{}};
 const resultData={runData:resume?.prefix??Object.create(null)};
 if(Object.keys(plan.pinData).length){
  resultData.pinData=structuredClone(plan.pinData);
  if(partial&&resume){
   for(const [name,tasks] of Object.entries(resume.prefix)){
    if(own(resultData.pinData,name))resultData.pinData[name]=tasks[0].data.main[0];
   }
  }
 }
 let outstanding=1,sequence=resume?.index??0,resolveComplete,failed=false,uncertain=false,initialized=false,deadline;
 const complete=new Promise(resolve=>{resolveComplete=resolve;});
 async function observe(nodeId){
  let observed;
  try{observed=await requestHost('effect',{nodeId});}
  catch{uncertain=true;throw Error('Checked HTTP observation unavailable');}
  if(observed.stage==='UNKNOWN')uncertain=true;
  if(observed.binding_sha256)resultData.studioCheckedEffects=[{nodeId,stage:observed.stage,binding_sha256:observed.binding_sha256}];
  if(observed.stage!=='VERIFIED')throw Error('Checked HTTP request rejected');
  return observed.json;
 }
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
     const evaluate=async(value,itemIndex)=>{
      const result=await requestHost('expression',{value,node:step.name,items:msg.items,itemIndex,
       source:msg.source,runData:resultData.runData,pinData:resultData.pinData});
      return result.kind==='missing'?undefined:result.value;
     };
     let ports;
     if(step.pinned){
      const items=resultData.pinData[step.name].map(item=>({...item,pairedItem:item.pairedItem??{item:0}}));
      resultData.pinData[step.name]=items;
      ports=[items];
     }else{
      ports=await step.execute(msg.items,deadline,observe,evaluate);
     }
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
     resultData.error={name:'NodeOperationError',message:step.effectNode?
      'The checked HTTP request did not return a verified response.':'The admitted node rejected an input item.'};
     resultData.runData[step.name]=[{startTime,executionIndex,source:msg.source,executionTime:Date.now()-startTime,
      executionStatus:'error',error:resultData.error}];
    }finally{done();if(--outstanding===0)resolveComplete();}
   });
  });
  await RED.start();
  const entryId=(resume?.entry??plan.entry).id;
  for(let attempt=0;attempt<500&&!RED.nodes.getNode(entryId);attempt++)await delay(20);
  const entry=RED.nodes.getNode(entryId);
  if(!entry)throw Error('Node-RED startup timed out');
  if(plan.timeout>0)deadline=AbortSignal.timeout(plan.timeout*1000);
  entry.receive({items:resume?.items??[],source:resume?.source??[]});
  await complete;
  if(uncertain)return {status:'needs_review',data:{version:1,resultData}};
  if(deadline?.aborted){
   resultData.error={name:'ManualExecutionCancelledError',message:'The execution was cancelled manually'};
   return {status:'canceled',data:{version:1,resultData}};
  }
  const startData={studioSelection:selection,...(reused.length?{
   studioPartial:{checkpoint:partial.checkpoint.run_id,reused},
  }:{})};
  return {status:failed?'error':'success',data:{version:1,startData,resultData,executionData:{
   contextData:{},nodeExecutionStack:[],metadata:{},waitingExecution:{},waitingExecutionSource:{},
  }}};
 }finally{
  if(initialized)await RED.stop();
 }
}

function canceled(){
 return {status:'canceled',data:{version:1,resultData:{runData:{}}}};
}

function runWorker(frame,signal,plan,observe,evaluate){
 return new Promise((resolve,reject)=>{
  const child=spawn(process.execPath,[__filename,'--worker'],{windowsHide:true,
   stdio:['pipe','pipe','ignore',...(plan.effectNodes.length||plan.expressionNodes.length?['ipc']:[])]});
  const output=[];
  let bytes=0,termination=null,failed=false;
  let effectPending,busy=false,evaluations=0;
  const terminate=reason=>{
   if(termination||child.exitCode!==null||child.signalCode!==null)return;
   try{if(child.kill('SIGTERM'))termination=reason;}catch{failed=true;}
  };
  const stop=()=>terminate('stop');
  const timeout=setTimeout(()=>terminate('timeout'),30000);
  child.on('error',()=>{failed=true;});
  child.stdin.on('error',()=>{});
  child.on('message',message=>{
   const args=message?.args;
   const effect=message?.kind==='effect'&&only(args,['nodeId'])&&plan.effectNodes.includes(args.nodeId)&&!effectPending;
   const expression=message?.kind==='expression'&&only(args,['value','node','items','itemIndex','source','runData','pinData'])&&
    plan.expressionNodes.includes(args.node)&&++evaluations<=512;
   if(busy||termination||signal?.aborted||!Number.isSafeInteger(message?.ticket)||(!effect&&!expression)){
    failed=true;terminate('execution protocol');return;
   }
   busy=true;
   const pending=(async()=>{
    let result;
    try{result=await (effect?observe(args.nodeId):evaluate(args));}
    catch(error){
     if(effect)result={stage:String(error.message).startsWith('PermissionError:')?'FAILED':'UNKNOWN'};
    }
    busy=false;
    try{if(child.connected)child.send({ticket:message.ticket,result},()=>{});}
    catch{failed=true;terminate('execution reply');}
    return result;
   })();
   if(effect)effectPending=pending;
  });
  child.stdout.on('data',chunk=>{
   bytes+=chunk.length;
   if(bytes>4*1024*1024){failed=true;terminate('output limit');}
   else output.push(chunk);
  });
  child.once('close',async (code,exitSignal)=>{
   clearTimeout(timeout);
   signal?.removeEventListener('abort',stop);
   const effect=await effectPending;
   if(termination==='stop'&&exitSignal==='SIGTERM'&&effect?.stage!=='UNKNOWN')return resolve(canceled());
   if(failed||code!==0||termination)return reject(Error('Node-RED manual worker unavailable'));
   try{resolve(JSON.parse(Buffer.concat(output).toString('utf8')));}
   catch{reject(Error('Invalid manual worker result'));}
  });
  signal?.addEventListener('abort',stop,{once:true});
  child.stdin.end(JSON.stringify(frame));
 });
}

function createManualRuntime({nodeRed,version,checkActive,effects=null,expression=null}){
 let running=0,service,expressionState='UNAVAILABLE';
 function warm(){
  if(!expression)return;
  if(!service){
   const parent=fs.realpathSync(os.tmpdir());
   const scratch=fs.mkdtempSync(path.join(parent,'mantle-studio-expression-'));
   service=expressionRuntime.start(expression,scratch);
   expressionState='STARTING';
   service.ready.then(()=>{expressionState='READY';},()=>{expressionState='UNAVAILABLE';});
   service.worker.process.once('close',()=>{
    expressionState='UNAVAILABLE';
    if(fs.existsSync(scratch)&&path.dirname(fs.realpathSync(scratch))===parent)
     fs.rmSync(scratch,{recursive:true,force:true});
   });
  }
  return service.ready;
 }
 return {warm,expressionStatus:()=>expression?expressionState:null,
 async close(){
  if(service?.worker.process.exitCode===null&&service.worker.process.signalCode===null){
   const closed=new Promise(resolve=>service.worker.process.once('close',resolve));
   service.worker.process.kill();await closed;
  }
 },
 async admit({workflow,selection,retry=null,partial=null}){
  await checkActive();
  const plan=compile(workflow,selection,Boolean(effects)&&!retry,Boolean(expression),retry);
  if(retry)resumePoint(plan,selection,retry);
  if(partial){
   demand([...plan.byId.values()].every(step=>!step.effectNode||step.name===selection.destination),
    'cached execution cannot repeat a checked ancestor');
   partialPoint(plan,partial);
  }
  if(plan.expressionNodes.length){
   try{await warm();}
   catch{throw Error('Unsupported execution: reviewed expression runtime unavailable');}
   demand(expressionState==='READY'&&service.worker.alive,'reviewed expression runtime unavailable');
  }
  for(const nodeId of plan.effectNodes)await effects.check(workflow,nodeId);
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
    const {id,name,nodes,connections,settings}=input.workflow;
    const graph={id,name,nodes:nodes.map(({id,name,type,typeVersion,position,parameters})=>({id,name,type,typeVersion,position,parameters})),
     connections,settings,active:false};
    return await runWorker({nodeRed,version,workflow:input.workflow,selection:input.selection,userDir,
     allowEffects:Boolean(effects),native:Boolean(expression),retry,partial},input.signal,plan,nodeId=>effects.observe(input,nodeId),
     args=>service.worker.call('evaluate',{...args,workflow:graph,executionId:input.id},5000));
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
  if(size>MAX_INPUT+65536+4*1024*1024)throw Error('Manual worker input too large');
  chunks.push(bytes);
 }
 const result=await dispatch(JSON.parse(Buffer.concat(chunks).toString('utf8')));
 if(process.connected)process.disconnect();
 process.stdout.write(JSON.stringify(result));
}
if(require.main===module&&process.argv[2]==='--worker')main().catch(()=>{process.exitCode=1;});
module.exports={createManualRuntime};
