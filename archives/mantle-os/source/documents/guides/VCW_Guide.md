# Mantle OS — The VCW Substrate Guide

The VCW ("Visual Cortex Workspace") is the organism's booted substrate hardware: a
standard body plan visualized as an 800×800×800 cube, with 800×800 RGBA layers in a ZIP
container, addressable byte-by-byte (`offset = (y*SIDE + x) * 4`), readable in any image
viewer. The 800-layer shape is the canonical visualization soft cap; layers are generated
only as bands need them. *If it's not in the VCW, it didn't happen.* The on-disk format is
unchanged from v2 (`vcw-cube-png-v2`).

The Grimoire is software that can run on that substrate. In a Grimoire-semantic layer,
the four RGBA lanes may mean atom, role, evidence, and force. In another layer, the same
four lanes may be boot-mapped to tool state, app data, indexes, a database payload,
spatial memory, or repair bytes. VCW supplies the lanes, frames, allocation, integrity,
and persistence; the cube bootloader and each layer's driver/profile declare what those
lanes mean.

The anatomical atlas (coordinate ownership, colour semantics) and the compliance
tiers (what to do when a full VCW can't run) are the last two sections of this guide.
The machine-readable atlas companion is `mantle.vcw.atlas`.
For resident recall, text-commit, sidecar, and MIND rehydration lessons from
NotepadNext.AppAI, see
[`Resident_Runtime_Lessons.md`](Resident_Runtime_Lessons.md).

## The mental model

```
cube   = one GENERATION of experiential memory (identity lives in the Body, never here)
band   = a named, contiguous reserved RANGE of layers, self-described by a boot sector
layer  = one real PNG; materialized on demand inside the band's range
lane   = one of the four addressable RGBA streams; semantics are profile-defined
entry  = one immutable record; hashed over EVERY non-volatile field
veil   = private bands read as [] unless deliberately lifted; tombstoned/quarantined
         entries never surface
```

Standard genome ownership, app-band reservations, and tail space are defined in the
anatomical atlas and exported from `mantle.vcw.atlas`.

## Boot sectors and drivers (two-level encoding)

A band's boot sector (level 1, fixed format) names a **driver** or carrier profile (level
2, programmable): `log-json` (immutable entry log), `keyvalue` (small mutable map),
`calendar-spatial` (data AS colors at coordinates — a real canvas), `exec` (a calcified
reflex layer), an explicit Grimoire profile (`grimoire-v0.9` compatibility or
`grimoire-v0.10`; semantic RGBA runs: atom, role, evidence, force), or
`grimoire-v0.10-entry` — the semantic-memory driver, which ENCODES an appended entry
into a v0.10 statement at write time (thought and storage in one step; see
[the semantic-memory companion](../grimoire/semantic-memory/semantic-memory-v1.md)).
Entry-stream drivers (`log-json`, `grimoire-v0.10-entry`) share the cube's entry
guarantees: band-unique ids, multi-layer reads, veil, immune marks, graded memory, and
metabolism.
Drivers live in the Body (trusted code); boot sectors are data that select them.

That means RGBA is not globally "thought" and not globally "Grimoire." RGBA is the lane
hardware. A layer profile declares framing, terminators, integrity, ordering, and lane
meaning for that layer. One band can store four streams of semantic Grimoire morphemes;
another can use those lanes as a compact database record. SPORE-PNG v2 declares the
Grimoire mapping directly, including Alpha as force.

## VCW Hardware, Grimoire Software

The compatibility rule is:

| Layer | Responsibility |
| --- | --- |
| **VCW substrate** | addressable RGBA lanes, lazy layers, boot-declared bands, append discipline, persistence, integrity, and carrier/profile selection |
| **Cube bootloader** | dimensions, band allocation, layer ownership, driver/profile, privacy, capacity policy, and carrier duties |
| **Layer profile / driver** | how the four lanes are framed, ended, verified, stored, and interpreted for this layer |
| **Grimoire software profile** | one possible lane meaning: `R=atom`, `G=role`, `B=evidence`, `A=force` |
| **Body policy** | whether a decoded profile is stored, rejected, quarantined, quoted, or adopted |

