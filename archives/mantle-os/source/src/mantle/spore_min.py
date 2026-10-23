#!/usr/bin/env python3
"""
spore_min.py -- the SPORE-PNG v2 "tool embryo".

This is a small, self-contained reader/writer for a Spore PNG.  A base64+zlib
copy of THIS file is embedded inside every Spore's own VCW payload (under
`embedded_tools`), so the PNG carries the minimal code needed to read and grow
itself -- it does not depend on the full `spore.py` SDK being present.

It is format-compatible with spore.py: a Spore written by one can be read and
appended by the other.  It keeps only the essentials (decode, append, render,
read) and always renders in STRICT fill mode.

Dependency: Pillow (PIL).  Standard library otherwise.
"""

from __future__ import annotations
import hashlib, json, sys, textwrap
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

MAGIC = b"SPOREPNG"
FORMAT_VERSION = 2
SPORE_FORMAT = "spore-png-v2"
CANVAS_W = CANVAS_H = 2000
VCW_X, VCW_Y, VCW_W, VCW_H = 0, 0, 2000, 1000
DISP_X, DISP_Y, DISP_W, DISP_H = 0, 1000, 2000, 1000
BOOT_STRIP_H = 300
VCW_BLOCKS = VCW_W * VCW_H
FRAME_PAYLOAD_BYTES = 1024
MAX_HEADER_BYTES = 64 * 1024
VCW_CAPACITY_BYTES = (VCW_BLOCKS - 1) // 2
DEFAULT_GRIMOIRE_PROFILE = "grimoire-v0.10"
LEGACY_GRIMOIRE_PROFILE = "grimoire-v0.9"

# NOTE: this string MUST be byte-identical to spore.py's BOOTLOADER_TEXT.
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

ROLE_MAP = {
    "user": ("USER", "USER", "conversation"),
    "assistant": ("ASSISTANT", "SPORE", "conversation"),
    "system": ("SYSTEM", "APP", "conversation"),
    "tool": ("TOOL", "APP", "conversation"),
    "identity": ("IDENTITY", "SPORE", "metadata"),
    "display": ("DISPLAY", "APP", "display"),
}

# --- Grimoire v0.9 QUOTE framing (self-contained copy of the carrier law) ---

def _parity(records, profile=LEGACY_GRIMOIRE_PROFILE):
    if profile == DEFAULT_GRIMOIRE_PROFILE:
        pr = pb = pa = 0
        for i, (r, g, b, a) in enumerate(records):
            w = i & 7
            rot = lambda value, amount: ((value << (amount & 7)) |
                                          (value >> (8 - (amount & 7)))) & 0xff
            pr ^= rot(r, w)
            pb ^= rot(b, w) ^ rot(g, w)
            pa ^= rot(a, w) ^ rot(g, 7 - w)
        return (pr or 254), 0x7f, pb, pa
    xr = xb = xa = 0
    for r, _g, b, a in records:
        xr ^= r
        xb ^= b
        xa ^= a
    return (xr or 254), 0x7f, xb, xa


def _encode_frame(data, profile=LEGACY_GRIMOIRE_PROFILE):
    if not data:
        raise ValueError("quoted-byte statement requires non-empty bytes")
    nibbles = []
    for value in bytes(data):
        nibbles.extend(((value >> 4) + 1, (value & 0x0f) + 1))
    records = [(nibbles[0], 0x01, 0x01, 0x0f)]
    records.extend((value, 0x40, 0x00, 0x00) for value in nibbles[1:])
    records.append(_parity(records, profile))
    return b"".join(bytes(record) for record in records)


def _decode_frame(raw, profile=LEGACY_GRIMOIRE_PROFILE):
    if len(raw) < 8 or len(raw) % 4:
        raise ValueError("invalid Grimoire frame length")
    records = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]
    if records[-1][1] != 0x7f or tuple(records[-1]) != _parity(records[:-1], profile):
        raise ValueError("PARITY mismatch")
    body = records[:-1]
    if body[0][1:] != (0x01, 0x01, 0x0f):
        raise ValueError("quoted frame must start HEAD/DIRECT/QUOTE")
    if any(record[1:] != (0x40, 0x00, 0x00) for record in body[1:]):
        raise ValueError("quoted continuation must inherit B/A")
    nibbles = [record[0] - 1 for record in body]
    if any(value < 0 or value > 15 for value in nibbles) or len(nibbles) % 2:
        raise ValueError("invalid quoted-byte nibble map")
    return bytes((nibbles[i] << 4) | nibbles[i + 1]
                 for i in range(0, len(nibbles), 2))


