"""Independent PNG vectors for the native and self-contained optical readers."""
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from mantleos import chromamem, optical_bootstrap


def chunk(tag, payload):
    return (struct.pack('>I', len(payload)) + tag + payload
            + struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff))


def png(width, height, raster, *, tail=b''):
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'iTXt', b'fixture\0\0\0\0\0synthetic')
            + chunk(b'IDAT', zlib.compress(raster) + tail) + chunk(b'IEND', b''))


# Hand-calculated forward-filter vectors. Expected pixels are independent of
# either reader, including modulo-256 wrap and Paeth's above-left prediction.
FIRST = bytes([10, 20, 30, 40, 50, 60])
SECOND = bytes([7, 9, 11, 80, 90, 100])
FIRST_FILTERED = [FIRST, bytes([10, 20, 30, 30, 30, 30]), FIRST,
                  bytes([10, 20, 30, 35, 40, 45]), bytes([10, 20, 30, 30, 30, 30])]
SECOND_FILTERED = [SECOND, bytes([7, 9, 11, 73, 81, 89]),
                   bytes([253, 245, 237, 40, 40, 40]),
                   bytes([2, 255, 252, 57, 61, 65]),
                   bytes([253, 245, 237, 40, 40, 70])]


class ChromaFilterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'synthetic.png'

    def readers(self):
        return (chromamem._png_data, optical_bootstrap.png_data)

    def test_all_filter_pairs_preserve_pixels_and_metadata(self):
        # Includes transitions both into and out of filter 0. The following
        # filtered row must see the correct previous row after the fast path.
        for first in range(5):
            for second in range(5):
                self.path.write_bytes(png(2, 2, bytes([first]) + FIRST_FILTERED[first]
                                          + bytes([second]) + SECOND_FILTERED[second]))
                for read in self.readers():
                    with self.subTest(first=first, second=second, reader=read.__module__):
                        self.assertEqual(read(self.path), (FIRST + SECOND, {'fixture': 'synthetic'}))

    def test_single_pixel_rows_and_cross_call_changes(self):
        for value in (bytes([0, 255, 128]), bytes([255, 0, 1])):
            self.path.write_bytes(png(1, 1, b'\0' + value))
            for read in self.readers():
                self.assertEqual(read(self.path)[0], value)
        self.path.write_bytes(png(1, 2, b'\0\xff\x80\0\x02\x02\xff\xff'))
        for read in self.readers():
            self.assertEqual(read(self.path)[0], bytes([255, 128, 0, 1, 127, 255]))

    def test_invalid_filters_remain_rejected(self):
        for kind in (5, 255):
            for raster in (bytes([kind]) + FIRST,
                           b'\0' + FIRST + bytes([kind]) + SECOND):
                self.path.write_bytes(png(2, len(raster) // 7, raster))
                for read in self.readers():
                    with self.subTest(kind=kind, reader=read.__module__), self.assertRaisesRegex(ValueError, 'filter'):
                        read(self.path)

    def test_invalid_raster_lengths_and_streams_remain_rejected(self):
        for raster, tail in ((b'\0' + FIRST[:-1], b''), (b'\0' + FIRST + b'\0', b''),
                             (b'\0' + FIRST, zlib.compress(b'extra'))):
            self.path.write_bytes(png(2, 1, raster, tail=tail))
            for read in self.readers():
                with self.subTest(reader=read.__module__), self.assertRaises(ValueError):
                    read(self.path)

    def test_crc_and_trailing_bytes_remain_rejected(self):
        valid = png(2, 1, b'\0' + FIRST)
        damaged = bytearray(valid)
        damaged[29] ^= 1  # IHDR CRC, while leaving dimensions intact.
        for data in (damaged, valid + b'extra'):
            self.path.write_bytes(data)
            for read in self.readers():
                with self.subTest(reader=read.__module__), self.assertRaises(ValueError):
                    read(self.path)

    def test_native_tape_round_trip_and_checksum_refusal(self):
        text = 'Synthetic \u2603 continuity. ' * 300
        records = [({'id': 'one', 'group': 'fixture'}, text)]
        self.path.write_bytes(chromamem._encode(records))
        decoded = chromamem.decode(self.path)
        self.assertEqual(decoded['by_id']['one']['text'], text)
        self.assertEqual(chromamem._png_data(self.path), optical_bootstrap.png_data(self.path))
        pixels, _ = chromamem._png_data(self.path)
        damaged = bytearray(pixels)
        damaged[9] ^= 1  # Tape checksum, with valid PNG CRC and zlib framing.
        stride = 1024 * 3
        raster = b''.join(b'\0' + damaged[i:i + stride] for i in range(0, len(damaged), stride))
        self.path.write_bytes(png(1024, len(damaged) // stride, raster))
        for read in (chromamem.decode, optical_bootstrap.inspect):
            with self.subTest(reader=read.__module__), self.assertRaises(ValueError):
                read(self.path)

    def test_portable_reader_works_in_isolated_python(self):
        portable = self.root / 'loader.py'
        shutil.copyfile(optical_bootstrap.__file__, portable)
        self.path.write_bytes(png(2, 2, b'\0' + FIRST + b'\x04' + SECOND_FILTERED[4]))
        command = ('import hashlib,runpy,sys; '
                   'read=runpy.run_path(sys.argv[1])["png_data"]; '
                   'print(hashlib.sha256(read(sys.argv[2])[0]).hexdigest())')
        result = subprocess.run([sys.executable, '-I', '-S', '-c', command, str(portable), str(self.path)],
                                cwd=self.root, capture_output=True, text=True, timeout=20, check=True)
        self.assertEqual(result.stdout.strip(), hashlib.sha256(FIRST + SECOND).hexdigest())


if __name__ == '__main__':
    unittest.main()
