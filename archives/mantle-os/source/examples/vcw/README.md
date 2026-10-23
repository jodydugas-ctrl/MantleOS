# examples/vcw — the VCW cube, standalone and fully defined

This directory is the **teaching home of the VCW cube**. Its centerpiece is
[`vcw_cube.py`](vcw_cube.py): a single, pure-stdlib, heavily documented Python file that
is the **normative, runnable definition of the cube format** — how a cube is born, how it
is read and appended, how the veil works, how entries are hashed, how a generation seals,
and how persistence stays atomic. It imports nothing from the `mantle` package, and the
bytes it writes are identical to the production engine's
([`src/mantle/vcw/cube.py`](../../src/mantle/vcw/cube.py)) — [`interop.py`](interop.py) proves
both directions on every CI run.

Read the cube as VCW hardware: addressable RGBA lanes, boot-declared bands, lazy layers,
drivers, integrity, and persistence. The standard body plan is visualized as an
800x800x800 cube, but layers materialize only as needed. Grimoire lane semantics are
software that can ride on the substrate; they are not the only meaning RGBA can have.

```bash
# the whole format, proven in one run
python vcw_cube.py selftest

# a cube you can poke at by hand
python vcw_cube.py create demo.vcw
python vcw_cube.py append demo.vcw facts '{"k": "sky", "v": "blue"}'
python vcw_cube.py read demo.vcw facts
python vcw_cube.py tombstone demo.vcw facts 0
python vcw_cube.py verify demo.vcw
python vcw_cube.py inspect demo.vcw
python vcw_cube.py extract demo.vcw 150 layer150.png   # open it in any image viewer
python vcw_cube.py seal demo.vcw

# one format, two faithful implementations (standalone <-> mantle engine)
python interop.py

# timings for the curious
python bench.py
```

## What else is here

| File | What it is |
|---|---|
| `vcw_cube.py` | **the standalone cube** — read this file to know the format |
| `interop.py` | proof the standalone and the engine speak the same bytes |
| `GUIDE.md` | the substrate teaching guide (concepts → code) |
| `bench.py` | tiny timing harness for the standalone codec |

The full engine lives in [`src/mantle/vcw/`](../../src/mantle/vcw/); this directory keeps the
standalone, normative definition of the cube format and proves it matches the engine
byte-for-byte (`interop.py`).
