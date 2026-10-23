"""Setup-inclusive synthetic Chroma workload for matched optimizer trials.

Run from the source tree being measured. Prints deterministic checksums only;
the SCAN/Optimizer experiment runner records process duration independently.
"""
import hashlib
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path.cwd() / 'src'))
from mantleos import chromamem, optical_bootstrap


def main():
    # About 3 MiB of non-ASCII text, spanning many of the writer's filter-0 rows.
    text = 'Synthetic \u2603 continuity, with no personal records.\n' * 60_000
    records = [({'id': 'synthetic', 'group': 'benchmark'}, text)]
    with tempfile.TemporaryDirectory(prefix='chroma-benchmark-') as temporary:
        path = Path(temporary) / 'fixture.png'
        path.write_bytes(chromamem._encode(records))
        for _ in range(2):
            native = chromamem.decode(path)
            if native['by_id']['synthetic']['text'] != text:
                raise AssertionError('Tape content changed')
            pixels, _ = optical_bootstrap.png_data(path)
            if pixels[9:41].hex() != native['body_sha256']:
                raise AssertionError('Portable tape checksum changed')
            print(hashlib.sha256(pixels).hexdigest())


if __name__ == '__main__':
    main()
