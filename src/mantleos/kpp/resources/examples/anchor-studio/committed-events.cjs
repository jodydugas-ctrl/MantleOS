/* Committed-only presentation notifications. The trusted Body rechecks release. */
'use strict';
class CommittedEvents {
 constructor(read){
  if(typeof read!=='function')throw Error('Trusted committed-result reader required');
  this.read=read;this.clients=new Set();this.timer=null;
 }
 attach(req,res){
  if(this.clients.size>=4){res.status(503).json({error:'RELEASE_STREAM_BUSY'});return;}
  res.status(200).set({'Content-Type':'text/event-stream','Cache-Control':'no-store','Connection':'keep-alive','X-Accel-Buffering':'no'});
  res.flushHeaders();this.clients.add(res);
  const remove=()=>{this.clients.delete(res);if(!this.clients.size&&this.timer){clearInterval(this.timer);this.timer=null;}};
  res.once('close',remove);res.once('finish',remove);
  if(!this.timer){this.timer=setInterval(()=>{for(const client of this.clients)this.send(client,': keepalive\n\n');},15000);this.timer.unref();}
 }
 send(client,packet){
  if(client.destroyed||client.writableEnded){this.clients.delete(client);return;}
  if(client.writableLength>524288||!client.write(packet)){
   this.clients.delete(client);client.end();
  }
 }
 async release(requestId){
  // Never accept a proposal/earlier receipt as an alternative to current release.
  const value=await this.read(requestId);
  if(value?.status!=='COMMITTED')return false;
  if(typeof value.reply!=='string'||Buffer.byteLength(value.reply)>65536||
     typeof value.commit_head!=='string'||!/^[a-f0-9]{64}$/.test(value.commit_head))throw Error('Invalid committed result');
  const packet='event: committed\ndata: '+JSON.stringify({request_id:requestId,status:'COMMITTED',reply:value.reply,commit_head:value.commit_head})+'\n\n';
  if(Buffer.byteLength(packet)>524288)throw Error('Release notification budget exceeded');
  for(const client of this.clients)this.send(client,packet);
  return true;
 }
 close(){
  if(this.timer)clearInterval(this.timer);this.timer=null;
  for(const client of this.clients)client.end();this.clients.clear();
 }
}
module.exports={CommittedEvents};
