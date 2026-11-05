'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),http=require('node:http');
const {createRequire}=require('node:module'),{once}=require('node:events');
const {JsonWorker}=require('./json-worker.cjs'),{localAccess}=require('./local-access.cjs');
const {mountCommunityEditor}=require('./community-editor.cjs'),{createResidentView}=require('./resident-view.cjs');
const {initialize,project}=require('./editor-local-context.cjs');
test('same-host adapter uses real durable workflow storage and a bounded Body view',
 {skip:!process.env.STUDIO_MODULES?'Owner-provisioned Node-RED runtime absent; HTTP integration untested':false,timeout:30000},async t=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'studio-community-'));
 const nodeRed=path.join(process.env.STUDIO_MODULES,'node-red');
 const express=createRequire(require.resolve(nodeRed))('express');
 const worker=new JsonWorker({python:process.env.STUDIO_PYTHON||'python',args:['-c','import sys; from pathlib import Path; from mantleos.studio_inventory import EditorInventory; from mantleos.studio_workflows import WorkflowStore,serve; i=EditorInventory(Path(sys.argv[1]).parent); i.initialize(reviewed=True); i.register("credentials",{"id":"synthetic-ref","name":"Synthetic descriptor","type":"httpBasicAuth"},reviewed=True); raise SystemExit(serve(WorkflowStore(sys.argv[1])))',path.join(root,'workflows')],label:'WORKFLOW',maxBytes:16*1024*1024+65536,maxPending:4});
 const app=express();let access;
 app.use((req,res,next)=>access.middleware(req,res,next));
 let encounters=0,reads=0;
 const head='a'.repeat(64),exactReply='  résumé\n🌊  ';
 const resident=createResidentView({body:async(op,args)=>{
  if(op==='status')return {phase:'ACTIVE',heartbeats:1,limbs:[],persona:{name:'Synthetic resident'},private_frame:'PRIVATE',owner_key:'PRIVATE'};
  assert.equal(op,'result');reads++;return {status:'COMMITTED',request_id:args.request_id,reply:exactReply,commit_head:head,private_context:'PRIVATE'};
 },conversation:async args=>{encounters++;return {status:'MIND_SCHEDULED',request_id:args.request_id,private_frame:'PRIVATE'};}});
 const context=project({identity:initialize(path.join(root,'owner.json'),{reviewed:true}),port:18880,settingsTemplate:{}});
 const editor={asset:name=>name==='assets/test.js'?Buffer.from('/* synthetic */'):null,index:()=>'<html><body>synthetic fixture</body></html>'};
 const catalog={asset:()=>Buffer.from('[]')};
 mountCommunityEditor(app,{express,workflows:worker,installation:{editor,catalog,inspection:{authority:'NONE'}},context,resident});
 app.get('/',(req,res)=>res.type('html').send('synthetic local entry'));
 const server=http.createServer(app);await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const port=server.address().port,base='http://127.0.0.1:'+port;
 access=localAccess({port,credentials:{user:'test-only',password:'synthetic-not-an-owner-credential'}});
 t.after(async()=>{
  server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
  const exited=once(worker.process,'exit');worker.end();await exited;
  if(path.dirname(path.resolve(root))!==path.resolve(os.tmpdir())||!path.basename(root).startsWith('studio-community-'))throw Error('Unsafe test cleanup');
  fs.rmSync(root,{recursive:true,force:true});
 });
 // A protocol fixture for document navigation, not browser qualification.
 // Node fetch sets its own Sec-Fetch-Mode and is not a document navigator.
 const entry=await new Promise((resolve,reject)=>{
  http.get(base+'/',{headers:{Accept:'text/html','Sec-Fetch-Mode':'navigate','Sec-Fetch-Dest':'document'}},response=>{
   response.resume();response.on('end',()=>resolve({status:response.statusCode,cookie:response.headers['set-cookie']?.[0]}));
  }).on('error',reject);
 });
 assert.equal(entry.status,200);const cookie=entry.cookie.split(';')[0];
 async function api(method,url,value,extra={}){
  const response=await fetch(base+url,{method,headers:{Cookie:cookie,...(value===undefined?{}:{'Content-Type':'application/json'}),...extra},...(value===undefined?{}:{body:JSON.stringify(value)})});
  const payload=await response.json();return {status:response.status,value:payload};
 }
 const template={name:'Synthetic graph',nodes:[],connections:{},settings:{'test':'one'}};
 const created=await api('POST','/rest/workflows',template);assert.equal(created.status,200);
 const first=created.value.data,route='/rest/workflows/'+first.id;
 const saved=await api('PATCH',route,{versionId:first.versionId,expectedChecksum:first.checksum,name:'Saved by actual storage'});
 assert.equal(saved.status,200);assert.notEqual(saved.value.data.versionId,first.versionId);
 assert.equal((await api('PATCH',route,{versionId:first.versionId,name:'stale'})).status,409);
 assert.equal((await api('PATCH',route,{expectedChecksum:saved.value.data.checksum,name:'no version'})).status,409);
 assert.equal((await api('GET',route)).value.data.name,'Saved by actual storage');
 const current=saved.value.data;
 const competing=await Promise.all(['writer-one','writer-two'].map(name=>api('PATCH',route,{versionId:current.versionId,expectedChecksum:current.checksum,name})));
 assert.deepEqual(competing.map(value=>value.status).sort(),[200,409]);
 assert.equal((await api('PATCH',route,{versionId:current.versionId,name:'forged'},{Origin:'http://outside.invalid'})).status,403);
 assert.equal((await api('POST',route+'/run',{})).status,501);
 const descriptors=await api('GET','/rest/credentials?includeData=true');
 assert.equal(descriptors.status,200);assert.equal(descriptors.value.data[0].id,'synthetic-ref');
 assert.equal(descriptors.value.scope,'DESCRIPTORS_ONLY_NO_SECRET_DATA');assert.equal(descriptors.value.data[0].data,undefined);
 const usable=await api('GET','/rest/credentials/for-workflow?workflowId='+first.id);
 assert.equal(usable.status,200);assert.deepEqual(usable.value.data,[]);assert.equal(usable.value.scope,'NO_QUALIFIED_WORKFLOW_CREDENTIAL_USE');
 assert.equal((await api('GET','/rest/credentials/for-workflow?projectId=not-owned')).status,403);
 assert.equal((await api('POST','/rest/credentials',{id:'FORGED',data:{password:'NEVER_ADMIT'}})).status,501);
 assert.deepEqual((await api('GET','/rest/tags')).value.data,[]);
 assert.equal((await api('GET','/rest/workflows?filter='+encodeURIComponent(JSON.stringify({unsupported:true})))).status,400);
 const malformed=await fetch(base+'/rest/workflows',{method:'POST',headers:{Cookie:cookie,'Content-Type':'application/json'},body:'{"PRIVATE_TOKEN" malformed'});
 assert.equal(malformed.status,400);assert.equal((await malformed.text()).includes('PRIVATE_TOKEN'),false);
 assert.equal((await api('POST','/appai/conversation',{request_id:'user-1',user:'hello'})).value.status,'MIND_SCHEDULED');
 for(let i=0;i<2;i++){
  const reply=await api('GET','/appai/result/user-1');assert.equal(reply.value.reply,exactReply);assert.equal(reply.value.commit_head,head);assert.equal(JSON.stringify(reply.value).includes('PRIVATE'),false);
 }
 assert.equal(encounters,1);assert.equal(reads,2);
 assert.equal(JSON.stringify((await api('GET','/appai/status')).value).includes('PRIVATE'),false);
 assert.equal((await api('POST','/appai/policy',{})).status,404);
 const badMessage=await fetch(base+'/appai/conversation',{method:'POST',headers:{Cookie:cookie,'Content-Type':'application/json'},body:'{"PRIVATE_TOKEN" malformed'});
 assert.equal(badMessage.status,400);assert.equal((await badMessage.text()).includes('PRIVATE_TOKEN'),false);
});
