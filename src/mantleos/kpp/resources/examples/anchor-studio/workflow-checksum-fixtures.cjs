'use strict';
function fixture(index){
 const workflow={name:'Synthetic '+index+' 🌊',description:index%3?null:'quote " and slash \\',
  nodes:[{name:'Input',parameters:{z:index,a:{second:[true,null,1e-30,-0,'é\u2028\u2029'],first:index%2}},position:[index,-index],type:'synthetic.input'},
         {name:'Sink',parameters:JSON.parse('{"__proto__":{"retained":"data"},"constructor":"data"}'),position:[index+20,0],type:'synthetic.output'}],
  connections:{Input:{main:[[{node:'Sink',type:'main',index:0}]]}},settings:{timezone:'UTC',executionOrder:'v1'},
  meta:index%2?{z:'last',a:'first'}:null,pinData:{Input:[{json:{count:index}}]},isArchived:index%2===1,activeVersionId:null,nodeGroups:[],
  revision:'excluded-'+index,versionId:'also-excluded-'+index};
 if(index%7===0)delete workflow.description;
 return workflow;
}
module.exports={fixture};
