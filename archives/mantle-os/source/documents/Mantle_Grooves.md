# Mantle OS — Groove Detection (Muscle Memory)

*Non-normative concept note. This document describes a proposed extension to the
Mantle OS organism model. It is not part of the Phase 1 or Phase 2 normative spec.*

---

## What a Groove Is

A **groove** is a repeated action the organism has performed often enough, and
consistently enough, that it no longer needs to think through each step. The organism
has acquired the action as a reflex — muscle memory.

Grooves are how the organism becomes more capable over its lifetime without requiring
MIND involvement for routine work. A well-grooved organism is faster, quieter, and
more resilient: its common actions run from the Body, leaving cognition free for
genuinely novel problems.

---

## Two Flavors

### Memo Grooves (Body-only)

A memo groove is a memoization cache: the Body has seen this exact input before,
produced a known-good output, and stored the pair. On future identical inputs, the
Body returns the cached output immediately — no MIND, no limb call, no latency.

- Stored in the **memo sub-band** of the armory band (keyvalue driver)
- Calcified immediately on first confirmed match
- No MIND involvement at any stage
- Eligible for **graduation** into a functional groove when enough pairs accumulate
  (the cached pairs become the trial suite)

### Functional Grooves (MIND-cultivated, Body-run)

A functional groove is a small, verified program the Body can execute autonomously.
The MIND observed a pattern, proposed code that reproduces it, the Body trialled the
code against real exemplars, and — after sufficient consistent agreement — the Body
calcified the code into the exec layer. From that point, the Body runs it forever
with no MIND.

- Stored in the **exec sub-band** of the armory band (ExecDriver entries)
- Trial suite built from internally-computed exemplars only (provenance-filtered)
- MIND proposes; Body trials; Body decides; Body runs
- Subject to ongoing immune monitoring and tombstoning via the Urge System

---

## The VCW Armory Band

The armory band is a dedicated region of the VCW cube, reserved at genesis as a §0
parameter. It is the organism's tool library — the place it looks first for a known
solution before engaging cognition.

**Structure:**

```
Armory Band
├── exec sub-band    — functional grooves (ExecDriver entries; hashed, capability-bound)
└── memo sub-band    — memo caches (keyvalue entries; input_hash → output)
```

**Write gate:** Only the Body's calcify path may write to the armory band. The MIND
cannot write here directly. A MIND-proposed groove must pass through Body trial before
any armory write occurs.

**Extensibility:** If the armory band fills a layer, the cube grows a new layer with
the same bootsector, expanding the surface. There is no hard cap on the number of
grooves — the armory grows organically with the organism's acquired skills.

**Across rebirth:** The armory band is inherited by the new generation but all
inherited grooves are re-marked `provisional`. They are not trusted until re-trialled
in the new generation's context (see Cross-Generation Survival below).

---

## Groove Lifecycle

```
OBSERVE → CLASSIFY → CALCIFY (memo)
                   → REHEARSE → CALCIFY (functional)
                                        ↓
                              WATCH (immune monitoring)
                                        ↓
                              TOMBSTONE (via URGE.TOMBSTONE)
```

**OBSERVE:** The Body's Senses organ classifies every input as REFLEX / ROUTINE /
SIGNIFICANT. Groove candidates emerge from ROUTINE events — actions the Body has
dispatched multiple times with stable outcomes.

**CLASSIFY:** The Body evaluates whether a candidate is memo-eligible (identical
inputs produce identical outputs — strict determinism) or functional-eligible (a
consistent pattern that could be expressed as code).

**CALCIFY (memo):** On confirmed match, the Body writes the input/output pair to the
memo sub-band immediately. No rehearsal required.

**REHEARSE (functional):** The MIND proposes code. The Body runs the code against
the exemplar pool — all exemplars must be internally-computed (provenance filter:
externally-supplied inputs are excluded). The confidence signal builds across
consecutive agreements. This is not a hard count; it is a growing confidence gradient.
When confidence becomes undeniable, the Body calcifies.

**CALCIFY (functional):** The Body writes the ExecDriver entry to the exec sub-band
with: `code_hash`, entry point, capability declaration (scope-pinned to trial values),
provenance chain, runner. Immune system logs the calcification event.

**WATCH:** Post-calcification, the immune system monitors every groove execution.
Outputs are compared against the trial distribution. Capability scope is verified
at each invocation. Any anomaly increments pressure on the groove's
`URGE.TOMBSTONE.<groove_ref>`.

**TOMBSTONE:** When `URGE.TOMBSTONE` pressure reaches its critical band, the Body
tombstones the groove entry (append-only: a tombstone record is written, the entry
is not deleted). The groove stops executing. The MIND is notified.

