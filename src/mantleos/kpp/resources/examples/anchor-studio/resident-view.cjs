/* Presentation over the SAME trusted Body controller. No provider keys, private
 * frames, model proposals, policy changes or acceptance operations are exposed.
 * A commit digest is continuity evidence, not independent authentication. */
'use strict';
class ViewError extends Error {constructor(code){super(code);this.code=code;}}
function identifier(value){
 if(typeof value!=='string'||!/^[A-Za-z0-9_.:-]{1,128}$/.test(value)||['.','..'].includes(value))throw new ViewError('INVALID_REQUEST_ID');return value;
}
function release(value,requestId){
 if(!value||!['COMMITTED','AWAITING_MIND','MIND_SCHEDULED','STASIS','NEEDS_REVIEW'].includes(value.status))throw new ViewError('INVALID_BODY_RESPONSE');
 if(value.request_id!==undefined&&value.request_id!==requestId||value.receipt?.request_id!==undefined&&value.receipt.request_id!==requestId)throw new ViewError('INVALID_BODY_RESPONSE');
 const result={status:value.status,request_id:requestId};
 if(value.status==='COMMITTED'){
  const head=value.commit_head||value.receipt?.commit_head;
  if(value.commit_head&&value.receipt?.commit_head&&value.commit_head!==value.receipt.commit_head)throw new ViewError('INVALID_BODY_RESPONSE');
  if(typeof value.reply!=='string'||Buffer.byteLength(value.reply)>65536||typeof head!=='string'||!/^[a-f0-9]{64}$/.test(head))throw new ViewError('INVALID_BODY_RESPONSE');
  result.reply=value.reply;result.commit_head=head;
 }
 return result;
}
function status(value){
 if(!value||!['ACTIVE','STASIS'].includes(value.phase)||!Number.isInteger(value.heartbeats)||value.heartbeats<0||!Array.isArray(value.limbs)||value.limbs.length>32)throw new ViewError('INVALID_BODY_RESPONSE');
 const members=value.limb_runtime?.members;
 if(members!==undefined&&(!Array.isArray(members)||members.length>32))throw new ViewError('INVALID_BODY_RESPONSE');
 return {phase:value.phase,heartbeats:value.heartbeats,
  persona:typeof value.persona?.name==='string'?value.persona.name.slice(0,512):'Resident (verification pending)',
  limb_count:value.limbs.length,limbs:Array.isArray(members)?members.map(m=>({role:String(m.id).slice(0,128),enabled:m.enabled===true})):[],
  pending_mind:Number.isInteger(value.pending_mind)&&value.pending_mind>=0?value.pending_mind:0,
  mind_route:value.mind_route==='OPENROUTER_OWNER_CONFIGURED'?'AUTOMATIC':'SUPERVISED',
  context:'RESIDENT_MEMORY',isolation:'SAME_OWNER_LOCAL_BOUNDARY_UNQUALIFIED'};
}
function createResidentView({body,conversation}){
 if(typeof body!=='function'||typeof conversation!=='function')throw new ViewError('TRUSTED_HOST_CALLBACKS_REQUIRED');
 return Object.freeze({async call(operation,args={}){
  if(!args||typeof args!=='object'||Array.isArray(args))throw new ViewError('INVALID_ARGUMENTS');
  if(operation==='status'){
   if(Object.keys(args).length)throw new ViewError('INVALID_ARGUMENTS');
   return status(await body('status',{}));
  }
  if(operation==='result'){
   if(Object.keys(args).join(',')!=='request_id')throw new ViewError('INVALID_ARGUMENTS');
   const id=identifier(args.request_id);return release(await body('result',{request_id:id}),id);
  }
  if(operation==='conversation'){
   if(Object.keys(args).sort().join(',')!=='request_id,user'||typeof args.user!=='string'||!args.user.trim()||Buffer.byteLength(args.user)>16384)throw new ViewError('INVALID_ARGUMENTS');
   const id=identifier(args.request_id);return release(await conversation({request_id:id,user:args.user}),id);
  }
  throw new ViewError('UNSUPPORTED_RESIDENT_OPERATION');
 }});
}
function mountResidentView(app,view,{jsonParser}){
 if(typeof jsonParser!=='function')throw new ViewError('TRUSTED_JSON_PARSER_REQUIRED');
 let active=0;
 app.use('/appai',(req,res,next)=>{
  if(active>=4)return res.status(503).json({error:'RESIDENT_BUSY'});
  active++;let ended=false;const done=()=>{if(!ended){ended=true;active--;}};
  res.once('finish',done);res.once('close',done);next();
 });
 app.use('/appai',jsonParser);
 const route=(method,path,operation,args)=>app[method](path,async(req,res)=>{
  try{res.json(await view.call(operation,args(req)));}
  catch(error){const code=error instanceof ViewError?error.code:'RESIDENT_UNAVAILABLE';
   res.status(code==='RESIDENT_UNAVAILABLE'?503:code==='INVALID_BODY_RESPONSE'?502:400).json({error:code});}
 });
 route('get','/appai/status','status',()=>({}));
 route('post','/appai/conversation','conversation',req=>req.body);
 route('get','/appai/result/:id','result',req=>({request_id:req.params.id}));
 app.use('/appai',(req,res)=>res.status(404).json({error:'UNSUPPORTED_RESIDENT_OPERATION'}));
 app.use('/appai',(error,req,res,next)=>{
  if(res.headersSent)return next(error);
  res.status(error.type==='entity.too.large'?413:400).json({error:error.type==='entity.too.large'?'RESIDENT_PAYLOAD_TOO_LARGE':'INVALID_RESIDENT_JSON'});
 });
}
module.exports={createResidentView,mountResidentView,ViewError};
