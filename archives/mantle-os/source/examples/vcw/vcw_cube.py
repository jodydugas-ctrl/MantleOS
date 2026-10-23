#!/usr/bin/env python3
"""
vcw_cube.py  --  the VCW Cube, standalone and fully defined  (Mantle OS)

THIS FILE IS THE NORMATIVE, RUNNABLE DEFINITION OF THE VCW CUBE FORMAT.
It is pure standard library (json, zlib, struct, zipfile, hashlib, os, time), imports
NOTHING from the mantle package, and is meant to be READ as much as RUN. Everything it
writes can be loaded by the production engine (`mantle/vcw/cube.py`) and everything the
engine writes can be loaded here -- the interop test in CI proves it on every commit.

--------------------------------------------------------------------------------
WHAT A CUBE IS
--------------------------------------------------------------------------------
The VCW ("Visual Cortex Workspace") cube is the durable experiential memory of a Mantle
AppAI: ONE GENERATION of everything it has sensed, done, learned, and thought.

  cube   = an ordered stack of 800 square RGBA layers      (index 0 .. 799)
  layer  = one 800 x 800 RGBA image = 2,560,000 bytes, stored as a REAL, valid PNG --
           the whole memory is a directory of pictures you can open in any image viewer
  band   = a named, contiguous reserved RANGE of layers, self-described by a BOOT SECTOR
  entry  = one immutable record appended into a band; hashed over every non-volatile field

Think of VCW as booted substrate hardware, and of Grimoire-style meaning as software that
may ride on it. The standard cube is visualized as 800x800x800, but layers materialize only
when a band needs them; 800 is the canonical soft cap/body plan, not a claim that every file
pre-allocates 800 PNGs. RGBA are four addressable lanes. Their semantics are declared by the
boot-selected driver/profile for the layer: log JSON, key-value data, spatial state, exec
reflex payload, database/tool data, or a Grimoire profile such as atom/role/evidence/force.

Identity (the Primer / commandments) is NOT in the cube. It lives in the BODY and
survives every rebirth; the cube is pure experiential memory. (HF-B45: putting the
Primer in the cube is a Stage-1 hard fail.)

--------------------------------------------------------------------------------
ADDRESSING
--------------------------------------------------------------------------------
A single byte inside a layer is addressed by (layer, x, y):

      offset = (y * SIDE + x) * CHANNELS          # CHANNELS = 4 (R,G,B,A)

Normal use never hand-places bytes: each non-spatial layer's pixel stream carries two
length-prefixed JSON blobs behind an 8-byte magic (see LAYER PIXEL STREAM below). The
(layer,x,y) formula is the primitive that spatial drivers and low-level tools rely on.

A LOGICAL entry address is its index into the band's concatenated VISIBLE stream
(tombstoned/quarantined entries excluded), so physical layer reuse never breaks a
reference like <facts.11>. Every entry also carries a BAND-UNIQUE, monotonic `id`
(assigned at append, never reused) for stable tombstone/quarantine addressing.

--------------------------------------------------------------------------------
LAYER PIXEL STREAM  (inside the decoded RGBA bytes of one non-spatial layer)
--------------------------------------------------------------------------------
  [ 8 bytes  MAGIC = b"VCWPNG2\\n" ]
  [ 4 bytes  big-endian uint32: length of the layer-boot JSON ][ layer-boot JSON utf-8 ]
  [ 4 bytes  big-endian uint32: length of the payload JSON    ][ payload JSON utf-8 ]
  [ zero padding up to LAYER_BYTES ]

  layer-boot JSON = {"band": <name>, "layer": <index>, "encoding": <driver>,
                     "private": <bool>, "v": 2}
  payload JSON    = {"content": <driver-native content>}     # log-json: a list of entries

  JSON is serialized compact + sorted: separators=(",", ":"), sort_keys=True.
  A calendar-spatial layer has NO stream: its raw RGBA canvas IS the image.

--------------------------------------------------------------------------------
THE CONTAINER  (a .vcw file is just a ZIP)
--------------------------------------------------------------------------------
  cube.json            -- the cube descriptor (see CubeMeta below)
  layers/000.png ...   -- every ACTIVE layer as a real PNG (zero-padded 3-digit names)

  cube.json keys:
    format           "vcw-cube-png-v2"   (the on-disk format id; stable since v2)
    generation       int                  this cube's generation number
    identity_in_body true                 the Primer is in the Body, never here
    sealed           bool                 sealed = ancestral = read-only forever
    seal_fingerprint "sha256:..." | null  content fingerprint taken at seal time
    bands            {name: band boot sector}
    band_layers      {name: [active physical layer indices, in fill order]}
    band_free        {name: [reclaimed indices available for reuse]}
    next_entry_id    {name: next band-unique entry id}

  BAND BOOT SECTOR = {"band": name, "head": first layer, "span": reserved layer count,
                      "purpose": human-readable reason this band exists,
                      "encoding": driver name ("log-json" | "keyvalue" |
                                  "calendar-spatial" | "exec"),
                      "params": driver params, "private": bool, "v": 3}

--------------------------------------------------------------------------------
THE ENTRY  (log-json bands; THE record of experience)
--------------------------------------------------------------------------------
  {"id": <band-unique int>, "ts": <unix float>, "opcode": "WRITE" | "SENSE" | ...,
   "author": "BODY" | "MIND" | <organ>, "source": <provenance string>,
   "content": <anything JSON>, "tombstone": false, "quarantined": false,
   ...any extra fields (authorship, verified, confidence, ...)...,
   "hash": <sha256 hex, first 16 chars>}

  THE HASH RULE (total): the hash covers EVERY field EXCEPT the four volatile ones the
  Body may flip after birth -- "id", "tombstone", "quarantined", and "hash" itself.
  Serialization for hashing: json.dumps(fields, separators=(",", ":"), sort_keys=True).
  So `authorship` and every extra field are tamper-evident by construction.

  APPEND-ONLY: an entry is never edited or deleted. Retirement = tombstone; isolation =
  quarantine; both only FLIP A FLAG, and both vanish from visible reads. Compaction may
  later drop dead entries and reclaim emptied layers (metabolism) -- that is the Body's
  reflex, not an edit.

--------------------------------------------------------------------------------
THE FOUR RULES OF READING AND APPENDING (commit these to memory)
--------------------------------------------------------------------------------
  1. APPEND, never overwrite. cube.append(band, content) -> a new hashed entry with a
     fresh band-unique id at the band's tail layer.
  2. READ through the VEIL. cube.read(band) returns only visible entries; a private
     band returns [] unless reveal_private=True; tombstoned/quarantined never surface.
  3. VERIFY before trusting. cube.verify() recomputes every entry hash and checks
     structural coherence; save() refuses to replace a healthy file with a sick one
     (durable staged commit: unique stage -> verify -> fsync -> replace -> dir fsync).
  4. SEALED means SEALED. A sealed (ancestral) cube refuses writes forever, and its
     seal fingerprint makes any rewritten history detectable.

Run `python vcw_cube.py selftest` to watch every rule proven, or use the CLI below to
create, append, read, mark, verify, seal, inspect, and extract layers as PNGs.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import tempfile
import time
import zipfile
import zlib
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------------------------------------------------------
# Format constants (normative)
# ----------------------------------------------------------------------------
VCW_FORMAT  = "vcw-cube-png-v2"
LAYER_COUNT = 800
SIDE        = 800
CHANNELS    = 4                          # RGBA
LAYER_BYTES = SIDE * SIDE * CHANNELS     # 2,560,000 bytes per layer
MAGIC       = b"VCWPNG2\n"               # 8 bytes; opens every non-spatial layer stream
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 8 * 1024 * 1024
MAX_IDAT_BYTES = 4 * 1024 * 1024
_SCANLINE_BYTES = (SIDE * CHANNELS + 1) * SIDE
_MAX_META_BYTES = 1024 * 1024
_STAGE_PREFIX = ".mantle-vcw-stage-"

# Capacity doctrine (enforced by the engine; stated here because it is format doctrine):
# allocation pressure >= 0.75 of a band's span triggers METABOLISM (compaction/dedupe);
# >= 0.90 triggers aggressive metabolism. Capacity NEVER triggers rebirth.
OVERFLOW_THRESHOLD  = 0.75
EMERGENCY_THRESHOLD = 0.90

# Fields the Body may set/flip after an entry is born; everything else is in the hash.
VOLATILE_FIELDS = ("id", "tombstone", "quarantined", "hash")


# ============================================================================
# 1. THE ENTRY -- making and hashing immutable records
# ============================================================================
def entry_hash(entry: Dict[str, Any]) -> str:
    """sha256 (first 16 hex chars) over every NON-VOLATILE field, serialized compact
    and key-sorted. Deterministic across processes, platforms, and save/reload."""
    h = {k: v for k, v in entry.items() if k not in VOLATILE_FIELDS}
    blob = json.dumps(h, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def make_entry(content: Any, opcode: str = "WRITE", author: str = "BODY",
               source: str = "", **extra) -> Dict[str, Any]:
    """One immutable record. Extra fields (authorship, verified, ...) go INSIDE the hash."""
    e = {"id": None, "ts": time.time(), "opcode": opcode, "author": author,
         "source": source, "content": content, "tombstone": False, "quarantined": False}
    e.update(extra)
    e["hash"] = entry_hash(e)
    return e


def visible(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The base visibility filter: tombstoned/quarantined entries never surface."""
    return [e for e in entries if not e.get("tombstone") and not e.get("quarantined")]


