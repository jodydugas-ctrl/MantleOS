/* One authenticated upgrade dispatcher preserves Node-RED's own websocket
 * handlers. Presence notifications never establish write locks or grants. */
'use strict';
const validPushRef=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{1,96}$/.test(value);
function attachEditorSockets({server,redServer,access,WebSocketServer,editorEnabled}){
 if(!server||!redServer||typeof access?.upgrade!=='function'||typeof WebSocketServer!=='function'||typeof editorEnabled!=='function')throw Error('TRUSTED_SOCKET_HOST_REQUIRED');
 const pushes=new WebSocketServer({noServer:true,maxPayload:65536});
 const byRef=new Map();
 const senders=new WeakMap();
 function upgrade(req,socket,head){
  access.upgrade(req,socket);
  if(socket.destroyed)return;
  if(!editorEnabled()||req.url.split('?')[0]!=='/rest/push')return redServer.emit('upgrade',req,socket,head);
  if(pushes.clients.size>=8)return socket.destroy();
  const params=new URLSearchParams(req.url.split('?')[1]||'');
  const [ref,...duplicates]=params.getAll('pushRef');
  if(ref!==undefined&&(!validPushRef(ref)||duplicates.length||byRef.has(ref)))return socket.destroy();
  pushes.handleUpgrade(req,socket,head,ws=>{
   ws.on('error',()=>{});
   if(ref){
    byRef.set(ref,ws);
    ws.once('close',()=>{if(byRef.get(ref)===ws)byRef.delete(ref);});
   }
   ws.on('message',bytes=>{
    try{
     const value=JSON.parse(bytes.toString('utf8'));
     const keys=value&&typeof value==='object'&&!Array.isArray(value)?Object.keys(value).sort().join(','):'';
     const heartbeat=value?.type==='heartbeat'&&keys==='type';
     const presence=['workflowOpened','workflowClosed'].includes(value?.type)&&keys==='type,workflowId'&&
      typeof value.workflowId==='string'&&/^[A-Za-z0-9_.:-]{1,128}$/.test(value.workflowId)&&!['.','..'].includes(value.workflowId);
     // The pinned client sends these even in a single-owner Community editor.
     // Accepting their shape keeps the real channel open; it performs no write,
     // claims no collaboration lock, and produces no execution-success event.
     if(!heartbeat&&!presence)ws.close(1008,'Unsupported editor message');
    }
    catch{ws.close(1008,'Invalid editor message');}
   });
  });
 }
 server.on('upgrade',upgrade);
 return Object.freeze({
  capture(ref){
   const ws=validPushRef(ref)?byRef.get(ref):null;
   if(ws?.readyState!==1)return null;
   // A run owns the connection captured at admission. Reuse of the same
   // reference after disconnect cannot redirect an earlier execution's data.
   if(senders.has(ws))return senders.get(ws);
   const send=frame=>{
    if(ws.readyState!==1||ws.bufferedAmount>1024*1024)return false;
    const encoded=JSON.stringify(frame);
    if(Buffer.byteLength(encoded)>1024*1024)return false;
    try{ws.send(encoded);return true;}catch{return false;}
   };
   senders.set(ws,send);
   return send;
  },
  close(){server.off('upgrade',upgrade);byRef.clear();for(const ws of pushes.clients)ws.terminate();pushes.close();}
 });
}
module.exports={attachEditorSockets};
