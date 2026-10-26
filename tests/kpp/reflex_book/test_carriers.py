"""M4 transport conformance. A successful decode is never admission."""
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from mantleos.reflex.bytecode import encode as encode_bytecode
from mantleos.reflex.compiler import compile_ir
from mantleos.reflex.canonical import dumps, loads
from mantleos.reflex.carriers import carrier, make_manifest
from mantleos.reflex.carriers.contract import (MAX_CARRIER_BYTES, MAX_MANIFEST_BYTES,
                                                      MAX_SOURCE_BYTES)
from mantleos.reflex.carriers.raw import HEADER, MAGIC, DOMAIN
from mantleos.reflex.carriers.zip_reflex import EPOCH, FILE_MODE
from mantleos.reflex.errors import ReflexError
from mantleos.reflex.parser import parse_program
from mantleos.reflex.vm import run

from .fixtures import workspace
ROOT=workspace()
EXAMPLES = ROOT / 'examples/reflex_book'


def program(name='location_rule.json'):
    return dumps(parse_program((EXAMPLES / name).read_bytes()))


def pair(kind, content=None):
    adapter = carrier(kind)
    content = program() if content is None else content
    manifest = make_manifest(content, adapter.carrier_id)
    return adapter, manifest, adapter.encode(content, manifest)


