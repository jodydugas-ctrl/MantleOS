# Semantic Memory — one-step thought-and-storage encoding

**Non-edition declaration.** This document is a **companion**, not a Grimoire
edition. It does not change the codec, the atom registry, the role/evidence/force
tables, or any composition row of the frozen `grimoire-v0.10` edition. The frozen
editions (`editions/grimoire-v0.9.md`, `editions/grimoire-v0.10.md`, `The Grimoire.md`)
are never edited by this profile. Verify that claim with:

```bash
python tools/grimoire_tool.py verify documents/grimoire/editions/grimoire-v0.10.md
python -m mantle prove
```

Status: **adopted for new tissue** (operator receipt `semantic_memory_adoption`).
Scope: **new-tissue-only**. No existing organism or carrier is migrated.

---

## 0. What this is

The one-step contract: a MIND reflection (or any Body record) is appended as **one
entry-shaped record**, and the append itself encodes the record into a Grimoire v0.10
pixel run. Thought and storage are one operation; the driver does the encoding; the
organism's API never changes.

```
MIND reflection / Body record (structured meaning)
        |
        v  ONE append call  (drivers.GrimoireV010EntryDriver -> semantic.encode_entry)
Grimoire v0.10 statements: structural run + content QUOTE frame, paritied
        |
        v
VCW band (PNG layer) -- hashed, veiled, retrievable, metabolizable
```

The driver is `grimoire-v0.10-entry`. The default genome boots it on `thoughts` and
`brain` (the MIND write surface); every other band stays `log-json`.

## 1. The two framed runs (design decision DD-Q)

The v0.10 decoder enforces **exactly one HEAD per statement**, so the structural
semantics and the content payload cannot share one run. Each semantic record therefore
carries **two framed runs**:

| field | what it is | integrity |
| --- | --- | --- |
| `semantic.raw` | the structural v0.10 statement: record-kind HEAD + author + time + PARITY | covered by the entry hash; parity re-checked by `decode_statement` |
| `semantic.content_raw` | the content QUOTE frame (`encode_quoted_bytes`: HEAD=DIRECT/QUOTE + BLEND nibbles + PARITY) | covered by the entry hash; byte-exact content |

Both are stored as **hex text** (never `bytes`) so layer payload JSON serialization
(`sort_keys=True`, compact separators) is deterministic and the entry hash is stable
across save/reload. The record is the unit of "one step"; both runs must survive
round-trip.

## 2. Channel mapping (the encoding contract)

| Grimoire channel | question | source (from the entry) |
| --- | --- | --- |
| R (atom) | what exists | record-kind composition + author atom + time nibbles |
| G (role) | how it connects | HEAD / AGENT / TIME roles; BLEND for composed spellings |
| B (evidence) | why believed | DEFAULT evidence table (section 3) |
| A (force) | what follows | DEFAULT force table (section 4) |

The opcode string itself is a record field (hash-covered); its semantic kind is the
HEAD record-kind composition. An opcode with no canonical composition carries the
undifferentiated HEAD atom 一 (`k1`, "one") with the opcode token preserved in the
record fields — **no atom address is ever invented** (A8 external address table).

## 3. DEFAULT evidence table (channel B)

Resolution order is a decision procedure; the table is its canonical statement.

| Entry state | Evidence |
| --- | --- |
| explicit `evidence` marker (valid name) | the marker, as-is |
| `verified is True`, source kind measured/sensor/direct | `MEASURED` |
| `verified is True`, source kind cited/external/reference | `CITED` |
| `verified is True`, no recognizable source kind | `UNKNOWN` |
| unverified `CONSOLIDATE` / `RECALL` / `CONSOLIDATION*` | `REMEMBERED` |
| unverified `THINK` / `DISCOVERY`, or author `MIND` | `INFERRED` |
| unverified with source kind conversation/chat/report | `REPORTED` |
| `assumption is True` or `confidence == "assumed"` | `ASSUMED` |
| source kind policy/genome/stipulated/rule/operator | `STIPULATED` |
| nothing identifiable (no opcode/author/source) | `UNKNOWN` |
| otherwise (honest default for unverified records) | `INFERRED` |

Hard rule: **`DIRECT` is never invented.** It is emitted only from an explicit
`evidence` marker **and** `verified is True` **and** a measured/sensor source;
otherwise the explicit-DIRECT request resolves to `UNKNOWN`. Relabeling `ASSUMED` as
`INFERRED` is a conformance failure (edition section 3) and is refused by the tests
and invariants.

## 4. DEFAULT force table (channel A)

| Entry opcode / author | Force |
| --- | --- |
| `THINK` (MIND reflection) | `MAY` — reflection, no obligation |
| `CONSOLIDATE` (retrospective) | `LET` — propose only |
| `PROPOSE` / `SPECIAL` | `MAY` |
| `DISPATCH` / `INTENTION` / `DELEGATED` | `GATE` — gated action |
| `PROOF` (limb action proof) | `BOUND` — recorded obligation of the action |
| `IMMUNE` / `WARN` | `MUST` — integrity response |
| `SENSE` (intake) | `WAY` — observed, informative |
| `RULE` / `POLICY` | `RULE` |
| `DEWEIGHT` / `WRITE` / `DISCOVERY` | `BOUND` — recorded Body action/claim |
| `MODEL.*` (body traces) | `BOUND` |
| `RECALL` | `WAY` |
| explicit `force` marker (valid name) | the marker, as-is |
| anything unmapped | `QUOTE` — inert, never invented |

`LAW` is reserved for operator stipulation: an explicit `force: "LAW"` marker resolves
to `QUOTE` unless the entry is marked `stipulated` or carries a policy/operator source.

