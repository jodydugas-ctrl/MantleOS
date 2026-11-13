'use strict';
// Presentation only. All authorized transitions are computed by logical_engine.py.
// Not a model call; browser file read/download are explicit user interactions.
const $ = id => document.getElementById(id);
const editor = $('editor');
let snapshot = null;
let localDraft = false;
let busy = false;
let highlighted = null;

function status(text, bad=false) {
  $('docstatus').textContent = text;
  $('docstatus').style.color = bad ? '#b33030' : '#5b6b7c';
}
function render(state, {preserveDraft=false}={}) {
  snapshot=state;
  if(!preserveDraft){editor.value=state.text;localDraft=false;}
  $('filename').textContent=state.path || 'Untitled · virtual';
  $('dirty').textContent=state.dirty || localDraft ? 'Unsaved' : 'Saved (virtual)';
  $('dirty').classList.toggle('unsaved',!!(state.dirty || localDraft));
  $('counts').textContent=`Rev ${state.revision} · ${state.undo_count} undo / ${state.redo_count} redo`;
}
function showTrace(reply, action='') {
  const tr=$('trace');
  tr.classList.toggle('error',reply.outcome==='REJECTED_BY_GATE'||reply.outcome==='UNDETERMINED');
  const lines=[
    `STIMULUS: ${action || 'view'}`,
    `OUTCOME: ${reply.outcome}`,
    reply.reason ? `REASON: ${reply.reason}` : null,
    reply.trace?.action_clause ? `CLAUSE: ${reply.trace.action_clause}` : null,
    reply.trace?.gate_families?.length ? `GATES: ${reply.trace.gate_families.join(', ')}` : null,
    reply.trace?.participants ? `ANCHORS: ${reply.trace.participants.join(' → ')}` : null,
    reply.trace?.external_effects?.length ? `EFFECTS: ${reply.trace.external_effects.join(', ')} (SIMULATED)` : null,
    reply.result?.kind ? `RESULT: ${JSON.stringify(reply.result)}` : null,
    reply.state ? `DOCUMENT: ${JSON.stringify(reply.state.text)}\nREVISION: ${reply.state.revision}; DIRTY: ${reply.state.dirty}` : null,
    `\nNo model call or actual filesystem/OS clipboard effect.`
  ].filter(Boolean);
  tr.textContent=lines.join('\n');
  status(reply.reason || `Action ${action||'view'}: ${reply.outcome}`,reply.outcome==='REJECTED_BY_GATE');
}
async function api(path,body){
  const init = body===undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
  const res=await fetch(path,init);const data=await res.json();
  if(!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
function pointToCp(offset){return Array.from(editor.value.slice(0,offset)).length;}
function cpToPoint(offset){return Array.from(editor.value).slice(0,offset).join('').length;}
function selection(){return {start:pointToCp(editor.selectionStart),end:pointToCp(editor.selectionEnd)};}
function applySelection(range){
  if(!range)return;
  editor.focus();editor.setSelectionRange(cpToPoint(range[0]),cpToPoint(range[1]));
  highlighted=range;
}
async function send(action,payload, {skipFlush=false}={}) {
  if(busy)return null;
  busy=true;
  try {
    if(!skipFlush && localDraft && action!=='edit') {
      const committed=await api('/api/command',{action:'edit',payload:editor.value});
      render(committed.state);
      if(committed.outcome!=='PREDICTED_FROM_ANCHORS'){showTrace(committed,'edit');return committed;}
    }
    const reply=await api('/api/command',{action,payload});
    render(reply.state);
    showTrace(reply,action);
    if(reply.result?.selection){applySelection(reply.result.selection);}
    return reply;
  } catch(e){status(`Shell error: ${e.message}`,true);$('trace').textContent=String(e);return null;}
  finally{busy=false;}
}
async function flushDraft(){
  if(!localDraft)return true;
  const from=editor.selectionStart,to=editor.selectionEnd;
  const reply=await send('edit',editor.value,{skipFlush:true});
  if(reply?.outcome==='PREDICTED_FROM_ANCHORS')editor.setSelectionRange(from,to);
  return !!reply && reply.outcome==='PREDICTED_FROM_ANCHORS';
}
async function run(action,payload){
  // For range operations, commit pending draft before calculating offsets from committed state.
  if(localDraft && !await flushDraft())return;
  return send(action,payload,{skipFlush:true});
}
editor.addEventListener('input',()=>{
  localDraft=true;
  $('dirty').textContent='Draft (not yet committed)';
  $('dirty').classList.add('unsaved');
  status('Editing local display draft · commits on next command');
});
editor.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='z'){
    e.preventDefault(); run(e.shiftKey?'redo':'undo',null);
  }
});
$('new').addEventListener('click',async()=>{
  if(!await flushDraft())return;
  const discard=snapshot?.dirty ? confirm('Discard the unsaved virtual document changes?') : false;
  if(snapshot?.dirty && !discard)return;
  send('new',{discard},{skipFlush:true});
});
$('open').addEventListener('click',async()=>{if(!await flushDraft())return;$('filepicker').click();});
$('filepicker').addEventListener('change',async e=>{
  const file=e.target.files?.[0];if(!file)return;
  try{
    const text=await file.text();
    const path='/virtual/'+file.name.replace(/[^\w.() -]/g,'_');
    await api('/api/seed-file',{path,text});
    const discard=!!snapshot?.dirty && confirm('Discard unsaved virtual changes before opening the selected file?');
    if(snapshot?.dirty && !discard)return;
    await send('open',{path,discard},{skipFlush:true});
    status(`Opened browser-selected ${file.name} into virtual file storage`);
  }catch(err){status(`Open failed: ${err.message}`,true)}finally{e.target.value='';}
});
$('save').addEventListener('click',async()=>{if(!await flushDraft())return;await send('save',null,{skipFlush:true});});
$('saveas').addEventListener('click',async()=>{
  if(!await flushDraft())return;
  const path=prompt('Choose a VIRTUAL filename (not a disk path):','/virtual/notes.txt');
  if(path===null)return;
  const reply=await send('save-as',{path,overwrite:false},{skipFlush:true});
  if(reply?.outcome==='REJECTED_BY_GATE' && reply.reason?.includes('overwrite')){
    if(confirm('Overwrite the existing virtual file?'))await send('save-as',{path,overwrite:true},{skipFlush:true});
  }
});
$('download').addEventListener('click',async()=>{
  if(!await flushDraft())return;
  const blob=new Blob([editor.value],{type:'text/plain;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');link.href=url;link.download=(snapshot?.path?.split('/').pop()||'anchor-notepad.txt');
  document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),3000);
  status('Browser download requested · disk save not verified');
});
$('undo').addEventListener('click',()=>run('undo',null));
$('redo').addEventListener('click',()=>run('redo',null));
$('copy').addEventListener('click',async()=>{if(!await flushDraft())return;await run('copy',selection());});
$('cut').addEventListener('click',async()=>{if(!await flushDraft())return;await run('cut',selection());});
$('paste').addEventListener('click',async()=>{if(!await flushDraft())return;await run('paste',selection());});
$('selectall').addEventListener('click',()=>run('select-all',null));
function searchArgs(){return {query:$('query').value,match_case:$('matchcase').checked}}
$('find').addEventListener('click',async()=>{if(!await flushDraft())return;const s=selection();await run('find',{...searchArgs(),start:s.end,wrap:true,backwards:false});});
$('replace').addEventListener('click',async()=>{
  if(!await flushDraft())return;
  const s=selection();await run('replace-one',{...searchArgs(),replacement:$('replacement').value,...s});
});
$('replaceall').addEventListener('click',async()=>{
  if(!await flushDraft())return;
  await run('replace-all',{...searchArgs(),replacement:$('replacement').value});
});
$('reset').addEventListener('click',async()=>{
  if(!confirm('Reset the entire virtual Notepad session?'))return;
  try{render((await api('/api/reset',{})).state);$('trace').textContent='Reset complete · no user file changed.';status('Reset virtual session')}catch(err){status(err.message,true)}
});
$('packet').addEventListener('click',async()=>{
  try{
    const packet=(await api('/api/packet')).prompt;
    $('packetview').value=packet;
    try{await navigator.clipboard.writeText(packet);status('LLM interpretation packet copied. No model call was made.');}
    catch{status('Packet displayed below. Select and copy it manually.');}
  }catch(err){status(err.message,true)}
});
async function init(){try{const r=await api('/api/state');render(r.state);status('Ready · virtual file/clipboard effects only')}catch(e){status('Local shell unavailable: '+e.message,true)}}
init();
