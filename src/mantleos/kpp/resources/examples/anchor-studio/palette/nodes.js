module.exports=function(RED){
 const conditions=require('../conditions.cjs');
 function StrictIf(config){
  RED.nodes.createNode(this,config);
  let spec;try{spec=conditions.validate(JSON.parse(config.conditions));}catch(e){this.error(e.message);}
  this.on('input',(msg,send,done)=>{
   try{
    if(!spec)throw Error('Invalid IF configuration');
    const result=conditions.partition(spec,msg.payload);
    send([result.true.length?{...msg,payload:result.true,conditionErrors:result.errors}:null,result.false.length?{...msg,payload:result.false,conditionErrors:result.errors}:null]);
    if(done)done();
   }catch(e){if(done)done(e);else this.error(e,msg);}
  });
 }
 RED.nodes.registerType('studio-strict-if',StrictIf);
 for(const type of ['blackhole','neutral','whitehole']) {
  function Design(config){RED.nodes.createNode(this,config);this.on('input',(msg,send,done)=>{if(done)done();});}
  RED.nodes.registerType('anchor-'+type,Design);
 }
};
