#!/usr/bin/env python3
"""
mantle.core.body  --  the BODY store (Mantle OS)

The Primer lives in the BODY, not in the VCW cube. The cube is pure experiential memory
(read/append-only). The Body holds the agent's *defining* data and provides the small
MUTABLE surface the append-only VCW cannot:

    Primer               read-only     -- who you are: identity + TRUTHS + COMMANDMENTS
    Special Instructions read/write    -- steering; the MIND GUIDES, the BODY APPLIES
    Immunization         read/write    -- safety rules (a VCW immune layer is the working copy)

The API boot order sent to a model is:  Primer + Special Instructions + Immunization.
The Body is also addressable like a layer:  <body.immune.11>  ->  the 11th immunization entry.

The Body holds the durable SELF RECORD -- Primer + commandments + the LINEAGE INDEX (which
cube generation is Prime, where the sealed ancestors live, and each ancestor's seal
fingerprint). That record, not any cube, is the continuity of the organism across rebirths.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any, Dict, List, Optional


def _entry(content: Any, author: str = "BODY") -> Dict[str, Any]:
    return {"ts": time.time(), "author": author, "content": content}


def _fingerprint(key: str) -> str:
    """The PUBLIC id of a genesis key: sha256 of the key, 16 hex chars. Safe to show,
    safe to persist in the clear -- it cannot be reversed into the key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class Body:
    CATEGORIES = ("primer", "special", "immunization")

    def __init__(self) -> None:
        self._primer: List[Dict[str, Any]] = []
        self._special: List[Dict[str, Any]] = []
        self._immunization: List[Dict[str, Any]] = []
        self._primer_sealed = False
        # the genesis key -- the cryptographic SELF (M2). Generated ONCE at birth, sealed
        # into the Body, NEVER in any cube, NEVER in boot_order/self_record (so the MIND
        # cannot leak what it does not know). It is the organism's immune identity: files
        # it can sign/verify are SELF; everything else is OTHER.
        self._genesis_key: Optional[str] = None
        self._key_fingerprint: Optional[str] = None
        # lineage index: generation -> {"role": "prime"|"ancestral", "location": str,
        #                               "seal_fingerprint": str|None}
        self.lineage_index: Dict[int, Dict[str, Any]] = {}
        self.prime_generation: int = 0
        self._edition_adoptions: List[Dict[str, Any]] = []

    # ---- birth: set the Primer once, immutably -----------------------------
    def birth(self, identity: Dict[str, Any], truths: List[str],
              commandments: List[str]) -> None:
        if self._primer_sealed:
            raise PermissionError("Primer is immutable post-birth")
        self._primer = [_entry({"identity": identity}),
                        _entry({"truths": truths}),
                        _entry({"commandments": commandments})]
        self._primer_sealed = True
        # the Commandments seed the Immunization working copy (doctrine -> immune)
        for c in commandments:
            self._immunization.append(_entry(c, author="BODY"))
        # mint the genesis key ONCE, at the moment the self comes online
        self._mint_genesis_key()

    @property
    def primer_sealed(self) -> bool:
        return self._primer_sealed

    # ---- the genesis key: the cryptographic SELF (M2) ----------------------
    def _mint_genesis_key(self) -> None:
        """Generate the one-time genesis key. Refused if one already exists -- the SELF
        is minted once and never re-minted (mirrors the sealed Primer)."""
        if self._genesis_key is not None:
            raise PermissionError("the genesis key is minted once; it cannot be re-minted")
        self._genesis_key = secrets.token_hex(32)
        self._key_fingerprint = _fingerprint(self._genesis_key)

    @property
    def key_fingerprint(self) -> Optional[str]:
        """The PUBLIC id of this Body's SELF. Safe to show; cannot reveal the key."""
        return self._key_fingerprint

    @property
    def has_key(self) -> bool:
        return self._genesis_key is not None

    def sign(self, data: bytes) -> str:
        """HMAC-SHA256 over `data` with the genesis key. Only this Body can produce it;
        any other body produces a different mac -> the basis of SELF/OTHER recognition."""
        if self._genesis_key is None:
            raise PermissionError("no genesis key: this Body has no SELF to sign with")
        return hmac.new(self._genesis_key.encode("utf-8"), data, hashlib.sha256).hexdigest()

    def verify(self, data: bytes, mac: str) -> bool:
        """True iff `mac` is THIS Body's signature over `data` (constant-time compare).
        A mac from another body, or a forged mac, is OTHER -> False."""
        if self._genesis_key is None or not isinstance(mac, str):
            return False
        return hmac.compare_digest(self.sign(data), mac)

    # ---- SELF-encryption: the seed vault depends on this (M8) ---------------
    def _keystream(self, n: int) -> bytes:
        """A deterministic keystream derived from the genesis key (sha256 in counter mode).
        Only this Body can reproduce it -- so only SELF can open what SELF sealed."""
        out = bytearray()
        counter = 0
        seed = self._genesis_key.encode("utf-8")
        while len(out) < n:
            out += hashlib.sha256(seed + counter.to_bytes(8, "big")).digest()
            counter += 1
        return bytes(out[:n])

    def seal_bytes(self, data: bytes) -> bytes:
        """Encrypt `data` under the genesis key (XOR stream cipher). The ciphertext is
        opaque to any other body: SELF can open it, OTHER cannot. The key never leaves the
        Body -- so it can never reach the MIND or a cube."""
        if self._genesis_key is None:
            raise PermissionError("no genesis key: this Body has no SELF to seal with")
        ks = self._keystream(len(data))
        return bytes(a ^ b for a, b in zip(data, ks))

    def open_bytes(self, ciphertext: bytes) -> bytes:
        """Decrypt what THIS Body sealed (the cipher is symmetric). Another body's key
        produces garbage -- the vault is unreadable as OTHER."""
        return self.seal_bytes(ciphertext)

    # ---- Special Instructions: MIND guides, BODY applies -------------------
    def mind_propose_special(self, text: str) -> Dict[str, Any]:
        """The MIND may only PROPOSE a change. Returns an intent; it is not written."""
        return {"intent": "special_instruction", "text": text, "author": "MIND"}

    def apply_special(self, text: str, source: str = "MIND") -> Dict[str, Any]:
        """Only the BODY writes. (Driven by a dispatch reflex in a full system.)"""
        e = _entry(text, author="BODY")
        e["guided_by"] = source
        self._special.append(e)
        return e

    # ---- Immunization (read/write) ----------------------------------------
    def add_immunization(self, rule: str) -> Dict[str, Any]:
        e = _entry(rule, author="BODY")
        self._immunization.append(e)
        return e

    # ---- addressing: the Body as a referenceable layer --------------------
    def category(self, name: str) -> List[Dict[str, Any]]:
        return {"primer": self._primer, "special": self._special,
                "immune": self._immunization, "immunization": self._immunization}[name]

    def get(self, category: str, index: int) -> Optional[Dict[str, Any]]:
        items = self.category(category)
        return items[index] if 0 <= index < len(items) else None

    # ---- the boot order assembled for the model ---------------------------
    def boot_order(self) -> Dict[str, Any]:
        return {
            "primer": [e["content"] for e in self._primer],
            "special_instructions": [e["content"] for e in self._special],
            "immunization": [e["content"] for e in self._immunization],
        }

    def boot_text(self) -> str:
        bo = self.boot_order()
        lines = ["=== PRIMER ==="]
        for p in bo["primer"]:
            lines.append("  " + str(p))
        lines.append("=== SPECIAL INSTRUCTIONS ===")
        lines += ["  " + str(s) for s in bo["special_instructions"]] or ["  (none)"]
        lines.append("=== IMMUNIZATION ===")
        lines += ["  " + str(i) for i in bo["immunization"]]
        return "\n".join(lines)

    # ---- the durable self record (continuity across generations) ----------
    def self_record(self) -> Dict[str, Any]:
        return {
            "primer": [e["content"] for e in self._primer],
            "prime_generation": self.prime_generation,
            "lineage_index": self.lineage_index,
            "edition_adoptions": list(self._edition_adoptions),
        }

    def record_edition_adoption(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        """Append an operator-authorized edition receipt to Body-owned tissue."""
        if not isinstance(receipt, dict) or receipt.get("operator_authorized") is not True:
            raise PermissionError("edition adoption requires operator authorization")
        if receipt.get("kind") not in ("grimoire_edition_adoption",
                                       "semantic_memory_adoption"):
            raise ValueError("unsupported edition receipt kind")
        self._edition_adoptions.append(dict(receipt))
        return self._edition_adoptions[-1]

    def identity_name(self) -> str:
        for e in self._primer:
            ident = e["content"].get("identity") if isinstance(e["content"], dict) else None
            if ident and "name" in ident:
                return ident["name"]
        return "unnamed AppAI"

    # ---- persistence ------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        # the genesis key persists with the Body (continuity of SELF across reloads). It
        # lives in body.json, NEVER in a cube, and NEVER in boot_order/self_record above --
        # so the MIND's snapshot can never carry it.
        return {"primer": self._primer, "special": self._special,
                "immunization": self._immunization, "primer_sealed": self._primer_sealed,
                "genesis_key": self._genesis_key, "key_fingerprint": self._key_fingerprint,
                "lineage_index": {str(k): v for k, v in self.lineage_index.items()},
                "prime_generation": self.prime_generation,
                "edition_adoptions": list(self._edition_adoptions)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Body":
        b = cls()
        b._primer = d.get("primer", [])
        b._special = d.get("special", [])
        b._immunization = d.get("immunization", [])
        b._primer_sealed = d.get("primer_sealed", bool(b._primer))
        b._genesis_key = d.get("genesis_key")
        # recompute the fingerprint from the loaded key; a key whose recorded fingerprint
        # disagrees is a tampered/replaced SELF -> caught loudly at the Organism load gate.
        b._key_fingerprint = d.get("key_fingerprint")
        b.lineage_index = {int(k): v for k, v in d.get("lineage_index", {}).items()}
        b.prime_generation = d.get("prime_generation", 0)
        b._edition_adoptions = list(d.get("edition_adoptions", []))
        return b

    def key_fingerprint_consistent(self) -> bool:
        """True iff the loaded key still hashes to its recorded fingerprint. A False here
        means the SELF was tampered with or orphaned -- the Organism raises on it (M2)."""
        if self._genesis_key is None:
            return self._key_fingerprint is None
        return _fingerprint(self._genesis_key) == self._key_fingerprint
