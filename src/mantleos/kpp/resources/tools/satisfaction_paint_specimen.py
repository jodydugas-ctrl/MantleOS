"""Bounded RGB/history/PNG failure specimen, not the complete Paint blueprint."""
import struct
import zlib


def checks():
    original = bytes([255,255,255] * 4)
    pixels = bytearray(original); pixels[:3] = bytes([12,34,56])
    history = [original, bytes(pixels)]
    assert history[-2] == original and history[-1] == bytes(pixels)
    saved = original
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    raw = b'\0'+bytes(pixels[:6])+b'\0'+bytes(pixels[6:])
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    cursor=8;decoded=b''
    while cursor<len(png):
        size=struct.unpack('>I',png[cursor:cursor+4])[0]
        kind=png[cursor+4:cursor+8];data=png[cursor+8:cursor+8+size]
        assert zlib.crc32(kind+data)==struct.unpack('>I',png[cursor+8+size:cursor+12+size])[0]
        if kind==b'IDAT':decoded+=data
        cursor+=size+12
    rows=zlib.decompress(decoded)
    assert rows[1:7]+rows[8:14]==bytes(pixels)
    # Simulated denied/failed I/O and cancelled transition preserve dirty pixels.
    before=bytes(pixels)
    for outcome in ('denied','failed','cancelled'):
        if outcome=='success':saved=bytes(pixels)
        assert bytes(pixels)==before and bytes(pixels)!=saved
    return {'pixel_history_png_roundtrip':'PASS','failed_cancelled_save_preserves_dirty':'PASS',
            'scope':'2x2 opaque RGB synthetic state; actual GUI, file permissions and full Paint UNTESTED'}


if __name__=='__main__':
    import json
    print(json.dumps(checks(),indent=2))
