/* Trusted host assembly. Reading an installation verifies inert source/data;
 * it neither starts a service nor installs packages, cognition or effect grants. */
'use strict';
const fs=require('node:fs'),crypto=require('node:crypto');
const {readProfile,loadSnapshot}=require('./editor-assets.cjs');
const {loadCatalog}=require('./editor-catalog.cjs');
const canonical=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':Array.isArray(v)?'['+v.map(canonical).join(',')+']':JSON.stringify(v);
const sha=v=>crypto.createHash('sha256').update(v).digest('hex');
function readCatalogProfile(file){
 const stat=fs.lstatSync(file);
 if(!stat.isFile()||stat.isSymbolicLink()||stat.size>65536)throw Error('EDITOR_CATALOG_PROFILE_INVALID');
 const fd=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
 try{
  const first=fs.fstatSync(fd);
  if(!first.isFile()||first.dev!==stat.dev||first.ino!==stat.ino||first.size!==stat.size)throw Error('EDITOR_CATALOG_PROFILE_CHANGED');
  const bytes=Buffer.alloc(first.size+1);let length=0;
  while(length<bytes.length){const n=fs.readSync(fd,bytes,length,bytes.length-length,null);if(!n)break;length+=n;}
  const after=fs.fstatSync(fd),current=fs.lstatSync(file);
  if(length!==first.size||after.size!==first.size||current.isSymbolicLink()||current.dev!==first.dev||current.ino!==first.ino||current.size!==first.size)throw Error('EDITOR_CATALOG_PROFILE_CHANGED');
  try{return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(0,length)));}catch{throw Error('EDITOR_CATALOG_PROFILE_INVALID');}
 }finally{fs.closeSync(fd);}
}
function openInstallation({packageRoot,editorProfile,catalogRoot,catalogProfile,expectedDigest}){
 const editor=loadSnapshot({packageRoot,profile:readProfile(editorProfile)});
 const catalog=loadCatalog({root:catalogRoot,profile:readCatalogProfile(catalogProfile),editorSourceDigest:editor.sourceDigest});
 const identity={schema:'studio.editor-installation/1',reference:'n8n@2.46.4',editor_source_digest:editor.sourceDigest,catalog_source_digest:catalog.sourceDigest};
 const digest=sha(canonical(identity));
 if(expectedDigest!==undefined&&expectedDigest!==digest)throw Error('EDITOR_INSTALLATION_CHANGED');
 return Object.freeze({editor,catalog,digest,inspection:Object.freeze({...identity,sha256:digest,files:editor.fileCount,
  asset_bytes:editor.totalBytes,nodes:catalog.counts.nodes,credential_types:catalog.counts.credentialTypes,
  version_entries:catalog.counts.versionEntries,authority:'NONE',workflow_execution:'NOT_GRANTED_BY_INSTALLATION'})});
}
function main(argv){
 const options={};
 for(let i=0;i<argv.length;i++){
  const key=argv[i];if(!['--package','--editor-profile','--catalog','--catalog-profile','--expected'].includes(key)||Object.hasOwn(options,key)||!argv[i+1]||argv[i+1].startsWith('--'))throw Error('EDITOR_ARGUMENT_INVALID');
  options[key]=argv[++i];
 }
 if(!['--package','--editor-profile','--catalog','--catalog-profile'].every(key=>options[key]))throw Error('EDITOR_ARGUMENT_REQUIRED');
 const value=openInstallation({packageRoot:options['--package'],editorProfile:options['--editor-profile'],catalogRoot:options['--catalog'],catalogProfile:options['--catalog-profile'],expectedDigest:options['--expected']});
 console.log(JSON.stringify(value.inspection));
}
module.exports={openInstallation};
if(require.main===module){try{main(process.argv.slice(2));}catch{console.error('EDITOR_INSTALLATION_REJECTED');process.exitCode=2;}}
