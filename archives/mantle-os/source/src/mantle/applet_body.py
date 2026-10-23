#!/usr/bin/env python3
"""
mantle.applet_body  --  VCW Applet Bodies: APPLET-BODY-CAPSULE (Mantle OS)

A VCW Applet Body is a small app/tool/project stored as SELF-contained app tissue inside
a parent AppAI's VCW. APPLET-BODY-CAPSULE raises an app into a VCW-resident capsule:
source as inert tissue, state as append-only memory, organ map as diagnosis, and face as
phenotype. It is NOT executable authority until trialed, calcified, or rendered through
an approved host boundary.

Composition, not invention -- every mechanic here is an existing Mantle system:

  * dissection      -> mantle.assimilator.scanner (read-only, never executes host code)
  * diagnosis       -> mantle.assimilator.organ_map (the assimilation organ model)
  * band validation -> mantle.compiler.validate_genome (the same Body gate the
                       self-redesigning VCW passes through)
  * the face        -> mantle.phenotype.express / wear (no second face mechanism)
  * refusals        -> immune events (never silent)
  * secrecy         -> mantle.core.redact at the state/report boundary

Status vocabulary (never falsely labeled alive):
  capsule     source, state, face, organ map stored; NOT certified as a Zombie Body
  zombie_body deterministic Body requirements passed the Stage-1 gate (not granted here)
  mind_ready  only under the normal MIND containment + Stage-1 rules (not granted here)

Everything this module creates stays "capsule". `audit_applet_body` is the smaller
deterministic audit for nested applets; it verifies the capsule, it does not certify a
Body. No stored source is ever executed, imported, or installed by any function here.

    python -m mantle applet-create <organism-dir> <source-dir> <name>
    python -m mantle applet-list   <organism-dir>
    python -m mantle applet-show   <organism-dir> <name>
    python -m mantle applet-export <organism-dir> <name> <dest-dir> [--overwrite]
    python -m mantle applet-wear   <organism-dir> <name>
    python -m mantle applet-audit  <organism-dir> <name>
    python -m mantle applet-clone  <organism-dir> <https-github-url>@<commit> <name>
                                    --allow-network
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .assimilator import scanner, organ_map
from .compiler import validate_genome
from .core.redact import redact, contains_secret
from .vcw.entry import make_entry

# ----------------------------------------------------------------------------
# the applet bands (app range 550-749; 550-699 belongs to the assimilator's
# host bands, 640-661 to the phenotype bands -- the applet tissue takes 700-747)
# ----------------------------------------------------------------------------
MANIFEST_BAND = "applets_manifest"
SOURCE_BAND = "applets_source"
STATE_BAND = "applets_state"
ORGANS_BAND = "applets_organs"
LOG_BAND = "applets_log"

MANIFEST_OPCODE = "APPLET-BODY"          # the doctrine phrase, in every audit-visible row
SOURCE_OPCODE = "APPLET-SOURCE"
STATE_OPCODE = "APPLET-STATE"
ORGANS_OPCODE = "APPLET-ORGANS"
LOG_OPCODE = "APPLET-LOG"

CAPSULE = "APPLET-BODY-CAPSULE"

# chunking follows the mantle.phenotype pattern: bounded chunks, bounded entries per
# layer, so no layer approaches LAYER_BYTES once JSON-wrapped.
CHUNK_B64 = 96_000                       # base64 chars per source chunk (~72 KB raw)
MAX_FILE_BYTES = 1_000_000               # larger binaries are skipped unless allowed

SKIP_DIRS = (".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build",
             ".tox", ".mypy_cache", ".pytest_cache", ".eggs", "target")
SKIP_SUFFIXES = (".pyc", ".pyo", ".so", ".dll", ".dylib", ".o", ".a", ".class",
                 ".zip", ".tar", ".gz", ".whl", ".exe")

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class AppletError(Exception):
    """An applet body could not be created, exported, shown, or audited. The reason is
    the message; a matching immune event is recorded on the organism."""


def applet_bands() -> List[Dict[str, Any]]:
    """The five dedicated applet bands as validated boot sectors. Routed through
    mantle.compiler.validate_genome -- the SAME Body gate a self-redesigned genome must
    pass (registered drivers only, app-range heads, no collisions)."""
    return validate_genome([
        {"band": MANIFEST_BAND, "head": 700, "span": 4, "encoding": "log-json",
         "purpose": "applet body manifests (APPLET-BODY-CAPSULE receipts)"},
        {"band": SOURCE_BAND, "head": 704, "span": 24, "encoding": "log-json",
         "private": True, "params": {"max_entries_per_layer": 8},
         "purpose": "applet source as inert, veiled tissue (never executed)"},
        {"band": STATE_BAND, "head": 728, "span": 8, "encoding": "log-json",
         "purpose": "applet state/variables (redacted, append-only)"},
        {"band": ORGANS_BAND, "head": 736, "span": 8, "encoding": "log-json",
         "purpose": "applet organ maps + scan reports (assimilation diagnosis)"},
        {"band": LOG_BAND, "head": 744, "span": 4, "encoding": "log-json",
         "purpose": "append-only applet event log (create/audit/export/wear)"},
    ])


APPLET_BANDS = (MANIFEST_BAND, SOURCE_BAND, STATE_BAND, ORGANS_BAND, LOG_BAND)


def has_applet_bands(org: Any) -> bool:
    return all(b in org.prime.bands for b in APPLET_BANDS)


def grow_applet_bands(org: Any) -> Any:
    """Give an existing organism the applet bands the LAWFUL way: a chosen rebirth (the
    compiler's propose/validate/adopt path), carrying the phenotype faces forward. The
    previous generation seals as a readable ancestor -- append-only history preserved."""
    if has_applet_bands(org):
        return org
    from .vcw.bands import standard_genome
    from . import phenotype as _ph
    _ph.rebirth_with_faces(org, new_genome=standard_genome() + applet_bands(),
                           reason="grow applet bands (%s)" % CAPSULE)
    return org


# ----------------------------------------------------------------------------
# small helpers (private-band physical read follows the phenotype pattern)
# ----------------------------------------------------------------------------
def _raw_entries(org: Any, band: str) -> List[Dict[str, Any]]:
    """Every entry physically in a band, in stream order (works through the veil --
    the applet source band is private, and listing must not need reveal)."""
    out: List[Dict[str, Any]] = []
    for idx in org.prime.band_layers.get(band, []):
        out.extend(org.prime.layer_content(idx))
    return out


def _refuse(org: Any, kind: str, detail: Dict[str, Any], msg: str) -> AppletError:
    try:
        org.immune_event(kind, detail)
    except Exception:
        pass
    return AppletError(msg)


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _log(org: Any, event: str, detail: Dict[str, Any]) -> None:
    org.prime.append(LOG_BAND, make_entry(dict(detail, event=event, capsule=CAPSULE),
                                          opcode=LOG_OPCODE, author="BODY",
                                          source="applet_body"))


def _manifest_of(org: Any, name: str) -> Optional[Dict[str, Any]]:
    for e in _raw_entries(org, MANIFEST_BAND):
        if e.get("opcode") == MANIFEST_OPCODE:
            c = e.get("content") or {}
            if c.get("applet") == name:
                return c
    return None


def _safe_rel_path(rel: str) -> Optional[str]:
    """Normalize a stored relative path; None if it could escape the applet root."""
    norm = os.path.normpath(str(rel).replace("\\", "/"))
    if os.path.isabs(norm) or norm.startswith("..") or norm == ".":
        return None
    if re.match(r"^[A-Za-z]:", norm):                       # windows drive escape
        return None
    parts = norm.replace("\\", "/").split("/")
    if any(p == ".." for p in parts):
        return None
    return norm.replace("\\", "/")


# ----------------------------------------------------------------------------
# collection: walk the project READ-ONLY (data in, nothing executed)
# ----------------------------------------------------------------------------
def _collect_files(source_dir: str, allow_large: bool = False
                   ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    files: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    root = os.path.abspath(source_dir)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS
                             and not d.endswith(".egg-info"))
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if os.path.islink(full):
                skipped.append({"path": rel, "why": "symlink"})
                continue
            if fn.lower().endswith(SKIP_SUFFIXES):
                skipped.append({"path": rel, "why": "binary artifact"})
                continue
            size = os.path.getsize(full)
            if size > MAX_FILE_BYTES and not allow_large:
                skipped.append({"path": rel, "why": "large (%d bytes)" % size})
                continue
            with open(full, "rb") as f:
                data = f.read()
            try:
                data.decode("utf-8")
                is_text = True
            except UnicodeDecodeError:
                is_text = False
            files.append({
                "path": rel, "data": data, "size": len(data),
                "sha256": _sha256(data),
                "mode": os.stat(full).st_mode & 0o777,
                "lang": os.path.splitext(fn)[1].lstrip(".").lower() or "none",
                "text": is_text,
            })
    return files, skipped


def _bundle_hash(files: List[Dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for f in sorted(files, key=lambda x: x["path"]):
        h.update(("%s:%s\n" % (f["path"], f["sha256"])).encode("utf-8"))
    return "sha256:" + h.hexdigest()


# ----------------------------------------------------------------------------
# the face (through mantle.phenotype -- never a second face mechanism)
# ----------------------------------------------------------------------------
def _face_name(name: str) -> str:
    return "applet:" + name


def _synth_face(name: str, source_hash: str, file_count: int,
                role_counts: Dict[str, int]) -> str:
    """A minimal, safe HTML face: a manifest/render surface. The buttons carry
    data-action markers a HOST may bridge; nothing here executes applet source."""
    roles = "".join("<li>%s: %d</li>" % (r, role_counts[r]) for r in sorted(role_counts))
    return ("<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>%(n)s · %(c)s</title></head><body>"
            "<h1>%(n)s</h1><p class=\"capsule\">%(c)s — source as inert tissue; "
            "not executable authority.</p>"
            "<dl><dt>source hash</dt><dd>%(h)s</dd>"
            "<dt>files</dt><dd>%(f)d</dd></dl>"
            "<h2>organ map</h2><ul>%(r)s</ul>"
            "<div id=\"controls\">"
            "<button data-action=\"export-source\">export source</button>"
            "<button data-action=\"inspect-organ-map\">inspect organ map</button>"
            "<button data-action=\"view-state\">view state</button>"
            "<button data-action=\"wear-shed\">wear / shed</button>"
            "</div></body></html>"
            % {"n": name, "c": CAPSULE, "h": source_hash, "f": file_count, "r": roles})


# ----------------------------------------------------------------------------
# create
# ----------------------------------------------------------------------------
def create_applet_body(org: Any, source_dir: str, name: str, *,
                       face_source: Optional[str] = None, entry: str = "",
                       include_source: bool = True,
                       state: Optional[Dict[str, Any]] = None,
                       metadata: Optional[Dict[str, Any]] = None,
                       provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Raise a local project into an APPLET-BODY-CAPSULE inside this organism's VCW.

    Deterministic and read-only toward the project: the assimilator scanner dissects it
    (never executing it), the organ map diagnoses it, the source is stored as inert
    veiled data with per-file hashes, the state is redacted into the state band, and a
    phenotype face is expressed. Returns the creation receipt."""
    if not _NAME_RE.match(name or ""):
        raise _refuse(org, "applet_refused", {"name": name, "why": "bad name"},
                      "applet name %r is not a safe slug ([A-Za-z0-9._-], max 64)" % name)
    if not has_applet_bands(org):
        raise _refuse(org, "applet_refused", {"name": name, "why": "no applet bands"},
                      "this organism has no applet bands (grow_applet_bands(), or birth "
                      "with standard_genome() + applet_bands())")
    if not os.path.isdir(source_dir):
        raise _refuse(org, "applet_refused", {"name": name, "why": "no source dir"},
                      "source directory %r does not exist" % source_dir)
    if _manifest_of(org, name) is not None:
        raise _refuse(org, "applet_refused", {"name": name, "why": "duplicate"},
                      "an applet named %r already exists (applet bodies are append-only; "
                      "use a new name)" % name)

    # 1. Assimilation-style dissection: read-only scan + organ map (existing systems)
    dissection = scanner.scan_project(source_dir)
    omap = organ_map.build_map(dissection)

    # 2. collect the source as data
    files, skipped = _collect_files(source_dir)
    source_hash = _bundle_hash(files)
    secret_suspects = [f["path"] for f in files
                       if f["text"] and contains_secret(f["data"].decode("utf-8"))]
    if secret_suspects:                       # suspicious input -> immune event, never silent
        org.immune_event("applet_source_secret_suspect",
                         {"applet": name, "paths": secret_suspects[:8]})

    source_provenance = {
        "origin": os.path.abspath(source_dir),
        "foreign": True,
        "method": "applet-create",
        "author": "BODY",
        **dict(provenance or {}),
    }
    # Acquired source remains OTHER regardless of caller-provided metadata.
    source_provenance["foreign"] = True
    source_provenance["author"] = "BODY"

    # 3. source into the veiled band, chunked (the phenotype chunking pattern)
    chunks_written = 0
    if include_source:
        for f in files:
            b64 = base64.b64encode(f["data"]).decode("ascii")
            parts = [b64[i:i + CHUNK_B64] for i in range(0, len(b64), CHUNK_B64)] or [""]
            for part, chunk in enumerate(parts):
                org.prime.append(SOURCE_BAND, make_entry(
                    {"applet": name, "path": f["path"], "part": part, "of": len(parts),
                     "b64": chunk, "sha256": f["sha256"], "size": f["size"],
                     "mode": f["mode"], "lang": f["lang"], "encoding": "base64",
                     "provenance": source_provenance},
                    opcode=SOURCE_OPCODE, author="BODY", source="applet_body"))
                chunks_written += 1

    # 4. state (REDACTED at the boundary -- HF-B20 holds for applet tissue too)
    org.prime.append(STATE_BAND, make_entry(
        {"applet": name, "state": redact(dict(state or {}))},
        opcode=STATE_OPCODE, author="BODY", source="applet_body"))

    # 5. organ map + scan report (diagnosis; symbol names are data, still redact-safe)
    org.prime.append(ORGANS_BAND, make_entry(
        {"applet": name,
         "organ_map": {"organs": {o: [s["symbol"] for s in syms]
                                  for o, syms in omap["organs"].items()},
                       "role_counts": omap["role_counts"],
                       "missing_organs": omap["missing_organs"],
                       "external": len(omap["external_host_code"]),
                       "gaps": len(omap["gap_report"])},
         "scan": {"python_files": dissection["python_files"],
                  "files_scanned": len(dissection["files"]),
                  "read_only": dissection["read_only"]}},
        opcode=ORGANS_OPCODE, author="BODY", source="applet_body"))

    # 6. the face: an obvious UI file, the caller's source, or the safe synthesized face
    from . import phenotype as _ph
    if face_source is None:
        index = next((f for f in files if f["path"].lower() in
                      ("index.html", "index.htm") and f["text"]), None)
        face_src = (index["data"].decode("utf-8") if index
                    else _synth_face(name, source_hash, len(files), omap["role_counts"]))
        face_from = index["path"] if index else "synthesized"
    else:
        face_src = face_source
        face_from = "caller"
    face = _face_name(name)
    _ph.express(org, face, "html", face_src, entry=entry or "index.html",
                provenance={"author": "BODY", "applet": name, "face_from": face_from})

    # 7. the manifest (hashes stay raw -- only metadata passes the redactor)
    manifest = {"applet": name, "capsule": CAPSULE, "status": "capsule",
                "source_hash": source_hash, "files": len(files),
                "bytes": sum(f["size"] for f in files), "chunks": chunks_written,
                "skipped": skipped, "role_counts": omap["role_counts"],
                "entry": entry, "face": face, "face_from": face_from,
                "include_source": bool(include_source),
                "secret_suspects": secret_suspects,
                "metadata": redact(dict(metadata or {})),
                "provenance": source_provenance,
                "bands": list(APPLET_BANDS)}
    org.prime.append(MANIFEST_BAND, make_entry(manifest, opcode=MANIFEST_OPCODE,
                                               author="BODY", source="applet_body"))
    _log(org, "create", {"applet": name, "source_hash": source_hash,
                         "files": len(files)})

    # 8. the receipt
    return {"applet": name, "capsule": CAPSULE, "status": "capsule",
            "stage1_ready": False,           # a capsule is never falsely labeled alive
            "source_hash": source_hash, "files": len(files), "chunks": chunks_written,
            "skipped": len(skipped), "role_counts": omap["role_counts"],
            "bands": list(APPLET_BANDS), "face": face, "face_from": face_from,
            "export_available": bool(include_source),
            "secret_suspects": secret_suspects,
            "provenance": source_provenance}


# ----------------------------------------------------------------------------
# list / show
# ----------------------------------------------------------------------------
def list_applet_bodies(org: Any) -> List[Dict[str, Any]]:
    """The cheap catalog: one row per applet, no source dumped."""
    if not has_applet_bands(org):
        return []
    out = []
    for e in _raw_entries(org, MANIFEST_BAND):
        if e.get("opcode") != MANIFEST_OPCODE:
            continue
        c = e.get("content") or {}
        out.append({"applet": c.get("applet"), "status": c.get("status"),
                    "files": c.get("files"), "source_hash": c.get("source_hash"),
                    "face": c.get("face"),
                    "export_available": bool(c.get("include_source"))})
    return out


def show_applet_body(org: Any, name: str) -> Dict[str, Any]:
    """The manifest + diagnosis + file listing WITHOUT dumping the source (paths, sizes,
    and hashes only -- the default view must stay giant-blob-free)."""
    manifest = _manifest_of(org, name)
    if manifest is None:
        raise _refuse(org, "applet_refused", {"name": name, "why": "unknown"},
                      "no applet named %r" % name)
    organs = None
    for e in _raw_entries(org, ORGANS_BAND):
        c = e.get("content") or {}
        if e.get("opcode") == ORGANS_OPCODE and c.get("applet") == name:
            organs = c
    state = None
    for e in _raw_entries(org, STATE_BAND):
        c = e.get("content") or {}
        if e.get("opcode") == STATE_OPCODE and c.get("applet") == name:
            state = c.get("state")
    seen = set()
    listing = []
    for e in _raw_entries(org, SOURCE_BAND):
        c = e.get("content") or {}
        if (e.get("opcode") == SOURCE_OPCODE and c.get("applet") == name
                and c.get("part", 0) == 0 and c.get("path") not in seen):
            seen.add(c["path"])
            listing.append({"path": c["path"], "size": c.get("size"),
                            "sha256": c.get("sha256"), "lang": c.get("lang")})
    audits = [e.get("content") for e in _raw_entries(org, LOG_BAND)
              if e.get("opcode") == LOG_OPCODE
              and (e.get("content") or {}).get("applet") == name
              and (e.get("content") or {}).get("event") == "audit"]
    return {"manifest": manifest, "organs": organs, "state": state,
            "source_files": listing, "last_audit": audits[-1] if audits else None}


# ----------------------------------------------------------------------------
# export ("download sourcecode": VCW -> local directory, hash-verified)
# ----------------------------------------------------------------------------
def _gather_source(org: Any, name: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Reassemble every stored file for an applet. Returns (files, errors); each file is
    {path, data, sha256_recorded, sha256_actual, ok, mode}. Path escapes are errors."""
    by_path: Dict[str, List[Dict[str, Any]]] = {}
    errors: List[str] = []
    for e in _raw_entries(org, SOURCE_BAND):
        c = e.get("content") or {}
        if e.get("opcode") == SOURCE_OPCODE and c.get("applet") == name:
            by_path.setdefault(c.get("path", ""), []).append(c)
    files = []
    for path, parts in sorted(by_path.items()):
        safe = _safe_rel_path(path)
        if safe is None:
            errors.append("path escape refused: %r" % path)
            continue
        parts.sort(key=lambda c: c.get("part", 0))
        try:
            data = b"".join(base64.b64decode(p.get("b64", "")) for p in parts)
        except Exception:
            errors.append("undecodable chunk(s) for %r" % path)
            continue
        recorded = parts[0].get("sha256", "")
        actual = _sha256(data)
        files.append({"path": safe, "data": data, "sha256_recorded": recorded,
                      "sha256_actual": actual, "ok": recorded == actual,
                      "mode": parts[0].get("mode")})
        if recorded != actual:
            errors.append("hash mismatch for %r (tampered or truncated)" % path)
    return files, errors


def export_applet_source(org: Any, name: str, dest_dir: str, *,
                         overwrite: bool = False, dry_run: bool = False
                         ) -> Dict[str, Any]:
    """Reconstruct an applet's source from the VCW into `dest_dir` -- the "download
    sourcecode" surface. Every file's hash is verified BEFORE writing; path traversal is
    refused; existing files are refused unless overwrite=True. dry_run verifies
    everything and writes nothing (the audit uses it). Returns the export receipt."""
    if _manifest_of(org, name) is None:
        raise _refuse(org, "applet_refused", {"name": name, "why": "unknown"},
                      "no applet named %r" % name)
    files, errors = _gather_source(org, name)
    if not files and not errors:
        errors.append("no stored source (created with include_source=False)")
    written: List[str] = []
    verified = sum(1 for f in files if f["ok"])
    if not dry_run:
        dest_real = os.path.realpath(dest_dir)
        collisions = [f["path"] for f in files
                      if os.path.exists(os.path.join(dest_real, f["path"]))]
        if collisions and not overwrite:
            err = ("destination already contains %d file(s) (e.g. %r); refusing "
                   "without overwrite=True" % (len(collisions), collisions[0]))
            _log(org, "export", {"applet": name, "ok": False, "why": err})
            return {"applet": name, "capsule": CAPSULE, "destination": dest_dir,
                    "dry_run": False, "files_written": [],
                    "hashes_verified": verified, "files_total": len(files),
                    "errors": errors + [err]}
        os.makedirs(dest_real, exist_ok=True)
        for f in files:
            if not f["ok"]:
                continue                          # a tampered file is never written
            target = os.path.realpath(os.path.join(dest_real, f["path"]))
            if not (target == dest_real
                    or target.startswith(dest_real + os.sep)):
                errors.append("path escape refused at write: %r" % f["path"])
                org.immune_event("applet_path_escape", {"applet": name,
                                                        "path": f["path"]})
                continue
            os.makedirs(os.path.dirname(target) or dest_real, exist_ok=True)
            with open(target, "wb") as fh:
                fh.write(f["data"])
            if isinstance(f.get("mode"), int):
                try:
                    os.chmod(target, f["mode"])
                except OSError:
                    pass
            written.append(f["path"])
        _log(org, "export", {"applet": name, "ok": not errors,
                             "files": len(written), "dest": os.path.abspath(dest_dir)})
    return {"applet": name, "capsule": CAPSULE, "destination": dest_dir,
            "dry_run": bool(dry_run), "files_written": written,
            "hashes_verified": verified, "files_total": len(files),
            "errors": errors}


# ----------------------------------------------------------------------------
# the applet audit (deterministic; verifies the CAPSULE, certifies nothing alive)
# ----------------------------------------------------------------------------
def audit_applet_body(org: Any, name: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """The smaller deterministic audit for a nested applet body. Checks the capsule's
    integrity end to end; never executes, imports, or installs stored source. Returns
    (passed, rows). A pass means 'a valid APPLET-BODY-CAPSULE', never 'alive'."""
    rows: List[Dict[str, Any]] = []

    def row(check: str, ok: bool, detail: str) -> None:
        rows.append({"check": check, "ok": bool(ok), "detail": detail,
                     "capsule": CAPSULE})

    manifest = _manifest_of(org, name)
    row("A-01 manifest exists", manifest is not None,
        "manifest present" if manifest else "no %s manifest for %r" % (CAPSULE, name))
    if manifest is None:
        _log(org, "audit", {"applet": name, "ok": False, "fails": ["A-01"]})
        return False, rows

    files, errors = _gather_source(org, name)
    escapes = [e for e in errors if "escape" in e]
    hash_bad = [f for f in files if not f["ok"]]
    if manifest.get("include_source"):
        row("A-02 source chunks hash-valid", not hash_bad and not errors,
            "%d/%d file(s) verified" % (len(files) - len(hash_bad), len(files))
            + ("; " + "; ".join(errors[:2]) if errors else ""))
        bundle_ok = _bundle_hash(
            [{"path": f["path"], "sha256": f["sha256_actual"]} for f in files]
        ) == manifest.get("source_hash")
        row("A-03 bundle hash matches manifest", bundle_ok and not hash_bad,
            "source_hash %s" % ("intact" if bundle_ok else "MISMATCH"))
    else:
        row("A-02 source chunks hash-valid", True, "no source stored (by request)")
        row("A-03 bundle hash matches manifest", True, "no source stored (by request)")
    row("A-04 no stored path escapes the applet root", not escapes,
        "all paths confined" if not escapes else "; ".join(escapes[:2]))

    organs = any((e.get("content") or {}).get("applet") == name
                 for e in _raw_entries(org, ORGANS_BAND)
                 if e.get("opcode") == ORGANS_OPCODE)
    row("A-05 organ map exists", organs, "diagnosis stored" if organs else "missing")

    state = any((e.get("content") or {}).get("applet") == name
                for e in _raw_entries(org, STATE_BAND)
                if e.get("opcode") == STATE_OPCODE)
    row("A-06 state band entry exists", state, "state stored" if state else "missing")

    from . import phenotype as _ph
    face = manifest.get("face") or _face_name(name)
    try:
        opened = _ph.open_face(org, face)          # SELF opens + integrity-verifies it
        row("A-07 phenotype face exists & SELF-openable", True,
            "face %r opens; %d byte(s) of surface" % (face, len(opened["source"])))
    except _ph.PhenotypeError as e:
        row("A-07 phenotype face exists & SELF-openable", False, str(e))

    if manifest.get("include_source"):
        dry = export_applet_source(org, name, "<dry-run>", dry_run=True)
        row("A-08 source export dry-run verifies", not dry["errors"]
            and dry["hashes_verified"] == dry["files_total"],
            "%d/%d hash(es) verified, no write performed"
            % (dry["hashes_verified"], dry["files_total"]))
    else:
        row("A-08 source export dry-run verifies", True, "no source stored (by request)")

    # the audit itself is the proof for A-09: every check above read data through the
    # VCW drivers -- log-json entries only; no exec band, no import, no eval anywhere.
    src_encodings = {org.prime.encoding(b) for b in APPLET_BANDS}
    row("A-09 stored source is inert (never executed)", src_encodings == {"log-json"},
        "applet bands are data bands (%s); the audit executed nothing"
        % ", ".join(sorted(src_encodings)))

    passed = all(r["ok"] for r in rows)
    _log(org, "audit", {"applet": name, "ok": passed,
                        "fails": [r["check"].split()[0] for r in rows if not r["ok"]]})
    return passed, rows


# ----------------------------------------------------------------------------
# wear (through mantle.phenotype -- the host renders; Mantle never executes it)
# ----------------------------------------------------------------------------
def wear_applet_face(org: Any, name: str) -> Dict[str, Any]:
    """Wear an applet's face: returns the phenotype BOOT MANIFEST a host renders."""
    if _manifest_of(org, name) is None:
        raise _refuse(org, "applet_refused", {"name": name, "why": "unknown"},
                      "no applet named %r" % name)
    from . import phenotype as _ph
    boot = _ph.wear(org, _face_name(name))
    _log(org, "wear", {"applet": name, "face": _face_name(name)})
    return boot


# ----------------------------------------------------------------------------
# GitHub ingestion (clone-then-create; tiny, explicit, never executes the clone)
# ----------------------------------------------------------------------------
_GITHUB_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
                        r"(\.git)?/?$")
_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def clone_github(url: str, commit: str, workdir: str, *,
                 allow_network: bool = False) -> Dict[str, Any]:
    """Fetch one exact GitHub commit into a detached, hook-disabled workspace.

    Network access is an explicit operator choice.  Moving refs, abbreviated hashes,
    submodules, and implicit checkout hooks are never used.  Returns acquisition
    provenance including the verified commit and deterministic source-tree hash.
    """
    if not _GITHUB_RE.match(url or ""):
        raise AppletError("only explicit https://github.com/<owner>/<repo> URLs are "
                          "accepted (got %r)" % url)
    if not _COMMIT_RE.match(commit or ""):
        raise AppletError("GitHub acquisition requires an exact 40-hex commit SHA")
    commit = commit.lower()
    if not allow_network:
        raise AppletError("network acquisition refused without --allow-network")
    import subprocess
    os.makedirs(workdir, exist_ok=True)
    dest = os.path.join(workdir, "clone")
    hooks = os.path.join(workdir, "disabled-hooks")
    os.makedirs(hooks, exist_ok=True)

    def git(args: List[str], label: str) -> str:
        proc = subprocess.run(
            ["git", "-c", "core.longpaths=true", "-c", "core.hooksPath=" + hooks]
            + args,
            capture_output=True, text=True, timeout=300,
        )
        if proc.returncode != 0:
            raise AppletError("%s failed: %s"
                              % (label, (proc.stderr or "").strip()[-300:]))
        return (proc.stdout or "").strip()

    git(["init", "--quiet", dest], "git init")
    git(["-C", dest, "remote", "add", "origin", url], "git remote add")
    git(["-C", dest, "-c", "protocol.file.allow=never", "fetch", "--depth", "1",
         "--no-tags", "origin", commit], "git fetch pinned commit")
    git(["-C", dest, "-c", "advice.detachedHead=false", "checkout", "--detach",
         "FETCH_HEAD"], "git detached checkout")
    actual = git(["-C", dest, "rev-parse", "HEAD"], "git verify commit").lower()
    if actual != commit:
        raise AppletError("pinned checkout mismatch: expected %s, got %s"
                          % (commit, actual or "<empty>"))
    files, _skipped = _collect_files(dest)
    return {
        "path": dest,
        "origin": url,
        "commit": actual,
        "tree_hash": _bundle_hash(files),
        "foreign": True,
        "method": "applet-clone-pinned",
        "submodules": "not-fetched",
        "hooks": "disabled",
    }
