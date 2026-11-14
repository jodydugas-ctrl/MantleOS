/* A projection of the canonical project. Canvas edits are drafts until save. */
'use strict';
const ui=id=>document.getElementById(id),svgNS='http://www.w3.org/2000/svg';
let selectedApp=null,canvasScale=1,dragging=null;
function showView(view){for(const name of ['canvas','contracts','verification','activity'])ui(name+'View').hidden=name!==view;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
function markDraft(){ui('dirty').textContent='Unsaved draft';}
function currentProject(){return JSON.parse(ui('project').value);}
function svg(tag,attrs,text){const e=document.createElementNS(svgNS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;}
function fitCanvas(){canvasScale=1;renderWorkspace();}
function zoomCanvas(by){canvasScale=Math.min(3,Math.max(.4,canvasScale*by));renderWorkspace();}
function inspectApp(id){selectedApp=id;const p=currentProject(),d=p.recipe.anchor_design,a=d.applications.find(x=>x.id===id),el=ui('selection');el.replaceChildren();if(!a)return;const title=document.createElement('h3');title.textContent=a.id;el.append(title);for(const text of [a.type,a.attributes.responsibility||'No responsibility declared',a.singularity,'State: '+(d.state.filter(s=>s.owner===id).map(s=>s.id).join(', ')||'None declared'),'Guards: '+(d.effects.filter(s=>s.guard===id).map(s=>s.id).join(', ')||'None declared')]){const para=document.createElement('p');para.textContent=text;el.append(para);}renderWorkspace();}
function renderWorkspace(){
 let p;try{p=currentProject();}catch{return;}const d=p.recipe.anchor_design,g=ui('graph');if(!g)return;g.replaceChildren();ui('projectName').textContent=p.id;ui('graphSummary').textContent=d.applications.length+' applications · '+d.flows.length+' typed relationships';
 const pos={};d.applications.forEach((a,i)=>pos[a.id]=p.layout[a.id]||[120+i*190,220]);
 const points=Object.values(pos);if(!points.length){g.setAttribute('viewBox','0 0 1000 520');return;}
 const minX=Math.min(...points.map(p=>p[0]))-95,minY=Math.min(...points.map(p=>p[1]))-150;
 const width=Math.max(720,Math.max(...points.map(p=>p[0]))-minX+150),height=Math.max(430,Math.max(...points.map(p=>p[1]))-minY+170);
 g.setAttribute('viewBox',`${minX-(width/canvasScale-width)/2} ${minY-(height/canvasScale-height)/2} ${width/canvasScale} ${height/canvasScale}`);
 const defs=svg('defs',{}),marker=svg('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#a9adb7'}));defs.append(marker);g.append(defs);
 for(const f of d.flows){const a=pos[f.from],b=pos[f.to];if(!a||!b)continue;const x=a[0]+45,y=a[1],tx=b[0]-45,ty=b[1],bend=Math.max(45,Math.abs(tx-x)/2);g.append(svg('path',{d:`M${x},${y} C${x+bend},${y} ${tx-bend},${ty} ${tx},${ty}`,class:'edge','marker-end':'url(#arrow)'}));g.append(svg('text',{x:(x+tx)/2,y:(y+ty)/2-14,'text-anchor':'middle',class:'edge-label'},f.relationship.slice(0,42)));}
 for(const a of d.applications){const [x,y]=pos[a.id],node=svg('g',{transform:`translate(${x},${y})`,class:'graph-node',role:'button',tabindex:0,'aria-label':a.id+' '+a.type});node.append(svg('rect',{x:-44,y:-44,width:88,height:88,rx:17,fill:'#fff',stroke:selectedApp===a.id?'#8c76d1':'#d5d8df','stroke-width':selectedApp===a.id?3:1.5}));node.append(svg('text',{x:0,y:8,'text-anchor':'middle',class:'node-icon'},{BlackHole:'↘',Neutral:'⇄',WhiteHole:'◇'}[a.type]||'○'));for(const sx of [-45,45])node.append(svg('circle',{cx:sx,cy:0,r:6,fill:'white',stroke:'#b6bbc5'}));node.append(svg('text',{x:0,y:68,'text-anchor':'middle',class:'node-label'},a.id));node.append(svg('text',{x:0,y:87,'text-anchor':'middle',class:'node-type'},a.type));node.addEventListener('click',()=>inspectApp(a.id));node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspectApp(a.id);}});node.addEventListener('pointerdown',e=>{if(e.button!==0)return;dragging={id:a.id,node,start:[e.clientX,e.clientY],origin:[x,y]};g.setPointerCapture(e.pointerId);});g.append(node);}
}
ui('graph').addEventListener('pointermove',e=>{if(!dragging||Math.hypot(e.clientX-dragging.start[0],e.clientY-dragging.start[1])<3)return;const matrix=ui('graph').getScreenCTM().inverse(),start=new DOMPoint(...dragging.start).matrixTransform(matrix),now=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix);dragging.position=[Math.round(dragging.origin[0]+now.x-start.x),Math.round(dragging.origin[1]+now.y-start.y)];dragging.node.setAttribute('transform',`translate(${dragging.position})`);});
ui('graph').addEventListener('pointerup',()=>{if(!dragging)return;const d=dragging;dragging=null;if(d.position){const p=currentProject();p.layout[d.id]=d.position;ui('project').value=JSON.stringify(p,null,2);markDraft();renderWorkspace();}else inspectApp(d.id);});
ui('graph').addEventListener('pointercancel',()=>{dragging=null;renderWorkspace();});
function studioStatus(s){ui('personaName').textContent=s.persona?.name||'Resident AppAI (verification pending)';ui('life').textContent=s.phase||'Unavailable';ui('heartCount').textContent=s.heartbeats??'—';ui('limbCount').textContent=s.limbs?.length??'—';const automatic=s.mind_route==='OPENROUTER_OWNER_CONFIGURED';ui('mindState').textContent=s.pending_mind?(automatic?'THINKING':'AWAITING HOST'):(automatic?'AUTOMATIC':'SUPERVISED');ui('mindRouteDescription').textContent=automatic?'Configured MIND · replies appear after durable commit.':'Supervised chat bridge · replies appear after durable commit.';const cards=ui('limbCards');cards.replaceChildren();for(const m of s.limb_runtime?.members||[]){const card=document.createElement('div');card.className='limb';card.textContent=m.id+' · '+(m.enabled?'enabled':'disabled');const detail=document.createElement('small');detail.textContent=m.identity;card.append(detail);cards.append(card);}}
async function exportSavedRecipe(){
 const button=ui('exportRecipe'),status=ui('recipeExportStatus');
 button.disabled=true;
 status.textContent='Reading the saved project…';
 try{
  const result=await api('recipe-export');
  if(result.error)throw Error(result.error);
  const url=URL.createObjectURL(new Blob([result.source],{type:'application/json;charset=utf-8'}));
  const link=document.createElement('a');
  link.href=url;
  link.download=result.id+'.json';
  link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
  status.textContent='Downloaded the Recipe from saved revision '+result.revision.slice(0,12)+'.';
 }catch(error){
  status.textContent=error.message;
 }finally{
  button.disabled=false;
 }
}
ui('exportRecipe').addEventListener('click',exportSavedRecipe);
renderWorkspace();
