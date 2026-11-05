/* Bounded, immutable public protocol data, not node execution,
 * credentials, grants, a requirements database or an acceptance receipt. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const FILES=Object.freeze(['PROVENANCE.json','credentials.json','node-versions.json','nodes.json','public-settings.json']);
const REVISION='261663556d98c9502663f6618edd8edd537e5688';
const LIMITS=Object.freeze({fileBytes:24*1024*1024,totalBytes:32*1024*1024});
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&Object.getPrototypeOf(v)===Object.prototype;
const canonical=v=>object(v)?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':Array.isArray(v)?'['+v.map(canonical).join(',')+']':JSON.stringify(v);
const exact=(v,keys)=>{if(!object(v)||Object.keys(v).sort().join(',')!==keys.slice().sort().join(','))throw Error('CATALOG_SCHEMA_INVALID');};
function json(bytes){try{return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw Error('CATALOG_JSON_INVALID');}}
function regular(file,directory=false){
 const stat=fs.lstatSync(file);
 if(stat.isSymbolicLink()||!(directory?stat.isDirectory():stat.isFile()))throw Error('CATALOG_LINK_OR_SPECIAL_FILE');
 return stat;
}
function readBounded(file){
 const before=regular(file);if(before.size>LIMITS.fileBytes)throw Error('CATALOG_SIZE_LIMIT');
 const fd=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
 try{
  const opened=fs.fstatSync(fd);
  if(!opened.isFile()||opened.dev!==before.dev||opened.ino!==before.ino||opened.size!==before.size)throw Error('CATALOG_SOURCE_CHANGED');
  const buffer=Buffer.alloc(opened.size+1);let length=0;
  while(length<buffer.length){const n=fs.readSync(fd,buffer,length,buffer.length-length,null);if(!n)break;length+=n;}
  const after=fs.fstatSync(fd),current=regular(file);
  if(length!==opened.size||after.size!==opened.size||current.dev!==opened.dev||current.ino!==opened.ino||current.size!==opened.size)throw Error('CATALOG_SOURCE_CHANGED');
  return Buffer.from(buffer.subarray(0,length));
 }finally{fs.closeSync(fd);}
}
function listing(root){
 regular(root,true);const directory=fs.opendirSync(root),names=[];
 try{
  for(let entry=directory.readSync();entry;entry=directory.readSync()){
   if(names.length>=FILES.length)throw Error('CATALOG_INVENTORY_CHANGED');
   regular(path.join(root,entry.name));names.push(entry.name);
  }
 }finally{directory.closeSync();}
 if(canonical(names.sort())!==canonical([...FILES].sort()))throw Error('CATALOG_INVENTORY_CHANGED');
}
function semantics(blobs){
 const parsed=Object.fromEntries([...blobs].map(([name,value])=>[name,json(value)]));
 const nodes=parsed['nodes.json'],credentials=parsed['credentials.json'],versions=parsed['node-versions.json'],settings=parsed['public-settings.json'];
 const name=x=>typeof x==='string'&&x.length>0&&x.length<=512;
 const version=x=>typeof x==='number'&&Number.isFinite(x)&&x>0;
 if(!Array.isArray(nodes)||!nodes.length||nodes.length>4096||nodes.some(n=>!object(n)||!name(n.name)||!(Array.isArray(n.version)?n.version.length>0&&n.version.every(version):version(n.version))))throw Error('CATALOG_NODES_INVALID');
 if(!Array.isArray(credentials)||credentials.length>2048||credentials.some(c=>!object(c)||!name(c.name)))throw Error('CATALOG_CREDENTIAL_TYPES_INVALID');
 if(!Array.isArray(versions)||!versions.length||versions.length>8192||!versions.every(name))throw Error('CATALOG_VERSIONS_INVALID');
 if(!object(settings)||settings.instanceId!=='HOST_RUNTIME_ID'||settings.urlBaseEditor!=='HOST_EDITOR_ORIGIN'||settings.telemetry?.enabled!==false||settings.posthog?.enabled!==false||settings.posthog?.apiKey!==''||settings.license?.consumerId!=='')throw Error('CATALOG_HOST_BINDING_REQUIRED');
 const p=parsed['PROVENANCE.json'];
 if(!object(p)||p.schema!=='studio.editor-catalog-provenance/1'||p.reference!=='n8n@2.46.4'||p.revision!==REVISION||p.kind!=='OBSERVED_PUBLIC_REFERENCE_PROTOCOL_DATA'||p.authority!=='NONE'||p.reference_owner_or_project_imported!==false||p.source_scripts_executed_on_import!==false)throw Error('CATALOG_PROVENANCE_INVALID');
 exact(p.files,FILES.filter(name=>name!=='PROVENANCE.json'));
 for(const [name,bound] of Object.entries(p.files)){
  exact(bound,['sha256','size']);if(bound.size!==blobs.get(name).length||bound.sha256!==sha(blobs.get(name)))throw Error('CATALOG_PROVENANCE_CHANGED');
 }
 return {nodes:nodes.length,credentialTypes:credentials.length,versionEntries:versions.length};
}
function validate(profile,editorSourceDigest){
 exact(profile,['schema','reference','revision','editor_source_digest','files','total_bytes','source_digest']);
 if(profile.schema!=='studio.editor-catalog/1'||profile.reference!=='n8n@2.46.4'||profile.revision!==REVISION)throw Error('CATALOG_PROFILE_UNSUPPORTED');
 if(typeof editorSourceDigest!=='string'||!/^[a-f0-9]{64}$/.test(editorSourceDigest)||profile.editor_source_digest!==editorSourceDigest)throw Error('CATALOG_EDITOR_BINDING_CHANGED');
 exact(profile.files,FILES);let total=0;
 for(const entry of Object.values(profile.files)){
  exact(entry,['sha256','size']);if(typeof entry.sha256!=='string'||!/^[a-f0-9]{64}$/.test(entry.sha256)||!Number.isSafeInteger(entry.size)||entry.size<0||entry.size>LIMITS.fileBytes)throw Error('CATALOG_PROFILE_INVALID');
  total+=entry.size;
 }
 if(total>LIMITS.totalBytes||profile.total_bytes!==total)throw Error('CATALOG_SIZE_LIMIT');
 const {source_digest,...bound}=profile;if(source_digest!==sha(canonical(bound)))throw Error('CATALOG_PROFILE_CHANGED');
 return profile;
}
function capture(root,expected){
 root=path.resolve(root);listing(root);const blobs=new Map(),files={};let total=0;
 for(const name of FILES){
  const bytes=readBounded(path.join(root,name));total+=bytes.length;if(total>LIMITS.totalBytes)throw Error('CATALOG_SIZE_LIMIT');
  const entry={sha256:sha(bytes),size:bytes.length};
  if(expected&&canonical(entry)!==canonical(expected.files[name]))throw Error('CATALOG_SOURCE_CHANGED');
  blobs.set(name,bytes);files[name]=entry;
 }
 listing(root);const counts=semantics(blobs);return {blobs,files,total,counts};
}
function pinCatalog({root,editorSourceDigest,reviewed=false}){
 if(reviewed!==true)throw Error('CATALOG_OWNER_REVIEW_REQUIRED');
 if(typeof editorSourceDigest!=='string'||!/^[a-f0-9]{64}$/.test(editorSourceDigest))throw Error('CATALOG_EDITOR_BINDING_REQUIRED');
 const {files,total}=capture(root);
 const profile={schema:'studio.editor-catalog/1',reference:'n8n@2.46.4',revision:REVISION,editor_source_digest:editorSourceDigest,files,total_bytes:total};
 profile.source_digest=sha(canonical(profile));return validate(profile,editorSourceDigest);
}
function loadCatalog({root,profile,editorSourceDigest}){
 profile=validate(JSON.parse(JSON.stringify(profile)),editorSourceDigest);
 const {blobs,counts}=capture(root,profile);
 return Object.freeze({sourceDigest:profile.source_digest,editorSourceDigest:profile.editor_source_digest,counts:Object.freeze(counts),
  asset(name){if(!FILES.includes(name))throw Error('CATALOG_ASSET_UNSUPPORTED');return Buffer.from(blobs.get(name));},
  json(name){if(!FILES.includes(name))throw Error('CATALOG_ASSET_UNSUPPORTED');return json(blobs.get(name));}
 });
}
module.exports={pinCatalog,loadCatalog,LIMITS};