## 5. Record-kind compositions (channel R, canonical section-6 rows)

Every row is a **canonical composition from the frozen edition's section-6 table**.
At import the mirror is verified against the edition document (a repository checkout);
an invented row refuses to import. Spellings use the edition's atom addresses.

| opcode | composition | spelling | gloss |
| --- | --- | --- | --- |
| `THINK` | reasoning | 心行 | mind + walk |
| `CONSOLIDATE` | redescription | 言更 | speech + further |
| `PROPOSE` / `SPECIAL` | proposal | 言將 | speech + soon |
| `DISPATCH` | guarded_action | 門行 | gate + walk |
| `INTENTION` | intent | 心向 | mind + toward |
| `DELEGATED` | handoff | 手向 | hand + toward |
| `PROOF` | proof | 石 | stone |
| `IMMUNE` | immune | 門血 | gate + blood |
| `WARN` | signal | 音 | sound |
| `SENSE` | sense | 耳 | ear |
| `RULE` / `POLICY` | law | 示 | altar |
| `DEWEIGHT` | weaken | 力欠 | power + lack |
| `WRITE` | entry | 門入 | gate + enter |
| `DISCOVERY` | discovery | 見生 | see + life |
| `RECALL` | history | 前文 | before + script |
| `MODEL.*` | receipt | 文 | script |
| anything else | — (HEAD 一) | — | undifferentiated record, opcode token in fields |

Author atoms: `MIND` → 心 (k61), `BODY` → 身 (k158). Any other author carries no
AGENT atom group; the author string stays in the record fields.

## 6. Integrity model

- The record `hash` is the **standard total entry hash** over every non-volatile
  field, where the canonical serialized form **includes** `semantic.raw` and
  `semantic.content_raw` (hex text). Volatile fields (`id`, `tombstone`,
  `quarantined`, `hash`) stay outside the hash, exactly as `log-json`.
- The Grimoire parity and the optional raw-run fingerprint ride inside `semantic`
  (`parity_status`, `fingerprint`) — statement-local integrity in addition to the
  cube's entry hash. Parity is not transport integrity; the two are never collapsed
  (GRIMOIRE-V010-09).
- `decode_entry` verifies: entry hash, statement parity, and byte-exact content
  against the QUOTE frame. Any drift raises.

## 7. Cube guarantees (inherited, not weakened)

Semantic bands are entry-stream bands (`entry_stream = True`), so they receive the
same Body guarantees as `log-json`: band-unique monotonic ids, multi-layer reads,
veil (private `thoughts`), tombstone/quarantine, graded memory (deweight ghosts and
restores), metabolism (compact/dedupe/reclaim), staged-save verification, and entry
hashes in `verify()`. Dedupe keys on `(opcode, content_hash)` for `log-json`; for
semantic records the key additionally includes evidence and force — a `MEASURED` fact
and an `INFERRED` reflection with identical content are **not** duplicates.

## 8. Design decisions

| # | decision |
| --- | --- |
| D1 | New driver `grimoire-v0.10-entry`; `grimoire-v0.9`/`grimoire-v0.10` remain pure carrier decoders (never silently change what an existing profile means). |
| D2 | Default semantic scope: `thoughts` + `brain`. `identity`/`immune` stay `log-json`. An operator receipt may later extend the semantic genome. |
| D3 | Structural semantics in real morphemes; content in a QUOTE-framed payload (byte-exact fidelity). Deep atomization of arbitrary content is a stretch goal (D3b), not Phase-1 scope. |
| D4 | Records stay entry-shaped (+ `semantic` metadata); existing consumers (nervous context, refs, mind context, deweight overlay) are untouched. |
| D5 | Entry hash covers the raw runs (hex text); parity + optional fingerprint ride in `semantic`; keep parity and transport integrity separate. |
| D6 | Band-unique monotonic ids, tombstone/quarantine flags, and the weight overlay behave exactly like `log-json`. |
| D7 | Backward compatible: no existing organism or carrier changes; migration is out of scope without a future operator receipt. |
| DD-Q | The one-HEAD-per-statement decoder rule requires the content QUOTE frame to be a separate framed run; the record is the unit of one step. |

## 9. Governance

Creating semantic-memory tissue requires the operator receipt
`adopt_semantic_memory` (mirrors `adopt_v010`): `operator_authorized is True` is
required, the receipt hashes the encoder, driver, cube, invariant file, and this
companion, records `default_scope: new-tissue-only`, and is appended to the Body's
`edition_adoptions`. Without the receipt, unauthorized adoption is refused.

## 10. Executable invariants

The `GRIMOIRE-ENC-*` family in `src/mantle/audits/invariants.py` (registered in the
live registry with `TM-GRIMOIRE-SEMANTIC` rows in `THREAT_MODEL.md`) makes every
guarantee in this document executable, each with a red case. Never hardcode counts in
prose — derive from `python -m mantle prove`.

## 11. Verification

```bash
PYTHONPATH=src python -m mantle prove
PYTHONPATH=src python -m mantle audit
PYTHONPATH=src python -m mantle doctor <nest>
PYTHONPATH=src python tools/grimoire_tool.py verify documents/grimoire/editions/grimoire-v0.10.md
PYTHONPATH=src python examples/semantic_memory/demo.py
pytest examples/tests/test_grimoire_semantic.py -q
```

## 12. Out of scope (Phase 1)

- Changing the frozen editions or the atom registry.
- Auto-migrating existing organisms/cubes (operator decision, separate receipt).
- Deep atomization of arbitrary content into composition rows (research-gated stretch).
- Changing the MIND write surface or fusion rules.
- Production hard-sandbox (wasm runner) — remains a prepared seam.
