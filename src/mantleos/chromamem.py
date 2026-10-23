"""ChromaMem v5 optical kernel: validated decoding and self-describing export.

Untrusted records are data. This decoder never executes embedded Python,
installs a Cartridge, adopts a Persona, or authorizes a host capability.
"""
from __future__ import annotations

import base64
import hashlib
import io
import math
import shutil
import tempfile
import json
from pathlib import Path
import struct
import zipfile
import zlib

SIGNATURE = b'\x89PNG\r\n\x1a\n'
MAX_PIXELS = 10_000_000
MAX_RECORDS = 100_000
ACTIVE_MANIFEST = 'auto'  # last tape manifest; explicit historic IDs still accepted
NATIVE_MANIFEST = 'agent.package.manifest.mantleos.001'
BOOT_SCHEMA = 'AgentChroma/0.2'  # Raven reference carrier's interoperable bootstrap ABI
CHROMA_PROTOCOL = '''ChromaMem v5 — self-decoding append-only memory
Pixel tape: 8-bit noninterlaced RGB PNG, row-major R/G/B bytes; iTXt ChromaMem
describes decoding, iTXt AgentChroma selects the manifest and primer, and
iTXt ChromaLoader carries the isolated stdlib-only recovery script.
42-byte tape header: CMEM | version 5 | u32 record count | SHA256(padded body) | zero.
Each record: STATE[3] | STRUCTURE[3] | CONTEXT[3] | XOR PARITY[3] |
u32 meta length | u32 text length | canonical UTF-8 JSON meta | UTF-8 text |
zero pad to RGB byte boundary. Links reference record IDs. The final manifest is
active, historic records are immutable on append; SHA256 manifest binds payloads.
Bit order for every byte: 128,64,32,16,8,4,2,1.
STATE R/evidence: reported observed measured inspected inferred claimed evidence established
STATE G/force: possible likely must forbidden should permitted not_required capable
STATE B/status: unknown missing not_reported unverified exact lower_bound upper_bound ambiguous
STRUCTURE R/logic: negated conditional alternative exception conjunction disjunction non_entailment causal
STRUCTURE G/quantifier: all each some none only exactly at_least at_most
STRUCTURE B/scope: description_bound condition_scope exception_scope attribution_scope evidence_relation execution_boundary literal temporal
CONTEXT R/graph: grouped outgoing_link incoming_link cross_group_outgoing multi_outgoing multi_incoming self_link dangling_outgoing
CONTEXT G/boundary: temporal literal execution_boundary attribution_scope evidence_relation condition_scope exception_scope description_bound
CONTEXT B/form: has_id has_group has_links non_ascii backtick_literal numeric_literal clock_literal date_literal
STATE/STRUCTURE/CONTEXT are semantic descriptors, NOT checksums or authority.
Host must verify body, primer and journal and explicitly approve any execution.
ORIENT -> checked action -> RESPOND -> commit, with no automatic host effects.
If execution is unavailable, disclose that bridge operations were not performed.
'''
MAX_FILE_BYTES = 40_000_000
MAX_ARCHIVE_BYTES = 50_000_000


class ChromaMemError(ValueError):
    pass


