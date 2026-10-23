#!/usr/bin/env python3
"""
mantle.vcw.cube  --  the boot-driven VCW substrate (Mantle OS)

One cube = one generation of experiential memory: a stack of 800 real-PNG layers grouped
into named BANDS, each band self-described by a boot sector that names a driver. Identity
is NOT here -- the Primer lives in the Body; the cube is pure experiential memory.

The 800x800x800 cube is the standard body plan and visualization geometry. The layer count
is a canonical soft cap: layers are materialized only when a boot-declared band needs them.
RGBA are the four substrate lanes, not permanently "thought" or "Grimoire" semantics. A
layer's boot-selected driver/profile declares how those lanes are framed, ended, verified,
and interpreted.

substrate properties (all invariant-preserving):

  lazy materialization     load() can defer layer decode until first touch (cold tier);
                           a sealed ancestor costs nothing until referenced
  hot/cold tiering         the Prime is hot (in memory, flushed on circulate); sealed
                           ancestors are cold (lazy, read-only, written once)
  changed-layer-only save  per-layer signatures; clean layers reuse cached PNG bytes
  staged durable commit    unique same-dir stage -> verify -> fsync -> replace -> dir fsync
  band-unique entry ids    the cube assigns monotonic per-band ids (stable references)
  compact read indexes     id/position lookups are O(1) after one lazy build
  capacity thresholds      allocation pressure >= 0.75 -> metabolism (overflow);
                           >= 0.90 -> aggressive metabolism (emergency). NEVER rebirth.
  sealed generations       seal() freezes the cube and fingerprints its entire content;
                           a tampered ancestor is detectable on load
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from typing import Any, Callable, Dict, List, Optional

from .png import (LAYER_COUNT, MAX_PNG_BYTES, VCW_FORMAT, encode_png_rgba,
                  decode_png_rgba, build_layer_rgba, parse_layer_rgba)
from .bands import get_driver, code_hash
from . import drivers as _drivers  # noqa: F401 -- registers the drivers on import
from .drivers import (ExecDriver, validate_skill_code, validate_calcify_payload,
                      validate_public_grant)
from .entry import entry_hash
from .indexes import BandIndexes
from . import metabolism

_EXEC = ExecDriver()
_LAZY = object()                  # sentinel: layer present in container, not yet decoded
_MAX_META_BYTES = 1024 * 1024
_STAGE_PREFIX = ".mantle-vcw-stage-"


def _read_bounded_member(z: zipfile.ZipFile, name: str, limit: int) -> bytes:
    """Read exactly one ZIP member without allowing duplicate-name or inflate bombs."""
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
    """Reject hostile cube topology before it can allocate layers or lazy sentinels."""
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
    """Bind the embedded layer boot sector to the container topology before use."""
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
    """Commit a rename to its parent directory where the platform exposes dir fsync."""
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


class CapacityError(Exception):
    """Raised when a band has exhausted its reserved range even AFTER metabolism. This is
    the true overflow reflex; it may motivate a chosen rebirth-reformat, never force one."""


class SealError(Exception):
    """Raised when a sealed cube's content no longer matches its seal fingerprint."""


