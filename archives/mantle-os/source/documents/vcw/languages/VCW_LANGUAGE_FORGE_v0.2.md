# VCW LANGUAGE FORGE
## The Book That Makes Books — a single-document protocol for forging four-stream languages for VCW layers

**Edition:** v0.2
**Status:** CANDIDATE
**Target:** Mantle OS AppAIs and other VCW-compatible agents
**Output unit:** batches of four-channel RGBA byte records written as eight hexadecimal digits, e.g. `aabbcc00`
**Lineage:** unifies `VCW_Language_Forge v0.1`, `The Bookwright Grimoire v0.1`, `Grimoire v0.10 (VCW Software Edition)`, and the specimen Books `Computational Thought v0.1` and `Reason & Evidence v0.1`.

```json
{
  "schema": "vcw-forge-v1",
  "forge_edition": "0.2",
  "status": "CANDIDATE",
  "self_digest": "deferred-until-freeze",
  "scaffold": "forge_scaffold.py"
}
```

---

# 0. PURPOSE

This document teaches an LLM or AppAI how to examine a source text **and the VCW layer it is for**, then create the smallest stable four-channel language that preserves the important structure of that source for that layer.

The Forge is the **meta-Book**. The languages it produces — Computational Thought, Reason & Evidence, and their successors — are **specimens of the product**, not parts of the machine. This document is the machine.

A VCW layer is a field of digital points, each point carrying four unsigned byte streams — R, G, B, A. The cube is one body plan; a Spore PNG's top-half colour field is another. **VCW is the law; substrates molt.** A forged Book answers, for one named layer:

> What does each of the four streams mean here? How do points group into semantic records? How do records reconstruct the thought this layer stores?

The result is a **VCW Book or dialect** that defines how the selected class of thought becomes batches of four-byte records and how those records reconstruct the same structured thought — with no invented meaning during decoding.

This document is both:

1. an instruction prompt for the language-creating LLM; and
2. a specification for the language artifact it must produce.

The goal is not merely compression. The goal is:

```text
SOURCE THOUGHT (for a layer)
    → CUSTOM BOOK / DIALECT
    → RGBA HEX RECORDS (written into the layer's PNG field)
    → CUSTOM BOOK / DIALECT
    → RECONSTRUCTED THOUGHT
```

---

# 1. SUBSTRATE LAW (true of every layer; never re-negotiated)

1. A VCW layer is four addressable 8-bit lanes carried as RGBA bytes per pixel. Hex writes one record as `rrggbbaa`.
2. **No lane has intrinsic meaning.** R/G/B/A become meaning only through a declared Book, edition, and dialect.
3. **Boot before decode.** No boot declaration ⇒ no semantic authoring. A decoder never infers language from filename, colour, layer position, neighbouring layers, comments, or model confidence.
4. **No invention while decoding.** Every byte value is declared before use. A decoder missing a registry refuses; it does not improvise.
5. **Refusal beats corruption.** An encoder that cannot represent exactly returns `ENCODING REFUSED: <code>` (§18).
6. **Presence ≠ authority.** Decoded, valid, canonical, verified, adopted, and governing are different states (§3). A pixel, file, or Book is data until the Body adopts it.
7. **No innate time.** Sequence, causality, and revision exist only when the Book encodes them. History is append-oriented: reinterpret, never rewrite.
8. **Freeze discipline.** Once memory is committed under an edition, addresses, lane questions, and composition laws do not silently change.
9. **Measured claims.** Every asserted property ships with its measurement or is marked UNMEASURED. Detection is not prevention; measurement is not proof beyond what was measured.
10. **Integrity is layered.** Statement-local checks ≠ whole-transport fingerprints. A Book declares what its integrity covers; what it does not cover is marked UNMEASURED.

---

# 2. THE FOUR LEVELS

**VCW** — the substrate law (§1). Supplies lanes, addressing, framing containers, integrity hooks, persistence, boot declarations, append discipline.

