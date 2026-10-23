# examples/spore — a custom VCW substrate (PNG body plan), proven pure

The **spore** is, most fundamentally, **an example of a custom VCW substrate**: a single PNG that
carries its whole memory in its top-half colour field. **VCW is the law — a memory grammar, not one
file format** — and the spore proves the substrate can molt into a different medium than the
800-layer cube. *The PNG does not merely carry VCW-like data; it can **be** the VCW layer.* See
[The VCW Substrate Guide](../../documents/guides/VCW_Guide.md#vcw-is-the-law--the-cube-is-one-body-plan-the-png-is-another)
and the [VCW Substrate Guide](../../documents/guides/VCW_Guide.md) for the canonical
regions, explicit Grimoire statement frames (new spores default to v0.10), and display/memory boundary.

SPORE-PNG v2 maps its physical lanes directly to the selected Grimoire profile;
new spores use `grimoire-v0.10` and historical spores retain `grimoire-v0.9`:
`R=atom`, `G=role`, `B=evidence`, and `A=force`. Inert manifest and payload bytes are
QUOTE statements. Every statement ends with a `G=0x7f` PARITY control pixel, and the
manifest carries a SHA-256 fingerprint over all raw payload RGBA lanes and frame
boundaries.

It wears a second hat too: because it is a whole self-contained agent — identity, one task, one
append-only conversation, and an embedded Python reader/writer inside its own pixels — it is also the
smallest form of the **SEED** reproductive method
([`documents/REPRODUCTION.md`](../../documents/REPRODUCTION.md)).

The engine lives in the package at [`src/mantle/spore.py`](../../src/mantle/spore.py) (with its
embryo `spore_min.py`). This directory carries its **purity gate**, a **VCW-conformance proof**, and
an example seed.

```bash
# regenerate the example seed and verify it
python -m mantle spore demo examples/spore/example_spore.png
python -m mantle spore verify examples/spore/example_spore.png

# prove the PNG is a conformant VCW substrate (the nine memory-grammar properties, live)
python examples/spore/vcw_conformance.py
python examples/spore/vcw_conformance.py examples/spore/example_spore.png

# the purity audit: proves the seed stays MINIMAL and never grows into full Mantle OS
python examples/spore/audit_spore.py
python examples/spore/audit_spore.py examples/spore/example_spore.png   # also verify a given PNG
```

## Why a purity audit?

A spore's whole value is that it is transparent and small — *one PNG, one agent, one task, one
conversation, one append-only memory*. `audit_spore.py` inspects `spore.py`'s own source and
**refuses feature creep**: no organs, immune events, encryption, rebirth, lineage, child spores,
compaction, or summarization may appear in the seed. Strangeness — the cache-ghost substrate,
symbiosis, the nine organs — is Mantle tissue **layered on** the format
([`src/mantle/ghost.py`](../../src/mantle/ghost.py), the reproduction facade), never baked into the
seed itself. This gate is what keeps that promise honest.
