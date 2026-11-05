/* Authenticated local editor projection over the Body's sealed credential store. */
'use strict';
const SCOPES=Object.freeze(['credential:create','credential:delete','credential:list','credential:read','credential:update']);
const editable=new Set(['name','type','data','id','projectId','homeProject','isGlobal','isResolvable','uiContext','usageScope']);

function credentialRoutes(route,{workflows,configuration,capture,personal}){
 const edits=new WeakMap(),deletions=new WeakMap();
 const tabs=new Map();
 const call=(op,args={})=>workflows.call('credential_'+op,{configuration,...args});
 function connection(req,required=true){
  const ref=req.headers['push-ref'],browser=req.headers['browser-id'];
  if(typeof ref==='string'&&/^[a-z0-9]{10}$/.test(ref)&&
     typeof browser==='string'&&/^[a-f0-9-]{36}$/.test(browser)){
   // The pinned overview uses authenticated HTTP without a live push socket.
   // These references separate optimistic revisions within the owner session.
   const key=browser+':'+ref,now=Date.now(),prior=tabs.get(key);
   const tab=prior&&prior.expires>now?prior:{};
   tab.expires=now+15*60*1000;
   tabs.delete(key);tabs.set(key,tab);
   if(tabs.size>32)tabs.delete(tabs.keys().next().value);
   return tab;
  }
  const socket=capture(ref);
  if(!socket&&required)throw Error('PermissionError: credential editor connection');
  return socket;
 }
 function remember(map,socket,row,limit=128){
  if(!socket)return;
  const entries=map.get(socket)??new Map();
  entries.delete(row.id);
  entries.set(row.id,row.revision);
  if(entries.size>limit)entries.delete(entries.keys().next().value);
  map.set(socket,entries);
 }
 function expected(map,socket,id){
  const revision=map.get(socket)?.get(id);
  if(!revision)throw Error('Conflict: reopen credential before modifying');
  return revision;
 }
 function dto(row){
  const {revision,...value}=row;
  return {...value,scopes:SCOPES,isGlobal:false,isManaged:false,isResolvable:false,
   resolverId:null,resolvableAllowFallback:false,pendingAuthorizationExpiresAt:null,usageScope:'workflow'};
 }
 function input(body,id){
  if(!body||typeof body!=='object'||Array.isArray(body)||Object.keys(body).some(key=>!editable.has(key))||
     (body.id!==undefined&&body.id!==(id??'')&&body.id!==null)||
     (body.projectId!==undefined&&body.projectId!==personal.id)||
     (body.homeProject!==undefined&&body.homeProject!==null&&body.homeProject.id!==personal.id)||
     (body.isGlobal!==undefined&&body.isGlobal!==false)||(body.isResolvable!==undefined&&body.isResolvable!==false)||
     (body.usageScope!==undefined&&body.usageScope!=='workflow')||
     (body.uiContext!==undefined&&typeof body.uiContext!=='string'))
   throw Error('Unsupported credential scope');
  return {name:body.name,type:body.type,data:body.data};
 }
 route('get','/rest/credentials/new',async req=>{
  const raw=req.query.name??'Unnamed credential';
  if(typeof raw!=='string'||!raw.trim()||Buffer.byteLength(raw)>110)throw Error('Invalid credential name');
  const names=new Set((await call('list')).map(item=>item.name));
  let name=raw;
  for(let suffix=2;names.has(name);suffix++)name=raw+' '+suffix;
  return {data:{name}};
 });
 route('get','/rest/credentials/:id',async req=>{
  if(req.query.includeData!==undefined&&!['true','false'].includes(req.query.includeData))throw Error('Invalid credential projection');
  const include_data=req.query.includeData==='true';
  const socket=connection(req,include_data);
  const row=await call('get',{identifier:req.params.id,include_data});
  if(include_data)remember(edits,socket,row);
  remember(deletions,socket,row);
  return {data:dto(row)};
 });
 route('post','/rest/credentials',async req=>{
  const socket=connection(req);
  const row=await call('save',{value:input(req.body,null),identifier:null,revision:null});
  remember(edits,socket,row);
  remember(deletions,socket,row);
  return {data:dto(row)};
 });
 route('patch','/rest/credentials/:id',async req=>{
  const socket=connection(req),identifier=req.params.id;
  const row=await call('save',{value:input(req.body,identifier),identifier,revision:expected(edits,socket,identifier)});
  remember(edits,socket,row);
  remember(deletions,socket,row);
  return {data:dto(row)};
 });
 route('delete','/rest/credentials/:id',async req=>{
  const socket=connection(req),identifier=req.params.id;
  const result=await call('remove',{identifier,revision:expected(deletions,socket,identifier)});
  edits.get(socket)?.delete(identifier);
  deletions.get(socket)?.delete(identifier);
  return {data:result};
 });
 return {async list(req){
  const socket=connection(req,false);
  const rows=await call('list');
  return rows.map(row=>{
   remember(deletions,socket,row,2048);
   return {...dto(row),homeProject:{id:personal.id,name:personal.name,type:personal.type},sharedWithProjects:[]};
  });
 }};
}
module.exports={credentialRoutes,SCOPES};
