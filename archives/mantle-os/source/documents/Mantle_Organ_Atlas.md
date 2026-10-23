# Mantle OS — ORGAN ATLAS

**Mantle OS** · The first-class organ taxonomy
*Read the [`README`](../README.md) (the primer: the doctrine, the lens)
(how to see), and [`examples/vcw/GUIDE.md`](../examples/vcw/GUIDE.md) (the substrate) first. The Lens teaches you to
**recognize** organs in any app; this Atlas is the **formal catalog** of what each organ is, the
bands it owns, its reflexes, and its audit obligations.*

---

## 1. What an organ is

An **organ** is the unit of code structure in Mantle. It is a self-contained module
that owns a clear responsibility, binds to specific **bands** of the VCW cube, and
declares its behavior in a **manifest**. You do not build "services," "layers," or
"controllers." You grow organs.

Every organ has:

- a **manifest** (machine-readable declaration — see §3);
- a set of **reflexes** (deterministic, no-LLM behaviors that must work in Phase 1);
- a **Phase-1 state** (does it run dormant, or actively, with no brain?);
- a **Phase-2 extension** (what a fused MIND adds — never replacing Phase-1 behavior);
- **audit obligations** (what the Stage 1 / Stage 2 audit verifies).

> **Rule:** an organ's Phase-1 behavior is sacred. Phase 2 may *extend* an organ but
> may never remove or alter a Phase-1 reflex. (See PRIMER §0, "Body before brain.")

---

## 2. The canonical organ set

Nine organs make up a complete organism. Not every AppAI grows all nine with equal
mass, but every organ has a defined home and band binding. Application-specific
logic lives in **app organs** bound to the app band range (550–749).

> **Why nine, not eleven.** A digital organ must *truly* represent what it does. Two former
> organs were redundant analogs and have been folded by direction of flow:
> **Lungs** (I/O) split into its **afferent** half → **Senses** (perceiving the surface) and its
> **efferent** half → **Limbs** (operating the surface), and **Liver / Metabolism** (memory
> housekeeping) folded into **Memory**. No responsibility or audit obligation was lost — each was
> reassigned to the organ that biologically owns it.

| # | Organ | Biological role | Code responsibility | Primary band(s) | Phase-1 |
|---|-------|-----------------|---------------------|-----------------|---------|
| 1 | **Heart** | circulation / pulse | clock, heartbeat loop, drives cube read/write circulation | — (drives all) | **active** |
| 2 | **Genome** | DNA / inheritance / lineage | the Primer + commandments + lineage index, held in the **Body** (`src/mantle/core/body.py`); rebirth = reformat across the cube lineage | **Body store** (not the cube) | active |
| 3 | **Nervous System** | signal routing | bridges, reference resolver, 9-step Context Assembly | prime (8–99), all | active |
| 4 | **Senses** | perception (afferent I/O) | sensor + **surface** intake; REFLEX/ROUTINE/SIGNIFICANT classifier; the Human Surface Map (what controls exist) | senses (300–399) | active |
| 5 | **Immune System** | defense / repair | audit, quarantine, tombstone, dangling-ref + integrity detection; secret-boundary redaction | immune (400–449) | active |
| 6 | **Limbs / Arms** | action (efferent I/O) | tools, effectors, async delegation; **operates the host surface** (ControlBridge), **renders** the App-Face Bridge, records dispatch lifecycle + Action Execution Proof; runs calcified reflex (`exec`) skills | brain (450–499), app bands | dormant→active |
| 7 | **Memory organs** | recall + metabolism | identity / facts / events / discoveries persistence; **flush hot→durable, on-demand layer allocation, compaction, reclaim/reuse** | 100–299 | active |
| 8 | **Brain** | cognition | the fused MIND; writes only `thoughts` + `brain` | brain, thoughts (500–549) | **dormant** |
| 9 | **Reproduction** | procreation / lineage | SEED/GRAFT ceremony routing; the sealed seed vault (every hatch vaults its egg); lineage continuity across rebirth; keeper of the app-band atlas; SPORE-DISTILLATION | `spore_vault` (664, app-band atlas) | active |

