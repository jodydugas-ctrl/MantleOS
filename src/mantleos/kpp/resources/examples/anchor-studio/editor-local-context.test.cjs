'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {initialize,read,project,SCOPES}=require('./editor-local-context.cjs');
function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'studio-owner-'));
 t.after(()=>{if(path.dirname(path.resolve(root))!==path.resolve(os.tmpdir())||!path.basename(root).startsWith('studio-owner-'))throw Error('Unsafe cleanup');fs.rmSync(root,{recursive:true,force:true});});
 return path.join(root,'owner.json');
}
test('fresh local metadata needs review, persists identity, and never creates credentials',t=>{
 const file=fixture(t);assert.throws(()=>read(file));assert.equal(fs.existsSync(file),false);
 assert.throws(()=>initialize(file),/REVIEW_REQUIRED/);
 const first=initialize(file,{reviewed:true}),bytes=fs.readFileSync(file);
 assert.deepEqual(initialize(file,{reviewed:true}),first);assert.deepEqual(fs.readFileSync(file),bytes);
 assert.deepEqual(read(file),first);assert.notEqual(initialize(fixture(t),{reviewed:true}).userId,first.userId);
 assert.deepEqual(Object.keys(first).sort(),['createdAt','instanceId','projectId','schema','userId']);
});
test('presentation records bind the fresh owner and advertise no execution grants or remote telemetry',t=>{
 const identity=initialize(fixture(t),{reviewed:true});
 const value=project({identity,port:18884,settingsTemplate:{instanceId:'reference-instance',enterprise:{sharing:true},posthog:{apiKey:'reference-analytics-key'},license:{consumerId:'reference-license'}}});
 assert.equal(value.user.id,identity.userId);assert.equal(value.personal.creatorId,identity.userId);assert.equal(value.personal.projectRelations[0].userId,identity.userId);
 assert.equal(value.projects[0].id,identity.projectId);assert.equal(value.settings.instanceId,identity.instanceId);
 assert.equal(value.settings.telemetry.enabled,false);assert.equal(value.settings.enterprise.sharing,false);
 assert.deepEqual(value.settings.enterprise.projects,{team:{limit:0}});
 assert.equal(JSON.stringify(value).includes('reference-'),false);assert.equal(value.capabilities.authority,'NONE');
 assert.deepEqual(value.user.globalScopes,SCOPES);assert.equal(value.user.globalScopes.includes('workflow:execute'),false);
 assert.equal(value.settings.publicApi.enabled,false);assert.equal(value.settings.ai.allowSendingParameterValues,false);
 const second=project({identity,port:18884,settingsTemplate:{}});value.user.globalScopes.push('FORGED');assert.deepEqual(second.user.globalScopes,SCOPES);
});
test('modified identity and unsafe state files fail explicitly',t=>{
 const file=fixture(t),identity=initialize(file,{reviewed:true});
 assert.throws(()=>project({identity:{...identity,grant:true},port:18884,settingsTemplate:{}}),/INVALID_LOCAL/);
 assert.throws(()=>project({identity,port:80,settingsTemplate:{}}),/INVALID_LOCAL_PORT/);
 fs.writeFileSync(file,JSON.stringify({...identity,projectId:'../outside'}));assert.throws(()=>read(file),/INVALID_LOCAL/);
});
