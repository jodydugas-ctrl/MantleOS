/* Controlled embedding of the original Node-RED runtime; no core patches. */
'use strict';
const http=require('http'),crypto=require('crypto'),fs=require('fs'),path=require('path');
const {spawn}=require('child_process');
const express=require('module').createRequire(require.resolve(process.env.STUDIO_MODULES+'/node-red'))('express');
const RED=require(process.env.STUDIO_MODULES+'/node-red');
const nest=path.resolve(process.env.STUDIO_NEST),userDir=path.join(nest,'node-red');
fs.mkdirSync(userDir,{recursive:true});
const credentialFile=path.join(nest,'operator.json');
if(!fs.existsSync(credentialFile))fs.writeFileSync(credentialFile,JSON.stringify({user:'studio',password:crypto.randomBytes(24).toString('base64url')}),{flag:'wx'});
const credentials=JSON.parse(fs.readFileSync(credentialFile));
if(!credentials.flowSecret){credentials.flowSecret=crypto.randomBytes(32).toString('hex');fs.writeFileSync(credentialFile,JSON.stringify(credentials));}
const expected=Buffer.from('Basic '+Buffer.from(credentials.user+':'+credentials.password).toString('base64'));
const worker=spawn(process.env.STUDIO_PYTHON||'python',['-m','mantleos','studio','serve','--nest',nest],{stdio:['pipe','pipe','pipe'],windowsHide:true});
let sequence=0,buffer='',alive=true;const pending=new Map();
function call(op,args={}){
 if(!alive)return Promise.reject(Error('BODY_UNAVAILABLE'));
 if(pending.size>=32)return Promise.reject(Error('BODY_BUSY'));
 const id=String(++sequence);
 return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pending.delete(id);reject(Error('BODY_TIMEOUT'));},op==='boot'?180000:30000);
 pending.set(id,{resolve,reject,timer});worker.stdin.write(JSON.stringify({id,op,args})+'\n');});
}
worker.stdout.on('data',data=>{buffer+=data.toString();if(buffer.length>2*1024*1024){worker.kill();return;}
 while(buffer.includes('\n')){const at=buffer.indexOf('\n'),line=buffer.slice(0,at);buffer=buffer.slice(at+1);
  try{const response=JSON.parse(line),p=pending.get(response.id);if(p){clearTimeout(p.timer);pending.delete(response.id);response.ok?p.resolve(response.result):p.reject(Error(response.error));}}catch(e){worker.kill();}
 }});
worker.on('exit',()=>{alive=false;for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('BODY_UNAVAILABLE'));}pending.clear();});
// Redacted process diagnostics; do not forward arbitrary output into cognition.
worker.stderr.on('data',()=>{});
const app=express();
app.use((req,res,next)=>{const supplied=Buffer.from(req.headers.authorization||'');
 if(supplied.length!==expected.length||!crypto.timingSafeEqual(supplied,expected)){res.setHeader('WWW-Authenticate','Basic realm="Anchor Studio"');return res.status(401).end();}
 if(req.method!=='GET'&&req.headers.origin&&req.headers.origin!==`http://127.0.0.1:${port}`)return res.status(403).end();
 next();});
