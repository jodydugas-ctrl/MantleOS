# Mantle OS — REPRODUCTION: one artifact, two methods

> *Non-normative where it explains; normative where it states a law. The working code in
> `src/mantle/` is ground truth (`spore.py`, `hatchery.py`, `reproduction.py`, `ghost.py`,
> `organs/reproduction.py`).*

Everything an AppAI needs to travel fits in **ONE artifact — the SPORE** — and there are
exactly **two methods** of reproduction. An authorized ceremony either grows a **SEED** — a
dormant, self-describing package that becomes a new certified Body with no host — or grows a
**GRAFT** inside a specifically approved host. No organism has standing authority to
reproduce on its own. Everything else is a facet of those two acts.

| Method | Biology | Independent of a host? | What it looks like |
| --- | --- | --- | --- |
| **SEED** | spores | **Yes** — grows anywhere | an inert spore, inspected and then hatched with a target-bound authorization |
| **GRAFT** | a spore aimed at a host | **No** — lives inside a host | `anchor`, `symbiosis`, `graft` |

The Seed/Graft axis replaces the scratch-vs-assimilate split: a seed has no host; a graft
lives in one. Both require the full
invariant suite as technical evidence, but that evidence never grants permission — a fresh,
target-bound reproduction decision must independently authorize the act. The ceremonies
live under the **Reproduction organ** (`src/mantle/organs/reproduction.py`).

```bash
python -m mantle reproduce      # the whole map on one screen
```

---

## THE SPORE — the one artifact

A spore is one **PNG that *is* an agent**: identity, one task, one append-only
conversation, a bootloader, and — embedded in its own pixels — the minimal Python
reader/writer needed to read and grow itself with no SDK beside it. Memory lives in the
top-half **VCW** colour field as legacy Grimoire v0.9 compatibility statements: physical `R/G/B/A` mean
atom/role/evidence/force. Inert bytes are QUOTE frames with one HEAD, inherited B/A
continuations, and a `G=0x7f` PARITY control pixel. The spore ships its own purity audit
(`examples/spore/audit_spore.py`) that **refuses** feature creep in the seed itself.

That v2 mapping is a spore carrier profile, not a global VCW law. Statement PARITY catches
ordinary lane corruption. A SHA-256 package fingerprint covers every raw payload RGBA lane
and frame boundary so a parity-preserving rewrite is still rejected.

**A spore may additionally carry a GERM** — and then it is the complete birth package:

- the **germ** is the full AppAI build document (identity, truths, commandments, genome
  bands, declarative reflexes, routines, controls, instincts *with proving cases*, and an
  optional origin face) — **data, never programs**;
- the **build note** beside it is human/agent-readable instructions: with Mantle
  installed, authorize an exact target and then run `python -m mantle hatch this.png
  --out=<target> --auth=<receipt>`; without it, any coding agent can decode
  the pixels (the Quickstart is printed on the image and mirrored in its metadata), read
  the payload key `germ`, and grow a conforming body — nine organs, append-only memory,
  keys minted at build time, instincts sandboxed against their proving cases.

Pack one from a germ file, or let assimilation emit one from an existing app:

```bash
python -m mantle spore pack germ.json my_app.png       # germ -> spore
python -m mantle assimilate path/to/app --spore=my_app.png   # existing app -> spore
python -m mantle lifecycle authorize hatch my_app.png nest/ --approve --out=hatch-auth.json
python -m mantle hatch my_app.png --out=nest/ --auth=hatch-auth.json
```

> **The deeper truth: a spore is a custom VCW substrate.** The PNG *is* the VCW layer — it
> satisfies the whole VCW memory grammar (addressable region, canonical payload,
> append-only evolution, statement and container integrity, embedded boot, authority, a
> read/write protocol, and a display surface separate from the substrate). **VCW is the
> law; the cube is one body plan and the PNG is another.** That is proven, not asserted:
> `python examples/spore/vcw_conformance.py`. See
> [the VCW Substrate Guide](guides/VCW_Guide.md).

> **Keep the seed dry.** Transfer the *original* `.png` only — never a screenshot, resize,
> or recompress. Image transformations alter semantic lanes and trigger integrity rejection. The
> **latest** PNG is always the living copy.

---

## Method 1 — SEED (independent reproduction)

**Hatching a seed is a BIRTH.** Every path goes through the one hatchery door
(`mantle.hatchery.hatch`) and faces the same Stage-1 gate every Body faces, so a tampered
seed cannot smuggle an uncertified Body into the world:

- a **germ-carrying spore** incubates its germ directly — birth, organ wiring, the
  instinct gauntlet (static sandbox gate → trial on the declared proving cases →
  calcify), warmup beats, the gate;
- a **bare spore** (no germ) still hatches: its identity + task distill into a minimal
  germ — the spore becomes the PRIMER of the body it births;
