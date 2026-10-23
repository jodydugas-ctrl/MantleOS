# Mantle OS — ARCHITECTURE: the shape, and the two-phase build path

**Mantle OS** · What the shape is, what each part owes the others, and how to build it —
Phase 1 (the Body) and Phase 2 (the MIND) — in one reference.

*The runnable gates are the authority on correctness: `python -m mantle audit`
(Stage 1), `audit-mind` (Stage 2), `prove` (the invariant suite) — see
[`guides/Audit_Guide.md`](guides/Audit_Guide.md). `python -m mantle teach` narrates the
whole build live.*

---

## 1. What it is

Mantle OS makes the organism **real as a mesh**: a `src/mantle/` package in which every one
of the nine organs is a module with a machine-readable contract, all inter-organ signalling
goes through one deterministic reflex bus, all inbound data enters through Senses, all
outbound action leaves through Limbs, and every integrity problem becomes an Immune event.
*Homeostatic* means the organism regulates its own memory pressure: capacity triggers
**metabolism** (compaction, deduplication, layer reclaim) — never rebirth, never a lossy
reset.

## 2. The package

```
src/mantle/
  cli.py / __main__.py     one entry point: python -m mantle <command>
  core/
    events.py        SignalBus — the deterministic reflex/event bus (fail-open; faults -> Immune)
    body.py          the Body store: Primer (sealed), Special Instructions, Immunization, lineage
    refs.py          the unified reference resolver (<target.selector.address>)
    organism.py      Organism — Body + Prime cube + sealed ancestors + the nine organs on the bus
    audit.py         shared audit scaffolding (rows, fail-open checks, expect_raise)
  vcw/
    png.py           pure-stdlib PNG codec (every layer is a real image)
    entry.py         the one entry hasher — hash covers every non-volatile field
    bands.py         boot sectors, the standard genome, driver registry, capacity thresholds
    drivers.py       log-json / keyvalue / calendar-spatial / exec (+ sandbox, trust, runners)
    indexes.py       compact per-band read indexes (id -> physical position; O(1) retrieve)
    metabolism.py    compaction, tombstone reclamation, deduplication, coherence, pressure
    cube.py          the Cube: lazy materialization, changed-layer-only staged atomic persistence
  organs/
    contract.py      OrganContract — manifest, reflex surface, band permissions, audit obligations
    heart.py         pulse -> sense intake -> context assembly -> reflexes -> immune scan -> checkpoint
    genome.py        identity & lineage (wraps the Body store; seals the Primer)
    nervous.py       reference resolution + the deterministic Context Assembly snapshot
    senses.py        the ONLY inbound boundary (classify REFLEX/ROUTINE/SIGNIFICANT, redact, record)
    immune.py        the ONLY failure boundary (events, scan, quarantine, tombstone, redaction)
    limbs.py         the ONLY outbound boundary (dispatch lifecycle, ControlBridge, proofs)
    memory.py        remember/recall + metabolism (flush, allocate, compact, dedupe, pressure)
    brain.py         the dormant Phase-2 socket (holds a fused MIND; never required by Phase 1)
    reproduction.py  the ninth organ: seed/graft verbs, vault + spore heirlooms, lineage duty
  mind/
    transport.py     pluggable model transports (offline stub default; no vendor SDK anywhere)
    containment.py   the bounded write surface (thoughts + brain only) — one choke point
    port.py          least-authority MIND/operator capability facades (not a Python sandbox)
    mind.py          the fused MIND: think, propose, cultivate (Body trials + calcifies)
    inner_voice.py   self-inquiry — answers are INFERRED, never auto-promoted to facts
    runtime.py       AppAIRuntime — how an agent inspects and acts from INSIDE the organism
  assimilator/
    scanner.py       read-only AST dissection of a host codebase
    organ_map.py     symbol roles -> organ map (what is Heart/Senses/Limbs/Memory/Immune/external)
    wrappers.py      fail-open hook runtime (wrap host behavior; never change it)
    report.py        the assimilation map + APP_INVENTORY artifact + emit_spore (Phase 0)
  audits/
    stage1.py        the Stage-1 Zombie Body gate (deterministic, LLM-free)
    stage2.py        Stage-2 containment + closed-world base/reborn/resident regression
    invariants.py    invariant implementations + the one live typed registry
    registry.py      InvariantSpec validation, threat mapping, and concern views
  spore.py           THE artifact: one PNG agent, optionally carrying a germ (+ spore_min.py)
  hatchery.py        the one birth door: germ or spore -> certified organism
  anchor.py / symbiosis.py / graft.py    residency, the energy economy, the graft germ
  mem.py / compiler.py / ganglia.py      knowledge plasmids, the self-redesigning VCW, parallel limbs
  ghost.py / ghost_http.py               the cache-ghost substrate (optional Phase-2 tissue)
  ingestion.py / doctor.py / face.py / teach.py
```

`examples/vcw/` holds the standalone, normative cube codec and its parity proof. All work
builds on `src/mantle/`.

## 3. The organism mesh (how the nine organs hold together)

