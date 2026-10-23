/* Reviewed first-surface specimen; independent of optional KPP modules or MIND. */
(() => {
'use strict';
const left=document.getElementById('left'), right=document.getElementById('right');
const operation=document.getElementById('operation'), output=document.getElementById('result');
const key='kpp-example-progressive-calculator-v1';
// Lightweight biological organization, not a MIND or agent:
// CELL = numerical operations; TISSUE = combine operations;
// ORGAN = calculate and retain output; APPLICATION = this interactive DOM.
const CELLS=Object.freeze({add:(x,y)=>x+y, subtract:(x,y)=>x-y});
const ARITHMETIC_TISSUE=Object.freeze({evaluate:(op,x,y)=>CELLS[op](x,y)});

try {
 const saved=JSON.parse(localStorage.getItem(key)||'null');
 if(saved&&typeof saved==='object') {
  if(typeof saved.left==='string')left.value=saved.left;
  if(typeof saved.right==='string')right.value=saved.right;
  if(['add','subtract'].includes(saved.operation))operation.value=saved.operation;
  if(typeof saved.result==='string')output.textContent=saved.result;
 }
} catch(_) { /* Storage not required for basic calculation. */ }
function save() {
 try { localStorage.setItem(key,JSON.stringify({left:left.value,right:right.value,operation:operation.value,result:output.textContent})); }
 catch(_) { /* Not all hosts provide persistence. */ }
}
function render(result) {
 output.textContent=String(result);
 save();
}
document.getElementById('calculator').addEventListener('submit',event=>{
 event.preventDefault();
 if(left.value.trim()===''||right.value.trim()==='') {render('Both numbers required');return;}
 const x=Number(left.value), y=Number(right.value);
 if(!Number.isFinite(x)||!Number.isFinite(y)) {render('Invalid input');return;}
 render(ARITHMETIC_TISSUE.evaluate(operation.value,x,y));
});
for(const field of [left,right,operation])field.addEventListener('change',save);
window.CalculatorBody=Object.freeze({read:()=>output.textContent,render});
window.KPPBody=Object.freeze({
 snapshot:()=>({left:left.value,right:right.value,operation:operation.value,result:output.textContent}),
 restore(state) {
  if(!state||![state.left,state.right,state.result].every(value=>typeof value==='string')||!['add','subtract'].includes(state.operation))throw new Error('Invalid calculator snapshot');
  left.value=state.left;right.value=state.right;operation.value=state.operation;output.textContent=state.result;save();
 }
});
})();