def _fingerprint(frames):
    h = hashlib.sha256()
    h.update(b"SPORE-PNG-v2\0")
    for index, raw in enumerate(frames):
        h.update(index.to_bytes(4, "big"))
        h.update(len(raw).to_bytes(4, "big"))
        h.update(raw)
    return "sha256:" + h.hexdigest()


def _payload_frames(payload, profile=LEGACY_GRIMOIRE_PROFILE):
    return [_encode_frame(payload[i:i + FRAME_PAYLOAD_BYTES], profile)
            for i in range(0, len(payload), FRAME_PAYLOAD_BYTES)]


def _sha(data):
    return hashlib.sha256(data).hexdigest()[:16]


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --- stream <-> pixels -----------------------------------------------------

def _read_frame(px, start):
    raw = bytearray()
    for i in range(start, VCW_BLOCKS):
        pixel = tuple(px[VCW_X + (i % VCW_W), VCW_Y + (i // VCW_W)])
        if pixel == (0, 0, 0, 0):
            raise ValueError("frame ended before PARITY")
        raw.extend(pixel)
        if pixel[1] == 0x7f:
            return bytes(raw), i + 1
    raise ValueError("frame exceeds VCW region")


def decode_pixels(img):
    px = img.load()
    header_raw, next_block = _read_frame(px, 0)
    try:
        header_bytes = _decode_frame(header_raw, LEGACY_GRIMOIRE_PROFILE)
    except ValueError:
        header_bytes = _decode_frame(header_raw, DEFAULT_GRIMOIRE_PROFILE)
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise ValueError("header exceeds configured size limit")
    header = json.loads(header_bytes.decode("utf-8"))
    if header.get("magic") != MAGIC.decode("ascii"):
        raise ValueError("bad magic")
    if header.get("format_version") != FORMAT_VERSION:
        raise ValueError("unsupported format version")
    profile = header.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)
    if profile not in (LEGACY_GRIMOIRE_PROFILE, DEFAULT_GRIMOIRE_PROFILE):
        raise ValueError("unsupported Grimoire profile")
    if header.get("encoding") != profile + "-quoted-bytes":
        raise ValueError("unsupported encoding")
    if header.get("frame_payload_bytes") != FRAME_PAYLOAD_BYTES:
        raise ValueError("unsupported frame size")
    frame_count = header.get("payload_frame_count")
    if (not isinstance(frame_count, int) or frame_count < 0
            or frame_count > VCW_BLOCKS):
        raise ValueError("invalid payload frame count")
    payload_length = header.get("payload_length")
    if (not isinstance(payload_length, int) or payload_length < 0
            or payload_length > VCW_CAPACITY_BYTES):
        raise ValueError("invalid payload length")
    parts, raw_frames = [], []
    for _ in range(frame_count):
        raw, next_block = _read_frame(px, next_block)
        parts.append(_decode_frame(raw, profile))
        raw_frames.append(raw)
    actual = _fingerprint(raw_frames)
    if actual != header.get("payload_fingerprint"):
        raise ValueError("full-lane fingerprint mismatch")
    payload = b"".join(parts)
    if len(payload) != payload_length:
        raise ValueError("payload length mismatch")
    if _sha(payload) != header.get("payload_checksum"):
        raise ValueError("payload checksum mismatch")
    report = {
        "statement_count": frame_count + 1,
        "parity_status": "ok",
        "fingerprint_status": "ok",
        "full_lane_fingerprint": actual,
        "used_pixels": next_block,
    }
    return header, payload, report


def _header(state, payload):
    i = state["identity"]
    profile = i.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)
    frames = _payload_frames(payload, profile)
    return {
        "magic": "SPOREPNG", "format_version": FORMAT_VERSION,
        "canvas": f"{CANVAS_W}x{CANVAS_H}",
        "vcw_region": [VCW_X, VCW_Y, VCW_W, VCW_H],
        "display_region": [DISP_X, DISP_Y, DISP_W, DISP_H],
        "boot_strip_region": [DISP_X, DISP_Y, DISP_W, BOOT_STRIP_H],
        "grimoire_profile": profile,
        "encoding": profile + "-quoted-bytes",
        "payload_format": "stripped_appai_log",
        "payload_length": len(payload), "payload_checksum": _sha(payload),
        "frame_payload_bytes": FRAME_PAYLOAD_BYTES,
        "payload_frame_count": len(frames),
        "payload_fingerprint": _fingerprint(frames),
        "entry_count": len(state.get("conversation", [])),
        "created_at": i.get("created_at"), "updated_at": i.get("updated_at"),
        "spore_name": i.get("spore_name"), "birth_marker": i.get("birth_marker"),
        "task": i.get("task"),
    }


def _metadata(state, header):
    i = state["identity"]
    info = PngInfo()
    f = {
        "Spore-Format": SPORE_FORMAT, "Spore-Name": i.get("spore_name", ""),
        "Spore-Version": i.get("version", "1.0.0"), "Author": i.get("author", "") or "",
        "Created-At": i.get("created_at", ""), "Updated-At": i.get("updated_at", ""),
        "Canvas": f"{CANVAS_W}x{CANVAS_H}",
        "VCW-Region": f"x={VCW_X},y={VCW_Y},w={VCW_W},h={VCW_H}",
        "Display-Region": f"x={DISP_X},y={DISP_Y},w={DISP_W},h={DISP_H}",
        "Boot-Strip-Region": f"x={DISP_X},y={DISP_Y},w={DISP_W},h={BOOT_STRIP_H}",
        "Grimoire-Profile": header.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE),
        "Encoding": "%s RGBA statements (A=force, G=0x7f parity)" %
                    header.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE),
        "Payload-Format": "stripped Mantle/AppAI conversation log (JSON)",
        "Payload-Checksum": header["payload_checksum"],
        "Full-Lane-Fingerprint": header["payload_fingerprint"],
        "Payload-Length": str(header["payload_length"]),
        "Entry-Count": str(header["entry_count"]),
        "Birth-Marker": i.get("birth_marker") or "", "Task": i.get("task", ""),
        "Embedded-Tool": "spore_min.py (base64+zlib) in payload.embedded_tools",
        "Authority": "identity+conversation: VCW payload; bootloader/spec: metadata over strip",
        "Transport-Warning": "Transfer the ORIGINAL .png only; do not screenshot/resize/recompress/flatten.",
        "Quickstart": QUICKSTART_CODE,
        "Bootloader": BOOTLOADER_TEXT,
    }
    for k, v in f.items():
        try:
            info.add_itxt(k, v)
        except Exception:
            info.add_text(k, v)
    return info


