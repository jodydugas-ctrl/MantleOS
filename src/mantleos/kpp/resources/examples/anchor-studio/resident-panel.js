/* Resident conversation is a separate view over the Body-owned release path. */
(()=>{
 'use strict';
 if(document.getElementById('anchor-studio-resident'))return;
 const style=document.createElement('style');
 style.textContent=`#anchor-studio-resident{position:fixed;right:16px;bottom:48px;z-index:100001;font:13px/1.5 system-ui,sans-serif;color:#eee}
 #anchor-studio-resident button{font:inherit;cursor:pointer;border:1px solid #605c72;border-radius:8px;background:#302a3e;color:#f3efff;padding:8px 14px}
 #anchor-studio-resident button:disabled{opacity:.5;cursor:default}
 #anchor-studio-resident-panel{width:350px;max-width:calc(100vw - 32px);max-height:calc(100vh - 130px);overflow:auto;border:1px solid #5c536b;border-radius:12px;background:#252229;box-shadow:0 10px 48px #0008;padding:18px;margin-bottom:8px}
 #anchor-studio-resident [hidden]{display:none!important}#anchor-studio-resident h2{font-size:17px;margin:0 0 8px}
 #anchor-studio-resident p{margin:6px 0}#anchor-studio-resident small{color:#c2b9cc}
 #anchor-studio-resident textarea{box-sizing:border-box;width:100%;min-height:84px;resize:vertical;font:inherit;border:1px solid #655b72;background:#17151c;color:#fff;border-radius:8px;padding:10px;margin:10px 0}
 #anchor-studio-resident-reply{white-space:pre-wrap;overflow-wrap:anywhere;background:#1c1922;border-radius:8px;padding:12px;max-height:230px;overflow:auto}
 #anchor-studio-resident .resident-actions{display:flex;gap:8px;flex-wrap:wrap}
 #anchor-studio-resident-receipt{display:block;overflow-wrap:anywhere;font-size:10px;margin-top:8px}`;
 document.head.append(style);
 const root=document.createElement('div');root.id='anchor-studio-resident';
 root.innerHTML=`<section id="anchor-studio-resident-panel" role="region" aria-label="Resident AppAI conversation" hidden>
 <h2 id="anchor-studio-resident-name">Resident AppAI</h2><p id="anchor-studio-resident-status">Connecting to the resident…</p>
 <small>Context: resident memory</small><p id="anchor-studio-resident-reply" aria-live="polite">Ready for a message.</p>
 <label for="anchor-studio-resident-message">Message to resident</label><textarea id="anchor-studio-resident-message" maxlength="16384"></textarea>
 <div class="resident-actions"><button id="anchor-studio-resident-send" type="button">Send to resident</button>
 <button id="anchor-studio-resident-check" type="button" hidden>Check saved response</button></div>
 <p id="anchor-studio-resident-reconnect" hidden><a href="/?studio_connect=1" target="_blank" rel="noopener">Reconnect editor</a> in a new tab; keep this draft open.</p>
 <details id="anchor-studio-resident-receipt-details" hidden><summary>Saved response details</summary><small id="anchor-studio-resident-receipt"></small></details></section>
 <button id="anchor-studio-resident-toggle" type="button" aria-expanded="false" aria-controls="anchor-studio-resident-panel">AppAI</button>`;
 document.body.append(root);
 const element=name=>document.getElementById('anchor-studio-resident-'+name);
 const panel=element('panel'),toggle=element('toggle'),send=element('send'),reply=element('reply'),check=element('check');
 let requestId=null,busy=false,active=false,poll=null,health=null;
 try{requestId=sessionStorage.getItem('anchor-studio-resident-request');}catch{}
 async function api(path,value){
  const response=await fetch('/appai/'+path,{...(value===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)})});
  const result=await response.json();if(!response.ok||result.error){const error=Error(result.error||'BODY_UNAVAILABLE');error.httpStatus=response.status;throw error;}return result;
 }
 function state(text){element('status').textContent=text;}
 function working(value){busy=value;send.disabled=value||!active;}
 function receipt(head){element('receipt').textContent=head?'Body commit: '+head:'';element('receipt-details').hidden=!head;}
 async function status(){
  try{
   const value=await api('status');element('reconnect').hidden=true;active=value.phase==='ACTIVE';working(busy);element('name').textContent=value.persona;
   state(`${value.phase==='ACTIVE'?'Active':'Stasis'} · ${value.mind_route==='AUTOMATIC'?'Automatic cognition':'Supervised cognition'} · ${value.limb_count} limbs`);
   if(value.phase!=='ACTIVE'){reply.textContent='The resident is in stasis.';receipt(null);}
  }catch(error){active=false;working(busy);element('reconnect').hidden=error.httpStatus!==401;state(error.httpStatus===401?'Reconnect the editor to continue.':'Resident unavailable. Start the local Studio and check again.');reply.textContent='';receipt(null);}
 }
 async function saved(id=requestId){
  if(!id||id!==requestId)return;
  clearTimeout(poll);
  try{
   const value=await api('result/'+encodeURIComponent(id));
   if(id!==requestId)return;
   if(value.status==='COMMITTED'){
    reply.textContent=value.reply;receipt(value.commit_head);working(false);check.hidden=false;return;
   }
   if(['AWAITING_MIND','MIND_SCHEDULED'].includes(value.status)){
    reply.textContent='Thinking…';working(true);check.hidden=true;poll=setTimeout(()=>saved(id),450);return;
   }
   working(value.status!=='STASIS');check.hidden=false;receipt(null);
   reply.textContent=value.status==='STASIS'?'The resident is in stasis.':'This request needs operator review; no response was released.';
  }catch(error){
   if(id!==requestId)return;
   if(error.httpStatus===401)element('reconnect').hidden=false;
   working(true);check.hidden=false;receipt(null);reply.textContent='The outcome is not yet known. Check the saved response; the message will not be resent.';
  }
 }
 send.addEventListener('click',async()=>{
  const user=element('message').value;
  if(busy||!active||!user.trim())return;
  if(new TextEncoder().encode(user).length>16384){reply.textContent='Use a message up to 16 KiB.';return;}
  clearTimeout(poll);requestId='skin-user-'+crypto.randomUUID();const id=requestId;
  try{sessionStorage.setItem('anchor-studio-resident-request',requestId);}catch{}
  working(true);check.hidden=true;reply.textContent='Sending to the resident…';receipt(null);
  try{
   const value=await api('conversation',{user,request_id:id});if(id!==requestId)return;
   if(value.status==='COMMITTED'){reply.textContent=value.reply;receipt(value.commit_head);working(false);check.hidden=false;}
   else await saved();
  }catch{if(id!==requestId)return;reply.textContent='Delivery is uncertain. Check the saved response; the message will not be resent.';check.hidden=false;}
  status();
 });
 check.addEventListener('click',()=>{reply.textContent='Checking the saved response…';saved();});
 toggle.addEventListener('click',()=>{
  const open=panel.hidden;panel.hidden=!open;toggle.setAttribute('aria-expanded',String(open));
  clearInterval(health);
  if(open){reply.textContent='';receipt(null);if(requestId)working(true);status().then(()=>requestId&&saved());health=setInterval(status,3000);}
 });
 window.addEventListener('pagehide',()=>{clearTimeout(poll);clearInterval(health);},{once:true});
})();