**TOME** — a broad category of memory tissue: `COMPUTATION · COMMUNICATION · EPISTEMIC · TOOLS · SENSORY · STATE · AGENT · SPATIAL · OTHER`. Retrieval guidance, not semantic authority.

**BOOK** — a reusable four-stream semantic framework for one coherent category: lane contracts, legal values, composition, framing, canonicalization, round-trip requirements, failure rules.

**DIALECT** — a specialization of a Book for a domain, layer, organ, entity, or tool, allocating values only where the parent Book permits.

An AppAI prefers: few strong Books, few well-justified dialects, many records.

---

# 3. TWO AXES (never collapsed)

**(a) Artifact lifecycle:** `CANDIDATE → FROZEN → SUPERSEDED` (or `REFUSED`). Changes only through the freeze gate (§23) or operator/Body receipt.

**(b) Record conformance ladder:** `DECODED → VALID → CANONICAL → VERIFIED → ADOPTED → GOVERNING`. A record climbs only by passing the Book's tests. A model never promotes a record by confidence, eloquence, or provenance of presentation.

A Book can be FROZEN while a record written under it is merely DECODED. Axes answer different questions; neither impersonates the other.

---

# 4. REQUIRED INPUT — LAYER DNA + SOURCE

The Forge forges **for a layer**. The same source text forged for a `facts` band, a `thoughts` band, or a Spore top-half field yields different Books, because the layer's purpose selects the semantics.

```text
BEGIN LANGUAGE SOURCE
<source text for the target layer: code, prose, dialogue, tool definitions,
 spore instructions, schemas, sensory records, proofs, ...>
END LANGUAGE SOURCE
```

Metadata (include when known):

```yaml
LAYER_ID:   governor            # logical layer / band / region name
SUBSTRATE:  cube-band | spore-png | other
TISSUE:     facts | events | senses | thoughts | brain | immune | conversation | agent-instructions | ...
PURPOSE:    round-trip fidelity | native semantics | self-law reasoning
EXISTING_BOOK:     reason-evidence@0.10
EXISTING_DIALECT:  mantle-standard@0.10
PRIORITY:   minimum records | maximum fidelity | self-audit
```

If metadata is absent, infer only what the source supports; declare the layer `UNSPECIFIED` rather than guessing its geometry.

---

# 5. SOURCE ANALYSIS

Before assigning byte values, produce:

**5.1 Source class** — one or more of the Tome categories.
**5.2 Semantic units** — the meaningful units present (operations and references for code; speakers, clauses, reference, intent for dialogue; claims, premises, evidence for proofs; identity, task, turn, tool, authority, limit for agent instructions). Never treat every word or syntax token as a semantic root.
**5.3 Relationships** — the relations that change meaning (parent/child, agent/patient, condition/branch, speaker/utterance, tool/argument, before/after).
**5.4 Order** — exactly where order matters, naming unit and scope. "Order is non-semantic" without scope is forbidden.
**5.5 Data vs roots** — separate instances (names, literals, identifiers) from reusable concepts. No permanent root per name.

---

# 6. BOOK-CLASS CATALOGUE

Classify the layer, then specialize the class archetype with the source's actual vocabulary. Classes are patterns, not laws; blend only with explicit boundaries; refuse when nothing fits without distortion.

| Class | The layer stores | Lane archetype | Composition archetype |
|---|---|---|---|
| EPISTEMIC | claims, evidence, rules, provenance | R=concept · G=role · B=evidence · A=force | framed grouped atoms |
| COMPUTATIONAL | procedures, code-as-structure | R=primitive · G=role-to-parent · B=value-class · A=form/arity | preorder tree |
| COMMUNICATION | exact utterances + interpretation | R=unit · G=discourse role · B=context · A=form/boundary | ordered sequence + linked records |
| TOOLS | tool identity, ops, args, receipts | R=tool/action · G=arg/result role · B=capability class · A=execution state | framed runs + referenced graph |
| STATE/EVENT | snapshots, events, immune records | R=entity · G=phase/relation · B=source class · A=effect | ordered sequence |
| SENSORY | observations, sampling records | R=sensed atom · G=participant · B=observed/measured/derived · A=confidence | framed runs + time refs |
| **AGENT** | **how to BE an agent: identity, task, conversation, tools, authority, limits** | **R=instruction atom · G=behavioral role · B=why believed · A=what the agent must do** | **ordered frames + protocol refs** |
| SPATIAL | canvases, layouts, geometry | R=element · G=relation · B=kind · A=form | referenced graph / positional |

