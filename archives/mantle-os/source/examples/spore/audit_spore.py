#!/usr/bin/env python3
"""
audit_spore.py -- automated SPORE-PNG v1 compliance + robustness checks.

Verifies that the implementation preserves the essential Spore traits and does
NOT quietly grow into full Mantle OS (no organs, immune events, encryption,
tombstones, quarantine, rebirth, lineage, child spores, compaction,
summarization) or degrade into a fake "image demo".

It also hardens beyond the happy path: metadata stripping, Alpha/Force
flattening, statement parity rejection, full-lane fingerprint mismatch, a long
round-trip, and the self-hosting (embedded tool) trait.

This is the PURITY GATE for the SPORE seed. SPORE is the smallest reproductive
form of a Mantle organism (the minimal SEED); its whole value is that it stays
minimal and transparent. Strangeness -- the cache-ghost substrate, symbiosis,
organs -- lives in Mantle tissue LAYERED ON the format (mantle.ghost, the
reproduction facade), never inside spore.py itself. This audit is what keeps
that promise honest: it inspects the seed's own source and refuses feature creep.

Usage:
    python examples/spore/audit_spore.py               # audit mantle.spore + tests
    python examples/spore/audit_spore.py <a_spore.png> # also verify a given PNG

Exit code 0 = PASS, non-zero = FAIL.
"""

from __future__ import annotations

import base64
import os
import re
import shutil
import sys
import tempfile
import zlib

from PIL import Image
from PIL.PngImagePlugin import PngInfo

# The seed now lives inside the package. Import it from Mantle and locate its
# source through __file__ so the "no feature creep" grep inspects the real file.
try:
    from mantle import spore
except ImportError:  # allow running without an editable install
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
    from mantle import spore

SPORE_SRC = os.path.abspath(spore.__file__)

REQUIRED_API = ["create_spore", "read_spore", "append_turn", "render_spore",
                "verify_spore"]

FORBIDDEN_DEFS = ["encrypt", "decrypt", "tombstone", "quarantine", "immune",
                  "rebirth", "lineage", "compact", "summariz", "summaris",
                  "spawn", "evolve"]


class Audit:
    def __init__(self):
        self.passes, self.problems, self.overbuilt = [], [], []

    def ok(self, name, detail=""):
        self.passes.append(name + (f"  ({detail})" if detail else ""))

    def fail(self, name, detail=""):
        self.problems.append(name + (f"  -> {detail}" if detail else ""))

    def over(self, name, detail=""):
        self.overbuilt.append(name + (f"  -> {detail}" if detail else ""))

    def check(self, cond, name, detail=""):
        (self.ok if cond else self.fail)(name, detail)
        return bool(cond)


def _resave(img, srcpath, dst):
    """Re-save `img` preserving the text metadata found in `srcpath`."""
    meta = Image.open(srcpath).text
    pi = PngInfo()
    for k, v in meta.items():
        pi.add_itxt(k, v)
    img.save(dst, "PNG", pnginfo=pi)


# --- static / structural audits --------------------------------------------

def audit_api(a: Audit):
    for fn in REQUIRED_API:
        a.check(hasattr(spore, fn) and callable(getattr(spore, fn)),
                f"required API present: {fn}()")


def audit_geometry(a: Audit):
    a.check(spore.CANVAS_W == 2000 and spore.CANVAS_H == 2000, "canvas is 2000x2000")
    a.check((spore.VCW_X, spore.VCW_Y, spore.VCW_W, spore.VCW_H) == (0, 0, 2000, 1000),
            "VCW region is the top half")
    a.check((spore.DISP_X, spore.DISP_Y, spore.DISP_W, spore.DISP_H) == (0, 1000, 2000, 1000),
            "display region is the bottom half")
    a.check(0 < spore.BOOT_STRIP_H < spore.DISP_H, "boot strip on VCW/display boundary")
    a.check(spore.VCW_CAPACITY_BYTES == (2000 * 1000 - 1) // 2,
            "VCW capacity reflects two semantic morphemes per payload byte")