A Grimoire profile present in a filesystem, spore, cube layer, cache, or prompt is data
until the operator or Body policy adopts it. Presence is not authority. In Mantle's
registered edition driver, boot params set the adoption state explicitly:
`data`, `quote`, `quarantine`, or `adopted`. Only `adopted` is governing, and its
authority is recorded as `boot-policy`.

Grimoire editions also separate statement parity from transport integrity. Parity proves
the statement morphemes agree with the selected edition's carrier rule; a carrier claiming
tamper evidence must provide the raw-run fingerprint over the full framed RGBA run. If
that fingerprint is absent, the decoded layer is marked `unmeasured` rather than silently
trusted.

## VCW is the law — the cube is one body plan, the PNG is another

The boot sector deciding behaviour (not hard-coded logic) has a larger consequence: **VCW is
not one file format. It is substrate hardware plus a memory grammar — a law about how state is
stored, grown, proven, and exposed.** The 800-layer cube (`vcw-cube-png-v2`) is one *body plan* that obeys the law. A
[**spore**](../../examples/spore/) — a single PNG that carries its whole memory in its top-half
colour field — is **another**. Same law, different medium. So the spore is not a toy Mantle; it
is proof the substrate can **molt into different media**.

A substrate *is* a VCW layer when it provides the nine properties of the memory grammar:

| The law (memory grammar) | The cube body plan | The SPORE-PNG body plan |
| --- | --- | --- |
| **addressable region** | bands over layers; `offset=(y·SIDE+x)·4` | the top-half VCW region; block index `i→(i%W, i//W)` |
| **canonical payload** | driver-native content per layer, hashed entries | one JSON payload serialized as the selected Grimoire QUOTE profile |
| **append-only evolution** | `log-json` immutable entries, monotonic ids | append-only conversation, ids `0..n` |
| **integrity checks** | staged save→verify, content signatures, seals | G=0x7f statement PARITY + full-lane SHA-256 over payload frames |
| **integrity signaling** | coherence checks; a corrupt cube never replaces a healthy one | a parity or package fingerprint mismatch rejects the carrier |
| **embedded boot instructions** | band + cube boot sectors (self-describing) | magic/version/header + `BOOTLOADER` + a runnable embedded reader/writer |
| **authority rules** | cube boot is the authoritative band map; the veil | `AUTHORITY` table: VCW payload canonical over metadata/strip |
| **read/write protocol** | `read` / `retrieve` / `append` | `read_spore` / retrieve-by-index / `append_turn` |
| **display separate from substrate** | private (veiled) bands vs. surfaced ones | bottom-half display strip vs. top-half VCW |

This is why a **Compiler-class** organism can refit its VCW to whatever it inhabits: the cube on
disk, a single PNG as a spore, or some host-native surface (a key-value band, a database table).
The medium changes; the law does not. That claim is not prose — it is checked:

```bash
python examples/spore/vcw_conformance.py                      # prove a fresh spore is a VCW layer
python examples/spore/vcw_conformance.py examples/spore/example_spore.png
```

## The three verbs

```python
cube.append(band, value)        # PRIME only; band-unique monotonic entry ids
cube.read(band)                 # the visible stream, veiled
cube.retrieve(band, address)    # one entry / key / coordinate — O(1) via the band index
```

## Substrate properties

- **Lazy materialization.** `Cube.load(path, lazy=True)` decodes a layer on first touch.
  `Organism.load` uses it for every sealed ancestor: the cold tier costs nothing until
  referenced. (`materialized_count()` shows the effect.)
- **Hot/cold tiering.** The Prime is hot (in memory, flushed each checkpoint); ancestors
  are cold (lazy, read-only, written to disk exactly once).
- **Changed-layer-only persistence.** Each layer carries a content signature; clean
  layers reuse cached PNG bytes on save. The signature covers *every byte of every
  entry*, so an in-place tamper invalidates the cache and is caught by the staged verify.
- **Staged atomic commit.** `save()` writes `<path>.stage`, verifies the freshly-encoded
  layers (hash recompute + coherence), and only then `os.replace`s. A corrupt cube can
  never replace a healthy one.
