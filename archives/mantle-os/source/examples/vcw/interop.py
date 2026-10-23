#!/usr/bin/env python3
"""
interop.py  --  proof that the standalone codec and the production engine speak the
                SAME bytes (Mantle OS)

Direction A: the ENGINE (mantle/vcw/cube.py) saves a cube; this directory's standalone
`vcw_cube.py` loads it, verifies every hash, reads through the veil, APPENDS to it, and
saves it back.
Direction B: the engine loads that file again, verifies, and reads the standalone's
appended entry -- plus seal fingerprints computed by both implementations must be
byte-identical.

Run from the repository root or from this directory:
    python examples/vcw/interop.py
"""
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "src"))  # the mantle package (src-layout)
sys.path.insert(0, _HERE)                       # the standalone codec (this directory)

import vcw_cube as standalone                      # noqa: E402
from mantle.vcw.cube import Cube as EngineCube     # noqa: E402
from mantle.vcw.entry import make_entry            # noqa: E402


def main() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("  [%s] %-52s %s" % ("PASS" if cond else "FAIL", name, detail))

    d = tempfile.mkdtemp(prefix="vcw-interop-")
    path = os.path.join(d, "gen000.vcw")

    # ---- Direction A: engine writes -> standalone reads/appends -------------
    eng = EngineCube.genesis(__import__("mantle.vcw.bands",
                                        fromlist=["standard_genome"]).standard_genome())
    eng.append("facts", make_entry({"k": "writer", "v": "engine"}, source="interop"))
    eng.append("thoughts", make_entry("engine musing", opcode="THINK", author="MIND"))
    eng.save(path)

    sa = standalone.Cube.load(path)
    check("standalone loads an engine-written cube", True, path)
    check("standalone verify(): healthy", sa.verify() == [])
    check("standalone sees the engine's entry",
          sa.read("facts")[0]["content"] == {"k": "writer", "v": "engine"})
    check("standalone honors the veil on engine data", sa.read("thoughts") == [])
    appended = sa.append("facts", {"k": "writer", "v": "standalone"}, source="interop")
    sa.save(path)
    check("standalone appended + staged-saved", appended["id"] == 1)

    # ---- Direction B: engine reads the standalone's bytes -------------------
    eng2 = EngineCube.load(path)
    check("engine loads the standalone-written cube", eng2.verify() == [])
    vals = [e["content"] for e in eng2.read("facts")]
    check("engine sees BOTH writers' entries",
          vals == [{"k": "writer", "v": "engine"}, {"k": "writer", "v": "standalone"}])
    check("engine retrieve() honors the shared logical addressing",
          eng2.retrieve("facts", 1)["content"]["v"] == "standalone")

    # ---- seal fingerprints must be byte-identical across implementations ----
    fp_engine = eng2.fingerprint()
    fp_standalone = standalone.Cube.load(path).fingerprint()
    check("seal fingerprints byte-identical", fp_engine == fp_standalone,
          fp_engine[:24] + "...")

    print("\ninterop:", "ALL GREEN -- one format, two faithful implementations"
          if ok else "FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