def audit_no_forbidden(a: Audit):
    with open(SPORE_SRC, encoding="utf-8") as f:
        src = f.read()
    def_names = re.findall(r"^\s*def\s+([A-Za-z_]\w*)", src, re.MULTILINE)
    for token in FORBIDDEN_DEFS:
        hits = [d for d in def_names if token in d.lower()]
        (a.over if hits else a.ok)(
            f"forbidden feature implemented: {token}" if hits else f"no forbidden feature: {token}",
            ", ".join(hits))


def audit_grimoire_frames(a: Audit):
    raw = spore.encode_quoted_bytes(bytes([0x12, 0xab, 0x00, 0xff]))
    records = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]
    a.check(records[0] == (0x02, 0x01, 0x01, 0x0f),
            "HEAD maps physical A to QUOTE force")
    a.check(all(rec[2:] == (0, 0) for rec in records[1:-1]),
            "non-HEAD morphemes set B=A=0 to inherit")
    a.check(records[-1][1] == 0x7f,
            "statement terminates with G=0x7f PARITY")
    a.check(spore.decode_quoted_bytes(raw) == bytes([0x12, 0xab, 0x00, 0xff]),
            "strict RGBA byte order round-trips without endian conversion")

    damaged = bytearray(raw)
    damaged[0] ^= 0x01
    try:
        spore.decode_quoted_bytes(bytes(damaged))
        a.fail("single-byte corruption rejected by statement parity", "no error raised")
    except ValueError:
        a.ok("single-byte corruption rejected by statement parity")


# --- behavioural + robustness audits ---------------------------------------