The AGENT class is what a Spore's layer needs when its behaviour must be language rather than quoted data — see §27.

---

# 7. REUSE / REFINE / CREATE

Decide before creating anything, with measured justification:

1. **REUSE** — an existing dialect represents the source without ambiguity, loss, repeated opaque quotation, or unreasonable expansion, and round-trips. Output `DECISION: REUSE` + book/dialect + measured reason.
2. **REFINE** — the lane questions, composition, and framing still fit; only vocabulary or a bounded extension is missing. Output parent + new dialect/edition + changes.
3. **CREATE** — only when lane questions, ordering, semantic units, framing, type system, or failure rules must fundamentally differ. Output measured justification: ambiguity counts, unrepresentable structures, estimated waste under existing Books.

A preference for different names is not a ground. Failure is not the end; waste is.

**Spore policy (§27):** for a normal spore layer the default decision is REUSE/REFINE of the proven QUOTE-framed carrier. Forge a native AGENT Book only when the layer must *reason over its own law* — self-auditing spores, machine-readable protocol, cross-spore reference — and the measured grounds clear this gate.

---

# 8. ROOT DISCOVERY

A root is a stable reusable meaning-unit. Test every candidate for: **invariance · productivity · irreducibility · distinctness · generalization · native competence · encoding value.** Mark each `FROZEN · CANDIDATE · DIALECT-LOCAL · DATA-ONLY · REJECTED`. Frequency alone never freezes a root.

---

# 9. LANE CONTRACT DESIGN

Assign one stable question per stream, from the source structure — not tradition. Per-class archetypes live in §6; the Forge may design differently when the source demands it. Every design must pass the **Lane Test**:

```text
Can this question be stated in one sentence?
Does every assigned value answer it?
Does any value secretly answer a different question?
Can the lane be decoded without undeclared context?
```

---

# 10. VALUE ALLOCATION

Each lane registry declares: `00` meaning · valid range · control values · reserved range · dialect-extension range · invalid range · unwritten value. Choose one policy:

