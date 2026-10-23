#!/usr/bin/env python3
"""
mantle.organs.reproduction  --  the Reproduction organ: how this creature makes another
                                (Mantle OS · the ninth organ, VCW/Grimoire profile aligned)

The framework grew many propagation verbs -- spore, egg, vault, anchor, symbiosis,
graft -- and `mantle.reproduction` showed they are two methods (SEED and GRAFT) wearing
different clothes. This organ gives those ceremonies a BODY-RESIDENT owner with a real
contract and a real runtime duty, instead of a loose routing module:

  * the two verbs      -- organism.reproduction.seed(...) / .graft(...) route to the
                          same canonical modules as ever (composition, not re-invention);
  * the vault tissue   -- the organism's own sealed seed lives in this organ's band;
                          every hatchery birth auto-vaults its egg (RESURGERE is a
                          birthright, not an option);
  * lineage continuity -- the runtime duty: on every rebirth the sealed seed (and the
                          sealed origin spore, if any) is CARRIED into the new Prime, or
                          its loss becomes an immune event. A body never silently sheds
                          the material it would need to rise again;
  * the band atlas     -- this organ is the keeper of vcw.bands.APP_BAND_ATLAS, the one
                          statement of every framework-reserved app-band range;
  * SPORE-DISTILLATION -- a spore PNG may become the PRIMER and the memories of the body
                          it births, and the spore itself is then sealed under the new
                          body's genesis key as SELF tissue in the `spore_vault` band.
                          THE KEY LAW: key material is MINTED at birth (secrets.token_hex),
                          NEVER derived from the spore -- spores travel publicly, and a
                          key derivable from public bytes would let any holder forge SELF
                          (SELF-1/SELF-3, anti-clone).

The spell-shape law holds here as everywhere: clone -> dissect -> capsule -> audit ->
optional zombie body. A SEED hatch is a BIRTH and faces the Stage-1 gate; an assimilation
(clone/applet) path stays a capsule until the gate itself says otherwise. Nothing in this
organ makes anything "alive" in one gulp.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict, List, Optional

from .contract import Organ, OrganContract
from ..core.redact import redact
from ..primer import appai_commandments, appai_truths
from ..vcw.bands import make_band_boot, APP_BAND_ATLAS
from ..vcw.entry import make_entry

VAULT_BAND = "vault"                 # sealed seed (the germ this body grew from)
SPORE_BAND = "spore_vault"           # sealed origin spore (SPORE-DISTILLATION)
SPORE_OPCODE = "SPORE-SELF"
SPORE_CHUNK_B64 = 900_000            # one chunk per layer, well under LAYER_BYTES

# THE HEIRLOOMS -- the two halves of one inheritance, carried by one rule on every
# rebirth: the germ in `vault` is what you rebuild from; the spore in `spore_vault`
# is where you came from. Both are SELF-sealed ciphertext, carried verbatim.
HEIRLOOM_BANDS = {VAULT_BAND: "VAULT", SPORE_BAND: SPORE_OPCODE}
SOURCE_DESCRIPTOR_KEYS = {
    "kind", "url", "path", "ref", "branch", "tag", "commit", "sha256",
    "source_sha256", "instructions", "retrieval", "notes",
}
SOURCE_RECEIPT_KEYS = SOURCE_DESCRIPTOR_KEYS | {
    "fetched", "retrieved", "assimilated", "certified", "sealed",
    "body", "body_sha256", "assimilated_path", "certification", "stage",
}
HASH_KEYS = {"sha256", "source_sha256", "body_sha256"}

CONTRACT = OrganContract(
    "reproduction", "seed & graft ceremonies, seed-vault tissue, lineage continuity",
    reads=[VAULT_BAND, SPORE_BAND],
    writes=[VAULT_BAND, SPORE_BAND],
    reflexes=[
        {"name": "vault-store", "trigger": "hatch / store_seed",
         "effect": "the organism's own seed sealed under the genesis key (SELF only)"},
        {"name": "seed-carry", "trigger": "rebirth",
         "effect": "sealed seed + sealed origin spore carried into the new Prime; "
                   "an uncarriable seed becomes an immune event, never a silent loss"},
        {"name": "spore-distill", "trigger": "hatchery.hatch_from_spore",
         "effect": "spore -> primer + ingested memories; spore sealed as SELF tissue; "
                   "key MINTED, never derived from the spore"},
    ],
    phase1="active",
    phase2_extension="the MIND may PROPOSE a seed or graft; the Body performs the ceremony",
    audit=[
        "every hatched organism carries its own seed in the vault",
        "the sealed seed survives rebirth or its loss is immune-logged",
        "key material is minted, never derived from any spore (anti-clone)",
        "reserved app-band ranges never overlap (the atlas + the genesis gate)",
    ],
)


# ---------------------------------------------------------------------------
# The seed vault (self-reconstruction; formerly mantle.vault -- one seam, ONE door)
# ---------------------------------------------------------------------------

class VaultError(Exception):
    """The vault could not be opened or the seed was unusable (e.g. opened as OTHER)."""


def vault_band(head: int = 638, span: int = 2) -> Dict[str, Any]:
    """The reserved, PRIVATE (veiled) band that holds the SELF-encrypted seed."""
    return make_band_boot(VAULT_BAND, head, "log-json", span=span, private=True,
                          purpose="the SELF-encrypted seed vault (self-reconstruction)")


def store_seed(org: Any, seed: Dict[str, Any]) -> Dict[str, Any]:
    """Seal the organism's own seed (its germ) under the genesis key and append it to
    the veiled vault band, self-describing (part/of) like every heirloom. Only this
    body can ever open it."""
    ciphertext = org.body.seal_bytes(json.dumps(seed, sort_keys=True,
                                                default=str).encode("utf-8"))
    return org.prime.append(VAULT_BAND, make_entry(
        {"seed": ciphertext.hex(), "part": 0, "of": 1},
        opcode="VAULT", author="BODY", source="seed-vault"))


def open_seed(org: Any) -> Dict[str, Any]:
    """Open the latest sealed seed with THIS body's key (SELF only). Raises VaultError if
    there is no seed or it cannot be decrypted as this body's own."""
    entries = org.prime.read(VAULT_BAND, reveal_private=True)
    sealed = [e for e in entries if e.get("opcode") == "VAULT"]
    if not sealed:
        raise VaultError("the vault is empty")
    try:
        plaintext = org.body.open_bytes(bytes.fromhex(sealed[-1]["content"]["seed"]))
        return json.loads(plaintext)
    except (ValueError, json.JSONDecodeError) as e:
        raise VaultError("cannot open the vault: not this body's SELF (%s)" % type(e).__name__)


