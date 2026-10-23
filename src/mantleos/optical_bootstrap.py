#!/usr/bin/env python3
"""Portable ChromaMem v5 bootstrap, distilled from the Raven Engram wire protocol.

stdlib-only: inspect or extract verified *carrier bytes*. No automatic code
execution, Persona adoption, host authority, or claim of full Body verification.
Use a trusted MantleOS host to verify the extracted Body before activation.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
from pathlib import PurePosixPath
import struct
import sys
import zipfile
import zlib

MAGIC=b'\x89PNG\r\n\x1a\n'

def reject(message):
    raise ValueError('Chroma bootstrap: '+message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def png_data(path):
    raw=Path(path).read_bytes()
    if not raw.startswith(MAGIC) or len(raw)>40_000_000:reject('Invalid/big PNG')
    pos=8; packed=bytearray(); annotation={};size=None;ended=False
    while pos+12<=len(raw):
        n,tag=struct.unpack('>I4s',raw[pos:pos+8]);pos+=8
        if n>40_000_000 or n>len(raw)-pos-4:reject('Bad PNG chunk')
        content=raw[pos:pos+n];pos+=n
        crc=struct.unpack('>I',raw[pos:pos+4])[0];pos+=4
        if zlib.crc32(tag+content)&0xffffffff!=crc:reject('Bad PNG CRC')
        if tag==b'IHDR':
            if size is not None or len(content)!=13:reject('Invalid IHDR')
            w,h,depth,mode,cm,fm,il=struct.unpack('>IIBBBBB',content)
            if not 0<w*h<=10_000_000 or (depth,mode,cm,fm,il)!=(8,2,0,0,0):reject('Unsupported PNG')
            size=(w,h)
        elif tag==b'IDAT':
            packed.extend(content)
            if len(packed)>40_000_000:reject('IDAT too large')
        elif tag==b'iTXt':
            key,rest=content.split(b'\0',1);flag,method=rest[:2];rest=rest[2:]
            lang,rest=rest.split(b'\0',1);translated,value=rest.split(b'\0',1)
            if key in annotation or flag not in (0,1) or method or lang or translated:reject('Bad iTXt')
            if flag:
                dec=zlib.decompressobj();value=dec.decompress(value,20_001)
                if not dec.eof or dec.unused_data or dec.unconsumed_tail:reject('Bad iTXt stream')
            if len(value)>20_000:reject('iTXt too long')
            annotation[key.decode('ascii')]=value.decode('utf-8')
        elif tag==b'IEND':
            if n or pos!=len(raw):reject('Bad IEND')
            ended=True;break
        elif not tag[0]&32:reject('Unknown critical chunk')
    if not ended or size is None or not packed:reject('Incomplete PNG')
    w,h=size; stride=w*3;length=h*(stride+1)
    dec=zlib.decompressobj();data=dec.decompress(bytes(packed),length+1)
    if len(data)!=length or not dec.eof or dec.unused_data or dec.unconsumed_tail:reject('Invalid raster')
    pixels=bytearray();previous=bytes(stride);pos=0
    for _ in range(h):
        kind=data[pos];pos+=1;row=bytearray(data[pos:pos+stride]);pos+=stride
        if kind>4:reject('Invalid PNG filter')
        # Filter 0 is already reconstructed, including the next row's input.
        if kind==0:
            pixels.extend(row);previous=row
            continue
        for j in range(stride):
            a=row[j-3] if j>=3 else 0;b=previous[j];c=previous[j-3] if j>=3 else 0
            if kind==1:f=a
            elif kind==2:f=b
            elif kind==3:f=(a+b)//2
            elif kind==4:
                p=a+b-c;da,db,dc=abs(p-a),abs(p-b),abs(p-c)
                f=a if da<=db and da<=dc else b if db<=dc else c
            else:f=0
            row[j]=(row[j]+f)&255
        pixels.extend(row);previous=row
    return bytes(pixels),annotation

def inspect(path):
    pixels,notes=png_data(path)
    if len(pixels)<42 or pixels[:5]!=b'CMEM\x05' or pixels[41]:reject('Not ChromaMem v5')
    count=int.from_bytes(pixels[5:9],'big')
    if count>100_000:reject('Too many records')
    offset=42;rows=[];ids={}
    for ix in range(count):
        if offset+20>len(pixels):reject('Truncated record')
        channels=pixels[offset:offset+12];offset+=12
        if any(channels[j]^channels[j+3]^channels[j+6]!=channels[j+9] for j in range(3)):
            reject('Record parity')
        ml,tl=struct.unpack('>II',pixels[offset:offset+8]);offset+=8
        if ml>1_000_000 or tl>10_000_000 or offset+ml+tl>len(pixels):reject('Bad record lengths')
        meta=json.loads(pixels[offset:offset+ml].decode('utf8'));offset+=ml
        value=pixels[offset:offset+tl].decode('utf8');offset+=tl
        if not isinstance(meta,dict) or not isinstance(meta.get('id'),str) or not meta['id'] or meta['id'] in ids:reject('Duplicate/missing ID')
        pad=(-offset)%3
        if any(pixels[offset:offset+pad]):reject('Nonzero record pad')
        offset+=pad
        rows.append(meta['id']);ids[meta['id']]=(meta,value)
    if hashlib.sha256(pixels[42:offset]).digest()!=pixels[9:41] or any(pixels[offset:]):reject('Tape hash/padding')
    for meta,value in ids.values():
        for link in meta.get('links',[]):
            if not isinstance(link,dict) or link.get('to') not in ids:reject('Broken link')
    manifests=[r for r in rows if r.startswith('agent.package.manifest.')]
    if not manifests:reject('No package manifest')
    selected=manifests[-1];manifest=json.loads(ids[selected][1])
    if manifest.get('schema')!='mantle.engram-image-package/2':reject('Manifest version')
    keys={'primer':('primer_id','primer_sha256'),'host':('host_contract_id','host_contract_sha256'),
          'prompt':('prompt_id','mount_prompt_sha256'),'runtime':('runtime_id','runtime_sha256'),
          'schema':('schema_id','schema_sha256'),'ledger':('ledger_id','source_ledger_sha256'),
          'resume':('resume_id','resume_sha256'),'validation':('bridge_validation_id','bridge_validation_sha256')}
    for name,(ref,digest) in keys.items():
        if manifest.get(ref) not in ids or sha(ids[manifest[ref]][1].encode('utf8'))!=manifest.get(digest):reject('Bad '+name+' reference')
    parts=manifest.get('bundle_part_ids')
    if not isinstance(parts,list) or not parts or len(parts)>100 or parts[0]!=manifest.get('bundle_id') or len(set(parts))!=len(parts):reject('Bad archive index')
    try:archive=base64.b64decode(''.join(ids[key][1] for key in parts),validate=True)
    except (KeyError,ValueError) as exc:raise ValueError('Invalid archive payload') from exc
    if sha(archive)!=manifest.get('bundle_sha256') or len(archive)>50_000_000:reject('Bad archive digest/size')
    boot=None
    if 'AgentChroma' in notes:
        if 'ChromaMem' not in notes:reject('Missing format protocol')
        boot=json.loads(notes['AgentChroma'])
        if boot.get('schema')!='AgentChroma/0.2' or boot.get('manifest_id')!=selected:reject('Bootstrap mismatch')
        if boot.get('primer_id')!=manifest['primer_id'] or boot.get('primer_sha256')!=manifest['primer_sha256']:reject('Primer mismatch')
        ix=boot.get('primer_record')
        if type(ix) is not int or not 0<=ix<len(rows) or rows[ix]!=boot['primer_id']:reject('Primer index mismatch')
        if boot.get('auto_execute') is not False:reject('Unsafe native execution policy')
        if boot.get('bootstrap_id'):
            if boot['bootstrap_id'] not in ids or sha(ids[boot['bootstrap_id']][1].encode())!=manifest.get('bootstrap_sha256'):reject('Bootstrap source mismatch')
            if notes.get('ChromaLoader')!=ids[boot['bootstrap_id']][1]:reject('Embedded portable loader mismatch')
    ledger=ids[manifest['ledger_id']][1].encode()
    if not boot:reject('Missing current bootstrap')
    if sha(ledger)!=manifest['source_ledger_sha256']:reject('Ledger hash')
    if len(ledger.splitlines())!=manifest.get('ledger_records'):reject('Ledger count')
    return {'schema':'mantle.portable-chroma/1','records':len(rows),'manifest':selected,
            'agent_id':manifest.get('agent_id'),'ledger_sha256':sha(ledger),
            'bootstrap':'VERIFIED','executed':False},archive,manifest,ledger

def extract(path,destination):
    info,archive,manifest,ledger=inspect(path)
    if manifest['schema']!='mantle.engram-image-package/2' or manifest.get('bundle_role')!='VERIFIED_CARTRIDGE_BODY':
        reject('Historical artifact is inspect-only; native Body required')
    target=Path(destination).resolve()
    if target.exists() or not target.parent.is_dir():reject('Need a new destination under an existing parent')
    with zipfile.ZipFile(io.BytesIO(archive)) as zipfile_in:
        members=zipfile_in.infolist()
        if len(members)>5000 or sum(m.file_size for m in members)>50_000_000:reject('Oversized archive')
        seen=set()
        for member in members:
            name=member.filename
            mode=(member.external_attr>>16)&0o170000
            if (not name or name in seen or PurePosixPath(name).as_posix()!=name
                or name.startswith('/') or '\\' in name or ':' in name
                or '..' in name.split('/') or name.endswith('/') or mode not in (0,0o100000)):
                reject('Unsafe archive path')
            seen.add(name)
        if 'MANIFEST.json' not in seen or 'ENGRAM.jsonl' not in seen:reject('Body files missing')
        if sha(zipfile_in.read('MANIFEST.json'))!=manifest.get('body_manifest_sha256') or zipfile_in.read('ENGRAM.jsonl')!=ledger:reject('Bundle/ledger mismatch')
        import tempfile,shutil
        temp=Path(tempfile.mkdtemp(prefix='.chroma-',dir=target.parent))
        try:
            for member in members:
                dest=temp/member.filename;dest.parent.mkdir(parents=True,exist_ok=True)
                with zipfile_in.open(member) as source, dest.open('xb') as out:shutil.copyfileobj(source,out)
            # This tool validates a carrier but does not certify the Body; run
            # trusted MantleOS verify on the extracted directory before use.
            if target.exists():reject('Destination appeared during unpack')
            temp.rename(target)
        finally:
            if temp.exists():shutil.rmtree(temp)
    return {**info,'output':str(target),'carrier':'VERIFIED','body':'UNVERIFIED_UNTIL_TRUSTED_HOST_VERIFY'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inspect','extract'])
    parser.add_argument('image');parser.add_argument('--output')
    args=parser.parse_args()
    if args.action=='extract' and not args.output:parser.error('--output required')
    value=inspect(args.image)[0] if args.action=='inspect' else extract(args.image,args.output)
    print(json.dumps(value,indent=2,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,zipfile.BadZipFile,zlib.error) as exc:
        print('FAIL: '+str(exc),file=sys.stderr);sys.exit(2)
