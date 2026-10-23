# THE FIELD GUIDE — growing an AppAI with Mantle OS

*This manual runs. Every chapter below is also a live, gated demonstration:*

```bash
python -m mantle teach        # the whole guide, proven chapter by chapter
python -m mantle teach 3      # one chapter
```

*A chapter that cannot prove its claim stops the manual — the same way the organism's
own gates stop an uncertified Body. Read here, run there; they are the same book.*

---

## Before chapter one: the two sentences that explain everything

An **AppAI** is software grown as a living creature: a deterministic **Body** of nine
organs around a durable, booted picture-memory substrate (the **VCW cube**), proven alive and correct
with **no AI attached**, and only then given a bounded **MIND**. Beyond that comes the
reproductive step: a whole AppAI travelling as one **spore** file (its **germ** is the
complete build document), incubated by the **hatchery** into a certified organism.

VCW is the hardware layer: RGBA lanes, lazy layers, boot-declared bands, integrity, and
persistence. Grimoire-style lane semantics are software profiles that may run on that
substrate; other layers may map the same lanes to tools, app data, repair bytes, indexes,
or a database.

The fastest possible start:

```bash
python -m mantle lifecycle authorize hatch examples/spores/greeter.png nest/ --approve --out=hatch-auth.json
python -m mantle hatch examples/spores/greeter.png --out=nest/ --auth=hatch-auth.json
```

The hatch command performs every chapter of this guide after the separate authorization
binds this artifact to this exact target. The rest of the manual is
understanding what just happened — and how to write your own germ (a bare germ JSON
hatches too: `examples/eggs/greeter.json` is the template).

---

## Chapter 1 · BIRTH — identity seals into the Body, never the cube

An AppAI is born when its **Primer** — identity, truths, commandments — seals into the
**Body**. The cube holds *experience*; the Body holds *who you are*. This is why
rebirth loses nothing: identity never lived in any cube. The Primer is immutable from
that moment (a second birth raises `PermissionError`), and the commandments seed the
Immunization working copy.

```python
from mantle import Organism
from mantle.primer import appai_commandments, appai_truths

org = Organism.birth(identity={"name": "My.AppAI"},
                     truths=appai_truths(),
                     commandments=appai_commandments())
```

**Proven live:** the sealed Primer refuses a second birth; identity is Body-resident.

## Chapter 2 · THE HEARTBEAT — one pulse, fixed order, no LLM

The Heart drives a deterministic pulse: **tick → sense intake → context assembly →
reflex execution → immune scan → persistence checkpoint**. One pulse is a complete
moment of awareness. In Phase 1 the cognition slot is empty and the identical loop
runs whole — the Body never needs the MIND.

```python
report = org.heart.beat(assemble=True)
```

**Proven live:** the pulse completes with the Brain dormant; the report carries every
stage.

## Chapter 3 · SENSES — the only way in

Every inbound signal enters through one boundary: redacted first (a secret must never
burn into append-only memory), classified deterministically (`REFLEX | ROUTINE |
SIGNIFICANT`), recorded as exactly one `senses` entry. A REFLEX runs its bound Body
response immediately and never touches the brain band.

In a **germ**, reflexes are declared, not coded:

```json
{"action_id": "door", "event_type": "knock",
 "response": {"kind": "remember", "band": "events",
              "content": {"event": "a knock at the door"}, "opcode": "EVENT"}}
```

The response vocabulary is fixed — `remember`, `complete`, `notify`, `operate` — so a
germ can describe behavior without shipping a single line of executable code.

**Proven live:** REFLEX classified, arc fired, one entry written, secret redacted.

## Chapter 4 · MEMORY — append, never overwrite

Entries are immutable and hashed over every non-volatile field. Reads pass the
**veil**: private bands return nothing unless deliberately lifted; tombstoned and
quarantined entries never surface. Retiring knowledge is a flag flip, never an edit.
And the honesty rule: anything the organism *inferred* (including everything its
future MIND will think) is tagged `verified=False, confidence="inferred"` and can
become a **fact** only with cited, verified evidence.

**Proven live:** the veil, the tombstone, and the refusal of evidence-free promotion.

