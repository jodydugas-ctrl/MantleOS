'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),http=require('node:http'),path=require('node:path');
const {once}=require('node:events'),{createRequire}=require('node:module');
const {attachEditorSockets}=require('./editor-sockets.cjs'),{localAccess}=require('./local-access.cjs');
test('authenticated dispatcher keeps host sockets working alongside editor heartbeats',
 {skip:!process.env.STUDIO_MODULES?'Owner-provisioned websocket runtime absent; dispatch untested':false,timeout:15000},async t=>{
 const requireHost=createRequire(require.resolve(path.join(process.env.STUDIO_MODULES,'node-red'))),WebSocket=requireHost('ws');
 const server=http.createServer(),redServer=http.createServer();let editorEnabled=true,redUpgrades=0;
 const host=new WebSocket.Server({noServer:true});
 redServer.on('upgrade',(req,socket,head)=>{redUpgrades++;host.handleUpgrade(req,socket,head,ws=>{ws.on('error',()=>{});ws.send('host ready');});});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const port=server.address().port;
 const credentials={user:'synthetic',password:'test-only'},access=localAccess({port,credentials});
 const attached=attachEditorSockets({server,redServer,access,WebSocketServer:WebSocket.Server,editorEnabled:()=>editorEnabled});
 const clients=[];
 t.after(async()=>{for(const ws of clients)ws.terminate();attached.close();for(const ws of host.clients)ws.terminate();host.close();await new Promise(resolve=>server.close(resolve));});
 const headers={Authorization:'Basic '+Buffer.from(credentials.user+':'+credentials.password).toString('base64')};
 function socket(url,extra={}){const ws=new WebSocket('ws://127.0.0.1:'+port+url,{headers:{...headers,...extra}});clients.push(ws);return ws;}
 const editor=socket('/rest/push?pushRef=synthetic');await once(editor,'open');editor.send(JSON.stringify({type:'heartbeat'}));
 editor.send(JSON.stringify({type:'workflowOpened',workflowId:'synthetic-workflow'}));
 editor.send(JSON.stringify({type:'workflowClosed',workflowId:'synthetic-workflow'}));
 for(const route of ['/red/comms','/flows/host-owned-socket']){const ws=socket(route);assert.equal((await once(ws,'message'))[0].toString(),'host ready');}
 assert.equal(redUpgrades,2);
 assert.equal(editor.readyState,WebSocket.OPEN,'The actual client presence protocol must not cause an offline/reconnect loop');
 const denied=socket('/red/comms',{Origin:'http://outside.invalid'});await once(denied,'error');assert.equal(redUpgrades,2);
 const forgedPresence=socket('/rest/push');await once(forgedPresence,'open');
 forgedPresence.send(JSON.stringify({type:'workflowOpened',workflowId:'synthetic-workflow',authority:'APPROVED'}));
 assert.equal((await once(forgedPresence,'close'))[0],1008);
 editor.send(JSON.stringify({type:'execute',authority:'FORGED'}));assert.equal((await once(editor,'close'))[0],1008);
 editorEnabled=false;const legacy=socket('/rest/push');assert.equal((await once(legacy,'message'))[0].toString(),'host ready');assert.equal(redUpgrades,3);
});
