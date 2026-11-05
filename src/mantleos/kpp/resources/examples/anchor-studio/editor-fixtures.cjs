/* Synthetic inert package/catalog for host tests. No upstream assets, real
 * credentials, persona, or acceptance are included. Never installed as a host. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {pinPackage}=require('./editor-assets.cjs'),{pinCatalog}=require('./editor-catalog.cjs');
function create(root){
 const packageRoot=path.join(root,'package'),catalogRoot=path.join(root,'catalog');
 fs.mkdirSync(path.join(packageRoot,'dist'),{recursive:true});fs.mkdirSync(catalogRoot);
 for(const [name,value] of Object.entries({'package.json':JSON.stringify({name:'n8n-editor-ui',version:'2.46.4',scripts:{postinstall:'NEVER EXECUTE'}}),'LICENSE.md':'Synthetic license','LICENSE_EE.md':'Synthetic notice','dist/index.html':'<html><body>synthetic editor host fixture</body></html>'}))fs.writeFileSync(path.join(packageRoot,name),value);
 const editorProfile=path.join(root,'editor-profile.json'),pinned=pinPackage({packageRoot,revision:'261663556d98c9502663f6618edd8edd537e5688',reviewed:true});
 fs.writeFileSync(editorProfile,JSON.stringify(pinned));
 const values={'nodes.json':[{name:'synthetic.if',version:1}],'credentials.json':[{name:'syntheticCredential',properties:[]}],'node-versions.json':['synthetic.if@1'],
  'public-settings.json':{instanceId:'HOST_RUNTIME_ID',urlBaseEditor:'HOST_EDITOR_ORIGIN',telemetry:{enabled:false},posthog:{enabled:false,apiKey:''},license:{consumerId:''}}};
 const files={};for(const [name,value] of Object.entries(values)){const bytes=Buffer.from(JSON.stringify(value));fs.writeFileSync(path.join(catalogRoot,name),bytes);files[name]={sha256:crypto.createHash('sha256').update(bytes).digest('hex'),size:bytes.length};}
 fs.writeFileSync(path.join(catalogRoot,'PROVENANCE.json'),JSON.stringify({schema:'studio.editor-catalog-provenance/1',reference:'n8n@2.46.4',revision:'261663556d98c9502663f6618edd8edd537e5688',kind:'OBSERVED_PUBLIC_REFERENCE_PROTOCOL_DATA',reference_owner_or_project_imported:false,source_scripts_executed_on_import:false,authority:'NONE',files}));
 const catalogProfile=path.join(root,'catalog-profile.json');
 fs.writeFileSync(catalogProfile,JSON.stringify(pinCatalog({root:catalogRoot,editorSourceDigest:pinned.sourceDigest,reviewed:true})));
 return {packageRoot,editorProfile,catalogRoot,catalogProfile};
}
module.exports={create};
if(require.main===module)console.log(JSON.stringify(create(process.argv[2])));