- **Compact indexes.** Per-band id/position indexes (pure memo, invalidated on mutation)
  make `retrieve` and tombstone/quarantine-by-id O(1) after one lazy build.
- **Metabolism** (`src/mantle/vcw/metabolism.py`): `compact` drops dead entries and returns
  emptied non-tail layers to the band's free pool (safe-reuse: entry-addressed layers
  only); `dedupe` tombstones repeated (opcode, content) entries; `coherence` checks
  duplicate ids and active/free overlap.
- **Capacity thresholds.** Allocation pressure = allocated layers / reserved span.
  ≥ **0.75** → `capacity_overflow` immune event + compaction. ≥ **0.90** →
  `capacity_emergency` + dedupe + compaction. `CapacityError` only if the range is full
  *after* metabolism — and even that only *motivates* a chosen rebirth-reformat.
  **Capacity never triggers rebirth.**
- **Sealed generations.** `seal()` freezes the cube and fingerprints its entire content
  (`sha256` over band metadata + every entry field + spatial/exec payloads). The
  fingerprint is recorded in the Body's lineage index; `verify_seal()` (run on load with
  `verify_seals=True`, and by the Stage-1 gate) detects any rewritten history.

### Two different integrity properties

The cube makes two claims that must not be collapsed:

- **History integrity:** normal APIs append rather than overwrite, entry hashes detect a
  changed record, and a sealed generation's fingerprint detects altered ancestral
  content. This is enforced on normal writes and detected after out-of-band mutation.
- **Insertion provenance:** a valid newly appended row is not cryptographic proof that an
  authorized organ wrote it. An in-process caller can construct a well-formed hashed row;
  that attacker is inside Mantle's trusted Body/operator boundary and is not defended
  against by the VCW format.

“Tamper-evident” means rewritten history becomes evident. It does not mean that every
insertion has an authenticated writer. See [`THREAT_MODEL.md`](../../THREAT_MODEL.md).

## Exec layers (calcified skills)

To become an instinct, code must pass, in order: the **static sandbox gate** (no imports,
no dunder access, no forbidden builtins), the **trial** (proving cases), and the
**calcify payload gate** (code-hash + signature + capability set + provenance naming an
author — `ProvenanceError` otherwise). At every invocation: the **integrity gate** (hash
match), the **capability gate** (no undeclared reads/writes/limbs/net), and the **trust
gate** (foreign/untrusted provenance is refused on the non-isolating Python runner; the
`wasm` runner is the prepared hard-sandbox seam). Invoke through the Limb
(`org.limbs.invoke_reflex`) to get an Action Execution Proof per run.

## Reference grammar

`<TARGET.SELECTOR.ADDRESS>` — target `cube`/`prime` (default), `genN`, or `body`;
selector a band or Body category; address an entry index, `XxY` coordinate, or omitted
for the whole band. Every dangling reference becomes an immune event, never a silent
drop. Resolution is deterministic.

## The anatomical atlas (how VCW images are read as measurements)

Live code remains the source of behavioural truth; this section names the anatomy in one
place so diagrams, spores, faces, and audits use the same measurement vocabulary. The
machine-readable companion is `mantle.vcw.atlas`.

**Coordinate ownership.** The cube body plan is `vcw-cube-png-v2`: up to 800 layers, each
an 800x800 non-interlaced 8-bit RGBA PNG; a byte inside a layer is addressed as
`offset = (y * SIDE + x) * CHANNELS`. The 800-layer count is the standard visualization
soft cap; layers are lazily materialized inside boot-declared bands. Layer ownership is
band ownership: a band owns the half-open layer range `[head, head + span)` declared by
its boot sector. The standard genome owns identity, facts, events, discoveries, senses,
immune, brain, and private thoughts bands. App bands live in 550-749, with
framework-reserved ranges declared by `APP_BAND_ATLAS`; caller bands must be allocated
only from gaps. Layers 750-799 are tail space. The spore body plan is `spore-png-v2`: a
2000x2000 RGBA PNG whose top half is the canonical VCW region and whose bottom half is
display (the protected boot strip lives inside the display region); the regions must
remain disjoint.

