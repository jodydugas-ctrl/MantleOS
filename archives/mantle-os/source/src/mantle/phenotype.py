#!/usr/bin/env python3
"""
mantle.phenotype  --  wearable app-faces stored inside the VCW (Mantle OS · M9)

One stable organism (Body + append-only cube + nine organs) can express MANY front-facing
surfaces -- a spreadsheet, a CLI, a phone shell, a chat face -- while the nervous system and
the VCW underneath never change. A PHENOTYPE (a "face") is a whole front-end, sealed under the
genesis key into a private VCW band. The Compiler does not run apps; it WEARS them.

Three laws hold it safe -- the same laws as the seed vault (the Reproduction organ), one band richer:
  * a face is SELF-encrypted (M2): the source is sealed under the genesis key, so it is
    unreadable -- and un-wearable -- as OTHER. A copied nest in a different body gets garbage.
  * a face is SOURCE, never executed here: wearing returns a boot manifest a HOST renders.
    The organism never exec's a front-end's source -- that is exactly what the sandbox forbids.
  * wearing is append-only: the active face is the LATEST wear-event, never an overwrite. Every
    face-save and every change of face is an accreted, immutable, hashed event -- the fossil
    record the doctrine promises ("if it is not in the VCW it did not happen").

THE DEFAULT FACE.  Every hatched organism carries, from its first breath, an encrypted copy of
its ORIGIN surface -- the app it was created from -- as the `default` face. Even if no other
face is ever added, the organism always holds a sealed copy of its own source in the VCW: a
self-reconstruction / security guarantee, the sibling of the seed vault.

THE SOCKET.  A face declares the `controls` it expresses. It is wearable only if every declared
control already has a socket in the organism's Human Surface Map (mantle.organs.senses) -- the
"same nervous system to plug into" the body plan requires. A face that reaches for a control the
body cannot drive is refused.

    python -m mantle face-save <dir> <name> <source-file> [--kind=html] [--default]
    python -m mantle face-list <dir>
    python -m mantle face-wear <dir> <name>
"""
from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from .vcw.bands import make_band_boot, code_hash
from .vcw.entry import make_entry

# the private bands: big sealed source blobs, and a tiny append-only wear-log
PHENO_BAND = "phenotypes"
WEAR_BAND = "phenotype_log"
EXPRESS_OPCODE = "PHENOTYPE"
WEAR_OPCODE = "WEAR"

# one ciphertext chunk per layer: kept well under LAYER_BYTES (2,560,000) once base64-expanded
# (x4/3) and wrapped in JSON. A face larger than one chunk spans several PHENOTYPE entries.
CHUNK_BYTES = 1_200_000


class PhenotypeError(Exception):
    """A face could not be saved, opened, or worn -- a duplicate/second-default, an OTHER-sealed
    or tampered face, foreign provenance, or a control with no socket to plug into."""


@dataclass(frozen=True)
class FaceAttestation:
    schema_version: str
    appai_identity: str
    public_self_fingerprint: str
    face_name: str
    face_source_hash: str
    face_provenance: Dict[str, Any]
    declared_capabilities: Dict[str, Any]
    verified_socket_capabilities: List[str]
    wear_event_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ----------------------------------------------------------------------------
# the reserved bands (app range 550-749, both veiled like the vault)
# ----------------------------------------------------------------------------
def phenotype_bands(head: int = 640, span: int = 16,
                    log_head: int = 660, log_span: int = 2) -> List[Dict[str, Any]]:
    """The two reserved, PRIVATE bands. `phenotypes` holds the SELF-encrypted source (one
    ciphertext chunk per layer); `phenotype_log` holds the tiny append-only wear-events."""
    return [
        make_band_boot(PHENO_BAND, head, "log-json", span=span, private=True,
                       params={"max_entries_per_layer": 1},
                       purpose="SELF-encrypted front-end faces (the worn body plans)"),
        make_band_boot(WEAR_BAND, log_head, "log-json", span=log_span, private=True,
                       purpose="append-only wear-log: which face is expressed now"),
    ]


def has_phenotype_bands(org: Any) -> bool:
    return PHENO_BAND in org.prime.bands and WEAR_BAND in org.prime.bands


# ----------------------------------------------------------------------------
# express: seal a face into the VCW
# ----------------------------------------------------------------------------
def _raw_entries(org: Any, band: str) -> List[Dict[str, Any]]:
    """Every entry physically in a private band, in stream order (no veil, no overlay)."""
    out: List[Dict[str, Any]] = []
    for idx in org.prime.band_layers.get(band, []):
        out.extend(org.prime.layer_content(idx))
    return out