**The bus.** `core/events.py` is a deterministic, synchronous signal bus. Organs publish
typed signals and subscribe reflexes; ordering is registration order; a faulting reflex is
caught, degraded, and reported as an Immune event (fail-open — never silent, never crashing
the host). Organs hold no references to each other; they hold the bus and the cube bands
they own.

**The boundaries.** Three are absolute:

- *Inbound:* every external signal enters through `Senses.inhale` — which redacts at the
  boundary, classifies deterministically, writes exactly one `senses` entry, and runs bound
  reflex arcs without touching the brain band.
- *Outbound:* every external effect leaves through `Limbs` — dispatch lifecycle with
  immutable authorship, ControlBridge actuation, an Action Execution Proof per effector
  use, and calcified reflex (`exec`) invocation behind hash/capability/provenance/trust
  gates.
- *Failure:* every dangling reference, integrity fault, overreach, stalled pulse, refused
  write, or policy violation becomes an `immune` event. Nothing fails silently.

**The heartbeat.** One pulse is a complete moment of awareness, in fixed order:
`tick → sense intake (drain the inbox) → context assembly (deterministic, LLM-free) →
reflex execution (bus) → immune scan → persistence checkpoint (staged atomic save)`.
In Phase 1 the cognition slot is empty and the same loop runs whole. In Phase 2 the same
pulse additionally offers the assembled snapshot to the fused MIND — an extension, never a
replacement.

**Contracts.** Every organ carries an `OrganContract`: name, role, bands it may read/write,
reflex surface, Phase-1 state, Phase-2 extension, audit obligations, fail mode. Contracts
are data, validated at wiring time; an organ writing outside its declared bands is an
Immune event.

## 4. The VCW substrate (optimized, invariants intact)

Unchanged doctrine: VCW is the durable booted substrate: RGBA lane hardware, named bands,
immutable hashed entries, the veil, staged save → verify → atomic replace, append before
overwrite, and rebirth separate from capacity. The standard cube is visualized as
800x800x800, but layers materialize only as boot-declared bands need them. Layer
drivers/profiles decide what the four lanes mean: log bytes, key/value storage, spatial
state, exec payload, or Grimoire software lanes. What the implementation adds, without
weakening any of that:

- **Lazy layer materialization** — a sealed ancestor costs nothing until referenced.
- **Changed-layer-only persistence** — per-layer signatures; only dirty layers re-encode.
- **Hot/cold tiering** — the Prime is hot; sealed ancestors are cold, read-only.
- **Metabolism** — `vcw/metabolism.py`: compaction drops dead entries, empty layers return
  to the band free pool, duplicates are tombstoned (dedup), id/hash coherence is checked.
- **Compact indexes** — per-band id→position indexes; `retrieve` never scans.
- **Deterministic reference resolution** — one grammar (`core/refs.py`); every miss an
  Immune event.
- **Sealed ancestral cubes** — sealing computes a content seal-hash recorded in the Body's
  lineage index; a tampered ancestor is detectable on load.
- **Capacity thresholds** — `OVERFLOW = 0.75`, `EMERGENCY = 0.90` of a band's reserved
  span; crossing them fires immune events and (aggressive) metabolism. **Capacity never
  triggers rebirth** — rebirth remains a separate, chosen reformat (the canonical
  walkthrough lives in [`REPRODUCTION.md`](REPRODUCTION.md)).

## 5. Phase 1 — growing the Body (the Zombie certification)

**The goal:** an organism that runs, persists, perceives, defends itself, and acts — with
**no LLM anywhere in the loop**. The product is a **Zombie Body**: provably alive (a
heartbeat, memory, senses, reflexes, a mapped surface) but dormant (no cognition, no
voice). If any behavior in Phase 1 depends on a model, the design is wrong — push that
logic into a reflex or defer it to a Phase-2 extension.

Two ways in, one gate out:

- **Declarative (preferred):** author a germ, inspect it, authorize the exact target, and
  hatch it with `python -m mantle hatch <spore.png|germ.json> --out=<target>
  --auth=<receipt>`. The hatchery performs the whole sequence below deterministically;
  the authorization supplies permission, not technical proof.
- **Hand-grown:** build in this order, each organ to its contract:

```
 1  Declaration & genesis      the §0 block; genesis the cube (standard genome + app bands)
 2  Heart                      clock, heartbeat, circulation (checkpoint on pulse)
 3  Genome                     identity in the BODY (Primer sealed, never in a cube)
 4  Nervous System             references + deterministic Context Assembly
 5  Memory organs              identity/facts/events/discoveries bands + remember/recall
 6  Senses                     intake + classifier + Human Surface Map (afferent I/O)
 7  Immune System              audit, tombstone, quarantine (the only failure boundary)
 8  Memory metabolism          flush, allocation, compaction, reclaim
 9  Surface Parity             Senses perceive / Limbs operate the same I/O surface
10  Limbs / Arms               effectors, dispatch lifecycle, action proofs
11  Brain stub                 dormant bands, NO writer
12  Boot, dual-flush, fail-open   the survival invariants
13  Zombie certification       python -m mantle audit  (the Stage-1 gate)
```

