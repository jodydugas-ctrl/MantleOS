# The VCW Substrate — Teaching Guide (Mantle OS)

*One sitting, concepts → bytes → code. The normative companion is
[`vcw_cube.py`](vcw_cube.py) in this directory — a standalone, pure-stdlib implementation
whose docstring defines the format field by field. The production engine is
[`src/mantle/vcw/`](../../src/mantle/vcw/). When prose and code disagree, the code is ground truth.*

---

## 1. Why memory is pictures

The VCW ("Visual Cortex Workspace") cube stores an AppAI's whole experiential memory as a
booted substrate: a standard **800×800×800** body plan made of real PNG layers, each
800×800 RGBA, inside a ZIP. The 800-layer shape is the canonical visualization soft cap;
layers are created only when a band needs them. Not "like" images — actual, valid PNGs you
can open in any viewer (`python vcw_cube.py extract …`). The point is *inspectability as a
property of the substrate*: an organism whose memory is pictures cannot have invisible
memory. A spatial band (the calendar driver) takes it literally: data IS colors at
coordinates.

Memory doctrine, in one breath: **if it's not in the VCW, it didn't happen** — so the
cube is append-only, every entry is hashed, every read is veiled, every save is verified
before it can replace the previous truth, and every retired generation seals with a
tamper-evident fingerprint.

Here “tamper-evident” has a narrow meaning: changing an existing entry or sealed
generation is detected. Hashing does not authenticate the organ that inserted a new,
otherwise-valid row; that would require writer attestation outside this format.

## 2. The anatomy of a cube

```
.vcw (ZIP)
├── cube.json            the cube descriptor: bands, layers, free pools, ids, seal
└── layers/NNN.png       every ACTIVE layer (bands materialize layers on demand)
```

A **band** is a named reserved range of layers, self-described by a **boot sector**
(head, span, purpose, encoding/driver, params, private flag). The standard genome
reserves eight: `identity` 100 · `facts` 150 · `events` 200 · `discoveries` 250 ·
`senses` 300 · `immune` 400 · `brain` 450 · `thoughts` 500 (private). App bands live in
550–749. Identity (the Primer) is **never** in the cube — it lives in the Body, which is
why rebirth loses nothing.

Two-level encoding: the boot-sector format is fixed and universal (the Body always knows
how to read it); the *payload* format is programmable — the boot sector names a driver or
carrier profile (`log-json`, `keyvalue`, `calendar-spatial`, `exec`, or an explicit
Grimoire edition such as `grimoire-v0.9` or `grimoire-v0.10`).

RGBA are the four substrate lanes, not a universal meaning. A layer can boot them as log
bytes, spatial state, repair-protected spore payload, tool/database state, or Grimoire
software lanes such as `R=atom`, `G=role`, `B=evidence`, `A=force`. VCW is the hardware
and boot map; the Grimoire is software that may run on that hardware.

## 3. The entry — the atom of experience

```json
{"id": 7, "ts": 1760000000.0, "opcode": "SENSE", "author": "BODY",
 "source": "webhook", "content": {...}, "tombstone": false, "quarantined": false,
 "hash": "9f2c4a1d03b7e851"}
```

The **hash rule is total**: sha256 (first 16 hex) over *every* field except the four
volatile ones (`id`, `tombstone`, `quarantined`, `hash`), serialized compact + key-sorted.
Extra fields like `authorship` or `verified` sit *inside* the hash — "what your organ
does, you have done" is enforced by arithmetic, not convention. `id` is band-unique and
monotonic (assigned at append, never reused), so marks survive layer reuse.

## 4. The four rules (read `vcw_cube.py` §"THE FOUR RULES")

1. **Append, never overwrite.** New knowledge = a new entry at the band's tail. When the
   tail layer fills (`max_entries_per_layer`), the band grows onto the next layer in its
   range — preferring a recycled layer from its free pool.
2. **Read through the veil.** `read(band)` returns only visible entries; private bands
   return `[]` unless deliberately revealed; tombstoned/quarantined entries never
   surface — from `read`, `retrieve`, or context assembly.
3. **Verify before trusting.** `verify()` recomputes every hash and checks coherence.
   `save()` is a **staged commit**: write `.stage` → verify the staged bytes → atomic
   `os.replace`. A corrupt cube can never replace a healthy one.
4. **Sealed means sealed.** `seal()` freezes a generation and fingerprints its entire
   content (every field of every entry — a tamper that leaves a stale hash behind still
   breaks the seal). Sealed ancestors refuse writes forever and stay addressable via
   generation-pinned references (`<gen0.facts.2>`).

## 5. Logical addressing & references

An entry's logical address is its index into the band's **visible stream** — stable under
physical layer reuse. The organism-level grammar is `<TARGET.SELECTOR.ADDRESS>`:
`<facts.11>` (Prime), `<gen2.senses.0>` (an ancestor), `<body.immune.1>` (the Body),
`<calendar.23x33>` (a coordinate). A reference that resolves to nothing is **dangling**
and must become an immune event — never a silent drop.

## 6. Metabolism and the capacity doctrine

"Failure is not the end; **waste** is." Tombstoned entries are food: `compact()` drops
them and returns emptied non-tail layers to the band's free pool; `dedupe()` (engine)
tombstones repeated `(opcode, content)` entries. The engine fires this automatically as
**pressure** (allocated layers / span) crosses **0.75** (`capacity_overflow`) and
**0.90** (`capacity_emergency`) — and *never* triggers rebirth. Exhausting a range even
after metabolism may *motivate* a chosen rebirth-reformat; it can never force one.

## 7. Exec layers — learning that became instinct

An `exec` band holds one calcified skill: `{code, code_hash, entry, signature,
capabilities, limits, provenance}`. To get there, code passes the **static sandbox gate**
(no imports, no dunders, no forbidden builtins), the **trial** (proving cases), and the
**calcify payload gate** (hash + signature + capability set + provenance naming an
author). At each invocation: integrity (hash match), capability (no undeclared access),
trust (foreign provenance refused on the non-isolating Python runner; `wasm` is the
prepared hard-sandbox seam). Calcified skills run with **no MIND** — they are the Body's
own reflexes.

## 8. From this file to the living organism

Everything above is substrate. The organism around it — the eight contracted organs, the
SignalBus, the heartbeat, the gates, the bounded MIND, the assimilator — lives in
[`src/mantle/`](../../src/mantle/) and is documented in [`documents/guides/`](../../documents/guides/). Start with
`python -m mantle demo`, then `python -m mantle audit`.

The promise this guide can make, because CI enforces it: **what `vcw_cube.py` defines,
`src/mantle/vcw/` implements, byte for byte** (`python interop.py`).
