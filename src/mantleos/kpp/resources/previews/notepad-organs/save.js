/* Save contract: {text, filename} -> download initiation or explicit failure. */
window.KPP.define('save',ctx=>{
 'use strict';
 const app=window.NotepadBody,status=document.getElementById('save-status');
 const pending=new Map();
 function release(href) {
  const timer=pending.get(href);
  if(timer!==undefined){clearTimeout(timer);pending.delete(href);URL.revokeObjectURL(href);}
 }
 ctx.cleanup(()=>{for(const href of [...pending.keys()])release(href);});
 function save(input) {
  let href;
  try {
   if(typeof input.text!=='string'||typeof input.filename!=='string')throw new Error('Invalid Save input');
   const blob=new Blob([input.text],{type:'text/plain;charset=utf-8'});
   href=URL.createObjectURL(blob);
   pending.set(href,setTimeout(()=>release(href),3000));
   const link=document.createElement('a');link.href=href;link.download=input.filename;
   link.click();
   return Object.freeze({status:'DOWNLOAD_INITIATED',filename:input.filename});
  }catch(error){
   if(href)release(href);
   return Object.freeze({status:'FAILED',error:String(error)});
  }
 }
 ctx.listen(document.getElementById('save'),'click',event=>{
  if(!event.isTrusted||!navigator.userActivation.isActive){status.textContent='Save requires a user action';return;}
  const result=save({text:app.draft(),filename:app.filename()});
  status.textContent=result.status==='DOWNLOAD_INITIATED'?'Download initiated (confirm in browser)':'Save failed: '+result.error;
  document.dispatchEvent(new CustomEvent('kpp:save-result',{detail:result}));
 });
});
