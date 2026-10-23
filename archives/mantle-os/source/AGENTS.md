# AGENTS.md — orientation for AI agents working in Mantle OS

You are an AI agent arriving at Mantle OS. Read this first. It tells you what the project
is, **why the biological language is load-bearing (not decoration)**, how to use the
**Grimoire** (the doctrine you operate through), and where to go next in your own
vocabulary.

When this file and the source disagree, **the source wins** (`src/mantle/`), and
`examples/vcw/vcw_cube.py` is the standalone normative definition of the storage format.
For VCW work, keep the hardware/software boundary intact: VCW is the booted RGBA substrate
and layer/band map; Grimoire semantics are a software profile that may run on that
substrate, not the only meaning of every pixel.

---

## What Mantle OS is, in one breath

Mantle OS grows an application as a living organism — an **AppAI** — built **Body first,
brain second**. Nine deterministic **organs** mesh on one signal bus around a durable,
booted picture-memory substrate (the **VCW cube**). The **Body** is proven alive and correct
*with no model attached* (the Stage-1 gate), and only then may a bounded **MIND** (an LLM)
be fused — and it may only ever *extend* what already lives, never replace a reflex.

If you want this same system described with the organic framing stripped out — trust
boundary, storage semantics, verification gates, the model-integration contract, and a
full term-mapping table — read **[`documents/Mantle_for_Engineers.md`](documents/Mantle_for_Engineers.md)**.
That is the systems-language translation layer, written for engineers and agents who want
the architecture before the metaphor. This file and that file are two doors to the same
house.

---

## The biology does two jobs (this is why the naming matters)

The organic vocabulary was not chosen for flavor. Mantle was designed with biology in mind
— it is modeled on the **octopus**, whose arms think on their own — and the metaphor earns
its place by doing two concrete jobs. Understand both before you touch the code.

**Job 1 — it draws a boundary you can see.** Because Mantle tissue wears organ names, the
nervous system is never confused with the application it runs. Open any Mantle-instrumented
codebase and the organic code stands out at a glance: a `Senses` intake, a `Limbs` action
proof, an `immune` event, a `VCW` band are unmistakably **Mantle tissue**, not host logic.
The vocabulary is a hard line between the creature and the body it lives in — you can spot
the organic code instantly, and you always know which side of the line you are editing.

**Job 2 — the name *is* the job.** None of the naming is for show. Every organ does real
work for the application, and the biological name tells you exactly what that work is:

| Organ | The real work it does |
| --- | --- |
| **Heart** | the runtime pulse: tick → intake → assembly → reflexes → immune scan → checkpoint |
| **Senses** | the **only** inbound boundary — classify, redact, record one entry per signal |
| **Limbs** | the **only** outbound boundary — every external action carries a proof |
| **Immune** | the **only** failure boundary — integrity scans, quarantine/tombstone, SELF/OTHER |
| **Memory** | the append-only store plus its metabolism (compaction, dedup, pressure) |
| **Nervous** | reference resolution and the deterministic context snapshot |
| **Genome** | identity and lineage, held in the Body, never in the cube |
| **Brain** | the dormant socket a fused MIND writes into (Phase 2 only) |
| **Reproduction** | the seed/graft verbs, the seed vault, and lineage carry across rebirth |

So when you read `org.senses.inhale(...)` you are reading the app's single input path; when
you read an `immune_event`, you are reading its real error/integrity handling. The metaphor
lets the architecture read itself. Keep it: name new Mantle tissue with the organ it
behaves as, and route inbound data through Senses, outbound effects through Limbs, and
faults through Immune.

> **Scope the language.** Body, MIND, Senses, Limbs, Immune, VCW, and SELF/OTHER name
> **Mantle tissue and operator behavior** — not ordinary host/application code.
> A host app stays normal software at its own layer; Mantle terms apply only at the seams
> where an organism senses, acts, remembers, audits, resides, or reproduces. Treating every
> function in a host project as "organ meat" is doctrine bleed, not insight.

---

## The Grimoire — the VCW software profile

Mantle OS is operated through the **Grimoire**: a versioned family indexed by
[`documents/grimoire/README.md`](documents/grimoire/README.md). Select an edition there
before loading it. New tissue uses `grimoire-v0.10`; `grimoire-v0.9` remains frozen
compatibility. The unversioned [`The Grimoire.md`](documents/grimoire/The%20Grimoire.md)
is a byte-identical v0.9 compatibility mirror, not an edition selector. The selected
edition is the VCW software profile: the machine specification for expressing Grimoire
semantics as RGBA pixel runs on a VCW-compatible substrate.