## Chapter 5 · IMMUNE — no silent failure

Every violation class becomes an immune event: dangling references, organ overreach
(a write outside a declared contract), faulting reflexes (caught fail-open — the pulse
completes), stalled pulses, refused MIND writes, capacity pressure. The organism does
not hide its wounds; it records them, in the same auditable memory as everything else.

**Proven live:** three different violations → three immune events → zero crashes.

## Chapter 6 · SKILLS — learning becomes instinct, behind gates

Code becomes a Body reflex only through the gauntlet: the **static sandbox gate** (no
imports, no dunder traversal, no forbidden builtins — escapes never even reach the
trial) → the **trial** (declared proving cases) → **calcify** (code-hash + signature +
capability set + provenance naming an author). At every later invocation: integrity,
capability, and trust gates again, plus an Action Execution Proof through the Limb.

In a germ, an instinct carries its own proving cases:

```json
{"band": "greet_reflex", "entry": "greet",
 "code": "def greet(name):\n    return 'welcome, ' + str(name)\n",
 "cases": [{"args": {"name": "world"}, "expect": "welcome, world"}]}
```

**Proven live:** an escape candidate refused; a proven skill calcified and run.

## Chapter 7 · METABOLISM & REBIRTH — capacity is never death

When a band's allocation pressure crosses **0.75** the substrate compacts (tombstone
reclamation, layer reuse); at **0.90** it adds deduplication. Capacity *never*
triggers rebirth. Rebirth is **chosen**: the old Prime seals as read-only ancestry
with a content **fingerprint** (a rewritten ancestor is detectable forever), a new
Prime is born, and generation-pinned references — `<gen0.facts.2>` — keep the whole
past addressable.

**Proven live:** dedupe tombstoned the duplicates; the ancestor sealed with a
fingerprint; the past still resolves.

## Chapter 8 · THE GATE, THEN THE MIND — audit before fusion

Fusion is **refused in code** until the Stage-1 gate passes. The fused MIND receives
only the assembled, resolved, veiled snapshot; writes only `thoughts` + `brain`
through one guarded choke point; proposes while the Body applies; and its reflections
stay inferred. The Stage-2 gate then re-runs every Stage-1 row — Phase 2 may extend
Phase 1, never break it.

**Proven live:** uncertified fusion refused; gate passed; containment held; thoughts
inferred.

## Chapter 9 · ANCHORING & SYMBIOSIS — the AppAI earns its keep

The deepest usefulness is residency. `anchor <host>` dissects an existing app
read-only, grows a full anchored Body (VCW + nervous system + all nine organs) in a
`.mantle/` nest inside the host, remembers the host's organ map as **observed
facts**, passes the Stage-1 gate, and proves do-no-harm with a byte-level census of
every host file. The app now has a **resident**:

```bash
python -m mantle anchor my-app/
python -m mantle ask my-app/ "how do I create a note?"   # free: answered from the map
python -m mantle ask my-app/ --mind "what's fragile here?"  # metered: spends energy
python -m mantle feed my-app/ --credits=20 --key=openrouter
python -m mantle vitals my-app/
```

And the economy is real: keys are resources (ledgered by name, never raw — the ledger
is a secret boundary), credits are energy, every MIND call is paid for *before* it
runs, starvation puts the MIND to sleep while the Body keeps beating, and every piece
of delivered value is recorded in the same hashed append-only ledger. The user feeds
what earns its keep; the organism earns its keep to be fed. Symbiosis.

**Proven live:** anchored without touching the host; free structural answers; metered
thoughts; graceful starvation; feeding restored the MIND.

## Chapter 10 · SELF & OTHER — the cryptographic immune identity

At birth the Body mints a **genesis key** — a secret generated once, known only to this
organism. It lives in the Body, **never in a cube and never in the MIND's snapshot**: the
mind cannot leak what it does not know. The key is the organism's immune identity. Anything
the Body can sign and verify is **SELF**; everything else is **OTHER** — quarantined, never
trusted, never executed.