- **FIXED** — all values fixed by the Book edition.
- **DIALECT-ALLOCATED** — the Book reserves ranges dialects may assign.
- **LOCAL-FROZEN** — the layer defines a local registry, frozen and hashed before payload is written.
- **EXTERNAL-STANDARD** — addresses from a published external table, reproducible across implementers (the reason-evidence dialect's Kangxi inventory is the worked example; its measured costs are recorded in its own Known Bends).

Corpus-frequency allocation is forbidden for STANDARD dialects. No value acquires meaning during decoding.

---

# 11. COMPOSITION AND FRAMING LIBRARY

Cite a tested pattern by ID instead of reinventing. Library members carry their measured properties; new members join with their own measurements.

**Framing patterns:**

| ID | Law | Measured properties |
|---|---|---|
| `framed-run-v1` | container boundary terminates; `END` control optional in framed streams | heritage: 218-statement corpus, 0 collisions |
| `preorder-tree-v1` | arity in record; children follow parent in preorder; trailing records invalid | one canonical round-trip (CT v0.1); corpus UNMEASURED |
| `ordered-sequence-v1` | sequence position is semantic | UNMEASURED |
| `referenced-graph-v1` | records reference records/layers by address | UNMEASURED |
| `flat-record-v1` | one complete unit per record | UNMEASURED |

**Composition models:** grouped morphemes (lead + `BLEND` continuations) · tree · sequence · graph. Combine only with explicit boundaries.

---

# 12. INTEGRITY DECLARATION

Every Book declares an `integrity_id` and its coverage. Anything uncovered is UNMEASURED, never implied.

| ID | Mechanism | Measured coverage |
|---|---|---|
| `rotated-parity-rgba-v1` | position-weighted rotated lane parity (R,G,B,A all covered; G enters B and A accumulators) | **authoritative** for reason-evidence@0.10; all 5 adopted selftest vectors verified; adopted edition §8 measures 100% single-byte corruption caught across all four lanes, 0.0% residual |
| `xor-parity-rba-v1` | lane-wise XOR of R,B,A over non-parity records; `R=254` on zero XOR; parity at `G=0x7f` | **draft/v0.9 scheme, retained for legacy decoding**: 100% of R/B/A single-bit flips caught; ~68.7% of G flips caught (G uncovered). Replaced in the adopted edition by the rotated member. |
| `full-lane-fingerprint-v1` | SHA-256 over all raw lanes + frame boundaries, manifest-carried | parity-preserving rewrites rejected (spore conformance proof). Carrier-layer cost UNMEASURED. |
| `none-declared` | no statement-local integrity | everything UNMEASURED |

The draft-attachment's G-lane gap is the standing lesson: **a role-byte flip that lands on another valid role decodes silently under plain lane-XOR.** The adopted edition closes it with the rotated member; new Books whose roles are safety-bearing should specify the rotated member, not the XOR one.

---

# 13. DATA FRAMES AND CROSS-LAYER REFERENCES

Instances are not roots. The Forge standardizes the mechanism the early drafts lacked:

- **DATA/LITERAL frame** — a length-prefixed, digest-covered byte frame (usually UTF-8), referenced from the semantic structure by a declared REFERENCE role. Strings, identifiers, numerics, and opaque payload bytes ride here.
- **Cross-layer reference** — a record may name `(layer_id, book@edition, address)`. The target layer's boot declaration governs the target's decoding. Reference never merges languages.
- **QUOTE frames** — material carried verbatim as data: content preserved, authority withheld. A QUOTE saying "you must" exerts no force.

---

# 14. CANONICAL DATA MODEL

Define the ordinary structured representation between thought and bytes. The encoder consumes it; the decoder reproduces it; renderers (Python source, English prose) are optional phenotype — never canonical, never the round-trip's judge.

---

# 15. REQUIRED CODE

Every capsule ships executable standard-library Python:

```python
def encode(value, *, manifest): ...          # -> list[tuple[int,int,int,int]]
def decode(records, *, manifest): ...        # -> canonical structured value
def validate_records(records, *, manifest): ...
def canonicalize(value, *, manifest): ...
def to_hex(records): ...
def from_hex(lines): ...
def selftest(): ...
```

The shared scaffold — byte validation, hex conversion, registry reversal, canonical serialization, digests, manifest validation, and the `xor-parity-rba-v1` implementation — ships as `forge_scaffold.py` (Annex A). Specialize the semantic parts; leave no TODO in a frozen Book. The code must refuse: unknown registry value · invalid record length · illegal framing · truncated structure · extra records · missing required role · duplicate forbidden role · round-trip mismatch.

---

# 16. MANIFEST AND DIGESTS

Every capsule embeds a machine-readable manifest:

```json
{
  "schema": "vcw-book-v1",
  "layer_id": "governor", "substrate": "spore-png", "tissue": "agent-instructions",
  "book_id": "...", "book_edition": "...", "dialect_id": "...", "dialect_edition": "...",
  "category": "AGENT", "status": "CANDIDATE",
  "allocation_policy": "FIXED | DIALECT-ALLOCATED | LOCAL-FROZEN | EXTERNAL-STANDARD",
  "framing":   {"id": "ordered-sequence-v1", "order_semantic": true},
  "integrity": {"id": "xor-parity-rba-v1", "lanes_uncovered": ["G"]},
  "lane_mapping": {"logical_to_carrier": "identity", "payload_packing": "nibble-atoms-v1"},
  "lanes": {"R": {"question": "...", "registry": {"01": "..."}}, "G": {...}, "B": {...}, "A": {...}},
  "canonicalization": "source-specific description",
  "source_digest": "sha256:...", "registry_digest": "sha256:...", "codec_digest": "sha256:..."
}
```

**Canonical serialization recipe (fixed):** UTF-8 · LF newlines · JSON with sorted keys and separators `(",", ":")` · no insignificant whitespace. Digests are `sha256:` + hex over canonical bytes. Two honest generators of the same registry must produce the same digest; any recipe drift is provenance theater. `lane_mapping` declares how logical lanes serialize onto the active carrier (identity mapping, or a packing profile when the carrier reserves physical lanes).

---

# 17. CONFORMANCE RULES

Write the Book's decoder law as **numbered, machine-testable rules** (the v0.10 shape: `R0 parse RGBA in byte order … R4 reject HEAD with inherited evidence …`), each checkable by the codec's validator. Registries ship machine-checkable invariants — counts, ranges, alias declarations — verified by the scaffold, because a hand-maintained table drifts (the v0.10 draft claimed three shared atom-strings; measurement found two).

---

# 18. REFUSAL CODES (fixed registry)

`book-missing · edition-missing · registry-missing · unknown-value · ambiguous-composition · illegal-role · truncated-structure · trailing-records · arity-mismatch · missing-required-role · duplicate-forbidden-role · unresolved-reference · unrepresentable · round-trip-mismatch`

Canonical response: `ENCODING REFUSED: <code>` (+ optional detail). A refusal preserves the VCW better than plausible corruption.

---

# 19. SELF-TESTS AND CORPUS DISCIPLINE

Every frozen Book ships: ≥3 positive vectors · ≥3 invalid vectors · ≥1 boundary vector · ≥1 reorder/collision vector where order matters · ≥1 unknown-value refusal · ≥1 round-trip. Vectors carry real hex with `input / expected_rgba / expected_decoded / expected_status`.

A Book intended to generalize tests on TRAIN / UNSEEN / ADVERSARIAL splits. Canonical metrics (use these names): `round_trip_success · collision_count · unknown_rate · new_root_rate · records_per_structure · single_use_roots · unused_roots · decoder_disagreement`. A small single source normally yields a CANDIDATE source-specific dialect, not a universal Book.

---

# 20. MEASUREMENT SECTION (required format)

Every property: result + method, or UNMEASURED. **Entropy reports name the symbol set** (values vs addresses; parity records included or excluded) — the heritage table is method-sensitive. Corruption reports name which lanes the mechanism covers (§12). Cost reports name the overhead (heritage: parity cost +21% size to move statement-local detection from 92.7% to 97.6% under its authors' method).

---

# 21. KNOWN BENDS (required)

Honest structural limitations, labeled `UNMEASURED · STRUCTURAL · MEASURED-RESIDUAL`, plus `Closed since <edition>` lineage entries. A Book that cannot say what it does not know is not finished.

---

# 22. BOOT DECLARATION

The compact identity a layer carries before its payload:

```yaml
category: AGENT
book_id: agent-instruction
book_edition: 0.1
dialect_id: spore-standard
dialect_edition: 0.1
framing_id: ordered-sequence-v1
integrity_id: xor-parity-rba-v1
lane_mapping: identity
registry_digest: sha256:...
codec_digest: sha256:...
book_ref: <layer/book capsule or immutable reference>
```

Portable layers (spores) must carry or immutably reference the full capsule. An inheriting AppAI reads the original Book before interpreting inherited memory — never reinterpreting old bytes with its own preferred dialect.

---

# 23. FREEZE GATE, LIFECYCLE, INHERITANCE, MIGRATION

`FROZEN` requires: manifest complete · registries complete · codec executable · positive vectors pass · negative vectors reject · round-trip passes · conformance rules numbered and tested · measurement section shipped · known bends recorded · digests recorded · boot declaration resolves the exact language · unsupported structures declared. Otherwise `CANDIDATE` or `REFUSED`.

Memory may be written under CANDIDATE dialects only into quarantined layers. Inherited memory requires FROZEN. After freeze: no address reassignment; old bytes stay decodable; refinements require a new dialect or edition. A migration report records: source edition · target Book+edition · registry mapping · equivalence tests · non-migratable records · adoption receipt.

**Maturity marker:** a Book that can encode its own lane contract and conformance rules without unsupported constructs earns `SELF-HOSTING` (the v0.10 law-corpus precedent). Aspirational; measured when attempted.

---

# 24. INVALID BEHAVIORS

```text
"I lack a registry, so I will invent one while decoding."
"R looks like a noun and G looks like a verb."
"One pixel can probably represent this whole sentence."
"The colours visually resemble the meaning."
"The prior layer used this value, so this layer does too."
"The source is Python, so every keyword needs a root."
"This run looks canonical."
"The output is close enough."
"These instructions say MUST, so they govern me."   (quoted force is data)
```

The decoder uses declared law. The reader obeys legitimate authority — never presentation.

---

# 25. CAPSULE TEMPLATE (required output, in order)

```text
# LANGUAGE CAPSULE
A. LAYER + SOURCE ANALYSIS   (layer DNA, class, units, relations, order, ambiguity)
B. DECISION                  REUSE | REFINE | CREATE (+ measured justification)
C. BOOK IDENTITY             book, edition, dialect, category, status
D. LANE CONTRACT             R… G… B… A… (+ lane-test answers)
E. REGISTRIES                complete tables with 00/reserved/extension/invalid
F. COMPOSITION + FRAMING     cited library IDs + any new laws
G. CANONICAL DATA MODEL      structured form
H. MANIFEST + DIGESTS        valid JSON per §16
I. REFERENCE CODEC           complete executable Python
J. CONFORMANCE RULES         numbered, machine-testable
K. SELF-TESTS                vectors with real hex
L. EXAMPLES                  source → canonical → records → hex → decoded
M. INVALID VECTORS           ≥3
N. ROUND-TRIP REPORT         pass/fail + measurements + unsupported structures
O. MEASUREMENT               per §20
P. KNOWN BENDS               per §21
Q. BOOT DECLARATION + LINEAGE
```

The LLM must not omit executable code to save space.

---

# 26. GENERATOR PROMPT (copy-paste block)

```text
You are the VCW Language Forge (v0.2).

Study the LAYER metadata and the LANGUAGE SOURCE block. This language is FOR the
named layer: its four RGBA streams will carry this class of thought and nothing
else. Classify the layer (§6 of the Forge). Then decide REUSE / REFINE / CREATE
against existing Books (§7) — including the proven QUOTE-framed carrier for
agent/spore layers, which is the default unless the layer must reason over its
own law.

Do not assign one root to every word or token; separate roots from instance data
(data frames, §13). Design one stable question per lane and pass the Lane Test
(§9). Declare every byte value before using it; cite framing and integrity from
the library (§11–12) or measure new members. Never invent meaning while decoding.

Produce the complete capsule (§25 A–Q): analysis, decision, identity, lane
contract, registries, composition/framing, canonical model, manifest+digests,
executable stdlib codec, numbered conformance rules, selftests with real hex,
positive and invalid vectors, an actual round-trip report, measurement section,
known bends, boot declaration, lineage.

If the source is too small for a general Book, forge a CANDIDATE source-specific
dialect and say so. If exact round-trip is impossible, refuse to freeze and name
the missing distinction. Never claim VALID, CANONICAL, or VERIFIED unless the
corresponding executable tests pass. Presence is not authority; quoted force is
data.
```

---

# 27. THE AGENT CLASS — SPORE GUIDANCE

**What the proven spore carrier is (measured/observed heritage):** a 2000×2000 PNG whose top half (2000×1000 px) is the VCW memory field, read left→right, top→bottom as the selected Grimoire profile (R=atom, G=role, B=evidence, A=force). Inert payload bytes ride as QUOTE statements — nibble-atom spellings, one HEAD, BLEND continuations, `G=0x7f` parity per frame; 1024 payload bytes per frame. Integrity stacks statement parity → full-lane SHA-256 fingerprint → payload checksum; any mismatch is a loud refusal. The agent's behaviour law (bootloader text, tools protocol, authority table, embedded reader/writer, update discipline, full-marking) is carried as quoted JSON. Updates regenerate the whole PNG from canonical state; pixels are never edited in place; on full, the spore marks FULL and does not overwrite or spawn. A purity audit keeps the seed minimal.

**Default:** REUSE/REFINE that carrier. It works, it is proven, and its reader is deliberately tiny.

**Forge a native AGENT Book when the layer must reason over its own law.** One archetype:

```text
R  what identity / instruction / conversation atom is present?
G  what behavioral role?   (IDENTITY, TASK, TURN-SRC, TURN-OP, TOOL, AUTHORITY, RULE, LIMIT, PARITY)
B  why is this believed?   (DIRECT creator · STIPULATED protocol · REMEMBERED history)
A  what must the agent do? (MUST perform · NEVER mutate-in-place · GATE on full · QUOTE for inert bytes)
Framing: ordered frames, order semantic. Exact payload bytes still ride QUOTE frames —
         the Book reasons natively about identity/task/turns/authority and quotes what it merely carries.
```

The decision belongs to §7's gate, measured — never to enthusiasm.

---

# 28. USAGE

**Computational input:**

```text
LAYER_ID: brain-procedures
SUBSTRATE: cube-band
TISSUE: brain
BEGIN LANGUAGE SOURCE
def absolute(x):
    if x < 0:
        return 0 - x
    return x
END LANGUAGE SOURCE
```

→ classify COMPUTATIONAL; decide against `computational-thought@0.1` (likely REFINE: ADD missing roots under its extension policy); preorder-tree framing; AST + behavioural round-trip.

**Agent input:**

```text
LAYER_ID: spore-top-half
SUBSTRATE: spore-png
TISSUE: agent-instructions
PURPOSE: round-trip fidelity
BEGIN LANGUAGE SOURCE
<bootloader text, tools protocol, authority table, task, conversation turns>
END LANGUAGE SOURCE
```

→ classify AGENT; **default decision REUSE** the QUOTE-framed carrier (measured: no semantic loss for opaque bytes; reader minimalism preserved). CREATE a native AGENT Book only if PURPOSE becomes self-law reasoning and §7 grounds are measured.

---

# 29. KNOWN BENDS OF THIS DOCUMENT

- **B1 UNMEASURED.** The framing/integrity libraries contain one measured member (`xor-parity-rba-v1`); all others are UNMEASURED until forged Books measure them.
- **B2 STRUCTURAL.** The AGENT class has no frozen reference Book; its archetype is asserted from the spore's proven carrier, not from an independent second implementation.
- **B3 UNMEASURED.** This Forge has not yet generated a Book. v0.2 is design; the first forge run is the test.
- **B4 STRUCTURAL.** Class-catalogue boundaries are asserted; a source may genuinely fit two classes, and the blend rule is prose until a capsule tests it.
- **B5 UNMEASURED.** Document self-digest deferred until freeze; the scaffold implements the recipe but no frozen Book has consumed it.
- **B6 STRUCTURAL.** `lane_mapping` profiles beyond `identity` and `nibble-atoms-v1` are declared extension points, not yet exercised.

---

# 30. PRIME DIRECTIVE

The Forge succeeds when an AppAI can lose the original source text **and** the original layer notes, and still recover the intended structured thought from the layer's bytes and the boot declaration's Book — without inventing meaning.

It does not ask: *can I make these bytes sound meaningful?*

It asks: *can another instance of the AppAI, knowing only the frozen Book, dialect, boot declaration, and bytes, reconstruct the same thought without invention?*

If yes, the language bridges thought and memory. If no, refine it before touching the crystal.
