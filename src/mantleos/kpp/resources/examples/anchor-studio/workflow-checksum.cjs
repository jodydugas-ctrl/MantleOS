/* n8n 2.46.4 editor protocol compatibility. The reference field
 * contract was inspected at n8n-io/n8n 261663556d98c9502663f6618edd8edd537e5688.
 * This independent JSON projection loads no n8n backend or workflow engine.
 * Integrity only: a checksum never grants permission or accepts an obligation. */
'use strict';
const crypto=require('node:crypto');
const FIELDS=Object.freeze(['name','description','nodes','connections','settings','meta','pinData','isArchived','activeVersionId','nodeGroups']);
function sorted(value){
 if(value===null||typeof value==='string'||typeof value==='boolean')return value;
 if(typeof value==='number'){if(!Number.isFinite(value))throw Error('FINITE_JSON_WORKFLOW_REQUIRED');return value;}
 if(Array.isArray(value))return value.map(sorted);
 if(value&&typeof value==='object'&&[Object.prototype,null].includes(Object.getPrototypeOf(value)))
  // Upstream's ordinary-object assignment omits this special own key from
  // serialized output. Match that projection without assigning a prototype.
  // Full document revisions remain mandatory: this checksum is incomplete.
  return Object.fromEntries(Object.keys(value).filter(key=>key!=='__proto__').sort().map(key=>[key,sorted(value[key])]));
 throw Error('JSON_WORKFLOW_REQUIRED');
}
async function calculateWorkflowChecksum(workflow){
 if(!workflow||typeof workflow!=='object'||Array.isArray(workflow))throw Error('JSON_WORKFLOW_REQUIRED');
 const selected=Object.fromEntries(FIELDS.filter(key=>workflow[key]!==undefined).map(key=>[key,workflow[key]]));
 const bytes=JSON.stringify(sorted(selected));
 if(Buffer.byteLength(bytes)>16*1024*1024)throw Error('WORKFLOW_SIZE_LIMIT');
 return crypto.createHash('sha256').update(bytes).digest('hex');
}
module.exports={calculateWorkflowChecksum,FIELDS};
