"""Experimental strict ZIP data envelope. NOT a MantleOS Cartridge Body.

Two members only: manifest.json and program.json, never paths or executables.
The archive does not contain a BODY, operator receipt, approval or capability.
"""
import io
import zipfile
import zlib

from ..canonical import dumps
from ..errors import refuse
from .contract import (MAX_CARRIER_BYTES, MAX_MANIFEST_BYTES, MAX_SOURCE_BYTES,
                       decode_manifest, report, verify_digest, verify_manifest)

FILES = ('manifest.json', 'program.json')
EPOCH = (1980, 1, 1, 0, 0, 0)
FILE_MODE = 0o100644 << 16


class ZipReflexCarrier:
    carrier_id = 'reflex-zip/0.1-experimental'

    def encode(self, canonical: bytes, manifest: dict) -> bytes:
        checked = verify_manifest(canonical, manifest, self.carrier_id)
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9, allowZip64=False) as archive:
            for name, payload in (('manifest.json', dumps(checked)), ('program.json', canonical)):
                info = zipfile.ZipInfo(name, date_time=EPOCH)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = FILE_MODE
                archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED,
                                 compresslevel=9)
        result = mem.getvalue()
        if len(result) > MAX_CARRIER_BYTES:
            refuse('E_SIZE', 'ZIP carrier exceeds archive byte budget')
        return result

    def decode(self, carrier: bytes) -> tuple[bytes, dict]:
        if type(carrier) is not bytes or len(carrier) > MAX_CARRIER_BYTES:
            refuse('E_CARRIER', 'ZIP carrier must be bounded bytes')
        # No appended/prefixed polyglot bytes: require normal local header at 0
        # and an empty-comment end-of-central-directory exactly at EOF.
        if (len(carrier) < 22 or not carrier.startswith(b'PK\x03\x04')
                or carrier[-22:-18] != b'PK\x05\x06' or carrier[-2:] != b'\x00\x00'):
            refuse('E_CARRIER', 'ZIP carrier framing is not a standalone ZIP')
        try:
            with zipfile.ZipFile(io.BytesIO(carrier), mode='r', allowZip64=False) as archive:
                infos = archive.infolist()
                if len(infos) != 2 or tuple(info.filename for info in infos) != FILES:
                    refuse('E_CARRIER', 'ZIP must have exactly two ordered literal files')
                if archive.comment:
                    refuse('E_CARRIER', 'ZIP comments are unsupported')
                for info, max_size in zip(infos, (MAX_MANIFEST_BYTES, MAX_SOURCE_BYTES)):
                    if (info.file_size == 0 or info.file_size > max_size or info.is_dir()
                            or info.flag_bits != 0 or info.compress_type != zipfile.ZIP_DEFLATED
                            or info.extra or info.comment or info.date_time != EPOCH
                            or info.create_system != 3 or info.external_attr != FILE_MODE):
                        refuse('E_CARRIER', 'invalid ZIP member metadata or declared size')
                parts = []
                for info, max_size in zip(infos, (MAX_MANIFEST_BYTES, MAX_SOURCE_BYTES)):
                    with archive.open(info, mode='r') as source:
                        blob = source.read(max_size + 1)
                    if len(blob) != info.file_size or len(blob) > max_size:
                        refuse('E_SIZE', 'ZIP expanded member exceeds bound')
                    parts.append(blob)
            metadata, payload = parts
            manifest = decode_manifest(metadata)
            verify_manifest(payload, manifest, self.carrier_id)
            # Freeze this experimental ZIP edition at byte-level on the same
            # host encoder. This rejects polyglot prefixes and changes to
            # otherwise-ignored ZIP local/central header fields. Native and
            # cross-zlib interop requires a separately qualified edition.
            if self.encode(payload, manifest) != carrier:
                refuse('E_CARRIER', 'ZIP envelope is not exact canonical carrier bytes')
            return payload, manifest
        except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, RuntimeError,
                OSError, ValueError, OverflowError, zlib.error) as error:
            if hasattr(error, 'code'):
                raise
            refuse('E_CARRIER', 'invalid, truncated, encrypted or corrupt ZIP carrier')

    def verify(self, carrier: bytes, expected_digest: str) -> dict:
        canonical, manifest = self.decode(carrier)
        verify_digest(canonical, expected_digest)
        return report(self.carrier_id, canonical, manifest)
