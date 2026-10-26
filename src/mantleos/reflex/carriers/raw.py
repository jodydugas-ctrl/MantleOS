"""Framed data-only REFLEX program: RFC1 | sizes | SHA256 | JSON manifest | JSON IR.

Manifest and program are each canonical JSON; SHA256 covers both with domain
separation. CRC/signature/authorization are not inferred from the digest.
"""
import hashlib
import struct

from ..errors import refuse
from .contract import (MAX_CARRIER_BYTES, MAX_MANIFEST_BYTES, MAX_SOURCE_BYTES,
                       decode_manifest, report, verify_digest, verify_manifest)

MAGIC = b'RFC1'
HEADER = struct.Struct('>4sII32s')
DOMAIN = b'mantle.reflex-raw/0.1-experimental\x00'


class RawCarrier:
    carrier_id = 'reflex-raw/0.1-experimental'

    def encode(self, canonical: bytes, manifest: dict) -> bytes:
        checked = verify_manifest(canonical, manifest, self.carrier_id)
        from ..canonical import dumps
        metadata = dumps(checked)
        authenticated = DOMAIN + metadata + canonical
        return (HEADER.pack(MAGIC, len(metadata), len(canonical),
                            hashlib.sha256(authenticated).digest()) + metadata + canonical)

    def decode(self, carrier: bytes) -> tuple[bytes, dict]:
        if type(carrier) is not bytes or len(carrier) > MAX_CARRIER_BYTES:
            refuse('E_CARRIER', 'raw carrier must be bounded bytes')
        if len(carrier) < HEADER.size:
            refuse('E_CARRIER', 'truncated raw carrier header')
        magic, ml, pl, digest = HEADER.unpack_from(carrier)
        if magic != MAGIC:
            refuse('E_CARRIER', 'unknown raw carrier magic/edition')
        if not 1 <= ml <= MAX_MANIFEST_BYTES or not 1 <= pl <= MAX_SOURCE_BYTES:
            refuse('E_SIZE', 'raw carrier declared lengths out of range')
        if len(carrier) != HEADER.size + ml + pl:
            refuse('E_CARRIER', 'raw carrier frame length mismatch')
        metadata = carrier[HEADER.size:HEADER.size + ml]
        payload = carrier[HEADER.size + ml:]
        actual = hashlib.sha256(DOMAIN + metadata + payload).digest()
        if actual != digest:
            refuse('E_INTEGRITY', 'raw carrier frame digest mismatch')
        manifest = decode_manifest(metadata)
        verify_manifest(payload, manifest, self.carrier_id)
        return payload, manifest

    def verify(self, carrier: bytes, expected_digest: str) -> dict:
        canonical, manifest = self.decode(carrier)
        verify_digest(canonical, expected_digest)
        return report(self.carrier_id, canonical, manifest)
