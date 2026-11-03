/* Independent, bounded strict IF adapter. This is JavaScript, not an Anchor opcode.
 * Semantic reference: n8n 2.46.4 filter-parameter.ts and If/V2/IfV2.node.ts.
 * No arbitrary expressions, regex, conversion, dates, arrays or object operators.
 */
'use strict';
const operations=Object.freeze({
 string:['exists','notExists','empty','notEmpty','equals','notEquals','contains','notContains','startsWith','notStartsWith','endsWith','notEndsWith'],
 number:['exists','notExists','empty','notEmpty','equals','notEquals','gt','gte','lt','lte'],
 boolean:['exists','notExists','empty','notEmpty','equals','notEquals','true','false']
});
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const unary=new Set(['exists','notExists','empty','notEmpty','true','false']);
const numericEmpty=value=>typeof value==='string'&&value.trim()===''||Array.isArray(value)&&value.length===0;
function plain(o){return o!==null&&typeof o==='object'&&[Object.prototype,null].includes(Object.getPrototypeOf(o));}
function jsonOnly(value,depth=0,seen=new Set()){
 if(depth>32)throw Error('JSON nesting limit exceeded');
 if(value===null||typeof value==='string'||typeof value==='boolean'||typeof value==='number'&&Number.isFinite(value))return;
 if(!Array.isArray(value)&&!plain(value)||seen.has(value))throw Error('Only finite acyclic JSON values are supported');
 seen.add(value);
 if(Array.isArray(value)){for(let i=0;i<value.length;i++){if(!own(value,i))throw Error('Sparse JSON array');jsonOnly(value[i],depth+1,seen);}}
 else for(const item of Object.values(value))jsonOnly(item,depth+1,seen);
 seen.delete(value);
}
function validate(spec){
 if(!plain(spec)||Object.keys(spec).some(k=>!['schema','combinator','caseSensitive','continueOnFail','conditions'].includes(k))||spec.schema!=='studio.if/1'||!['and','or'].includes(spec.combinator)||typeof spec.caseSensitive!=='boolean'||typeof spec.continueOnFail!=='boolean'||!Array.isArray(spec.conditions)||spec.conditions.length<1||spec.conditions.length>32)throw Error('Invalid bounded IF contract');
 for(const c of spec.conditions){
  if(!plain(c)||Object.keys(c).some(k=>!['field','type','operation','value'].includes(k))||!own(operations,c.type)||!operations[c.type].includes(c.operation))throw Error('Unsupported IF operator');
  if(typeof c.field!=='string'||!c.field||c.field.length>256||c.field.split('.').some(k=>!/^[_A-Za-z][_A-Za-z0-9]*$/.test(k)||['__proto__','prototype','constructor'].includes(k)))throw Error('Unsupported field path');
  if(!unary.has(c.operation)&&(!own(c,'value')||(c.value!==null&&typeof c.value!==c.type&&!(c.type==='number'&&numericEmpty(c.value)))))throw Error('Wrong comparison value type');
  if(typeof c.value==='number'&&!Number.isFinite(c.value))throw Error('Nonfinite comparison');
 }
 return spec;
}
function field(item,path){let value=item;for(const key of path.split('.')){if(!plain(value)||!own(value,key))return undefined;value=value[key];}return value;}
function condition(c,json,caseSensitive){
 let left=field(json,c.field),right=c.value;
 // n8n filter version 3+ normalizes empty strings/arrays before strict validation.
 if(c.type==='number'){if(numericEmpty(left))left=null;if(numericEmpty(right))right=null;}
 if(left!==null&&left!==undefined&&typeof left!==c.type)throw Error('Wrong type at '+c.field+': expected '+c.type);
 const exists=left!==undefined&&left!==null;
 if(c.operation==='exists')return exists;if(c.operation==='notExists')return !exists;
 if(c.type==='string'){
  left=left??'';right=right??'';
  if(!caseSensitive){left=left.toLocaleLowerCase();right=right.toLocaleLowerCase();}
  if(c.operation==='empty')return left.length===0;if(c.operation==='notEmpty')return left.length!==0;
  if(c.operation==='contains')return left.includes(right);if(c.operation==='notContains')return !left.includes(right);
  if(c.operation==='startsWith')return left.startsWith(right);if(c.operation==='notStartsWith')return !left.startsWith(right);
  if(c.operation==='endsWith')return left.endsWith(right);if(c.operation==='notEndsWith')return !left.endsWith(right);
 }else{
  if(c.operation==='empty')return !exists;if(c.operation==='notEmpty')return exists;
  if(c.operation==='true')return Boolean(left);if(c.operation==='false')return !left;
  if(c.operation==='gt')return left>right;if(c.operation==='gte')return left>=right;
  if(c.operation==='lt')return left<right;if(c.operation==='lte')return left<=right;
 }
 if(c.operation==='equals')return left===right;if(c.operation==='notEquals')return left!==right;
 throw Error('Unsupported IF operation');
}
function partition(spec,items){
 jsonOnly(spec);validate(spec);jsonOnly(items);
 if(!Array.isArray(items)||items.length>128||Buffer.byteLength(JSON.stringify(items),'utf8')>256*1024||items.some(i=>!plain(i)||!plain(i.json)))throw Error('IF needs at most 128 JSON items / 256 KiB');
 const out={true:[],false:[],errors:[]};
 items.forEach((source,itemIndex)=>{
  const item=JSON.parse(JSON.stringify(source));if(!own(item,'pairedItem'))item.pairedItem={item:itemIndex};
  try{
   const pass=spec.combinator==='and'?spec.conditions.every(c=>condition(c,item.json,spec.caseSensitive)):spec.conditions.some(c=>condition(c,item.json,spec.caseSensitive));
   out[pass?'true':'false'].push(item);
  }catch(e){if(!spec.continueOnFail)throw Error('Item '+itemIndex+': '+e.message);out.false.push(item);out.errors.push({item:itemIndex,message:e.message});}
 });
 return out;
}
module.exports={operations,validate,partition};
