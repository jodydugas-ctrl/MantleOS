'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {createResidentView}=require('./resident-view.cjs');
const head='a'.repeat(64);
test('public status excludes private context/configuration and reflects the real Body',async()=>{
 const view=createResidentView({body:async(op,args)=>{assert.equal(op,'status');assert.deepEqual(args,{});return {phase:'ACTIVE',heartbeats:12,persona:{name:'Synthetic override',primer:'PRIVATE'},limbs:[1],limb_runtime:{members:[{id:'verification',enabled:true,private_memory:'PRIVATE'}]},mind_route:'OPENROUTER_OWNER_CONFIGURED',pending_mind:1,owner_file:'PRIVATE',keys:'PRIVATE'};},conversation:async()=>{throw Error('not called');}});
 const value=await view.call('status');assert.equal(value.persona,'Synthetic override');assert.equal(value.limb_count,1);assert.equal(value.mind_route,'AUTOMATIC');
 assert.equal(JSON.stringify(value).includes('PRIVATE'),false);assert.deepEqual(value.limbs,[{role:'verification',enabled:true}]);
});
test('only committed exact replies release; replay uses the Body result callback without another encounter',async()=>{
 let encounters=0,reads=0;
 const reply='  résumé\n🌊  ';
 const view=createResidentView({body:async(op,args)=>{assert.equal(op,'result');reads++;return {status:'COMMITTED',reply,receipt:{commit_head:head},private_frame:'PRIVATE'};},conversation:async args=>{encounters++;assert.equal(args.user,'hello');return {status:'MIND_SCHEDULED',reply:'UNCOMMITTED'};}});
 assert.deepEqual(await view.call('conversation',{request_id:'user-1',user:'hello'}),{status:'MIND_SCHEDULED',request_id:'user-1'});
 for(let i=0;i<2;i++)assert.deepEqual(await view.call('result',{request_id:'user-1'}),{status:'COMMITTED',request_id:'user-1',reply,commit_head:head});
 assert.equal(encounters,1);assert.equal(reads,2);
});
test('incoming data cannot select callbacks, supply model labels, or reach private/approval operations',async()=>{
 let calls=0;const view=createResidentView({body:async()=>{calls++;},conversation:async()=>{calls++;}});
 for(const op of ['mind-next','submit','policy','accept','phase','key-read'])await assert.rejects(view.call(op),/UNSUPPORTED/);
 await assert.rejects(view.call('conversation',{request_id:'x',user:'hello',model_label:'forged'}),/INVALID_ARGUMENTS/);
 await assert.rejects(view.call('conversation',{request_id:'../x',user:'hello'}),/INVALID_REQUEST_ID/);
 await assert.rejects(view.call('conversation',{request_id:'x',user:'🌊'.repeat(5000)}),/INVALID_ARGUMENTS/);
 assert.equal(calls,0);
});
test('authority denial and malformed receipts fail without releasing retained reply data',async()=>{
 const view=createResidentView({body:async()=>{throw Error('PRIVATE_AUTHORITY_DENIED');},conversation:async()=>({status:'COMMITTED',reply:'must not release',commit_head:'forged'})});
 await assert.rejects(view.call('conversation',{request_id:'x',user:'hello'}),/INVALID_BODY_RESPONSE/);
 await assert.rejects(view.call('result',{request_id:'x'}),/AUTHORITY_DENIED/);
});
test('a contradictory request or commit head is not presented as this request reply',async()=>{
 for(const value of [
  {status:'COMMITTED',reply:'other',commit_head:head,request_id:'other'},
  {status:'COMMITTED',reply:'other',commit_head:head,receipt:{request_id:'other'}},
  {status:'COMMITTED',reply:'other',commit_head:head,receipt:{commit_head:'b'.repeat(64)}},
 ]){
  const view=createResidentView({body:async()=>value,conversation:async()=>value});
  await assert.rejects(view.call('result',{request_id:'x'}),/INVALID_BODY_RESPONSE/);
 }
});