def _png_data(path):
    raw = Path(path).read_bytes()
    if len(raw) > 40_000_000 or not raw.startswith(SIGNATURE):
        raise ChromaMemError('Not a bounded PNG')
    index = 8; width=height=None; compressed=bytearray(); seen_iend=False; seen_ihdr=False
    metadata={}
    while index + 12 <= len(raw):
        length = struct.unpack('>I', raw[index:index+4])[0]
        tag = raw[index+4:index+8]
        if length > 40_000_000 or index+12+length>len(raw):
            raise ChromaMemError('Corrupt PNG chunk length')
        payload = raw[index+8:index+8+length]
        crc = struct.unpack('>I', raw[index+8+length:index+12+length])[0]
        if zlib.crc32(tag+payload)&0xffffffff != crc:
            raise ChromaMemError('PNG chunk CRC mismatch')
        index+=12+length
        if tag==b'IHDR':
            if seen_ihdr or length != 13: raise ChromaMemError('Invalid PNG header')
            seen_ihdr=True
            width,height,depth,mode,compression,filter_mode,interlace=struct.unpack('>IIBBBBB',payload)
            if not (0<width*height<=MAX_PIXELS and depth==8 and mode==2 and compression==0 and filter_mode==0 and interlace==0):
                raise ChromaMemError('ChromaMem requires 8-bit noninterlaced RGB PNG')
        elif tag==b'IDAT':
            if not seen_ihdr: raise ChromaMemError('IDAT before IHDR')
            compressed.extend(payload)
            if len(compressed)>40_000_000:raise ChromaMemError('Too much compressed image data')
        elif tag==b'IEND':
            if length: raise ChromaMemError('Invalid IEND')
            seen_iend=True
            if index!=len(raw):raise ChromaMemError('Trailing PNG bytes')
            break
        elif tag==b'iTXt':
            try:
                key,rest=payload.split(b'\0',1)
                if not key or key in metadata or len(key)>79:raise ValueError('Invalid iTXt key')
                flag,method=rest[:2];rest=rest[2:]
                language,rest=rest.split(b'\0',1)
                translated,value=rest.split(b'\0',1)
                if flag not in (0,1) or method!=0 or language or translated:
                    raise ValueError('Unsupported iTXt encoding')
                if flag:
                    inflater=zlib.decompressobj()
                    value=inflater.decompress(value,20_001)
                    if not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
                        raise ValueError('Invalid compressed iTXt')
                if len(value)>20_000:raise ValueError('Oversized iTXt')
                metadata[key.decode('ascii')]=value.decode('utf-8')
            except (ValueError, UnicodeError, zlib.error) as exc:
                raise ChromaMemError('Malformed Chroma bootstrap metadata') from exc
        elif not tag[0]&32:
            raise ChromaMemError('Unsupported critical PNG chunk')
    if not seen_ihdr or not seen_iend or not compressed:raise ChromaMemError('Incomplete PNG')
    stride = width*3; length = height*(stride+1)
    dec=zlib.decompressobj()
    data=dec.decompress(bytes(compressed), length+1)
    if len(data)!=length or not dec.eof or dec.unconsumed_tail or dec.unused_data:
        raise ChromaMemError('Invalid PNG pixel byte length')
    pos=0; prev=bytes(stride); pixels=bytearray()
    for _ in range(height):
        filt=data[pos]; pos+=1
        current=bytearray(data[pos:pos+stride]);pos+=stride
        if filt>4:raise ChromaMemError('Unknown PNG filter')
        # Filter 0 already contains reconstructed bytes; retain the row for
        # the next row's predictors without a Python loop over every byte.
        if filt==0:
            pixels.extend(current); prev=current
            continue
        for j in range(stride):
            a=current[j-3] if j>=3 else 0
            b=prev[j];c=prev[j-3] if j>=3 else 0
            if filt==1: predict=a
            elif filt==2:predict=b
            elif filt==3:predict=(a+b)//2
            elif filt==4:
                p=a+b-c; da,db,dc=abs(p-a),abs(p-b),abs(p-c)
                predict=a if da<=db and da<=dc else b if db<=dc else c
            else:predict=0
            current[j]=(current[j]+predict)&255
        pixels.extend(current); prev=current
    return bytes(pixels),metadata


def _png_rgb(path):
    return _png_data(path)[0]


def decode(path):
    b,metadata=_png_data(path)
    if len(b)<42 or b[:4]!=b'CMEM' or b[4]!=5 or b[41]!=0:
        raise ChromaMemError('Invalid ChromaMem v5 header')
    count=struct.unpack('>I',b[5:9])[0]
    if count>MAX_RECORDS:raise ChromaMemError('Too many ChromaMem records')
    pos=42;rows=[];by_id={}
    for idx in range(count):
        start=pos
        if pos+20>len(b):raise ChromaMemError('Truncated record')
        parity=b[pos:pos+12];pos+=12
        if any(parity[j]^parity[j+3]^parity[j+6]!=parity[j+9] for j in range(3)):
            raise ChromaMemError('Record parity mismatch')
        ml,tl=struct.unpack('>II',b[pos:pos+8]);pos+=8
        if ml>1_000_000 or tl>10_000_000 or pos+ml+tl>len(b):
            raise ChromaMemError('Invalid record lengths')
        try:
            meta=json.loads(b[pos:pos+ml].decode('utf-8'));pos+=ml
            content=b[pos:pos+tl].decode('utf-8');pos+=tl
        except (ValueError,UnicodeError) as exc:raise ChromaMemError('Invalid record metadata/text') from exc
        if not isinstance(meta,dict) or not isinstance(meta.get('id'),str) or not meta['id'] or meta['id'] in by_id:
            raise ChromaMemError('Missing/duplicate record identity')
        pad=(-pos)%3
        if b[pos:pos+pad]!=bytes(pad):raise ChromaMemError('Invalid record padding')
        pos+=pad
        row={'meta':meta,'text':content,'index':idx,'raw':b[start:pos]}
        rows.append(row);by_id[meta['id']]=row
    if hashlib.sha256(b[42:pos]).digest()!=b[9:41] or any(b[pos:]):
        raise ChromaMemError('ChromaMem body checksum/trailing padding mismatch')
    for row in rows:
        for link in row['meta'].get('links',[]):
            if not isinstance(link,dict) or link.get('to') not in by_id:
                raise ChromaMemError('Broken ChromaMem record link')
    return {'records':rows,'by_id':by_id,'body_sha256':hashlib.sha256(b[42:pos]).hexdigest(),
            'body_bytes':pos-42,'pixel_bytes':len(b),'metadata':metadata}


