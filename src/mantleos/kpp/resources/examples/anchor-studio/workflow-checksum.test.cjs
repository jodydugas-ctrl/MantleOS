'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {calculateWorkflowChecksum,FIELDS}=require('./workflow-checksum.cjs');
const {fixture}=require('./workflow-checksum-fixtures.cjs');
const vectors=require('./workflow-checksum-vectors.json');
test('257 synthetic projections and reordered inputs preserve the pinned reference results',async()=>{
 assert.equal(vectors.schema,'studio.workflow-checksum-vectors/1');assert.deepEqual(FIELDS,vectors.fields);assert.equal(vectors.cases.length,257);
 for(const {index,sha256} of vectors.cases){
  const value=fixture(index);assert.equal(await calculateWorkflowChecksum(value),sha256);
  assert.equal(await calculateWorkflowChecksum(Object.fromEntries(Object.entries(value).reverse())),sha256);
 }
});
test('selected content changes the binding; version and identity require independent CAS',async()=>{
 const baseline={name:'Draft',nodes:[],connections:{},settings:{}},hash=await calculateWorkflowChecksum(baseline);
 assert.equal(await calculateWorkflowChecksum({...baseline,revision:'changed',id:'other',versionId:'other'}),hash);
 assert.notEqual(await calculateWorkflowChecksum({...baseline,isArchived:true}),hash);
 assert.notEqual(await calculateWorkflowChecksum({...baseline,settings:{timezone:'UTC'}}),hash);
 await assert.rejects(calculateWorkflowChecksum({...baseline,settings:{value:Infinity}}),/FINITE_JSON/);
 await assert.rejects(calculateWorkflowChecksum({...baseline,nodes:[()=>{}]}),/JSON_WORKFLOW/);
});
test('special-key compatibility cannot establish complete document integrity',async()=>{
 const first={name:'Draft',nodes:[],connections:{},settings:JSON.parse('{"__proto__":{"retained":"one"}}')};
 const second={...first,settings:JSON.parse('{"__proto__":{"retained":"two"}}')};
 assert.equal(await calculateWorkflowChecksum(first),await calculateWorkflowChecksum(second));assert.notEqual(JSON.stringify(first),JSON.stringify(second));
 assert.equal(Object.hasOwn(first.settings,'__proto__'),true);assert.equal(Object.prototype.retained,undefined);
});