app.use('/studio',express.json({limit:'1mb'}));
const route=(method,url,handler)=>app[method](url,async(req,res)=>{try{res.json(await handler(req));}catch(e){res.status(400).json({error:e.message});}});
route('get','/studio/status',()=>call('status'));
route('get','/studio/result/:id',req=>call('result',{request_id:req.params.id}));
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
route('post','/studio/mind-submit',req=>call('submit',{request_id:req.body.request_id,proposal:req.body.proposal}));
route('post','/studio/conversation',req=>call('conversation',{user:req.body.user,request_id:req.body.request_id,model_label:'CURRENT_CHAT_HOST'}));
route('post','/studio/intention',req=>call('intention',req.body));
route('post','/studio/publish-intentions',req=>call('publish_intentions',{request_id:req.body.request_id}));
route('post','/studio/pain',req=>call('event',{kind:'pain',value:{cause:'operator-synthetic-fixture'},request_id:req.body.request_id}));
app.get('/studio',(req,res)=>res.type('html').send(`<!doctype html><meta charset="utf-8"><title>Anchor Studio</title>
<style>body{font:16px system-ui;max-width:960px;margin:2rem auto;background:#101820;color:#e4eff4}a{color:#8ed5fa}textarea{width:100%;min-height:6em}button{padding:.6em;margin:.5em}pre{white-space:pre-wrap}</style>
<h1>Anchor Studio</h1><p><a href="/red/">Open the original Node-RED editor and Anchor palette</a></p>
<p>The MIND uses a supervised host bridge. Replies appear after durable commit.</p>
<button onclick="phase(true)">Activate</button><button onclick="phase(false)">Stasis</button>
<h2>Canonical project contract</h2><p><a href="/studio/download">Save portable project</a> <label>Import project (data only) <input id="projectFile" type="file" accept=".anchorstudio"></label><button onclick="importProject()">Import selected project</button></p><p>Typed links describe declared relationships; they do not execute Node-RED messages.</p><label>From <select id="linkFrom"></select></label><label>To <select id="linkTo"></select></label><label>Relationship <input id="linkMeaning"></label><button onclick="addLink()">Add typed relationship</button><pre id="links"></pre><button onclick="prepareKpp()">Prepare KPP work packet</button><button onclick="flowDraft()">Review canvas draft</button><button onclick="loadProject()">Load project</button><button onclick="saveProject()">Validate and save revision</button><textarea id="project" style="height:20em" aria-label="Canonical project JSON"></textarea><p id="projectResult"></p><h2>Reviewed calculator evaluation</h2><p>Run the packaged synthetic bake: staged checks, deliberate undo regression, rejection and repair. Imported fixture code never runs here.</p><button onclick="demoTest()">Run packaged regression and repair</button><button onclick="demoAccept()">Baker: accept current verified calculator</button><pre id="evaluation"></pre><h2>Supervised conversation</h2><textarea id="message" aria-label="Message"></textarea><button onclick="send()">Send</button><button onclick="publishIntentions()">Publish proposed limb intentions</button><pre id="reply"></pre><pre id="status"></pre>
<script>async function api(p,b){let r=await fetch('/studio/'+p,b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{});return r.json();}
async function demoTest(){document.getElementById('evaluation').textContent=JSON.stringify(await api('demo-test',{}),null,2);}
async function demoAccept(){if(!confirm('Accept only the current verified calculator obligations as the authenticated Baker?'))return;document.getElementById('evaluation').textContent=JSON.stringify(await api('demo-accept',{confirmed:true}),null,2);}
async function importProject(){try{const file=document.getElementById('projectFile').files[0];if(!file||file.size>550000)throw Error('Choose a project up to 550 kB; larger projects use the CLI');const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);const r=await api('project-import',{encoded:btoa(binary),revision:projectRevision});document.getElementById('projectResult').textContent=r.error||r.inspection.status;if(!r.error)loadProject();}catch(e){document.getElementById('projectResult').textContent=e.message;}}
async function prepareKpp(){document.getElementById('projectResult').textContent=JSON.stringify(await api('kpp-prepare',{}));}
async function flowDraft(){const flows=await api('flows');const r=await api('flow-draft',{flows});document.getElementById('project').value=JSON.stringify(r.project,null,2);projectRevision=r.base_revision;document.getElementById('projectResult').textContent=r.error||r.inspection.status;}
function showLinks(project){const apps=project.recipe.anchor_design.applications;for(const id of ['linkFrom','linkTo']){const select=document.getElementById(id);select.replaceChildren();for(const app of apps){const option=document.createElement('option');option.value=app.id;option.textContent=app.id+' ('+app.type+')';select.appendChild(option);}}document.getElementById('links').textContent=project.recipe.anchor_design.flows.map(e=>e.from+' -> '+e.to+': '+e.relationship).join('\\n');}
function addLink(){try{const p=JSON.parse(document.getElementById('project').value);const relationship=document.getElementById('linkMeaning').value.trim();if(!relationship)throw Error('Relationship meaning is required');p.recipe.anchor_design.flows.push({from:document.getElementById('linkFrom').value,to:document.getElementById('linkTo').value,relationship});document.getElementById('project').value=JSON.stringify(p,null,2);showLinks(p);document.getElementById('projectResult').textContent='DRAFT: validate and save explicitly';}catch(e){document.getElementById('projectResult').textContent=e.message;}}
let projectRevision=null;async function loadProject(){const r=await api('project');projectRevision=r.revision;if(r.project)showLinks(r.project);document.getElementById('project').value=JSON.stringify(r.project,null,2);document.getElementById('projectResult').textContent=r.inspection?.status||r.error;}
async function saveProject(){try{const r=await api('project',{project:JSON.parse(document.getElementById('project').value),revision:projectRevision});projectRevision=r.revision||projectRevision;if(r.project)showLinks(r.project);document.getElementById('projectResult').textContent=r.error||r.inspection.status;}catch(e){document.getElementById('projectResult').textContent=e.message;}}
let lastRequest=null;async function refresh(){document.getElementById('status').textContent=JSON.stringify(await api('status'),null,2);if(lastRequest){const r=await api('result/'+lastRequest);document.getElementById('reply').textContent=r.reply||r.status||r.error;}}
async function publishIntentions(){if(!lastRequest)return;const r=await api('publish-intentions',{request_id:lastRequest});document.getElementById('reply').textContent=r.error||JSON.stringify(r,null,2);}
async function phase(active){await api('phase',{active});refresh();}
async function send(){lastRequest='user-'+crypto.randomUUID();const value=await api('conversation',{user:document.getElementById('message').value,request_id:lastRequest});document.getElementById('status').textContent=value.error||'AWAITING_MIND: host frame is ready';}
setInterval(refresh,3000);refresh();loadProject();</script>`));
const server=http.createServer(app),port=Number(process.env.STUDIO_PORT||18880);
RED.init(server,{userDir,flowFile:'flows.json',credentialSecret:credentials.flowSecret,httpAdminRoot:'/red',httpNodeRoot:'/flows',nodesDir:path.join(__dirname,'palette'),
 functionGlobalContext:{},logging:{console:{level:'info',metrics:false,audit:false},studio:{level:'warn',metrics:false,audit:false,logger:()=>msg=>{if(alive)call('event',{kind:'pain',value:{level:msg.level,type:String(msg.type||'runtime').slice(0,80)},request_id:'pain-'+crypto.randomUUID()}).catch(()=>{});}}}});
