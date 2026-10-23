#!/usr/bin/env python3
"""
mantle.vcw.png  --  the pure-stdlib PNG lane hardware codec (Mantle OS)

Every VCW layer is a REAL, valid PNG image: the whole organism's memory is a directory of
pictures you can open in any image viewer. This module is the lowest substrate primitive --
flat RGBA bytes <-> PNG bytes, and the layer pixel-stream layout:

  [ 8 bytes  MAGIC = b"VCWPNG2\\n" ]
  [ 4 bytes  uint32 length of boot JSON   ][ boot JSON utf-8 ]
  [ 4 bytes  uint32 length of payload JSON][ payload JSON utf-8 ]
  [ zero padding up to LAYER_BYTES ]

A single byte inside a layer is addressed by (layer, x, y):
  offset = (y * SIDE + x) * CHANNELS          # CHANNELS = 4 (R,G,B,A)

This file deliberately does not assign semantic meaning to R/G/B/A. Those are the four
addressable substrate lanes. The cube boot sector and the layer's driver/profile decide
whether the lanes carry log JSON bytes, spatial state, tool/database payload, or a
Grimoire software profile such as atom/role/evidence/force.

We WRITE filter type 0 (None) scanlines at zlib level 1 (the payload is JSON + zero pad --
level 1 compresses it nearly as small as level 6 at a fraction of the CPU; the level is
invisible to the decoder). We READ all five PNG filter types for robustness.
"""
from __future__ import annotations

import json
import struct
import zlib
from typing import Any, Dict, Optional, Tuple