def verify_bootstrap(decoded,manifest,manifest_id=ACTIVE_MANIFEST):
    """Check mandatory current AgentChroma pointers without executing data."""
    metadata=decoded['metadata']
    if 'AgentChroma' not in metadata:
        raise ChromaMemError('Missing current AgentChroma bootstrap')
    if 'ChromaMem' not in metadata or 'ChromaMem v5' not in metadata['ChromaMem']:
        raise ChromaMemError('Missing optical decoding protocol')
    try: boot=json.loads(metadata['AgentChroma'])
    except (ValueError,UnicodeError) as exc:raise ChromaMemError('Invalid AgentChroma metadata') from exc
    if not isinstance(boot,dict) or boot.get('schema')!=BOOT_SCHEMA:
        raise ChromaMemError('Unsupported AgentChroma bootstrap')
    if boot.get('manifest_id')!=_manifest_id(decoded,manifest_id):
        raise ChromaMemError('Bootstrap active manifest mismatch')
    if boot.get('primer_id') != manifest['primer_id'] or boot.get('primer_sha256')!=manifest['primer_sha256']:
        raise ChromaMemError('AgentChroma primer contract mismatch')
    rows=decoded['records']; idx=boot.get('primer_record')
    if type(idx) is not int or idx<0 or idx>=len(rows) or rows[idx]['meta']['id']!=boot['primer_id']:
        raise ChromaMemError('AgentChroma primer index mismatch')
    for pointer,key in (('prompt_id','prompt_id'),('ledger_id','ledger_id'),('runtime_id','runtime_id'),
                        ('host_contract_id','host_contract_id'),('source_bundle_id','bundle_id')):
        if boot.get(pointer)!=manifest[key]:raise ChromaMemError('AgentChroma '+pointer+' mismatch')
    if boot.get('mount_protocol')!='HOSTED_BRIDGE_REQUIRED':
        raise ChromaMemError('Chroma mount protocol must use checked hosted bridge')
    if boot.get('auto_execute') is not False:
        raise ChromaMemError('Native Chroma cannot enable automatic embedded execution')
    if manifest.get('bootstrap_id'):
        if boot.get('bootstrap_id') != manifest['bootstrap_id']:
            raise ChromaMemError('Chroma bootstrap code reference mismatch')
        source=decoded['by_id'].get(manifest['bootstrap_id'])
        if source is None or _digest(source['text'].encode('utf-8'))!=manifest.get('bootstrap_sha256'):
            raise ChromaMemError('Chroma bootstrap code digest mismatch')
        if metadata.get('ChromaLoader')!=source['text']:
            raise ChromaMemError('Optical bootstrap is not self-contained')
    return {'status':'VERIFIED','host_bridge':'HOSTED_BRIDGE_REQUIRED','auto_execute':False}


def _manifest_id(decoded, requested=ACTIVE_MANIFEST):
    if requested == 'auto':
        candidates=[r['meta']['id'] for r in decoded['records']
                    if r['meta']['id'].startswith('agent.package.manifest.')]
        if not candidates: raise ChromaMemError('Image has no package manifest')
        return candidates[-1]   # tape append order is the only automatic ordering
    if requested not in decoded['by_id']:
        raise ChromaMemError('Unknown active manifest; choose one explicitly')
    return requested


def verify_manifest(decoded, manifest_id=ACTIVE_MANIFEST):
    by_id=decoded['by_id']
    manifest_id=_manifest_id(decoded,manifest_id)
    try:manifest=json.loads(by_id[manifest_id]['text'])
    except (ValueError,UnicodeError) as exc:raise ChromaMemError('Invalid manifest JSON') from exc
    if not isinstance(manifest,dict) or manifest.get('schema') != 'mantle.engram-image-package/2':
        raise ChromaMemError('Unsupported ChromaMem package manifest')
    specs={'primer':('primer_id','primer_sha256',False),
           'host_contract':('host_contract_id','host_contract_sha256',False),
           'prompt':('prompt_id','mount_prompt_sha256',False),
           'runtime':('runtime_id','runtime_sha256',False),
           'schema':('schema_id','schema_sha256',False),
           'ledger':('ledger_id','source_ledger_sha256',False),
           'resume':('resume_id','resume_sha256',False),
           'bridge_validation':('bridge_validation_id','bridge_validation_sha256',False),
           'source_bundle':('bundle_id','bundle_sha256',True)}
    try:
        for name,(id_key,hash_key,encoded) in specs.items():
            source=(base64.b64decode(_bundle_text(decoded,manifest),validate=True)
                    if encoded else by_id[manifest[id_key]]['text'].encode('utf-8'))
            if hashlib.sha256(source).hexdigest()!=manifest[hash_key]:
                raise ChromaMemError('Manifest '+name+' checksum mismatch')
    except (KeyError,TypeError,ValueError) as exc:raise ChromaMemError('Invalid manifest reference or digest: '+str(exc)) from exc
    if manifest.get('bootstrap_id'):
        row=by_id.get(manifest['bootstrap_id'])
        if row is None or _digest(row['text'].encode('utf-8'))!=manifest.get('bootstrap_sha256'):
            raise ChromaMemError('Native portable bootstrap checksum mismatch')
    return manifest


