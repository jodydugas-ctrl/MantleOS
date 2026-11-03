/* Automatic owner-local browser sessions, not personal identity or isolation. */
'use strict';
const crypto=require('node:crypto');

function localAccess({port,credentials}) {
 const host=`127.0.0.1:${port}`,origin=`http://${host}`;
 const cookieName=`studio_session_${port}`,session=crypto.randomBytes(32).toString('base64url');
 const expected='Basic '+Buffer.from(credentials.user+':'+credentials.password).toString('base64');
 const equal=(a,b)=>{const left=Buffer.from(a||''),right=Buffer.from(b);return left.length===right.length&&crypto.timingSafeEqual(left,right);};
 function boundary(req) {
  return ['127.0.0.1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress)&&req.headers.host===host&&
   (!req.headers.origin||req.headers.origin===origin);
 }
 function authenticated(req) {
  if(!boundary(req)||!['same-origin','none',undefined].includes(req.headers['sec-fetch-site']))return false;
  if(equal(req.headers.authorization,expected))return true; // Private operator scripts only; never challenge the browser.
  const cookies=(req.headers.cookie||'').split(';').map(x=>x.trim());
  return cookies.some(x=>x.startsWith(cookieName+'=')&&equal(x.slice(cookieName.length+1),session));
 }
 function documentNavigation(req) {
  const pathname=req.url.split('?')[0];
  if(req.method!=='GET'||!['/','/studio','/studio/','/red','/red/'].includes(pathname))return false;
  const mode=req.headers['sec-fetch-mode'],dest=req.headers['sec-fetch-dest'];
  return mode==='navigate'&&dest==='document'||(!mode&&!dest&&(req.headers.accept||'').includes('text/html'));
 }
 function middleware(req,res,next) {
  res.setHeader('X-Frame-Options','SAMEORIGIN');
  res.setHeader('Content-Security-Policy',"frame-ancestors 'self'");
  res.setHeader('Referrer-Policy','same-origin');
  res.setHeader('Cache-Control','no-store');
  if(!boundary(req))return res.status(403).json({error:'LOCAL_ORIGIN_REQUIRED'});
  if(authenticated(req))return next();
  if(documentNavigation(req)){
   res.setHeader('Set-Cookie',`${cookieName}=${session}; Path=/; HttpOnly; SameSite=Strict`);
   return next();
  }
  return res.status(['cross-site','same-site'].includes(req.headers['sec-fetch-site'])?403:401).json({error:'OPEN_LOCAL_STUDIO',url:origin+'/studio'});
 }
 function upgrade(req,socket) {if(!authenticated(req))socket.destroy();}
 return {middleware,upgrade};
}
module.exports={localAccess};
