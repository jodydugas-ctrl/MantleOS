'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),{partition,validate}=require('./conditions.cjs');
const spec=(conditions,extra={})=>({schema:'studio.if/1',combinator:'and',caseSensitive:true,continueOnFail:false,conditions,...extra});
const n=(operation,value=10)=>({field:'score',type:'number',operation,value});
const items=(...values)=>values.map(score=>({json:{score}}));
test('number boundary and stable input pairing',()=>{
 const input=items(9,10,11),copy=JSON.stringify(input),r=partition(spec([n('gte')]),input);
 assert.deepEqual(r.true.map(x=>x.json.score),[10,11]);assert.deepEqual(r.false.map(x=>x.json.score),[9]);
 assert.deepEqual(r.true.map(x=>x.pairedItem.item),[1,2]);assert.equal(JSON.stringify(input),copy);
});
test('strict types reject numeric strings and booleans rather than coercing',()=>{
 for(const value of ['10',true,{},[1]])assert.throws(()=>partition(spec([n('gte')]),items(value)),/Wrong type/);
});
test('AND/OR short circuit preserves the evaluated error boundary',()=>{
 const conditions=[n('gt',0),{field:'label',type:'string',operation:'equals',value:'yes'}];
 assert.equal(partition(spec(conditions),items(-1)).false.length,1);
 assert.equal(partition(spec(conditions,{combinator:'or'}),items(1)).true.length,1);
 assert.equal(partition(spec(conditions),[{json:{score:2,label:'yes'}}]).true.length,1);
 assert.equal(partition(spec(conditions),[{json:{score:2,label:'no'}}]).false.length,1);
});
test('null, missing and empty values follow distinct inspected strict cases',()=>{
 assert.equal(partition(spec([n('notExists')]),[{json:{}},{json:{score:null}}]).true.length,2);
 assert.equal(partition(spec([{field:'text',type:'string',operation:'empty'}]),[{json:{}},{json:{text:''}}]).true.length,2);
 assert.equal(partition(spec([{field:'flag',type:'boolean',operation:'false'}]),[{json:{flag:false}}]).true.length,1);
 assert.equal(partition(spec([n('exists')]),items(0)).true.length,1);
});
test('case-sensitive string operators and explicit ignore case',()=>{
 const c={field:'label',type:'string',operation:'equals',value:'raven'},i=[{json:{label:'RAVEN'}}];
 assert.equal(partition(spec([c]),i).false.length,1);assert.equal(partition(spec([c],{caseSensitive:false}),i).true.length,1);
 for(const [operation,value] of [['contains','AVE'],['startsWith','RA'],['endsWith','VEN']])assert.equal(partition(spec([{...c,operation,value}]),i).true.length,1);
});
test('continueOnFail routes only failing items to false and preserves explicit pairing',()=>{
 const input=items(11,'bad',9);input[0].pairedItem={item:88};const r=partition(spec([n('gte')],{continueOnFail:true}),input);
 assert.equal(r.true.length,1);assert.equal(r.false.length,2);assert.deepEqual(r.true[0].pairedItem,{item:88});assert.equal(r.errors[0].item,1);
 assert.throws(()=>partition(spec([n('gte')]),input),/Item 1/);
});
test('unknown operations, expression paths and unsafe properties fail explicitly',()=>{
 for(const c of [{...n('regex')},{...n('gt'),field:'score[0]'},{...n('gt'),field:'__proto__.x'},{...n('gt'),type:'dateTime'}])assert.throws(()=>validate(spec([c])));
 assert.throws(()=>validate(spec([])));assert.throws(()=>validate(spec([n('gte')],{typeValidation:'loose'})));
});
test('empty input, missing JSON, size and item limits',()=>{
 assert.deepEqual(partition(spec([n('gte')]),[]),{true:[],false:[],errors:[]});
 assert.throws(()=>partition(spec([n('gte')]),[{}]));assert.throws(()=>partition(spec([n('gte')]),items(...Array(129).fill(5))));
});
test('native messages cannot silently coerce non-JSON values or cycles',()=>{
 for(const score of [NaN,Infinity,undefined,new Date(),()=>1])assert.throws(()=>partition(spec([n('exists')]),items(score)));
 const item={json:{score:10}};item.json.loop=item;assert.throws(()=>partition(spec([n('gte')]),[item]));
 assert.throws(()=>partition(spec([n('gte')]),new Array(3)));
});
test('reference-discovered numeric empty values normalize before strict checks',()=>{
 for(const value of ['', '  ', []]){
  assert.equal(partition(spec([n('empty')]),items(value)).true.length,1);
  assert.equal(partition(spec([n('exists')]),items(value)).false.length,1);
  assert.equal(partition(spec([n('lt',10)]),items(value)).true.length,1);
 }
 assert.equal(partition(spec([n('equals','')]),items(null)).true.length,1);
 assert.throws(()=>partition(spec([n('gte')]),items('10')),/Wrong type/);
});
