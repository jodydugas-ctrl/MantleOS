/* Same-host HTTP adapter over the existing operational workflow worker.
 * Callbacks and source snapshots come from trusted launcher code, never recipes
 * or model replies. Unknown operations stay unavailable, not silently accepted. */
'use strict';
const crypto=require('node:crypto');
const {calculateWorkflowChecksum}=require('./workflow-checksum.cjs');
const {mountResidentView}=require('./resident-view.cjs');
const {mountExecutionRoutes}=require('./editor-executions.cjs');
function mountCommunityEditor(app,{express,workflows,installation,context,resident,execution=null}){
 if(typeof express?.json!=='function'||typeof workflows?.call!=='function'||!installation?.editor||!installation?.catalog||!context?.personal||!resident)throw Error('TRUSTED_EDITOR_HOST_REQUIRED');
 const {editor,catalog}=installation,{personal}=context;
 const workflowScopes=personal.scopes.filter(value=>value.startsWith('workflow:'));
 if(execution)workflowScopes.push('workflow:execute');
 let pending=0;
 app.use('/rest',(req,res,next)=>{
  if(pending>=4)return res.status(503).json({code:503,message:'Workflow intake is busy'});
  pending++;let ended=false;const done=()=>{if(!ended){ended=true;pending--;}};res.once('finish',done);res.once('close',done);next();
 });
 app.use('/rest',express.json({limit:16*1024*1024+65536}));
 const route=(method,url,handler)=>app[method](url,async(req,res)=>{
  try{res.json(await handler(req));}
  catch(error){const message=String(error.message),code=message.startsWith('Unsupported execution:')?501:message.startsWith('Conflict:')?409:message.startsWith('KeyError:')?404:message.startsWith('PermissionError:')?403:/WORKFLOW_(BUSY|TIMEOUT|UNAVAILABLE)/.test(message)?503:400;
   res.status(code).json({code,message:message==='Conflict: execution stop requires review'?'Execution stop could not be verified. Review its stored state.':
    message==='Conflict: execution already finished'?'The execution finished before it could be stopped.':
    code===409?'Workflow changed or its loaded version is missing. Retain the draft and reconcile.':code===404?'Workflow or execution not found':code===503?'Workflow storage is unavailable':code===501?'This execution selection is unavailable.':'Workflow request rejected'});}
 });
 route('get','/rest/settings',()=>({data:context.settings}));
 route('get','/rest/login',()=>({data:context.user}));
 route('get','/rest/users',()=>({data:[context.user],count:1}));
 route('get','/rest/projects',()=>({data:context.projects}));
 route('get','/rest/projects/my-projects',()=>({data:context.myProjects}));
 route('get','/rest/projects/count',()=>({data:context.projectCount}));
 route('get','/rest/projects/personal',()=>({data:personal}));
 route('get','/rest/projects/:id',req=>{if(req.params.id!==personal.id)throw Error('KeyError: project');return {data:personal};});
 route('get','/rest/module-settings',()=>({data:{}}));
 route('get','/rest/roles',()=>({data:context.roles}));
 async function inventory(req,collection){
  const filter=req.query.filter?JSON.parse(req.query.filter):{};
  if(!filter||typeof filter!=='object'||Array.isArray(filter)||Object.keys(filter).some(key=>!['name','projectId'].includes(key)))throw Error('Unsupported inventory filter');
  if(filter.projectId!==undefined&&filter.projectId!==personal.id||req.query.projectId!==undefined&&req.query.projectId!==personal.id)throw Error('PermissionError: project');
  if(filter.name!==undefined&&typeof filter.name!=='string')throw Error('Invalid inventory name');
  const skip=Number(req.query.skip||0),take=Number(req.query.take||2048);
  if(!Number.isSafeInteger(skip)||skip<0||!Number.isSafeInteger(take)||take<1||take>2048)throw Error('Invalid inventory pagination');
  const values=await workflows.call('inventory',{collection});
  const filtered=values.filter(value=>!filter.name||value.name.toLowerCase().includes(filter.name.toLowerCase()));
  return {data:filtered.slice(skip,skip+take),count:filtered.length};
 }
 route('get','/rest/credentials',async req=>{
  if(req.query.externalSecretsStore!==undefined||req.query.onlySharedWithMe==='true')throw Error('Unsupported credential sharing');
  const value=await inventory(req,'credentials');
  return {...value,data:value.data.map(item=>({...item,scopes:['credential:read']})),scope:'DESCRIPTORS_ONLY_NO_SECRET_DATA'};
 });
 route('get','/rest/credentials/for-workflow',async req=>{
  if(req.query.forAgent!==undefined)throw Error('Unsupported agent credential use');
  if(req.query.workflowId!==undefined)await workflows.call('get',{id:req.query.workflowId});
  await inventory(req,'credentials');
  // This runtime has no qualified workflow credential-use grants. A descriptor
  // is not a capability, and the MIND's provider key is never a workflow key.
  return {data:[],scope:'NO_QUALIFIED_WORKFLOW_CREDENTIAL_USE'};
 });
 route('get','/rest/tags',req=>inventory(req,'tags'));
 route('get','/rest/favorites',async()=>({data:await workflows.call('inventory',{collection:'favorites'})}));
 route('get','/rest/license',()=>({data:{license:{planId:'',planName:'Community'},
  // No activation, evaluations or published triggers are supported by this
  // host yet. This is the pinned free-edition UI contract, not an entitlement.
  usage:{activeWorkflowTriggers:{value:0,limit:-1,warningThreshold:.8},workflowsHavingEvaluations:{value:0,limit:0}}},
  authority:'NONE; no upstream license activation or workflow effects granted'}));
 route('get','/rest/active-workflows',()=>({data:[]}));
 route('get','/rest/workflows/active',()=>({data:[]}));
 route('get','/rest/workflows/new',()=>({data:{name:'My workflow',settings:{executionOrder:'v1',binaryMode:'separate'}}}));
 async function dto(value){return {...value,active:false,activeVersion:null,description:value.description??null,nodeGroups:value.nodeGroups||[],meta:value.meta??null,staticData:value.staticData??null,
  shared:[{role:'workflow:owner',projectId:personal.id,project:personal}],tags:value.tags||[],parentFolder:null,scopes:workflowScopes,checksum:await calculateWorkflowChecksum(value)};}
 route('get','/rest/workflows/:id/exists',async req=>{
  try{await workflows.call('get',{id:req.params.id});return {data:{exists:true}};}
  catch(error){if(String(error.message).startsWith('KeyError:'))return {data:{exists:false}};throw error;}
 });
 route('get','/rest/workflows',async req=>{
  const filter=req.query.filter?JSON.parse(req.query.filter):{};
  if(!filter||typeof filter!=='object'||Array.isArray(filter)||Object.keys(filter).some(key=>!['name','isArchived','projectId'].includes(key)))throw Error('Unsupported filter');
  if(filter.projectId!==undefined&&filter.projectId!==personal.id)throw Error('PermissionError: project');
  if(req.query.sortBy!==undefined&&req.query.sortBy!=='updatedAt:desc')throw Error('Unsupported order');
  const value=await workflows.call('list',{search:filter.name||'',archived:filter.isArchived??false,offset:Number(req.query.skip||0),limit:Math.min(200,Number(req.query.take||50))});
  return {count:value.count,data:await Promise.all(value.data.map(dto))};
 });
 route('get','/rest/workflows/:id',async req=>({data:await dto(await workflows.call('get',{id:req.params.id}))}));
 route('post','/rest/workflows',async req=>({data:await dto(await workflows.call('mutate',{request_id:'http-'+crypto.randomUUID(),action:'create',value:req.body,...(Object.hasOwn(req.body,'id')?{id:req.body.id}:{})}))}));
 route('patch','/rest/workflows/:id',async req=>{
  const current=await workflows.call('get',{id:req.params.id});
  if(typeof req.body.versionId!=='string'||req.body.versionId!==current.versionId)throw Error('Conflict: version');
  if(req.body.expectedChecksum!==undefined&&req.body.expectedChecksum!==await calculateWorkflowChecksum(current))throw Error('Conflict: checksum');
  return {data:await dto(await workflows.call('mutate',{request_id:'http-'+crypto.randomUUID(),action:'update',id:current.id,revision:current.revision,value:{...current,...req.body}}))};
 });
 const executionRoutes=execution?mountExecutionRoutes(route,{workflows,runtime:execution.runtime,capture:execution.capture,projectId:personal.id}):null;
 app.use('/rest',(req,res)=>res.status(501).json({code:501,message:'This operation is not yet implemented in this BUILDING editor.'}));
 app.use('/rest',(error,req,res,next)=>{if(res.headersSent)return next(error);res.status(error.type==='entity.too.large'?413:400).json({code:error.type==='entity.too.large'?413:400,message:'Invalid or oversized workflow JSON'});});
 for(const name of ['nodes.json','credentials.json','node-versions.json'])app.get('/types/'+name,(req,res)=>{res.setHeader('X-Content-Type-Options','nosniff');res.type('json').send(catalog.asset(name));});
 app.get('/static/base-path.js',(req,res)=>res.type('js').send("window.BASE_PATH = '/';"));
 app.get('/static/posthog.init.js',(req,res)=>res.type('js').send('/* External telemetry is disabled. */'));
 app.get('/static/prefers-color-scheme.css',(req,res)=>res.type('css').send(':root {color-scheme: dark;}'));
 app.get('/assets/:name',(req,res)=>{try{const value=editor.asset('assets/'+req.params.name);if(value===null)return res.sendStatus(404);res.setHeader('X-Content-Type-Options','nosniff');res.type(req.params.name).send(value);}catch{res.sendStatus(404);}});
 app.get('/favicon.ico',(req,res)=>{const value=editor.asset('favicon.ico');if(value===null)return res.sendStatus(404);res.type('ico').send(value);});
 mountResidentView(app,resident,{jsonParser:express.json({limit:'128kb'})});
 return Object.freeze({index(){return editor.index().replace('</body>','<script defer src="/studio/resident-panel.js"></script></body>');},
  async close(){await executionRoutes?.close();},
  inspection:{...installation.inspection,status:'BUILDING_NOT_ACCEPTED',workflow_execution:execution?'HOST_ADMITTED_MANUAL':'UNAVAILABLE',context:'RESIDENT_MEMORY'}});
}
module.exports={mountCommunityEditor};