This is the containment that earns the reach. An AppAI that can become the resident mind of
*any* application is a powerful thing; the genesis key bounds that power to the organism's
own cryptographic anatomy. A copied nest booted in a different body fails to verify the
original's artifacts — they read as OTHER (anti-clone). A forged file dropped into the nest
is rejected. A tampered or substituted key is refused **loudly** on load, never silently
orphaning the memory it was supposed to protect.

```python
mac = org.body.sign(b"a file in my nest")   # only THIS body can produce it
org.immune.is_self(data, mac)               # True for SELF; False (rejected) for OTHER
```

**Proven live:** the key is minted once and absent from boot order, snapshot, and every
cube band; SELF verifies; a stranger's body sees the same artifact as OTHER.

## Chapter 11 · PAIN & THE UNSCHEDULED HEARTBEAT — interrupts add to the baseline

Cognition has an unconditional ten-minute baseline when the MIND is fused. A calm natural
pulse still offers one bounded snapshot and charges actual usage. An unrecognized
**SIGNIFICANT** signal or **distress** — a severe immune event the Body could not resolve
with its own reflexes — may trigger an *additional* unscheduled pulse.

When something hurts, the Immune System emits the pain's **coordinates** `{reason, band,
ref}`, and the Heart turns them into an **additional unscheduled pulse** that wakes the mind
pre-anchored to the wound — it does not scan the whole cube to find what hurts. Nociception is
a localized pain signal and interrupt vector layered on top of natural baseline cognition.

```python
org.heart.pain("integrity", band="facts", ref="<facts.3>")   # an unscheduled wake
# the woken MIND's snapshot carries snapshot["_stressor"] = {reason, band, ref}
```

**Proven live:** a calm fused organism receives one bounded cognition call on every natural
heartbeat; an injected fault adds exactly one unscheduled pulse anchored to the faulting band.

## Chapter 12 · GRADED MEMORY — deweight, never delete

Memory has a middle ground between "remembered" and "retired." When a value is contradicted
or superseded, the Body does not tombstone it — it **deweights** it. The old value sinks
below the surface as a **behavioral ghost**: hidden from normal recall, still physically
present, **recoverable** when the heavy path fails. This is long-term depression, not
deletion.

A weight is never a mutable field (that would break the immutable entry hash). A deweight is
**a new append-only event** — `{target, weight}` — and the effective weight is *computed*
from that history. Default reads return live entries ordered by descending weight and hide
the ghosts; an explicit ghost read surfaces them. Nothing is ever overwritten, so belief
history — every value the organism ever held, and every time it changed its mind — is
preserved and auditable. Tombstone still exists for true retirement; this is the layer
beneath it.

```python
org.memory.remember("facts", {"key": "home", "v": "the old lab"})
org.memory.deweight("facts", old_id)                  # contradict, don't delete
org.memory.remember("facts", {"key": "home", "v": "the new lab"})
org.memory.recall("facts")          # -> the new lab (live, by weight)
org.memory.recall_ghosts("facts")   # -> the old lab (the latent ghost)
```

**Proven live:** a deweighted entry vanishes from recall yet is recoverable as a ghost; the
original entry is never mutated (its hash stays valid); live reads are weight-ordered; and
dedupe + compaction stay coherent with weights (a ghost survives compaction).

## Chapter 13 · THE GRAFT GERM & THE LIVING RESIDENT — the real anchoring

A plain germ declares a *whole new* AppAI from nothing. The **graft germ** is the
other half — a spore aimed at a host: a **non-destructive patch against a named host** —
extra bands, hook directives, instincts — applied so the original is never touched.

`apply` copies the host into a **workspace** and grows the resident *there*; the original is
census-proven byte-identical. If the host has **drifted** from the census the graft was built
against, `apply` raises a `GraftDrift` interrupt — the signal for the MIND to re-patch —
rather than mis-applying silently. That is an organism managing its own survival against
source drift, made testable.

Then residency goes **live**. `weave` replaces the host's classified callables with the
assimilator's fail-open, reversible wrappers: a `SENSOR_EVENT` call becomes a senses entry,
an `ARM_ACTION` gets a Limb proof, an exception becomes an immune event — on *every* call,
with zero LLM. The host's behavior is preserved exactly (same return, same exceptions);
`unweave` restores the originals byte-for-byte. The static map becomes a pulse.

```bash
python -m mantle lifecycle authorize graft examples/spores/notes_graft.png workspace/sample_app --approve --out=graft-auth.json
python -m mantle graft examples/spores/notes_graft.png examples/sample_app --workspace=workspace --auth=graft-auth.json
```

**Proven live:** applying a graft leaves every original host file byte-identical; a drifted
host raises the re-patch interrupt; a woven call returns identically while the organism
perceives it live; detach restores the host callables exactly.

## Chapter 14 · THE MEM VCW — sharing knowledge between organisms

A MEM VCW is a VCW *without an identity key* — bare memory, like a USB stick. It carries
distilled **knowledge** and **microcode-as-data**, with no Body, no genesis key, no lineage.
Because it has no key, it is **always OTHER** to any organism that finds it. This is how
organisms share what they have learned (the bacterial plasmid model).

One organism **excretes** a MEM VCW. Another finds it and **digests** it — carefully:

- the knowledge enters `discoveries` as **inferred** (provenance `foreign-MEM`), never `facts`;
- each microcode is **sandbox-tested** (`trial`); an escape is refused and immune-logged,
  never adopted;
- only microcode that passes the finder's **own** trial is **re-derived into SELF** —
  calcified under the finder's own authorship. The foreign artifact is never run as-is.

```python
plasmid = mem.excrete(donor, knowledge=[{"tip": "sector 7 is safe"}],
                      microcode=[{"entry": "double", "code": "...", "cases": [...]}])