# ============================================================================
# 2. THE PNG CODEC -- every layer is a real image (pure stdlib, hand-rolled)
# ============================================================================
def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png_rgba(raw: bytes, width: int = SIDE, height: int = SIDE) -> bytes:
    """Flat RGBA bytes (len == width*height*4) -> PNG bytes. We write filter type 0
    scanlines at zlib level 1 (the payload is JSON + zero pad; level 1 compresses it
    nearly as well as level 6 for a fraction of the CPU, and the level is invisible to
    any decoder)."""
    if len(raw) != width * height * CHANNELS:
        raise ValueError("encode_png_rgba: raw length %d != %d"
                         % (len(raw), width * height * CHANNELS))
    stride = width * CHANNELS
    out = bytearray(height * (stride + 1))      # filter bytes stay 0 from zero-init
    for y in range(height):
        dst = y * (stride + 1) + 1
        out[dst:dst + stride] = raw[y * stride:(y + 1) * stride]
    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)   # 8-bit RGBA
    return (sig + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", zlib.compress(bytes(out), 1))
            + _png_chunk(b"IEND", b""))


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png_rgba(png: bytes) -> bytes:
    """Decode the fixed VCW PNG profile with CRC and decompression limits."""
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
        if stored_crc != (zlib.crc32(tag + data) & 0xFFFFFFFF):
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
        elif ftype == 1:                                   # Sub
            for i in range(CHANNELS, stride):
                line[i] = (line[i] + line[i - CHANNELS]) & 0xFF
        elif ftype == 2:                                   # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:                                   # Average
            for i in range(stride):
                a = line[i - CHANNELS] if i >= CHANNELS else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:                                   # Paeth
            for i in range(stride):
                a = line[i - CHANNELS] if i >= CHANNELS else 0
                c = prev[i - CHANNELS] if i >= CHANNELS else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 0xFF
        else:
            raise ValueError("decode_png_rgba: bad filter type %d" % ftype)
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return bytes(out)