def _bundle_text(decoded,manifest):
    parts=manifest.get('bundle_part_ids')
    if not isinstance(parts,list) or not parts or len(parts)>100 or parts[0]!=manifest.get('bundle_id') or len(set(parts))!=len(parts):
        raise ChromaMemError('Invalid Chroma bundle part index')
    try:return ''.join(decoded['by_id'][part]['text'] for part in parts)
    except (KeyError,TypeError) as exc:raise ChromaMemError('Missing Chroma source bundle part') from exc


def safe_bundle(decoded,manifest):
    raw=base64.b64decode(_bundle_text(decoded,manifest),validate=True)
    archive,items=_checked_archive(raw)
    with archive:
        _validate_native_bundle(decoded,manifest)
        return len(items)


def inspect(path, *, manifest_id=ACTIVE_MANIFEST):
    decoded=decode(path);manifest=verify_manifest(decoded,manifest_id)
    bootstrap=verify_bootstrap(decoded,manifest,manifest_id)
    ledger=decoded['by_id'][manifest['ledger_id']]['text']
    historical=decoded['by_id'].get('mantle.engram.ledger.2026')
    if historical is not None and not ledger.startswith(historical['text']):
        raise ChromaMemError('Historical ledger prefix mismatch')
    from tempfile import TemporaryDirectory
    from .engram import read, ZERO
    with TemporaryDirectory() as td:
        p=Path(td)/'ENGRAM.jsonl';p.write_text(ledger,encoding='utf-8'); records=read(p)
    ledger_head=records[-1]['sha256'] if records else ZERO
    if manifest.get('ledger_records')!=len(records) or manifest.get('ledger_head')!=ledger_head:
        raise ChromaMemError('Native carrier ledger identity mismatch')
    return {'schema':'mantle.engram-image-inspection/1','format':'ChromaMem/5','records':len(decoded['records']),
            'manifest':_manifest_id(decoded,manifest_id),'manifest_hashes':'VERIFIED','body_sha256':decoded['body_sha256'],
            'ledger_records':len(records),'ledger_head':ledger_head,
            'historical_prefix_preserved':historical is not None,'embedded_archive_members':safe_bundle(decoded,manifest),
            'bootstrap':bootstrap['status'],'host_bridge':bootstrap.get('host_bridge'),
            'executed':False,'mounted':False,'claimed_effect':'NONE'}


def extract_ledger(path, output, *, manifest_id=ACTIVE_MANIFEST, expected_prefix=None):
    """Explicitly copy validated ledger to new path. Does NOT import into a live Body."""
    summary=inspect(path,manifest_id=manifest_id)
    decoded=decode(path);manifest=verify_manifest(decoded,manifest_id)
    ledger=decoded['by_id'][manifest['ledger_id']]['text'].encode('utf-8')
    if expected_prefix is not None:
        prefix=Path(expected_prefix).read_bytes()
        if not ledger.startswith(prefix):raise ChromaMemError('Current continuity is not the exact preserved prefix')
        summary['expected_prefix_bytes']=len(prefix)
    target=Path(output)
    if target.exists():raise FileExistsError('Engram extraction never overwrites an existing file')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(ledger)
    return {'schema':'mantle.engram-image-extraction/1','destination':str(target.resolve()),
            'ledger_sha256':hashlib.sha256(ledger).hexdigest(),**summary}


def extract_bootstrap(path,output):
    """Materialize the self-contained image decoder; never execute it."""
    decoded=decode(path); manifest=verify_manifest(decoded)
    verify_bootstrap(decoded,manifest)
    name=manifest.get('bootstrap_id')
    if not name:raise ChromaMemError('This Chroma image has no embedded portable loader')
    target=Path(output)
    if target.exists():raise FileExistsError('Bootstrap output already exists')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as out:out.write(decoded['by_id'][name]['text'].encode('utf-8'))
    return {'schema':'mantle.chroma-bootstrap-extraction/1','output':str(target.resolve()),
            'sha256':manifest['bootstrap_sha256'],'executed':False}


# ChromaMem writing shares the reader's exact tape/CRC framing. No second
# thought language or memory store is created: exported bytes are an immutable
# snapshot of the verified Cartridge Body with its canonical Engram journal.
def _canonical(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True)


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _record(name,text,group,links=()):
    meta={'id':name,'group':group}
    if links: meta['links']=[{'rel':relation,'to':target} for relation,target in links]
    return (meta,text)


def _png_chunk(tag,payload):
    return (struct.pack('>I',len(payload))+tag+payload+
            struct.pack('>I',zlib.crc32(tag+payload)&0xffffffff))


