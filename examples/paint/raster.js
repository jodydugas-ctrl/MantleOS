/* Mantle Paint: deterministic raster Body. Original project source. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PaintCore = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const MAX_PIXELS = 2000000, MAX_SIDE = 2048;
  const PRIMER = 'Mantle Paint / 1. Bio-Software, not an AppAI or agent. Preserve the user\'s pixels; append experience; keep prior executable meaning fixed. No MIND is required. Local files and drawing commands confer no additional authority.';
  const palette = ['#000000','#808080','#800000','#808000','#008000','#008080','#000080','#800080','#808040','#004040','#0080ff','#004080','#8000ff','#804000',
    '#ffffff','#c0c0c0','#ff0000','#ffff00','#00ff00','#00ffff','#0000ff','#ff00ff','#ffff80','#00ff80','#80ffff','#8080ff','#ff0080','#ff8040'];
  const colorCache = new Map();
  function color(value) {
    if (Array.isArray(value) || value instanceof Uint8ClampedArray) return value;
    if (!/^#[0-9a-f]{6}$/i.test(value)) throw Error('Expected an RGB hex color');
    if (!colorCache.has(value)) colorCache.set(value, [parseInt(value.slice(1,3),16),parseInt(value.slice(3,5),16),parseInt(value.slice(5,7),16),255]);
    return colorCache.get(value);
  }
  function bounds(w,h) {
    if (!Number.isInteger(w) || !Number.isInteger(h) || w<1 || h<1 || w>MAX_SIDE || h>MAX_SIDE || w*h>MAX_PIXELS) throw Error('Image limit: 1–2048 pixels per side, 2 million pixels total');
  }
  function hex(c) { return '#' + Array.from(c).slice(0,3).map(v=>v.toString(16).padStart(2,'0')).join(''); }
  function canonical(value) {
    if (Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
    if (value && typeof value==='object') return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
    return JSON.stringify(value);
  }
  async function hash(value) {
    const bytes = typeof value==='string' ? new TextEncoder().encode(value) : value;
    if (!globalThis.crypto?.subtle) throw Error('Verified memory needs Web Crypto; drawing remains available');
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(v=>v.toString(16).padStart(2,'0')).join('');
  }
  function b64(bytes) {
    if (typeof Buffer!=='undefined') return Buffer.from(bytes).toString('base64');
    let text=''; for(let n=0;n<bytes.length;n+=8192) text+=String.fromCharCode(...bytes.subarray(n,n+8192));
    return btoa(text);
  }
  function unb64(text) {
    if (typeof text!=='string' || text.length>11000000 || text.length%4 || !/^[A-Za-z0-9+/]*={0,2}$/.test(text)) throw Error('Invalid pixel encoding');
    if (typeof Buffer!=='undefined') return new Uint8ClampedArray(Buffer.from(text,'base64'));
    return Uint8ClampedArray.from(atob(text),c=>c.charCodeAt(0));
  }
  function imageDimensions(bytes) {
    const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);let w,h;
    if(bytes.length>=24&&[137,80,78,71,13,10,26,10].every((v,i)=>bytes[i]===v)) {w=view.getUint32(16);h=view.getUint32(20);}
    else if(bytes.length>=10&&String.fromCharCode(...bytes.subarray(0,6)).match(/^GIF8[79]a$/)) {w=view.getUint16(6,true);h=view.getUint16(8,true);}
    else if(bytes.length>=54&&bytes[0]===66&&bytes[1]===77) {w=view.getInt32(18,true);h=Math.abs(view.getInt32(22,true));}
    else if(bytes.length>=4&&bytes[0]===255&&bytes[1]===216) {
      let pos=2;
      while(pos+4<=bytes.length){if(bytes[pos++]!==255)throw Error('Invalid JPEG marker');while(bytes[pos]===255)pos++;const marker=bytes[pos++];if(marker===217||marker===218)break;const length=view.getUint16(pos);if(length<2||pos+length>bytes.length)throw Error('Truncated JPEG');
        if([192,193,194,195,197,198,199,201,202,203,205,206,207].includes(marker)){if(length<8)throw Error('Invalid JPEG frame');h=view.getUint16(pos+3);w=view.getUint16(pos+5);break;}pos+=length;
      }
    }
    if(w===undefined||h===undefined)throw Error('Supported images: PNG, JPEG, GIF and uncompressed BMP');bounds(w,h);return {width:w,height:h};
  }
  class Raster {
    constructor(w,h,background='#ffffff',data=null) {
      bounds(w,h); this.w=w;this.h=h;
      if(data && data.length!==w*h*4) throw Error('Pixel length does not match dimensions');
      this.data=data ? new Uint8ClampedArray(data) : new Uint8ClampedArray(w*h*4);
      if(!data) this.clear(background);
    }
    clone() { return new Raster(this.w,this.h,'#ffffff',this.data); }
    get(x,y) {x=Math.floor(x);y=Math.floor(y);return x<0||y<0||x>=this.w||y>=this.h ? null : Array.from(this.data.subarray((y*this.w+x)*4,(y*this.w+x)*4+4));}
    put(x,y,c) {x=Math.round(x);y=Math.round(y);if(x>=0&&y>=0&&x<this.w&&y<this.h)this.data.set(color(c),(y*this.w+x)*4);}
    clear(c) {c=color(c);for(let n=0;n<this.data.length;n+=4)this.data.set(c,n);}
    stamp(x,y,c,size=1,shape='square',replace=null) {
      c=color(c);const match=replace?color(replace):null;
      size=Math.max(1,Math.min(32,Math.round(size)));const lo=-Math.floor(size/2),hi=lo+size;
      for(let j=lo;j<hi;j++)for(let i=lo;i<hi;i++) {
        if(shape==='round' && (i+.5)**2+(j+.5)**2>(size/2)**2)continue;
        if(shape==='slash' && Math.abs(i+j)>1)continue;
        const old=this.get(x+i,y+j);
        if(old&&(!match||old.slice(0,3).every((v,n)=>v===match[n])))this.put(x+i,y+j,c);
      }
    }
    line(x0,y0,x1,y1,c,size=1,shape='square',replace=null) {
      [x0,y0,x1,y1]=[x0,y0,x1,y1].map(v=>Math.max(-4096,Math.min(4096,Math.round(v))));
      let dx=Math.abs(x1-x0),sx=x0<x1?1:-1,dy=-Math.abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;
      for(;;){this.stamp(x0,y0,c,size,shape,replace);if(x0===x1&&y0===y1)break;const e=2*err;if(e>=dy){err+=dy;x0+=sx;}if(e<=dx){err+=dx;y0+=sy;}}
    }
    rect(x0,y0,x1,y1,fg,bg,mode='outline',width=1,rounded=false) {
      let left=Math.min(x0,x1),right=Math.max(x0,x1),top=Math.min(y0,y1),bottom=Math.max(y0,y1);
      if(right<0||bottom<0||left>=this.w||top>=this.h)return;
      if(rounded) {
        const cx=(left+right)/2,cy=(top+bottom)/2,hx=(right-left+1)/2,hy=(bottom-top+1)/2,r=Math.min(12,hx/2,hy/2);
        const inside=(x,y,inset)=>{const a=hx-inset,b=hy-inset;if(a<=0||b<=0)return false;const rr=Math.max(0,r-inset),dx=Math.max(Math.abs(x-cx)-(a-rr),0),dy=Math.max(Math.abs(y-cy)-(b-rr),0);return dx*dx+dy*dy<=rr*rr;};
        for(let y=Math.max(0,top);y<=Math.min(this.h-1,bottom);y++)for(let x=Math.max(0,left);x<=Math.min(this.w-1,right);x++)if(inside(x,y,0)) {
          if(mode==='solid')this.put(x,y,fg);else if(!inside(x,y,width))this.put(x,y,fg);else if(mode==='both')this.put(x,y,bg);
        }
        return;
      }
      if(mode!=='outline')for(let y=Math.max(0,top);y<=Math.min(this.h-1,bottom);y++)this.line(Math.max(0,left),y,Math.min(this.w-1,right),y,mode==='solid'?fg:bg);
      if(mode!=='solid') {this.line(left,top,right,top,fg,width);this.line(right,top,right,bottom,fg,width);this.line(right,bottom,left,bottom,fg,width);this.line(left,bottom,left,top,fg,width);}
    }
    ellipse(x0,y0,x1,y1,fg,bg,mode='outline',width=1) {
      const left=Math.min(x0,x1),right=Math.max(x0,x1),top=Math.min(y0,y1),bottom=Math.max(y0,y1),rx=(right-left+1)/2,ry=(bottom-top+1)/2,cx=(left+right)/2,cy=(top+bottom)/2;
      for(let y=Math.max(0,top);y<=Math.min(this.h-1,bottom);y++)for(let x=Math.max(0,left);x<=Math.min(this.w-1,right);x++) {
        if(((x-cx)/rx)**2+((y-cy)/ry)**2>1)continue;
        const inner=rx>width&&ry>width&&((x-cx)/(rx-width))**2+((y-cy)/(ry-width))**2<1;
        if(mode==='solid'||!inner)this.put(x,y,fg);else if(mode==='both')this.put(x,y,bg);
      }
    }
    polygon(points,fg,bg,mode='outline',width=1) {
      if(points.length<2||points.length>512)throw Error('Polygon needs 2–512 vertices');
      if(mode!=='outline') {
        const min=Math.max(0,Math.floor(Math.min(...points.map(p=>p[1])))),max=Math.min(this.h-1,Math.ceil(Math.max(...points.map(p=>p[1]))));
        for(let y=min;y<=max;y++) {
          const cuts=[];
          for(let i=0,j=points.length-1;i<points.length;j=i++) {const [x1,y1]=points[j],[x2,y2]=points[i];if((y1>y+.5)!==(y2>y+.5))cuts.push(x1+(y+.5-y1)*(x2-x1)/(y2-y1));}
          cuts.sort((a,b)=>a-b);
          for(let i=0;i+1<cuts.length;i+=2)this.line(Math.ceil(cuts[i]),y,Math.floor(cuts[i+1]),y,mode==='solid'?fg:bg);
        }
      }
      if(mode!=='solid')for(let i=0;i<points.length;i++)this.line(...points[i],...points[(i+1)%points.length],fg,width);
    }
    curve(start,end,bends,fg,width=1) {
      if(!bends.length)return this.line(...start,...end,fg,width);
      let prev=start;const steps=Math.min(4096,Math.max(32,(Math.abs(end[0]-start[0])+Math.abs(end[1]-start[1]))*3));
      for(let i=1;i<=steps;i++) {const t=i/steps,u=1-t;let p;
        if(bends.length===1)p=[u*u*start[0]+2*u*t*bends[0][0]+t*t*end[0],u*u*start[1]+2*u*t*bends[0][1]+t*t*end[1]];
        else p=[u**3*start[0]+3*u*u*t*bends[0][0]+3*u*t*t*bends[1][0]+t**3*end[0],u**3*start[1]+3*u*u*t*bends[0][1]+3*u*t*t*bends[1][1]+t**3*end[1]];
        this.line(...prev,...p,fg,width);prev=p;
      }
    }
    flood(x,y,c) {
      x=Math.floor(x);y=Math.floor(y);const old=this.get(x,y);c=color(c);if(!old||old.every((v,i)=>v===c[i]))return;
      const queue=new Int32Array(this.w*this.h);let head=0,tail=0;
      const add=(index)=>{const off=index*4;if(old.every((v,i)=>this.data[off+i]===v)){this.data.set(c,off);queue[tail++]=index;}};
      add(y*this.w+x);
      while(head<tail){const n=queue[head++],xx=n%this.w;if(xx>0)add(n-1);if(xx<this.w-1)add(n+1);if(n>=this.w)add(n-this.w);if(n<this.w*(this.h-1))add(n+this.w);}
    }
    spray(x,y,c,radius=8,seed=1) {
      const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
      for(let n=0;n<30;n++){const angle=random()*Math.PI*2,r=Math.sqrt(random())*radius;this.put(x+Math.cos(angle)*r,y+Math.sin(angle)*r,c);}return seed;
    }
    crop(x,y,w,h,points=null) {
      x=Math.max(0,Math.min(this.w-1,Math.floor(x)));y=Math.max(0,Math.min(this.h-1,Math.floor(y)));
      w=Math.max(1,Math.min(this.w-x,Math.round(w)));h=Math.max(1,Math.min(this.h-y,Math.round(h)));
      const image=new Raster(w,h),mask=new Uint8Array(w*h).fill(1);
      for(let j=0;j<h;j++)for(let i=0;i<w;i++){image.put(i,j,this.get(x+i,y+j));if(points){let inside=false;for(let a=0,b=points.length-1;a<points.length;b=a++)if((points[a][1]>y+j+.5)!==(points[b][1]>y+j+.5)&&(x+i+.5<(points[b][0]-points[a][0])*(y+j+.5-points[a][1])/(points[b][1]-points[a][1])+points[a][0]))inside=!inside;mask[j*w+i]=Number(inside);}}
      return {x,y,image,mask};
    }
    paste(selection,x,y,transparent=null) {
      const {image,mask}=selection,skip=transparent?color(transparent):null;
      for(let j=0;j<image.h;j++)for(let i=0;i<image.w;i++){if(mask&&!mask[j*image.w+i])continue;const c=image.get(i,j);if(skip&&c.slice(0,3).every((v,n)=>v===skip[n]))continue;this.put(x+i,y+j,c);}
    }
    eraseSelection(selection,bg) {for(let j=0;j<selection.image.h;j++)for(let i=0;i<selection.image.w;i++)if(!selection.mask||selection.mask[j*selection.image.w+i])this.put(selection.x+i,selection.y+j,bg);}
    resize(w,h,bg='#ffffff',stretch=false) {
      const next=new Raster(w,h,bg);
      for(let y=0;y<h;y++)for(let x=0;x<w;x++){const p=stretch?this.get(Math.floor(x*this.w/w),Math.floor(y*this.h/h)):this.get(x,y);if(p)next.put(x,y,p);}return next;
    }
    transform(kind) {
      if(!['flipH','flipV','rotate90','rotate180','rotate270'].includes(kind))throw Error('Unknown transform');
      const swap=kind==='rotate90'||kind==='rotate270',next=new Raster(swap?this.h:this.w,swap?this.w:this.h);
      for(let y=0;y<this.h;y++)for(let x=0;x<this.w;x++) {
        let dest=kind==='flipH'?[this.w-1-x,y]:kind==='flipV'?[x,this.h-1-y]:kind==='rotate90'?[this.h-1-y,x]:kind==='rotate270'?[y,this.w-1-x]:[this.w-1-x,this.h-1-y];next.put(...dest,this.get(x,y));
      }return next;
    }
    skew(horizontal,vertical,bg='#ffffff') {
      if(![horizontal,vertical].every(v=>Number.isFinite(v)&&Math.abs(v)<=45))throw Error('Skew range is -45 to 45 degrees');
      const a=Math.tan(horizontal*Math.PI/180),b=Math.tan(vertical*Math.PI/180),det=1-a*b;
      if(Math.abs(det)<.05)throw Error('Skew would collapse the image');
      const corners=[[0,0],[this.w,0],[0,this.h],[this.w,this.h]].map(([x,y])=>[x+a*y,b*x+y]);
      const left=Math.floor(Math.min(...corners.map(p=>p[0]))),top=Math.floor(Math.min(...corners.map(p=>p[1]))),right=Math.ceil(Math.max(...corners.map(p=>p[0]))),bottom=Math.ceil(Math.max(...corners.map(p=>p[1])));
      const out=new Raster(right-left,bottom-top,bg);
      for(let y=0;y<out.h;y++)for(let x=0;x<out.w;x++){const xx=x+left,yy=y+top,c=this.get(Math.floor((xx-a*yy)/det),Math.floor((yy-b*xx)/det));if(c)out.put(x,y,c);}return out;
    }
    invert() {for(let n=0;n<this.data.length;n++)if(n%4!==3)this.data[n]=255-this.data[n];}
    bmp() {
      const stride=Math.ceil(this.w*3/4)*4,bytes=new Uint8Array(54+stride*this.h),view=new DataView(bytes.buffer);
      bytes[0]=66;bytes[1]=77;view.setUint32(2,bytes.length,true);view.setUint32(10,54,true);view.setUint32(14,40,true);view.setInt32(18,this.w,true);view.setInt32(22,this.h,true);view.setUint16(26,1,true);view.setUint16(28,24,true);view.setUint32(34,stride*this.h,true);
      for(let y=0;y<this.h;y++)for(let x=0;x<this.w;x++){const s=(y*this.w+x)*4,d=54+(this.h-1-y)*stride+x*3;bytes[d]=this.data[s+2];bytes[d+1]=this.data[s+1];bytes[d+2]=this.data[s];}return bytes;
    }
    static fromBMP(bytes) {
      const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
      if(bytes.length<54||bytes[0]!==66||bytes[1]!==77||view.getUint32(14,true)!==40||view.getUint16(26,true)!==1||view.getUint32(30,true)!==0)throw Error('Only uncompressed Windows 24/32-bit BMP is supported');
      const w=view.getInt32(18,true),rawH=view.getInt32(22,true),h=Math.abs(rawH),bits=view.getUint16(28,true),offset=view.getUint32(10,true);bounds(w,h);
      if(![24,32].includes(bits))throw Error('Unsupported BMP bit depth');
      const stride=Math.ceil(w*(bits/8)/4)*4;if(offset<54||offset+stride*h>bytes.length)throw Error('Truncated BMP');
      const out=new Raster(w,h);for(let y=0;y<h;y++)for(let x=0;x<w;x++){const n=offset+(rawH>0?h-1-y:y)*stride+x*(bits/8);out.put(x,y,[bytes[n+2],bytes[n+1],bytes[n],255]);}return out;
    }
  }
  class History {
    constructor(raster){this.items=[raster.clone()];this.index=0;}
    push(raster){const current=this.items[this.index];if(current.w===raster.w&&current.h===raster.h&&current.data.every((v,i)=>v===raster.data[i]))return false;
      this.items.splice(this.index+1);this.items.push(raster.clone());this.index++;
      while(this.items.length>1&&(this.items.length>16||this.items.reduce((n,r)=>n+r.data.length,0)>32000000)){this.items.shift();this.index--;}return true;}
    undo(){return this.index>0?this.items[--this.index].clone():null;}
    redo(){return this.index<this.items.length-1?this.items[++this.index].clone():null;}
  }
  class Memory {
    constructor(id=globalThis.crypto.randomUUID()){this.id=id;this.events=[];this.root=null;}
    async init(){this.root=await hash(canonical({id:this.id,primer:PRIMER}));return this;}
    async append(kind,details){if(this.events.length>=4096)throw Error('Memory is full. Save the picture; recover the last verified organism for continuity.');
      const event={seq:this.events.length+1,prev:this.events.length?this.events.at(-1).hash:this.root,kind,details,at:new Date().toISOString()};event.hash=await hash(canonical(event));this.events.push(event);return event;}
  }
  async function project(raster,memory){return {schema:'mantle.paint-organism/1',expression:'bio-software',identity:memory.id,primer:PRIMER,image:{width:raster.w,height:raster.h,rgba:b64(raster.data),sha256:await hash(raster.data)},memory:{root:memory.root,events:memory.events.map(e=>({...e,details:{...e.details}}))}};}
  async function restore(text){if(typeof text!=='string'||text.length>16000000)throw Error('Organism file exceeds limit');
    const p=JSON.parse(text);if(p.schema!=='mantle.paint-organism/1'||p.expression!=='bio-software'||p.primer!==PRIMER||typeof p.identity!=='string'||p.identity.length>128||!p.identity||Object.keys(p).sort().join()!=='expression,identity,image,memory,primer,schema')throw Error('Unsupported organism, identity or founding PRIMER');
    const memory=await new Memory(p.identity).init();if(!p.memory||p.memory.root!==memory.root||!Array.isArray(p.memory.events)||p.memory.events.length>4096)throw Error('Invalid memory root');
    for(const entry of p.memory.events){const {hash:pin,...event}=entry;if(event.seq!==memory.events.length+1||event.prev!==(memory.events.at(-1)?.hash||memory.root)||typeof event.kind!=='string'||event.kind.length>64||typeof event.at!=='string'||!event.details||typeof event.details!=='object'||canonical(event).length>8192||await hash(canonical(event))!==pin)throw Error('Memory lineage mismatch');memory.events.push(entry);}
    const image=p.image;bounds(image.width,image.height);const bytes=unb64(image.rgba);if(bytes.length!==image.width*image.height*4||await hash(bytes)!==image.sha256||bytes.some((v,i)=>i%4===3&&v!==255))throw Error('Pixel integrity mismatch');
    if(memory.events.length&&memory.events.at(-1).details.imageSha256!==image.sha256)throw Error('Image is detached from its experience');
    return {raster:new Raster(image.width,image.height,'#ffffff',bytes),memory};
  }
  return {Raster,History,Memory,project,restore,hash,canonical,color,hex,palette,PRIMER,MAX_PIXELS,MAX_SIDE,imageDimensions};
});
