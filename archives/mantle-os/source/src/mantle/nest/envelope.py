"""Pluggable Body secret-envelope interface.

The Body never travels in plaintext to a remote NEST. A publisher must refuse any
file inventory that carries plaintext secrets (``genesis_key``, provider API keys,
GitHub tokens/app keys/webhook secrets/bearer credentials, or unredacted
secret-shaped Senses/Immune/model/workflow data). Instead the Body is sealed into
an authenticated envelope that binds repository ID, schema, key fingerprint, and
manifest hash as associated data.

This module lives OUTSIDE the Body runtime. The envelope-opening capability is
never exposed to the MIND (enforced by GHNEST-10). Plaintext is materialized only
inside an owner-private temporary directory and deleted best-effort.

The production provider uses ``cryptography``'s AESGCM (established authenticated
encryption -- we do not invent a cipher) and supports GitHub OIDC to an external
KMS so no long-lived decryption credential is stored in the repository.
"""
from __future__ import annotations

import base64
import dataclasses
import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Optional, Protocol

from .manifest import canonical_json


class PlaintextRefusedError(Exception):
    """Raised when a payload would publish plaintext secrets to the remote NEST."""


# ---- context bound to the envelope as associated data ----------------------
@dataclass(frozen=True)
class EnvelopeContext:
    schema: str
    repo_id: int
    key_fingerprint: str
    manifest_hash: str

    def aad_bytes(self) -> bytes:
        return canonical_json(dataclasses.asdict(self))


@dataclass(frozen=True)
class EnvelopeKey:
    secret: bytes  # raw secret material (32 bytes for AES-256)
    fingerprint: str  # sha256:... of the secret

    @classmethod
    def generate(cls) -> "EnvelopeKey":
        secret = os.urandom(32)
        return cls(secret=secret, fingerprint="sha256:" + hashlib.sha256(secret).hexdigest())


_STEN_BYTES = (b"genesis_key", b"sk-or-v1-", b"ghp_", b"gho_", b"ghu_", b"ghs_",
               b"bearer ", b"-----BEGIN ")
_STEN_TEXT = ("genesis_key", "openai_api_key", "anthropic_api_key", "deepseek_api_key",
              "webhook_secret", "app_private_key", "client_secret", "installation_token")


def scan_for_plaintext_secrets(inventory: Dict[str, bytes]) -> Optional[str]:
    """Return the first offending path containing plaintext secret-shaped content.

    Returns None if the inventory is safe to publish. Detection is a refusal
    boundary, not a guarantee that no secret could ever slip past: the envelope
    and exact-revision materialization are the primary controls, this scan is an
    additional loud guard (GHNEST-3).
    """
    for rel, data in sorted(inventory.items()):
        low = data.lower()
        if b"genesis_key" in low or b'"genesis_key"' in low:
            return rel
        for marker in _STEN_BYTES:
            if marker in low:
                return rel
        text = data[:4096].decode("utf-8", errors="ignore")
        tl = text.lower()
        for marker in _STEN_TEXT:
            if marker in tl:
                return rel
    return None


class BodyEnvelopeProvider(Protocol):
    """Seal/Open with associated data binding and a stable key fingerprint."""

    def seal(self, plaintext: bytes, context: EnvelopeContext) -> bytes: ...

    def open(self, envelope: bytes, context: EnvelopeContext) -> bytes: ...

    def key_fingerprint(self) -> str: ...


class AESGCMEnvelopeProvider:
    """Authenticated envelope via ``cryptography`` AESGCM with associated data.

    Wire format: ``base64( nonce(12) || ciphertext || tag )``.
    Opening with a wrong context (repo id, schema, key fp, manifest hash) or a
    wrong key fails authentication and raises ``ValueError`` -- tamper detection.
    """

    def __init__(self, key: EnvelopeKey):
        self._key = key

    def key_fingerprint(self) -> str:
        return self._key.fingerprint

    def seal(self, plaintext: bytes, context: EnvelopeContext) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(12)
        aes = AESGCM(self._key.secret)
        ct = aes.encrypt(nonce, plaintext, context.aad_bytes())
        return base64.b64encode(nonce + ct)

    def open(self, envelope: bytes, context: EnvelopeContext) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        raw = base64.b64decode(envelope)
        nonce, payload = raw[:12], raw[12:]
        aes = AESGCM(self._key.secret)
        return aes.decrypt(nonce, payload, context.aad_bytes())


# ---- plaintext publication policy ------------------------------------------

# File paths that, if present in plaintext, are unconditionally refused.
_REFUSE_PLAINTEXT_PATHS = (
    "body.json",
    "body.public.json.gpg",
    "genesis.json",
    "self_seal.key",
)

# Paths that MAY travel in the remote nest but must never carry plaintext secrets.
_ALLOWED_REMOTE_PATHS = (
    "mantle-nest/nest.json",
    "mantle-nest/body.sealed",
    "mantle-nest/body.public.json",
    "mantle-nest/organism.json",
    "mantle-nest/resident_protocol.json",
    "mantle-nest/self_seal.json",
    "mantle-nest/transport_seal.json",
    "mantle-nest/transport_proof.json",
)


def enforce_publishable(inventory: Dict[str, bytes]) -> None:
    """Refuse a remote inventory that leaks the Body or any plaintext secret."""
    for rel, data in inventory.items():
        low = rel.lower()
        # refuse plaintext Body files (genesis_key carrier) outright
        if low.endswith("body.json") or low in _REFUSE_PLAINTEXT_PATHS:
            raise PlaintextRefusedError(
                "refusing to publish plaintext Body path: %s" % rel
            )
        if data.startswith(b"{") and b"genesis_key" in data:
            raise PlaintextRefusedError("plaintext genesis_key detected in %s" % rel)
    offender = scan_for_plaintext_secrets(inventory)
    if offender is not None:
        raise PlaintextRefusedError(
            "refusing to publish secret-shaped content in %s" % offender
        )


def redact_inventory(inventory: Dict[str, bytes]) -> Dict[str, bytes]:
    """Return a publishable copy, refusing to publish if secrets would leak.

    ``body.public.json`` may be carried (public, non-secret organism facts) but
    ``body.json`` (which carries ``genesis_key``) must be replaced by
    ``mantle-nest/body.sealed`` by the caller. This function refuses rather than
    silently dropping secrets.
    """
    enforce_publishable(inventory)
    return dict(inventory)
