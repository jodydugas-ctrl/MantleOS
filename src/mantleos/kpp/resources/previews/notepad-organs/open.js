/* Reviewed, user-initiated files; asynchronous reads handle their own failures. */
window.KPP.define('open',ctx=>{
 const app=window.NotepadBody,picker=document.getElementById('filepicker'),status=document.getElementById('save-status');
 let readGeneration=0;
 ctx.cleanup(()=>{readGeneration++;});
 ctx.listen(document.getElementById('open'),'click',()=>picker.click());
 ctx.listen(picker,'change',()=>{
  const file=picker.files&&picker.files[0];if(!file)return;
  if(file.size>2000000){window.alert('File exceeds 2MB limit');picker.value='';return;}
  if(app.draft()&&!window.confirm('Replace the current draft with this file?')){picker.value='';return;}
  const generation=++readGeneration,draftBefore=app.draft();
  file.arrayBuffer().then(bytes=>{
   const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
   // Withdrawn extensions must not complete a pending user effect later.
   if(generation!==readGeneration||!window.KPP.has('open'))return;
   if(app.draft()!==draftBefore){status.textContent='Draft changed during file read; select the file again';return;}
   app.restore(text);app.setFilename(file.name||app.filename());status.textContent='Opened '+app.filename();
  }).catch(error=>{if(generation===readGeneration&&window.KPP.has('open'))status.textContent='Open failed: '+String(error);})
    .finally(()=>{if(generation===readGeneration)picker.value='';});
 });
});