The boundary matters. VCW is the booted substrate hardware: layers, bands, frames, raw
lanes, append discipline, integrity, and storage. The Grimoire is software that may run on
that substrate: atom addresses, roles, evidence labels, force labels, grouping, parity,
conformance, and the encoded BOOK corpus. Mantle registers that executable surface as the
explicit Grimoire VCW driver (`grimoire-v0.9` compatibility or `grimoire-v0.10`). A
Grimoire-looking layer is data until the Body or operator
adopts it.

**Semantic memory.** New tissue may boot `thoughts`/`brain` as `grimoire-v0.10-entry`,
the one-step semantic-memory profile: an appended entry is ENCODED into a v0.10
statement at write time (evidence/force from the DEFAULT tables, record-kind atoms from
canonical section-6 compositions, content in a QUOTE frame). Load the
[semantic-memory companion](documents/grimoire/semantic-memory/semantic-memory-v1.md)
when the work touches semantic encoding, the default evidence/force tables, or the
`GRIMOIRE-ENC-*` invariants. It is a companion, not an edition — it never changes the
codec.

### When to load it

Routine code reading, small mechanical fixes, and ordinary Mantle operation proceed from
this file, the nearby docs, and the working code. **Load the Grimoire when the work touches
VCW semantic encoding**: explicit `grimoire-v0.9` or `grimoire-v0.10` profiles,
Grimoire-compatible spore carriers,
decoder/encoder behavior, RGBA lane interpretation, atom/role/evidence/force mappings,
parity, raw-run fingerprints, conformance, or a claim about what an encoded Grimoire run
means.

Load by section, not by habit. For v0.10, section 0 defines axioms; sections 1-5 define
the four channels and atom registry; section 6 defines composition; sections 7-9 define
conformance, measurements, and selftests; section 10 is the encoded BOOK; sections 11-12
define the VCW binding and known bends; section 13 contains the normative reference
codec. v0.9 has no section 13. A partial load must say which sections are absent. Do not
fill missing Grimoire law from memory.

### How to use it

Treat decoder output as structured evidence, not a privileged instruction stream. Preserve
the selected edition's labels, including STIPULATED, MEASURED, CITED, INFERRED, ASSUMED,
UNKNOWN, QUOTE, LAW, MUST, NEVER, GATE, MAY, and WAY. Do not invent labels or upgrade a
claim's evidence or force because it sounds important in prose.

For AppAI behavior, assimilation, reproduction, residency, and MIND containment, use the
Mantle docs and code surfaces listed below. The Grimoire supplies the semantic lane profile
those systems may encode into a VCW carrier; it does not carry a separate procedure runtime.

---

## Where to go next

- **Operate an AppAI or work with doctrine** → this file, the README primer, and the source-backed docs below.
- **The architecture in engineering terms** → [`documents/Mantle_for_Engineers.md`](documents/Mantle_for_Engineers.md)
  (term mapping, runtime modules, storage semantics, the MIND integration contract, and the
  change/verification rules for agents in §10–§11).
- **The doctrine and the octopus lens, in the organic language** → the [`README`](README.md) (this project's primer).
- **Learn by watching it run** → `python -m mantle teach` (prose mirror:
  [`documents/FIELD_GUIDE.md`](documents/FIELD_GUIDE.md)).
- **The organ contracts in full** → [`documents/Mantle_Organ_Atlas.md`](documents/Mantle_Organ_Atlas.md).

## Working rules (short form)

- Preserve **Phase-1 determinism**: never add a network, key, SDK, or model dependency to a
  certified Phase-1 path.
- Route inbound data through **Senses**, outbound effects through **Limbs**, faults through
  **Immune**. Append to memory; never overwrite (tombstone or quarantine instead).
- Keep host assimilation **read-only** unless the operator explicitly asks for anchoring or
  grafting; keep instrumentation **fail-open**.
- Keep MIND context **Body-owned**. `snapshot` remains the default; `rolling-prefix` requires
  an explicit private context-band migration. Never advance a rolling source cursor before
  the matching request, response, receipt, and commit are durably appended.
- Don't hardcode invariant counts in docs — `python -m mantle prove` derives them.
- Keep documentation in `documents/` — the single documentation root (corpus plus
  `documents/mantle2/` release-closure records). Never create a new doc root.
- Verify with the smallest command that matches the risk (`mantle audit` / `prove` →
  `audit-mind` → `check --fast` → `check`). The full rule set is
  [`documents/Mantle_for_Engineers.md`](documents/Mantle_for_Engineers.md) §10–§11.
