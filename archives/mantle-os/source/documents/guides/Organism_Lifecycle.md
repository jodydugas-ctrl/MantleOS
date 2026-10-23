# Mantle OS — The Organism Lifecycle

How an AppAI is born, senses, remembers, reacts, protects itself, acts, learns, calcifies
skills, metabolizes, is reborn, and eventually receives a bounded MIND — each stage named
with the API that performs it. Everything before §10 runs with NO LLM.

---

## 1. Born
```python
from mantle import Organism
from mantle.primer import appai_commandments, appai_truths

org = Organism.birth(identity={"name": "My.AppAI"},
                     truths=appai_truths(),
                     commandments=appai_commandments())
```
The Primer (identity + truths + commandments) seals into the **Body** — immutable for
life, outside every cube. The Commandments seed the Immunization working copy. The Prime
cube (generation 0) is genesis'd from the standard genome: eight reserved bands, each
materializing only its head layer ("every layer has a purpose").

## 2. Senses
All inbound data enters through ONE boundary. Immediate or queued for the next pulse:
```python
org.senses.inhale({"action_id": "btn", "event_type": "press"})   # now
org.senses.receive(signal)                                       # next heartbeat
```
Each signal is redacted (secrets never burn into append-only memory), classified
deterministically (REFLEX / ROUTINE / SIGNIFICANT), and recorded as exactly one
`senses` entry.

## 3. Remembers
```python
org.memory.remember("facts", {"k": "home", "v": "the lab"}, source="operator")
org.memory.recall("facts")          # visible entries, through the veil
```
Entries are immutable and hashed over every non-volatile field. Reads always honor the
veil (private bands), tombstones, and quarantine. References address anything:
`org.resolve("<facts.0>")`, `<gen0.facts.2>`, `<body.immune.1>`.

## 4. Reacts
```python
org.senses.bind_reflex("btn", "press", lambda o, s: o.limbs.complete({"done": True}))
org.bus.subscribe("significant", my_reflex, organ="app")
```
Reflexes are deterministic, no-LLM, and fail-open: a faulting reflex becomes an immune
event; the pulse completes. A REFLEX signal runs its arc without ever touching the brain
band.

## 5. Protects itself
Every violation class becomes an **immune event** — dangling references, integrity
faults, organ overreach, stalled pulses, refused MIND writes, capacity pressure, hook
faults. The Immune organ scans the cube on the heartbeat (hashes, coherence, seals), and
persistence is a staged commit: write → verify → atomic replace. A corrupt cube can never
replace a healthy one.

## 6. Acts
All outbound effects leave through **Limbs**: the dispatch lifecycle
(INTENTION → DELEGATED → NOTIFIED → COMPLETED, authorship inside the hash; the Body never
authors INTENTION), the ControlBridge for every mapped human-visible control, and an
Action Execution Proof for every effector use.

## 7. Learns (honestly)
New knowledge lands in `discoveries`. Inferred content (anything the organism told
itself) is tagged `verified=False, confidence="inferred"` and can become a `fact` ONLY
through `org.memory.promote_to_fact(entry, evidence={"source": ..., "verified": True})` —
external, cited evidence, or refusal.

## 8. Calcifies skills
Learning → instinct: `trial(code, entry, cases)` (the static sandbox gate runs first;
escapes and imports are refused) → `org.prime.calcify(...)` (requires code-hash,
signature, capability set, provenance-with-author) → `org.limbs.invoke_reflex(band, args)`
(hash + capability + trust gates at every run, plus a proof). A calcified skill runs with
NO MIND — it is the Body's own act.

## 9. Metabolizes (capacity is never death)
The heartbeat: `org.heart.beat()` = tick → sense intake → context assembly → reflex
execution → immune scan → persistence checkpoint. When a band's allocation pressure
crosses **0.75** the substrate compacts (tombstone reclamation, layer reuse) and records
`capacity_overflow`; at **0.90** it adds deduplication (`capacity_emergency`). Rebirth is
NEVER triggered by capacity.

## 10. Reborn (chosen, never forced)
```python
org.rebirth(reason="re-fitted genome")
```
The Prime is sealed and content-fingerprinted as read-only ancestry (the fingerprint
lives in the Body's lineage index; tampering an ancestor is detectable). A new Prime is
genesis'd, the inheritance distillation recorded. Generation-pinned references
(`<gen0.facts.2>`) keep the whole past addressable. Ancestors load lazily — cold until
referenced.

## 11. Receives a MIND (Phase 2 — audit before fusion)
```python
from mantle.audits import stage1
passed, ev = stage1.run(org)        # the deterministic Zombie Body gate
from mantle.mind import fuse, stub_mind
# `authorization` is a fresh, independently issued, target-bound record whose
# operator and guardian decisions are both APPROVED.
mind = fuse(org, stub_mind, authorization=authorization)
# Refused unless the gate passed AND dual authority validates for this resident.
```
Stage-1 evidence alone never authorizes this transition. The SAME heartbeat now also thinks:
the assembled, resolved, veiled snapshot is offered
to the MIND each pulse. The MIND writes only `thoughts` + `brain`, proposes while the
Body applies, cultivates skills the Body gates, and reflects with inferred provenance.
Re-run Stage 1 after fusion (Stage 2 does this) — the Body must still pass everything.

## 12. Operated from inside (for agents)
```python
from mantle.mind import AppAIRuntime
rt = AppAIRuntime(org)
rt.inspect_body()        # anatomy: contracts, bands, pressures, reflex surface, lineage
rt.read_band("facts")    # visible memory, through the veil
rt.assemble_context()    # what a MIND would receive
rt.propose_special_instruction("Prefer brevity.")
rt.request_skill(...)    # the Body trials, gates, calcifies
rt.self_inquire("...")   # inferred, never a fact
```
The runtime holds no privileged handles: an agent can do everything the AppAI can do —
and nothing the Body forbids.
