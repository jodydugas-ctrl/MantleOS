"""Self-contained offline report. Lens changes filter the same embedded graph."""
import json
from .common import atomic_text, ScanError
from .scanner import verify_report
from .planner import plan


def render_report(report, registry, destination):
    verify_report(report)
    data = json.dumps({"report": report, "lenses": registry.lenses(), "plan": plan(report)}, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    atomic_text(destination, TEMPLATE.replace("__SCAN_DATA__", data))


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SCAN / Optimizer · Evidence atlas</title>
<style>
:root{color-scheme:light;--ink:#172d38;--muted:#526977;--paper:#f3f6f5;--line:#d7e2df;--accent:#087b70}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 system-ui,sans-serif}header{background:#102d36;color:#e8f8f4;padding:32px max(24px,calc((100vw - 1280px)/2))}header small{letter-spacing:.2em;color:#79d3bd}h1{font-size:36px;line-height:1.15;margin:9px 0}header p{margin:10px 0;color:#c0d8d8;max-width:900px}main{max-width:1328px;margin:auto;padding:24px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:22px}.stat,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:18px}.stat strong{display:block;font-size:26px}.stat span{color:var(--muted);font-size:13px}nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}button,input{font:inherit}button{border:1px solid #b8cdca;background:white;color:var(--ink);padding:9px 16px;border-radius:8px;cursor:pointer}button[aria-pressed=true]{background:var(--accent);color:white;border-color:var(--accent)}button:hover{border-color:var(--accent)}button:focus-visible,input:focus-visible{outline:3px solid #d69c36;outline-offset:2px}input{border:1px solid #b8cdca;padding:10px 12px;border-radius:8px;width:100%;margin:12px 0}.grid{display:grid;grid-template-columns:2fr 1fr;gap:16px}.panel h2{font-size:19px;margin:0 0 8px}.caption,.muted{color:var(--muted);font-size:13px}.map{width:100%;height:430px;display:block;background:#f7faf9;border-radius:8px}.node{cursor:pointer}.node:focus{outline:none}.node:focus circle{stroke:#d69c36;stroke-width:4}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 ui-monospace,monospace;background:#f5f8f7;padding:12px;border-radius:8px;max-height:430px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}th{color:var(--muted)}tr[data-id]{cursor:pointer}tr[data-id]:hover{background:#eaf6f2}.tablewrap{max-height:380px;overflow:auto;margin-top:14px}.lower{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}.card{border-left:3px solid #6aaa94;padding:6px 12px;margin:14px 0}.card p{margin:4px 0;font-size:13px}.tag{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#795609;background:#fff1cf;padding:3px 7px;border-radius:4px}.id{font-family:monospace;font-size:11px;overflow-wrap:anywhere}footer{padding:24px 0;color:var(--muted);font-size:12px}ul{padding-left:22px}@media(max-width:850px){.grid,.lower{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr}h1{font-size:28px}}
</style></head><body>
<header><small>SCAN / OPTIMIZER</small><h1>One system. Several ways to see it.</h1><p>Inspect structure, follow possible routes, and find repeated work. Every lens uses the same evidence; each improvement still needs a measured experiment.</p><span class="tag">Static evidence · source not executed</span></header>
<main><section class="stats" aria-label="Scan summary" id="stats"></section>
<nav id="lenses" aria-label="Scan lenses"></nav><div id="lensDescription" class="muted"></div>
<label for="search">Find a file, symbol, or record type</label><input id="search" placeholder="For example: loop, process, app.py" type="search">
<section class="grid"><div class="panel"><h2>Evidence map</h2><div class="caption" id="mapCaption"></div><svg class="map" id="map" viewBox="0 0 760 430" role="img" aria-label="Filtered static graph"></svg><div class="tablewrap"><table><thead><tr><th>Kind</th><th>Name</th><th>Location</th></tr></thead><tbody id="rows"></tbody></table></div><p class="caption" id="tableCaption"></p></div>
<aside class="panel"><h2>Source evidence</h2><p class="muted">Select a node or row. IDs, source hashes, locations, and evidence classes remain unchanged across lenses.</p><pre id="details">Select a record to inspect it.</pre><h2>What this map means</h2><p class="muted">Lines represent observed ownership or syntactic enclosure, or explicitly inferred possible calls/imports. Position and size are for readability. They do not measure traffic, importance, cost, or biological function.</p></aside></section>
<section class="lower"><div class="panel"><h2>Optimization hypotheses</h2><p class="muted">Repetition suggests where to measure. It does not prove a bottleneck or safe reuse.</p><div id="opportunities"></div></div><div class="panel"><h2>Coverage and limits</h2><div id="gaps"></div><pre id="scope"></pre></div></section>
<footer>Local report · no network requests · <span id="identity" class="id"></span></footer></main>
<script type="application/json" id="scan-data">__SCAN_DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('scan-data').textContent),r=data.report,g=r.graph;
const el=id=>document.getElementById(id),txt=(tag,text,parent,cls)=>{let n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;parent.appendChild(n);return n};
let active='organic';
for(const [number,label] of [[g.files.length,'Files inventoried'],[g.nodes.length,'Evidence records'],[g.gaps.length,'Coverage gaps'],[r.run.cache_hits,'Reused file analyses']]){let d=txt('div','',el('stats'),'stat');txt('strong',number,d);txt('span',label,d)}
for(const [name,spec] of Object.entries(data.lenses)){const b=txt('button',name,el('lenses'));b.dataset.lens=name;b.addEventListener('click',()=>{active=name;draw()})}
el('identity').textContent='Graph '+r.graph_digest;
el('scope').textContent=JSON.stringify(g.scope,null,2);
if(!g.gaps.length)txt('p','No recorded gaps within the declared exclusions and scan limits. This is not proof of complete semantics.',el('gaps'),'muted');
for(const gap of g.gaps.slice(0,50))txt('p',gap.path+' — '+gap.reason,el('gaps'),'muted');
if(g.gaps.length>50)txt('p','Showing 50 of '+g.gaps.length+' gaps. See the JSON report for all gaps.',el('gaps'));
for(const o of data.plan.opportunities.slice(0,12)){let d=txt('div','',el('opportunities'),'card');txt('span','Unmeasured hypothesis',d,'tag');txt('p',o.observation,d);txt('p',o.path+':'+o.line,d,'id');txt('p',o.next_measurement,d)}
if(!data.plan.opportunities.length)txt('p','No loop-based hypotheses in this scan. That does not establish that the system is optimal.',el('opportunities'),'muted');
if(data.plan.opportunities.length>12)txt('p','Showing 12 of '+data.plan.opportunities.length+' hypotheses; use the plan command for the full bounded list.',el('opportunities'),'muted');
function select(n){el('details').textContent=JSON.stringify(n,null,2)}
const NS='http://www.w3.org/2000/svg';
function svg(tag,attrs,parent){let n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);parent.appendChild(n);return n}
function draw(){
 const s=data.lenses[active],q=el('search').value.toLowerCase();
 for(const b of el('lenses').children)b.setAttribute('aria-pressed',b.dataset.lens===active);
 el('lensDescription').textContent=s.description;
 const nodes=g.nodes.filter(n=>(!s.kinds.length||s.kinds.includes(n.kind))&&Math.max(n.loop_depth,n.attributes.nested_depth||0)>=s.min_loop_depth&&(!q||(n.name+' '+n.path+' '+n.kind).toLowerCase().includes(q)));
 const shown=nodes.slice(0,72),ids=new Set(shown.map(n=>n.id));const edges=g.edges.filter(e=>ids.has(e.src)&&ids.has(e.dst));
 el('mapCaption').textContent='Showing '+shown.length+' of '+nodes.length+' matching records and '+Math.min(edges.length,240)+' of '+edges.length+' edges between shown records. Schematic layout.';
 el('map').replaceChildren();let positions=new Map(),columns=8;
 shown.forEach((n,i)=>positions.set(n.id,{x:50+(i%columns)*94,y:35+Math.floor(i/columns)*44}));
 for(const e of edges.slice(0,240)){let a=positions.get(e.src),b=positions.get(e.dst);svg('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:e.kind.startsWith('possible')?'#bf914b':'#b8ceca','stroke-width':1,'stroke-dasharray':e.kind.startsWith('possible')?'4 3':'none'},el('map'))}
 for(const n of shown){let p=positions.get(n.id),group=svg('g',{class:'node',tabindex:0,role:'button','aria-label':n.kind+' '+n.name},el('map'));svg('circle',{cx:p.x,cy:p.y,r:n.kind==='module'?10:7,fill:n.kind==='loop'?'#b77a25':n.kind==='call'?'#478ab0':'#168472',stroke:'white','stroke-width':2},group);let title=svg('title',{},group);title.textContent=n.kind+' '+n.name+' · '+n.path+':'+n.line;let label=svg('text',{x:p.x,y:p.y+19,'text-anchor':'middle','font-size':8,fill:'#415c68'},group);label.textContent=n.name.length>15?n.name.slice(0,13)+'…':n.name;group.addEventListener('click',()=>select(n));group.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(n)}})}
 el('rows').replaceChildren();for(const n of nodes.slice(0,200)){let tr=txt('tr','',el('rows'));tr.dataset.id=n.id;tr.tabIndex=0;txt('td',n.kind,tr);txt('td',n.name,tr);txt('td',n.path+(n.line?':'+n.line:''),tr);tr.addEventListener('click',()=>select(n));tr.addEventListener('keydown',e=>{if(e.key==='Enter')select(n)})}
 el('tableCaption').textContent='Table shows '+Math.min(nodes.length,200)+' of '+nodes.length+' matching records. Full records are available in latest-scan.json.';
}
el('search').addEventListener('input',draw);draw();
</script></body></html>'''
