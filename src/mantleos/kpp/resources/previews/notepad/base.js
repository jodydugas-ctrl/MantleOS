/* Product Body: owns editor/draft state. Shared KPP runtime owns module delivery. */
(() => {
'use strict';
const editor=document.getElementById('notes'), status=document.getElementById('save-status');
const key='kpp-notes-draft';
let filename='notes.txt';
try {const saved=localStorage.getItem(key);if(saved!==null)editor.value=saved;}
catch(error){status.textContent='Recovery unavailable; copy draft before closing';}
editor.addEventListener('input',()=>{
 try {localStorage.setItem(key,editor.value);status.textContent='Draft cached locally';}
 catch(error){status.textContent='Draft not cached; storage unavailable';}
});
window.NotepadBody=Object.freeze({editor,draft:()=>editor.value,
 filename:()=>filename,setFilename:value=>{filename=value;},
 restore(value){editor.value=value;editor.dispatchEvent(new Event('input',{bubbles:true}));}});
window.KPPBody=Object.freeze({
 snapshot:()=>({text:editor.value,start:editor.selectionStart,end:editor.selectionEnd,
               direction:editor.selectionDirection,scrollTop:editor.scrollTop,filename}),
 restore(state) {
  if(!state||typeof state.text!=='string'||typeof state.filename!=='string'||!Number.isInteger(state.start)||!Number.isInteger(state.end))throw new Error('Invalid Notepad snapshot');
  window.NotepadBody.restore(state.text);filename=state.filename;
  editor.setSelectionRange(state.start,state.end,state.direction);editor.scrollTop=state.scrollTop;
 }
});
const last={};
for(const element of document.querySelectorAll('[data-area]')) {
 element.addEventListener('click',()=>{
  if(!document.getElementById('observe').checked)return;
  const area=element.dataset.area,now=Date.now();if(now-(last[area]||0)<3000)return;last[area]=now;
  fetch('/activity',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({area})}).catch(()=>{});
 });
}
fetch('/priority').then(r=>r.json()).then(data=>{
 document.getElementById('chase').textContent=data.chase.length?'Next Chase: '+data.chase[0].id:'No remaining Anchors';
}).catch(()=>{document.getElementById('chase').textContent='Live priority unavailable';});
})();