Certification is technical evidence, not fusion authority: Phase 2 additionally requires
separate target-bound operator and guardian approvals. The Stage-1 rows, hard-fail
taxonomy (HF-B*), and the waste axis are executable — `audits/stage1.py` and
`python -m mantle prove` are the authority; [`guides/Audit_Guide.md`](guides/Audit_Guide.md)
narrates them.

## 6. Phase 2 — fusing the MIND

**The law of fusion: the MIND may only ever *extend* the Body.** It may never replace,
disable, or bypass a Phase-1 reflex. Every check the Body passed in Stage 1 must still
pass after fusion — the Stage-2 gate (`python -m mantle audit-mind`) re-runs the entire
Stage-1 audit first, before testing anything new.

The Brain is one organ, grown dormant in Phase 1; Phase 2 wakes it. Its powers are
deliberately narrow: it **receives** the deterministically-assembled, veiled context (it
never assembles its own); it **thinks** into the private `thoughts` band; it **intends**
by authoring `INTENTION`/`DELEGATED` in the `brain` band; it **does nothing else
directly** — all effecting happens through Body reflexes, with proofs the Body records.

Resident maintenance is also Body tissue. `resident/commands.py` supplies the shared
slash-command dispatcher and ephemeral provider state. `/key`, `/model`, `/offline`,
`/status`, `/help`, and registered host extensions execute without consulting the MIND.
`/mind` remains a compatibility alias for `/model`.
Senses receives a sanitized command, Memory appends the redacted outcome, and each
configuration mutation emits `body_configuration_changed`. The default routed model is
`openrouter/free`; the credential remains session-only and is absent from Context
Assembly.
Transport receipts retain requested and provider-reported model identifiers separately;
resident-visible provider text crosses a redaction and terminal-control sanitizer.

The fusion sequence: the pre-fusion gate (a Body that is not Stage-1 certified refuses
fusion) → keyfile & model selection (one keyfile; the transport is a pluggable
`model(prompt) → text`, no vendor SDK) → the Awakening Ceremony → the bounded write
surface (`thoughts` + `brain` only, one choke point — `mind/containment.py`) → the veil
as a layer boundary → the heartbeat cognition loop (the ten-minute baseline plus
nociception pulses) → the MODEL.REQUEST trace → action dispatch & async limb delegation →
starvation & graceful sleep (the symbiosis ledger; a starved MIND sleeps, the Body keeps
beating) → optional online skills (Extensions). MIND-initiated rebirth — the data-rot
gradient, the Ancestor-as-oracle, the memory bridge, MEM VCW knowledge sharing — is
covered by the canonical rebirth walkthrough in [`REPRODUCTION.md`](REPRODUCTION.md) and
FIELD_GUIDE chapters 13–15.

## 7. The Assimilator (Path B, as code)

`src/mantle/assimilator/` implements Path B: read-only substrate scanners classify
evidence-bearing host symbols into candidate organ roles; **organ_map** folds the
classification into an assimilation map and resident host evidence index; **report** emits
the APP_INVENTORY artifact (the signed Phase 0 gate), a
JSON map, and — with `--spore=out.png` — the host's **germ spore** (see
[`REPRODUCTION.md`](REPRODUCTION.md)); **wrappers** is the fail-open hook runtime that
threads host behavior through Senses/Limbs/Memory/Immune without changing it.
`python -m mantle assimilate <path> --dry-run` runs the read-only pipeline against any
host. Python uses `ast`; `.js`, `.mjs`, and `.go` use optional tree-sitter parsers; Rust
and native C/C++ retain deterministic pure-stdlib fallback coverage when structured
parsers are absent. Shared scanners also extract Qt UI/QRC resources, balanced signal
connections, helper-wired actions, and CMake target/source topology. Coverage is reported
as `COMPLETE`, `PARTIAL`, or `BLOCKED`; a dominant first-party substrate with no executable
parser coverage cannot pass as a successful Phase-0 map. The Grimoire supplies the VCW
semantic software profile; assimilation procedure is owned by this code path and the
assimilation guide.

The host evidence index is the resident's local-first consultation substrate. A resident
answers questions about its software from the inventory, organ map, control surfaces, gap
report, and limitations before provider-backed reasoning is allowed to interpret that
evidence.

## 8. The gates

`audits/stage1.py` is deterministic and LLM-free; `audits/stage2.py` re-runs every Stage-1
row after fusion and adds containment rows; `audits/invariants.py` proves each guard
red/green (`python -m mantle prove` prints the live count). Tamper flags (`--break-hash`,
`--break-primer`, `--break-seal`) prove the harness *catches* violations. No invariant was
weakened to pass.

## 9. Design principles (binding)

Body before brain. Reflex before reasoning. Append before overwrite. Veil before exposure.
Immune event before silent failure. Audit before fusion. Capability before action.
Provenance before trust. **Metabolism before rebirth.** Harmony before cleverness.
