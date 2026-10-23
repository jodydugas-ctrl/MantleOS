"""Strict bounded 8-bit RGB/RGBA PNG evidence codec; Python standard library only."""
import binascii
from pathlib import Path
import struct
import zlib

from .core import KPPError

SIGNATURE=b'\x89PNG\r\n\x1a\n'
MAX_BYTES=16*1024*1024
MAX_PIXELS=16_000_000


def read(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_BYTES:
        raise KPPError('Missing, unsafe or oversized PNG capture')
    return decode(path.read_bytes())


def decode(data):
    if len(data)>MAX_BYTES or not data.startswith(SIGNATURE):raise KPPError('Invalid PNG capture')
    position=8;header=None;compressed=bytearray();ended=False;idat_seen=False;idat_closed=False;palette_seen=False
    while position<len(data):
        if position+12>len(data):raise KPPError('Truncated PNG chunk')
        length=struct.unpack('>I',data[position:position+4])[0]
        kind=data[position+4:position+8];stop=position+8+length
        if len(kind)!=4 or any(not (65<=letter<=90 or 97<=letter<=122) for letter in kind):raise KPPError('Invalid PNG chunk type')
        if stop+4>len(data):raise KPPError('Truncated PNG payload')
        content=data[position+8:stop]
        checksum=struct.unpack('>I',data[stop:stop+4])[0]
        if binascii.crc32(kind+content)&0xffffffff!=checksum:raise KPPError('PNG CRC mismatch')
        if header is None and kind!=b'IHDR':raise KPPError('PNG must start with IHDR')
        if idat_seen and kind!=b'IDAT':idat_closed=True
        if kind==b'IHDR':
            if header is not None or length!=13:raise KPPError('Invalid PNG header')
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',content)
            if not width or not height or width*height>MAX_PIXELS:raise KPPError('PNG dimensions exceed evidence limits')
            if depth!=8 or color not in (2,6) or compression or filtering or interlace:
                raise KPPError('Unsupported PNG profile: require noninterlaced 8-bit RGB or RGBA')
            header=(width,height,3 if color==2 else 4)
        elif kind==b'IDAT':
            if idat_closed:raise KPPError('PNG image chunks must be consecutive')
            idat_seen=True;compressed.extend(content)
        elif kind==b'IEND':
            if length or stop+4!=len(data):raise KPPError('Invalid PNG end or trailing bytes')
            ended=True;break
        elif kind==b'tRNS':raise KPPError('Unsupported PNG transparency chunk; use RGBA')
        elif kind in (b'acTL',b'fcTL',b'fdAT'):raise KPPError('Animated PNG is not a static GUI capture')
        elif kind==b'PLTE':
            if palette_seen or idat_seen or not length or length%3 or length>768:raise KPPError('Invalid optional PNG palette')
            palette_seen=True
        elif kind and not kind[0]&32:raise KPPError('Unsupported critical PNG chunk')
        position=stop+4
    if not ended or not compressed:raise KPPError('PNG is incomplete')
    width,height,channels=header;stride=width*channels;expected=(stride+1)*height
    try:
        decoder=zlib.decompressobj();raw=decoder.decompress(bytes(compressed),expected+1)
    except zlib.error as error:raise KPPError('Invalid PNG compression') from error
    if len(raw)!=expected or not decoder.eof or decoder.unused_data:raise KPPError('PNG decoded size/stream mismatch')
    pixels=bytearray();prior=bytearray(stride);position=0
    for _ in range(height):
        mode=raw[position];row=bytearray(raw[position+1:position+1+stride]);position+=stride+1
        if mode>4:raise KPPError('Unsupported PNG row filter')
        for index in range(stride) if mode else ():
            left=row[index-channels] if index>=channels else 0
            above=prior[index];upper=prior[index-channels] if index>=channels else 0
            if mode==0:predict=0
            elif mode==1:predict=left
            elif mode==2:predict=above
            elif mode==3:predict=(left+above)//2
            else:
                p=left+above-upper;pa,pb,pc=abs(p-left),abs(p-above),abs(p-upper)
                predict=left if pa<=pb and pa<=pc else above if pb<=pc else upper
            row[index]=(row[index]+predict)&255
        if channels==4:pixels.extend(row)
        else:
            for index in range(0,stride,3):pixels.extend((*row[index:index+3],255))
        prior=row
    return width,height,bytes(pixels)


def encode(width,height,rgba):
    if type(width) is not int or type(height) is not int or width<1 or height<1 or width*height>MAX_PIXELS or len(rgba)!=width*height*4:
        raise KPPError('Invalid evidence PNG dimensions/pixels')
    def chunk(kind,payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',binascii.crc32(kind+payload)&0xffffffff)
    stride=width*4
    raw=b''.join(b'\0'+rgba[y*stride:(y+1)*stride] for y in range(height))
    return SIGNATURE+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