class Cube:
    def __init__(self, generation: int = 0, identity_in_body: bool = True) -> None:
        self.generation = generation
        self.identity_in_body = identity_in_body
        self.sealed = False
        self.seal_fingerprint: Optional[str] = None
        self.bands: Dict[str, Dict[str, Any]] = {}         # name -> boot sector
        self.band_layers: Dict[str, List[int]] = {}        # name -> active physical layers
        self.band_free: Dict[str, List[int]] = {}          # name -> reclaimed reuse pool
        self.layers: Dict[int, Any] = {}                   # idx -> content | _LAZY
        self.indexes = BandIndexes()
        self._next_entry_id: Dict[str, int] = {}           # band -> next band-unique id
        # pressure hook: fn(band, level, report) -- wired to the Immune organ by the Organism
        self.pressure_hook: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
        # lazy source (cold tier): the container path layers are decoded from on demand
        self._lazy_path: Optional[str] = None
        # persistence memo: a layer's PNG is re-encoded only when its signature changed
        self._png_cache: Dict[int, bytes] = {}
        self._layer_sig: Dict[int, str] = {}

    # ---- genesis ----------------------------------------------------------
    @classmethod
    def genesis(cls, genome: List[Dict[str, Any]], generation: int = 0) -> "Cube":
        from .bands import genome_overlaps
        problems = genome_overlaps(genome)
        if problems:
            raise ValueError("genome refused at genesis (overlapping band ranges "
                             "eventually stomp layers): %s" % "; ".join(problems))
        c = cls(generation=generation)
        for boot in genome:
            name = boot["band"]
            c.bands[name] = boot
            c.band_layers[name] = [boot["head"]]
            c.band_free[name] = []
            c.layers[boot["head"]] = get_driver(boot["encoding"]).empty(boot["params"])
            c._next_entry_id[name] = 0
        return c

    def add_band(self, boot: Dict[str, Any]) -> None:
        """Explicitly graft one empty band into an unsealed Prime cube.

        This is a topology migration, not an ordinary memory write.  Callers must
        make the authorization decision before invoking it; the substrate enforces
        uniqueness, range coherence, and registered-driver validity.
        """
        from .bands import genome_overlaps
        if self.sealed:
            raise PermissionError("cannot graft a band into an ancestral cube")
        name = str(boot.get("band", ""))
        if not name:
            raise ValueError("band boot sector requires a name")
        if name in self.bands:
            raise ValueError("band %r already exists" % name)
        proposed = list(self.bands.values()) + [dict(boot)]
        problems = genome_overlaps(proposed)
        if problems:
            raise ValueError("band graft refused: %s" % "; ".join(problems))
        driver = get_driver(str(boot.get("encoding", "")))
        head = int(boot["head"])
        self.bands[name] = dict(boot)
        self.band_layers[name] = [head]
        self.band_free[name] = []
        self.layers[head] = driver.empty(dict(boot.get("params") or {}))
        self._next_entry_id[name] = 0

    # ---- band helpers -----------------------------------------------------
    def _boot(self, band: str) -> Dict[str, Any]:
        if band not in self.bands:
            raise KeyError("no band %r in generation %d" % (band, self.generation))
        return self.bands[band]

    def _driver(self, band: str):
        return get_driver(self._boot(band)["encoding"])

    def encoding(self, band: str) -> str:
        return self._boot(band)["encoding"]

    def primary_layer(self, band: str) -> int:
        return self.band_layers[band][0]

    def layer_count(self, band: str) -> int:
        return len(self.band_layers[band])

    def free_count(self, band: str) -> int:
        return len(self.band_free[band])

    def pressure(self, band: str) -> float:
        return metabolism.pressure(self, band)

    # ---- layer content access (the lazy/cold seam) -------------------------
    def layer_content(self, idx: int) -> Any:
        """Return a layer's driver-native content, decoding it from the container on first
        touch if this cube was lazily loaded."""
        content = self.layers[idx]
        if content is _LAZY:
            content = self._materialize(idx)
        return content

    def set_layer_content(self, idx: int, content: Any) -> None:
        self.layers[idx] = content

    def release_layer(self, band: str, idx: int) -> None:
        """Return a reclaimed physical layer to the band's free pool (metabolism)."""
        self.layers.pop(idx, None)
        self._png_cache.pop(idx, None)
        self._layer_sig.pop(idx, None)
        self.band_free[band].append(idx)

    def _materialize(self, idx: int) -> Any:
        if self._lazy_path is None:
            raise KeyError("layer %d has no content and no lazy source" % idx)
        band = self._band_of(idx)
        boot = self.bands[band]
        with zipfile.ZipFile(self._lazy_path, "r") as z:
            png = _read_bounded_member(z, "layers/%03d.png" % idx, MAX_PNG_BYTES)
        raw = decode_png_rgba(png)
        if boot["encoding"] == "calendar-spatial":
            content = bytearray(raw)
        else:
            content = _decode_layer_payload(raw, band, idx, boot)
        self.layers[idx] = content
        self._png_cache[idx] = png
        self._layer_sig[idx] = self._layer_signature(idx, boot)
        return content

    def materialized_count(self) -> int:
        return sum(1 for v in self.layers.values() if v is not _LAZY)

    def _band_of(self, idx: int) -> str:
        for band, idxs in self.band_layers.items():
            if idx in idxs:
                return band
        raise KeyError("layer %d belongs to no active band" % idx)

    # ---- on-demand allocation + the capacity reflex ------------------------
    def _allocate(self, band: str) -> int:
        """Allocate one physical layer: reuse a freed slot, else the next unused index in
        [head, head+span-1]. Crossing the capacity thresholds triggers METABOLISM (compact/
        dedupe/reclaim) and an immune notification -- never a rebirth. CapacityError only
        when the range is exhausted even after metabolism."""
        boot = self._boot(band)
        level = metabolism.classify_pressure(
            (len(self.band_layers[band]) + 1) / float(boot["span"]))
        if level != "normal":
            report = metabolism.reclaim(self, band, aggressive=(level == "emergency"))
            if self.pressure_hook is not None:
                self.pressure_hook(band, level, report)
        if self.band_free[band]:                          # prefer reuse (efficiency)
            idx = self.band_free[band].pop(0)
        else:
            head, span = boot["head"], boot["span"]
            used = set(self.band_layers[band]) | set(self.band_free[band])
            free_slots = [i for i in range(head, head + span) if i not in used]
            if not free_slots:
                raise CapacityError(
                    "band %r exhausted its %d reserved layers even after metabolism "
                    "(this may motivate a chosen rebirth-reformat, never a forced reset)"
                    % (band, span))
            idx = free_slots[0]
        self.layers[idx] = get_driver(boot["encoding"]).empty(boot["params"])
        self.band_layers[band].append(idx)
        return idx

    # ---- the three verbs ----------------------------------------------------
    def append(self, band: str, value: Any) -> Any:
        if self.sealed:
            raise PermissionError(
                "generation %d is ANCESTRAL (read-only); experiential writes go to PRIME only"
                % self.generation)
        boot = self._boot(band)
        drv = self._driver(band)
        tail = self.band_layers[band][-1]
        content = self.layer_content(tail)
        cap = boot["params"].get("max_entries_per_layer")
        if cap and (boot["encoding"] in metabolism.ENTRY_ENCODINGS
                    or getattr(drv, "entry_stream", False)) and len(content) >= cap:
            tail = self._allocate(band)
            content = self.layer_content(tail)
        if boot["encoding"] == "log-json":
            from .entry import make_entry
            if not (isinstance(value, dict) and "hash" in value):
                value = make_entry(value)                    # wrap a bare value into an entry
            if value.get("id") is None:
                value = dict(value)
                value["id"] = self._next_entry_id.get(band, 0)   # band-unique, monotonic
                self._next_entry_id[band] = value["id"] + 1
        elif getattr(drv, "entry_stream", False):
            # semantic entry streams get the same band-unique monotonic ids as log-json,
            # so indexes, immune marks, deweight, and metabolism work identically.
            # A bare dict (no entry hash, no carrier raw) is wrapped like log-json;
            # dicts carrying raw/hex and raw strings remain carriers.
            from .entry import make_entry
            if isinstance(value, dict) and "hash" not in value \
                    and "raw" not in value and "hex" not in value:
                value = make_entry(value)
            if isinstance(value, dict) and "hash" in value:
                if value.get("id") is None:
                    value = dict(value)
                    value["id"] = self._next_entry_id.get(band, 0)
                    self._next_entry_id[band] = value["id"] + 1
        self.layers[tail] = drv.append(content, boot["params"], value)
        self.indexes.invalidate(band)
        return value

    def read(self, band: str, reveal_private: bool = False, ghosts: bool = False) -> Any:
        boot = self._boot(band)
        if boot["private"] and not reveal_private:
            return []                                     # the veil (a Body reflex)
        drv = self._driver(band)
        if boot["encoding"] == "log-json" or getattr(drv, "entry_stream", False):
            # entry-stream bands (log-json + semantic): concatenate the visible stream
            # across ALL layers in fill order, then apply the graded-memory overlay.
            from .entry import weight_overlay
            out: List[Any] = []
            for idx in self.band_layers[band]:
                out.extend(drv.read(self.layer_content(idx), boot["params"], reveal_private))
            # graded-memory overlay (M3): drop deweight bookkeeping, hide ghosts, order by
            # weight. A band with no deweight activity is returned unchanged.
            return weight_overlay(out, ghosts=ghosts)
        if boot["encoding"] == "keyvalue":
            merged: Dict[str, Any] = {}
            for idx in self.band_layers[band]:
                merged.update(drv.read(self.layer_content(idx), boot["params"]))
            return merged
        return drv.read(self.layer_content(self.primary_layer(band)), boot["params"],
                        reveal_private)

    def _ensure_index(self, band: str) -> None:
        if not self.indexes.has(band):
            self.indexes.build(band, self.band_layers[band], self.layer_content)

    def retrieve(self, band: str, address: Any) -> Any:
        boot = self._boot(band)
        if boot["private"]:
            return None
        drv = self._driver(band)
        if boot["encoding"] == "log-json" or getattr(drv, "entry_stream", False):
            # O(1) via the band index (visible index -> physical layer/position)
            self._ensure_index(band)
            try:
                entry_id = int(address)
            except (TypeError, ValueError):
                return None
            slot = self.indexes.locate(band, entry_id)
            if slot is None:
                return None
            layer, pos = slot
            return self.layer_content(layer)[pos]
        if boot["encoding"] == "keyvalue":
            for idx in self.band_layers[band]:
                v = drv.retrieve(self.layer_content(idx), boot["params"], address)
                if v is not None:
                    return v
            return None
        return drv.retrieve(self.layer_content(self.primary_layer(band)),
                            boot["params"], address)

    # ---- immune marks (tombstone / quarantine by band-unique id) ----------
    def _find_by_id(self, band: str, entry_id: int) -> Optional[Dict[str, Any]]:
        self._ensure_index(band)
        slot = self.indexes.locate_id(band, entry_id)
        if slot is None:
            return None
        layer, pos = slot
        return self.layer_content(layer)[pos]

    def tombstone(self, band: str, entry_id: int) -> bool:
        if self.sealed:
            raise PermissionError("generation %d is ANCESTRAL (read-only)" % self.generation)
        e = self._find_by_id(band, entry_id)
        if e is None:
            return False
        e["tombstone"] = True
        self.indexes.invalidate(band)
        return True

    def quarantine(self, band: str, entry_id: int) -> bool:
        if self.sealed:
            raise PermissionError("generation %d is ANCESTRAL (read-only)" % self.generation)
        e = self._find_by_id(band, entry_id)
        if e is None:
            return False
        e["quarantined"] = True
        self.indexes.invalidate(band)
        return True

    def deweight(self, band: str, entry_id: int, weight: float = 0.0, *,
                 source: str = "deweight", **extra: Any) -> bool:
        """Graded suppression (M3): lower the effective weight of `entry_id` by APPENDING a
        DEWEIGHT event -- the original entry is never touched (its hash stays valid; it
        remains retrievable as a behavioral ghost). `weight=0.0` (default) fully suppresses
        it from default reads; any positive weight keeps it, ranked by weight. Restoring is
        the same operation with a higher weight. Belief history is preserved: every deweight
        is itself an immutable, hashed event."""
        if self.sealed:
            raise PermissionError("generation %d is ANCESTRAL (read-only)" % self.generation)
        if self._find_by_id(band, entry_id) is None:
            return False
        from .entry import make_entry, DEWEIGHT_OPCODE
        self.append(band, make_entry({"target": entry_id, "weight": float(weight)},
                                     opcode=DEWEIGHT_OPCODE, author="BODY", source=source,
                                     **extra))
        return True

    # ---- metabolism (delegated; kept as methods for the Memory organ) ------
    def compact(self, band: str) -> Dict[str, Any]:
        return metabolism.compact(self, band)

    def dedupe(self, band: str) -> Dict[str, Any]:
        return metabolism.dedupe(self, band)

    def reclaim(self, band: str, aggressive: bool = False) -> Dict[str, Any]:
        return metabolism.reclaim(self, band, aggressive)

    def tombstone_all(self, band: str) -> int:
        """Mark every visible entry tombstoned (test/demo helper for compaction)."""
        n = 0
        for idx in self.band_layers[band]:
            for e in self.layer_content(idx):
                if not e.get("tombstone"):
                    e["tombstone"] = True
                    n += 1
        self.indexes.invalidate(band)
        return n

    # ---- calendar convenience ----------------------------------------------
    def calendar_set(self, band: str, iso: str, meaning: str) -> None:
        if self.sealed:
            raise PermissionError("generation %d is ANCESTRAL (read-only)" % self.generation)
        boot = self._boot(band)
        layer = self.primary_layer(band)
        self.layers[layer] = self._driver(band).append(self.layer_content(layer),
                                                       boot["params"], (iso, meaning))

    def calendar_get(self, band: str, iso: str) -> str:
        boot = self._boot(band)
        return self._driver(band).get_date(self.layer_content(self.primary_layer(band)),
                                           boot["params"], iso)

    # ---- reflex layers (calcify + invoke) -----------------------------------
    def calcify(self, band: str, code: str, entry: str, signature: Dict[str, Any],
                capabilities: Dict[str, Any], provenance: Dict[str, Any],
                limits: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Promote proven code into an exec (reflex) layer. PRIME only. Gates, in order:
        static sandbox (the code), then hash/signature/capability/provenance (the payload)."""
        if self.sealed:
            raise PermissionError("cannot calcify into an ancestral cube")
        if self.encoding(band) != "exec":
            raise ValueError("band %r is not an exec band" % band)
        validate_skill_code(code)
        content = {"code": code, "code_hash": code_hash(code), "entry": entry,
                   "language": "python", "signature": signature,
                   "capabilities": capabilities, "limits": limits or {"ms": 200},
                   "provenance": provenance}
        validate_calcify_payload(content)
        self.layers[self.primary_layer(band)] = content
        return content

    def invoke(self, band: str, args: Dict[str, Any],
               granted: Optional[Dict[str, Any]] = None) -> Any:
        """Run a calcified reflex. Works with NO MIND -- a zombie-state capability."""
        granted = validate_public_grant(granted)
        content = self.layer_content(self.primary_layer(band))
        if not content:
            raise ValueError("reflex band %r is empty (no skill calcified)" % band)
        return _EXEC.execute(content, args, granted)

    # ---- sealing (ancestral cubes) ------------------------------------------
    def fingerprint(self) -> str:
        """A deterministic content fingerprint: band metadata + every entry hash + exec/
        spatial content hashes. Used to seal a generation and detect ancestor tampering."""
        h = hashlib.sha256()
        h.update(json.dumps({"generation": self.generation, "bands": self.bands,
                             "band_layers": self.band_layers},
                            sort_keys=True, separators=(",", ":"), default=str).encode())
        for band in sorted(self.bands):
            boot = self.bands[band]
            for idx in self.band_layers[band]:
                content = self.layer_content(idx)
                if boot["encoding"] == "log-json":
                    # cover EVERY field of every entry (not just the recorded hash):
                    # an in-place content tamper that leaves the stale hash behind must
                    # still break the seal.
                    h.update(json.dumps(content, sort_keys=True, separators=(",", ":"),
                                        default=str).encode())
                elif boot["encoding"] == "calendar-spatial":
                    h.update(hashlib.sha256(bytes(content)).digest())
                else:
                    h.update(json.dumps(content, sort_keys=True, separators=(",", ":"),
                                        default=str).encode())
        return "sha256:" + h.hexdigest()

    def seal(self) -> str:
        """Freeze this generation as ancestral memory and fingerprint its entire content.
        The fingerprint is recorded in the Body's lineage index by the Organism."""
        self.sealed = True
        self.seal_fingerprint = self.fingerprint()
        return self.seal_fingerprint

    def verify_seal(self) -> List[str]:
        """For a sealed cube: recompute the fingerprint and compare. Empty list == intact."""
        if not self.sealed:
            return []
        if self.seal_fingerprint is None:
            return ["sealed cube has no fingerprint"]
        actual = self.fingerprint()
        if actual != self.seal_fingerprint:
            return ["seal fingerprint mismatch: ancestor content has been altered"]
        return []

    # ---- persistence ---------------------------------------------------------
    def _layer_signature(self, idx: int, boot: Dict[str, Any]) -> str:
        content = self.layer_content(idx)
        enc = boot["encoding"]
        if enc == "log-json":
            # The signature covers EVERY byte of every entry (not just id/hash/flags):
            # an in-place tamper that leaves the stale hash behind must invalidate the
            # PNG memo, get re-encoded, and be CAUGHT by the staged verify -- never
            # silently masked by a clean cached layer. Still far cheaper than zlib.
            blob = json.dumps(content, separators=(",", ":"), sort_keys=True,
                              default=str).encode("utf-8")
        elif enc == "keyvalue":
            blob = json.dumps(content, separators=(",", ":"), sort_keys=True).encode("utf-8")
        elif enc == "calendar-spatial":
            blob = bytes(content)
        else:
            blob = json.dumps(content, separators=(",", ":"), sort_keys=True,
                              default=str).encode("utf-8")
        return "%s:%s" % (enc, hashlib.sha1(blob).hexdigest())

    def _encode_layer(self, band: str, boot: Dict[str, Any], idx: int) -> bytes:
        content = self.layer_content(idx)
        if boot["encoding"] == "calendar-spatial":
            return encode_png_rgba(bytes(content))          # the canvas itself IS the image
        lboot = {"band": band, "layer": idx, "encoding": boot["encoding"],
                 "private": bool(boot.get("private")), "v": 2}
        return encode_png_rgba(build_layer_rgba(lboot, {"content": content}))

    def _meta(self) -> Dict[str, Any]:
        return {"format": VCW_FORMAT, "generation": self.generation,
                "identity_in_body": self.identity_in_body, "sealed": self.sealed,
                "seal_fingerprint": self.seal_fingerprint,
                "bands": self.bands, "band_layers": self.band_layers,
                "band_free": self.band_free, "next_entry_id": self._next_entry_id}

    def _write_container(self, path: str) -> set:
        """Write the container, re-encoding ONLY layers whose signature changed; clean
        layers reuse their cached PNG bytes. Returns the freshly (re)encoded indices."""
        active = set()
        changed = set()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("cube.json", json.dumps(self._meta(), indent=2))
            for band, boot in self.bands.items():
                for idx in self.band_layers[band]:
                    active.add(idx)
                    sig = self._layer_signature(idx, boot)
                    png = self._png_cache.get(idx)
                    if png is None or self._layer_sig.get(idx) != sig:
                        png = self._encode_layer(band, boot, idx)
                        self._png_cache[idx] = png
                        self._layer_sig[idx] = sig
                        changed.add(idx)
                    # PNG bytes are already compressed -- store verbatim
                    z.writestr("layers/%03d.png" % idx, png,
                               compress_type=zipfile.ZIP_STORED)
        for idx in list(self._png_cache):                  # keep the memo bounded
            if idx not in active:
                self._png_cache.pop(idx, None)
                self._layer_sig.pop(idx, None)
        return changed

    def _verify_staged(self, stage: str, changed: set) -> List[str]:
        """Durability check: metadata sanity + decode of ONLY the freshly-written layers
        (unchanged layers were verified by the save that first wrote them)."""
        problems: List[str] = []
        for band, boot in self.bands.items():
            if not self.band_layers.get(band):
                problems.append("band %s has no active layer" % band)
            try:
                get_driver(boot["encoding"])
            except KeyError:
                problems.append("band %s names unknown driver %s" % (band, boot["encoding"]))
            problems.extend(metabolism.coherence(self, band))
        if not changed:
            return problems
        idx_band = {idx: band for band, idxs in self.band_layers.items() for idx in idxs}
        with zipfile.ZipFile(stage, "r") as z:
            for idx in changed:
                boot = self.bands[idx_band[idx]]
                raw = decode_png_rgba(_read_bounded_member(
                    z, "layers/%03d.png" % idx, MAX_PNG_BYTES))
                if boot["encoding"] == "calendar-spatial":
                    continue
                content = _decode_layer_payload(raw, idx_band[idx], idx, boot)
                if boot["encoding"] == "log-json" or getattr(
                        get_driver(boot["encoding"]), "entry_stream", False):
                    for e in content:
                        if isinstance(e, dict) and "hash" in e and entry_hash(e) != e["hash"]:
                            problems.append("staged entry hash mismatch in band %s layer %d "
                                            "id=%s" % (idx_band[idx], idx, e.get("id")))
        return problems

    def save(self, path: str) -> None:
        """Verify a unique same-directory stage, sync it, replace, then sync the parent.

        A failed writer cannot collide with another save's stage, and after a reported
        success a crash may expose the old valid cube or the new valid cube -- never an
        acknowledged but directory-uncommitted rename on POSIX filesystems.
        """
        directory = os.path.dirname(os.path.abspath(path))
        stage_fd, stage = tempfile.mkstemp(prefix=_STAGE_PREFIX, dir=directory)
        os.close(stage_fd)
        try:
            changed = self._write_container(stage)
            problems = self._verify_staged(stage, changed)
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
        if self._lazy_path is None and self.sealed:
            self._lazy_path = path

    @classmethod
    def load(cls, path: str, lazy: bool = False) -> "Cube":
        """Load a cube. With lazy=True (the cold tier -- default for sealed ancestors via
        Organism.load) layer payloads stay in the container until first touched."""
        with zipfile.ZipFile(path, "r") as z:
            meta = json.loads(_read_bounded_member(z, "cube.json", _MAX_META_BYTES))
            _validate_container_meta(meta)
            c = cls(generation=meta["generation"],
                    identity_in_body=meta.get("identity_in_body", True))
            c.sealed = meta.get("sealed", False)
            c.seal_fingerprint = meta.get("seal_fingerprint")
            c.bands = meta["bands"]
            c.band_layers = {k: list(v) for k, v in meta["band_layers"].items()}
            c.band_free = {k: list(v) for k, v in meta.get("band_free", {}).items()}
            c._next_entry_id = {k: int(v) for k, v in meta.get("next_entry_id", {}).items()}
            for band in c.bands:
                c.band_free.setdefault(band, [])
                c._next_entry_id.setdefault(band, 0)
                get_driver(c.bands[band].get("encoding"))
            if lazy:
                c._lazy_path = path
                for band, idxs in c.band_layers.items():
                    for idx in idxs:
                        c.layers[idx] = _LAZY
                return c
            for band, boot in c.bands.items():
                for idx in c.band_layers[band]:
                    png = _read_bounded_member(z, "layers/%03d.png" % idx, MAX_PNG_BYTES)
                    raw = decode_png_rgba(png)
                    if boot["encoding"] == "calendar-spatial":
                        c.layers[idx] = bytearray(raw)
                    else:
                        c.layers[idx] = _decode_layer_payload(raw, band, idx, boot)
                    c._png_cache[idx] = png
                    c._layer_sig[idx] = c._layer_signature(idx, boot)
        return c

    # ---- verify ----------------------------------------------------------------
    def verify(self) -> List[str]:
        """The Immune System's `scan` reflex: the cube attests to its own integrity --
        band/driver/reuse/coherence sanity plus a recompute of EVERY entry hash, plus the
        seal fingerprint when sealed."""
        problems: List[str] = []
        for band, boot in self.bands.items():
            if not self.band_layers.get(band):
                problems.append("band %s has no active layer" % band)
            try:
                get_driver(boot["encoding"])
            except KeyError:
                problems.append("band %s names unknown driver %s" % (band, boot["encoding"]))
            problems.extend(metabolism.coherence(self, band))
            if boot["encoding"] == "log-json" or getattr(
                    get_driver(boot["encoding"]), "entry_stream", False):
                for idx in self.band_layers.get(band, []):
                    for e in self.layer_content(idx):
                        if isinstance(e, dict) and "hash" in e and entry_hash(e) != e["hash"]:
                            problems.append("entry hash mismatch in band %s layer %d id=%s"
                                            % (band, idx, e.get("id")))
        problems.extend(self.verify_seal())
        return problems