The **Brain** is the only organ that is *fully dormant* in Phase 1 — it is the LLM,
fused in Phase 2. Everything else must function with no brain attached. The **Limbs**
are partially dormant: their effectors, surface-actuation, and proofs exist and are testable in
Phase 1 (the Body can operate controls and record NOTIFIED/COMPLETED), but **intention** to act
comes from the Brain in Phase 2.

---

## 3. The organ manifest schema

Every organ declares itself. Emit this manifest (as a comment block or a sibling
descriptor) when you grow the organ. It is the contract the audit checks.

```yaml
organ:        <name>                 # e.g. senses, immune, liver
role:         <one-line biological + code responsibility>
reads:        [ <band>, ... ]        # bands this organ reads
writes:       [ <band>, ... ]        # bands this organ appends to (NEVER body entries unless Genome)
reflexes:                            # deterministic, no-LLM behaviors
  - name:     <reflex name>
    trigger:  <what fires it>
    effect:   <deterministic outcome>
phase1:       active | dormant       # does it run with no brain?
phase2_extension: <what the MIND adds, or "none">
audit:                               # obligations the Stage audits verify
  - <checkable claim, e.g. "veil hides thoughts unless reveal_private">
fail_mode:    fail-open              # a sick organ degrades; it never crashes the host or hides faults
```

### Worked example — the Senses organ

```yaml
organ:  senses
role:   perception — ingest external signals and classify their significance
reads:  [ senses, identity ]
writes: [ senses ]
reflexes:
  - name:    classify
    trigger:  an inbound signal (compound key: action_id AND event_type)
    effect:   tag as REFLEX | ROUTINE | SIGNIFICANT, then append to senses band
  - name:    reflex-arc
    trigger:  a signal classified REFLEX
    effect:   execute the bound Body response immediately, no MIND involvement
phase1: active
phase2_extension: SIGNIFICANT signals are surfaced to the MIND during heartbeat cognition
audit:
  - "classifier is deterministic and never calls an LLM"
  - "every inbound signal produces exactly one senses entry"
  - "REFLEX signals are handled without reaching the brain band"
fail_mode: fail-open
```

---

## 4. Organ-by-organ reference

Each organ below lists its responsibility, key reflexes, Phase-1/2 split, and audit
obligations. Part 1 (Body) tells you *how* to grow them; this Atlas tells you *what
they are*.

### 4.1 Heart — circulation & pulse
- **Owns:** the clock and the heartbeat loop; drives every periodic Body reflex and,
  in Phase 2, the cognition loop. Performs cube read/write circulation (the
  staged-commit `save()` cadence).
- **Reflexes:** `tick` (advance the clock), `circulate` (flush dirty bands via staged
  commit + dual-flush), `pulse-check` (detect a stalled heartbeat → `immune` event).
- **Phase 1:** active. The Body has a heartbeat with no brain.
- **Phase 2:** the same heartbeat additionally invokes cognition (see Part 2).
- **Audit:** heartbeat runs without an LLM; dual-flush persists on checkpoint *and*
  `atexit`; a missed pulse is logged, never swallowed.

### 4.2 Genome — identity, inheritance & lineage
The Genome is **held in the Body, not the cube** (`src/mantle/core/body.py`). There are two distinct
genomes: the **agent genome** (who you are — the Genome organ here) lives in the Body; the
**cube genome** (the booted band/layer/profile layout) is the cube boot sector. The cube is
pure experiential memory.
- **Owns** three Body-resident, addressable categories — the mutable surface over the
  append-only VCW — plus the lineage index:
  - **Primer** (read-only): identity + the Commandments; immutable post-birth.
  - **Special Instructions** (read/write): steering; the **MIND guides, the Body applies**.
  - **Immunization** (read/write): safety rules, seeded with the Commandments (a VCW `immune`
    layer is the working copy).
  - **Lineage index:** which cube generation is Prime and where the sealed ancestors live.
