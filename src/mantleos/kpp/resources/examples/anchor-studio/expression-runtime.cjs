/* Owner-provisioned n8n expression code. Node-RED continues to execute workflows. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const VERSION='2.46.4',LOCK_LIMIT=2*1024*1024;
const LIMITS={entries:16000,bytes:128*1024*1024,file:12*1024*1024,frame:1024*1024};
function demand(ok){if(!ok)throw Error('EXPRESSION_INSTALLATION_REJECTED');}

function inspect(root,snapshot=null){
 const base=path.resolve(root),hash=crypto.createHash('sha256');
 demand(fs.realpathSync(base)===base);
 let files=0,bytes=0,entries=0,metadata;
 function read(name,limit){
  const file=path.join(base,name),before=fs.lstatSync(file);
  demand(before.isFile()&&!before.isSymbolicLink()&&before.size<=limit&&++files<=LIMITS.entries);
  bytes+=before.size;demand(bytes<=LIMITS.bytes);
  const fd=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
  try{
   const opened=fs.fstatSync(fd);
   demand(opened.dev===before.dev&&opened.ino===before.ino&&opened.size===before.size);
   const buffer=Buffer.alloc(before.size+1);
   let length=0;
   while(length<buffer.length){
    const read=fs.readSync(fd,buffer,length,buffer.length-length,null);
    if(!read)break;length+=read;
   }
   const after=fs.lstatSync(file);
   demand(length===before.size&&after.dev===before.dev&&after.ino===before.ino&&after.size===before.size);
   const data=buffer.subarray(0,length);
   hash.update(JSON.stringify([name,length,crypto.createHash('sha256').update(data).digest('hex')])+'\n');
   if(snapshot)fs.writeFileSync(path.join(snapshot,name),data,{flag:'wx'});
   return data;
  }finally{fs.closeSync(fd);}
 }
 function walk(directory){
  demand(++entries<=LIMITS.entries&&fs.lstatSync(path.join(base,directory)).isDirectory());
  if(snapshot)fs.mkdirSync(path.join(snapshot,directory));
  const names=fs.readdirSync(path.join(base,directory),{withFileTypes:true}).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0);
  for(const entry of names){
   demand(entry.name.length<=255&&!/[\\:\u0000-\u001f]/.test(entry.name));
   const name=directory+'/'+entry.name;
   demand(name.length<=768);
   if(entry.isDirectory())walk(name);
   else{
    const data=read(name,LIMITS.file);
    if(name==='node_modules/n8n-workflow/package.json')metadata=JSON.parse(data);
   }
  }
 }
 const lock=JSON.parse(read('package-lock.json',LOCK_LIMIT));
 demand(lock.lockfileVersion===3&&lock.packages?.['node_modules/n8n-workflow']?.version===VERSION);
 walk('node_modules');
 demand(metadata?.name==='n8n-workflow'&&metadata.version===VERSION);
 return {reference:'n8n-workflow@'+VERSION,engine:'quickjs',sha256:hash.digest('hex'),files,bytes};
}

function expressionEnv(userDir){
 const inherited=Object.fromEntries(['SystemRoot','WINDIR'].filter(key=>process.env[key]).map(key=>[key,process.env[key]]));
 return {...inherited,TEMP:userDir,TMP:userDir,TMPDIR:userDir,N8N_BLOCK_ENV_ACCESS_IN_NODE:'true'};
}

async function open({root,sha256,scratch}){
 demand(process.permission&&process.env.N8N_BLOCK_ENV_ACCESS_IN_NODE==='true');
 const snapshot=path.join(scratch,'closure');
 fs.mkdirSync(snapshot);
 const installation=inspect(root,snapshot);
 demand(installation.sha256===sha256);
 const lib=require(path.join(snapshot,'node_modules','n8n-workflow'));
 await lib.Expression.initExpressionEngine({engine:'quickjs',bridgeTimeout:250,bridgeMemoryLimit:64,
  poolSize:1,maxCodeCacheSize:128});
 return {
  installation,
  evaluate({workflow,value,node,items,itemIndex,source,runData,pinData,executionId}){
   demand(typeof node==='string'&&Array.isArray(workflow?.nodes)&&Array.isArray(items)&&
    Number.isInteger(itemIndex)&&itemIndex>=0&&itemIndex<items.length&&workflow.nodes.some(entry=>entry.name===node));
   const graph=new lib.Workflow({...workflow,pinData,nodeTypes:{getByNameAndVersion:()=>undefined}});
   const execution=lib.createRunExecutionData({resultData:{runData,pinData}});
   const executeData={data:{main:[items]},node:graph.nodes[node],source:{main:source}};
   return graph.expression.withIsolate(()=>graph.expression.getParameterValue(value,execution,0,itemIndex,node,
    items,'manual',{$execution:{id:executionId,mode:'test'}},executeData,false,{},node));
  },
  close(){return lib.Expression.disposeExpressionEngine();},
 };
}

async function serve(profile){
 const engine=await open(profile);
 try{
  const lines=require('node:readline').createInterface({input:process.stdin,crlfDelay:Infinity});
  for await(const line of lines){
   let id;
   try{
    demand(Buffer.byteLength(line)<=LIMITS.frame);
    const packet=JSON.parse(line);
    id=packet.id;
    demand(typeof id==='string'&&['ready','evaluate'].includes(packet.op));
    let result=engine.installation;
    if(packet.op==='evaluate'){
     const value=await engine.evaluate(packet.args);
     result=value===undefined?{kind:'missing'}:{kind:'json',value};
    }
    const reply=JSON.stringify({id,ok:true,result},(_key,value)=>{
     demand(typeof value!=='number'||Number.isFinite(value));
     return value;
    });
    demand(Buffer.byteLength(reply)<=LIMITS.frame);
    process.stdout.write(reply+'\n');
   }catch{process.stdout.write(JSON.stringify({id,ok:false,error:'EXPRESSION_REJECTED'})+'\n');}
  }
 }finally{await engine.close();}
}

function start(profile,scratch){
 const {JsonWorker}=require('./json-worker.cjs');
 const worker=new JsonWorker({python:process.execPath,args:[
  '--permission',... [__filename,profile.root,scratch].map(value=>'--allow-fs-read='+value),
  '--allow-fs-write='+scratch,__filename,'--serve',profile.root,profile.sha256,scratch,
 ],label:'EXPRESSION',maxBytes:LIMITS.frame,maxPending:8,
 spawnProcess:(command,args,options)=>require('node:child_process').spawn(command,args,{...options,env:expressionEnv(scratch)})});
 const ready=worker.call('ready',{},180000).then(receipt=>{
  demand(receipt.sha256===profile.sha256);
  return receipt;
 });
 ready.catch(()=>worker.process.kill());
 return {worker,ready};
}

if(require.main===module){
 const fail=()=>{process.stderr.write('EXPRESSION_INSTALLATION_REJECTED\n');process.exitCode=1;};
 if(process.argv[2]==='--serve'){
  const [root,sha256,scratch]=process.argv.slice(3);
  serve({root,sha256,scratch}).catch(fail);
 }else{
  try{process.stdout.write(JSON.stringify(inspect(process.argv[2]))+'\n');}
  catch{fail();}
 }
}
module.exports={inspect,start};