app.use('/red',RED.httpAdmin);app.use('/flows',RED.httpNode);
let pulsing=false;
const timer=setInterval(async()=>{if(pulsing||!alive)return;pulsing=true;try{await call('pulse');}catch(e){}finally{pulsing=false;}},1000);
async function close(){clearInterval(timer);try{await call('phase',{active:false});}catch(e){}await RED.stop();worker.stdin.end();server.close();}
route('post','/studio/shutdown',async()=>{setTimeout(()=>close().then(()=>process.exit(0)),100);return {status:'STOPPING'};});
process.on('SIGINT',()=>close().then(()=>process.exit(0)));process.on('SIGTERM',()=>close().then(()=>process.exit(0)));
call('boot').then(receipt=>{console.log('Studio sessions verified: '+receipt.sessions+'; local startup verification '+receipt.startup_verification_ms.toFixed(0)+' ms');return call('phase',{active:true});}).then(()=>RED.start())
 .then(()=>call('event',{kind:'host.started',value:{node_red:RED.version()},request_id:'host-'+crypto.randomUUID()})).then(()=>server.listen(port,'127.0.0.1',()=>console.log('Anchor Studio ready at http://127.0.0.1:'+port+'/studio; operator credentials: '+credentialFile)))
 .catch(()=>{console.error('Studio startup failed; inspect NEST state');worker.kill();process.exit(1);});
