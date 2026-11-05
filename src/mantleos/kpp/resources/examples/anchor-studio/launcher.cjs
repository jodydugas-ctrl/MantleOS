/* Controlled embedding of the original Node-RED runtime; no core patches. */
'use strict';
const http=require('http'),crypto=require('crypto'),fs=require('fs'),path=require('path');
const {JsonWorker}=require('./json-worker.cjs');
const {CommittedEvents}=require('./committed-events.cjs');
const express=require('module').createRequire(require.resolve(process.env.STUDIO_MODULES+'/node-red'))('express');
const RED=require(process.env.STUDIO_MODULES+'/node-red');
const nest=path.resolve(process.env.STUDIO_NEST),userDir=path.join(nest,'node-red');
fs.mkdirSync(userDir,{recursive:true});
const credentialFile=path.join(nest,'operator.json');
if(!fs.existsSync(credentialFile))fs.writeFileSync(credentialFile,JSON.stringify({user:'studio',password:crypto.randomBytes(24).toString('base64url')}),{flag:'wx'});
const credentials=JSON.parse(fs.readFileSync(credentialFile));
if(!credentials.flowSecret){credentials.flowSecret=crypto.randomBytes(32).toString('hex');fs.writeFileSync(credentialFile,JSON.stringify(credentials));}
const port=Number(process.env.STUDIO_PORT||18880);
const access=require('./local-access.cjs').localAccess({port,credentials});
const python=process.env.STUDIO_PYTHON||'python';
const body=new JsonWorker({python,args:['-m','mantleos','studio','serve','--nest',nest]});
const workflows=new JsonWorker({python,args:['-m','mantleos','studio','workflow-serve','--nest',nest],label:'WORKFLOW',maxBytes:16*1024*1024+65536,maxPending:4});
const automatic=fs.existsSync(path.join(nest,'mind-route.json'));
const mind=automatic?new JsonWorker({python,args:['-m','mantleos','studio','mind-serve','--nest',nest],label:'MIND',maxBytes:512*1024,maxPending:1}):null;
const call=(op,args={})=>body.call(op,args,op==='boot'?180000:30000);
const releases=new CommittedEvents(request_id=>call('result',{request_id}));
let cognitionBusy=false,cognitionFailure=null;
async function cognize(requestId){
 if(!mind||cognitionBusy||cognitionFailure?.request_id===requestId)return;
 cognitionBusy=true;
 try{
  for(let step=0;step<2;step++){
   const result=await mind.call('generate',{request_id:requestId},150000);
   if(result.status==='ALREADY_COMMITTED')return;
   if(result.status!=='RESULT'||!result.value?.proposal)throw Error('MIND_NEEDS_REVIEW');
   const admitted=await call('submit',{request_id:requestId,proposal:result.value.proposal});
   if(admitted.status==='COMMITTED'){await releases.release(requestId).catch(()=>{});return;}
   if(admitted.status!=='AWAITING_MIND')throw Error('MIND_NEEDS_REVIEW');
  }
  throw Error('MIND_ACTION_LIMIT');
 }catch(error){
  cognitionFailure={request_id:requestId,status:'NEEDS_REVIEW',error:'AUTOMATIC_MIND_UNAVAILABLE'};
  if(body.alive)call('event',{kind:'pain',value:{component:'automatic-mind',status:'NEEDS_REVIEW'},request_id:'mind-pain-'+crypto.randomUUID()}).catch(()=>{});
 }finally{cognitionBusy=false;}
}
const workflowFailure=()=>{if(body.alive)call('event',{kind:'pain',value:{component:'workflow-state',status:'UNAVAILABLE'},request_id:'workflow-pain-'+crypto.randomUUID()}).catch(()=>{});};
workflows.process.on('exit',workflowFailure);workflows.process.on('error',workflowFailure);
const app=express();
app.use(access.middleware);
let editorHost=null,sockets=null;
app.get('/',(req,res)=>{
 if(req.query.studio_connect==='1')return res.type('html').send('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Studio reconnected</title></head><body><p>The local editor session is refreshed. Your existing editor tab stays open.</p><p>You can close this tab and return to the editor.</p></body></html>');
 return editorHost?res.type('html').send(editorHost.index()):res.redirect('/studio');
});
let workflowRequests=0;
app.use('/studio/workflows',(req,res,next)=>{
 if(workflowRequests>=4)return res.status(503).json({error:'WORKFLOW_BUSY'});
 workflowRequests++;let finished=false;const release=()=>{if(!finished){finished=true;workflowRequests--;}};
 res.once('finish',release);res.once('close',release);next();
});
app.use('/studio/workflows',express.json({limit:16*1024*1024+65536}));
app.use('/studio',express.json({limit:'1mb'}));
const route=(method,url,handler)=>app[method](url,async(req,res)=>{try{res.json(await handler(req));}catch(e){res.status(400).json({error:e.message});}});
route('get','/studio/status',()=>call('status'));
app.get('/healthz',async(req,res)=>{
 try{
  if(!body.alive||!workflows.alive)throw Error('HOST_WORKER_UNAVAILABLE');
  const state=await call('status'),storage=await workflows.call('health',{});
  if(storage.status!=='ok')throw Error('WORKFLOW_STORE_UNAVAILABLE');
  res.json({status:'ok',runtime:'node-red',version:RED.version(),resident_phase:state.phase});
 }catch{res.status(503).json({status:'unavailable'});}
});
app.get('/studio/events',(req,res)=>releases.attach(req,res));
const workflowRoute=(method,url,handler)=>app[method](url,async(req,res)=>{try{res.json(await handler(req));}catch(error){
 const message=String(error.message||'WORKFLOW_ERROR');
 res.status(message.startsWith('Conflict:')?409:message.startsWith('KeyError:')?404:message.startsWith('PermissionError:')?403:/^WORKFLOW_(TIMEOUT|UNAVAILABLE|BUSY)/.test(message)?503:400).json({error:message});
}});
workflowRoute('get','/studio/workflows',req=>{
 let archived=false;
 if(req.query.archived!==undefined){if(req.query.archived==='all')archived=null;else if(['true','false'].includes(req.query.archived))archived=req.query.archived==='true';else throw Error('Invalid archive filter');}
 return workflows.call('list',{search:req.query.search||'',archived,offset:req.query.offset===undefined?0:Number(req.query.offset),limit:req.query.limit===undefined?100:Number(req.query.limit)});
});
workflowRoute('get','/studio/workflows/:id',req=>workflows.call('get',{id:req.params.id}));
workflowRoute('get','/studio/workflows/:id/history',req=>workflows.call('history',{id:req.params.id}));
workflowRoute('post','/studio/workflows/mutate',req=>workflows.call('mutate',req.body));
async function resultFor(request_id){const result=await call('result',{request_id});return result.status!=='COMMITTED'&&cognitionFailure?.request_id===request_id?cognitionFailure:result;}
route('get','/studio/result/:id',req=>resultFor(req.params.id));
route('get','/studio/mind-status',()=>mind?mind.call('status'):({route:'SUPERVISED_HOST_ONLY'}));
route('get','/studio/project',()=>call('project_get'));
app.get('/studio/download',async(req,res)=>{try{const r=await call('project_bundle');res.setHeader('Content-Disposition','attachment; filename=Anchor-Studio-Demo.anchorstudio');res.type('application/zip').send(Buffer.from(r.base64,'base64'));}catch(e){res.status(400).json({error:e.message});}});
route('post','/studio/project-import',req=>call('project_import',{encoded:req.body.encoded,expected_revision:req.body.revision}));
route('post','/studio/kpp-prepare',()=>call('kpp_prepare'));
route('post','/studio/demo-test',()=>call('demo_test'));
route('post','/studio/demo-accept',req=>call('demo_accept',{confirmed:req.body.confirmed===true}));
route('get','/studio/flows',()=>RED.runtime.flows.getFlows({user:{permissions:'*'}}));
route('post','/studio/project',req=>call('project_set',{value:req.body.project,expected_revision:req.body.revision}));
route('post','/studio/flow-draft',req=>call('flow_draft',{flows:req.body.flows}));
route('post','/studio/phase',req=>{if(typeof req.body.active!=='boolean')throw Error('Boolean phase required');return call('phase',{active:req.body.active});});
route('post','/studio/mind-submit',async req=>{const result=await call('submit',{request_id:req.body.request_id,proposal:req.body.proposal});if(result.status==='COMMITTED')await releases.release(req.body.request_id).catch(()=>{});return result;});
async function encounter({user,request_id}){
 const result=await call('conversation',{user,request_id,model_label:automatic?'OPENROUTER_OWNER_CONFIGURED':'CURRENT_CHAT_HOST'});
 if(result.status==='COMMITTED')return result;
 if(result.status==='AWAITING_MIND'&&automatic)setImmediate(()=>cognize(request_id));
 return {status:result.status==='AWAITING_MIND'&&automatic?'MIND_SCHEDULED':result.status,request_id};
}
route('post','/studio/conversation',req=>encounter(req.body));
route('post','/studio/intention',req=>call('intention',req.body));
route('post','/studio/publish-intentions',req=>call('publish_intentions',{request_id:req.body.request_id}));
route('post','/studio/pain',req=>call('event',{kind:'pain',value:{cause:'operator-synthetic-fixture'},request_id:req.body.request_id}));
for(const asset of ['workspace.css','workspace.js','resident-panel.js'])app.get('/studio/'+asset,(req,res)=>res.sendFile(path.join(__dirname,asset)));
app.get('/studio',(req,res)=>res.type('html').send(fs.readFileSync(path.join(__dirname,'workspace.html'),'utf8')+`<script>async function api(p,b){let r=await fetch('/studio/'+p,b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{});return r.json();}
async function demoTest(){document.getElementById('evaluation').textContent=JSON.stringify(await api('demo-test',{}),null,2);}
async function demoAccept(){if(!confirm('Accept only the current verified calculator obligations as the authenticated Baker?'))return;document.getElementById('evaluation').textContent=JSON.stringify(await api('demo-accept',{confirmed:true}),null,2);}
async function importProject(){try{const file=document.getElementById('projectFile').files[0];if(!file||file.size>550000)throw Error('Choose a project up to 550 kB; larger projects use the CLI');const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);const r=await api('project-import',{encoded:btoa(binary),revision:projectRevision});document.getElementById('projectResult').textContent=r.error||r.inspection.status;if(!r.error)loadProject();}catch(e){document.getElementById('projectResult').textContent=e.message;}}
async function prepareKpp(){document.getElementById('projectResult').textContent=JSON.stringify(await api('kpp-prepare',{}));}
async function flowDraft(){const flows=await api('flows');const r=await api('flow-draft',{flows});document.getElementById('project').value=JSON.stringify(r.project,null,2);projectRevision=r.base_revision;document.getElementById('projectResult').textContent=r.error||r.inspection.status;}
function showLinks(project){const apps=project.recipe.anchor_design.applications;for(const id of ['linkFrom','linkTo']){const select=document.getElementById(id);select.replaceChildren();for(const app of apps){const option=document.createElement('option');option.value=app.id;option.textContent=app.id+' ('+app.type+')';select.appendChild(option);}}document.getElementById('links').textContent=project.recipe.anchor_design.flows.map(e=>e.from+' -> '+e.to+': '+e.relationship).join('\\n');}
function addLink(){try{const p=JSON.parse(document.getElementById('project').value);const relationship=document.getElementById('linkMeaning').value.trim();if(!relationship)throw Error('Relationship meaning is required');p.recipe.anchor_design.flows.push({from:document.getElementById('linkFrom').value,to:document.getElementById('linkTo').value,relationship});document.getElementById('project').value=JSON.stringify(p,null,2);showLinks(p);document.getElementById('projectResult').textContent='DRAFT: validate and save explicitly';}catch(e){document.getElementById('projectResult').textContent=e.message;}}
let projectRevision=null;async function loadProject(){const r=await api('project');projectRevision=r.revision;if(r.project)showLinks(r.project);document.getElementById('project').value=JSON.stringify(r.project,null,2);document.getElementById('projectResult').textContent=r.inspection?.status||r.error;window.renderWorkspace?.();document.getElementById('dirty').textContent='Saved locally';}
async function saveProject(){try{const r=await api('project',{project:JSON.parse(document.getElementById('project').value),revision:projectRevision});projectRevision=r.revision||projectRevision;if(r.project)showLinks(r.project);document.getElementById('projectResult').textContent=r.error||r.inspection.status;if(!r.error){window.renderWorkspace?.();document.getElementById('dirty').textContent='Saved locally';}}catch(e){document.getElementById('projectResult').textContent=e.message;}}
let lastRequest=null;async function refresh(){const status=await api('status');document.getElementById('status').textContent=JSON.stringify(status,null,2);window.studioStatus?.(status);if(lastRequest){const r=await api('result/'+lastRequest);document.getElementById('reply').textContent=r.reply||r.status||r.error;}}
async function publishIntentions(){if(!lastRequest)return;const r=await api('publish-intentions',{request_id:lastRequest});document.getElementById('reply').textContent=r.error||JSON.stringify(r,null,2);}
async function phase(active){await api('phase',{active});refresh();}
async function send(){lastRequest='user-'+crypto.randomUUID();const value=await api('conversation',{user:document.getElementById('message').value,request_id:lastRequest});document.getElementById('reply').textContent=value.error||value.reply||(value.status==='MIND_SCHEDULED'?'Your message is queued for the configured MIND.':value.status);refresh();}
if(typeof EventSource==='function'){const updates=new EventSource('/studio/events');updates.addEventListener('committed',event=>{try{const value=JSON.parse(event.data);if(value.status==='COMMITTED'&&value.request_id===lastRequest&&typeof value.reply==='string')document.getElementById('reply').textContent=value.reply;}catch(error){}});updates.onopen=()=>{if(lastRequest)refresh();};window.addEventListener('pagehide',()=>updates.close(),{once:true});}
setInterval(refresh,3000);refresh();loadProject();</script><script src="/studio/workspace.js"></script></body></html>`));
const server=http.createServer(app);
// Node-RED retains every upgrade handler on a private dispatch target. A single
// public dispatcher authenticates first, then selects editor or host sockets.
const redServer=http.createServer();
RED.init(redServer,{userDir,flowFile:'flows.json',credentialSecret:credentials.flowSecret,httpAdminRoot:'/red',httpNodeRoot:'/flows',nodesDir:path.join(__dirname,'palette'),
 functionGlobalContext:{},logging:{console:{level:'info',metrics:false,audit:false},studio:{level:'warn',metrics:false,audit:false,logger:()=>msg=>{if(body.alive)call('event',{kind:'pain',value:{level:msg.level,type:String(msg.type||'runtime').slice(0,80)},request_id:'pain-'+crypto.randomUUID()}).catch(()=>{});}}}});