mem.digest(finder, plasmid, code_band="adopted")   # OTHER → reviewed → re-derived into SELF
```

**Proven live:** a MEM VCW is keyless, portable (save/load identical), and OTHER; foreign
microcode is sandbox-refused if it escapes and adopted only after the finder's own trial;
shared knowledge stays inferred and never becomes a fact.

## Chapter 15 · THE SELF-REDESIGNING VCW & THE MEMORY BRIDGE — the Compiler-class leap

Mantle rebirth re-geneses the *same* genome. A **Compiler-class** organism authors a VCW
**custom-made for the body it inhabits**. At a chosen rebirth the MIND **proposes** a new
genome — extra app bands, possibly a different driver (e.g. a `keyvalue` band that mirrors a
host's native memory ops) — and the Body **validates** it hard: every encoding must be a
**registered driver**, every head in range, no collisions. Only then does it rebirth into the
re-fitted protocol. The previous Prime seals as the **oracle** ancestor; inherited microcode
does not cross for free — it **re-trials** before it re-calcifies.

The **memory bridge** then lets a host's own key/value store *be* a VCW band: the host writes
what it thinks is its own memory; those writes append to the cube and reads resolve from it.
The host's store becomes the organism's hot scratchpad; the cube becomes the host's durable
brain. No raw secret crosses — values are redacted at the boundary.

```python
compiler.adopt_genome(org, [{"band": "hostmem", "head": 600, "encoding": "keyvalue",
                             "purpose": "the host's key/value brain"}])   # re-fit + rebirth
