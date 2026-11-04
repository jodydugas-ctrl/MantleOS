'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {pinPackage,loadSnapshot,readProfile,LIMITS}=require('./editor-assets.cjs');
const revision='261663556d98c9502663f6618edd8edd537e5688';
function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'studio-editor-'));
 t.after(()=>{if(path.dirname(path.resolve(root))!==path.resolve(os.tmpdir())||!path.basename(root).startsWith('studio-editor-'))throw Error('Unsafe cleanup path');fs.rmSync(root,{recursive:true,force:true});});
 const pkg=path.join(root,'package');fs.mkdirSync(path.join(pkg,'dist','assets'),{recursive:true});
 fs.writeFileSync(path.join(pkg,'package.json'),JSON.stringify({name:'n8n-editor-ui',version:'2.46.4',scripts:{postinstall:'NEVER EXECUTE'}}));
 fs.writeFileSync(path.join(pkg,'LICENSE.md'),'Synthetic license fixture; not upstream licensing.');
 fs.writeFileSync(path.join(pkg,'LICENSE_EE.md'),'Synthetic additional notice.');
 fs.writeFileSync(path.join(pkg,'dist','index.html'),'<html>%CONFIG_TAGS%<script nonce="{{CSP_NONCE}}" src="/{{BASE_PATH}}/assets/editor.js"></script></html>');
 fs.writeFileSync(path.join(pkg,'dist','assets','editor.js'),'const a="/{{BASE_PATH}}/x",b="/%7B%7BBASE_PATH%7D%7D/y";');
 fs.writeFileSync(path.join(pkg,'dist','assets','picture.png'),Buffer.from([0,255,128,4]));
 return {root,pkg,pin:()=>pinPackage({packageRoot:pkg,revision,reviewed:true})};
}
test('owner review is required; deterministic complete pins never execute package scripts',t=>{
 const {pkg,pin}=fixture(t);
 assert.throws(()=>pinPackage({packageRoot:pkg,revision}),/OWNER_REVIEW_REQUIRED/);
 assert.throws(()=>pinPackage({packageRoot:pkg,revision:'unresolved',reviewed:true}),/REVISION_REQUIRED/);
 const a=pin(),b=pin();assert.deepEqual(a,b);assert.equal(Object.keys(a.files).length,6);
 assert.equal(a.totalBytes,Object.values(a.files).reduce((sum,e)=>sum+e.size,0));
 assert.equal(JSON.stringify(a).includes(pkg),false);
});
test('verified snapshots preserve source and notices; callers cannot change admitted bytes',t=>{
 const {pkg,pin}=fixture(t),profile=pin(),snapshot=loadSnapshot({packageRoot:pkg,profile});
 const before=fs.readFileSync(path.join(pkg,'dist','assets','editor.js'));
 assert.equal(snapshot.asset('assets/editor.js').toString(),'const a="/x",b="/y";');
 assert.deepEqual(snapshot.asset('assets/picture.png'),Buffer.from([0,255,128,4]));
 assert.equal(snapshot.asset('missing.js'),null);
 assert.equal(snapshot.notice('LICENSE.md').toString(),fs.readFileSync(path.join(pkg,'LICENSE.md'),'utf8'));
 assert.throws(()=>snapshot.notice('package.json'),/NOTICE_UNKNOWN/);
 const html=snapshot.index();assert.ok(html.includes('src="/assets/editor.js"'));assert.ok(!html.includes('{{'));assert.ok(!html.includes('%CONFIG_TAGS%'));
 assert.notEqual(html,snapshot.index());
 snapshot.asset('assets/editor.js').fill(0);profile.files['dist/assets/editor.js'].sha256='0'.repeat(64);
 fs.writeFileSync(path.join(pkg,'dist','assets','editor.js'),'changed after session opened');
 assert.equal(snapshot.asset('assets/editor.js').toString(),'const a="/x",b="/y";');
 assert.ok(before.toString().includes('{{BASE_PATH}}'));assert.ok(Object.isFrozen(snapshot));
 assert.throws(()=>loadSnapshot({packageRoot:pkg,profile:pinPackage({packageRoot:pkg,revision,reviewed:true})}).asset('../LICENSE.md'),/PATH_INVALID/);
});
test('same-size changed content, missing files, extra files and changed notices invalidate reopening',t=>{
 const {pkg,pin}=fixture(t),profile=pin(),file=path.join(pkg,'dist','assets','editor.js'),original=fs.readFileSync(file);
 fs.writeFileSync(file,Buffer.alloc(original.length,32));assert.throws(()=>loadSnapshot({packageRoot:pkg,profile}),/SOURCE_CHANGED/);
 fs.writeFileSync(file,original);fs.writeFileSync(path.join(pkg,'dist','unexpected.js'),'extra');
 assert.throws(()=>loadSnapshot({packageRoot:pkg,profile}),/INVENTORY_CHANGED/);
 fs.unlinkSync(path.join(pkg,'dist','unexpected.js'));fs.unlinkSync(file);
 assert.throws(()=>loadSnapshot({packageRoot:pkg,profile}),/INVENTORY_CHANGED/);
 fs.writeFileSync(file,original);fs.appendFileSync(path.join(pkg,'LICENSE.md'),'changed');
 assert.throws(()=>loadSnapshot({packageRoot:pkg,profile}),/SOURCE_CHANGED/);
});
test('malformed profiles, traversal and cross-platform path collisions fail closed',t=>{
 const {pkg,pin}=fixture(t),profile=pin();
 for(const edit of [p=>p.files['dist/index.html'].sha256='0'.repeat(64),p=>p.totalBytes++,p=>p.package.version='9.0.0',p=>p.approved=true,p=>p.files['dist/../outside']={sha256:'0'.repeat(64),size:0},p=>p.files['dist/INDEX.html']=p.files['dist/index.html']]){
  const value=structuredClone(profile);edit(value);assert.throws(()=>loadSnapshot({packageRoot:pkg,profile:value}),/EDITOR_/);
 }
 const snapshot=loadSnapshot({packageRoot:pkg,profile});
 for(const name of ['../LICENSE.md','/index.html','a\\b','assets/%2e%2e/x','a//b','a?b','con.txt','x.'])assert.throws(()=>snapshot.asset(name),/PATH_INVALID/);
 fs.writeFileSync(path.join(pkg,'dist','AssetsCase.js'),'a');fs.writeFileSync(path.join(pkg,'dist','assetscase.js'),'b');
 if(fs.readdirSync(path.join(pkg,'dist')).includes('AssetsCase.js')&&fs.readdirSync(path.join(pkg,'dist')).includes('assetscase.js'))assert.throws(pin,/PATH_COLLISION/);
});
test('links and resource limits are rejected before admission',t=>{
 const {pkg,root,pin}=fixture(t),external=path.join(root,'outside');fs.mkdirSync(external);
 fs.writeFileSync(path.join(external,'secret.js'),'must not be served');
 // Junctions need no Windows symlink privilege; POSIX uses a directory symlink.
 fs.symlinkSync(external,path.join(pkg,'dist','linked'),process.platform==='win32'?'junction':'dir');
 assert.throws(pin,/LINK_OR_SPECIAL_FILE/);fs.unlinkSync(path.join(pkg,'dist','linked'));
 const large=path.join(pkg,'dist','large.bin'),fd=fs.openSync(large,'wx');
 try{fs.ftruncateSync(fd,LIMITS.fileBytes+1);}finally{fs.closeSync(fd);}
 assert.throws(pin,/SOURCE_LIMIT/);fs.unlinkSync(large);
 fs.writeFileSync(path.join(pkg,'LICENSE.md'),'');assert.throws(pin,/LICENSE_MISSING/);
});
test('pin/check CLI uses an unused output and check is read only in a fresh receiving process',t=>{
 const {pkg,root}=fixture(t),profileFile=path.join(root,'editor-source.json'),script=path.join(__dirname,'editor-assets.cjs');
 const run=(...args)=>spawnSync(process.execPath,[script,...args],{encoding:'utf8',timeout:15000});
 const created=run('pin','--package',pkg,'--profile',profileFile,'--revision',revision,'--reviewed');assert.equal(created.status,0,created.stderr);
 const before=fs.readFileSync(profileFile),profile=readProfile(profileFile);
 const check=run('check','--package',pkg,'--profile',profileFile);assert.equal(check.status,0,check.stderr);
 assert.equal(JSON.parse(check.stdout).sourceDigest,profile.sourceDigest);assert.equal(JSON.parse(check.stdout).authority,'NONE');
 const duplicate=run('pin','--package',pkg,'--profile',profileFile,'--revision',revision,'--reviewed');assert.notEqual(duplicate.status,0);
 assert.deepEqual(fs.readFileSync(profileFile),before);
 fs.appendFileSync(path.join(pkg,'dist','index.html'),'bad');assert.notEqual(run('check','--package',pkg,'--profile',profileFile).status,0);
 assert.deepEqual(fs.readFileSync(profileFile),before);
});
test('invalid UTF-8 executable assets and oversized profiles never become a serving snapshot',t=>{
 const {pkg,root,pin}=fixture(t);
 fs.writeFileSync(path.join(pkg,'dist','assets','editor.js'),Buffer.from([0xc3,0x28]));
 const profile=pin();assert.throws(()=>loadSnapshot({packageRoot:pkg,profile}),/encoded data/);
 const file=path.join(root,'oversized.json'),fd=fs.openSync(file,'wx');
 try{fs.ftruncateSync(fd,LIMITS.profileBytes+1);}finally{fs.closeSync(fd);}
 assert.throws(()=>readProfile(file),/PROFILE_LIMIT/);
});
