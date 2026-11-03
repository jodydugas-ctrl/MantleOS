module.exports=function(RED){
 for(const type of ['blackhole','neutral','whitehole']) {
  function Design(config){RED.nodes.createNode(this,config);this.on('input',(msg,send,done)=>{if(done)done();});}
  RED.nodes.registerType('anchor-'+type,Design);
 }
};
