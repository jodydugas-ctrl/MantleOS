/* Managed editing capability: resources unwind on withdrawal or handler failure. */
window.KPP.define('edit',ctx=>{
 const app=window.NotepadBody,editor=app.editor,counter=document.getElementById('counter');
 const update=()=>{counter.textContent=editor.value.length+' characters';};
 ctx.cleanup(()=>{counter.textContent='Editor preview';});
 ctx.listen(document.getElementById('selectall'),'click',()=>{editor.focus();editor.select();});
 ctx.listen(document.getElementById('clear'),'click',()=>{
  if(editor.value&&!window.confirm('Clear the entire draft?'))return;
  app.restore('');update();editor.focus();
 });
 ctx.listen(editor,'input',update);update();
});