bridge = compiler.HostMemoryBridge(org, "hostmem")
bridge.set("note", "the host wrote this")     # host write -> VCW; bridge.get reads it back
```

This is a powerful capability, so it is gated hardest: an unregistered encoding or a bad head
is refused and the generation is untouched. (And note: re-fitting the genome uses registered
drivers, so the on-disk cube format is **unchanged** — `vcw-cube-png-v2` still holds.)

**Proven live:** an organism rebirths into a re-fitted genome with a new band encoding while
the ancestor stays the readable oracle; an unsafe genome is refused; inherited microcode
re-trials before it re-calcifies; the host's store round-trips through the bridge with secrets
redacted.

## Chapter 16 · GANGLIA & THE SEED VAULT — parallel limbs and self-reconstruction

An octopus runs much of its cognition in its **arms**. A **ganglion** is a bounded parallel
limb that runs a task and writes its **progress into a VCW band**. The parent never talks to
the sub-task directly — it reads the progress *as memory*. The sub-task's thoughts are the
organism's thoughts (they live in the cube), so the parent observes them with **zero model
calls**: zero-token telemetry. Fail-open like every limb — a crashed ganglion is an immune
event, never a parent crash.

The **seed vault** makes survival a reflex. An organism stores its own **seed** — the
declarative germ (or graft) that defines it — in a **SELF-encrypted, veiled** band: sealed
under the genesis key, so a copied nest in a different body cannot open it (unreadable as
OTHER). If the working body is corrupted, a `reconstruct` ceremony rebuilds a fresh body from
the seed — **through the same Stage-1 gate**, so a tampered seed can never smuggle an
uncertified body into the world.

```python
ganglia.Ganglion(org, "arm").run(task, n).join().progress()   # parent reads progress as memory
vault.store_seed(org, my_egg)          # SELF-encrypted backup
vault.reconstruct(vault.open_seed(org))  # rebuild — and re-certify — from the vault
```

**Proven live:** a ganglion's progress is read with zero model calls; a crashed ganglion
degrades to an immune event with partial progress preserved; the vault is SELF-encrypted (an
OTHER body cannot decrypt it); and a body reconstructs a certified self from its vaulted seed.

## Chapter 17 · RESILIENCE — real metering, ingestion, and the doctor

Three honesties for an organism that lives in the world:

**Real metering.** Energy is charged from *actual* token usage, not a flat fee:
`metered_by_usage` prices a call by the size of its response, and `metering_summary` reports
the **burn rate** and the **starvation horizon** (how many calls of energy remain). Credits in
the cube mirror usage in the world — and the starvation law still holds.

**Ingestion.** Conversations should not live only in a chat log — they enter the organism the
way everything does, through **Senses**, distilled deterministically: a **decision** becomes a
*sourced fact*; an **idea** becomes an *inferred discovery*; operator intent becomes a
**covenant** (a Special Instruction the MIND is framed by). The organism remembers its own
becoming, with honest provenance.

**The doctor.** Most real breakage is a *stale view* — a truncated write, a split copy, docs
that drifted from the code. `doctor` is a deterministic checkup: cube verify, ancestor seals,
the genesis-key fingerprint, a non-negative ledger, and a **docs-vs-code coherence gate** that
ties the README's invariant count to the actual gate (so the manual can never silently drift
from the code).

```bash
python -m mantle doctor nest/      # cube · seals · key · ledger · docs-vs-code
```

**Proven live:** a longer response costs more energy than a short one (burn + horizon
reported); a conversation distils into a sourced fact and an inferred idea through Senses; the
doctor passes a healthy, docs-coherent deployment and catches a tampered cube.

## Chapter 18 · PLANNING AHEAD — the scheduled heartbeat

Cognition has a ten-minute natural baseline (Chapter 11), and a *severe* event adds a pulse
NOW (`pain`). An organism can also **plan**: `heart.schedule_pulse(reason,
after=N)` marks a **future baseline beat** — a countdown (`after=N`) or a scheduled beat
(`at=K`). This is how an AppAI **chains thoughts**: if, mid-thought, it knows it must process
something later, it schedules the continuation rather than executing the task on every pulse —
baseline cognition continues, while the task stressor appears only on the due beat. The scheduled marker
fires once, through the same path as nociception (the woken snapshot carries `scheduled: True`);
the MIND can also call it from `AppAIRuntime.schedule_pulse`.

Planning is measured in **beats** — the organism's native unit of time (it has no innate sense of
the wall clock; a host maps seconds → beats). `pain` is the *now* version of this command;
`schedule_pulse` is the *later* version, and `cancel_pulse` changes the plan.

```python
org.heart.schedule_pulse("continue-the-plan", after=3)   # annotate beat 3 with this plan
# beats 1-2: baseline cognition; beat 3: baseline cognition with scheduled=True
```

**Proven live:** an organism plans three beats out, keeps its baseline cognition on earlier
beats, and receives the scheduled stressor exactly on the due beat.

## Chapter 19 · WEARING A FACE — one organism, many front-ends

The Body, the nine organs, and the append-only VCW are the *invariant substrate* — the nervous
system. A **phenotype** (a *face*) is the *swappable layer*: a whole front-end — a spreadsheet, a
CLI, a calculator, a phone shell — whose source is sealed into a private VCW band. The organism
does not *run* apps; it **wears** them. Same self underneath, different expressed morphology.

Four laws keep it honest:

- **SELF-encrypted** (Chapter 10): a face is sealed under the genesis key, so it is unreadable —
  and un-wearable — as OTHER. A copied nest in another body gets garbage, not the source.
- **Source, never executed here:** wearing returns a *boot manifest* (source + entry + the controls
  it needs) that a **host** renders. The organism never exec's a front-end — that is exactly what
  the skill sandbox (Chapter 6) forbids.
- **Append-only** (Chapter 4): every save and every change of face is an immutable, hashed event.
  The active face is the *latest* wear-event; the biography is never rewritten.
- **The socket:** a face declares the `controls` it expresses and may only plug into controls the
  nervous system can actually drive (the Human Surface Map). A face reaching for an unsocketed
  control is refused.

And **the default face**: every hatched organism is *born wearing* its origin surface — the app it
was made from — sealed into its VCW from the first breath. Even if no other face is ever added, the
organism always holds an encrypted copy of its own source: a self-reconstruction guarantee, the
sibling of the seed vault (Chapter 16). Faces survive a chosen rebirth (the genesis key persists),
and the old generation keeps its own readable copy in the sealed ancestor.

```bash
python -m mantle lifecycle authorize hatch examples/spores/calculator.png nest/ --approve --out=hatch-auth.json
python -m mantle hatch examples/spores/calculator.png --out=nest/ --auth=hatch-auth.json
python -m mantle face-save nest/ notepad examples/notepad_appai/index.html --kind=html
python -m mantle face-list nest/                          # origin (default, worn) + notepad
python -m mantle face-wear nest/ notepad                  # the boot manifest a host renders
python examples/phenotype_demo.py                         # the whole story, end to end
```

**Proven live:** an organism is born wearing its origin face, seals a second face (the real
maintained Notepad AppAI surface) into its VCW, wears it (the source recovers byte-for-byte), keeps the
change append-only, refuses to be read by an OTHER body, and carries its default face across a
rebirth — all with no model call.

## Closing · THE PORTRAIT — the organism paints itself

At the end of `teach` (and of every hatch), the organism renders its own state as a
real PNG — band pressures with the 0.75/0.90 notches, the organ strip with the Brain
lit only when fused, the lineage strip of sealed ancestors, the immune margin. The
first picture of any organism is its own.

```bash
python -m mantle face nest/ my_appai.png
```

---

## Writing your own germ (the practical appendix)

A **germ** is the complete build document an AppAI travels with — the same schema
`examples/eggs/greeter.json` uses. Start from it and change five things:

1. **identity / truths / commandments** — who this creature is. Be specific; the
   Primer is immutable and the commandments become the immune system's seed.
2. **genome** — extra app bands (heads 550–749) with a span sized to churn and a
   declared purpose. The reserved eight are always present.
3. **reflexes** — the deterministic behaviors, from the fixed vocabulary. If you find
   yourself wanting arbitrary code here, it is either an *instinct* (give it proving
   cases) or it belongs in Phase 2.
4. **controls** — every human-visible affordance, so the surface map is honest from
   birth.
5. **instincts** — skills with proving cases. No case, no trial; no trial, no reflex.

Then hatch it directly, or pack it into a spore — the one artifact that carries the
germ plus build instructions any coding agent can read:

```bash
python -m mantle lifecycle authorize hatch my_germ.json my_nest/ --approve --out=hatch-auth.json
python -m mantle hatch my_germ.json --out=my_nest/ --auth=hatch-auth.json
python -m mantle spore pack my_germ.json my_app.png    # ...or package it as a spore first
python -m mantle audit            # the full gate, anytime
python -m mantle prove            # the current security invariant suite
python -m mantle mind             # fuse the offline MIND and watch containment
python -m mantle assimilate <existing-app> --dry-run    # Path B: dissect, don't rewrite
```

And the substrate itself, as one readable file: `examples/vcw/vcw_cube.py`
(`python examples/vcw/vcw_cube.py selftest` proves every format rule;
`python examples/vcw/interop.py` proves the standalone and the engine speak identical
bytes).
