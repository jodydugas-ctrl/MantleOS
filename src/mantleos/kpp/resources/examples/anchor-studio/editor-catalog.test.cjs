'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {pinCatalog,loadCatalog,LIMITS}=require('./editor-catalog.cjs');
const editorSourceDigest='a'.repeat(64);
function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'studio-catalog-'));
 t.after(()=>{if(path.dirname(path.resolve(root))!==path.resolve(os.tmpdir())||!path.basename(root).startsWith('studio-catalog-'))throw Error('Unsafe cleanup');fs.rmSync(root,{recursive:true,force:true});});
 const values={'nodes.json':[{name:'synthetic.if',version:[1,2.4]}],'credentials.json':[{name:'syntheticCredential',properties:[]}],
  'node-versions.json':['synthetic.if@1','synthetic.if@2.4'],'public-settings.json':{instanceId:'HOST_RUNTIME_ID',urlBaseEditor:'HOST_EDITOR_ORIGIN',telemetry:{enabled:false},posthog:{enabled:false,apiKey:''},license:{consumerId:''}}};
 for(const [name,value] of Object.entries(values))fs.writeFileSync(path.join(root,name),JSON.stringify(value));
 function provenance(changes={}){
  const files=Object.fromEntries(Object.keys(values).map(name=>{const bytes=fs.readFileSync(path.join(root,name));return [name,{sha256:crypto.createHash('sha256').update(bytes).digest('hex'),size:bytes.length}];}));
  fs.writeFileSync(path.join(root,'PROVENANCE.json'),JSON.stringify({schema:'studio.editor-catalog-provenance/1',reference:'n8n@2.46.4',revision:'261663556d98c9502663f6618edd8edd537e5688',kind:'OBSERVED_PUBLIC_REFERENCE_PROTOCOL_DATA',reference_owner_or_project_imported:false,source_scripts_executed_on_import:false,authority:'NONE',files,...changes}));
 }
 provenance();return {root,provenance,pin:()=>pinCatalog({root,editorSourceDigest,reviewed:true})};
}
test('explicit reviewed catalog pins pair to one editor source and are deterministic',t=>{
 const {root,pin}=fixture(t);assert.throws(()=>pinCatalog({root,editorSourceDigest}),/REVIEW_REQUIRED/);
 const a=pin();assert.deepEqual(pin(),a);assert.equal(JSON.stringify(a).includes(root),false);
 assert.throws(()=>loadCatalog({root,profile:a,editorSourceDigest:'b'.repeat(64)}),/EDITOR_BINDING_CHANGED/);
 const loaded=loadCatalog({root,profile:a,editorSourceDigest});assert.deepEqual(loaded.counts,{nodes:1,credentialTypes:1,versionEntries:2});
});
test('disk and caller changes cannot mutate an admitted catalog snapshot',t=>{
 const {root,pin}=fixture(t),profile=pin(),loaded=loadCatalog({root,profile,editorSourceDigest});
 loaded.asset('nodes.json').fill(0);loaded.json('nodes.json')[0].name='forged';profile.files['nodes.json'].sha256='0'.repeat(64);
 fs.writeFileSync(path.join(root,'nodes.json'),'changed after open');
 assert.equal(loaded.json('nodes.json')[0].name,'synthetic.if');assert.ok(Object.isFrozen(loaded));
 assert.throws(()=>loaded.asset('../outside'),/ASSET_UNSUPPORTED/);assert.throws(()=>loadCatalog({root,profile,editorSourceDigest}),/PROFILE_CHANGED/);
});
test('changed files and extra directory entries fail before serving data',t=>{
 const {root,pin}=fixture(t),profile=pin();fs.writeFileSync(path.join(root,'unexpected.json'),'{}');
 assert.throws(()=>loadCatalog({root,profile,editorSourceDigest}),/INVENTORY_CHANGED/);fs.unlinkSync(path.join(root,'unexpected.json'));
 fs.writeFileSync(path.join(root,'credentials.json'),'[]');assert.throws(()=>loadCatalog({root,profile,editorSourceDigest}),/SOURCE_CHANGED/);
});
test('provenance assertions cannot grant authority or import a reference owner',t=>{
 const {root,pin,provenance}=fixture(t);
 provenance({authority:'OWNER'});assert.throws(pin,/PROVENANCE_INVALID/);
 provenance({reference_owner_or_project_imported:true});assert.throws(pin,/PROVENANCE_INVALID/);
 provenance();const settings=JSON.parse(fs.readFileSync(path.join(root,'public-settings.json')));settings.instanceId='reference-owner-instance';
 fs.writeFileSync(path.join(root,'public-settings.json'),JSON.stringify(settings));provenance();assert.throws(pin,/HOST_BINDING_REQUIRED/);
});
test('malformed executable-looking JSON and oversized source fail with bounded diagnostics',t=>{
 const {root,pin,provenance}=fixture(t);fs.writeFileSync(path.join(root,'nodes.json'),'private-looking malformed token');provenance();
 assert.throws(pin,error=>error.message==='CATALOG_JSON_INVALID');
 const file=path.join(root,'nodes.json'),fd=fs.openSync(file,'w');try{fs.ftruncateSync(fd,LIMITS.fileBytes+1);}finally{fs.closeSync(fd);}
 assert.throws(pin,/SIZE_LIMIT/);
});
