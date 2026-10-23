#!/usr/bin/env python3
"""
SPORE-PNG v1  --  the smallest viable AppAI agent.

A "Spore" is a single PNG image that carries its own memory, visible identity,
bootstrap instructions and update protocol.  The PNG is not a picture of the
agent -- the PNG *is* the agent.

This file implements the whole format:

    * VCW color-memory encoding  (top half of the image)
    * versioned Grimoire RGBA statements (new spores default to v0.10; v0.9 is preserved)
    * G=0x7f statement-local PARITY control pixels
    * an in-band manifest with a full-lane SHA-256 payload fingerprint
    * canonical PNG iTXt metadata
    * a visible protected boot strip + a mutable lower display
    * an EMBEDDED minimal tool (spore_min.py) carried inside the payload, so the
      PNG can read/grow itself without the full SDK beside it
    * an honest strict fill for the unused VCW field (colored == data)
    * create / read / append / render / verify

It intentionally does NOT implement organs, immune events, rebirth, lineage,
encryption, symbiosis, metabolism, tombstones, quarantine, child spores,
compaction or summarization.  A Spore is transparent and simple:

    one PNG - one agent - one task - one conversation - one append-only memory

SPORE-PNG v2 supports explicit Grimoire carrier profiles. New spores default to v0.10;
historical v0.9 carriers remain readable. Physical RGBA bytes are logical atom/role/evidence/force lanes. Inert manifest and payload bytes are serialized as
QUOTE statements: one composed nibble-atom spelling per frame, one HEAD, inherited
B/A on every BLEND continuation, and one PARITY control pixel. Whole-payload mutation
is detected by a SHA-256 fingerprint over every raw RGBA payload frame and its boundary.

The canonical PNG payload path is pure standard library. Pillow (PIL) is optional and
only improves the visible lower-panel rendering with text. NumPy is used if present
(faster fill) but is optional.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import sys
import textwrap
import zlib
from datetime import datetime, timezone

try:
    from PIL import Image, ImageDraw, ImageFont
    from PIL.PngImagePlugin import PngInfo
except ImportError:                    # the framework stays pure-stdlib importable;
    Image = ImageDraw = ImageFont = PngInfo = None   # visible text rendering needs it


def _require_pil() -> None:
    if Image is None:
        raise RuntimeError("spore PNG operations need Pillow: pip install pillow "
                           "(or: pip install mantle-os[spore])")

try:
    import numpy as _np
except Exception:                      # numpy is optional
    _np = None

# ---------------------------------------------------------------------------
# Constants -- the canonical geometry of a default Spore.
# ---------------------------------------------------------------------------

MAGIC = b"SPOREPNG"          # 8 bytes, first thing in the VCW byte-stream
FORMAT_VERSION = 2
GERM_SCHEMA_VERSION = "mantle-germ-v2"
HOST_EVIDENCE_SCHEMA_VERSION = "mantle-host-evidence-v3"
SPORE_FORMAT = "spore-png-v2"

# A spore MAY additionally carry a GERM: the complete build data for a full
# AppAI (identity, truths, commandments, genome bands, reflexes, controls,
# instincts with proving cases -- the document the hatchery incubates), plus a
# human/agent-readable "build" note explaining how to grow it. A germ-carrying
# spore is the ONE artifact that births an AppAI: hand the PNG to
# `python -m mantle hatch` or to any coding agent, which can read the germ out
# of the payload and build a conforming body from it. The germ is inert data
# here -- the spore stores it; the hatchery validates and grows it.
GERM_FORMAT = "mantle-germ-v2"

CANVAS_W = 2000
CANVAS_H = 2000

VCW_X, VCW_Y, VCW_W, VCW_H = 0, 0, 2000, 1000        # top half: memory
DISP_X, DISP_Y, DISP_W, DISP_H = 0, 1000, 2000, 1000  # bottom half: visible
BOOT_STRIP_H = 300                                    # protected strip height

VCW_BLOCKS = VCW_W * VCW_H              # 2,000,000 pixels
FRAME_PAYLOAD_BYTES = 1024
MAX_HEADER_BYTES = 64 * 1024
# Each byte occupies two semantic morpheme pixels; every frame adds one PARITY pixel.
VCW_CAPACITY_BYTES = (VCW_BLOCKS - 1) // 2
DEFAULT_GRIMOIRE_PROFILE = "grimoire-v0.10"
LEGACY_GRIMOIRE_PROFILE = "grimoire-v0.9"

# The canonical bootloader / spec text.  This exact string is mirrored into the
# visible protected strip AND into PNG metadata (key "Bootloader").
# It MUST stay byte-identical to spore_min.py's BOOTLOADER_TEXT.
BOOTLOADER_TEXT = (
    "SPORE-PNG v2  -  this PNG is a self-contained AppAI agent.\n"
    "MEMORY lives in the TOP HALF (y=0..999) as a VCW color field: read pixels\n"
    "left-to-right, top-to-bottom as the selected Grimoire RGBA profile. R is atom,\n"
    "G is role, B is evidence, and A is force. Inert bytes are framed as QUOTE:\n"
    "one HEAD, BLEND continuations with B=A=0 inheritance, then G=0x7f PARITY.\n"
    "The first statement is a JSON manifest; following statements carry payload.\n"
    "The manifest records a SHA-256 fingerprint over every raw payload RGBA lane\n"
    "and frame boundary. Parity or fingerprint mismatch rejects the carrier.\n"
    "A minimal Python reader/writer is embedded in the payload (embedded_tools).\n"
    "Canonical spec ALSO lives in PNG iTXt metadata; metadata is canonical over\n"
    "THIS strip, but the VCW payload owns identity + conversation memory.\n"
    "KEEP THE SEED DRY: transfer the ORIGINAL .png only. Do NOT screenshot, resize,\n"
    "recompress, flatten transparency, or pass me through lossy image tools - that\n"
    "changes semantic lanes and causes a loud integrity rejection.\n"
    "To use me: open in a Spore app, or hand me to a Python-capable LLM and let\n"
    "Python (not eyeballs) decode the pixels. RULE: the LATEST PNG is the living copy."
)
LEGACY_BOOTLOADER_TEXT = BOOTLOADER_TEXT.replace(
    "the selected Grimoire RGBA profile", "Grimoire v0.9 RGBA statements")

TRANSPORT_WARNING = (
    "Transfer the ORIGINAL .png only; do not screenshot/resize/recompress/flatten."
)

# A tiny, self-contained reader printed IN the view area (and mirrored in the
# "Quickstart" metadata).  It reads an undamaged Spore with no dependencies
# beyond Pillow -- the full repairing reader is the embedded spore_min.py.
QUICKSTART_CODE = (
    "# BOOT ME FROM THIS IMAGE ALONE - needs only: pip install pillow\n"
    "from PIL import Image; import json, base64, zlib, hashlib\n"
    "px = Image.open('spore.png').convert('RGBA').load()\n"
    "i=0\n"
    "def frame():\n"
    "    global i\n"
    "    rec=[]\n"
    "    while True:\n"
    "        p=px[i%2000,i//2000]; i+=1; rec.append(p)\n"
    "        if p[1]==0x7f: break\n"
    "    q=rec[-1]; body=rec[:-1]\n"
    "    xr=xb=xa=0\n"
    "    for r,g,b,a in body: xr^=r; xb^=b; xa^=a\n"
    "    assert (q[0],q[2],q[3])==((xr or 254),xb,xa)\n"
    "    n=[r-1 for r,g,b,a in body]\n"
    "    return bytes((n[j]<<4)|n[j+1] for j in range(0,len(n),2)),bytes(sum((list(p) for p in rec),[]))\n"
    "hb,_=frame(); H=json.loads(hb); chunks=[]; runs=[]\n"
    "for _ in range(H['payload_frame_count']): c,r=frame(); chunks.append(c); runs.append(r)\n"
    "h=hashlib.sha256(); h.update(b'SPORE-PNG-v2\\0')\n"
    "for j,r in enumerate(runs): h.update(j.to_bytes(4,'big')+len(r).to_bytes(4,'big')+r)\n"
    "assert 'sha256:'+h.hexdigest()==H['payload_fingerprint']\n"
    "S=json.loads(b''.join(chunks)[:H['payload_length']])\n"
    "print(S['identity']['spore_name'], '-', S['identity']['task'])\n"
    "for e in S['conversation']: print(e['opcode'], ':', e['content'])\n"
    "# GROW ME: I carry my own reader/writer - extract and use it:\n"
    "open('spore_min.py','w').write(zlib.decompress(base64.b64decode(S['embedded_tools']['code'])).decode())\n"
    "import spore_min  # spore_min.append('spore.png','user','hi'); ...('assistant','reply')"
)

# Authority table -- which source wins for which concern (mirrored into the PNG
# metadata; doctrine: documents/REPRODUCTION.md).
AUTHORITY = {
    "bootloader_spec": "metadata wins over the visible boot strip",
    "identity": "VCW payload is canonical (metadata only mirrors it)",
    "conversation": "VCW payload is canonical",
    "display": "VCW payload is canonical",
}

TOOLS_PROTOCOL = {
    "reader": ("decode VCW top-half as framed Grimoire v0.9 QUOTE statements: "
               "manifest frame followed by declared payload frames"),
    "integrity": ("G=0x7f statement PARITY plus SHA-256 over all raw RGBA "
                  "payload lanes and frame boundaries"),
    "vcw_model": ("append-only delta log: genesis records (identity, tools, "
                  "embedded_tools) are written once; thereafter each turn is ONE "
                  "appended delta. Current state = genesis folded with the deltas. "
                  "The LLM context window is NEVER re-stored per turn, so total VCW "
                  "memory is the SUM of deltas (linear), not the history repeated."),
    "embedded_tool": "a base64+zlib copy of spore_min.py lives in payload.embedded_tools",
    "update_protocol": [
        "1. load latest PNG",
        "2. read metadata + decode VCW",
        "3. parse header + payload",
        "4. rebuild conversation/task context",
        "5. append new turn(s)",
        "6. regenerate the WHOLE PNG from canonical state (never edit pixels in place)",
    ],
    "authority": AUTHORITY,
    "display_rules": "protected boot strip is redrawn verbatim; lower display is mutable",
    "full_rule": "if no VCW room remains, mark FULL, do not overwrite memory, do not spawn children",
    "transport": TRANSPORT_WARNING,
}

ROLE_MAP = {
    "user":      ("USER", "USER", "conversation"),
    "assistant": ("ASSISTANT", "SPORE", "conversation"),
    "system":    ("SYSTEM", "APP", "conversation"),
    "tool":      ("TOOL", "APP", "conversation"),
    "identity":  ("IDENTITY", "SPORE", "metadata"),
    "display":   ("DISPLAY", "APP", "display"),
}

# Import after the carrier constants exist: mantle.vcw builds its atlas eagerly,
# and that atlas measures this module during package initialization.
from .vcw.grimoire import (  # noqa: E402
    GrimoireDecodeError,
    decode_quoted_bytes,
    encode_quoted_bytes,
)
from .vcw.grimoire_editions.v010 import (  # noqa: E402
    decode_quoted_bytes as decode_quoted_bytes_v010,
    encode_quoted_bytes as encode_quoted_bytes_v010,
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _checksum_text(text: str) -> str:
    return _sha(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Embedded tool  (self-hosting: the PNG carries spore_min.py)
# ---------------------------------------------------------------------------

_EMBEDDED_CACHE = None

_FALLBACK_TOOL = (
    "# minimal Spore tool embryo (fallback stub).\n"
    "# The full spore_min.py was not found beside spore.py at creation time.\n"
    "def read(path):\n"
    "    raise NotImplementedError('regenerate with spore_min.py present')\n"
    "def append(path, role, content):\n"
    "    raise NotImplementedError('regenerate with spore_min.py present')\n"
)


def _load_embedded_source() -> str:
    """Load spore_min.py source from beside this file (cached); else a stub."""
    global _EMBEDDED_CACHE
    if _EMBEDDED_CACHE is not None:
        return _EMBEDDED_CACHE
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, "spore_min.py")
    try:
        with open(candidate, encoding="utf-8") as f:
            _EMBEDDED_CACHE = f.read()
    except Exception:
        _EMBEDDED_CACHE = _FALLBACK_TOOL
    return _EMBEDDED_CACHE


def _make_embedded_tools() -> dict:
    src = _load_embedded_source()
    raw = src.encode("utf-8")
    packed = base64.b64encode(zlib.compress(raw, 9)).decode("ascii")
    return {
        "language": "python",
        "filename": "spore_min.py",
        "encoding": "base64+zlib",
        "entrypoints": ["read", "append"],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "code": packed,
    }


def extract_embedded_tool(path: str, out_path: str | None = None) -> str:
    """Decode the embedded spore_min.py source from a Spore PNG."""
    state = read_spore(path)["state"]
    et = state.get("embedded_tools")
    if not et or "code" not in et:
        raise ValueError("no embedded tool present in this spore")
    src = zlib.decompress(base64.b64decode(et["code"])).decode("utf-8")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(src)
    return src


# ---------------------------------------------------------------------------
# Grimoire statement frames <-> spore package (v0.9 compatibility and v0.10 default)
# ---------------------------------------------------------------------------

def _full_lane_fingerprint(frames: list[bytes]) -> str:
    """SHA-256 every raw RGBA lane plus explicit frame index and byte length."""
    h = hashlib.sha256()
    h.update(b"SPORE-PNG-v2\0")
    for index, raw in enumerate(frames):
        h.update(index.to_bytes(4, "big"))
        h.update(len(raw).to_bytes(4, "big"))
        h.update(raw)
    return "sha256:" + h.hexdigest()


def _payload_frames(payload_bytes: bytes, profile: str = LEGACY_GRIMOIRE_PROFILE) -> list[bytes]:
    encode_frame, _decode_frame = _codec(profile)
    return [
        encode_frame(payload_bytes[i:i + FRAME_PAYLOAD_BYTES])
        for i in range(0, len(payload_bytes), FRAME_PAYLOAD_BYTES)
    ]


def _codec(profile: str):
    if profile == DEFAULT_GRIMOIRE_PROFILE:
        return encode_quoted_bytes_v010, decode_quoted_bytes_v010
    if profile == LEGACY_GRIMOIRE_PROFILE:
        return encode_quoted_bytes, decode_quoted_bytes
    raise ValueError("unsupported Grimoire profile %r" % profile)


def build_stream(header: dict, payload_bytes: bytes) -> bytes:
    """Build the complete top-half raw RGBA run.

    The first statement carries the manifest. Remaining statements carry inert
    payload bytes. The manifest fingerprints the raw payload statements, avoiding
    a self-referential package hash while covering every application-data lane.
    """
    profile = header.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)
    encode_frame, _decode_frame = _codec(profile)
    payload_frames = [encode_frame(payload_bytes[i:i + FRAME_PAYLOAD_BYTES])
                      for i in range(0, len(payload_bytes), FRAME_PAYLOAD_BYTES)]
    manifest = dict(header)
    manifest.update({
        "magic": MAGIC.decode("ascii"),
        "format_version": FORMAT_VERSION,
        "grimoire_profile": profile,
        "encoding": profile + "-quoted-bytes",
        "frame_payload_bytes": FRAME_PAYLOAD_BYTES,
        "payload_frame_count": len(payload_frames),
        "payload_fingerprint": _full_lane_fingerprint(payload_frames),
    })
    header_bytes = json.dumps(
        manifest, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise ValueError("spore manifest exceeds %d bytes" % MAX_HEADER_BYTES)
    header_frame = encode_quoted_bytes(header_bytes)
    raw = header_frame + b"".join(payload_frames)
    if len(raw) % 4:
        raise AssertionError("Grimoire package is not whole RGBA pixels")
    if len(raw) // 4 > VCW_BLOCKS:
        raise ValueError("stream exceeds VCW capacity")
    return raw


class _PixelView:
    def __init__(self, rgba: bytes | bytearray, width: int):
        self.rgba = rgba
        self.width = width

    def __getitem__(self, xy):
        x, y = xy
        off = ((y * self.width) + x) * 4
        return tuple(self.rgba[off:off + 4])


class _RawPng:
    def __init__(self, width: int, height: int, rgba: bytes, meta: dict):
        self.size = (width, height)
        self.mode = "RGBA"
        self.text = meta
        self._rgba = rgba
        self._width = width

    def convert(self, mode: str) -> "_RawPng":
        if mode != "RGBA":
            raise ValueError("pure-stdlib spore reader only supports RGBA")
        return self

    def load(self):
        return _PixelView(self._rgba, self._width)


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    )


def _png_itxt(keyword: str, value: str) -> bytes:
    key = str(keyword).encode("latin-1", "replace")[:79] or b"Spore"
    return _png_chunk(b"iTXt", key + b"\0\0\0\0\0" + str(value).encode("utf-8"))


def _write_png(path: str, width: int, height: int, rgba: bytes | bytearray,
               metadata: dict) -> None:
    stride = width * 4
    raw = bytearray((stride + 1) * height)
    pos = 0
    for y in range(height):
        raw[pos] = 0
        pos += 1
        start = y * stride
        raw[pos:pos + stride] = rgba[start:start + stride]
        pos += stride
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    chunks = [_png_chunk(b"IHDR", ihdr)]
    for key, value in metadata.items():
        chunks.append(_png_itxt(key, value))
    chunks.append(_png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
    chunks.append(_png_chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _parse_itxt(payload: bytes) -> tuple[str, str] | None:
    try:
        key_end = payload.index(b"\0")
        key = payload[:key_end].decode("latin-1")
        flag = payload[key_end + 1]
        method = payload[key_end + 2]
        rest = payload[key_end + 3:]
        lang_end = rest.index(b"\0")
        rest = rest[lang_end + 1:]
        translated_end = rest.index(b"\0")
        text = rest[translated_end + 1:]
        if flag:
            if method != 0:
                return None
            text = zlib.decompress(text)
        return key, text.decode("utf-8")
    except Exception:
        return None


def _unfilter_rgba(raw: bytes, width: int, height: int) -> bytes:
    """Reconstruct non-interlaced 8-bit RGBA scanlines without per-byte filter dispatch."""
    stride = width * 4
    expected = (stride + 1) * height
    if len(raw) != expected:
        raise ValueError("PNG decoded data length %d != expected %d" % (len(raw), expected))
    bpp = 4
    rgba = bytearray(stride * height)
    prev = bytearray(stride)
    src = 0
    dst = 0
    abs_ = abs
    for _y in range(height):
        filt = raw[src]
        src += 1
        row = bytearray(raw[src:src + stride])
        src += stride
        if filt == 0:
            pass
        elif filt == 1:
            for i in range(bpp, stride):
                row[i] = (row[i] + row[i - bpp]) & 0xff
        elif filt == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xff
        elif filt == 3:
            for i in range(bpp):
                row[i] = (row[i] + (prev[i] // 2)) & 0xff
            for i in range(bpp, stride):
                row[i] = (row[i] + ((row[i - bpp] + prev[i]) // 2)) & 0xff
        elif filt == 4:
            # With no left byte, Paeth(0, up, 0) always selects up.
            for i in range(bpp):
                row[i] = (row[i] + prev[i]) & 0xff
            for i in range(bpp, stride):
                a = row[i - bpp]
                b = prev[i]
                c = prev[i - bpp]
                p = a + b - c
                pa = abs_(p - a)
                pb = abs_(p - b)
                pc = abs_(p - c)
                predictor = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                row[i] = (row[i] + predictor) & 0xff
        else:
            raise ValueError("unsupported PNG filter %d" % filt)
        rgba[dst:dst + stride] = row
        dst += stride
        prev = row
    return bytes(rgba)


def _read_png(path: str) -> _RawPng:
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG file")
    pos = 8
    width = height = bit_depth = color_type = interlace = None
    idat = bytearray()
    meta = {}
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        if pos + 12 + length > len(data):
            raise ValueError("truncated PNG payload")
        crc_actual = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
        if zlib.crc32(kind + payload) & 0xffffffff != crc_actual:
            raise ValueError("PNG chunk %r failed CRC" % kind)
        pos += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _comp, _filt, interlace = struct.unpack(
                ">IIBBBBB", payload)
        elif kind == b"IDAT":
            idat.extend(payload)
        elif kind == b"tEXt" and b"\0" in payload:
            key, value = payload.split(b"\0", 1)
            meta[key.decode("latin-1")] = value.decode("latin-1")
        elif kind == b"iTXt":
            parsed = _parse_itxt(payload)
            if parsed:
                key, value = parsed
                meta[key] = value
        elif kind == b"IEND":
            break
    if width is None or height is None:
        raise ValueError("PNG missing IHDR")
    if bit_depth != 8 or color_type != 6 or interlace != 0:
        raise ValueError("spore PNG must be non-interlaced 8-bit RGBA")
    raw = zlib.decompress(bytes(idat))
    rgba = _unfilter_rgba(raw, width, height)
    return _RawPng(width, height, rgba, meta)


def encode_pixels(stream: bytes, img: Image.Image) -> None:
    """Write a complete raw Grimoire RGBA package into the top-half VCW region."""
    if len(stream) % 4:
        raise ValueError("Grimoire package length is not whole RGBA pixels")
    n_blocks = len(stream) // 4
    if n_blocks > VCW_BLOCKS:
        raise ValueError("stream exceeds VCW capacity")

    if _np is not None:                       # fast path (optional numpy)
        arr = _np.zeros((VCW_H, VCW_W, 4), dtype=_np.uint8)
        flat = arr.reshape(-1, 4)
        flat[:n_blocks] = _np.frombuffer(stream, dtype=_np.uint8).reshape(-1, 4)
        img.paste(Image.fromarray(arr, "RGBA"), (VCW_X, VCW_Y))
        return

    px = img.load()                           # pure-Python fallback
    for y in range(VCW_Y, VCW_Y + VCW_H):
        for x in range(VCW_X, VCW_X + VCW_W):
            px[x, y] = (0, 0, 0, 0)
    for i in range(n_blocks):
        off = i * 4
        px[VCW_X + (i % VCW_W), VCW_Y + (i // VCW_W)] = tuple(
            stream[off:off + 4])


def _read_frame(px, start_block: int, frame_id: str) -> tuple[bytes, int]:
    raw = bytearray()
    for i in range(start_block, VCW_BLOCKS):
        x = VCW_X + (i % VCW_W)
        y = VCW_Y + (i // VCW_W)
        pixel = tuple(int(value) for value in px[x, y])
        if len(pixel) != 4:
            raise ValueError("spore pixel is not one raw RGBA record")
        if pixel == (0, 0, 0, 0):
            raise ValueError("%s ended before its G=0x7f PARITY pixel" % frame_id)
        raw.extend(pixel)
        if pixel[1] == 0x7f:
            return bytes(raw), i + 1
    raise ValueError("%s exceeds the VCW region" % frame_id)


def decode_pixels(img: Image.Image) -> tuple[dict, bytes, dict]:
    """Decode strict raw RGBA statements into manifest, payload, and integrity report."""
    px = img.load()
    header_raw, next_block = _read_frame(px, 0, "spore-header")
    try:
        try:
            header_bytes = decode_quoted_bytes(header_raw, frame_id="spore-header")
        except GrimoireDecodeError:
            header_bytes = decode_quoted_bytes_v010(header_raw, frame_id="spore-header")
        if len(header_bytes) > MAX_HEADER_BYTES:
            raise ValueError("header exceeds the configured size limit")
        header = json.loads(header_bytes.decode("utf-8"))
    except GrimoireDecodeError as exc:
        raise ValueError("spore-header rejected: %s" % exc) from exc
    except Exception as e:
        raise ValueError(f"header is corrupt / unreadable: {e}")

    if header.get("magic") != MAGIC.decode("ascii"):
        raise ValueError("bad spore manifest magic")
    if header.get("format_version") != FORMAT_VERSION:
        raise ValueError("unsupported spore format version %r"
                         % header.get("format_version"))
    profile = header.get("grimoire_profile")
    if profile is None and header.get("encoding") == "grimoire-v0.9-quoted-bytes":
        # Historical v2 payloads had no profile field; this is the documented
        # compatibility fallback and is not content-based edition inference.
        profile = LEGACY_GRIMOIRE_PROFILE
    encode_frame, decode_frame = _codec(profile)
    if header.get("encoding") != profile + "-quoted-bytes":
        raise ValueError("unsupported spore encoding %r" % header.get("encoding"))
    payload_length = header.get("payload_length")
    if not isinstance(payload_length, int) or payload_length < 0:
        raise ValueError("header payload_length invalid")
    frame_count = header.get("payload_frame_count")
    if not isinstance(frame_count, int) or frame_count < 0 or frame_count > VCW_BLOCKS:
        raise ValueError("header payload_frame_count invalid")
    if header.get("frame_payload_bytes") != FRAME_PAYLOAD_BYTES:
        raise ValueError("unsupported payload frame size")

    payload_parts = []
    payload_raw_frames = []
    for index in range(frame_count):
        frame_id = "spore-payload-%06d" % index
        frame_raw, next_block = _read_frame(px, next_block, frame_id)
        try:
            payload_parts.append(decode_frame(frame_raw, frame_id=frame_id))
        except GrimoireDecodeError as exc:
            raise ValueError("%s rejected: %s" % (frame_id, exc)) from exc
        payload_raw_frames.append(frame_raw)

    actual_fingerprint = _full_lane_fingerprint(payload_raw_frames)
    expected_fingerprint = header.get("payload_fingerprint")
    if not isinstance(expected_fingerprint, str) or expected_fingerprint != actual_fingerprint:
        raise ValueError(
            "full-lane fingerprint mismatch: expected=%r actual=%s"
            % (expected_fingerprint, actual_fingerprint))

    payload_bytes = b"".join(payload_parts)
    if len(payload_bytes) != payload_length:
        raise ValueError("payload length mismatch: expected=%d actual=%d"
                         % (payload_length, len(payload_bytes)))
    if _sha(payload_bytes) != header.get("payload_checksum"):
        raise ValueError(
            "payload checksum mismatch: expected=%r actual=%s"
            % (header.get("payload_checksum"), _sha(payload_bytes)))

    if isinstance(img, _RawPng):
        vcw_end = VCW_BLOCKS * 4
        tail = img._rgba[next_block * 4:vcw_end]
        if any(tail):
            raise ValueError("nonzero RGBA data follows the declared spore package")

    report = {
        "statement_count": frame_count + 1,
        "parity_status": "ok",
        "fingerprint_status": "ok",
        "full_lane_fingerprint": actual_fingerprint,
        "used_pixels": next_block,
    }
    return header, payload_bytes, report


# ---------------------------------------------------------------------------
# Visible rendering  (protected boot strip + mutable lower display)
# ---------------------------------------------------------------------------

def _load_font(size: int):
    candidates = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/lib/python3.10/dist-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _load_mono(size: int):
    for p in ("DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/local/lib/python3.10/dist-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSansMono.ttf",
              "C:/Windows/Fonts/consola.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_wrapped(draw, xy, text, font, fill, max_chars, line_h):
    x, y = xy
    for para in text.split("\n"):
        for ln in (textwrap.wrap(para, width=max_chars) or [""]):
            draw.text((x, y), ln, font=font, fill=fill)
            y += line_h
    return y


def render_visible(img: Image.Image, state: dict, status: str) -> None:
    draw = ImageDraw.Draw(img)
    draw.rectangle([DISP_X, DISP_Y, DISP_X + DISP_W - 1, DISP_Y + DISP_H - 1],
                   fill=(248, 248, 250, 255))

    # protected boot strip (canonical -- never creatively altered)
    draw.rectangle([DISP_X, DISP_Y, DISP_X + DISP_W - 1, DISP_Y + BOOT_STRIP_H - 1],
                   fill=(20, 24, 34, 255))
    draw.text((30, DISP_Y + 12), "PROTECTED BOOT STRIP  (canonical - do not alter)",
              font=_load_font(24), fill=(120, 220, 160, 255))
    _draw_wrapped(draw, (30, DISP_Y + 48), BOOTLOADER_TEXT, _load_font(18),
                  (225, 230, 235, 255), max_chars=126, line_h=18)

    ident = state["identity"]
    disp = state.get("display", {})
    y = DISP_Y + BOOT_STRIP_H + 20
    name_color = (150, 40, 40, 255) if status == "FULL" else (30, 40, 60, 255)
    draw.text((40, y), f"SPORE: {ident.get('spore_name', '?')}", font=_load_font(44), fill=name_color)
    y += 62

    lines = [
        f"TASK: {ident.get('task', '')}",
        "WHAT I AM: an AppAI agent inside this PNG (I carry my own reader)",
        "HOW TO USE: give me to a Python-capable LLM, or open me in a Spore app",
        "MEMORY: upper color field (VCW).  KEEP THE SEED DRY: send the ORIGINAL .png",
        f"ENTRIES: {len(state.get('conversation', []))}    "
        f"BIRTH: {ident.get('birth_marker') or '-'}    STATUS: {status}",
    ]
    for extra in disp.get("lines", []):
        lines.append(str(extra))
    lf = _load_font(26)
    for ln in lines:
        y = _draw_wrapped(draw, (40, y), ln, lf, (35, 45, 60, 255), max_chars=104, line_h=33)
        y += 3

    if status == "FULL":
        _draw_wrapped(draw, (40, y + 8),
                      f"SPORE FULL - Name: {ident.get('spore_name', '?')} - memory cannot be "
                      "safely appended; preserve this PNG as the final state.",
                      _load_font(30), (150, 40, 40, 255), max_chars=92, line_h=36)

    # --- runnable QUICKSTART code panel (view area carries a real reader) ----
    code_top = DISP_Y + 590
    draw.rectangle([DISP_X, code_top, DISP_X + DISP_W - 1, DISP_Y + DISP_H - 1],
                   fill=(17, 20, 28, 255))
    draw.text((30, code_top + 10),
              "BOOT FROM THIS IMAGE ALONE  -  paste into Python (reads my memory, then self-extracts my writer):",
              font=_load_font(18), fill=(120, 220, 160, 255))
    cy = code_top + 42
    for ln in QUICKSTART_CODE.split("\n"):
        draw.text((34, cy), ln, font=_load_mono(17), fill=(214, 222, 233, 255))
        cy += 20


# ---------------------------------------------------------------------------
# Header + metadata assembly
# ---------------------------------------------------------------------------

def _make_header(state: dict, payload_bytes: bytes) -> dict:
    ident = state["identity"]
    profile = ident.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)
    payload_frames = _payload_frames(payload_bytes, profile)
    return {
        "magic": "SPOREPNG",
        "format_version": FORMAT_VERSION,
        "canvas": f"{CANVAS_W}x{CANVAS_H}",
        "vcw_region": [VCW_X, VCW_Y, VCW_W, VCW_H],
        "display_region": [DISP_X, DISP_Y, DISP_W, DISP_H],
        "boot_strip_region": [DISP_X, DISP_Y, DISP_W, BOOT_STRIP_H],
        "grimoire_profile": profile,
        "encoding": profile + "-quoted-bytes",
        "payload_format": "stripped_appai_log",
        "payload_length": len(payload_bytes),
        "payload_checksum": _sha(payload_bytes),
        "frame_payload_bytes": FRAME_PAYLOAD_BYTES,
        "payload_frame_count": len(payload_frames),
        "payload_fingerprint": _full_lane_fingerprint(payload_frames),
        "entry_count": len(state.get("conversation", [])),
        "created_at": ident.get("created_at"),
        "updated_at": ident.get("updated_at"),
        "spore_name": ident.get("spore_name"),
        "birth_marker": ident.get("birth_marker"),
        "task": ident.get("task"),
    }


def _metadata_fields(state: dict, header: dict) -> dict:
    ident = state["identity"]
    profile = header.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)
    bootloader = (LEGACY_BOOTLOADER_TEXT if profile == LEGACY_GRIMOIRE_PROFILE
                  else BOOTLOADER_TEXT)
    return {
        "Spore-Format": SPORE_FORMAT,
        "Spore-Name": ident.get("spore_name", ""),
        "Spore-Version": ident.get("version", "1.0.0"),
        "Author": ident.get("author", "") or "",
        "Created-At": ident.get("created_at", ""),
        "Updated-At": ident.get("updated_at", ""),
        "Canvas": f"{CANVAS_W}x{CANVAS_H}",
        "VCW-Region": f"x={VCW_X},y={VCW_Y},w={VCW_W},h={VCW_H}",
        "Display-Region": f"x={DISP_X},y={DISP_Y},w={DISP_W},h={DISP_H}",
        "Boot-Strip-Region": f"x={DISP_X},y={DISP_Y},w={DISP_W},h={BOOT_STRIP_H}",
        "Grimoire-Profile": profile,
        "Encoding": "%s RGBA statements (A=force, G=0x7f parity)" % profile,
        "Payload-Format": "stripped Mantle/AppAI conversation log (JSON)",
        "Payload-Checksum": header["payload_checksum"],
        "Full-Lane-Fingerprint": header["payload_fingerprint"],
        "Payload-Length": str(header["payload_length"]),
        "Entry-Count": str(header["entry_count"]),
        "Birth-Marker": ident.get("birth_marker") or "",
        "Task": ident.get("task", ""),
        "Embedded-Tool": "spore_min.py (base64+zlib) in payload.embedded_tools",
        "Authority": "identity+conversation: VCW payload; bootloader/spec: metadata over strip",
        "Transport-Warning": TRANSPORT_WARNING,
        "Quickstart": QUICKSTART_CODE,
        "Bootloader": bootloader,
    }


def _make_metadata(state: dict, header: dict) -> PngInfo:
    info = PngInfo()
    fields = _metadata_fields(state, header)
    for k, v in fields.items():
        try:
            info.add_itxt(k, v)
        except Exception:
            info.add_text(k, v)
    return info


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _new_state(name: str, task: str, author: str | None,
               profile: str = DEFAULT_GRIMOIRE_PROFILE) -> dict:
    _codec(profile)
    ts = _now()
    return {
        "identity": {
            "spore_name": name,
            "birth_marker": None,
            "task": task,
            "author": author or "",
            "version": "1.0.0",
            "format_version": FORMAT_VERSION,
            "grimoire_profile": profile,
            "created_at": ts,
            "updated_at": ts,
        },
        "tools": TOOLS_PROTOCOL,
        "embedded_tools": _make_embedded_tools(),
        "conversation": [],
        "display": {"lines": [], "status": "ACTIVE"},
    }


def _append_entry(state: dict, role: str, content: str) -> None:
    role = role.lower()
    if role not in ROLE_MAP:
        raise ValueError(f"unknown role {role!r}; use one of {list(ROLE_MAP)}")
    opcode, author, source = ROLE_MAP[role]
    state["conversation"].append({
        "id": len(state["conversation"]),
        "ts": _now(),
        "opcode": opcode,
        "author": author,
        "source": source,
        "content": content,
        "checksum": _checksum_text(content),
    })
    if opcode == "ASSISTANT" and not state["identity"].get("birth_marker"):
        state["identity"]["birth_marker"] = _checksum_text(content)[:8]


def _payload_bytes(state: dict) -> bytes:
    return json.dumps(state, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _fits(state: dict) -> bool:
    payload = _payload_bytes(state)
    if len(payload) > VCW_CAPACITY_BYTES:
        return False
    try:
        header = _make_header(state, payload)
        stream = build_stream(header, payload)
    except ValueError:
        return False
    return (len(stream) // 4) <= VCW_BLOCKS


def _render_spore_stdlib(state: dict, path: str, status: str, header: dict,
                         stream: bytes) -> None:
    """Pure-stdlib canonical spore writer.

    It writes the same VCW payload and metadata as the Pillow path. The lower display is
    a deterministic status panel background instead of drawn text; metadata remains the
    canonical source for the bootloader and quickstart text.
    """
    if len(stream) % 4:
        raise ValueError("Grimoire package length is not whole RGBA pixels")
    n_blocks = len(stream) // 4
    if n_blocks > VCW_BLOCKS:
        raise ValueError("stream exceeds VCW capacity")
    rgba = bytearray(CANVAS_W * CANVAS_H * 4)
    rgba[:len(stream)] = stream

    # Deterministic visible region: dark protected strip, light status area. Pillow, when
    # present, upgrades this to a human-readable text panel without changing payload law.
    for y in range(DISP_Y, DISP_Y + DISP_H):
        if y < DISP_Y + BOOT_STRIP_H:
            color = (20, 24, 34, 255)
        elif status == "FULL":
            color = (88, 22, 28, 255)
        else:
            color = (248, 248, 250, 255)
        row_start = y * CANVAS_W * 4
        row = bytes(color) * CANVAS_W
        rgba[row_start:row_start + CANVAS_W * 4] = row
    _write_png(path, CANVAS_W, CANVAS_H, rgba, _metadata_fields(state, header))


def render_spore(state: dict, path: str, status: str = "ACTIVE") -> str:
    """Regenerate the WHOLE PNG from canonical state and save it to `path`."""
    state["identity"]["updated_at"] = _now()
    disp = state.setdefault("display", {})
    disp["status"] = status

    payload = _payload_bytes(state)
    header = _make_header(state, payload)
    stream = build_stream(header, payload)

    if Image is None:
        _render_spore_stdlib(state, path, status, header, stream)
        return path

    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
    encode_pixels(stream, img)
    render_visible(img, state, status)
    img.save(path, "PNG", pnginfo=_make_metadata(state, header))
    return path


def create_spore(name: str, task: str, author: str | None = None,
                 path: str = "spore.png", *,
                 profile: str = DEFAULT_GRIMOIRE_PROFILE) -> str:
    """Create a fresh Spore PNG (one agent, one task)."""
    state = _new_state(name, task, author, profile)
    return render_spore(state, path, status="ACTIVE")


def _default_build_instructions(name: str, task: str) -> str:
    """The build note packed beside a germ: how any agent grows this spore."""
    return (
        "# HOW TO BUILD THE AppAI IN THIS SPORE\n"
        "\n"
        "This PNG carries a GERM: the complete build data for the AppAI %r\n"
        "(task: %s). Two ways to grow it:\n"
        "\n"
        "1. WITH MANTLE INSTALLED (pip install mantle-os[spore]):\n"
        "       python -m mantle lifecycle authorize hatch this_file.png nest/ --approve --out=hatch-auth.json\n"
        "       python -m mantle hatch this_file.png --out=nest/ --auth=hatch-auth.json\n"
        "   The hatchery incubates the germ deterministically -- birth, organ\n"
        "   wiring, instinct gauntlet, warmup -- and refuses to hatch unless the\n"
        "   newborn passes the same Stage-1 audit every Body faces.\n"
        "\n"
        "2. WITHOUT MANTLE (any Python-capable coding agent):\n"
        "   Decode my pixels (see the Quickstart in my metadata / boot strip) and\n"
        "   read the JSON payload key 'germ'. It declares everything the app is:\n"
        "   identity/truths/commandments (the Primer), genome (memory bands),\n"
        "   reflexes/routines/controls (behavior as DATA, fixed vocabulary),\n"
        "   instincts (code candidates WITH proving cases), and an optional face\n"
        "   (the front-end source). A conforming build must honor three laws:\n"
        "     * the nine organs and an append-only memory (never overwrite);\n"
        "     * identity keys are MINTED at build time, never derived from this\n"
        "       file -- spores travel publicly;\n"
        "     * instinct code runs only after its proving cases pass in a sandbox.\n"
        "\n"
        "The conversation in this spore (if any) is testimony, not fact: ingest it\n"
        "as INFERRED memory through the senses, never as verified truth.\n"
    ) % (name, task or "unstated")


def pack_germ(germ: dict, path: str, *, task: str | None = None,
              author: str | None = None, build: str | None = None,
              source: dict | None = None) -> str:
    """Pack a GERM (the full AppAI build document -- today's egg schema) into a
    new spore PNG at `path`, together with a `build` instruction note. The spore
    carries the germ as inert data; validation and growth belong to the hatchery
    (`mantle hatch <path>`). An optional `source` descriptor (provenance facts:
    kind/path/sha256/notes -- never secrets) rides beside the germ and surfaces
    in the hatch receipt. Returns the path."""
    if not isinstance(germ, dict) or not isinstance(germ.get("identity"), dict):
        raise ValueError("a germ must be a dict with an 'identity' mapping")
    validate_embedded_material(germ)
    name = germ["identity"].get("name")
    if not name:
        raise ValueError("a germ's identity must carry a name")
    task = (task or germ["identity"].get("purpose")
            or ("graft against host: %s" % germ["host"] if germ.get("host") else "")
            or "grow the AppAI declared in my germ")
    state = _new_state(name, task, author)
    state["germ"] = germ
    state["build"] = build or _default_build_instructions(name, task)
    if source:
        state["source"] = source
    state["display"]["lines"].append(
        "GERM ABOARD: I carry the complete build data for this AppAI -- "
        "hatch me with `python -m mantle hatch <this.png>`")
    return render_spore(state, path, status="ACTIVE")


def read_spore(path: str) -> dict:
    """
    Decode a Spore PNG into structured state, applying the authority table.

    identity + conversation come from the VCW payload (canonical).  Metadata is
    only canonical over the visible boot strip.  If the metadata Spore-Name has
    drifted from the payload name, it is reported as a mirror mismatch with the
    VCW payload named canonical.
    """
    # Always use the strict parser: raw 8-bit RGBA, no conversion, color
    # management, premultiplication, resampling, or host-endian reinterpretation.
    img = _read_png(path)
    meta = dict(img.text)
    header, payload_bytes, integrity = decode_pixels(img)
    state = json.loads(payload_bytes.decode("utf-8"))
    status = state.get("display", {}).get("status", "ACTIVE")

    name_mirror_mismatch = None
    meta_name = meta.get("Spore-Name")
    if meta_name and meta_name != state["identity"].get("spore_name"):
        name_mirror_mismatch = {
            "field": "spore_name",
            "metadata_mirror": meta_name,
            "payload": state["identity"].get("spore_name"),
            "canonical": "vcw_payload",
        }

    return {
        "path": path,
        "state": state,
        "header": header,
        "metadata": meta,
        "integrity": integrity,
        "status": status,
        "authority": AUTHORITY,
        "name_mirror_mismatch": name_mirror_mismatch,
    }


def append_turn(path: str, role: str, content: str) -> dict:
    """Append a turn and regenerate the PNG (new living copy); FULL-safe."""
    info = read_spore(path)
    state = info["state"]

    if state.get("display", {}).get("status") == "FULL":
        return {"status": "FULL", "appended": False,
                "reason": "spore already full", "path": path}

    trial = json.loads(json.dumps(state))     # deep copy
    _append_entry(trial, role, content)
    if not _fits(trial):
        render_spore(state, path, status="FULL")   # keep old memory intact
        return {"status": "FULL", "appended": False,
                "reason": "no VCW capacity remaining", "path": path}

    render_spore(trial, path, status="ACTIVE")
    return {"status": "ACTIVE", "appended": True,
            "entry_count": len(trial["conversation"]),
            "birth_marker": trial["identity"].get("birth_marker"),
            "path": path}


def rename_spore(path: str, new_name: str) -> dict:
    info = read_spore(path)
    state = info["state"]
    state["identity"]["spore_name"] = new_name
    _append_entry(state, "identity", f"renamed to {new_name}")
    render_spore(state, path, status=state.get("display", {}).get("status", "ACTIVE"))
    return {"spore_name": new_name, "path": path}


def _check_embedded_tool(state: dict) -> tuple[bool, str]:
    """Return (ok, detail) for the embedded self-hosting tool."""
    et = state.get("embedded_tools")
    if not et or "code" not in et:
        return False, "missing embedded_tools"
    try:
        src = zlib.decompress(base64.b64decode(et["code"])).decode("utf-8")
    except Exception as e:
        return False, f"undecodable: {e}"
    if hashlib.sha256(src.encode("utf-8")).hexdigest() != et.get("sha256"):
        return False, "embedded sha256 mismatch"
    try:
        compile(src, "<embedded spore_min.py>", "exec")
    except SyntaxError as e:
        return False, f"does not compile: {e}"
    if "def read(" not in src or "def append(" not in src:
        return False, "embedded tool lacks read()/append()"
    return True, f"{len(src)} bytes, compiles, has read()/append()"


def verify_spore(path: str) -> dict:
    """Verify a Spore PNG.  Returns {ok, checks, problems, ...}."""
    checks, problems = [], []

    def ck(name, cond, detail=""):
        checks.append({"check": name, "pass": bool(cond), "detail": detail})
        if not cond:
            problems.append(f"{name}: {detail}")

    img = _read_png(path)
    ck("canvas 2000x2000", img.size == (CANVAS_W, CANVAS_H), str(img.size))
    ck("mode RGBA", img.mode == "RGBA")

    info = read_spore(path)
    header, state, meta = info["header"], info["state"], info["metadata"]
    integrity = info["integrity"]

    ck("magic present", header.get("magic") == "SPOREPNG")
    ck("format_version==2", header.get("format_version") == FORMAT_VERSION)
    profile = header.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)
    ck("known Grimoire profile", profile in (LEGACY_GRIMOIRE_PROFILE, DEFAULT_GRIMOIRE_PROFILE))
    ck("encoding matches profile", header.get("encoding") == profile + "-quoted-bytes")
    ck("vcw_region top-half", header.get("vcw_region") == [VCW_X, VCW_Y, VCW_W, VCW_H])
    ck("display_region bottom-half", header.get("display_region") == [DISP_X, DISP_Y, DISP_W, DISP_H])
    ck("boot_strip declared", header.get("boot_strip_region") == [DISP_X, DISP_Y, DISP_W, BOOT_STRIP_H])

    ck("payload checksum matches header",
       _sha(_payload_bytes(state)) == header.get("payload_checksum"))
    ck("entry_count matches", header.get("entry_count") == len(state.get("conversation", [])))

    for key in ("Spore-Format", "Bootloader", "Payload-Checksum",
                "Full-Lane-Fingerprint", "Task",
                "Spore-Name", "Transport-Warning", "Embedded-Tool", "Authority",
                "Quickstart"):
        ck(f"metadata has {key}", key in meta and meta[key] != "")
    expected_bootloaders = {BOOTLOADER_TEXT, LEGACY_BOOTLOADER_TEXT}
    ck("metadata bootloader canonical", meta.get("Bootloader") in expected_bootloaders)
    ck("metadata format canonical", meta.get("Spore-Format") == SPORE_FORMAT)
    ck("metadata fingerprint mirrors manifest",
       meta.get("Full-Lane-Fingerprint") == header.get("payload_fingerprint"))

    et_ok, et_detail = _check_embedded_tool(state)
    ck("embedded self-hosting tool valid", et_ok, et_detail)

    ck("all statement parity verified", integrity.get("parity_status") == "ok",
       str(integrity.get("parity_status")))
    ck("full-lane fingerprint verified", integrity.get("fingerprint_status") == "ok",
       str(integrity.get("fingerprint_status")))

    status = info["status"]
    ck("status is ACTIVE or FULL", status in ("ACTIVE", "FULL"), status)
    ids = [e["id"] for e in state.get("conversation", [])]
    ck("conversation ids ordered 0..n", ids == list(range(len(ids))))

    return {"ok": len(problems) == 0, "checks": checks, "problems": problems,
            "integrity": integrity, "status": status,
            "authority": info["authority"],
            "name_mirror_mismatch": info["name_mirror_mismatch"],
            "embedded_tool": et_detail}


def inspect_spore(path: str, *, include_conversation: bool = False) -> dict:
    """Return a safe manifest for operators deciding whether to activate a spore.

    Raw conversation is intentionally omitted unless explicitly requested.  A spore
    is an inert carrier; inspection never hatches, grafts, executes, or grants
    authority to anything found in its payload.
    """
    info = read_spore(path)
    state = info["state"]
    identity = state.get("identity", {})
    germ = state.get("germ") or {}
    entries = state.get("conversation", [])
    manifest = {
        "inspection_schema": "mantle-spore-inspection-v1",
        "carrier_format": FORMAT_VERSION,
        "inert": True,
        "activation": "requires target-bound operator authorization",
        "path_hint": os.path.basename(os.path.abspath(path)),
        "status": info["status"],
        "integrity": info["integrity"],
        "artifact_fingerprint": info["header"].get("payload_fingerprint"),
        "identity": {k: identity.get(k) for k in ("spore_name", "birth_marker", "author")
                     if k in identity},
        "germ": {
            "schema": germ.get("schema") or germ.get("format") or GERM_SCHEMA_VERSION,
            "task": germ.get("task"),
            "controls": germ.get("controls", []),
            "instincts": germ.get("instincts", []),
            "capabilities": germ.get("capabilities", []),
            "target": germ.get("target"),
            "lineage": germ.get("lineage"),
        },
        "conversation": {
            "count": len(entries),
            "sha256": hashlib.sha256(
                json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "included": bool(include_conversation),
        },
        "authority": "testimony/inferred memory only; never executable authority",
    }
    if include_conversation:
        manifest["conversation"]["entries"] = [
            {"id": e.get("id"), "opcode": e.get("opcode"),
             "content": str(e.get("content", ""))[:4096]}
            for e in entries
        ]
    return manifest


def inspect_spore_typed(path: str):
    """Return the public typed inspection contract without raw conversation."""
    from .lifecycle import LineageAttestation, SporeInspection
    manifest = inspect_spore(path, include_conversation=False)
    with open(path, "rb") as handle:
        artifact_sha = hashlib.sha256(handle.read()).hexdigest()
    germ = manifest["germ"]
    claimed = germ.get("lineage")
    lineage = LineageAttestation.unattested(artifact_sha)
    if isinstance(claimed, dict) and claimed.get("signature"):
        lineage = LineageAttestation(
            "mantle-lineage-attestation-v1", artifact_sha,
            claimed.get("issuer"), claimed.get("parent_fingerprint"),
            claimed.get("signature"), "CLAIMED_UNVERIFIED",
        )
    integrity = manifest.get("integrity") or {}
    return SporeInspection(
        "mantle-spore-inspection-v1",
        integrity.get("parity_status") == "ok" and
        integrity.get("fingerprint_status") == "ok",
        artifact_sha,
        str(germ.get("schema") or GERM_SCHEMA_VERSION),
        True,
        int(manifest["conversation"]["count"]),
        str(manifest["conversation"]["sha256"]),
        lineage,
        tuple(germ.get("controls") or ()),
        tuple(germ.get("instincts") or ()),
        tuple(germ.get("capabilities") or ()),
        germ.get("task"), germ.get("target"),
    )


def validate_embedded_material(germ: dict) -> None:
    """Validate declared embedded files before minting a lifecycle carrier.

    Material is embedded as data, never read by path here. A declaration that
    includes a path must also include the exact content and SHA-256 so a stale,
    missing, or path-only build input cannot be blessed into a spore.
    """
    rows = germ.get("embedded_material", [])
    if rows is None:
        return
    if not isinstance(rows, list):
        raise ValueError("embedded_material must be a list")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("embedded material %d must be a mapping" % index)
        path = str(row.get("path") or "")
        content = row.get("content")
        recorded = str(row.get("sha256") or "").removeprefix("sha256:")
        if not path or os.path.isabs(path) or ".." in path.replace("\\", "/").split("/"):
            raise ValueError("embedded material %d has an unsafe path" % index)
        if not isinstance(content, str) or not recorded:
            raise ValueError("embedded material %d requires content and sha256" % index)
        actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if actual != recorded:
            raise ValueError("embedded material %d sha256 is stale" % index)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_USAGE = """\
spore.py -- SPORE-PNG v1

  python spore.py create  <path> "<name>" "<task>" [author]
  python spore.py pack    <germ.json> <out.png>        # germ (egg data) -> one spore
  python spore.py append  <path> <user|assistant|system|tool|display> "<content>"
  python spore.py read    <path>
  python spore.py inspect <path> [--include-conversation]
  python spore.py rename  <path> "<new name>"
  python spore.py verify  <path>
  python spore.py extract <path> [out=spore_min.py]   # dump the embedded tool
  python spore.py demo    [path]                       # build example_spore.png
"""


def _demo(path: str = "example_spore.png") -> str:
    create_spore("SPORE-SEED", "Answer one question about the SPORE-PNG format.",
                 author="Mantle OS contributors", path=path)
    append_turn(path, "user", "What are you and how do I keep you alive?")
    append_turn(path, "assistant",
                "I am a Spore: a single PNG that holds one agent, one task and one "
                "conversation. My memory is encoded in the color field of my top half, "
                "and I carry a minimal Python reader/writer embedded inside that memory. "
                "Keep me alive by always saving and reusing the LATEST PNG as the living "
                "copy -- and send the ORIGINAL file, never a screenshot.")
    append_turn(path, "user", "Where exactly is the memory stored?")
    append_turn(path, "assistant",
                "In the top half (y=0..999). Each pixel is a raw Grimoire v0.9 RGBA "
                "morpheme: atom, role, evidence, and force. G=0x7f closes each statement "
                "with parity, and the manifest verifies every payload lane with SHA-256.")
    return path


def main(argv):
    if len(argv) < 2:
        print(_USAGE)
        return 2
    cmd = argv[1]
    try:
        if cmd == "create":
            path, name, task = argv[2], argv[3], argv[4]
            author = argv[5] if len(argv) > 5 else None
            create_spore(name, task, author, path)
            print(f"created {path}")
        elif cmd == "pack":
            with open(argv[2], encoding="utf-8") as f:
                germ = json.load(f)
            pack_germ(germ, argv[3])
            print(f"packed germ {argv[2]} into spore {argv[3]}")
        elif cmd == "append":
            print(json.dumps(append_turn(argv[2], argv[3], argv[4]), indent=2))
        elif cmd == "read":
            info = read_spore(argv[2])
            print(json.dumps({
                "identity": info["state"]["identity"],
                "status": info["status"],
                "entries": len(info["state"]["conversation"]),
                "integrity": info["integrity"],
                "name_mirror_mismatch": info["name_mirror_mismatch"],
                "embedded_tool": info["state"].get("embedded_tools", {}).get("sha256"),
                "conversation": [
                    {"id": e["id"], "opcode": e["opcode"], "content": e["content"]}
                    for e in info["state"]["conversation"]
                ],
            }, indent=2))
        elif cmd == "inspect":
            include = "--include-conversation" in argv[3:]
            print(json.dumps(inspect_spore(argv[2], include_conversation=include), indent=2))
        elif cmd == "rename":
            print(json.dumps(rename_spore(argv[2], argv[3]), indent=2))
        elif cmd == "verify":
            rep = verify_spore(argv[2])
            print(json.dumps(rep, indent=2))
            return 0 if rep["ok"] else 1
        elif cmd == "extract":
            out = argv[3] if len(argv) > 3 else "spore_min.py"
            extract_embedded_tool(argv[2], out)
            print(f"embedded tool written to {out}")
        elif cmd == "demo":
            _demo(argv[2] if len(argv) > 2 else "example_spore.png")
            print("demo spore written")
        else:
            print(_USAGE)
            return 2
    except (IndexError, ValueError) as e:
        print(f"error: {e}\n\n{_USAGE}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
