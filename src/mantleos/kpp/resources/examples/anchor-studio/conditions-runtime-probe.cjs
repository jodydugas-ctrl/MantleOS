/* Run a synthetic IF flow in a separate native Node-RED runtime, without a listener.
 * Never opens the resident userDir, calls a provider, or deploys imported source.
 */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),http=require('node:http');
const RED=require(path.resolve(process.env.STUDIO_MODULES,'node-red'));
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'studio-if-'));
const spec={schema:'studio.if/1',combinator:'and',caseSensitive:true,continueOnFail:false,conditions:[{field:'score',type:'number',operation:'gte',value:10}]};
let received=[],errors=[];
RED.init(http.createServer(),{userDir:temp,flowFile:'flows.json',credentialSecret:'synthetic-if-only',httpAdminRoot:false,httpNodeRoot:false,nodesDir:path.join(__dirname,'palette'),logging:{console:{level:'off'}}});
function Sink(config){RED.nodes.createNode(this,config);this.on('input',(msg,send,done)=>{received.push({branch:config.branch,payload:msg.payload});done();});}
RED.nodes.registerType('studio-probe-sink',Sink);
function CatchSink(config){RED.nodes.createNode(this,config);this.on('input',(msg,send,done)=>{errors.push(msg.error.message);done();});}
RED.nodes.registerType('studio-probe-error',CatchSink);
const pause=()=>new Promise(resolve=>setTimeout(resolve,20));
async function settle(check){for(let i=0;i<100&&!check();i++)await pause();assert.ok(check(),'Native Node-RED result timeout');}
(async()=>{
 try{
  await RED.start();
  const flows=[{id:'tab',type:'tab',label:'Synthetic IF probe'},{id:'if',type:'studio-strict-if',z:'tab',name:'strict IF',conditions:JSON.stringify(spec),wires:[['true'],['false']]},
   {id:'true',type:'studio-probe-sink',z:'tab',branch:'true',wires:[]},{id:'false',type:'studio-probe-sink',z:'tab',branch:'false',wires:[]},
   {id:'catch',type:'catch',z:'tab',scope:['if'],uncaught:false,wires:[['error']]},{id:'error',type:'studio-probe-error',z:'tab',wires:[]}];
  await RED.runtime.flows.setFlows({user:{permissions:'*'},flows:{flows:flows.map(n=>n.type==='tab'?n:{...n,x:120,y:100})}});
  await settle(()=>Boolean(RED.nodes.getNode('if')));
  const node=RED.nodes.getNode('if');assert.ok(node,'Actual registered IF node missing');
  node.receive({payload:[{json:{score:9}},{json:{score:10}},{json:{score:11}}]});
  await settle(()=>received.length===2);assert.deepEqual(received.find(r=>r.branch==='true').payload.map(x=>x.json.score),[10,11]);assert.deepEqual(received.find(r=>r.branch==='false').payload.map(x=>x.json.score),[9]);
  received=[];node.receive({payload:[{json:{score:12}}]});await settle(()=>received.length===1);assert.equal(received[0].branch,'true');await pause();assert.equal(received.length,1,'Empty false branch emitted a message');
  received=[];node.receive({payload:[{json:{score:12}},{json:{score:'12'}}]});await settle(()=>errors.length===1);assert.equal(received.length,0,'Invalid batch partially released output');assert.match(errors[0],/Wrong type/);
  console.log(JSON.stringify({native_runtime:RED.version(),true_false_partition:'PASS',empty_branch_suppression:'PASS',strict_error_catch:'PASS',no_partial_release:'PASS',scope:'Synthetic IF adapter only; n8n reference runtime and full workflow parity are untested'}));
 }finally{await RED.stop();if(path.dirname(path.resolve(temp))!==path.resolve(os.tmpdir())||!path.basename(temp).startsWith('studio-if-'))throw Error('Unsafe probe cleanup path');fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
