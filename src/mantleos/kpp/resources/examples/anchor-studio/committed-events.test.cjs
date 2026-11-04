'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {EventEmitter}=require('node:events');
const {CommittedEvents}=require('./committed-events.cjs');
class Response extends EventEmitter {
 constructor(){super();this.packets=[];this.writableLength=0;this.accept=true;this.writableEnded=false;}
 status(value){this.statusCode=value;return this;}
 set(value){this.headers=value;return this;}
 flushHeaders(){}
 write(value){this.packets.push(value);return this.accept;}
 json(value){this.body=value;this.end();}
 end(){this.writableEnded=true;this.emit('finish');}
}
const head='a'.repeat(64);
test('only current Body-authorized committed fields reach presentation',async()=>{
 let calls=0;const reply='Exact\n<script>not markup</script>';
 const events=new CommittedEvents(async id=>{calls++;assert.equal(id,'one');return {status:'COMMITTED',reply,commit_head:head,frame:'PRIVATE CONTEXT'};});
 const res=new Response();events.attach({},res);
 try{
  assert.equal(await events.release('one'),true);assert.equal(calls,1);
  const line=res.packets[0];assert.ok(line.startsWith('event: committed\ndata: '));
  assert.deepEqual(JSON.parse(line.slice(23).trim()),{request_id:'one',status:'COMMITTED',reply,commit_head:head});
  assert.ok(!line.includes('PRIVATE CONTEXT'));
 }finally{events.close();}
});
test('denial and reader failure release nothing; each attempt rechecks authority',async()=>{
 let mode='STASIS',reads=0;
 const events=new CommittedEvents(async()=>{reads++;if(mode==='ERROR')throw Error('denied');return {status:mode,reply:'committed only',commit_head:head};});
 const res=new Response();events.attach({},res);
 try{
  assert.equal(await events.release('one'),false);assert.equal(res.packets.length,0);
  mode='ERROR';await assert.rejects(events.release('one'));assert.equal(res.packets.length,0);
  mode='COMMITTED';await events.release('one');assert.equal(res.packets.length,1);assert.equal(reads,3);
 }finally{events.close();}
});
test('malformed commits are rejected and valid maximum-length replies survive encoding',async()=>{
 let value={status:'COMMITTED',reply:'x',commit_head:'forged'};
 const events=new CommittedEvents(async()=>value),res=new Response();events.attach({},res);
 try{
  await assert.rejects(events.release('one'));assert.equal(res.packets.length,0);
  value={status:'COMMITTED',reply:'\0'.repeat(65536),commit_head:head};
  await events.release('one');assert.ok(Buffer.byteLength(res.packets[0])<524288);
  value.reply+='x';await assert.rejects(events.release('one'));assert.equal(res.packets.length,1);
 }finally{events.close();}
});
test('slow clients are detached without blocking other displays',async()=>{
 const events=new CommittedEvents(async()=>({status:'COMMITTED',reply:'exact',commit_head:head}));
 const slow=new Response(),fast=new Response();slow.accept=false;events.attach({},slow);events.attach({},fast);
 try{
  await events.release('one');assert.equal(slow.writableEnded,true);assert.equal(events.clients.size,1);
  await events.release('two');assert.equal(slow.packets.length,1);assert.equal(fast.packets.length,2);
 }finally{events.close();}
});
test('connection budget and shutdown are bounded',()=>{
 const events=new CommittedEvents(async()=>({status:'STASIS'}));
 const clients=Array.from({length:5},()=>new Response());
 for(const res of clients)events.attach({},res);
 assert.equal(clients[4].statusCode,503);assert.equal(events.clients.size,4);
 events.close();assert.ok(clients.every(res=>res.writableEnded));assert.equal(events.clients.size,0);
});
