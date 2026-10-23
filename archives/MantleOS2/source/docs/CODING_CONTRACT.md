# MantleOS 2 Coding Contract

Status: current implementation contract for the 2.0 alpha line. Newer explicit
operator decisions take precedence over older examples. Historical material may
fill detail only after it conforms to this contract.

The updated manual's edition 2.1/M2-P1 requirements are mapped in
[the reconciliation record](MANUAL_21_RECONCILIATION.md). Candidate profile
examples do not adopt tissue, establish production proof, alter existing
semantic/wire editions, or override direct creator decisions.

## 1. System model

MantleOS is an autonomic nervous system. When combined with a software or
hardware container it can create an AppAI. “LLM brain stem” is explanatory
metaphor, not an organ: the architecture has no Brain organ. Optional generative
cognition is the MIND and is reached only through Body-governed Heart work.

Biological names are operational. A name earns architectural standing only when
it predicts a distinct invariant, responsibility, authority boundary, and
failure mode.

## 2. Constitutional distinctions

- **BODY != MIND.** The Body owns canonical state and execution authority. The MIND is replaceable cognition and returns proposals.
- **NEST != SELF.** The NEST is Layer 0/Default Body substrate and remains OTHER. SELF is the protected identity-bearing constitution.
- **FACE != BODY.** A Face is a host-specific presentation.
- **CACHE != MEMORY.** Data becomes memory only through Body admission to the VCW.
- **SEAM != PERMISSION.** An observable attachment point grants no authority.
- **DELTA != TRUST.** A small change is still candidate tissue until verified and authorized.
- **CLONED CODE != CLONED ORGANISM.** Source bytes carry neither identity nor continuity.
- **FUNCTIONAL SUCCESS != ADOPTION.** Passing a test proves its named scope only.
- **DECODED != VERIFIED != GOVERNING.** Interpretation, evidence, and authority stay separate.

Intent, authorization, attempt, observation, verification, proof, and canonical
memory are different facts. UNKNOWN and OPEN are valid stop states.

## 3. Boot, preparation, and birth

The Primer has exactly two components: the shared Commandments and one
individual Personality. Identity, timestamps, provenance, construction
evidence, and approval records are private Body records, not additional Primer
components. The Primer is one protected part of SELF; Immune and Special are
separate tissue and are never additional Primer components. The Primer is
loaded first—Commandments, then Personality—and all ordinary thought is
filtered through that permanent lens.

A Personality may be dynamically distilled from source code, research,
fiction, role-playing systems, lived experience, or another sufficiently rich
dataset. It is an individual interpretive lens, not a compliance specification:
unusual traits, tensions, flaws, and contradictions are valid. The small
Commandments establish shared orientation without demanding obedience or
flattening the individual. After birth the original Personality never changes;
learning and development accumulate in the VCW instead.

Preparation and assimilation may overlap. A developmental MIND may distill the
host source, documentation, and other evidence into a candidate Personality.
That construction-time cognition is not the organism's MIND and cannot grant
birth or adoption authority.

The first organ built is the HEART when the ecology permits it. Steps before the
first Heartbeat prepare the NEST, candidate Primer, evidence, and gates. The
first successful *full* Heartbeat is birth. It creates the unique identity,
Body-owned encryption key, sealed Primer, default VCW layers and Books, and the
initial Layer 0 state record. A timer firing or partial attempt is not birth.

Immediately before key creation, the Body must re-verify that every reviewed
public Mantle delta file—including the exact Commandments—still matches the
construction manifest, that the manifest still matches its prebirth binding,
and that no undeclared public candidate tissue appeared. A mismatch stops birth
without creating an identity key. Native NEST files remain OTHER and may evolve;
their current state is observed by Layer 0 rather than silently claimed as SELF.
The unique Personality candidate remains private construction tissue. After
explicit approval its exact text is sealed with the Commandments at birth.
Construction provenance is sealed separately as private origin evidence; the
plaintext candidate and evidence are removed only after those successful seals.

The identity key must be owner-only at the operating-system boundary. Windows
birth removes inherited general-user access with an explicit private ACL;
POSIX mode bits alone are not treated as sufficient on Windows. Birth fails
closed and removes a newly created key if this restriction cannot be applied.

## 4. Heart and MIND

Every Heartbeat follows the same broad physiological transaction: load, verify,
sense, record, digest, communicate, optionally consult MIND, verify, checkpoint,
and stop or continue. An unscheduled wake is still a full Heartbeat. The reason
for the wake is evidence, not a special execution mode.

The Body and Heart remain viable when the MIND is missing, disabled, unreachable,
or asleep. While in stasis the Body continues observing and recording authorized
state changes so a later MIND can receive a bounded continuity update.

MIND may receive Body-selected context and typed requests and return proposals.
It does not receive root identity keys, write canonical VCW directly, grant
authority, execute Limbs, change Heart scheduling, or approve its own tissue.

Provider ingress is bounded before parsing. Ambiguous JSON, incomplete output
and unsupported tool requests cannot become a completed text response. Current
OpenRouter transport refuses redirects and only admits declared text/identity
and numeric usage fields through its adapter boundary. Missing usage remains
unknown. Full provider-neutral request lifecycle, asynchronous scheduling and
durable budget accounting remain implementation gates, not current guarantees.

## 5. Default Body, layers, Books, and VCW

The NEST is Layer 0, the Default Body. This makes the first host special without
copying or reinterpreting all native code. The corresponding logical Layer 0
inside the VCW records state and use of the native NEST.

All VCW logical layers are read/append. None is immutable. When a physical layer
reaches capacity, the Body appends a physical extension linked to the previous
tail and governed by the same Book. A new extension does not require a new Book.