# ============================================================================
# 3. THE LAYER STREAM -- (layer boot, payload) <-> RGBA bytes
# ============================================================================
def build_layer_rgba(boot: Dict[str, Any], payload: Dict[str, Any]) -> bytes:
    boot_b = json.dumps(boot, separators=(",", ":"), sort_keys=True).encode("utf-8")
    pay_b  = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = (MAGIC + struct.pack(">I", len(boot_b)) + boot_b
            + struct.pack(">I", len(pay_b)) + pay_b)
    if len(body) > LAYER_BYTES:
        raise ValueError("layer payload overflow: %d > %d bytes" % (len(body), LAYER_BYTES))
    return body + b"\x00" * (LAYER_BYTES - len(body))


def parse_layer_rgba(raw: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("parse_layer_rgba: layer must be bytes")
    if len(raw) != LAYER_BYTES:
        raise ValueError("parse_layer_rgba: layer size %d != %d" % (len(raw), LAYER_BYTES))
    if raw[:8] != MAGIC:
        return None, None                                  # a spatial canvas or empty layer
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


def _read_bounded_member(z: zipfile.ZipFile, name: str, limit: int) -> bytes:
    matches = [info for info in z.infolist() if info.filename == name]
    if len(matches) != 1:
        raise ValueError("VCW container needs exactly one %r member" % name)
    info = matches[0]
    if info.file_size > limit:
        raise ValueError("VCW member %r exceeds its size limit" % name)
    with z.open(info, "r") as stream:
        data = stream.read(limit + 1)
    if len(data) != info.file_size or len(data) > limit:
        raise ValueError("VCW member %r has an invalid expanded size" % name)
    return data


def _validate_container_meta(meta: Any) -> None:
    if not isinstance(meta, dict) or meta.get("format") != VCW_FORMAT:
        raise ValueError("not a %s container" % VCW_FORMAT)
    bands = meta.get("bands")
    band_layers = meta.get("band_layers")
    band_free = meta.get("band_free", {})
    next_ids = meta.get("next_entry_id", {})
    if not all(isinstance(value, dict)
               for value in (bands, band_layers, band_free, next_ids)):
        raise ValueError("VCW metadata maps are malformed")
    if not bands or set(bands) != set(band_layers) or len(bands) > LAYER_COUNT:
        raise ValueError("VCW band topology is malformed")
    if not set(band_free).issubset(bands) or not set(next_ids).issubset(bands):
        raise ValueError("VCW metadata names an undeclared band")
    generation = meta.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 0:
        raise ValueError("VCW generation is malformed")
    active = set()
    free = set()
    ranges = []
    for band, boot in bands.items():
        if (not isinstance(band, str) or not band or len(band) > 128
                or not isinstance(boot, dict) or boot.get("band") != band):
            raise ValueError("VCW band metadata is malformed")
        head, span = boot.get("head"), boot.get("span")
        if (not isinstance(head, int) or isinstance(head, bool)
                or not isinstance(span, int) or isinstance(span, bool)
                or span < 1 or head < 0 or head + span > LAYER_COUNT):
            raise ValueError("VCW band range is outside the layer atlas")
        for other_head, other_end in ranges:
            if head < other_end and other_head < head + span:
                raise ValueError("VCW band ranges overlap")
        ranges.append((head, head + span))
        indices = band_layers[band]
        freed = band_free.get(band, [])
        if not isinstance(indices, list) or not indices or not isinstance(freed, list):
            raise ValueError("VCW layer lists are malformed")
        for idx, target in [(idx, active) for idx in indices] + [(idx, free) for idx in freed]:
            if (not isinstance(idx, int) or isinstance(idx, bool)
                    or idx < head or idx >= head + span or idx in active or idx in free):
                raise ValueError("VCW layer index is invalid, duplicated, or out of band")
            target.add(idx)
        next_id = next_ids.get(band, 0)
        if not isinstance(next_id, int) or isinstance(next_id, bool) or next_id < 0:
            raise ValueError("VCW next-entry id is malformed")
    if len(active) + len(free) > LAYER_COUNT:
        raise ValueError("VCW metadata exceeds the layer atlas")


def _decode_layer_payload(raw: bytes, band: str, idx: int,
                          boot: Dict[str, Any]) -> Any:
    layer_boot, payload = parse_layer_rgba(raw)
    expected = {
        "band": band,
        "layer": idx,
        "encoding": boot.get("encoding"),
        "private": bool(boot.get("private")),
        "v": 2,
    }
    if layer_boot is None or payload is None:
        raise ValueError("VCW non-spatial layer is missing its boot sector")
    if any(layer_boot.get(key) != value for key, value in expected.items()):
        raise ValueError("VCW layer boot sector does not match container metadata")
    if "content" not in payload:
        raise ValueError("VCW layer payload has no content")
    return payload["content"]


def _sync_file(path: str) -> None:
    flags = os.O_RDWR if os.name == "nt" else os.O_RDONLY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sync_directory(path: str) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        if os.name == "nt":
            return
        raise
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


# ============================================================================
# 4. BOOT SECTORS + THE STANDARD GENOME
# ============================================================================
def make_band_boot(band: str, head: int, encoding: str = "log-json",
                   params: Optional[Dict[str, Any]] = None, private: bool = False,
                   span: int = 1, purpose: str = "") -> Dict[str, Any]:
    """A band's boot sector. The band reserves [head, head+span-1]; physical layers
    materialize on demand as it fills; every band declares a purpose."""
    return {"band": band, "head": head, "span": max(1, int(span)),
            "purpose": purpose or band, "encoding": encoding, "params": params or {},
            "private": bool(private), "v": 3}


def standard_genome() -> List[Dict[str, Any]]:
    """The eight reserved experiential bands. (No Primer here -- identity is the Body's.)"""
    return [
        make_band_boot("identity",    100, "log-json", span=50,  purpose="experiential self-state"),
        make_band_boot("facts",       150, "log-json", span=50,  purpose="durable truths"),
        make_band_boot("events",      200, "log-json", span=50,  purpose="event history"),
        make_band_boot("discoveries", 250, "log-json", span=50,  purpose="learned knowledge"),
        make_band_boot("senses",      300, "log-json", span=100, purpose="sensor intake"),
        make_band_boot("immune",      400, "log-json", span=50,  purpose="audit/defense"),
        make_band_boot("brain",       450, "log-json", span=50,  purpose="dispatch log"),
        make_band_boot("thoughts",    500, "log-json", span=50,  purpose="private reflection",
                       private=True),
    ]


# ============================================================================
# 5. THE CUBE -- genesis, append, read, mark, verify, seal, save, load
# ============================================================================
class Cube:
    """A minimal but COMPLETE, format-faithful VCW cube. (The production engine in
    mantle/vcw/cube.py adds lazy loading, PNG caching, indexes, and metabolism; the
    bytes it writes and reads are identical to these.)"""

    def __init__(self, generation: int = 0) -> None:
        self.generation = generation
        self.identity_in_body = True            # always; the cube never holds the Primer
        self.sealed = False
        self.seal_fingerprint: Optional[str] = None
        self.bands: Dict[str, Dict[str, Any]] = {}
        self.band_layers: Dict[str, List[int]] = {}
        self.band_free: Dict[str, List[int]] = {}
        self.layers: Dict[int, Any] = {}        # idx -> entries list | dict | bytearray
        self.next_entry_id: Dict[str, int] = {}

    # ---- genesis -----------------------------------------------------------
    @classmethod
    def genesis(cls, genome: Optional[List[Dict[str, Any]]] = None,
                generation: int = 0) -> "Cube":
        """Create a newborn cube: each band gets its boot sector and ONE materialized
        head layer ('every layer has a purpose; allocate only what is needed')."""
        c = cls(generation=generation)
        for boot in (genome or standard_genome()):
            name = boot["band"]
            c.bands[name] = boot
            c.band_layers[name] = [boot["head"]]
            c.band_free[name] = []
            c.layers[boot["head"]] = (bytearray(LAYER_BYTES)
                                      if boot["encoding"] == "calendar-spatial"
                                      else {} if boot["encoding"] in ("keyvalue", "exec")
                                      else [])
            c.next_entry_id[name] = 0
        return c

    # ---- helpers -------------------------------------------------------------
    def _boot(self, band: str) -> Dict[str, Any]:
        if band not in self.bands:
            raise KeyError("no band %r in generation %d" % (band, self.generation))
        return self.bands[band]

    def pressure(self, band: str) -> float:
        """Allocated fraction of the band's reserved span (the capacity doctrine's input)."""
        return len(self.band_layers[band]) / float(self._boot(band)["span"])

    def _allocate(self, band: str) -> int:
        """One more physical layer for a band: reuse a freed slot first, else the next
        unused index in range. (The engine adds the 0.75/0.90 metabolism response here.)"""
        boot = self._boot(band)
        if self.band_free[band]:
            idx = self.band_free[band].pop(0)
        else:
            head, span = boot["head"], boot["span"]
            used = set(self.band_layers[band]) | set(self.band_free[band])
            slots = [i for i in range(head, head + span) if i not in used]
            if not slots:
                raise OverflowError("band %r exhausted its %d reserved layers "
                                    "(metabolize, or CHOOSE a rebirth-reformat -- "
                                    "capacity never forces one)" % (band, span))
            idx = slots[0]
        self.layers[idx] = []
        self.band_layers[band].append(idx)
        return idx

    # ---- RULE 1: APPEND, never overwrite ---------------------------------------
    def append(self, band: str, content: Any, opcode: str = "WRITE",
               author: str = "BODY", source: str = "", **extra) -> Dict[str, Any]:
        """Append one immutable entry. Returns the stored entry (with its band-unique id).
        Raises PermissionError on a sealed cube -- RULE 4."""
        if self.sealed:
            raise PermissionError("generation %d is ANCESTRAL (read-only); "
                                  "experiential writes go to the PRIME only"
                                  % self.generation)
        boot = self._boot(band)
        if boot["encoding"] != "log-json":
            raise ValueError("append() is for log-json bands; %r is %s"
                             % (band, boot["encoding"]))
        e = (content if isinstance(content, dict) and "hash" in content
             else make_entry(content, opcode=opcode, author=author, source=source, **extra))
        e = dict(e)
        e["id"] = self.next_entry_id[band]               # band-unique, monotonic, never reused
        self.next_entry_id[band] = e["id"] + 1
        tail = self.band_layers[band][-1]
        cap = boot["params"].get("max_entries_per_layer")
        if cap and len(self.layers[tail]) >= cap:        # the tail is full: grow on demand
            tail = self._allocate(band)
        self.layers[tail].append(e)
        return e

    # ---- RULE 2: READ through the veil ------------------------------------------
    def read(self, band: str, reveal_private: bool = False) -> List[Dict[str, Any]]:
        """The band's concatenated VISIBLE stream. A private band is veiled to [] unless
        deliberately revealed; tombstoned/quarantined entries never surface."""
        boot = self._boot(band)
        if boot["private"] and not reveal_private:
            return []                                     # the veil
        out: List[Dict[str, Any]] = []
        for idx in self.band_layers[band]:
            out.extend(visible(self.layers[idx]))
        return out

    def retrieve(self, band: str, address: int) -> Optional[Dict[str, Any]]:
        """One entry by LOGICAL address: its index into the visible stream. Stable under
        physical layer reuse. None (a dangling reference -- the caller's Immune System
        must log it) when out of range."""
        vis = self.read(band)
        return vis[address] if 0 <= address < len(vis) else None

    # ---- immune marks (flag flips; never edits) ------------------------------------
    def _find_by_id(self, band: str, entry_id: int) -> Optional[Dict[str, Any]]:
        for idx in self.band_layers[band]:
            for e in self.layers[idx]:
                if e.get("id") == entry_id:
                    return e
        return None

    def tombstone(self, band: str, entry_id: int) -> bool:
        """Retire an entry by its band-unique id. The record remains; reads hide it."""
        if self.sealed:
            raise PermissionError("generation %d is ANCESTRAL (read-only)" % self.generation)
        e = self._find_by_id(band, entry_id)
        if e is None:
            return False
        e["tombstone"] = True
        return True

    def quarantine(self, band: str, entry_id: int) -> bool:
        """Isolate a suspect entry by id. Same mechanics, different meaning."""
        if self.sealed:
            raise PermissionError("generation %d is ANCESTRAL (read-only)" % self.generation)
        e = self._find_by_id(band, entry_id)
        if e is None:
            return False
        e["quarantined"] = True
        return True

    def compact(self, band: str) -> Dict[str, Any]:
        """Metabolism: drop dead entries; an emptied non-tail layer returns to the band's
        free pool for reuse. Visible history is preserved exactly."""
        reclaimed = 0
        keep: List[int] = []
        for idx in list(self.band_layers[band]):
            live = visible(self.layers[idx])
            dropped = len(self.layers[idx]) - len(live)
            self.layers[idx] = live
            if not live and (len(self.band_layers[band]) - reclaimed) > 1:
                del self.layers[idx]
                self.band_free[band].append(idx)
                reclaimed += 1
            else:
                keep.append(idx)
        self.band_layers[band] = keep or [self.band_layers[band][0]]
        return {"band": band, "reclaimed": reclaimed,
                "active": len(self.band_layers[band]), "free": len(self.band_free[band])}

    # ---- RULE 3: VERIFY before trusting ----------------------------------------------
    def verify(self) -> List[str]:
        """Recompute EVERY entry hash + structural coherence + the seal fingerprint.
        An empty list is a healthy cube; anything else is an immune finding."""
        problems: List[str] = []
        for band, boot in self.bands.items():
            if not self.band_layers.get(band):
                problems.append("band %s has no active layer" % band)
            if set(self.band_layers.get(band, [])) & set(self.band_free.get(band, [])):
                problems.append("band %s has a layer both active and free" % band)
            if boot["encoding"] == "log-json":
                seen_ids = set()
                for idx in self.band_layers.get(band, []):
                    for e in self.layers.get(idx, []):
                        if isinstance(e, dict) and "hash" in e and entry_hash(e) != e["hash"]:
                            problems.append("entry hash mismatch in band %s layer %d id=%s"
                                            % (band, idx, e.get("id")))
                        eid = e.get("id")
                        if eid is not None:
                            if eid in seen_ids:
                                problems.append("band %s duplicate entry id %s" % (band, eid))
                            seen_ids.add(eid)
        if self.sealed and self.seal_fingerprint:
            if self.fingerprint() != self.seal_fingerprint:
                problems.append("seal fingerprint mismatch: ancestor content was altered")
        return problems

    # ---- RULE 4: SEALED means SEALED ---------------------------------------------------
    def fingerprint(self) -> str:
        """A deterministic content fingerprint over band metadata + EVERY field of every
        entry (so a tamper that leaves a stale hash behind still breaks the seal).
        Byte-identical to mantle/vcw/cube.py::Cube.fingerprint."""
        h = hashlib.sha256()
        h.update(json.dumps({"generation": self.generation, "bands": self.bands,
                             "band_layers": self.band_layers},
                            sort_keys=True, separators=(",", ":"), default=str).encode())
        for band in sorted(self.bands):
            boot = self.bands[band]
            for idx in self.band_layers[band]:
                content = self.layers[idx]
                if boot["encoding"] == "log-json":
                    h.update(json.dumps(content, sort_keys=True, separators=(",", ":"),
                                        default=str).encode())
                elif boot["encoding"] == "calendar-spatial":
                    h.update(hashlib.sha256(bytes(content)).digest())
                else:
                    h.update(json.dumps(content, sort_keys=True, separators=(",", ":"),
                                        default=str).encode())
        return "sha256:" + h.hexdigest()

    def seal(self) -> str:
        """Freeze this generation as ancestral memory. Returns the fingerprint (the
        Organism records it in the Body's lineage index)."""
        self.sealed = True
        self.seal_fingerprint = self.fingerprint()
        return self.seal_fingerprint

    # ---- persistence: staged commit -> verify -> atomic replace --------------------------
    def _meta(self) -> Dict[str, Any]:
        return {"format": VCW_FORMAT, "generation": self.generation,
                "identity_in_body": self.identity_in_body, "sealed": self.sealed,
                "seal_fingerprint": self.seal_fingerprint, "bands": self.bands,
                "band_layers": self.band_layers, "band_free": self.band_free,
                "next_entry_id": self.next_entry_id}

    def _encode_layer(self, band: str, idx: int) -> bytes:
        boot = self.bands[band]
        content = self.layers[idx]
        if boot["encoding"] == "calendar-spatial":
            return encode_png_rgba(bytes(content))         # the canvas itself IS the image
        lboot = {"band": band, "layer": idx, "encoding": boot["encoding"],
                 "private": bool(boot.get("private")), "v": 2}
        return encode_png_rgba(build_layer_rgba(lboot, {"content": content}))

    def save(self, path: str) -> None:
        """RULE 3: verify and sync a unique stage, replace, then sync the parent."""
        directory = os.path.dirname(os.path.abspath(path))
        stage_fd, stage = tempfile.mkstemp(prefix=_STAGE_PREFIX, dir=directory)
        os.close(stage_fd)
        try:
            with zipfile.ZipFile(stage, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("cube.json", json.dumps(self._meta(), indent=2))
                for band in self.bands:
                    for idx in self.band_layers[band]:
                        z.writestr("layers/%03d.png" % idx, self._encode_layer(band, idx),
                                   compress_type=zipfile.ZIP_STORED)
            problems = Cube.load(stage).verify()
            if problems:
                raise RuntimeError("staged cube failed verify: %s" % problems)
            _sync_file(stage)
            os.replace(stage, path)
            stage = ""
            _sync_file(path)
            _sync_directory(directory)
        finally:
            if stage:
                try:
                    os.remove(stage)
                except FileNotFoundError:
                    pass

    @classmethod
    def load(cls, path: str) -> "Cube":
        with zipfile.ZipFile(path, "r") as z:
            meta = json.loads(_read_bounded_member(z, "cube.json", _MAX_META_BYTES))
            _validate_container_meta(meta)
            c = cls(generation=meta.get("generation", 0))
            c.identity_in_body = meta.get("identity_in_body", True)
            c.sealed = meta.get("sealed", False)
            c.seal_fingerprint = meta.get("seal_fingerprint")
            c.bands = meta["bands"]
            c.band_layers = {k: list(v) for k, v in meta["band_layers"].items()}
            c.band_free = {k: list(v) for k, v in meta.get("band_free", {}).items()}
            c.next_entry_id = {k: int(v) for k, v in meta.get("next_entry_id", {}).items()}
            for band, boot in c.bands.items():
                c.band_free.setdefault(band, [])
                c.next_entry_id.setdefault(band, 0)
                for idx in c.band_layers[band]:
                    raw = decode_png_rgba(_read_bounded_member(
                        z, "layers/%03d.png" % idx, MAX_PNG_BYTES))
                    if boot["encoding"] == "calendar-spatial":
                        c.layers[idx] = bytearray(raw)
                    else:
                        c.layers[idx] = _decode_layer_payload(raw, band, idx, boot)
        return c

    # ---- inspection ------------------------------------------------------------------
    def inspect(self) -> str:
        lines = ["format=%s generation=%d sealed=%s layers=%d"
                 % (VCW_FORMAT, self.generation, self.sealed, len(self.layers))]
        for name, boot in self.bands.items():
            n = len(self.read(name, reveal_private=True))
            lines.append("  band %-12s head=%-3d span=%-3d enc=%-16s entries=%-4d "
                         "pressure=%.2f%s  -- %s"
                         % (name, boot["head"], boot["span"], boot["encoding"], n,
                            self.pressure(name),
                            "  [PRIVATE]" if boot["private"] else "", boot["purpose"]))
        return "\n".join(lines)


# ============================================================================
# 6. SELFTEST -- every rule of the format, proven in one run
# ============================================================================
def selftest() -> int:
    import tempfile
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("  [%s] %-46s %s" % ("PASS" if cond else "FAIL", name, detail))

    def refused(fn):
        try:
            fn()
            return False
        except ValueError:
            return True

    print("VCW cube selftest (standalone, pure stdlib)")
    c = Cube.genesis()
    check("genesis: 8 bands, head layers only",
          len(c.bands) == 8 and len(c.layers) == 8)

    # RULE 1: append
    e0 = c.append("facts", {"k": "sky", "v": "blue"}, source="selftest")
    e1 = c.append("facts", {"k": "grass", "v": "green"})
    c.append("thoughts", "a private musing", opcode="THINK", author="MIND")
    check("append: band-unique monotonic ids", (e0["id"], e1["id"]) == (0, 1))
    check("append: entries hashed", entry_hash(e0) == e0["hash"])

    # RULE 2: the veil + marks
    check("read: visible stream", len(c.read("facts")) == 2)
    check("veil: private band reads []", c.read("thoughts") == [])
    check("veil: deliberate reveal works",
          len(c.read("thoughts", reveal_private=True)) == 1)
    c.tombstone("facts", e0["id"])
    check("tombstone: hidden from read + retrieve",
          len(c.read("facts")) == 1 and c.retrieve("facts", 0)["id"] == e1["id"])
    check("tombstone: record preserved (append-only)",
          any(x["id"] == e0["id"] for x in c.layers[c.band_layers["facts"][0]]))

    # RULE 3: verify + staged save
    check("verify: healthy cube", c.verify() == [])
    d = tempfile.mkdtemp(prefix="vcw-selftest-")
    p = os.path.join(d, "gen000.vcw")
    c.save(p)
    back = Cube.load(p)
    check("round-trip: reads identical", back.read("facts") == c.read("facts"))
    check("round-trip: every layer a real PNG",
          zipfile.ZipFile(p).read("layers/150.png")[:8] == b"\x89PNG\r\n\x1a\n")
    back.layers[back.band_layers["facts"][0]][0]["content"] = {"k": "TAMPERED"}
    problems = back.verify()
    check("verify: catches a tampered entry",
          any("hash mismatch" in pr for pr in problems), problems[:1])
    try:
        back.save(p)
        check("staged save: refuses a corrupt cube", False)
    except RuntimeError:
        check("staged save: refuses a corrupt cube",
              Cube.load(p).verify() == [], "on-disk file still healthy")

    layer = build_layer_rgba(
        {"band": "facts", "layer": 150, "encoding": "log-json", "private": False},
        {"content": []},
    )
    valid_png = encode_png_rgba(layer)
    bad_crc = bytearray(valid_png)
    bad_crc[29] ^= 1
    ihdr = struct.pack(">IIBBBBB", SIDE, SIDE, 8, 6, 0, 0, 0)
    expanded = b"\0" * (_SCANLINE_BYTES + 1)
    bomb = (PNG_SIGNATURE + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", zlib.compress(expanded, 9))
            + _png_chunk(b"IEND", b""))
    bad_layer = bytearray(layer)
    bad_layer[8:12] = struct.pack(">I", LAYER_BYTES)
    check("hostile input: CRC mismatch refused",
          refused(lambda: decode_png_rgba(bad_crc)))
    check("hostile input: wrong dimensions refused",
          refused(lambda: decode_png_rgba(encode_png_rgba(b"\0" * CHANNELS, 1, 1))))
    check("hostile input: truncated PNG refused",
          refused(lambda: decode_png_rgba(valid_png[:-1])))
    check("hostile input: decompression bomb refused",
          refused(lambda: decode_png_rgba(bomb)))
    check("hostile input: layer length overflow refused",
          refused(lambda: parse_layer_rgba(bad_layer)))
    wrong_boot = build_layer_rgba(
        {"band": "events", "layer": 150, "encoding": "log-json",
         "private": False, "v": 2},
        {"content": []},
    )
    check("hostile input: swapped layer boot refused",
          refused(lambda: _decode_layer_payload(
              wrong_boot, "facts", 150,
              {"band": "facts", "encoding": "log-json", "private": False})))
    hostile_meta = json.loads(json.dumps(c._meta()))
    hostile_meta["bands"]["facts"]["span"] = 100
    check("hostile input: overlapping band atlas refused",
          refused(lambda: _validate_container_meta(hostile_meta)))

    # RULE 4: seal
    c2 = Cube.load(p)
    fp = c2.seal()
    check("seal: fingerprint recorded", fp.startswith("sha256:"))
    try:
        c2.append("facts", {"k": "x"})
        check("seal: writes refused", False)
    except PermissionError:
        check("seal: writes refused", True)
    c2.layers[c2.band_layers["facts"][0]][0]["content"] = {"k": "REWRITTEN"}
    check("seal: tampered history detected",
          any("fingerprint" in pr for pr in c2.verify()))

    # metabolism
    c3 = Cube.genesis([make_band_boot("log", 600, span=4,
                                      params={"max_entries_per_layer": 2},
                                      purpose="rolling")])
    for i in range(4):
        c3.append("log", {"i": i})
    first = c3.band_layers["log"][0]
    for e in c3.layers[first]:
        e["tombstone"] = True
    rep = c3.compact("log")
    check("metabolism: emptied layer reclaimed", rep["reclaimed"] == 1
          and first in c3.band_free["log"])
    c3.append("log", {"j": 0}); c3.append("log", {"j": 1}); c3.append("log", {"j": 2})
    check("metabolism: freed layer REUSED", first in c3.band_layers["log"])

    print("\nselftest:", "ALL GREEN" if ok else "FAILURES ABOVE")
    return 0 if ok else 1


# ============================================================================
# 7. CLI -- create / append / read / retrieve / tombstone / quarantine /
#           verify / seal / inspect / extract / selftest
# ============================================================================
def _cli(argv: List[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="vcw_cube",
                                description="the standalone VCW cube (vcw-cube-png-v2)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("create", help="genesis a new cube file (standard genome)")
    s.add_argument("path")

    s = sub.add_parser("append", help="append one entry to a band")
    s.add_argument("path"); s.add_argument("band"); s.add_argument("content")
    s.add_argument("--opcode", default="WRITE"); s.add_argument("--author", default="BODY")
    s.add_argument("--source", default="cli")

    s = sub.add_parser("read", help="read a band's visible stream")
    s.add_argument("path"); s.add_argument("band")
    s.add_argument("--reveal-private", action="store_true")

    s = sub.add_parser("retrieve", help="one entry by visible index")
    s.add_argument("path"); s.add_argument("band"); s.add_argument("index", type=int)

    for mark in ("tombstone", "quarantine"):
        s = sub.add_parser(mark, help="%s an entry by its band-unique id" % mark)
        s.add_argument("path"); s.add_argument("band"); s.add_argument("id", type=int)

    s = sub.add_parser("verify", help="recompute every hash + coherence + seal")
    s.add_argument("path")

    s = sub.add_parser("seal", help="seal as ancestral; print the fingerprint")
    s.add_argument("path")

    s = sub.add_parser("inspect", help="band map, entry counts, pressures")
    s.add_argument("path")

    s = sub.add_parser("extract", help="dump one layer's PNG (open it in any viewer)")
    s.add_argument("path"); s.add_argument("layer", type=int); s.add_argument("out")

    sub.add_parser("selftest", help="prove every rule of the format in one run")

    a = p.parse_args(argv)

    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "create":
        Cube.genesis().save(a.path)
        print("created %s (generation 0, standard genome)" % a.path)
        return 0

    cube = Cube.load(a.path)
    if a.cmd == "append":
        try:
            content = json.loads(a.content)
        except ValueError:
            content = a.content
        e = cube.append(a.band, content, opcode=a.opcode, author=a.author, source=a.source)
        cube.save(a.path)
        print("appended id=%d hash=%s to %s" % (e["id"], e["hash"], a.band))
        return 0
    if a.cmd == "read":
        for e in cube.read(a.band, reveal_private=a.reveal_private):
            print(json.dumps(e))
        return 0
    if a.cmd == "retrieve":
        e = cube.retrieve(a.band, a.index)
        print(json.dumps(e) if e else "DANGLING (log an immune event)")
        return 0 if e else 1
    if a.cmd in ("tombstone", "quarantine"):
        okk = getattr(cube, a.cmd)(a.band, a.id)
        cube.save(a.path)
        print("%s id=%d in %s: %s" % (a.cmd, a.id, a.band, "ok" if okk else "not found"))
        return 0 if okk else 1
    if a.cmd == "verify":
        problems = cube.verify()
        if problems:
            print("UNHEALTHY:")
            for pr in problems:
                print("  -", pr)
            return 1
        print("healthy")
        return 0
    if a.cmd == "seal":
        fp = cube.seal()
        cube.save(a.path)
        print("sealed generation %d  fingerprint=%s" % (cube.generation, fp))
        return 0
    if a.cmd == "inspect":
        print(cube.inspect())
        return 0
    if a.cmd == "extract":
        band = next(b for b, idxs in cube.band_layers.items() if a.layer in idxs)
        with open(a.out, "wb") as f:
            f.write(cube._encode_layer(band, a.layer))
        print("layer %d (%s) -> %s  -- open it in any image viewer" % (a.layer, band, a.out))
        return 0
    return 2


if __name__ == "__main__":
    import sys
    raise SystemExit(_cli(sys.argv[1:]))
