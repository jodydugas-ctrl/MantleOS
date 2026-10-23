/* Managed optional CELL. Base arithmetic is independent. */
window.KPP.define('square',ctx=>{
 ctx.listen(document.getElementById('square'),'click',()=>{
  const value=Number(window.CalculatorBody.read());
  if(Number.isFinite(value)&&window.CalculatorBody.read().trim()!=='')window.CalculatorBody.render(value*value);
 });
});