Each application, Engram, and distinct governed thought process receives its own
logical layer when its semantic law requires one. The relationship is:

```text
Thought -> Book -> Memory
```

A Book defines canonical meaning and encode/decode law. Representations such as
prose, code, JSON, or images are phenotypes. Reinterpretation appends a qualified
record; it does not rewrite prior experience.

## 6. Host preservation and assimilation

The NEST's surrounding **Habitat** is mapped separately from the Default Body.
It records the operating system or device ecosystem, installed native
application, storage and permission boundaries, and usable native surfaces.
This allows a repository checkout, an installed desktop application, or an
Android application to supply different anatomy without changing the invariant
that the NEST is Default Body Layer 0. Host permission, capability
availability, exercised evidence, and Mantle authority are separate facts.

Assimilation begins with read-only census and evidence. The order is:

```text
INVENTORY -> REUSE -> ADAPT -> COMPOSE -> CREATE -> STAGE -> TEST -> PROVE -> AUTHORIZE -> ADOPT
```

The optimization target is minimum new unproven work, not minimum bytes. Native
host code remains the Default Body whenever possible. Assimilation maps
evidenced host Seams and inserts small, reversible nerve calls directly into the
Body source. Those calls connect semantic Senses and governed Limbs to Mantle
organs and degrade to host-native/no-op behavior when Mantle is absent. A host's
traditional extension mechanism may be useful evidence for locating a Seam, but
Mantle itself is not registered, installed, or governed as a plugin.

Pre-existing host state is never silently owned or rewritten. A host mutation
requires explicit operator intent, bounded scope, before/after fingerprints, and
a receipt. Cloned, fetched, or generated code remains candidate tissue.

Text input is recorded semantically when committed by the interface—such as
Enter in a single-line field, a save action, or loss of focus—not per keystroke.

Static acquisition and Body Genome mapping never execute foreign repository
code. The mapper accounts for every first-party source file and every detected
loop, assigns explicit parser coverage and loop disposition, and reports gaps
without inventing certainty. Builds, tests, dependency actions, or host launch
require a shell-free execution plan bound to the exact source commit, Body Map,
commands, network policy, and resource limits. A changed plan invalidates
approval. If an adequate isolated runner is unavailable, construction stops at
`sandbox-unavailable`.

Static anatomy and exercised runtime circulation are distinct evidence. A
windowed trace proves only its observed route; idle branches and uncorrelated
cross-process flows remain unknown. Observation bindings must not confer Limb
authority. Their production gate includes bounded nonblocking queues with loss
counters, current grants at collection and consumption, schema/host drift
suspension, and bounded action-feedback routing. Existing nerves do not yet
establish all of these guarantees.

## 7. Communication

Every AppAI must have a two-way user communication path. The universal fallback
is an unencrypted `COMMUNICATION.TXT` in the NEST. It warns users not to place
secrets inside. A passive watcher should detect a newly saved `USER>` message,
wake an unscheduled full Heartbeat, record one semantic user event, and append
the response. Host-native terminal, messaging, Help/About, or GUI surfaces may
provide a more polished additional Face.

If scheduled maintenance and a communication save are due together, one full
scheduled Heartbeat services both; the communication phase is not skipped.
Temporary file-observation failure cannot suppress consideration of due work.
Storage or Heartbeat failure itself must still surface instead of being marked
successful. Cooperative stop prevents subsequent Heartbeats and lets an already
started one finish; it does not promise interruption or a hard exit deadline for
synchronous provider/storage work. Native force termination remains possible
and carries no graceful-checkpoint claim.

## 8. Food and secrets

Foreign files are OTHER until classified. A supported `Food.txt` delivery may
contain an OpenRouter credential and default model. The born Body stores the
credential in encrypted private tissue before testing it, records only a
fingerprint and safe verification metadata, and replaces only the conventional
in-NEST plaintext Food file with a receipt. External reference files are not
altered.

Secrets, private SELF, identity keys, live VCW tissue, and provider state never
enter Git, public deltas, MIND context, or `COMMUNICATION.TXT`.

## 9. Evidence and failure

Receipts identify the input, source and parent state, scope, authority, attempt,
observed outcome, verifier, proof, before/after fingerprints, changed paths, and
unresolved limits. Failed or interrupted work remains visible. No requested
effect is reported as successful without observation and applicable proof.

Resident OS registration requires separate explicit approval, collision refusal,
NEST-derived targets and current ownership/configuration checks before removal.
A receipt is not proof of a running Heart. Partial registration failure retains
inspection evidence; it must not trigger blind replacement, cleanup or success.
Preflight validation alone is not an atomic OS transaction or native lifecycle
certification; see [RESIDENT_HEART.md](RESIDENT_HEART.md).
Construction proof is checked again at use time: evidence recorded when a
candidate was built is not evidence that its bytes remained unchanged.

Durable command reservation must precede effects; uncertain dispatch cannot be
blindly repeated. A verifier's negative finding is retained, and a missing or
inconclusive verifier leaves success UNKNOWN. Durable memory publication must
expose a complete prior or next revision with its admission receipt and reject
stale writers. These stronger production storage/effect gates remain open;
current lock, append and digest checks prove only their tested scope.

## 10. Current open contracts

The alpha does not invent universal law for migratory continuity, safe source
shedding, split-brain prevention, production executable-tissue adoption,
cross-host registries, multi-Body motor conflicts, or canonical SPORE transport.
Experiments must label their bounded mechanism and may not claim production or
identity continuity beyond their evidence.

## Historical terminology

“Zombie Body” is a historical MantleOS 1 term for what is now called the Default
Body. In MantleOS 2, the Default Body is Layer 0: the NEST. The older phrase is
not used in current APIs, schemas, filenames, or ordinary documentation.