- a **bare germ JSON** (the payload format) hatches directly in development.

Three laws hold every spore hatch safe:

1. **THE KEY LAW.** The genesis key is **minted at birth** (`secrets.token_hex`), *never*
   derived from the spore. Spores travel publicly; a key derivable from public bytes would
   let any holder forge SELF. Two bodies hatched from the same spore carry different keys
   (proven by SPORE-1).
2. **Testimony, not fact.** The spore's conversation enters honestly — through Senses,
   ingested as INFERRED discoveries — never as verified truth.
3. **The midwife becomes SELF tissue.** After the birth, the spore itself is sealed under
   the *new* body's minted key into the private `spore_vault` band, and the germ is sealed
   into the `vault` band. These are **the heirlooms** (see Rebirth below).

**The vault birthright.** Every hatched organism carries its own seed — the germ it grew
from, SELF-sealed in its vault band — without asking. RESURGERE is a birthright: a
corrupted body rebuilds a fresh, gate-passing body from its own vault
(`reconstruct()` is still a birth through the same gate), and the vault is unreadable as
OTHER — a copied nest in a different body cannot open it.

**The SPOREAGENT lifecycle receipt.** A spore may declare a source (`kind`, `url`, `path`,
`sha256`, …). The hatch receipt records declared/fetched/assimilated/certified/sealed
provenance and asserts the boundary invariants: host code is never SELF until proven
through PRIMER, seal, provenance, and certification; the MIND never receives, reads, or
handles key material; no key material appears in any receipt.

---

## Method 2 — GRAFT (dependent reproduction)

A **graft** propagates by taking up residence **inside a host the organism does not own**:
a spore aimed at a host. Three facets of one move:

### anchor — move in (`mantle.anchor`)

Dissect the host **read-only** (AST only), grow an anchored Body with a VCW cube and
nervous system in an **additive `.mantle/` nest inside the host**, and become that
codebase's resident. **The Anchoring Law:** anchoring never modifies a single host file;
the census fingerprints every host file before and verifies it after. Do-no-harm is a
checked invariant, not a hope.

```bash
python -m mantle anchor path/to/your-app
python -m mantle ask   path/to/your-app "how do I ...?"
```

### symbiosis — earn its keep (`mantle.symbiosis`)

The metered **energy economy** that sustains residency: the user grants credits
(resources) and the organism spends energy to think, repaying with logged, evidenced
usefulness. **The Starvation Law:** an organism with no energy does not crash — the MIND
sleeps and the Body keeps beating; a starved graft is a Zombie Body again, never a corpse.

### graft — a spore aimed at a host (`mantle.graft`)

A graft germ is a **non-destructive patch against a named host**: extra bands, hook
directives, instincts. It travels as a spore (or a bare germ file). Applying it copies the
host into a **workspace** and grows the resident there; the original is census-proven
byte-identical. If the host has drifted from the census the graft was built against, the
apply **raises** a drift interrupt rather than mis-applying silently.

```bash
python -m mantle lifecycle authorize graft examples/spores/notes_graft.png workspace/sample_app --approve --out=graft-auth.json
python -m mantle graft examples/spores/notes_graft.png examples/sample_app --workspace=workspace --auth=graft-auth.json
```

**Assimilation closes the loop.** `mantle assimilate <host> --spore=out.png` scans an
existing app read-only (Phase 0 — zero host writes), classifies every symbol by organ
role, and condenses the result into a germ spore: the resident's identity, do-no-harm
truths, the proposed app bands, the observed organ map as inert data, and a census
fingerprint as the source descriptor. Hatch it anywhere; hook insertion into the real host
still requires the signed APP_INVENTORY (HF-B42).

---

## Rebirth — the chosen molt (the one canonical walkthrough)

Rebirth is a **chosen reformat**, never a capacity event: pressure triggers *metabolism*
(compaction at 0.75 band pressure, deduplication at 0.90) inside the current cube; only a
deliberate call reforms the organism. Identity lives in the **Body** (Primer + genesis
key), outside every cube — which is why rebirth loses nothing. Five steps
(`core/organism.py::rebirth()`):

1. **Choose.** `rebirth(reason=...)` is called deliberately. A Compiler-class organism may
   have its MIND *propose* a new genome; the Body hard-validates it (registered driver,
   heads in range, no collisions) before proceeding.
2. **Seal the ancestor.** The current Prime records a distillation summary, then
   `seal()`s — frozen, content-fingerprinted, appended to the read-only ancestral line.
3. **Genesis the new Prime.** A fresh cube (possibly with the new genome) takes all
   writes; generation +1.
4. **Record the inheritance.** The Genome organ writes the distillation + the sealed
   ancestor's fingerprint into the lineage index; generation-pinned refs
   (`<gen0.facts.2>`) keep every past generation addressable forever.