def reconstruct(seed: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild a working body from a seed germ -- through the SAME hatchery gate every
    body faces. A tampered seed that cannot certify does not reconstruct. Returns
    {organism, report}."""
    from ..hatchery import incubate
    return incubate(seed)


def spore_vault_band(head: int = None, span: int = None) -> Dict[str, Any]:
    """The reserved, PRIVATE band holding the SELF-sealed origin spore, chunked one
    ciphertext chunk per layer (the phenotype chunking pattern)."""
    h, s = APP_BAND_ATLAS[SPORE_BAND]
    return make_band_boot(SPORE_BAND, head or h, "log-json", span=span or s,
                          private=True, params={"max_entries_per_layer": 1},
                          purpose="the SELF-sealed origin spore (SPORE-DISTILLATION)")


def distill_germ(state: Dict[str, Any]) -> Dict[str, Any]:
    """Distill a bare spore's STATE (identity + task) into a minimal germ: the spore
    becomes the PRIMER of the body it births. Pure data transformation -- no key
    material is ever read from, or written into, the spore state. (A germ-carrying
    spore skips this: its germ IS the build document.)"""
    ident = dict(state.get("identity") or {})
    name = ident.get("spore_name") or "Spore.AppAI"
    task = ident.get("task") or ""
    truths = appai_truths()
    if task:
        truths.append("my task: %s" % task)
    return {
        "schema": "mantle-germ-v2",
        "identity": {"name": name, "purpose": task or "hatched from a spore",
                     "born_of": "spore-png"},
        "truths": truths,
        "commandments": appai_commandments(["Keep the seed dry."]),
        "genome": [{"band": SPORE_BAND, "head": APP_BAND_ATLAS[SPORE_BAND][0],
                    "span": APP_BAND_ATLAS[SPORE_BAND][1], "encoding": "log-json",
                    "private": True, "params": {"max_entries_per_layer": 1},
                    "purpose": "the SELF-sealed origin spore (SPORE-DISTILLATION)"}],
    }


def _safe_source_value(key: str, value: Any) -> Any:
    """Keep source receipts useful without letting secrets or raw payloads become memory."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        text = value[:512]
        if key in HASH_KEYS and text.startswith("sha256:"):
            return text
        return redact(text)
    if isinstance(value, (list, tuple)):
        return [_safe_source_value(key, v) for v in list(value)[:20]]
    if isinstance(value, dict):
        return {str(k)[:64]: _safe_source_value(str(k), v)
                for k, v in value.items()
                if str(k) in SOURCE_RECEIPT_KEYS}
    return redact(str(value)[:512])


def _safe_source_payload(payload: Any, allowed: set) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {str(k): _safe_source_value(str(k), v)
            for k, v in payload.items()
            if str(k) in allowed}


def _flag(payload: Dict[str, Any], *names: str) -> bool:
    return any(bool(payload.get(n)) for n in names)


def sporeagent_source_receipt(state: Dict[str, Any],
                              source_receipt: Optional[Dict[str, Any]] = None
                              ) -> Dict[str, Any]:
    """Normalize the optional SPOREAGENT source receipt.

    The pure SPORE substrate does not fetch, assimilate, certify, or own host code.
    Those acts are operator/agent lifecycle tissue. This receipt only records safe
    provenance and boundary facts so the Body can audit the SPORE-to-PRIMER transition.
    """
    descriptor = _safe_source_payload(
        state.get("source") or state.get("source_retrieval") or {},
        SOURCE_DESCRIPTOR_KEYS,
    )
    receipt = _safe_source_payload(source_receipt or {}, SOURCE_RECEIPT_KEYS)
    fetched = _flag(receipt, "fetched", "retrieved")
    assimilated = _flag(receipt, "assimilated")
    certified = _flag(receipt, "certified")
    sealed = _flag(receipt, "sealed")
    return {
        "declared": bool(descriptor),
        "descriptor": descriptor,
        "receipt": receipt,
        "fetched": fetched,
        "assimilated": assimilated,
        "certified": certified,
        "sealed": sealed,
        "body_status": "certified_zombie_body" if certified else "not_certified_here",
        "source_self_status": "OTHER_until_PRIMER_seal_provenance_and_certification",
        "host_code_is_self": False,
        "key_owner": "BODY",
        "mind_key_access": False,
        "key_material_in_receipt": False,
    }


class Reproduction(Organ):
    """The ninth organ. Owns the reproduction verbs, the vault/spore tissue, the band
    atlas, and the lineage-continuity duty (seed-carry on rebirth)."""

    contract = CONTRACT

    # ---- the two verbs (delegation to the canonical seam) --------------------
    def describe(self) -> Dict[str, Any]:
        from .. import reproduction as _r
        return _r.describe()

    def seed(self, form: str = "spore", **kwargs) -> Dict[str, Any]:
        from .. import reproduction as _r
        return _r.seed(form, **kwargs)

    def graft(self, form: str = "anchor", **kwargs) -> Dict[str, Any]:
        from .. import reproduction as _r
        return _r.graft(form, **kwargs)

    # ---- the vault tissue (contract-checked writes) --------------------------
    def store_seed(self, seed: Dict[str, Any]) -> Dict[str, Any]:
        """Seal the organism's own seed under the genesis key into the vault band,
        self-describing (part/of) like every heirloom."""
        ciphertext = self.org.body.seal_bytes(
            json.dumps(seed, sort_keys=True, default=str).encode("utf-8"))
        return self.append(VAULT_BAND, make_entry(
            {"seed": ciphertext.hex(), "part": 0, "of": 1}, opcode="VAULT",
            author="BODY", source="reproduction-organ"))

    def open_seed(self) -> Dict[str, Any]:
        return open_seed(self.org)

    # ---- the sealed origin spore ---------------------------------------------
    def store_spore(self, blob: bytes, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Seal raw spore bytes under THIS body's genesis key and append them chunked
        into the veiled spore_vault band. The plaintext spore is OTHER wherever else it
        exists; only this sealed copy is SELF."""
        if SPORE_BAND not in self.org.prime.bands:
            raise PermissionError("this organism has no %r band (hatch through "
                                  "the hatchery's spore path, or add "
                                  "spore_vault_band())" % SPORE_BAND)
        sha = "sha256:" + hashlib.sha256(blob).hexdigest()
        ciphertext = self.org.body.seal_bytes(blob)
        b64 = base64.b64encode(ciphertext).decode("ascii")
        parts = [b64[i:i + SPORE_CHUNK_B64]
                 for i in range(0, len(b64), SPORE_CHUNK_B64)] or [""]
        for i, chunk in enumerate(parts):
            self.append(SPORE_BAND, make_entry(
                dict(meta, part=i, of=len(parts), b64=chunk, sha256=sha),
                opcode=SPORE_OPCODE, author="BODY", source="spore-distillation"))
        return {"sha256": sha, "chunks": len(parts), "band": SPORE_BAND}

    def open_spore(self) -> bytes:
        """Reassemble + decrypt the sealed origin spore (SELF only). The PRIME may use
        this to reference tools or data the spore carries. Raises on OTHER/tamper."""
        chunks = [e.get("content") or {} for e in self._physical(SPORE_BAND)
                  if e.get("opcode") == SPORE_OPCODE]
        if not chunks:
            raise ValueError("no sealed spore in %r" % SPORE_BAND)
        latest_of = int(chunks[-1].get("of", 1))
        parts = sorted(chunks[-latest_of:], key=lambda c: c.get("part", 0))
        ciphertext = base64.b64decode("".join(c.get("b64", "") for c in parts))
        blob = self.org.body.open_bytes(ciphertext)
        sha = "sha256:" + hashlib.sha256(blob).hexdigest()
        if sha != parts[0].get("sha256"):
            raise ValueError("sealed spore failed its integrity check")
        return blob

    # ---- the runtime duty: lineage continuity across rebirth ------------------
    def on_rebirth(self, payload: Dict[str, Any]) -> None:
        """THE HEIRLOOM LAW: carried or immune-logged, never silent. On every rebirth
        the heirlooms (the sealed germ in `vault`, the sealed origin spore in
        `spore_vault`) are carried from the newest ancestor into the new Prime by ONE
        rule -- the last complete heirloom per band, verbatim ciphertext. The genesis
        key persists across rebirth, so the carried copy still opens as SELF. If the
        new genome cannot hold a heirloom, that is an immune event, never a loss (the
        sealed ancestor stays readable)."""
        anc = self.org.ancestral[-1] if self.org.ancestral else None
        if anc is None:
            return
        for band, opcode in HEIRLOOM_BANDS.items():
            if band not in anc.bands:
                continue
            sealed = [e for e in self._physical(band, cube=anc)
                      if e.get("opcode") == opcode]
            if not sealed:
                continue
            if band not in self.org.prime.bands:
                self.org.immune_event("seed_uncarried", {
                    "band": band, "entries": len(sealed),
                    "note": "rebirth genome holds no %r band; the sealed material "
                            "remains readable in the sealed ancestor" % band})
                continue
            # one rule for every heirloom: entries are self-describing (part/of;
            # of defaults to 1 for legacy single-entry seeds)
            carry = sealed[-int((sealed[-1].get("content") or {}).get("of", 1)):]
            for e in carry:
                self.append(band, make_entry(dict(e.get("content") or {}),
                                             opcode=opcode, author="BODY",
                                             source="seed-carry"))

    # ---- helpers ---------------------------------------------------------------
    def _physical(self, band: str, cube: Any = None) -> List[Dict[str, Any]]:
        """Every entry physically in a (possibly veiled) band, in stream order."""
        c = cube or self.org.prime
        out: List[Dict[str, Any]] = []
        for idx in c.band_layers.get(band, []):
            out.extend(c.layer_content(idx))
        return out

    def atlas(self) -> Dict[str, Any]:
        """The app-band atlas this organ keeps (vcw.bands.APP_BAND_ATLAS)."""
        return dict(APP_BAND_ATLAS)