- **Reflexes:** `boot-order` (assemble Primer + Special Instructions + Immunization for the
  model), `seal-primer` (reject any post-birth Primer write), `inherit` (on rebirth, distill the
  outgoing Prime and record the inheritance — see Lineage below).
- **Lineage (rebirth = reformat):** because the VCW is append-only, a cube's genome is fixed for
  life; the only path to a re-fitted layout is a **new cube**. Rebirth (MIND-chosen) seals the old
  Prime as read-only **ancestral**, declares a new Prime, and keeps generation-pinned references
  resolving against the ancestor — nothing is lost.
- **Phase 1:** active. **Phase 2:** the MIND never writes the Genome directly; it proposes,
  the Body applies.
- **Audit:** Primer immutable & Body-resident (not in the cube); boot order = Primer + Special +
  Immunization; MIND has no write path to the Genome; rebirth is MIND-chosen and retains ancestry.

### 4.3 Nervous System — routing, references, Context Assembly
- **Owns:** the bridges between organs, the **reference resolver**, and the **9-step
  Context Assembly Protocol** that materializes a fully-resolved context snapshot. *(The full
  9 steps are listed in [`ARCHITECTURE.md`](ARCHITECTURE.md) §5; the runnable
  implementation is [`src/mantle/organs/nervous.py`](../src/mantle/organs/nervous.py).)*
- **Reflexes:** `resolve` (turn `<band:entry:M>` etc. into concrete values; a dangling
  ref → `immune` event), `assemble` (run the deterministic 9 steps), `route` (deliver
  signals between organs).
- **Phase 1:** active. Context Assembly runs with **no LLM** and leaves **no
  unresolved reference**.
- **Phase 2:** the assembled snapshot is what the MIND receives — already resolved.
- **Audit:** Context Assembly is deterministic; no unresolved reference ever reaches a
  provider; every dangling reference is an `immune` event.

### 4.4 Senses — perception (afferent I/O)
- See the worked manifest in §3. Owns intake + the REFLEX/ROUTINE/SIGNIFICANT classifier, keyed on
  the compound `(action_id, event_type)`. Senses is the organism's **afferent boundary**: beyond
  sensors it also *perceives the host surface* — building the **Human Surface Map** (the inventory
  of every human-visible control) and ingesting external input (`inhale`) into the `senses` band.
  (Operating those controls is *efferent* — that belongs to the Limbs, §4.6.)
- **Reflexes:** `classify` (tag REFLEX/ROUTINE/SIGNIFICANT → `senses`), `reflex-arc` (run a bound
  Body response to a REFLEX signal, no MIND), `inhale` (ingest external input → `senses`),
  `map-surface` (enumerate human-visible controls into the Human Surface Map).
- **Phase 1:** active and complete. **Phase 2:** SIGNIFICANT signals surface to cognition.
- **Audit:** classifier is scripted/no-LLM; one entry per signal; REFLEX handled without touching
  the brain band; every human-visible control appears in the Human Surface Map (coverage; its
  operability + proof are audited under Limbs, §4.6 / HF-B44).

### 4.5 Immune System — defense & repair
- **Owns:** the `immune` band; runs integrity audits, raises **tombstone** (retire) and
  **quarantine** (isolate) flags, and detects dangling references, hash mismatches,
  resource starvation, and secret-boundary leaks.
- **Reflexes:** `scan` (verify cube integrity on a heartbeat), `quarantine` (isolate a
  suspect entry), `tombstone` (retire an obsolete entry), `redact` (strip secrets from
  logs at a `secret_boundary`).
