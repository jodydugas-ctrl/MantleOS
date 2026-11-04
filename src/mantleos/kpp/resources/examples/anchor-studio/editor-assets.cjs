/* Owner-reviewed static editor source. This loads bytes, never package code.
 * Original n8n assets and notices retain their licenses. A digest supplies
 * integrity, not permission, behavioral parity, or Baker acceptance. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');

const SCHEMA='studio.editor-source/1',VERSION='2.46.4';
const LIMITS=Object.freeze({files:2048,fileBytes:10*1024*1024,totalBytes:64*1024*1024,profileBytes:1024*1024});
const ROOT_FILES=['LICENSE.md','LICENSE_EE.md','package.json'];
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const plain=value=>value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype;
function canonical(value){
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 if(plain(value))return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
 return JSON.stringify(value);
}
function fail(code){throw new Error(code);}
function exact(value,keys){if(!plain(value)||Object.keys(value).sort().join(',')!==keys.slice().sort().join(','))fail('EDITOR_PROFILE_INVALID');}
function relativeName(name){
 if(typeof name!=='string'||name.length>512||name.split('/').some(part=>!part||part==='.'||part==='..'||!/^[A-Za-z0-9_@().+=-]+$/.test(part)||part.endsWith('.')||/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part)))fail('EDITOR_PATH_INVALID');
 return name;
}
function validate(profile){
 exact(profile,['schema','package','provenance','files','totalBytes','sourceDigest']);
 exact(profile.package,['name','version']);exact(profile.provenance,['repository','revision']);
 if(profile.schema!==SCHEMA||profile.package.name!=='n8n-editor-ui'||profile.package.version!==VERSION||profile.provenance.repository!=='https://github.com/n8n-io/n8n'||!/^[a-f0-9]{40}$/.test(profile.provenance.revision))fail('EDITOR_PROFILE_UNSUPPORTED');
 if(!plain(profile.files))fail('EDITOR_PROFILE_INVALID');
 const names=Object.keys(profile.files),folded=new Set();let total=0;
 if(names.length<4||names.length>LIMITS.files)fail('EDITOR_SOURCE_LIMIT');
 for(const name of names){
  relativeName(name);if(!ROOT_FILES.includes(name)&&!name.startsWith('dist/'))fail('EDITOR_PATH_INVALID');
  if(folded.has(name.toLowerCase()))fail('EDITOR_PATH_COLLISION');folded.add(name.toLowerCase());
  const entry=profile.files[name];exact(entry,['sha256','size']);
  if(!/^[a-f0-9]{64}$/.test(entry.sha256)||!Number.isSafeInteger(entry.size)||entry.size<0||entry.size>LIMITS.fileBytes)fail('EDITOR_PROFILE_INVALID');
  total+=entry.size;
 }
 for(const name of [...ROOT_FILES,'dist/index.html'])if(!Object.hasOwn(profile.files,name))fail('EDITOR_SOURCE_INCOMPLETE');
 if(total>LIMITS.totalBytes||profile.totalBytes!==total)fail('EDITOR_SOURCE_LIMIT');
 const {sourceDigest,...bound}=profile;
 if(typeof sourceDigest!=='string'||digest(canonical(bound))!==sourceDigest)fail('EDITOR_PROFILE_DIGEST_CHANGED');
 return profile;
}
function regular(file,directory=false){
 const stat=fs.lstatSync(file);
 if(stat.isSymbolicLink()||!(directory?stat.isDirectory():stat.isFile()))fail('EDITOR_LINK_OR_SPECIAL_FILE');
 return stat;
}
function inventory(packageRoot){
 const root=path.resolve(packageRoot);regular(root,true);regular(path.join(root,'dist'),true);
 const names=[...ROOT_FILES],directories=['dist'];let visited=0;
 while(directories.length){
  if(++visited>LIMITS.files)fail('EDITOR_SOURCE_LIMIT');
  const name=directories.pop();regular(path.join(root,name),true);
  const directory=fs.opendirSync(path.join(root,name));
  try{
   for(let entry=directory.readSync();entry;entry=directory.readSync()){
    const next=relativeName(name+'/'+entry.name),file=path.join(root,next),stat=regularOrDirectory(file);
    if(stat.isDirectory())directories.push(next);else names.push(next);
    if(names.length+directories.length>LIMITS.files)fail('EDITOR_SOURCE_LIMIT');
   }
  }finally{directory.closeSync();}
 }
 names.sort();const folded=new Set();
 for(const name of names){relativeName(name);if(folded.has(name.toLowerCase()))fail('EDITOR_PATH_COLLISION');folded.add(name.toLowerCase());}
 return {root,names};
}
function regularOrDirectory(file){
 const stat=fs.lstatSync(file);
 if(stat.isSymbolicLink()||!stat.isDirectory()&&!stat.isFile())fail('EDITOR_LINK_OR_SPECIAL_FILE');
 return stat;
}
function readRegular(root,name){
 const parts=name.split('/');for(let i=1;i<parts.length;i++)regular(path.join(root,...parts.slice(0,i)),true);
 const file=path.join(root,name),before=regular(file);
 if(before.size>LIMITS.fileBytes)fail('EDITOR_SOURCE_LIMIT');
 const fd=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
 try{
  const opened=fs.fstatSync(fd);
  if(!opened.isFile()||opened.dev!==before.dev||opened.ino!==before.ino||opened.size!==before.size)fail('EDITOR_SOURCE_CHANGED');
  // Read only the bounded declared size plus one byte, even if the file grows.
  const buffer=Buffer.alloc(opened.size+1);let length=0;
  while(length<buffer.length){const n=fs.readSync(fd,buffer,length,buffer.length-length,null);if(!n)break;length+=n;}
  const after=fs.fstatSync(fd),current=regular(file);
  if(length!==opened.size||after.size!==opened.size||current.dev!==opened.dev||current.ino!==opened.ino||current.size!==opened.size)fail('EDITOR_SOURCE_CHANGED');
  return Buffer.from(buffer.subarray(0,length));
 }finally{fs.closeSync(fd);}
}
function capture(packageRoot,expected){
 const {root,names}=inventory(packageRoot);
 if(expected&&canonical(names)!==canonical(Object.keys(expected.files).sort()))fail('EDITOR_INVENTORY_CHANGED');
 const blobs=new Map(),files={};let totalBytes=0;
 for(const name of names){
  const bytes=readRegular(root,name);totalBytes+=bytes.length;if(totalBytes>LIMITS.totalBytes)fail('EDITOR_SOURCE_LIMIT');
  const entry={sha256:digest(bytes),size:bytes.length};
  if(expected&&canonical(entry)!==canonical(expected.files[name]))fail('EDITOR_SOURCE_CHANGED');
  files[name]=entry;blobs.set(name,bytes);
 }
 if(canonical(names)!==canonical(inventory(root).names))fail('EDITOR_INVENTORY_CHANGED');
 const metadata=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(blobs.get('package.json')));
 if(metadata.name!=='n8n-editor-ui'||metadata.version!==VERSION)fail('EDITOR_PACKAGE_UNSUPPORTED');
 for(const name of ['LICENSE.md','LICENSE_EE.md'])if(!blobs.get(name).length)fail('EDITOR_LICENSE_MISSING');
 return {files,totalBytes,blobs};
}
function pinPackage({packageRoot,revision,reviewed=false}){
 if(reviewed!==true)fail('EDITOR_OWNER_REVIEW_REQUIRED');
 if(typeof revision!=='string'||!/^[a-f0-9]{40}$/.test(revision))fail('EDITOR_REVISION_REQUIRED');
 const {files,totalBytes}=capture(packageRoot);
 const profile={schema:SCHEMA,package:{name:'n8n-editor-ui',version:VERSION},provenance:{repository:'https://github.com/n8n-io/n8n',revision},files,totalBytes};
 profile.sourceDigest=digest(canonical(profile));return validate(profile);
}
function readProfile(file){
 const stat=regular(file);if(stat.size>LIMITS.profileBytes)fail('EDITOR_PROFILE_LIMIT');
 const bytes=readRegular(path.dirname(path.resolve(file)),path.basename(file));
 if(bytes.length>LIMITS.profileBytes)fail('EDITOR_PROFILE_LIMIT');
 return validate(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
}
function loadSnapshot({packageRoot,profile}){
 // Detach caller-owned objects; mutation after validation cannot change admission.
 const pinned=validate(JSON.parse(JSON.stringify(profile))),{blobs}=capture(packageRoot,pinned);
 const transformed=new Map(),decoder=new TextDecoder('utf-8',{fatal:true});
 const expand=text=>text.replaceAll('/{{BASE_PATH}}/','/').replaceAll('/%7B%7BBASE_PATH%7D%7D/','/');
 for(const [name,bytes] of blobs)if(name.startsWith('dist/')){
  transformed.set(name,/\.(html|js|css)$/.test(name)?Buffer.from(expand(decoder.decode(bytes))):bytes);
 }
 function asset(name){
  relativeName(name);const bytes=transformed.get('dist/'+name);
  return bytes===undefined?null:Buffer.from(bytes);
 }
 return Object.freeze({sourceDigest:pinned.sourceDigest,fileCount:blobs.size,totalBytes:pinned.totalBytes,
  asset,
  notice(name){if(!['LICENSE.md','LICENSE_EE.md'].includes(name))fail('EDITOR_NOTICE_UNKNOWN');return Buffer.from(blobs.get(name));},
  index(){return asset('index.html').toString('utf8').replaceAll('%CONFIG_TAGS%','<meta name="n8n:config:rest-endpoint" content="cmVzdA==">').replaceAll('{{CSP_NONCE}}',crypto.randomBytes(24).toString('base64'));}
 });
}
function main(argv){
 const [operation,...values]=argv,options={};
 if(!['pin','check'].includes(operation))fail('Usage: editor-assets.cjs pin|check --package PATH --profile FILE [--revision COMMIT --reviewed]');
 for(let i=0;i<values.length;i++){
  const key=values[i];if(!['--package','--profile','--revision','--reviewed'].includes(key)||Object.hasOwn(options,key))fail('EDITOR_ARGUMENT_INVALID');
  if(key==='--reviewed')options[key]=true;else{if(!values[i+1]||values[i+1].startsWith('--'))fail('EDITOR_ARGUMENT_INVALID');options[key]=values[++i];}
 }
 if(!options['--package']||!options['--profile'])fail('EDITOR_ARGUMENT_INVALID');
 if(operation==='pin'){
  const profile=pinPackage({packageRoot:options['--package'],revision:options['--revision'],reviewed:options['--reviewed']});
  const fd=fs.openSync(options['--profile'],'wx',0o600);
  try{fs.writeFileSync(fd,JSON.stringify(profile,null,2)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
  console.log(JSON.stringify({status:'PINNED',sourceDigest:profile.sourceDigest,files:Object.keys(profile.files).length,totalBytes:profile.totalBytes,authority:'NONE'}));
 }else{
  if(options['--reviewed']||options['--revision'])fail('EDITOR_ARGUMENT_INVALID');
  const snapshot=loadSnapshot({packageRoot:options['--package'],profile:readProfile(options['--profile'])});
  console.log(JSON.stringify({status:'VERIFIED',sourceDigest:snapshot.sourceDigest,files:snapshot.fileCount,totalBytes:snapshot.totalBytes,authority:'NONE'}));
 }
}
module.exports={pinPackage,readProfile,loadSnapshot,LIMITS};
if(require.main===module){try{main(process.argv.slice(2));}catch(error){console.error(error.message);process.exitCode=2;}}
