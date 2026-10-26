"""Strict M4 manifest contract for bytes-as-data, never program authority."""
import hashlib
import hmac
from typing import Protocol

from ..canonical import dumps, loads, MAX_SOURCE_BYTES
from ..errors import refuse
from ..parser import parse_program

MANIFEST_SCHEMA = 'mantle.reflex-carrier-manifest/0.1-experimental'
MAX_MANIFEST_BYTES = 4096
MAX_CARRIER_BYTES = 256 * 1024


class CarrierAdapter(Protocol):
    carrier_id: str
    def encode(self, canonical: bytes, manifest: dict) -> bytes: ...
    def decode(self, carrier: bytes) -> tuple[bytes, dict]: ...
    def verify(self, carrier: bytes, expected_digest: str) -> dict: ...


def checked_program(canonical: bytes) -> dict:
    if type(canonical) is not bytes:
        refuse('E_CARRIER', 'canonical source must be exact bytes')
    if len(canonical) == 0 or len(canonical) > MAX_SOURCE_BYTES:
        refuse('E_SIZE', 'canonical program size out of bounds')
    parsed = parse_program(canonical)
    if dumps(parsed) != canonical:
        refuse('E_CANONICAL', 'carrier payload must be exact canonical UTF-8 IR')
    return parsed


def make_manifest(canonical: bytes, carrier_id: str) -> dict:
    ir = checked_program(canonical)
    if carrier_id not in ('reflex-raw/0.1-experimental', 'reflex-zip/0.1-experimental'):
        refuse('E_CARRIER', 'unsupported carrier edition')
    return {
        'schema': MANIFEST_SCHEMA,
        'carrier_id': carrier_id,
        'program_id': ir['id'],
        'book': ir['book'],
        'program_sha256': hashlib.sha256(canonical).hexdigest(),
        'program_bytes': len(canonical),
        'authority': 'NONE',
        'installed': False,
        'executable_on_decode': False,
    }


def verify_manifest(canonical: bytes, manifest: dict, carrier_id: str) -> dict:
    expected = make_manifest(canonical, carrier_id)
    if type(manifest) is not dict or dumps(manifest) != dumps(expected):
        refuse('E_INTEGRITY', 'carrier manifest is not the exact unprivileged contract')
    if len(dumps(manifest)) > MAX_MANIFEST_BYTES:
        refuse('E_SIZE', 'carrier manifest exceeds size limit')
    return expected


def decode_manifest(raw: bytes) -> dict:
    if type(raw) is not bytes or len(raw) == 0 or len(raw) > MAX_MANIFEST_BYTES:
        refuse('E_SIZE', 'carrier manifest byte count out of bounds')
    manifest = loads(raw)
    if type(manifest) is not dict or dumps(manifest) != raw:
        refuse('E_CANONICAL', 'carrier manifest must be canonical JSON object')
    return manifest


def verify_digest(payload: bytes, expected: str) -> None:
    import re
    if type(expected) is not str or re.fullmatch('[0-9a-f]{64}', expected) is None:
        refuse('E_INTEGRITY', 'expected digest must be lowercase SHA-256 hex')
    if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), expected):
        refuse('E_INTEGRITY', 'carrier program digest differs from host expectation')


def report(carrier_id: str, payload: bytes, manifest: dict) -> dict:
    return {
        'status': 'VERIFIED_TRANSPORT_ONLY',
        'carrier_id': carrier_id,
        'program_id': manifest['program_id'],
        'program_sha256': manifest['program_sha256'],
        'program_bytes': len(payload),
        'authorized': False,
        'installed': False,
        'executed': False,
    }