def zip_edit(entries, *, comment=b'', name2='program.json', metadata_override=None):
    """Build deliberately malformed ZIP from byte content, bypassing encoder."""
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for i, (name, content) in enumerate(entries):
            info = zipfile.ZipInfo(name, date_time=EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = FILE_MODE
            if metadata_override and i in metadata_override:
                for key, value in metadata_override[i].items():
                    setattr(info, key, value)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                z.writestr(info, content)
        z.comment = comment
    return b.getvalue()


class CarrierConformanceTests(unittest.TestCase):
    def refuses(self, fn, code=None):
        with self.assertRaises(ReflexError) as caught:
            fn()
        if code:
            self.assertEqual(caught.exception.code, code)

    def test_reproducible_roundtrip_both_codecs_two_programs(self):
        for kind in ('raw', 'zip'):
            for case in ('location_rule.json', 'counter_rule.json'):
                with self.subTest(kind=kind, case=case):
                    source = program(case)
                    c, m, packed = pair(kind, source)
                    self.assertEqual(c.encode(source, m), packed)
                    self.assertEqual(c.decode(packed), (source, m))
                    result = c.verify(packed, hashlib.sha256(source).hexdigest())
                    self.assertFalse(result['authorized'])
                    self.assertFalse(result['installed'])
                    self.assertFalse(result['executed'])
                    self.assertEqual(result['status'], 'VERIFIED_TRANSPORT_ONLY')
                    self.assertEqual(encode_bytecode(compile_ir(parse_program(source))),
                                     encode_bytecode(compile_ir(parse_program(c.decode(packed)[0]))))

    def test_expected_digest_is_an_independent_host_anchor(self):
        for kind in ('raw', 'zip'):
            c, m, blob = pair(kind)
            self.refuses(lambda: c.verify(blob, '0' * 64), 'E_INTEGRITY')
            self.refuses(lambda: c.verify(blob, 'not-a-sha'), 'E_INTEGRITY')
            self.refuses(lambda: c.verify(blob, None), 'E_INTEGRITY')
            self.refuses(lambda: c.verify(blob, 'A' * 64), 'E_INTEGRITY')
            # A fully self-consistent different program still fails host's pin.
            c2, m2, newblob = pair(kind, program('counter_rule.json'))
            self.refuses(lambda: c2.verify(newblob, m['program_sha256']), 'E_INTEGRITY')

    def test_manifest_must_bind_exact_program_without_authority(self):
        p = program()
        for kind in ('raw', 'zip'):
            c = carrier(kind)
            m = make_manifest(p, c.carrier_id)
            for key, value in [('authority', 'APPROVED'), ('installed', True),
                               ('executable_on_decode', True), ('program_bytes', 0),
                               ('program_sha256', '0'*64), ('carrier_id', 'other')]:
                changed = dict(m)
                changed[key] = value
                self.refuses(lambda: c.encode(p, changed), 'E_INTEGRITY')
            extra = dict(m)
            extra['operator_secret'] = 'nope'
            self.refuses(lambda: c.encode(p, extra), 'E_INTEGRITY')
            self.refuses(lambda: c.encode(p, {}), 'E_INTEGRITY')
            self.refuses(lambda: c.encode(p, None), 'E_INTEGRITY')

    def test_noncanonical_and_malformed_program_refused(self):
        source = program()
        for kind in ('raw', 'zip'):
            c = carrier(kind)
            self.refuses(lambda: make_manifest(b' ' + source, c.carrier_id), 'E_CANONICAL')
            self.refuses(lambda: make_manifest(source + b'\n', c.carrier_id), 'E_CANONICAL')
            self.refuses(lambda: make_manifest(b'', c.carrier_id), 'E_SIZE')
            self.refuses(lambda: make_manifest(b'!'*65537, c.carrier_id), 'E_SIZE')
            self.refuses(lambda: make_manifest(None, c.carrier_id), 'E_CARRIER')
            self.refuses(lambda: make_manifest(b'{}', c.carrier_id))
            self.refuses(lambda: make_manifest(source, 'untrusted-new-edition'), 'E_CARRIER')

    def test_raw_frame_corruption_and_truncation(self):
        c, _, blob = pair('raw')
        self.assertEqual(blob[:4], MAGIC)
        for idx in (0, 3, 4, 7, 8, 11, 12, 23, HEADER.size, len(blob)//2, len(blob)-1):
            mutated = bytearray(blob)
            mutated[idx] ^= 0x01
            with self.subTest(index=idx):
                self.refuses(lambda: c.decode(bytes(mutated)))
        for truncated in (blob[:0], blob[:1], blob[:HEADER.size-1], blob[:-1]):
            self.refuses(lambda: c.decode(truncated))
        self.refuses(lambda: c.decode(blob + b'junk'), 'E_CARRIER')
        self.refuses(lambda: c.decode(bytearray(blob)), 'E_CARRIER')
        self.refuses(lambda: c.decode(b'X' * (MAX_CARRIER_BYTES + 1)), 'E_CARRIER')

    def test_raw_recomputed_digest_cannot_grant_authority(self):
        c, manifest, blob = pair('raw')
        ml = len(dumps(manifest))
        metadata = dict(manifest)
        metadata['authority'] = 'APPROVED'
        changed_meta = dumps(metadata)
        payload = program()
        newhash = hashlib.sha256(DOMAIN + changed_meta + payload).digest()
        forged = HEADER.pack(MAGIC, len(changed_meta), len(payload), newhash) + changed_meta + payload
        self.refuses(lambda: c.decode(forged), 'E_INTEGRITY')
        self.assertNotEqual(changed_meta, blob[HEADER.size:HEADER.size+ml])

    def test_zip_entries_path_traversal_duplicate_and_extras(self):
        c, m, blob = pair('zip')
        man = dumps(m)
        prog = program()
        alterations = [
            [('manifest.json', man), ('../program.json', prog)],
            [('manifest.json', man), ('program.json', prog), ('another', b'bad')],
            [('manifest.json', man), ('manifest.json', man)],
            [('program.json', prog), ('manifest.json', man)],
            [('manifest.json', man)],
            [],
        ]
        for entries in alterations:
            self.refuses(lambda: c.decode(zip_edit(entries)), 'E_CARRIER')
        self.refuses(lambda: c.decode(zip_edit([('manifest.json', man), ('program.json', prog)], comment=b'x')), 'E_CARRIER')
        self.refuses(lambda: c.decode(zip_edit([('manifest.json', man), ('program.json', prog)],
                          metadata_override={1:{'external_attr': 0o120777 << 16}})), 'E_CARRIER')
        self.refuses(lambda: c.decode(zip_edit([('manifest.json', man), ('program.json', prog)],
                          metadata_override={1:{'date_time': (2026, 1, 1, 0, 0, 0)}})), 'E_CARRIER')

    def test_zip_bombs_and_bounded_read(self):
        c, m, blob = pair('zip')
        man = dumps(m)
        prog = program()
        self.refuses(lambda: c.decode(zip_edit([('manifest.json', man),
                                                ('program.json', b'A'*(MAX_SOURCE_BYTES+1))])), 'E_CARRIER')
        self.refuses(lambda: c.decode(zip_edit([('manifest.json', b'A'*(MAX_MANIFEST_BYTES+1)),
                                                ('program.json', prog)])), 'E_CARRIER')
        self.refuses(lambda: c.decode(b'Z' * (MAX_CARRIER_BYTES+1)), 'E_CARRIER')
        self.refuses(lambda: c.decode(b'not-a-zip'), 'E_CARRIER')
        self.refuses(lambda: c.decode(blob[:-8]), 'E_CARRIER')
        self.refuses(lambda: c.decode(bytearray(blob)), 'E_CARRIER')

    def test_zip_bogus_payload_manifest_and_corruption(self):
        c, m, blob = pair('zip')
        man = dumps(m)
        prog = program()
        changed = prog.replace(b'example.unusual-location', b'example.unusual-locatiox')
        self.refuses(lambda: c.decode(zip_edit([('manifest.json', man), ('program.json', changed)])), 'E_INTEGRITY')
        self.refuses(lambda: c.decode(zip_edit([('manifest.json', man + b' ',), ('program.json', prog)])), 'E_CANONICAL')
        meta = dict(m)
        meta['authority'] = 'APPROVED'
        self.refuses(lambda: c.decode(zip_edit([('manifest.json', dumps(meta)), ('program.json', prog)])), 'E_INTEGRITY')
        mutated = bytearray(blob)
        mutated[len(mutated)//2] ^= 1
        self.refuses(lambda: c.decode(bytes(mutated)))

    def test_transport_roundtrip_never_invokes_runtime_or_operator(self):
        from mantleos.reflex import vm, admission
        for kind in ('raw', 'zip'):
            c, m, blob = pair(kind)
            with patch.object(vm, 'run', side_effect=AssertionError('VM EXECUTED')), \
                 patch.object(admission, 'operator_issue_receipt', side_effect=AssertionError('AUTHORIZED')):
                c.verify(blob, m['program_sha256'])
                c.decode(blob)

    def test_cli_pack_verify_unpack_exact_digest_and_exclusive_write(self):
        for kind in ('raw', 'zip'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                temp = Path(tmp)
                packed = temp / 'transport.bin'
                unpacked = temp / 'program.json'
                digest = hashlib.sha256(program()).hexdigest()
                cmd = [sys.executable, '-m', 'mantleos.reflex.cli']
                def invoke(*args):
                    return subprocess.run(cmd+list(args), cwd=ROOT, capture_output=True, text=True, timeout=12)
                result = invoke('carrier-pack', str(EXAMPLES/'location_rule.json'), '--carrier', kind,
                                '--output', str(packed))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(json.loads(result.stdout)['authorized'])
                self.assertEqual(invoke('carrier-pack', str(EXAMPLES/'location_rule.json'), '--carrier', kind,
                                        '--output', str(packed)).returncode, 2)
                result = invoke('carrier-verify', str(packed), '--carrier', kind,
                                '--expected-sha256', digest)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(invoke('carrier-unpack', str(packed), '--carrier', kind,
                                        '--expected-sha256', '0'*64, '--output', str(unpacked)).returncode, 2)
                self.assertFalse(unpacked.exists())
                result = invoke('carrier-unpack', str(packed), '--carrier', kind,
                                '--expected-sha256', digest, '--output', str(unpacked))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(unpacked.read_bytes(), program())
                self.assertEqual(invoke('carrier-unpack', str(packed), '--carrier', kind,
                                        '--expected-sha256', digest, '--output', str(unpacked)).returncode, 2)

    def test_zip_polyglots_and_trailing_bytes_refused(self):
        c, m, blob = pair('zip')
        self.refuses(lambda: c.decode(b'PREFIX' + blob), 'E_CARRIER')
        self.refuses(lambda: c.decode(blob + b'TRAILING'), 'E_CARRIER')
        self.refuses(lambda: c.decode(b'PK\x03\x04garbage' + blob), 'E_CARRIER')
        self.refuses(lambda: c.decode(blob.replace(b'PK\x05\x06', b'ABCD', 1)), 'E_CARRIER')

    def test_seeded_mutation_corpus_refuses_changes(self):
        import random
        rnd = random.Random(0x4D34524658)
        for kind in ('raw', 'zip'):
            c, m, blob = pair(kind)
            for i in range(200):
                at = rnd.randrange(len(blob))
                changed = bytearray(blob)
                changed[at] ^= 1 << rnd.randrange(8)
                with self.subTest(carrier=kind, iteration=i, index=at):
                    self.refuses(lambda: c.verify(bytes(changed), m['program_sha256']))

    def test_packaged_golden_carrier_bytes(self):
        vectors = json.loads((EXAMPLES / 'm4_carrier_golden_vectors.json').read_text('utf-8'))
        p = program()
        self.assertEqual(vectors['canonical_sha256'], hashlib.sha256(p).hexdigest())
        for kind, spec in vectors['fixtures'].items():
            packed = (EXAMPLES / spec['file']).read_bytes()
            self.assertEqual(len(packed), spec['bytes'])
            self.assertEqual(hashlib.sha256(packed).hexdigest(), spec['sha256_on_this_host'])
            c = carrier(kind)
            self.assertEqual(c.decode(packed)[0], p)
            self.assertFalse(c.verify(packed, vectors['canonical_sha256'])['authorized'])
            if kind == 'raw':
                self.assertEqual(c.encode(p, make_manifest(p,c.carrier_id)), packed)
            # The ZIP encoder's deflate output may differ across zlib implementations.
            # A future cross-platform/approved edition needs independent goldens.

    def test_legacy_binary_is_not_a_carrier(self):
        b = encode_bytecode(compile_ir(parse_program(program())))
        for kind in ('raw', 'zip'):
            self.refuses(lambda: carrier(kind).decode(b), 'E_CARRIER')

    def test_cross_carrier_confusion_is_refused(self):
        a, ma, raw = pair('raw')
        b, mb, zipped = pair('zip')
        self.refuses(lambda: a.decode(zipped), 'E_CARRIER')
        self.refuses(lambda: b.decode(raw), 'E_CARRIER')
        self.refuses(lambda: a.encode(program(), mb), 'E_INTEGRITY')
        self.refuses(lambda: b.encode(program(), ma), 'E_INTEGRITY')
        self.refuses(lambda: carrier('Cartridge'), 'E_CARRIER')


if __name__ == '__main__':
    unittest.main()
