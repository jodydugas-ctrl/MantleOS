# Germ spores — one file births one AppAI

Each PNG here is a **germ spore**: a single self-contained file carrying

- the **germ** — the complete build data for an AppAI (identity, truths,
  commandments, genome bands, declarative reflexes, controls, instincts with
  proving cases), and
- the **build note** — instructions any coding agent can read to grow the app,
  with or without Mantle installed.

Hatch one:

```bash
python -m mantle lifecycle authorize hatch examples/spores/greeter.png nest/ --approve --out=hatch-auth.json
python -m mantle hatch examples/spores/greeter.png --out=nest/ --auth=hatch-auth.json
```

Without Mantle, decode the pixels (the Quickstart is mirrored in PNG metadata and, when
Pillow is available during generation, printed on the image itself) and read the payload
key `germ`.

`notes_graft.png` carries a **graft germ** — a spore aimed at a host — applied
using a fresh authorization bound to the artifact and exact promoted target:

```bash
python -m mantle lifecycle authorize graft examples/spores/notes_graft.png workspace/sample_app --approve --out=graft-auth.json
python -m mantle graft examples/spores/notes_graft.png examples/sample_app --workspace=workspace --auth=graft-auth.json
```

The PNGs are generated from the germ files in `../eggs/` by
`python examples/spores/make_spores.py`; regenerate them after editing a germ. The
generator derives the shared AppAI Primer from `mantle.primer`, rewrites drifted example
germs, and verifies each emitted PNG structurally. Pytest then hatches every independent
SEED spore through the Stage-1 gate so Primer drift cannot hide inside a valid PNG.