def _face_names(org: Any) -> List[str]:
    seen, names = set(), []
    for e in _raw_entries(org, PHENO_BAND):
        if e.get("opcode") == EXPRESS_OPCODE:
            n = (e.get("content") or {}).get("name")
            if n is not None and n not in seen:
                seen.add(n); names.append(n)
    return names


def _default_name(org: Any) -> Optional[str]:
    for e in _raw_entries(org, PHENO_BAND):
        c = e.get("content") or {}
        if e.get("opcode") == EXPRESS_OPCODE and c.get("default"):
            return c.get("name")
    return None


def express(org: Any, name: str, kind: str, source: str, *, entry: str = "",
            controls: Optional[List[Dict[str, Any]]] = None,
            capabilities: Optional[Dict[str, Any]] = None, default: bool = False,
            provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Seal a whole front-end as a face. The manifest (source + how to mount it + the socket it
    needs + what it may touch) is sealed under the genesis key and appended -- chunked across
    layers if large. Refuses a duplicate name, a second default, or foreign provenance."""
    if not has_phenotype_bands(org):
        raise PhenotypeError("this organism has no phenotype bands (call phenotype_bands() "
                             "into its genome at birth)")
    if name in _face_names(org):
        raise PhenotypeError("a face named %r already exists (faces are append-only; save "
                             "under a new name)" % name)
    if default and _default_name(org) is not None:
        raise PhenotypeError("a default face already exists (%r); there is exactly one origin"
                             % _default_name(org))
    prov = dict(provenance or {"author": "BODY"})
    prov.setdefault("born_gen", org.prime.generation)
    prov.setdefault("foreign", False)
    if prov.get("foreign") or prov.get("author") not in ("BODY", "MIND"):
        raise PhenotypeError("a face must be SELF-authored to be sealed under SELF "
                             "(author=%r foreign=%r)" % (prov.get("author"), prov.get("foreign")))

    manifest = {"name": name, "kind": kind, "default": bool(default), "source": source,
                "source_hash": code_hash(source), "entry": entry,
                "controls": list(controls or []), "capabilities": dict(capabilities or {}),
                "provenance": prov}
    ciphertext = org.body.seal_bytes(
        json.dumps(manifest, sort_keys=True).encode("utf-8"))
    chunks = [ciphertext[i:i + CHUNK_BYTES] for i in range(0, len(ciphertext), CHUNK_BYTES)] \
        or [b""]
    of = len(chunks)
    for part, chunk in enumerate(chunks):
        org.prime.append(PHENO_BAND, make_entry(
            {"name": name, "default": bool(default), "part": part, "of": of,
             "b64": base64.b64encode(chunk).decode("ascii")},
            opcode=EXPRESS_OPCODE, author="BODY", source="phenotype"))
    return {"name": name, "default": bool(default), "parts": of,
            "source_hash": manifest["source_hash"]}


# ----------------------------------------------------------------------------
# list / open
# ----------------------------------------------------------------------------
def list_faces(org: Any) -> List[Dict[str, Any]]:
    """The cheap catalog: face names, which is default, how many chunks, and which is worn --
    WITHOUT decrypting any source (only SELF can read the source, and listing should not need
    the key)."""
    if not has_phenotype_bands(org):
        return []
    by_name: Dict[str, Dict[str, Any]] = {}
    for e in _raw_entries(org, PHENO_BAND):
        if e.get("opcode") != EXPRESS_OPCODE:
            continue
        c = e.get("content") or {}
        rec = by_name.setdefault(c["name"], {"name": c["name"], "default": bool(c.get("default")),
                                             "parts": int(c.get("of", 1))})
        rec["default"] = rec["default"] or bool(c.get("default"))
    worn = active_face(org)
    out = list(by_name.values())
    for rec in out:
        rec["worn"] = (rec["name"] == worn)
    return out


def open_face(org: Any, name: str) -> Dict[str, Any]:
    """Reassemble + decrypt a face with THIS body's key (SELF only). Verifies the source still
    hashes to its sealed source_hash. Raises PhenotypeError on OTHER, tamper, or unknown name."""
    parts = sorted((e.get("content") or {} for e in _raw_entries(org, PHENO_BAND)
                    if e.get("opcode") == EXPRESS_OPCODE and (e.get("content") or {}).get("name") == name),
                   key=lambda c: c.get("part", 0))
    if not parts:
        raise PhenotypeError("no face named %r" % name)
    ciphertext = b"".join(base64.b64decode(c["b64"]) for c in parts)
    try:
        manifest = json.loads(org.body.open_bytes(ciphertext))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise PhenotypeError("cannot open face %r: not this body's SELF (sealed as OTHER, or "
                             "tampered)" % name)
    if not isinstance(manifest, dict) or code_hash(manifest.get("source", "")) != manifest.get("source_hash"):
        raise PhenotypeError("face %r failed its integrity check (source != source_hash)" % name)
    return manifest


# ----------------------------------------------------------------------------
# wear / shed: change the expressed face (append-only)
# ----------------------------------------------------------------------------
def _socket(org: Any) -> set:
    """The organism's Human Surface Map -- the controls its nervous system can actually drive."""
    return set(getattr(org.senses, "surface_map", {}) or {})


def wear(org: Any, name: str, strict_socket: bool = True) -> Dict[str, Any]:
    """Express a face: open it (SELF + integrity), confirm every declared control has a socket
    to plug into (the Body ABI), record an append-only WEAR event, and return the BOOT MANIFEST
    a host renders. The source is never executed here."""
    manifest = open_face(org, name)
    if strict_socket:
        socket = _socket(org)
        missing = [c.get("id") for c in manifest.get("controls", []) if c.get("id") not in socket]
        if missing:
            raise PhenotypeError("face %r declares control(s) %s with no socket in this nervous "
                                 "system -- a face may only plug into controls the body can drive"
                                 % (name, missing))
    wear_event = org.prime.append(
        WEAR_BAND,
        make_entry({"wear": name}, opcode=WEAR_OPCODE,
                   author="BODY", source="phenotype"),
    )
    verified_sockets = sorted(
        str(control.get("id")) for control in manifest.get("controls", [])
        if control.get("id") in _socket(org)
    )
    attestation = FaceAttestation(
        "mantle-face-attestation-v1",
        str(org.body.identity_name()),
        str(org.body.key_fingerprint),
        name,
        str(manifest["source_hash"]),
        dict(manifest.get("provenance") or {}),
        dict(manifest.get("capabilities") or {}),
        verified_sockets,
        str(wear_event.get("hash") or wear_event.get("id") or "unavailable"),
    )
    return {"name": name, "kind": manifest["kind"], "entry": manifest["entry"],
            "source": manifest["source"], "controls": manifest["controls"],
            "capabilities": manifest["capabilities"],
            "face_attestation": attestation.to_dict()}


def active_face(org: Any) -> Optional[str]:
    """The face expressed right now: the latest WEAR event, else the default (origin) face."""
    if not has_phenotype_bands(org):
        return None
    for e in reversed(_raw_entries(org, WEAR_BAND)):
        if e.get("opcode") == WEAR_OPCODE:
            return (e.get("content") or {}).get("wear")
    return _default_name(org)


def shed(org: Any) -> Dict[str, Any]:
    """Revert to the default (origin) face -- itself an append-only wear-event."""
    d = _default_name(org)
    if d is None:
        raise PhenotypeError("no default face to shed back to")
    return wear(org, d)


# ----------------------------------------------------------------------------
# rebirth survival: faces persist across a chosen reformat (the key persists too)
# ----------------------------------------------------------------------------
def snapshot(org: Any) -> List[Dict[str, Any]]:
    """The raw sealed PHENOTYPE entries of the current Prime -- carried forward verbatim across
    a rebirth. The ciphertext stays sealed under the same (persistent) genesis key."""
    return [dict(e.get("content") or {}) for e in _raw_entries(org, PHENO_BAND)
            if e.get("opcode") == EXPRESS_OPCODE]


def restore(org: Any, snap: List[Dict[str, Any]]) -> int:
    """Re-append carried face chunks into the new Prime's phenotype band (sealed, unchanged --
    still openable, because the genesis key survives rebirth)."""
    if not has_phenotype_bands(org):
        raise PhenotypeError("the reborn genome has no phenotype bands to restore into")
    for c in snap:
        org.prime.append(PHENO_BAND, make_entry(dict(c), opcode=EXPRESS_OPCODE,
                                                author="BODY", source="phenotype-carry"))
    return len(snap)


def rebirth_with_faces(org: Any, new_genome: Optional[List[Dict[str, Any]]] = None,
                       reason: str = "reformat") -> Any:
    """Rebirth that preserves the worn faces -- especially the always-present default. Snapshots
    the sealed faces, rebirths (ensuring the reborn genome carries the phenotype bands), and
    restores them. The old generation's faces also remain readable in the sealed ancestor."""
    from .vcw.bands import standard_genome
    snap = snapshot(org)
    genome = list(new_genome) if new_genome is not None else standard_genome()
    if not any(b.get("band") == PHENO_BAND for b in genome):
        genome = genome + phenotype_bands()
    org.rebirth(new_genome=genome, reason=reason)
    restore(org, snap)
    return org