def _mono(sz):
    for p in ("DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "C:/Windows/Fonts/consola.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def _font(sz):
    for p in ("DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def _render(state, path, status="ACTIVE"):
    state["identity"]["updated_at"] = _now()
    state.setdefault("display", {})["status"] = status
    payload = json.dumps(state, separators=(",", ":"), sort_keys=True).encode("utf-8")
    header = _header(state, payload)
    profile = header.get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)
    hb = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(hb) > MAX_HEADER_BYTES:
        raise ValueError("spore manifest exceeds configured size limit")
    stream = _encode_frame(hb, profile) + b"".join(_payload_frames(payload, profile))

    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
    px = img.load()
    for y in range(VCW_Y, VCW_Y + VCW_H):          # strict fill
        for x in range(VCW_X, VCW_X + VCW_W):
            px[x, y] = (0, 0, 0, 0)
    n = len(stream) // 4
    if n > VCW_BLOCKS:
        raise ValueError("stream exceeds VCW capacity")
    for k in range(n):
        off = k * 4
        px[VCW_X + (k % VCW_W), VCW_Y + (k // VCW_W)] = tuple(
            stream[off:off + 4])

    d = ImageDraw.Draw(img)
    d.rectangle([DISP_X, DISP_Y, DISP_X + DISP_W - 1, DISP_Y + DISP_H - 1], fill=(248, 248, 250, 255))
    d.rectangle([DISP_X, DISP_Y, DISP_X + DISP_W - 1, DISP_Y + BOOT_STRIP_H - 1], fill=(20, 24, 34, 255))
    bf = _font(20)
    y = DISP_Y + 16
    for para in BOOTLOADER_TEXT.split("\n"):
        for ln in (textwrap.wrap(para, 118) or [""]):
            d.text((30, y), ln, font=bf, fill=(225, 230, 235, 255))
            y += 21
    i = state["identity"]
    d.text((40, DISP_Y + BOOT_STRIP_H + 30), f"SPORE: {i.get('spore_name','?')}", font=_font(46), fill=(30, 40, 60, 255))
    d.text((40, DISP_Y + BOOT_STRIP_H + 96), f"TASK: {i.get('task','')}", font=_font(28), fill=(35, 45, 60, 255))
    d.text((40, DISP_Y + BOOT_STRIP_H + 140), f"STATUS: {status}   ENTRIES: {len(state.get('conversation',[]))}   (grown by spore_min)", font=_font(28), fill=(35, 45, 60, 255))
    ct = DISP_Y + 590
    d.rectangle([DISP_X, ct, DISP_X + DISP_W - 1, DISP_Y + DISP_H - 1], fill=(17, 20, 28, 255))
    d.text((30, ct + 10), "BOOT FROM THIS IMAGE ALONE  -  paste into Python (reads memory, then self-extracts writer):", font=_font(18), fill=(120, 220, 160, 255))
    cy = ct + 42
    for ln in QUICKSTART_CODE.split("\n"):
        d.text((34, cy), ln, font=_mono(17), fill=(214, 222, 233, 255)); cy += 20
    img.save(path, "PNG", pnginfo=_metadata(state, header))
    return path


def read(path):
    img = Image.open(path)
    if img.mode != "RGBA":
        raise ValueError("spore PNG must expose raw 8-bit RGBA lanes")
    meta = dict(img.text) if hasattr(img, "text") else {}
    header, payload, integrity = decode_pixels(img)
    state = json.loads(payload.decode("utf-8"))
    return {"state": state, "header": header, "metadata": meta, "integrity": integrity}


def append(path, role, content):
    info = read(path)
    state = info["state"]
    if state.get("display", {}).get("status") == "FULL":
        return {"status": "FULL", "appended": False}
    r = role.lower()
    op, au, src = ROLE_MAP[r]
    trial = json.loads(json.dumps(state))
    trial["conversation"].append({
        "id": len(trial["conversation"]), "ts": _now(), "opcode": op,
        "author": au, "source": src, "content": content,
        "checksum": _sha(content.encode("utf-8")),
    })
    if op == "ASSISTANT" and not trial["identity"].get("birth_marker"):
        trial["identity"]["birth_marker"] = _sha(content.encode("utf-8"))[:8]
    payload = json.dumps(trial, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(payload) > VCW_CAPACITY_BYTES:
        _render(state, path, status="FULL")
        return {"status": "FULL", "appended": False}
    hb = json.dumps(_header(trial, payload), separators=(",", ":"), sort_keys=True).encode("utf-8")
    stream_blocks = (
        len(_encode_frame(hb, _header(trial, payload).get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)))
        + sum(len(frame) for frame in _payload_frames(
            payload, _header(trial, payload).get("grimoire_profile", LEGACY_GRIMOIRE_PROFILE)))
    ) // 4
    if stream_blocks > VCW_BLOCKS:
        _render(state, path, status="FULL")
        return {"status": "FULL", "appended": False}
    _render(trial, path, status="ACTIVE")
    return {"status": "ACTIVE", "appended": True, "entry_count": len(trial["conversation"])}


_USAGE = "python spore_min.py read <path> | append <path> <role> <content>"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(_USAGE); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "read":
        info = read(sys.argv[2])
        print(json.dumps({"identity": info["state"]["identity"],
                          "entries": len(info["state"]["conversation"]),
                          "integrity": info["integrity"]}, indent=2))
    elif cmd == "append":
        print(json.dumps(append(sys.argv[2], sys.argv[3], sys.argv[4]), indent=2))
    else:
        print(_USAGE); sys.exit(1)