def _encode(records, *, bootstrap=None, protocol=None, loader=None):
    """Encode a bounded ChromaMem v5 RGB PNG with canonical record digests."""
    if len(records)>MAX_RECORDS: raise ChromaMemError('Too many tape records')
    body=bytearray()
    for record in records:
        meta,text=record[:2]
        if len(record)==3:
            # Preserve every old record byte, including its original semantic
            # channels and exact JSON serialization, on self-templated re-SAVE.
            body.extend(record[2])
            continue
        mb=_canonical(meta).encode('utf-8');tb=text.encode('utf-8')
        if len(mb)>1_000_000 or len(tb)>10_000_000:
            raise ChromaMemError('Chroma record too large; use a smaller Body')
        # Interpret Raven's semantic channels, not as a pseudo-random content
        # hash. Labels describe *record structure*, not epistemic truth.
        form=(0x80 if meta.get('id') else 0)|(0x40 if meta.get('group') else 0)
        if meta.get('links'):form|=0x20
        if any(ord(c)>127 for c in text):form|=0x10
        if '`' in text:form|=0x08
        state=b'\x01\x00\x00'  # established = record structurally admitted
        structure=b'\x00\x00\x80'  # description-bound, not a statement of authority
        context=bytes([(0x80 if meta.get('group') else 0)|(0x40 if meta.get('links') else 0),0,form])
        parity=state+structure+context
        parity+=bytes(parity[j]^parity[j+3]^parity[j+6] for j in range(3))
        body.extend(parity+struct.pack('>II',len(mb),len(tb))+mb+tb)
        body.extend(bytes((-len(body))%3))
    header=b'CMEM'+b'\x05'+struct.pack('>I',len(records))+hashlib.sha256(body).digest()+b'\x00'
    tape=header+body
    width=1024
    height=math.ceil(len(tape)/(width*3))
    if height*width>MAX_PIXELS:raise ChromaMemError('Chroma snapshot exceeds bounded PNG pixel capacity')
    tape=tape.ljust(height*width*3,b'\x00')
    from .cells import rgb_tape
    rgb_tape(tape)
    compressor=zlib.compressobj(level=9)
    compressed=bytearray()
    stride=width*3
    for off in range(0,len(tape),stride):
        compressed.extend(compressor.compress(b'\x00'+tape[off:off+stride]))
    compressed.extend(compressor.flush())
    if len(compressed)>MAX_FILE_BYTES-100:raise ChromaMemError('Compressed PNG exceeds size budget')
    annotations=b''
    for key,value in (('ChromaMem',protocol),('AgentChroma',_canonical(bootstrap) if bootstrap else None),('ChromaLoader',loader)):
        if value is not None:
            annotations+=_png_chunk(b'iTXt',key.encode('ascii')+b'\0\x01\0\0\0'+zlib.compress(value.encode('utf-8'),9))
    png=(SIGNATURE+_png_chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
         annotations+_png_chunk(b'IDAT',compressed)+_png_chunk(b'IEND',b''))
    if len(png)>MAX_FILE_BYTES:raise ChromaMemError('PNG exceeds size budget')
    return png


def _bundle(body):
    """An explicit, digest-checked Cartridge directory, not executable on inspect."""
    from .cartridge import tracked_paths,validate_portable_tree
    body=Path(body)
    validate_portable_tree(body)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as arc:
        for path,name in [*tracked_paths(body),(body/'MANIFEST.json','MANIFEST.json')]:
            if not path.is_file():raise ChromaMemError('Body manifest missing')
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            arc.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    data=out.getvalue()
    if len(data)>MAX_ARCHIVE_BYTES:raise ChromaMemError('Chroma Body archive exceeds capacity')
    return data