def audit_behaviour(a: Audit):
    d = tempfile.mkdtemp(prefix="spore_audit_")
    try:
        p = os.path.join(d, "s.png")

        # create + metadata
        spore.create_spore("AUDIT-SPORE", "audit task", author="auditor", path=p)
        info = spore.read_spore(p)
        a.check(info["header"]["magic"] == "SPOREPNG", "create: in-band magic decodes")
        a.check(info["metadata"].get("Bootloader") == spore.BOOTLOADER_TEXT,
                "create: metadata bootloader is canonical text")
        a.check(info["metadata"].get("Transport-Warning", "") != "",
                "create: transport warning present in metadata")

        # self-hosting embedded tool
        ok, detail = spore._check_embedded_tool(info["state"])
        a.check(ok, "self-hosting: embedded spore_min.py valid + compiles", detail)
        src = spore.extract_embedded_tool(p)
        a.check("def append(" in src and "def read(" in src,
                "self-hosting: embedded tool exposes read()/append()")

        # append + ordering + birth marker
        spore.append_turn(p, "user", "hello")
        spore.append_turn(p, "assistant", "hi, I am a spore")
        conv = spore.read_spore(p)["state"]["conversation"]
        a.check([e["id"] for e in conv] == list(range(len(conv))),
                "append: entries kept in order, append-only")
        a.check(bool(spore.read_spore(p)["state"]["identity"]["birth_marker"]),
                "birth marker set from first assistant reply")

        # rename regenerate agreement
        spore.rename_spore(p, "AUDIT-RENAMED")
        info = spore.read_spore(p)
        a.check(info["state"]["identity"]["spore_name"] == info["metadata"]["Spore-Name"]
                == "AUDIT-RENAMED", "regenerate: payload + metadata name agree")

        # AUTHORITY: identity owned by VCW payload; metadata only mirrors it
        img = Image.open(p)
        meta = dict(img.text)
        meta["Spore-Name"] = "META-TAMPER"
        pi = PngInfo()
        for k, v in meta.items():
            pi.add_itxt(k, v)
        img.convert("RGBA").save(p, "PNG", pnginfo=pi)
        info = spore.read_spore(p)
        mm = info["name_mirror_mismatch"]
        a.check(mm and mm["canonical"] == "vcw_payload"
                and info["state"]["identity"]["spore_name"] == "AUDIT-RENAMED",
                "authority: VCW payload owns identity, metadata is only a mirror")

        # one raw-lane mutation is rejected by statement-local parity
        spore.create_spore("CORR", "corruption", path=p)
        spore.append_turn(p, "user", "protect me")
        img = Image.open(p).convert("RGBA")
        px = img.load()
        header_raw, payload_start = spore._read_frame(px, 0, "audit-header")
        x, y = payload_start % spore.VCW_W, payload_start // spore.VCW_W
        rr, gg, bb, aa = px[x, y]
        px[x, y] = (rr ^ 0b1, gg, bb, aa)
        _resave(img, p, p)
        try:
            spore.read_spore(p)
            a.fail("single-byte pixel corruption rejected by PARITY", "no error raised")
        except ValueError as exc:
            a.check("PARITY" in str(exc),
                    "single-byte pixel corruption rejected by PARITY", str(exc))

        # A coordinated data+parity rewrite still fails the container fingerprint.
        spore.create_spore("FINGERPRINT", "fingerprint", path=p)
        spore.append_turn(p, "user", "detect a recomputed statement")
        raw_img = spore._read_png(p)
        data = bytearray(raw_img._rgba)
        px = raw_img.load()
        _, payload_start = spore._read_frame(px, 0, "audit-header")
        frame_raw, frame_end = spore._read_frame(px, payload_start, "audit-payload")
        records = [list(frame_raw[i:i + 4]) for i in range(0, len(frame_raw), 4)]
        records[0][0] = 1 if records[0][0] != 1 else 2
        xr = xb = xa = 0
        for r, _g, b, alpha in records[:-1]:
            xr ^= r
            xb ^= b
            xa ^= alpha
        profile = spore.read_spore(p)["header"].get(
            "grimoire_profile", "grimoire-v0.9")
        if profile == "grimoire-v0.10":
            from mantle.vcw.grimoire_editions.v010 import parity_pixel
            records[-1] = list(parity_pixel([tuple(record) for record in records[:-1]]))
        else:
            records[-1] = [xr or 254, 0x7f, xb, xa]
        rewritten = b"".join(bytes(record) for record in records)
        start = payload_start * 4
        data[start:start + len(rewritten)] = rewritten
        spore._write_png(p, raw_img.size[0], raw_img.size[1], data, dict(raw_img.text))
        try:
            spore.read_spore(p)
            a.fail("full-lane fingerprint rejects parity-preserving rewrite",
                   "no error raised")
        except ValueError as exc:
            a.check("fingerprint mismatch" in str(exc),
                    "full-lane fingerprint rejects parity-preserving rewrite", str(exc))

        # header tamper: broken magic -> refusal
        spore.create_spore("HDR", "header", path=p)
        img = Image.open(p).convert("RGBA")
        px = img.load()
        px[0, 0] = (0, 0, 0, 0)
        _resave(img, p, p)
        try:
            spore.read_spore(p)
            a.fail("header tamper: broken magic refused", "no error raised")
        except ValueError:
            a.ok("header tamper: broken magic refused")

        # metadata stripped: VCW still decodes
        spore.create_spore("NOMETA", "meta strip", path=p)
        spore.append_turn(p, "user", "survive metadata loss")
        Image.open(p).convert("RGBA").save(p, "PNG")   # save WITHOUT pnginfo
        info = spore.read_spore(p)
        a.check(len(info["state"]["conversation"]) == 1 and info["metadata"] == {},
                "metadata stripped: VCW payload still decodes")

        # Alpha flattened: Force semantics destroyed -> loud failure
        spore.create_spore("FLAT", "flatten", path=p)
        spore.append_turn(p, "user", "do not flatten me")
        img = Image.open(p).convert("RGBA")
        px = img.load()
        for x in range(0, 60):          # flatten alpha across the header/payload
            r, g, b, _ = px[x, 0]
            px[x, 0] = (r, g, b, 255)
        _resave(img, p, p)
        loud = False
        try:
            spore.read_spore(p)
        except ValueError:
            loud = True
        a.check(loud, "alpha flattened: Force/parity failure is loud")

        # long round-trip (append-only, ordered, lossless)
        RT_N = 12
        spore.create_spore("RT", "round trip", path=p)
        for i in range(RT_N):
            spore.append_turn(p, "user" if i % 2 == 0 else "assistant", f"turn {i}")
        st = spore.read_spore(p)["state"]
        a.check(len(st["conversation"]) == RT_N, f"round-trip: {RT_N} turns preserved")
        a.check([e["id"] for e in st["conversation"]] == list(range(RT_N)),
                f"round-trip: ids stay ordered 0..{RT_N - 1}")
        q = os.path.join(d, "copy.png")
        spore.render_spore(st, q)
        st2 = spore.read_spore(q)["state"]
        a.check(st2["conversation"] == st["conversation"],
                "round-trip: re-rendered copy decodes to identical conversation")

        # append-only DELTA model: memory = sum of deltas, not repeated history
        spore.create_spore("DELTA", "delta log", path=p)
        sizes = []
        for i in range(4):
            spore.append_turn(p, "user", "D" * 200)   # equal-size deltas
            sizes.append(len(spore._payload_bytes(spore.read_spore(p)["state"])))
        deltas = [sizes[i + 1] - sizes[i] for i in range(len(sizes) - 1)]
        a.check(max(deltas) - min(deltas) <= 40,
                "delta model: each turn grows VCW by a CONSTANT delta (linear, not quadratic)",
                f"deltas={deltas}")
        a.check(max(deltas) < sizes[0],
                "delta model: a turn's growth << total payload (context not re-stored per turn)")

        # capacity / FULL
        spore.create_spore("FULLTEST", "capacity", path=p)
        n0 = len(spore.read_spore(p)["state"]["conversation"])
        res = spore.append_turn(p, "user", "Z" * (spore.VCW_CAPACITY_BYTES + 1000))
        after = spore.read_spore(p)
        a.check(res["status"] == "FULL" and not res["appended"],
                "capacity: oversized turn refused with FULL")
        a.check(len(after["state"]["conversation"]) == n0, "capacity: memory intact")
        a.check(after["status"] == "FULL", "capacity: FULL status shown")
        a.check(len([f for f in os.listdir(d) if f.endswith(".png")]) == 2,
                "capacity: no child spore created")

        # cross-tool: the EMBEDDED embryo can read + grow a spore.py-made spore
        spore.create_spore("XTOOL", "cross tool", path=p)
        spore.append_turn(p, "user", "can the embryo grow me?")
        embryo_path = os.path.join(d, "embryo.py")
        spore.extract_embedded_tool(p, embryo_path)
        import importlib.util
        spec = importlib.util.spec_from_file_location("embryo", embryo_path)
        embryo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(embryo)
        embryo.append(p, "assistant", "yes -- grown by my own embedded tool")
        back = spore.read_spore(p)
        a.check(back["state"]["conversation"][-1]["content"].startswith("yes"),
                "cross-tool: embedded embryo appended a turn spore.py can read")
        a.check(spore.verify_spore(p)["ok"],
                "cross-tool: spore grown by embryo still verifies")

        # strict verify
        spore.create_spore("VERIFY", "verify", path=p)
        rep = spore.verify_spore(p)
        a.check(rep["ok"], "verify_spore() passes on a fresh spore", "; ".join(rep["problems"]))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def audit_png(a: Audit, path: str):
    rep = spore.verify_spore(path)
    a.check(rep["ok"], f"supplied PNG verifies: {os.path.basename(path)}",
            "; ".join(rep["problems"]))


def main(argv):
    a = Audit()
    audit_api(a)
    audit_geometry(a)
    audit_no_forbidden(a)
    audit_grimoire_frames(a)
    audit_behaviour(a)
    if len(argv) > 1:
        audit_png(a, argv[1])

    print("=" * 66)
    print("SPORE-PNG v2 AUDIT")
    print("=" * 66)
    print(f"\nPASSED ({len(a.passes)}):")
    for p in a.passes:
        print(f"  [PASS] {p}")
    if a.overbuilt:
        print(f"\nOVERBUILT ({len(a.overbuilt)}):")
        for o in a.overbuilt:
            print(f"  [OVER] {o}")
    if a.problems:
        print(f"\nMISSING / FAILED ({len(a.problems)}):")
        for pr in a.problems:
            print(f"  [FAIL] {pr}")

    verdict = "PASS" if not a.problems and not a.overbuilt else "FAIL"
    print("\n" + "=" * 66)
    print(f"RESULT: {verdict}   (passed {len(a.passes)}, failed {len(a.problems)}, overbuilt {len(a.overbuilt)})")
    print("=" * 66)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
