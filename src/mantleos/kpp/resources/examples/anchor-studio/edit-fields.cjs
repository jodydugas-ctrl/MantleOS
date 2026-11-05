/* Manual Edit Fields on the reviewed JSON-only Node-RED profile. */
'use strict';
const blocked=new Set(['__proto__','constructor','prototype']);
const own=(value,key)=>value!=null&&Object.hasOwn(value,key);
const object=value=>value&&typeof value==='object'&&!Array.isArray(value);
const only=(value,keys)=>object(value)&&Object.keys(value).every(key=>keys.includes(key));
const types=new Set(['string','number','boolean','array','object']);
function demand(ok,message){if(!ok)throw Error('Unsupported execution: Edit Fields '+message);}

function fieldPath(value,dots){
 demand(typeof value==='string'&&value.trim()&&value.length<=256&&!value.startsWith('=')&&!/[\[\]\u0000]/.test(value),'field name');
 const parts=dots?value.split('.'):[value];
 demand(parts.length<=16&&parts.every(part=>part&&!blocked.has(part)),'field path');
 return {value,parts};
}
function pathIn(item,field){return own(item,field.value)?[field.value]:field.parts;}
function get(item,field){
 return pathIn(item,field).reduce((value,key)=>own(value,key)?value[key]:undefined,item);
}
function set(item,field,value){
 const parts=pathIn(item,field);
 let parent=item;
 for(const part of parts.slice(0,-1)){
  if(!own(parent,part)||!object(parent[part]))parent[part]={};
  parent=parent[part];
 }
 parent[parts.at(-1)]=structuredClone(value);
}
function remove(item,field){
 const parts=pathIn(item,field);
 const parent=parts.slice(0,-1).reduce((value,key)=>own(value,key)?value[key]:undefined,item);
 if(own(parent,parts.at(-1)))delete parent[parts.at(-1)];
}
function convert(value,type){
 if(value===null||value===undefined)return null;
 if(type==='string')return typeof value==='object'?JSON.stringify(value):String(value);
 if(type==='number'){
  const number=Number(value);
  if(Number.isFinite(number))return number;
 }else if(type==='boolean'){
  if(typeof value==='boolean')return value;
  if(typeof value==='string'&&['true','false'].includes(value.toLowerCase()))return value.toLowerCase()==='true';
  if(!(typeof value==='string'&&!value.trim())){
   const number=Number(value);
   if(number===0||number===1)return Boolean(number);
  }
 }else{
  const parsed=typeof value==='string'?JSON.parse(value):value;
  if(type==='array'?Array.isArray(parsed):object(parsed))return parsed;
 }
 throw Error('Field value does not match its type');
}
function fieldList(value,dots){
 demand(typeof value==='string'&&value.length<=8192&&!value.startsWith('='),'field selection');
 return value.split(',').map(name=>name.trim()).filter(Boolean).map(name=>fieldPath(name,dots));
}
function prepareEditFields(node,operand){
 const {parameters={}}=node;
 demand(node.typeVersion===3.5&&only(parameters,['mode','assignments','includeOtherFields','include','includeFields','excludeFields','options'])&&
  (parameters.mode??'manual')==='manual'&&
  (parameters.includeOtherFields===undefined||typeof parameters.includeOtherFields==='boolean'),'manual profile');
 const options=parameters.options??{};
 demand(only(options,['dotNotation','ignoreConversionErrors','stripBinary'])&&Object.values(options).every(value=>typeof value==='boolean'),'options');
 const dots=options.dotNotation!==false,include=parameters.includeOtherFields?(parameters.include??'all'):'none';
 demand(['all','none','selected','except'].includes(include),'include option');
 const selection=include==='selected'?fieldList(parameters.includeFields??'',dots):
  include==='except'?fieldList(parameters.excludeFields??'',dots):[];
 const assignments=parameters.assignments??{};
 demand(only(assignments,['assignments']),'assignments');
 const fields=assignments.assignments??[];
 demand(Array.isArray(fields)&&fields.length<=64,'assignment count');
 const operations=fields.map(field=>{
  demand(only(field,['id','name','type','value'])&&types.has(field.type),'assignment shape');
  return {path:fieldPath(field.name,dots),type:field.type,read:operand(field.value)};
 });
 return items=>{
  const mapped=items.map((item,index)=>{
   const pairedItem={item:index};
   try{
    const json=['all','except'].includes(include)?structuredClone(item.json):{};
    if(include==='except')for(const field of selection)remove(json,field);
    if(include==='selected')for(const field of selection){
     const value=get(item.json,field);
     if(value!==undefined)set(json,fieldPath(field.parts.at(-1),false),value);
    }
    const values=new Map();
    for(const operation of operations){
     const raw=operation.read(item.json);
     let value;
     try{value=convert(raw,operation.type);}
     catch(error){if(!options.ignoreConversionErrors)throw error;value=raw??null;}
     values.set(operation.path.value,{path:operation.path,value});
    }
    for(const {path,value} of values.values())set(json,path,value);
    return {json,pairedItem};
   }catch(error){
    if(!node.continueOnFail)throw error;
    return {json:{error:'Edit Fields could not assign an input value.'},pairedItem};
   }
  });
  demand(Buffer.byteLength(JSON.stringify(mapped))<=256*1024,'output size');
  return [mapped];
 };
}
module.exports={prepareEditFields};
