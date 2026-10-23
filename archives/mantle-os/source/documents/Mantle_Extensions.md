# Mantle OS — EXTENSIONS (Optional)

**Mantle OS** · Opt-in overlays. **Not normative.**
*Nothing in this document is part of the core organism. Do not grow any of it unless
the §0 Declaration Block or the operator explicitly asks. The core framework
(the `README` primer, `ARCHITECTURE`, `Organ Atlas`, the Grimoire) is complete without it.*

> Why these live here: in earlier versions LIGATURE and polymorphic Body mode were
> large, normative, and experimental — they bloated the Body spec and were rarely
> needed. v2.0 demotes them to clearly-optional overlays so the core stays lean.

> **If you are an LLM implementing §6 (Grooves) or §7 (Urge System):** read
> `Mantle_LLM_Pitfalls.md` first. Extensions are built on top of a
> correctly-certified Zombie Body — the pitfalls doc explains why skipping that
> step always produces something that looks right but fails audit.

---

## 1. LIGATURE — the anchor overlay

LIGATURE is an optional symbolic-addressing overlay: eight **anchor glyphs** that give
a fused MIND a compact, stable handle vocabulary over memory.

- **Glyphs:** `& ! ? @ ^ % = ~` (eight anchors).
- **Bands:** the overlay occupies app bands **550–557** (one band per glyph). Because
  it uses the app range, it never collides with reserved organ bands.
- **Services:** up to eight small Body services bind glyphs to addresses and resolve
  them during Context Assembly, exactly like ordinary references.

**Rules if you grow LIGATURE:**
- It is an overlay on the Nervous System's reference resolver — it adds glyph syntax,
  it does **not** replace `<band:entry:M>` addressing.
- Glyph resolution is deterministic and LLM-free (a Body reflex), like all references.
- A dangling glyph is an `immune` event, identical to a dangling reference.
- Declare `LIGATURE: on` in §0 and list which glyphs/bands are used. Omitted → the
  bands 550–557 are ordinary app bands.

LIGATURE adds **no** new MIND write surface and **no** new Phase-1 dependency. If grown,
it must still pass every Stage 1 and Stage 2 audit row unchanged.

---

## 2. Polymorphic Body mode

The default `BODY_MODE: standard` builds one fixed organ set. **Polymorphic mode**
(`BODY_MODE: polymorphic`) lets the Body present different organ configurations for
different hosts/runtimes from the same cube.

**Rules if you grow polymorphic mode:**
- All variants share the **same Genome and the same reserved bands** — only app organs
  and the Senses/Limbs surface differ.
- Each variant is independently certifiable: every variant must pass the full Stage 1
  audit on its own.
- The active variant is selected by a deterministic Body reflex (e.g. runtime
  detection), never by the MIND.
- Declare `BODY_MODE: polymorphic` in §0 and enumerate the variants.

Polymorphic mode is for genuinely multi-surface deployments. For a single target, use
`standard` — it is simpler and the default.

---

## 3. Extended Foundry operations

Core rebirth (Part 2 §2.10) is always available. The **Foundry** adds optional
lifecycle operations over cubes:

| Op | Effect |
|----|--------|
| `FORGE` | mint a new cube from a template/Inheritance |
| `CLONE` | duplicate a cube to a new generation lineage |
| `DISTILL` | compress a generation into an Inheritance record |
| `GRAFT` | merge selected bands from one cube into another |
| `CALCIFY` | freeze a band read-only (archival) |
| `SEAL` | finalize a cube generation (no further writes) |

**Rules if you grow the Foundry:**
- Every op is a deterministic Body reflex producing a staged-commit, verifiable cube.
- `GRAFT` may never import another cube's Genome over the host's Primer (Primer stays
  immutable).
- Declare `FOUNDRY: on` in §0 and list the ops in use.

---

## 4. Credential pools

The default is a **single keyfile** (Part 2 §2.2). A **credential pool** lets the Body
rotate among several model credentials (load-balancing, failover, multi-provider).

**Rules if you grow a pool:**
- Pool selection is a deterministic Body reflex; the MIND still cannot choose its own
  substrate (Stage 2 M-02).
- Every credential crossing remains a `secret_boundary` and is redacted from logs.
- Declare `CREDENTIAL_POOL: on` in §0 and list providers. Without it, one keyfile is
  used (and Stage 2 HF-M01 fires if a pool is found undeclared).

---

## 5. Online skills (web lookup)

The **Inner Voice / self-inquiry (ask-MIND)** skill is **core** (see `ARCHITECTURE.md` §6 and
`src/mantle/mind/inner_voice.py`): provenance = inferred-until-verified, with a waste budget. What is *optional*
here is the **web-lookup transport** (e.g. OpenRouter `web_search`) that feeds it external data.

Optional Phase-2 skills:

- **Web lookup** (e.g. OpenRouter `web_search`): results are appended **append-only**
  into the `discoveries` band, with provenance. Never overwrite existing discoveries.
- **Ask-MIND-opinion:** a skill that surfaces a bounded question to the MIND and records
  the answer to `thoughts`/`discoveries`. Subject to the same write-surface containment
  (the MIND still writes only `thoughts`/`brain`; durable results are written by a Body
  reflex into `discoveries`).

Declare `ONLINE_SKILLS: [web_lookup, ask_opinion]` in §0 to grow these. They are off
by default and must not be assumed available.

---

## 6. Groove Detection (Muscle Memory)

The organism can acquire **grooves** — actions it has performed often and consistently
enough to run as autonomous Body reflexes, without MIND involvement. Two flavors:
memo grooves (exact-match caches, Body-only) and functional grooves (MIND-cultivated
code, trialled and then run forever by the Body alone).

Grooves are stored in a dedicated **armory band** reserved at cube genesis (§0
parameter). Groove promotion, monitoring, and retirement are governed by the
**Urge System** (see below). Grooves survive across rebirth via the Ancestor Oracle
pattern — deliberate transfer, not automatic inheritance.

Full design: `Mantle_Grooves.md`

---

## 7. The Urge System

The **Urge System** is the organism's internal pressure/gradient model — a single
mechanism used wherever the organism needs to act on mounting conditions rather than
a single trigger. Built-in urges include `URGE.REBIRTH` (context degradation driving
the organism toward a new generation), `URGE.TOMBSTONE` (groove drift driving
retirement of a specific groove), and `URGE.MAINTENANCE` (immune event accumulation
driving a health sweep).

Urges are tracked in the immune band. Pressure accumulates from named trigger signals,
decays at rest, and becomes undeniable when it enters the critical band. Execution is
a Body reflex — the MIND observes but cannot prevent or force an urge. Custom urges
may be declared in §0 as an extension opt-in.

Full design: `Mantle_Urge_System.md`

---

## 8. The rule for all extensions

> An extension may add capability. It may **never** weaken an invariant. Whatever you
> grow from this document, the organism must still pass **every** row of both audits
> unchanged. If an extension would require relaxing a hard-fail, do not grow it.