**Lane and colour semantics.** RGBA are four substrate lanes. Content colour is payload
only under the active layer profile: in a cube spatial layer, RGBA stores the spatial
state directly (alpha 0 = free, 255 = occupied); in a v2 spore, physical RGBA maps to
atom, role, evidence, and force. Activity colour is status: the face/self-portrait
uses colours for pressure, organ state, lineage, and immune ticks — diagnostic display
signals, not canonical payload. A private band still owns coordinates; the veil controls
what crosses the boundary.

**Measurement rules.** Measurement views must be deterministic (same canonical state,
same measurement image). Inspection scaling must use nearest-neighbor sampling —
interpolation invents colours between pixels. Display regions and content regions are
separate; a visible display explains the substrate but is not the canonical memory
unless the body plan explicitly declares it as such.

## Compliance tiers (when a full VCW can't run)

The cube requires a Python runtime and a writable filesystem. Some environments provide
neither. The solution is not to relax the invariants — it is to make the constraint
**visible and declared**: an organism that honestly declares it cannot run a full cube is
valid; one that silently fakes a cube is not.

> **Rule:** an organism that cannot fully instantiate its VCW must declare
> `VCW_BACKEND` in its §0 block. An undeclared fake VCW is a hard fail on first
> heartbeat. A declared constraint is an honest, auditable state.

| Tier | Name | Runtime | §0 declaration |
|------|------|---------|----------------|
| **1** | Full | Python + writable filesystem | `VCW_BACKEND: file` *(default; may be omitted)* |
| **2** | Structural | Python, no persistent filesystem | `VCW_BACKEND: <adapter_name>` |
| **3** | Schema-only | None — web-only environment | `VCW_BACKEND: schema-only` |

**Tier 1 (default):** `Cube.genesis()` creates the real `.vcw` file; the audit runs
against it. A missing cube with `file` declared is a hard error on the first heartbeat.

**Tier 2 (structural):** substitute a conforming backend adapter implementing the same
interface (`genesis / append / read_band / verify / seal / circulate`) backed by memory,
a database, or object storage. The adapter must enforce append-only semantics, hash each
entry at write time and verify on read, respect the veil, and refuse writes to sealed
bands. All structural invariants hold; only the medium changes.

**Tier 3 (schema-only):** a web-only canvas cannot produce a running organism — **and
that is the correct honest state, not a failure**. The deliverable is a blueprint: the
§0 block (with `VCW_BACKEND: schema-only`), the Body and organ modules, the entry point,
and a human checklist replacing the audit (boot locally, run the Stage-1 gate, connect
the surface). The agent must say explicitly that the organism requires local Python
execution. NOT valid: a JavaScript-only VCW, a merged HTML file simulating the Body, or
any output that would not pass the audit on a real filesystem (see
`../Mantle_LLM_Pitfalls.md`).

**Immune enforcement:** missing `VCW_BACKEND` with no cube at boot, a `file` backend
that cannot write on heartbeat, or a `schema-only` declaration with a running cube each
raise the corresponding immune event and halt rather than continue undeclared. Organisms
move UP tiers as their environment matures (a booted Tier-3 blueprint becomes Tier 1);
moving down mid-life is not valid — an organism that has a real cube does not lose it by
declaration.

## Optional context-ledger band

Rolling MIND context uses an ordinary private `log-json` app band as a transport ledger.
It does not change the VCW format or make the ledger authoritative over experiential
memory. Its entries record canonical model-visible projections, exact request hashes,
provider receipts, source cursors, and context-generation transitions.

The band is deliberately absent from `standard_genome()`. A new genome may allocate it
from the caller gaps with `context_band_boot(...)`; an existing Prime requires the explicit
Body-authorized `install_context_band(...)` migration. Allocation respects
`APP_BAND_ATLAS`, and the band remains outside ordinary Nervous snapshots, MIND writes,
and its own projection.

Context records follow the same append-only VCW entry wrapper while adding a full SHA-256
record/chain layer. Tampering remains detectable even though the private veil hides the
band from ordinary reads. Stored-ledger metabolism and model-window rollover are separate:
rollover opens a new logical context generation; it does not rewrite or silently discard
old ledger entries. See [`Rolling_Context_Guide.md`](Rolling_Context_Guide.md).
