from __future__ import annotations

import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAGIC = b"VCWPNG2\n"
SIDE = 800
CHANNELS = 4
RAW_BYTES = SIDE * SIDE * CHANNELS
MAX_PNG_BYTES = 8 * 1024 * 1024


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def encode_rgba(raw: bytes) -> bytes:
    if len(raw) != RAW_BYTES:
        raise ValueError("VCW raw buffer must be exactly 800x800 RGBA bytes")
    stride = SIDE * CHANNELS
    filtered = bytearray((stride + 1) * SIDE)
    for y in range(SIDE):
        start = y * (stride + 1) + 1
        filtered[start:start + stride] = raw[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", SIDE, SIDE, 8, 6, 0, 0, 0)
    return PNG_SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(filtered), 1)) + _chunk(b"IEND", b"")


def decode_rgba(data: bytes) -> bytes:
    if len(data) > MAX_PNG_BYTES or not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a bounded PNG")
    pos = 8
    idat = bytearray()
    saw_iend = False
    end_pos = None
    width = height = None
    while pos < len(data):
        if len(data) - pos < 12:
            raise ValueError("truncated PNG chunk")
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + size
        if end > len(data):
            raise ValueError("truncated PNG data")
        payload = data[pos + 8:pos + 8 + size]
        stored = struct.unpack(">I", data[pos + 8 + size:end])[0]
        if stored != zlib.crc32(kind + payload) & 0xffffffff:
            raise ValueError("PNG CRC mismatch")
        if kind == b"IHDR":
            if size != 13 or width is not None:
                raise ValueError("invalid PNG header")
            width, height, depth, ctype, comp, filt, interlace = struct.unpack(">IIBBBBB", payload)
            if (width, height, depth, ctype, comp, filt, interlace) != (SIDE, SIDE, 8, 6, 0, 0, 0):
                raise ValueError("VCW layer must be 800x800 non-interlaced RGBA")
        elif kind == b"IDAT":
            idat.extend(payload)
        elif kind == b"IEND":
            saw_iend = True
            end_pos = end
            break
        elif kind and not (kind[0] & 0x20):
            raise ValueError("unsupported critical PNG chunk")
        pos = end
    if not saw_iend:
        raise ValueError("missing PNG IEND")
    if end_pos != len(data):
        raise ValueError("trailing bytes after PNG IEND")
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise ValueError("invalid PNG compression") from exc
    expected = (SIDE * CHANNELS + 1) * SIDE
    if len(raw) != expected:
        raise ValueError("unexpected PNG scanline size")
    out = bytearray(RAW_BYTES)
    stride = SIDE * CHANNELS
    for y in range(SIDE):
        if raw[y * (stride + 1)] != 0:
            raise ValueError("only filter type 0 is accepted for VCW layers")
        start = y * (stride + 1) + 1
        out[y * stride:(y + 1) * stride] = raw[start:start + stride]
    return bytes(out)


def pack_layer(boot: dict, payload: dict) -> bytes:
    import json
    boot_bytes = json.dumps(boot, separators=(",", ":"), sort_keys=True).encode()
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    body = MAGIC + struct.pack(">I", len(boot_bytes)) + boot_bytes + struct.pack(">I", len(payload_bytes)) + payload_bytes
    if len(body) > RAW_BYTES:
        raise ValueError("VCW layer payload overflow")
    return encode_rgba(body + bytes(RAW_BYTES - len(body)))


def unpack_layer(data: bytes) -> tuple[dict, dict]:
    import json
    raw = decode_rgba(data)
    if raw[:8] != MAGIC:
        raise ValueError("missing VCW layer magic")
    pos = 8
    def take() -> bytes:
        nonlocal pos
        if pos + 4 > RAW_BYTES:
            raise ValueError("missing VCW field length")
        size = struct.unpack(">I", raw[pos:pos + 4])[0]
        pos += 4
        if size > RAW_BYTES - pos:
            raise ValueError("VCW field exceeds layer boundary")
        value = raw[pos:pos + size]
        pos += size
        return value
    try:
        boot = json.loads(take().decode())
        payload = json.loads(take().decode())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid VCW JSON") from exc
    if not isinstance(boot, dict) or not isinstance(payload, dict) or any(raw[pos:]):
        raise ValueError("invalid VCW layer payload")
    return boot, payload