VCW_FORMAT  = "vcw-cube-png-v2"          # the on-disk format is unchanged from v2
LAYER_COUNT = 800
SIDE        = 800
CHANNELS    = 4                          # RGBA
LAYER_BYTES = SIDE * SIDE * CHANNELS     # 2,560,000 bytes per layer
MAGIC       = b"VCWPNG2\n"               # 8 bytes, opens every layer's payload stream
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# A VCW layer is a fixed 800x800 RGBA image.  These limits are deliberately format-level,
# not caller hints: cubes and spores are portable and therefore attacker-supplyable.  Bound
# both the compressed container and the decompressed scanlines before allocating from fields
# controlled by the file.
MAX_PNG_BYTES = 8 * 1024 * 1024
MAX_IDAT_BYTES = 4 * 1024 * 1024
_SCANLINE_BYTES = (SIDE * CHANNELS + 1) * SIDE


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png_rgba(raw: bytes, width: int = SIDE, height: int = SIDE) -> bytes:
    """Encode a flat RGBA byte buffer (len == width*height*4) into PNG bytes."""
    if len(raw) != width * height * CHANNELS:
        raise ValueError("encode_png_rgba: raw length %d != %d"
                         % (len(raw), width * height * CHANNELS))
    stride = width * CHANNELS
    out = bytearray(height * (stride + 1))      # filter bytes stay 0 from zero-init
    for y in range(height):
        dst = y * (stride + 1) + 1
        out[dst:dst + stride] = raw[y * stride:(y + 1) * stride]
    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(bytes(out), 1)
    return (sig + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b""))


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png_rgba(png: bytes) -> bytes:
    """Decode one fixed-size VCW PNG without trusting its lengths or compression ratio.

    The decoder accepts all five PNG filters, but only the non-interlaced 8-bit RGBA
    profile emitted by Mantle.  Every chunk CRC is checked and decompression is capped at
    exactly one layer's scanline budget.
    """
    if not isinstance(png, (bytes, bytearray)):
        raise TypeError("decode_png_rgba: png must be bytes")
    if len(png) > MAX_PNG_BYTES:
        raise ValueError("decode_png_rgba: PNG exceeds the VCW layer size limit")
    if png[:8] != PNG_SIGNATURE:
        raise ValueError("decode_png_rgba: not a PNG")
    pos = 8
    width = height = None
    idat = bytearray()
    saw_iend = False
    chunk_number = 0
    while pos < len(png):
        if len(png) - pos < 12:
            raise ValueError("decode_png_rgba: truncated chunk header")
        (length,) = struct.unpack(">I", png[pos:pos + 4])
        tag = png[pos + 4:pos + 8]
        if any(not (65 <= octet <= 90 or 97 <= octet <= 122) for octet in tag):
            raise ValueError("decode_png_rgba: invalid chunk type")
        end = pos + 12 + length
        if end > len(png):
            raise ValueError("decode_png_rgba: truncated %r chunk" % tag)
        data = png[pos + 8:pos + 8 + length]
        (stored_crc,) = struct.unpack(">I", png[pos + 8 + length:end])
        actual_crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            raise ValueError("decode_png_rgba: CRC mismatch in %r" % tag)
        pos = end
        if tag == b"IHDR":
            if chunk_number != 0 or width is not None or length != 13:
                raise ValueError("decode_png_rgba: invalid IHDR")
            width, height, depth, ctype, compression, filtering, interlace = \
                struct.unpack(">IIBBBBB", data)
            if (width, height) != (SIDE, SIDE):
                raise ValueError("decode_png_rgba: expected %dx%d VCW layer" % (SIDE, SIDE))
            if (depth, ctype, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise ValueError("decode_png_rgba: expected non-interlaced 8-bit RGBA")
        elif tag == b"IDAT":
            if width is None:
                raise ValueError("decode_png_rgba: IDAT before IHDR")
            if len(idat) + length > MAX_IDAT_BYTES:
                raise ValueError("decode_png_rgba: compressed image exceeds limit")
            idat += data
        elif tag == b"IEND":
            if length != 0 or width is None or not idat:
                raise ValueError("decode_png_rgba: invalid IEND")
            saw_iend = True
            break
        elif not (tag[0] & 0x20):
            raise ValueError("decode_png_rgba: unsupported critical chunk %r" % tag)
        chunk_number += 1
    if not saw_iend:
        raise ValueError("decode_png_rgba: missing IEND")
    if pos != len(png):
        raise ValueError("decode_png_rgba: trailing bytes after IEND")

    try:
        inflater = zlib.decompressobj()
        raw = inflater.decompress(bytes(idat), _SCANLINE_BYTES + 1)
    except zlib.error as exc:
        raise ValueError("decode_png_rgba: invalid compressed image") from exc
    if (len(raw) != _SCANLINE_BYTES or not inflater.eof
            or inflater.unconsumed_tail or inflater.unused_data):
        raise ValueError("decode_png_rgba: decompressed image size mismatch")

    stride = width * CHANNELS
    out = bytearray(width * height * CHANNELS)
    prev = bytearray(stride)
    src = 0
    for y in range(height):
        ftype = raw[src]; src += 1
        line = bytearray(raw[src:src + stride]); src += stride
        if ftype == 0:
            pass
        elif ftype == 1:  # Sub
            for i in range(CHANNELS, stride):
                line[i] = (line[i] + line[i - CHANNELS]) & 0xFF
        elif ftype == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:  # Average
            for i in range(stride):
                a = line[i - CHANNELS] if i >= CHANNELS else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:  # Paeth
            for i in range(stride):
                a = line[i - CHANNELS] if i >= CHANNELS else 0
                c = prev[i - CHANNELS] if i >= CHANNELS else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 0xFF
        else:
            raise ValueError("decode_png_rgba: bad filter type %d" % ftype)
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return bytes(out)


# ---- layer pixel stream (boot sector + payload JSON) <-> RGBA bytes --------
def build_layer_rgba(boot: Dict[str, Any], payload: Dict[str, Any]) -> bytes:
    """Serialize a Layer Boot Sector + payload into a full LAYER_BYTES RGBA stream."""
    boot_b = json.dumps(boot, separators=(",", ":"), sort_keys=True).encode("utf-8")
    pay_b  = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = (MAGIC + struct.pack(">I", len(boot_b)) + boot_b
            + struct.pack(">I", len(pay_b)) + pay_b)
    if len(body) > LAYER_BYTES:
        raise ValueError("layer payload overflow: %d > %d bytes" % (len(body), LAYER_BYTES))
    return body + b"\x00" * (LAYER_BYTES - len(body))


def parse_layer_rgba(raw: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Parse a LAYER_BYTES RGBA stream back into (boot, payload). Empty layer -> (None, None)."""
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("parse_layer_rgba: layer must be bytes")
    if len(raw) != LAYER_BYTES:
        raise ValueError("parse_layer_rgba: layer size %d != %d" % (len(raw), LAYER_BYTES))
    if raw[:8] != MAGIC:
        return None, None
    pos = 8

    def field(label: str) -> bytes:
        nonlocal pos
        if pos + 4 > LAYER_BYTES:
            raise ValueError("parse_layer_rgba: missing %s length" % label)
        (length,) = struct.unpack(">I", raw[pos:pos + 4])
        pos += 4
        if length > LAYER_BYTES - pos:
            raise ValueError("parse_layer_rgba: %s exceeds layer boundary" % label)
        value = bytes(raw[pos:pos + length])
        pos += length
        return value

    try:
        boot = json.loads(field("boot").decode("utf-8"))
        payload = json.loads(field("payload").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("parse_layer_rgba: invalid JSON") from exc
    if not isinstance(boot, dict) or not isinstance(payload, dict):
        raise ValueError("parse_layer_rgba: boot and payload must be objects")
    if any(raw[pos:]):
        raise ValueError("parse_layer_rgba: non-zero bytes after payload")
    return boot, payload
