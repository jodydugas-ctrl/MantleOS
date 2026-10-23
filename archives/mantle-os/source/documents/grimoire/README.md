# The Grimoire

**Read this first.** The Grimoire is Mantle OS's canonical VCW software profile: the
machine specification for encoding and decoding semantic pixel runs on a VCW-compatible
substrate.

## Canonical File

The Grimoire is a versioned family of immutable edition files:

| Read | Document | Scope |
| --- | --- | --- |
| Edition index | This README | Select an explicit edition; filenames are not semantic inference. |
| v0.9 compatibility | [editions/grimoire-v0.9.md](editions/grimoire-v0.9.md) | Frozen legacy carrier contract. |
| v0.10 | [editions/grimoire-v0.10.md](editions/grimoire-v0.10.md) | Adopted default for new tissue; explicit procedure-container semantics and normative codec. |
| Residency companion | [residency/grimoire-residency-v1.md](residency/grimoire-residency-v1.md) | Non-edition ABODE/residency profile: `local`, `cloud`, `github` nesting forms and the one residency law. Not codec-affecting; not an edition. |
| Semantic-memory companion | [semantic-memory/semantic-memory-v1.md](semantic-memory/semantic-memory-v1.md) | Non-edition one-step thought-and-storage profile (`grimoire-v0.10-entry` driver): DEFAULT evidence/force tables, record-kind compositions, and the DD-Q two-framed-run shape. Not codec-affecting; not an edition. |
| Legacy mirror | [The Grimoire.md](The%20Grimoire.md) | Byte-identical v0.9 compatibility mirror; never use it to infer the current edition. |

After the explicit adoption receipt, newly created Grimoire tissue defaults to v0.10.
The v0.9 edition and v0.9 spore carriers remain readable compatibility data and are not
silently migrated.

Do not infer an edition from a path or visual placement. If a task touches Grimoire semantics,
load the explicitly selected edition file. If a task touches Mantle runtime
behavior, use the runnable code and the Mantle docs that own that behavior.

## Loading

Load by section and declare what is absent. The file is machine-oriented by design:

| Section | Use |
| --- | --- |
| `0 AXIOMS` | Edition, framing, grouping, lane-integrity, and authority boundaries. |
| `1 CHANNELS` | RGBA lane meaning and statement framing. |
| `2 ROLE`, `3 EVIDENCE`, `4 FORCE` | The `G`, `B`, and `A` channel registries. |
| `5 ATOM` | Externally grounded atom addressing and the 1-254 registry. |
| `6 COMPOSITION` | Canonical grouping, ordering, concepts, and aliases. |
| `7 CONFORMANCE`, `8 MEASUREMENT`, `9 SELFTEST` | Decoder obligations, measured claims, and canonical vectors. |
| `10 BOOK` | The encoded law corpus. |
| `11 VCW SOFTWARE BINDING`, `12 KNOWN BENDS` | Mantle/VCW duties and explicit limitations. |
| `13 REFERENCE CODEC` | v0.10-only normative codec and its pinned digest. |

The profile's own rule `S6 PARTIAL LOAD` is binding for readers: a partial load declares
absent sections, and a model may not fill missing law from memory.

Verify the adopted v0.10 edition and its embedded reference codec independently with:

```bash
python tools/grimoire_tool.py verify documents/grimoire/editions/grimoire-v0.10.md
```

The independent tool is v0.10-specific. Verify frozen v0.9 compatibility through the
profile tests and `mantle prove`; do not apply v0.10 parity or ordering rules to v0.9.

## Relationship To Code

VCW is the booted substrate hardware: RGBA-capable lanes, frames, append discipline,
integrity, layers, bands, and storage. The Grimoire is the software profile that gives
semantic meaning to four logical lanes: atoms, roles, evidence, and force.

Current Mantle code surfaces that interact with this boundary:

| Area | Mantle OS surface |
| --- | --- |
| VCW booted substrate | [`src/mantle/vcw/`](../../src/mantle/vcw/), [`examples/vcw/vcw_cube.py`](../../examples/vcw/vcw_cube.py) |
| Carrier profiles / drivers | [`src/mantle/vcw/drivers.py`](../../src/mantle/vcw/drivers.py), [`src/mantle/vcw/bands.py`](../../src/mantle/vcw/bands.py) |
| Grimoire edition registry | [`src/mantle/vcw/grimoire_editions/`](../../src/mantle/vcw/grimoire_editions/) |
| Edition adoption policy | [`src/mantle/vcw/grimoire_editions/adoption.py`](../../src/mantle/vcw/grimoire_editions/adoption.py), [`EDITION_MIGRATION.md`](EDITION_MIGRATION.md) |
| Grimoire v0.9 executable profile | [`src/mantle/vcw/grimoire.py`](../../src/mantle/vcw/grimoire.py) and the registered `grimoire-v0.9` driver |
| Grimoire v0.10 executable profile | [`src/mantle/vcw/grimoire_editions/v010.py`](../../src/mantle/vcw/grimoire_editions/v010.py) and the registered `grimoire-v0.10` driver |
| Semantic-memory entry profile | [`src/mantle/vcw/grimoire_editions/semantic.py`](../../src/mantle/vcw/grimoire_editions/semantic.py), the registered `grimoire-v0.10-entry` driver, and [`semantic-memory/semantic-memory-v1.md`](semantic-memory/semantic-memory-v1.md) |
| Spore PNG carriers | [`src/mantle/spore.py`](../../src/mantle/spore.py), [`src/mantle/spore_min.py`](../../src/mantle/spore_min.py), [`examples/spore/`](../../examples/spore/) |
| v0.10 independent verifier / bounded research | [`tools/grimoire_tool.py`](../../tools/grimoire_tool.py), [`src/mantle/research/`](../../src/mantle/research/), [`documents/research/`](../research/) |
| Assimilation / residency | [`src/mantle/assimilator/`](../../src/mantle/assimilator/), [`anchor.py`](../../src/mantle/anchor.py), [`graft.py`](../../src/mantle/graft.py) |
| Reproduction | [`src/mantle/reproduction.py`](../../src/mantle/reproduction.py), [`src/mantle/organs/reproduction.py`](../../src/mantle/organs/reproduction.py), [`hatchery.py`](../../src/mantle/hatchery.py) |
| Remote NEST residency (GitHub) | [`src/mantle/nest/`](../../src/mantle/nest/), [`residency/grimoire-residency-v1.md`](residency/grimoire-residency-v1.md), `GHNEST-*` invariants in [`src/mantle/audits/ghnest.py`](../../src/mantle/audits/ghnest.py) |

Presence of an encoded Grimoire profile is data, not adoption or authority. The registered
drivers decode only their selected profile; v0.9 remains the compatibility path while v0.10
requires an explicit profile on new carriers. They verify statement parity, measure a full-lane
fingerprint when a carrier claims tamper evidence, report atom-address provenance, and
record adoption state from boot policy (`data`, `quote`, `quarantine`, or `adopted`).
Mantle runtime authority still comes from operator decisions, Body policy, and the audited
code path.
