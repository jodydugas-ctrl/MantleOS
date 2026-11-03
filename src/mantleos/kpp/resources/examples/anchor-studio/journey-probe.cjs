/* Synthetic manual-trigger -> IF -> debug journey in fresh receiving processes.
 * No resident state, HTTP listener, imported code or provider is used.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(process.argv[2]==='--child'){
 const RED=require(path.resolve(process.env.STUDIO_MODULES,'node-red')),http=require('node:http');
 const userDir=path.resolve(process.argv[3]);
 RED.init(http.createServer(),{userDir,flowFile:'flows.json',credentialSecret:'synthetic-journey-only',httpAdminRoot:false,httpNodeRoot:false,nodesDir:path.join(__dirname,'palette'),logging:{console:{level:'off'}}});
 const delay=()=>new Promise(r=>setTimeout(r,20));
 (async()=>{try{
  await RED.start();for(let i=0;i<100&&!RED.nodes.getNode('journey-input');i++)await delay();
  const out={true:null,false:null};
  for(const branch of ['true','false']){const node=RED.nodes.getNode('journey-'+branch);assert.ok(node);node.on('input',msg=>{out[branch]=msg.payload;});}
  RED.nodes.getNode('journey-input').receive({});
  for(let i=0;i<100&&(!out.true||!out.false);i++)await delay();
  assert.deepEqual(out.true.map(i=>i.json.score),[10,11]);assert.deepEqual(out.false.map(i=>i.json.score),[9]);assert.deepEqual(out.true.map(i=>i.pairedItem.item),[1,2]);
  console.log(JSON.stringify({runtime:RED.version(),manual_trigger:true,branches:out,provider_calls:0}));
 }finally{await RED.stop();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
}else{
 const output=path.resolve(process.argv[2]),fixture=path.join(__dirname,'if-journey.json');
 fs.mkdirSync(output,{recursive:false});const userDir=path.join(output,'receiving-body');fs.mkdirSync(userDir);
 fs.copyFileSync(fixture,path.join(userDir,'flows.json'));const pin=sha(path.join(userDir,'flows.json'));
 const {spawnSync}=require('node:child_process'),runs=[];
 for(let i=0;i<2;i++){
  const run=spawnSync(process.execPath,[__filename,'--child',userDir],{encoding:'utf8',timeout:30000,windowsHide:true});
  fs.writeFileSync(path.join(output,'process-'+i+'.log'),run.stdout+run.stderr);
  assert.equal(run.status,0,run.stdout+run.stderr);assert.equal(sha(path.join(userDir,'flows.json')),pin,'Journey source changed');
  runs.push(JSON.parse(run.stdout.trim()));
 }
 const report={fixture_sha256:sha(fixture),fresh_processes:2,runs,scope:'Synthetic manual trigger, IF routing, pairing and file-only reload. Not full n8n UI/workflow parity.',acceptance:'PENDING_BAKER'};
 fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}