def _body_records(body):
    from . import cartridge,checkpoint,engram
    body=Path(body)
    verified=cartridge.verify(body)
    ledger=(body/'ENGRAM.jsonl').read_text('utf-8')
    primer=(body/'PRIMER/COMMANDMENTS.md').read_text('utf-8')+'\n'+(body/'PRIMER/PERSONA.md').read_text('utf-8')
    host=(body/'HOSTED-BRIDGE.md').read_text('utf-8') if (body/'HOSTED-BRIDGE.md').is_file() else 'Host bridge: no automatic host effects. Explicit mount and checks required.'
    prompt=checkpoint.render(body)
    runtime=(body/'runtime.py').read_text('utf-8') if (body/'runtime.py').exists() else '# Launch verified Body with mantleos.application; no embedded code is executed automatically.\n'
    schema=(body/'COGNITIVE-SEED.json').read_text('utf-8')
    archive=_bundle(body)
    resume=_canonical({'schema':'mantle.chroma-resume/1','agent_id':verified['bio_software'],
                       'ledger_head':engram.head(body/'ENGRAM.jsonl'),
                       'authority':'VERIFIED_BODY_ONLY','thought_language':'anchor.coding.conversation/1.1',
                       'auto_execute':False})
    validation=_canonical({'schema':'mantle.chroma-export-validation/1',
                           'body_verify':'PASS','tracked_files':verified['tracked_files'],
                           'manifest_sha256':_digest((body/'MANIFEST.json').read_bytes()),
                           'ledger_head':engram.head(body/'ENGRAM.jsonl')})
    portable_source=Path(__file__).with_name('optical_bootstrap.py').read_text('utf-8')
    entries=[('primer',primer,'PRIMER'),('host_contract',host,'CONTRACT'),('prompt',prompt,'PROJECTION'),
             ('runtime',runtime,'RUNTIME_DATA'),('schema',schema,'SCHEMA'),('ledger',ledger,'MEMORY'),
             ('resume',resume,'CONTINUITY'),('bridge_validation',validation,'VALIDATION')]
    ids={k:'mantle.engram.'+k+'.001' for k,_,_ in entries}
    specs={'primer':('primer_id','primer_sha256'),'host_contract':('host_contract_id','host_contract_sha256'),
           'prompt':('prompt_id','mount_prompt_sha256'),'runtime':('runtime_id','runtime_sha256'),
           'schema':('schema_id','schema_sha256'),'ledger':('ledger_id','source_ledger_sha256'),
           'resume':('resume_id','resume_sha256'),'bridge_validation':('bridge_validation_id','bridge_validation_sha256'),
           'source_bundle':('bundle_id','bundle_sha256')}
    manifest={'schema':'mantle.engram-image-package/2','agent_id':verified['bio_software'],
              'cartridge_id':verified['cartridge_id'],'kernel':'chroma','carrier':'ChromaMem/5',
              'default_kernel':'cartridge','thought_language':'anchor.coding.conversation/1.1',
              'bundle_role':'VERIFIED_CARTRIDGE_BODY','body_manifest_sha256':_digest((body/'MANIFEST.json').read_bytes()),
              'ledger_records':len(engram.read(body/'ENGRAM.jsonl')),
              'ledger_head':engram.head(body/'ENGRAM.jsonl'),
              'mount_policy':'EXPLICIT_VERIFIED_RECONSTRUCTION_NO_AUTO_EXECUTION'}
    manifest['bootstrap_id']='mantle.engram.portable_bootstrap.001'
    manifest['bootstrap_sha256']=_digest(portable_source.encode('utf-8'))
    records=[]
    for key,value,group in entries:
        id_key,hash_key=specs[key]
        manifest[id_key]=ids[key]
        manifest[hash_key]=_digest(archive if key=='source_bundle' else value.encode('utf-8'))
        records.append(_record(ids[key],value,group))
    # ChromaMem v5 requires each record text to remain <= 10 MB; the ZIP
    # (including the portable Windows Python runtime) is split into 8 MB base64
    # pieces rather than dropped or weakened. Parts are joined before digesting.
    encoded=base64.b64encode(archive).decode('ascii')
    chunks=[encoded[i:i+8_000_000] for i in range(0,len(encoded),8_000_000)]
    if not chunks:raise ChromaMemError('Empty Body archive')
    part_ids=['mantle.engram.source_bundle.part.%04d'%(i+1) for i in range(len(chunks))]
    manifest['bundle_id']=part_ids[0]
    manifest['bundle_part_ids']=part_ids
    manifest['bundle_sha256']=_digest(archive)
    for part_id,chunk in zip(part_ids,chunks):
        records.append(_record(part_id,chunk,'BODY_ARCHIVE'))
    records.append(_record(manifest['bootstrap_id'],portable_source,'PORTABLE_LOADER'))
    records.append(_record(NATIVE_MANIFEST,_canonical(manifest),'MANIFEST',
                           [(key,ids[key]) for key,_,_ in entries]+[('source_bundle_part',part) for part in part_ids]+
                           [('portable_loader',manifest['bootstrap_id'])]))
    return records,manifest


def _agent_bootstrap(records,manifest,manifest_id=NATIVE_MANIFEST):
    primer=manifest['primer_id']
    primer_index=next(i for i,row in enumerate(records) if row[0]['id']==primer)
    return {'schema':BOOT_SCHEMA,'mantleos_schema':'mantle.engram-image/2',
            'authoritative':'tape','boot':'EXPLICIT_HOST_BRIDGE','auto_execute':False,
            'manifest_id':manifest_id,'primer_id':primer,'primer_record':primer_index,
            'primer_sha256':manifest['primer_sha256'],
            'prompt_id':manifest['prompt_id'],'ledger_id':manifest['ledger_id'],
            'host_contract_id':manifest['host_contract_id'],'runtime_id':manifest['runtime_id'],
            'source_bundle_id':manifest['bundle_id'],'bootstrap_id':manifest['bootstrap_id'],
            'mount_protocol':'HOSTED_BRIDGE_REQUIRED',
            'mount_command':'python chroma_host.py extract INPUT.png --output NEW_BODY',
            'activation':'Extract the ChromaLoader iTXt source or its pinned tape record; '
                         'decode and validate first, then run trusted Body verify and hosted bridge '
                         'only with explicit user and host permission. Never execute embedded code on reading.',
            'save_protocol':'NEW_VERIFIED_BODY_REBUILD',
            'recovery':'active-manifest-primer-link'}


