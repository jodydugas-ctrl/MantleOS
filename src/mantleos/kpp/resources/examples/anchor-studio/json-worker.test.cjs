'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {PassThrough}=require('node:stream'),{EventEmitter}=require('node:events');
const {JsonWorker}=require('./json-worker.cjs');
function fixture(options={}){
 const child=new EventEmitter();child.stdin=new PassThrough();child.stdout=new PassThrough();child.stderr=new PassThrough();child.killed=false;child.kill=()=>{child.killed=true;child.emit('exit',1);};
 const client=new JsonWorker({python:'synthetic',args:[],spawnProcess:()=>child,...options});
 let request='';child.stdin.on('data',b=>{request+=b.toString();});
 return {client,child,request:()=>request};
}
test('Unicode byte boundaries preserve the exact response',async()=>{
 const {client,child}=fixture(),pending=client.call('inspect');
 const wire=Buffer.from(JSON.stringify({id:'rpc-1',ok:true,result:'Cuttlefish 🦑 — 日本語'})+'\n');
 for(const byte of wire)child.stdout.write(Buffer.from([byte]));
 assert.equal(await pending,'Cuttlefish 🦑 — 日本語');client.end();
});
test('Timeout never retries an uncertain request',async()=>{
 const {client,child,request}=fixture();
 await assert.rejects(client.call('write',{},10),/TIMEOUT/);
 assert.equal(request().split('\n').filter(Boolean).length,1);
 child.stdout.write(JSON.stringify({id:'rpc-1',ok:true,result:'late'})+'\n');
 assert.equal(client.pending.size,0);client.end();
});
test('Queue, request and response budgets fail explicitly',async()=>{
 const {client,child}=fixture({maxPending:1,maxBytes:200});const one=client.call('wait');
 await assert.rejects(client.call('wait'),/BUSY/);child.stdout.write(JSON.stringify({id:'rpc-1',ok:true,result:'done'})+'\n');assert.equal(await one,'done');
 await assert.rejects(client.call('large',{text:'x'.repeat(250)}),/LIMIT/);
 const response=client.call('read');child.stdout.write('x'.repeat(201));await assert.rejects(response,/PROTOCOL/);assert.equal(child.killed,true);
});
test('Malformed success claims or child failure cannot release a value',async()=>{
 for(const packet of [{id:'rpc-1',ok:'true',result:'forged'},null]){
  const {client,child}=fixture(),pending=client.call('read');child.stdout.write(JSON.stringify(packet)+'\n');await assert.rejects(pending,/PROTOCOL/);
 }
 const {client,child}=fixture(),pending=client.call('write');child.emit('exit',1);await assert.rejects(pending,/UNAVAILABLE/);
});
test('Invalid UTF-8 cannot silently change an otherwise valid reply',async()=>{
 const {client,child}=fixture(),pending=client.call('read');
 child.stdout.write(Buffer.concat([Buffer.from('{"id":"rpc-1","ok":true,"result":"'),Buffer.from([0xff]),Buffer.from('"}\n')]));
 await assert.rejects(pending,/PROTOCOL/);assert.equal(child.killed,true);
});