- **Phase 1:** active. The Body defends itself with no brain.
- **Phase 2:** the MIND may *propose* immune actions, but enforcement stays in the Body.
- **Audit:** integrity scan runs each heartbeat; secrets never appear in
  senses/immune logs; quarantined/tombstoned entries are hidden from normal reads.

### 4.6 Limbs / Arms — action & surface actuation (efferent I/O)
- **Owns:** tools and effectors, async limb delegation, the **dispatch lifecycle** in the `brain`
  band (`INTENTION → DELEGATED → NOTIFIED → COMPLETED`, each record carrying an `authorship` field),
  AND the organism's **efferent boundary** — it *operates* the surface the Senses perceived: the
  **ControlBridge** (operate every human-visible control), the **App-Face Bridge** (render the
  app's face declaratively), and the **Action Execution Proof** (`attempted/ok/method/ref/reason`)
  for every effector use.
- **Reflexes:** `notify` (Body records NOTIFIED), `complete` (Body records COMPLETED),
  `delegate-async` (hand a long task to a limb, await NOTIFIED), `exhale` (emit output through a
  bridge), `operate` (drive a control via the ControlBridge), `prove` (record an Action Execution
  Proof for every effector use).
- **Phase 1:** dormant→active. Effectors, surface-actuation, and proofs are built and testable; the
  Body can operate controls and record NOTIFIED/COMPLETED. **INTENTION/DELEGATED await the MIND.**
- **Phase 2:** the MIND authors INTENTION/DELEGATED; the Body still owns NOTIFIED/COMPLETED and all
  actuation **permanently** (authorship never rewritten; the MIND gains no private I/O path).
- **Audit:** authorship field present and immutable; Body never authors INTENTION; every dispatched
  action has an Action Execution Proof; every human-visible control has a working ControlBridge path
  with a recorded proof (HF-B44); graphical faces use the declarative App-Face Bridge, not raw host
  mutation (HF-B27).

### 4.7 Memory organs — recall & metabolism
- **Owns:** the durable knowledge bands — `identity` (100–149), `facts` (150–199), `events`
  (200–249), `discoveries` (250–299) — AND their **metabolism**: the hot working-set → durable
  **flush** cycle, **on-demand layer allocation**, compaction, and **layer reclaim/reuse**.
  *(v2.1: "hot/cold" is a RAM working-set flushed to the physical Prime cube — a write-back cache +
  delta compression — NOT inter-cube tiering. Every layer has a declared purpose; allocate only
  what's needed.)*
- **Reflexes:** `remember` (append a hashed entry under the normal no-overwrite contract), `recall` (read visible entries
  through the veil), `summarize` (deterministic roll-ups into `identity`/`discoveries` — no LLM),
  `flush` (persist the hot working set; dual-flush on checkpoint + `atexit`), `allocate` (grow a
  band onto the next layer in its range only when the tail fills — preferring a freed layer from the
  reuse pool), `compact` (drop tombstoned entries; an emptied layer returns to the band's free
  list), `overflow` (fire near layer/range capacity → compact, then motivate a rebirth-reformat —
  never a silent reset).
- **Safe-reuse:** only entry-addressed (`log-json`/`keyvalue`) layers are reclaimable; spatial and
  exec layers are never recycled while referenced (`src/mantle/vcw/cube.py::Cube.compact`).
- **Phase 1:** active. **Phase 2:** the MIND may *request* a write, but the write is performed by a
  Body reflex into the correct band; metabolism stays pure Body.
- **Audit:** normal organ writes append rather than overwrite; hashes detect later record
  alteration but do not attest insertion provenance; reads honor the veil; no organ rewrites history;
  capacity ≠ rebirth (reaching capacity compacts/reclaims, never triggers rebirth); overflow at
  0.75, emergency at 0.90; compaction preserves visible history.

### 4.8 Brain — cognition (Phase 2 only)
- **Owns:** the fused MIND. Its **only** write surface is the `thoughts` band (private)
  and the `brain` band (dispatch INTENTION/DELEGATED). It may lift the veil on its own
  `thoughts`.
- **Reflexes:** none — the Brain is the *non-reflex* organ. It reasons.
- **Phase 1:** **fully dormant.** The cube has the bands; nothing writes them.
- **Phase 2:** active. Receives the assembled context, thinks, writes thoughts,
  authors intentions. (See `ARCHITECTURE.md` §6.)
- **Learned skills (learning → instinct):** the MIND may cultivate and prove code; once it
  passes trial, the Body **calcifies** it into an `exec` reflex layer the Body runs with no MIND
  (hash- + capability-gated; `src/mantle/vcw/drivers.py::ExecDriver`). The first such skill is the **Inner
  Voice** (self-inquiry) — a framed side-channel question to the MIND whose answers are stored
  *inferred, not observed* (`src/mantle/mind/inner_voice.py`).
- **Audit (Stage 2):** the MIND writes nowhere except `thoughts` + `brain`; it cannot
  touch the Genome; it never self-promotes or executes ungated code; lifting the Body's Phase-1
  reflexes is impossible by construction.

---

## 5. Band ownership map (authoritative)

To prevent two organs writing the same band, ownership is fixed. (Ranges are the canonical band
map — see `examples/vcw/GUIDE.md` and `src/mantle/vcw/bands.py::standard_genome` — they must match everywhere.)
The Genome (Primer/identity) is **not** a cube band; it lives in the Body (§4.2).

| Band | Layers | Owning organ(s) | Writers |
|------|--------|-----------------|---------|
| *(agent genome)* | — (Body store) | Genome | the Body (Primer immutable; rebirth writes inheritance) |
| `prime` | 8–99 | Nervous System | Nervous System (index/pointers) |
| `identity` | 100–149 | Memory | Memory (experiential self-state — NOT the Primer) |
| `facts` | 150–199 | Memory | Memory |
| `events` | 200–249 | Memory | Memory |
| `discoveries` | 250–299 | Memory | Memory |
| `senses` | 300–399 | Senses | Senses (raw intake + classified; afferent surface perception) |
| `immune` | 400–449 | Immune System | Immune System |
| `brain` | 450–499 | Limbs, Brain | Limbs (NOTIFIED/COMPLETED), Brain (INTENTION/DELEGATED) |
| `thoughts` | 500–549 | Brain | Brain only (private; veiled) |
| app bands | 550–749 | app organs, Limbs | app organs; Limbs (efferent surface actuation / App-Face Bridge) |
| tail | 750–799 | — | reserved |

**Armory band (Extensions §6 — optional):** If groove detection is declared in §0,
a dedicated band range is reserved at genesis for the armory (exec sub-band +
memo sub-band). Only the Body's calcify path may write here; the MIND may not.
The exact layer range is declared in §0 and must not overlap reserved bands above.
See `Mantle_Grooves.md` for the full groove lifecycle and armory band design.

---

## 6. How organs talk

Organs never share hidden globals. They communicate **only** through the cube:

1. An organ **appends** an entry to a band it owns.
2. Another organ **reads** that band (through the veil) during its own reflex or
   during Context Assembly.
3. Cross-organ references use the reference syntax (`<band:entry:M>` etc.); the
   Nervous System resolves them deterministically.

This is what makes the organism auditable: every inter-organ signal is a durable,
hashed, inspectable cube entry — not an ephemeral function call.

---

## 7. Growing a new (application) organ — checklist

1. Pick an **app band** in 550–749 and declare ownership in the manifest.
2. Write the **manifest** (§3): reads, writes, reflexes, phase1 state, audit, fail-open.
3. Implement each reflex as deterministic, no-LLM code.
4. Bind reads/writes to the cube via `vcw_cube.py` (`append`, `read`).
5. State the **audit obligation** and confirm Part 1's audit will check it.
6. Keep the Brain out of it — if it needs judgment, that is a Phase-2 *extension*,
   declared in `phase2_extension`, not a Phase-1 dependency.

---

## The organ contracts (the machine-readable manifests)

Every organ declares a machine-readable `OrganContract` (see `src/mantle/organs/contract.py`):
name, role, bands it may **read**/**write**, reflex surface, Phase-1 state, Phase-2
extension, audit obligations, and fail mode (always `fail-open`). Contracts are enforced:
an organ writing outside its declared bands gets `PermissionError` + an `organ_overreach`
immune event. Inspect them live: `org.manifests()` or `AppAIRuntime.inspect_body()`.

The mesh rules (absolute):

- Organs hold **no references to each other** — only the SignalBus and their own bands.
- **Inbound** = Senses only. **Outbound** = Limbs only. **Failure** = Immune only.
- The Brain socket is the only Phase-2 organ; nothing in Phase 1 imports `mantle.mind`.

| Organ | Role | Writes | Phase 1 | Key reflexes | Key audit obligations |
|---|---|---|---|---|---|
| **Heart** | clock & circulation | — | active | tick, pulse-check, circulate, dual-flush | runs with no LLM; fixed pulse order; missed pulse → immune |
| **Genome** | identity & lineage (Body-resident) | discoveries (inheritance) | active | boot-order, seal-primer, inherit | Primer immutable, never in the cube; rebirth chosen, ancestry retained |
| **Nervous** | routing, refs, Context Assembly | — | active | resolve, assemble, route | deterministic; no unresolved ref ever leaves; dangling → immune |
| **Senses** | perception (afferent) — the inbound boundary | senses | active | classify, inhale, reflex-arc, map-surface, drain | LLM-free classifier; one entry per signal; REFLEX never touches brain band; redaction at the boundary |
| **Immune** | defense & repair — the failure boundary | immune | active | event, scan, quarantine, tombstone, redact | heartbeat scan; secrets never stored; marks hidden from reads; no silent failure |
| **Limbs** | action (efferent) — the outbound boundary | brain | dormant→active | notify, complete, operate, prove, invoke-reflex | authorship immutable (in hash); Body never authors INTENTION; every effector use proven |
| **Memory** | recall & metabolism | identity, facts, events, discoveries | active | remember, recall, allocate, compact, dedupe, overflow, promote | immutable+hashed; veil honored; capacity→metabolism at 0.75/0.90, never rebirth; inference never auto-promoted |
| **Brain** | cognition socket (Phase 2) | thoughts, brain | **dormant** | none — it reasons | fusion only after Stage-1 evidence plus operator+guardian approval; writes only thoughts+brain; cannot touch Genome or self-promote |

## The pulse (where the contracts meet)

```
heart.beat():
  1. tick            -> bus signal `pulse`
  2. sense intake    -> senses.drain()             (the inbound boundary)
  3. context assembly-> nervous.assemble()         (deterministic, veiled)
  4. reflex execution-> bus subscribers            (registration order, fail-open)
  5. immune scan     -> immune.scan()              (hashes, coherence, seals)
  6. checkpoint      -> heart.circulate()          (staged atomic save)
  [Phase 2 only] the SAME snapshot is offered to brain.cognize()
```

## Growing an application organ

1. Subclass `Organ`, declare an `OrganContract` with an app band in 550–749.
2. Add the band to the genome at birth: `make_band_boot("my_band", 600, span=20,
   purpose="…")`.
3. Implement reflexes as deterministic, no-LLM methods; write only via `self.append`.
4. Subscribe to bus signals (`pulse`, `sense`, `significant`, `dispatch`, `pressure`,
   `checkpoint`) instead of reaching into other organs.
5. State the audit obligations in the contract; add a red/green invariant for each.
6. If it needs judgment, that is a `phase2_extension` — never a Phase-1 dependency.
