#!/usr/bin/env python3
"""bench.py -- tiny timing harness for the standalone codec: how expensive is a layer
encode, an append, a staged save, a load? Run: python bench.py [entries]"""
import os
import sys
import tempfile
import time

from vcw_cube import Cube, LAYER_BYTES, encode_png_rgba


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    t0 = time.time()
    png = encode_png_rgba(b"\x00" * LAYER_BYTES)
    t_enc = time.time() - t0

    cube = Cube.genesis()
    t0 = time.time()
    for i in range(n):
        cube.append("events", {"i": i}, opcode="EVENT")
    t_app = time.time() - t0

    d = tempfile.mkdtemp()
    p = os.path.join(d, "bench.vcw")
    t0 = time.time(); cube.save(p);  t_save = time.time() - t0
    t0 = time.time(); Cube.load(p);  t_load = time.time() - t0

    print("layer encode (2.56 MB -> %d KB PNG): %6.1f ms" % (len(png) // 1024, t_enc * 1e3))
    print("append x%-5d                      : %6.1f ms  (%.3f ms/entry)"
          % (n, t_app * 1e3, t_app * 1e3 / n))
    print("staged save (write+verify+replace) : %6.1f ms" % (t_save * 1e3))
    print("load                               : %6.1f ms" % (t_load * 1e3))


if __name__ == "__main__":
    main()
