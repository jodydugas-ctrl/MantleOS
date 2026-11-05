/* One authenticated upgrade dispatcher preserves Node-RED's own websocket
 * handlers. Presence notifications never establish write locks or grants. */
'use strict';
function attachEditorSockets({server,redServer,access,WebSocketServer,editorEnabled}){
 if(!server||!redServer||typeof access?.upgrade!=='function'||typeof WebSocketServer!=='function'||typeof editorEnabled!=='function')throw Error('TRUSTED_SOCKET_HOST_REQUIRED');
 const pushes=new WebSocketServer({noServer:true,maxPayload:65536});
 function upgrade(req,socket,head){
  access.upgrade(req,socket);
  if(socket.destroyed)return;
  if(!editorEnabled()||req.url.split('?')[0]!=='/rest/push')return redServer.emit('upgrade',req,socket,head);
  if(pushes.clients.size>=8)return socket.destroy();
  pushes.handleUpgrade(req,socket,head,ws=>{
   ws.on('error',()=>{});
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
 return Object.freeze({close(){server.off('upgrade',upgrade);for(const ws of pushes.clients)ws.terminate();pushes.close();}});
}
module.exports={attachEditorSockets};