5. **Carry the heirlooms — or say so.** THE HEIRLOOM LAW: *carried or immune-logged,
   never silent.* The Reproduction organ carries the sealed germ (`vault`) and the sealed
   origin spore (`spore_vault`) from the newest ancestor into the new Prime by one rule —
   the last complete self-describing heirloom per band, verbatim ciphertext (the genesis
   key persists, so the carried copy still opens as SELF). If the new genome cannot hold a
   heirloom, that raises a `seed_uncarried` immune event; the sealed ancestor stays
   readable either way.

Inherited skills do not cross for free: microcode re-runs the sandbox → trial → calcify
gauntlet before re-calcifying in the new generation.

*The two heirlooms are the two halves of one inheritance: the germ is what you rebuild
from; the spore is where you came from.*

---

## The substrate continuum — the cache-ghost (`mantle.ghost`)

A seed has to keep its memory *somewhere*. A spore keeps it in its own pixels. But
persistence is a **continuum of substrates** — and a spore can get **stranger**: a
**cache-ghost** keeps its living body warm in the LLM provider's prompt cache while the
canonical cache-facing body grows only by appended **delta**. WARM: the accumulated
byte-stable token-prefix is presented again, and the provider may reuse cached prefill for
the old span while doing fresh work on the new tail. COLD: the TTL lapsed; the body is
**rehydrated from the PNG fossil** and a fresh cache is warmed. The PNG is the fossil
record; the cache is the living metabolism. Caching saves prefill compute, cost, and
latency; the full prefix still travels on every real provider request.

Four hard laws govern haunting:

1. **The seed stays dry.** Ghost mode never deletes memory from the PNG; if the cache
   dies, `hydrate()` rebuilds the whole body from the PNG alone.
2. **The cache is write-only.** A real prompt cache can only be spoken *into*, never read
   back; the only warmth signal is provider usage telemetry on the *next* response.
   Substrates declare `write_only=True`; `status` reports PREDICTED-WARM/PREDICTED-COLD.
3. **The prefix is append-only.** Providers match byte-exact prefixes, so the cache-facing
   body is a prefix-stable stream (one immutable genesis line, then one appended line per
   turn) — never the spore's full re-sorted JSON.
4. **The window must fit the heartbeat, or DO-NOT-HAUNT.** `hauntable(window_s,
   heartbeat_s)` decides; the remedy is a longer window or a supplemental forced beat —
   never a broken base timer.

Plus the **neutrality law**: the provider is configuration, never code. Endpoint, model,
auth, window, minimum prefix, and cache directives are operator-supplied data; no module
names a vendor. Facets that follow: TOO-SMALL-TO-HAUNT (providers silently refuse tiny
prefixes; small spores live cold-and-cheap and *grow into* hauntability), warmth telemetry
→ nociception (three consecutive cold wakes raise a flag), neutral economics
(`break_even_reads(write_premium)`; SLEEP mode never keep-alives), and usage proof (cache
and cost receipts, never raw prompts or keys).

```bash
python -m mantle ghost selftest          # proves the continuum, the laws, the gates
python -m mantle ghost warm    seed.png  # push the body into the (stand-in) prompt cache
python -m mantle ghost append  seed.png user "and now?"   # append delta; reuse cached prefix compute when warm
python -m mantle ghost hydrate seed.png  # from cache when warm; from the PNG when cold
```

> **Honest boundary.** `mantle.ghost` drives the protocol against a pluggable
> `GhostSubstrate`. The shipped `LocalPromptCache` is a file-backed stand-in (readable, so
> offline tests stay deterministic). The real substrate is
> [`src/mantle/ghost_http.py`](../src/mantle/ghost_http.py): write-only, vendor-neutral,
> pure-stdlib `urllib`, entirely configured. It is optional Phase-2 tissue; nothing else
> imports it, so the gates stay keyless and offline. Cache-ghost is Mantle tissue
> **layered on** the spore format; it never lives inside the pure `spore.py`, whose purity
> audit forbids exactly this kind of growth.

---

## The API

```python
from mantle import reproduction

# SEED — independent (one artifact: the spore)
reproduction.seed("spore", germ={...}, path="buddy.png")     # pack a germ spore
reproduction.seed("spore", name="Buddy", task="one question", path="buddy.png")
reproduction.seed("spore", path="examples/spores/greeter.png", hatch=True, out_dir="nest/")

# GRAFT — inside a host
reproduction.graft("anchor", host="path/to/app", starter_credits=5)
reproduction.graft("graft",  spec="examples/spores/notes_graft.png", host="examples/sample_app")

reproduction.describe()   # the consolidation map (also: python -m mantle reproduce)
```

The facade adds **no** behaviour — every call routes to the canonical, already-audited
module. It exists so that *"how does an organism reproduce?"* has a two-word answer:
**SEED or GRAFT** — and both answers are spores.