---

## Capability Ceiling

Only low-stakes, reversible actions may auto-calcify. The ceiling is fixed at genesis
(§0 parameter) and is Body-enforced — the MIND cannot lower it.

**Ceiling evaluation rules:**

1. Each ExecDriver entry declares a `capability` set at calcify time, inherited from
   the trial run's arm capabilities.
2. If any declared capability exceeds the ceiling, calcification is blocked and the
   action is permanently routed through MIND.
3. Capabilities are **scope-pinned**: `WRITE_FILE` is not a blanket permission — it
   is permission to write to the exact directories used during trial. Execution
   outside that scope is blocked at the exec gate.
4. Composition audit: at calcify time, the immune system checks whether a chain of
   existing grooves could combine to produce a high-impact effect. If so, the newest
   link is blocked.

**Example ceiling table (illustrative — declared in §0):**

| Capability | Eligible for groove |
|------------|-------------------|
| `READ_FILE` (scoped) | Yes |
| `WRITE_FILE` (scoped to known dirs) | Yes |
| `KEYVALUE_READ` | Yes |
| `KEYVALUE_WRITE` (scoped) | Yes |
| `SEND_MESSAGE` | No — irreversible, external effect |
| `MAKE_CALL` | No |
| `DELETE` | No |
| `EXECUTE_SHELL` | No (without explicit §0 override) |

---

## Poisoning Defenses

**Provenance filter:** Only internally-computed exemplars count toward groove
promotion. Inputs are tagged at the Senses boundary. Externally-supplied inputs
are excluded from exemplar pools — they cannot contribute to calcification.

**Input diversity + time gate:** Confidence must build across distinct input
signatures *and* across real operating time (minimum window declared in §0). A
burst of engineered inputs — even varied ones — cannot satisfy a time-gated
threshold.

**Static capability scan:** MIND-proposed code is scanned for undeclared capabilities
before trial begins. Any undeclared capability → immediate rejection + immune event.

**Scope pinning:** A groove physically cannot access resources outside its scoped
capability declaration. The exec gate enforces this before the code runs — MIND
compromise cannot expand the scope post-calcification.

**Tombstone on first anomaly:** No grace period for functional grooves. First
confirmed output anomaly begins urge pressure accumulation immediately.

---

## Cross-Generation Survival (Ancestor Oracle)

Grooves do not automatically transfer across rebirth — blind inheritance of
unvalidated behavior is unsafe. Instead, the new PRIME uses the **Ancestor Oracle**
pattern:

1. New PRIME identifies grooves it wants from the ancestor (by consulting the
   ancestor's armory band reference coordinates via the lineage index).
2. New PRIME **asks the ancestor** for those coordinates — the ancestor is a sealed,
   queryable cube; it returns reference coordinates but cannot be modified.
3. New PRIME imports the groove as `provisional` in its own armory band.
4. The Body re-trials the provisional groove against new exemplars in the current
   generation's context.
5. On passing trial, the groove is promoted from `provisional` to `active` and
   calcified normally.
6. On failing trial, the groove is tombstoned in the new generation. The ancestor's
   copy is unaffected — it remains in stasis as part of the historical record.

This is how knowledge moves forward across generations: not by transplanting memory,
but by pointing at it and letting the new organism prove it for itself.

---

## Graduation: Memo to Functional

A memo groove that has accumulated enough pairs becomes eligible to graduate into a
functional groove:

1. The MIND observes the memo cache and proposes code that reproduces the pattern.
2. The cached pairs become the initial trial suite.
3. The functional trial runs against this suite plus any new exemplars.
4. On calcification, the memo cache is retained (it still serves identical-input
   lookups) but the functional groove now handles the broader pattern.

Graduation is not required — a memo groove that stays a memo is valid forever. But
graduation is how the organism moves from "I have seen this before" to "I understand
this pattern."

---

## What Grooves Are Not

- **Not taught.** No external actor can install a groove. All grooves emerge from the
  organism's own observed behavior.
- **Not permanent.** Every groove is subject to immune monitoring and tombstoning.
  Acquired skills can be retired when they no longer serve accurately.
- **Not cognitive shortcuts for MIND.** The MIND does not use grooves to think faster.
  Grooves replace MIND involvement entirely for their scope — the Body runs them
  autonomously. MIND stays free for novel work.
- **Not unbounded.** The capability ceiling, provenance filter, and scope pinning
  together ensure that no groove can acquire capabilities beyond what the Body's
  trial explicitly authorized.
