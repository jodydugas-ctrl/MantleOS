/* Matched execution against an explicitly provisioned n8n filter library.
 * Installs nothing, starts no provider or server, and supplies no acceptance.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const root=path.resolve(process.argv[2]);
const referencePath=path.join(root,'dist/cjs/node-parameters/filter-parameter.js');
if(JSON.parse(fs.readFileSync(path.join(root,'package.json'))).version!=='2.46.4'||sha(referencePath)!=='c8c5b68a9ab5c2a356a0df62b8069698e81ad8d44aba7e62f41e4091f6ca1d1e')throw Error('Unexpected reference filter source');
const {executeFilter}=require(referencePath),adapterPath=path.join(__dirname,'conditions.cjs'),adapter=require(adapterPath);
const field=(o,p)=>p.split('.').reduce((v,k)=>v!==null&&typeof v==='object'&&Object.hasOwn(v,k)?v[k]:undefined,o);
const cases=[];
for(const [type,ops] of Object.entries(adapter.operations)){
 const values=type==='string'?['Raven','raven','',null,undefined,10]:type==='number'?[-1,0,9,10,11,null,undefined,'10','',false,'  ',[],[1],{}]:[true,false,null,undefined,0,'true'];
 for(const operation of ops)for(const value of values){
  const c={field:'value',type,operation};if(!['exists','notExists','empty','notEmpty','true','false'].includes(operation))c.value=type==='string'?'raven':type==='number'?10:true;
  const spec={schema:'studio.if/1',combinator:'and',caseSensitive:true,continueOnFail:false,conditions:[c]};
  const json={};if(value!==undefined)json.value=value;
  cases.push({name:type+'/'+operation+'/'+(value===undefined?'MISSING':JSON.stringify(value)),spec,json});
 }
}
for(const combinator of ['and','or'])for(const score of [-1,1])for(const label of ['yes',5])cases.push({name:'group/'+combinator+'/'+score+'/'+label,spec:{schema:'studio.if/1',combinator,caseSensitive:true,continueOnFail:false,conditions:[{field:'score',type:'number',operation:'gt',value:0},{field:'label',type:'string',operation:'equals',value:'yes'}]},json:{score,label}});
cases.push({name:'ignore-case',spec:{schema:'studio.if/1',combinator:'and',caseSensitive:false,continueOnFail:false,conditions:[{field:'value',type:'string',operation:'equals',value:'raven'}]},json:{value:'RAVEN'}});
for(const value of ['',[],null])for(const operation of ['equals','notEquals','gte','lte'])cases.push({name:'empty-right/'+operation+'/'+JSON.stringify(value),spec:{schema:'studio.if/1',combinator:'and',caseSensitive:true,continueOnFail:false,conditions:[{field:'value',type:'number',operation,value}]},json:{value:null}});
const results=[];
for(const c of cases){
 let expected,observed;
 const filter={combinator:c.spec.combinator,options:{caseSensitive:c.spec.caseSensitive,typeValidation:'strict',version:4},conditions:c.spec.conditions.map(x=>({leftValue:field(c.json,x.field),rightValue:x.value,operator:{type:x.type,operation:x.operation,singleValue:!Object.hasOwn(x,'value')}}))};
 try{expected={pass:executeFilter(filter)};}catch{expected={error:true};}
 try{observed={pass:adapter.partition(c.spec,[{json:c.json}]).true.length===1};}catch{observed={error:true};}
 results.push({name:c.name,expected,observed,match:JSON.stringify(expected)===JSON.stringify(observed)});
}
const mismatches=results.filter(x=>!x.match);
const report={reference:'n8n-workflow@2.46.4',reference_source_sha256:sha(referencePath),candidate_sha256:sha(adapterPath),cases:results.length,matches:results.length-mismatches.length,mismatches,
 scope:'Actual published n8n filter library versus independent adapter; compares selected boolean/error outcomes, not exact error messages, expressions, complete IF versions, UI or full workflow equivalence',all_matched:mismatches.length===0,results};
if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({...report,results:undefined},null,2));
process.exitCode=mismatches.length?2:0;
