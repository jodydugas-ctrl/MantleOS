/* Reviewed managed modules; product-owned JSON state. This is not a JS sandbox. */
(() => {
'use strict';
const definitions=new Map(), active=new Map(), failures=new Map(), seen=new Map();
let revision=0, synchronizing=false, fingerprint=null, recipePin=null;
const body=window.KPPBody;
const validId=id=>typeof id==='string'&&/^[a-z][a-z0-9_-]{0,63}$/.test(id);
function copy(value) {
 function validate(item,ancestors,depth) {
  if(depth>128)throw new Error('Body state nesting exceeds json-body/1');
  if(item===null||typeof item==='string'||typeof item==='boolean')return;
  if(typeof item==='number'&&Number.isFinite(item))return;
  if(typeof item!=='object'||ancestors.has(item)||(!Array.isArray(item)&&![Object.prototype,null].includes(Object.getPrototypeOf(item))))throw new Error('Body state must contain finite plain JSON data');
  ancestors.add(item);for(const child of Object.values(item))validate(child,ancestors,depth+1);ancestors.delete(item);
 }
 if(!value||Array.isArray(value)||typeof value!=='object')throw new Error('Body state must be a JSON object');
 validate(value,new Set(),0);
 const encoded=JSON.stringify(value);
 if(typeof encoded!=='string'||new TextEncoder().encode(encoded).byteLength>8388608)throw new Error('Body snapshot exceeds JSON state contract');
 return JSON.parse(encoded);
}
function capture() {
 if(!body||typeof body.snapshot!=='function'||typeof body.restore!=='function')throw new Error('Missing json-body/1 state adapter');
 return copy(body.snapshot());
}
function restore(value) {body.restore(copy(value));}
function gate() {
 for(const node of document.querySelectorAll('[data-requires]')) {
  node.disabled=!(node.dataset.requires||'').split(/\s+/).filter(Boolean).every(id=>active.has(id));
  node.setAttribute('aria-disabled',String(node.disabled));
 }
}
function announce(phase='BUILDING') {
 const node=document.getElementById('kpp-progress');
 if(node)node.textContent=`${phase} · ${active.size} extensions active${failures.size?' · module issue':''}`;
 document.dispatchEvent(new CustomEvent('kpp:ready',{detail:{modules:[...active.keys()],revision,failures:[...failures.keys()]}}));
 gate();
}
function cleanup(record) {
 const errors=[];
 for(const undo of [...record.undo].reverse()) {try {undo();}catch(error){errors.push(String(error));}}
 record.undo.length=0;
 return errors;
}
function withdraw(id,preserve=true) {
 let before;
 if(preserve){try{before=capture();}catch(error){failures.set(id,'Cannot snapshot withdrawal: '+String(error));}}
 for(const [other,record] of [...active].reverse())if(record.depends.includes(id))withdraw(other,false);
 const record=active.get(id);
 if(record) {
  const errors=cleanup(record);active.delete(id);
  if(errors.length)failures.set(id,'Cleanup failed: '+errors.join('; '));
 }
 if(before!==undefined){try{restore(before);}catch(error){failures.set(id,'Withdrawal state restore failed: '+String(error));}}
}
function failed(id,record,before,error) {
 withdraw(id,false);
 const errors=cleanup(record);
 try {restore(before);}catch(recoveryError){errors.push('State restore failed: '+String(recoveryError));}
 failures.set(id,String(error)+(errors.length?' · '+errors.join('; '):''));
 announce();
}
function context(id,record) {
 return Object.freeze({
  listen(node,event,handler,options) {
   if(!node||typeof node.addEventListener!=='function'||typeof handler!=='function'||handler.constructor!==Function)throw new Error('Managed listeners require synchronous functions');
   const wrapped=eventValue=>{
    let before;
    try {
     before=capture();
     const result=handler(eventValue);
     if(result&&typeof result.then==='function')throw new Error('Managed handlers must be synchronous; product-owned asynchronous work handles its own errors');
    }catch(error){if(before!==undefined)failed(id,record,before,error);else{withdraw(id);failures.set(id,String(error));announce();}}
   };
   node.addEventListener(event,wrapped,options);
   record.undo.push(()=>node.removeEventListener(event,wrapped,options));
  },
  property(node,name,value) {
   if(!node||!['textContent','value','checked','hidden','title'].includes(name))throw new Error('Unsupported managed property');
   let properties=record.properties.get(node);
   if(!properties){properties=new Set();record.properties.set(node,properties);}
   if(!properties.has(name)){const previous=node[name];record.undo.push(()=>{node[name]=previous;});properties.add(name);}
   node[name]=value;
  },
  append(parent,node) {
   if(!parent||!node||node.parentNode)throw new Error('Managed insertion needs an unattached node');
   record.undo.push(()=>node.remove());parent.appendChild(node);
  },
  cleanup(callback) {
   if(typeof callback!=='function')throw new Error('Cleanup must be callable');record.undo.push(callback);
  }
 });
}
window.KPP=Object.freeze({
 define(id,activate) {
  const script=document.currentScript;
  if(!validId(id)||typeof activate!=='function'||activate.constructor!==Function||!script||script.dataset.kppModule!==id||definitions.has(id))throw new Error('Managed module declaration requires synchronous activation');
  definitions.set(id,activate);
 },
 has:id=>active.has(id),
 status:()=>({revision,active:[...active.keys()],failed:Object.fromEntries(failures)}),
 exportState:()=>{
  if(!fingerprint)throw new Error('Wait for source-bound preview synchronization before exporting');
  return {schema:'kpp.browser-state/1',profile:'json-body/1',recipe_sha256:recipePin,fingerprint,body:copy(capture())};
 },
 root:document.getElementById('app')
});
function loadScript(mod) {
 return new Promise((resolve,reject)=>{
  const script=document.createElement('script');
  script.dataset.kppModule=mod.id;
  script.src='/modules/'+encodeURIComponent(mod.id)+'.js';
  if(!/^[a-f0-9]{64}$/.test(mod.sha256)){reject(new Error('Missing source pin'));return;}
  const bytes=mod.sha256.match(/../g).map(s=>String.fromCharCode(parseInt(s,16))).join('');
  script.integrity='sha256-'+btoa(bytes);script.crossOrigin='anonymous';
  const timer=setTimeout(()=>{script.remove();reject(new Error('Module load timeout'));},5000);
  script.onload=()=>{clearTimeout(timer);script.remove();definitions.has(mod.id)?resolve():reject(new Error('Module did not define its managed activation'));};
  script.onerror=()=>{clearTimeout(timer);script.remove();reject(new Error('Script failed integrity/loading'));};
  document.head.appendChild(script);
 });
}
async function activate(mod) {
 if(active.has(mod.id)||failures.has(mod.id)||!mod.depends.every(id=>active.has(id)))return;
 let before;
 const record={depends:mod.depends,undo:[],properties:new WeakMap()};
 try {
  if(!definitions.has(mod.id))await loadScript(mod);
  // Capture after fetch, immediately before activation: typing during load is retained.
  before=capture();
  const result=definitions.get(mod.id)(context(mod.id,record));
  if(result&&typeof result.then==='function')throw new Error('Managed activation must be synchronous');
  if(JSON.stringify(capture())!==JSON.stringify(before))throw new Error('Module activation changed existing Body state');
  active.set(mod.id,record);announce();
 }catch(error){if(before!==undefined)failed(mod.id,record,before,error);else{cleanup(record);failures.set(mod.id,String(error));announce();}}
}
async function poll() {
 if(synchronizing)return;
 synchronizing=true;
 try {
  const response=await fetch('/snapshot',{cache:'no-store'});
  if(!response.ok)throw new Error('Preview snapshot unavailable');
  const snapshot=await response.json();
  if(snapshot.revision<revision)throw new Error('Stale revision');
  const desired=new Set(snapshot.modules.filter(mod=>mod.enabled).map(mod=>mod.id));
  for(const id of [...active.keys()].reverse())if(!desired.has(id))withdraw(id);
  for(const mod of snapshot.modules) {
   if(seen.has(mod.id)&&seen.get(mod.id)!==mod.sha256)throw new Error('Existing module source changed');
   seen.set(mod.id,mod.sha256);
   if(!mod.enabled)failures.delete(mod.id);
  }
  revision=snapshot.revision;
  fingerprint=snapshot.fingerprint;recipePin=snapshot.recipe_sha256;
  for(const mod of snapshot.modules)if(mod.enabled)await activate(mod);
  const node=document.getElementById('kpp-anchors');
  if(node)node.textContent=`Anchors accepted: ${snapshot.report.accepted}/${snapshot.report.required} · ${snapshot.phase}`;
  announce(snapshot.phase);
 }catch(error) {
  const node=document.getElementById('kpp-progress');
  if(node)node.textContent='Preview updates paused; current Body remains usable';
 }finally{synchronizing=false;setTimeout(poll,750);}
}
async function start() {
 try {
  capture();
  const response=await fetch('/body-state',{cache:'no-store'});
  if(!response.ok)throw new Error('Restored Body state unavailable');
  const initial=await response.json();
  if(initial.schema!=='kpp.browser-state/1')throw new Error('Unsupported restored state schema');
  if(initial.body!==null)restore(initial.body);
  announce();poll();
 }catch(error){const node=document.getElementById('kpp-progress');if(node)node.textContent='Unsupported preview Body: '+String(error);}
}
start();
})();