def export_body(body,output):
    """Export a verified Body to Chroma. No change to the live Body or ledger."""
    from . import cartridge
    body=Path(body).resolve();output=Path(output).resolve()
    if output.exists() or output.is_relative_to(body) or output.suffix.lower()!='.png':
        raise ValueError('Chroma export requires a new .png outside the Body')
    cartridge.verify(body)
    data,manifest=_body_records(body)
    portable_source=next(text for meta,text in data if meta['id']==manifest['bootstrap_id'])
    # The tiny self-extracting decoder is duplicated as iTXt metadata and a
    # digest-pinned record: bootstrap redundancy, not a second memory organ.
    png=_encode(data,bootstrap=_agent_bootstrap(data,manifest),protocol=CHROMA_PROTOCOL,
                loader=portable_source)
    output.parent.mkdir(parents=True,exist_ok=True)
    created=False
    try:
        with output.open('xb') as stream:
            created=True
            stream.write(png)
        summary=inspect(output)
        if summary['manifest']!=NATIVE_MANIFEST or summary['ledger_head']!=manifest['ledger_head']:
            raise ChromaMemError('Encoded Chroma verification failed')
    except BaseException:
        if created:output.unlink(missing_ok=True)
        raise
    return {'schema':'mantle.chroma-export/1','output':str(output),'bytes':len(png),
            'kernel':'chroma','ledger_head':summary['ledger_head'],'ledger_records':summary['ledger_records'],
            'record_count':summary['records'],'sha256':_digest(png),'inspection':'PASS'}


def evolve(parent_image,body,output):
    """Use a Chroma Engram itself as an append-only parent template.

    Refuses shortening memory, mismatched identity, and bodyless legacy carriers.
    This operation does not modify either source. Rebuild from the verified Body
    when a tape reaches its bounded optical capacity.
    """
    from . import cartridge
    source=Path(parent_image).resolve();body=Path(body).resolve();output=Path(output).resolve()
    if not source.is_file() or output.exists() or output==source or output.is_relative_to(body) or output.suffix.lower()!='.png':
        raise ValueError('Evolution needs a new .png outside the Body and parent')
    old=decode(source); previous=verify_manifest(old)
    verify_bootstrap(old,previous)
    inspect(source)  # Includes archive/ledger consistency, not just tape hashes.
    if previous.get('schema')!='mantle.engram-image-package/2' or previous.get('bundle_role')!='VERIFIED_CARTRIDGE_BODY':
        raise ChromaMemError('Self-templating requires a native Chroma Body, not a historical read-only specimen')
    verified=cartridge.verify(body)
    if verified['bio_software']!=previous['agent_id']:
        raise ChromaMemError('Evolution cannot change the agent identity')
    old_ledger=old['by_id'][previous['ledger_id']]['text'].encode('utf-8')
    new_ledger=(body/'ENGRAM.jsonl').read_bytes()
    if not new_ledger.startswith(old_ledger):
        raise ChromaMemError('Chroma evolution may only extend original ledger bytes')
    if (old_ledger==new_ledger and previous.get('body_manifest_sha256')==_digest((body/'MANIFEST.json').read_bytes())):
        raise ChromaMemError('No new Body version; unnecessary Chroma generation')
    generation=previous.get('generation',1)+1
    if type(generation) is not int or not 2<=generation<=9999:
        raise ChromaMemError('Invalid Chroma generation')
    fresh,manifest=_body_records(body)
    mapping={meta['id']:meta['id']+'.g%04d'%generation for meta,_ in fresh}
    new_manifest_id='agent.package.manifest.mantleos.%03d'%generation
    mapping[NATIVE_MANIFEST]=new_manifest_id
    for key in ('primer_id','host_contract_id','prompt_id','runtime_id','schema_id','ledger_id',
                'resume_id','bridge_validation_id','bundle_id','bootstrap_id'):
        manifest[key]=mapping[manifest[key]]
    manifest['bundle_part_ids']=[mapping[k] for k in manifest['bundle_part_ids']]
    manifest.update(generation=generation,previous_manifest_id=_manifest_id(old),
                    previous_tape_sha256=old['body_sha256'])
    # Historical records must be preserved in exact wire representation. Links
    # within the new generation point only to the new generation's artifacts.
    combined=[(r['meta'],r['text'],r['raw']) for r in old['records']]
    for meta,value in fresh:
        renamed=dict(meta);renamed['id']=mapping[meta['id']]
        if 'links' in meta:
            renamed['links']=[{'rel':edge['rel'],'to':mapping[edge['to']]} for edge in meta['links']]
        if meta['id']==NATIVE_MANIFEST:
            renamed['links'].append({'rel':'previous_manifest','to':_manifest_id(old)})
            value=_canonical(manifest)
        combined.append((renamed,value))
    source_text=next(text for meta,text in fresh if meta['id']=='mantle.engram.portable_bootstrap.001')
    png=_encode(combined,bootstrap=_agent_bootstrap(combined,manifest,new_manifest_id),
                protocol=CHROMA_PROTOCOL,loader=source_text)
    output.parent.mkdir(parents=True,exist_ok=True)
    created=False
    try:
        with output.open('xb') as writer:
            created=True;writer.write(png)
        checked=inspect(output)
        if checked['manifest']!=new_manifest_id or checked['ledger_head']!=manifest['ledger_head']:
            raise ChromaMemError('Chroma continuation self-check failed')
    except BaseException:
        if created:output.unlink(missing_ok=True)
        raise
    return {'schema':'mantle.chroma-evolution/1','output':str(output),'generation':generation,
            'previous_tape_sha256':old['body_sha256'],'ledger_head':checked['ledger_head'],
            'records':checked['records'],'bootstrap':checked['bootstrap'],
            'bytes':len(png),'sha256':_digest(png)}


