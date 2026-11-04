/* Bounded foreground JSON-lines transport. No retry, authority or model calls. */
'use strict';
const {spawn}=require('node:child_process');
const {TextDecoder}=require('node:util');

class JsonWorker {
 constructor({python,args,label='BODY',maxBytes=2*1024*1024,maxPending=32,spawnProcess=spawn}){
  this.label=label;this.maxBytes=maxBytes;this.maxPending=maxPending;this.pending=new Map();
  this.sequence=0;this.buffer='';this.decoder=new TextDecoder('utf-8',{fatal:true});this.alive=true;
  this.process=spawnProcess(python,args,{stdio:['pipe','pipe','pipe'],windowsHide:true});
  this.process.stdout.on('data',data=>this.receive(data));
  this.process.stderr.on('data',()=>{}); // Private diagnostics never enter browser/model frames.
  this.process.on('error',()=>this.fail('UNAVAILABLE'));
  this.process.on('exit',()=>this.fail('UNAVAILABLE'));
  this.process.stdin.on('error',()=>this.fail('UNAVAILABLE'));
 }
 failure(code){const error=Error(this.label+'_'+code);error.code=this.label+'_'+code;return error;}
 fail(code){
  this.alive=false;
  for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(this.failure(code));}
  this.pending.clear();this.buffer='';
 }
 receive(data){
  if(!this.alive)return;
  try{
   this.buffer+=this.decoder.decode(data,{stream:true});
   let newline;
   while((newline=this.buffer.indexOf('\n'))!==-1){
    const line=this.buffer.slice(0,newline);this.buffer=this.buffer.slice(newline+1);
    if(Buffer.byteLength(line)>this.maxBytes)throw Error('LIMIT');
    const packet=JSON.parse(line);
    if(typeof packet.id!=='string'||typeof packet.ok!=='boolean')throw Error('PROTOCOL');
    const p=this.pending.get(packet.id);if(!p)continue;
    if(!packet.ok&&typeof packet.error!=='string')throw Error('PROTOCOL');
    clearTimeout(p.timer);this.pending.delete(packet.id);
    if(packet.ok)p.resolve(packet.result);else p.reject(Error(packet.error));
   }
   if(Buffer.byteLength(this.buffer)>this.maxBytes)throw Error('LIMIT');
  }catch(error){this.fail('PROTOCOL');this.process.kill();}
 }
 call(op,args={},timeout=30000){
  if(!this.alive)return Promise.reject(this.failure('UNAVAILABLE'));
  if(this.pending.size>=this.maxPending)return Promise.reject(this.failure('BUSY'));
  const id='rpc-'+(++this.sequence),line=JSON.stringify({id,op,args})+'\n';
  if(Buffer.byteLength(line)>this.maxBytes)return Promise.reject(this.failure('LIMIT'));
  return new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>{this.pending.delete(id);reject(this.failure('TIMEOUT'));},timeout);
   this.pending.set(id,{resolve,reject,timer});
   this.process.stdin.write(line,error=>{if(error)this.fail('UNAVAILABLE');});
  });
 }
 end(){this.process.stdin.end();}
}
module.exports={JsonWorker};
