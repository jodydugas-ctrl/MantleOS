'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {localAccess}=require('./local-access.cjs');
const credentials={user:'synthetic',password:'test-only'};
const make=()=>localAccess({port:18880,credentials});
function request(access,changes={}) {
 const req={method:'GET',url:'/studio',socket:{remoteAddress:'127.0.0.1'},...changes,
  headers:{host:'127.0.0.1:18880',...changes.headers}};
 const result={headers:{},code:200,next:false};
 const res={setHeader:(key,value)=>result.headers[key.toLowerCase()]=value,
  status:code=>{result.code=code;return res;},json:body=>{result.body=body;}};
 access.middleware(req,res,()=>result.next=true);return result;
}
const navigation={'sec-fetch-mode':'navigate','sec-fetch-dest':'document',accept:'text/html'};
function cookie(access) {
 const result=request(access,{headers:navigation});assert.equal(result.next,true);
 assert.match(result.headers['set-cookie'],/HttpOnly; SameSite=Strict$/);
 return result.headers['set-cookie'].split(';')[0];
}
test('fresh direct Studio and editor visits create a session without a challenge',()=>{
 for(const url of ['/','/studio','/studio/','/red','/red/']){
  const result=request(make(),{url,headers:navigation});assert.equal(result.next,true);
  assert.ok(result.headers['set-cookie']);assert.equal(result.headers['www-authenticate'],undefined);
 }
});
test('session admits API and operator click, without resending private credentials',()=>{
 const access=make(),session=cookie(access);
 for(const method of ['GET','POST'])assert.equal(request(access,{method,url:'/studio/status',headers:{cookie:session,origin:'http://127.0.0.1:18880','sec-fetch-site':'same-origin'}}).next,true);
});
test('API, iframe, image and cross-site fetch cannot bootstrap a session',()=>{
 for(const changes of [{url:'/studio/status',headers:navigation},{method:'POST',headers:navigation},
  {headers:{'sec-fetch-mode':'navigate','sec-fetch-dest':'iframe'}},{headers:{'sec-fetch-mode':'no-cors','sec-fetch-dest':'image'}},
  {headers:{'sec-fetch-mode':'cors','sec-fetch-dest':'empty','sec-fetch-site':'cross-site'}}]){
  const result=request(make(),changes);assert.equal(result.next,false);assert.equal(result.headers['set-cookie'],undefined);assert.equal(result.headers['www-authenticate'],undefined);
 }
});
test('foreign origins, rebinding hosts and non-loopback peers are denied',()=>{
 const access=make(),session=cookie(access);
 for(const changes of [{headers:{origin:'http://evil.invalid'}},{headers:{host:'evil.invalid:18880'}},
  {headers:{host:'127.0.0.1:18881'}},{socket:{remoteAddress:'192.0.2.1'}}]){
  const result=request(access,{...changes,headers:{cookie:session,...changes.headers}});assert.equal(result.code,403);assert.equal(result.next,false);
 }
});
test('cross-site and same-site API calls fail even with a valid session',()=>{
 const access=make(),session=cookie(access);
 for(const site of ['cross-site','same-site'])assert.equal(request(access,{url:'/studio/status',headers:{cookie:session,'sec-fetch-site':site}}).code,403);
});
test('a top-level link can open the app; embedded pages cannot frame it',()=>{
 const result=request(make(),{headers:{...navigation,'sec-fetch-site':'cross-site'}});
 assert.equal(result.next,true);assert.equal(result.headers['x-frame-options'],'SAMEORIGIN');
 assert.equal(result.headers['content-security-policy'],"frame-ancestors 'self'");
});
test('missing, forged and previous-launch sessions fail without browser login prompts',()=>{
 const access=make();
 for(const value of ['', 'studio_session_18880=forged',cookie(make())]){
  const result=request(access,{url:'/studio/status',headers:{cookie:value}});assert.equal(result.code,401);assert.equal(result.next,false);assert.equal(result.headers['www-authenticate'],undefined);
 }
});
test('existing private operator scripts remain compatible; wrong credentials fail',()=>{
 const access=make(),authorization='Basic '+Buffer.from('synthetic:test-only').toString('base64');
 assert.equal(request(access,{method:'POST',url:'/studio/shutdown',headers:{authorization}}).next,true);
 assert.equal(request(access,{url:'/studio/status',headers:{authorization:'Basic wrong'}}).code,401);
});
test('WebSocket upgrades require the same local session and origin boundaries',()=>{
 const access=make(),session=cookie(access);
 for(const [headers,denied] of [[{cookie:session,origin:'http://127.0.0.1:18880'},false],[{},true],
  [{cookie:session,origin:'http://evil.invalid'},true],[{cookie:session,host:'evil.invalid'},true]]){
  let destroyed=false;access.upgrade({socket:{remoteAddress:'127.0.0.1'},headers:{host:'127.0.0.1:18880',...headers}},{destroy:()=>destroyed=true});assert.equal(destroyed,denied);
 }
});