def _checked_archive(raw):
    """All archive names and sizes are validated before any file is written."""
    from pathlib import PurePosixPath
    try: arc=zipfile.ZipFile(io.BytesIO(raw))
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        raise ChromaMemError('Bad embedded Body archive') from exc
    members=arc.infolist()
    if len(members)>5000 or sum(i.file_size for i in members)>MAX_ARCHIVE_BYTES:
        raise ChromaMemError('Embedded archive exceeds limits')
    seen=set()
    for item in members:
        name=PurePosixPath(item.filename)
        mode=(item.external_attr>>16)&0o170000
        if (not item.filename or item.filename.endswith('/') or name.as_posix()!=item.filename or name.is_absolute()
            or '..' in name.parts or '\\' in item.filename or ':' in item.filename
            or item.filename in seen or mode not in (0,0o100000)
            or '.git' in name.parts or 'NEST' in name.parts):
            raise ChromaMemError('Unsafe, duplicate or non-file embedded member')
        seen.add(item.filename)
    return arc,members


def _validate_native_bundle(decoded,manifest):
    if (manifest.get('schema')!='mantle.engram-image-package/2'
        or manifest.get('bundle_role')!='VERIFIED_CARTRIDGE_BODY'):
        raise ChromaMemError('Image is not an exportable verified MantleOS Body')
    archive=base64.b64decode(_bundle_text(decoded,manifest),validate=True)
    arc,members=_checked_archive(archive)
    with arc:
        if 'MANIFEST.json' not in arc.namelist() or 'ENGRAM.jsonl' not in arc.namelist():
            raise ChromaMemError('Native Chroma archive missing mandatory Body data')
        if _digest(arc.read('MANIFEST.json'))!=manifest.get('body_manifest_sha256'):
            raise ChromaMemError('Body manifest differs from carrier digest')
        if arc.read('ENGRAM.jsonl')!=decoded['by_id'][manifest['ledger_id']]['text'].encode('utf-8'):
            raise ChromaMemError('Body Engram journal differs from carrier ledger')
    return archive


def extract_body(path,output,*,manifest_id=ACTIVE_MANIFEST):
    """Reconstruct a verified portable Body only by explicit request; no execution."""
    from . import cartridge
    source=Path(path); target=Path(output).resolve()
    if target.exists():raise FileExistsError('Chroma reconstruction never overwrites an existing Body')
    parent=target.parent
    if not parent.is_dir():raise FileNotFoundError('Chroma output parent directory must exist')
    decoded=decode(source);manifest=verify_manifest(decoded,manifest_id)
    archive=_validate_native_bundle(decoded,manifest)
    temporary=Path(tempfile.mkdtemp(prefix='.mantle-chroma-',dir=parent))
    try:
        arc,members=_checked_archive(archive)
        with arc:
            for member in members:
                destination=temporary/member.filename
                destination.parent.mkdir(parents=True,exist_ok=True)
                with arc.open(member) as stream, destination.open('xb') as sink:
                    shutil.copyfileobj(stream,sink,length=65536)
        verification=cartridge.verify(temporary)
        if verification['bio_software']!=manifest['agent_id']:
            raise ChromaMemError('Bio-Software identity differs from carrier manifest')
        if _digest((temporary/'MANIFEST.json').read_bytes())!=manifest['body_manifest_sha256']:
            raise ChromaMemError('Restored manifest mismatch')
        if target.exists(): raise FileExistsError('Reconstruction output appeared during verification')
        temporary.rename(target)
        return {'schema':'mantle.chroma-reconstruction/1','output':str(target),
                'result':'VERIFIED','files':len(members),'bio_software':verification['bio_software'],
                'kernel':'chroma','executed':False,'ledger_head':manifest['ledger_head']}
    finally:
        if temporary.exists():shutil.rmtree(temporary)