app.use('/red',RED.httpAdmin);app.use('/flows',RED.httpNode);
app.use((error,req,res,next)=>{
 if(!req.path.startsWith('/studio/workflows'))return next(error);
 if(res.headersSent)return next(error);
 res.status(error.type==='entity.too.large'?413:400).json({error:error.type==='entity.too.large'?'WORKFLOW_PAYLOAD_TOO_LARGE':'INVALID_WORKFLOW_JSON'});
});
let pulsing=false;
const timer=setInterval(async()=>{if(pulsing||!body.alive)return;pulsing=true;try{await call('pulse');if(mind&&!cognitionBusy){const pending=await call('mind_pending');if(pending.request_id)cognize(pending.request_id);}}catch(e){}finally{pulsing=false;}},1000);
let shuttingDown;
function close(){
 if(!shuttingDown)shuttingDown=(async()=>{
  clearInterval(timer);releases.close();sockets?.close();
  try{await call('phase',{active:false});}catch{}
  await editorHost?.close();
  await RED.stop();body.end();workflows.end();if(mind)mind.end();server.close();
 })();
 return shuttingDown;
}
route('post','/studio/shutdown',async()=>{setTimeout(()=>close().then(()=>process.exit(0)),100);return {status:'STOPPING'};});
process.on('SIGINT',()=>close().then(()=>process.exit(0)));process.on('SIGTERM',()=>close().then(()=>process.exit(0)));
call('boot').then(async receipt=>{
 console.log('Studio sessions verified: '+receipt.sessions+'; local startup verification '+receipt.startup_verification_ms.toFixed(0)+' ms');
 const selected=await call('editor_config');
 if(selected){
  const {openInstallation}=require('./editor-installation.cjs');
  const installation=openInstallation({packageRoot:selected.package_root,editorProfile:selected.editor_profile,catalogRoot:selected.catalog_root,catalogProfile:selected.catalog_profile,expectedDigest:selected.installation_sha256});
  const owner=require('./editor-local-context.cjs');
  const context=owner.project({identity:owner.initialize(path.join(nest,'editor-owner.json'),{reviewed:true}),settingsTemplate:installation.catalog.json('public-settings.json'),port,credentialEditor:selected.credential_editor===true});
  const resident=require('./resident-view.cjs').createResidentView({body:(op,args)=>op==='result'?resultFor(args.request_id):call(op,args),conversation:encounter});
  const execution=selected.manual_execution===true?{
   capture:ref=>sockets?.capture(ref),
   runtime:require('./manual-node-red.cjs').createManualRuntime({
    nodeRed:require.resolve(process.env.STUDIO_MODULES+'/node-red'),version:RED.version(),
    checkActive:()=>call('editor_manual_authority',{sha256:selected.sha256}),
    effects:selected.credential_editor===true?{
     check:(workflow,nodeId)=>workflows.call('credential_effect_check',{workflow_id:workflow.id,
      version_id:workflow.versionId,node_id:nodeId,configuration:selected.sha256}),
     observe:(execution,nodeId)=>workflows.call('credential_effect_observe',{run_id:execution.id,
      claim:execution.claim,node_id:nodeId,configuration:selected.sha256}),
    }:null,
   }),
  }:null;
  const credentials=selected.credential_editor===true?{configuration:selected.sha256,capture:ref=>sockets?.capture(ref)}:null;
  editorHost=require('./community-editor.cjs').mountCommunityEditor(app,{express,workflows,installation,context,resident,execution,credentials});
  app.get('/studio/editor-status',(req,res)=>res.json(editorHost.inspection));
  app.use((req,res,next)=>{
   if(req.method!=='GET'||/^\/(?:studio|red|flows|appai|types|assets|rest)(?:\/|$)/.test(req.path))return next();
   res.type('html').send(editorHost.index());
  });
 }
 const nrRequire=require('module').createRequire(require.resolve(process.env.STUDIO_MODULES+'/node-red'));
 sockets=require('./editor-sockets.cjs').attachEditorSockets({server,redServer,access,WebSocketServer:nrRequire('ws').Server,editorEnabled:()=>!!editorHost});
 return call('phase',{active:true});
}).then(()=>RED.start())
 .then(()=>call('event',{kind:'host.started',value:{node_red:RED.version()},request_id:'host-'+crypto.randomUUID()})).then(()=>server.listen(port,'127.0.0.1',()=>console.log('Anchor Studio ready at http://127.0.0.1:'+port+(editorHost?'/':'/studio')+'; local access is automatic')))
 .catch(()=>{console.error('Studio startup failed; inspect NEST state');body.process.kill();workflows.process.kill();if(mind)mind.process.kill();process.exit(1);});
