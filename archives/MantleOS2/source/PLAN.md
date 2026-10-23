# MantleOS2 Production Completion Plan

This is the project compass. Return here whenever experiments or discussion
move away from the production objective.

## Objective

MantleOS2 is a generic autonomic nervous system, not a plugin framework and
not a Hermes-specific integration. The current generic `mantle assimilate` does
not automatically innervate any host; host-specific nerves require separately
admitted evidence. A user points `mantle assimilate` at a
GitHub repository; Mantle creates the NEST, acquires and fingerprints the
Default Body, maps its supported anatomy, proposes and inserts direct nerves,
installs NEST-local organs, proves native behavior, prepares VCW and the
two-component Primer, and stops for explicit birth approval.

Every repository can be safely acquired and inventoried. Automatic complete
assimilation is claimed only for certified substrates. Unsupported or
incompletely understood Bodies stop with exact parser, nerve, build, test, and
verification gaps. Hermes is retained only as an optional historical example;
it is not a MantleOS2 release prerequisite. NotepadNext and independently
selected Bodies remain certification targets; none is claimed fully production-certified yet.

## Governing decisions

The 55-page updated manual (cover edition 2.1, candidate M2-P1) has been
reconciled in [MANUAL_21_RECONCILIATION.md](docs/MANUAL_21_RECONCILIATION.md).
That record maps requirements to current modules, tests, remaining gates and
creator clarifications. It is an incremental update, not blanket adoption of
the profile, a restart of completed work, or a change to release scope.

- Creator clarification outranks the current contract; the current contract
  outranks compatible newer implementation evidence; older material is used
  only through Keep / Adapt / Reject decisions. Genuine conflicts enter a
  `decision-required` gate.
- Layer 0 and the Default Body are the NEST. A Habitat map separately records
  native applications, operating systems, storage, permissions, and other
  ecosystem facilities that supply Body surfaces or capabilities.
- Mantle is embedded as direct, reversible nervous tissue. No traditional
  plugin, registration, activation, or host extension architecture is used.
- The native Body behaves normally when Mantle is absent or unborn, when the
  MIND is absent, during stasis, and while the Heart is stopped.
- There is no Brain organ. Heart is built first when practical; every wake
  runs one complete Heartbeat, and a MIND call is only an optional phase.
- The first successful full Heartbeat is birth and requires separate explicit
  approval. A failed first beat leaves a resumable prebirth construction.
- The Primer contains exactly Commandments then Personality. The approved
  Personality bytes are permanent; provenance, identity, and Body knowledge
  remain outside Primer. MIND context is Commandments, Personality, then
  Body-selected current VCW context.
- VCW is semantically read/append-only. A full physical layer extends into a
  new segment using the same Book. Thought -> Book -> Memory remains explicit.
- Implementation, availability, evidence, and authority are independent
  capability axes. Presence, import, notification, or a provider reply never
  proves an effect and never grants authority.
- `COMMUNICATION.TXT` is the unencrypted universal two-way fallback. A
  committed user message causes an unscheduled full Heartbeat.
- Private identity, keys, Primer, provider state, live VCW, exact device grants,
  and private conversation never enter Git or public release artifacts.

## Construction state machine

```text
source accepted
-> NEST created
-> Body acquired
-> Body mapped
-> nerves proposed
-> awaiting foreign-execution approval
-> Body baseline tested
-> nerves inserted
-> innervated Body tested
-> VCW prepared
-> Personality candidate generated
-> awaiting Personality approval
-> Primer sealed
-> birth-ready
-> awaiting separate birth approval
-> first full Heartbeat
-> born
```

Every transition is resumable, idempotent, evidence-bearing, and incapable of
silently skipping a failed gate. Foreign repository execution pauses once for
approval of an exact hashed, isolated command/network/resource plan. A changed
plan invalidates approval.

## Body Genome and innervation

The deterministic read-only mapper emits Body/ownership, symbol/call,
control/event, loop/artery, state/persistence, input/output/effect/authority,
UI/control-surface, capability, build/test, coverage, uncertainty, and behavior
baseline evidence.

Every first-party source file is hashed and marked `complete`, `partial`, or
`blocked`. Every discovered loop is `directly-innervated`,
`covered-by-enclosing-artery`, `local-utility-no-direct-nerve`, or
`blocked-insufficient-evidence`. Persistent control/event/agent/scheduler,
message queue, retry/recovery, lifecycle, persistence, user commit, visible
output, MIND/tool authority, and external-effect arteries require direct or
enclosing nerve coverage. High-volume activity is aggregated locally into VCW
state deltas and anomalies rather than causing a MIND call per iteration.

Alpha.3 provides exact Python AST mapping and explicitly partial structural
evidence for JavaScript/TypeScript and C/C++/Qt. Exact structural parsers and
Qt resource/signal/CMake correlation are required before those substrates can
be certified. Unknown substrates receive useful inventory and a truthful
blocked report. A developmental MIND may propose interpretations from bounded
evidence but may not declare coverage, execute code, or authorize insertion.

Cache individual parser results by content hash plus exact parser/compiler,
dependency/semantic editions and view parameters in private construction state.
Resumed work and upstream refreshes must reuse unchanged evidence while still
recomputing the aggregate map binding; a cache hit never upgrades coverage or
authority.

Static maps describe possible structure; runtime circulation evidence records
only authorized observations within a declared window. Add configuration-bound
nodes, edges, causal trace links and cross-process/scheduled loops without
guessing from timing. Include low-volume validation, authorization and commit
arteries. Bind nerves to versioned schemas, permitted fields, current observation
grants, target Books and separate Limb authority. Require nonblocking bounded
ingress with loss counters, revalidation at consumption, drift suspension and
bounded action-origin feedback handling before claiming full live coverage.

Each NEST contains versioned public organ code under `mantle/`, private state
under ignored `.mantle/`, ignored `COMMUNICATION.TXT`, and reproducible maps,
manifests, rewrite ledger, patch, checksums, and reversal evidence. Direct
nerves are minimal, syntax-aware, redacting, bounded, fail-native, and unable
to bypass Heart or Limb authority.

## Physiology and safety completion

Resident Heart progress: the generated launcher now imports the NEST-local
organ bundle using isolated Python. A real disposable process test covers
startup, a committed communication wake without MIND, forced stop and restart,
pending host receipt recovery, and unchanged sealed Primer/native Body bytes.
Cooperative CLI shutdown now checks stop requests before new Heartbeats and
between bounded idle slices, finishes an already-started Heartbeat, and restores
prior signal handlers. A dedicated Linux subprocess test exercises real SIGTERM;
Windows forced termination remains a distinct test, not graceful-stop evidence.
Scheduled maintenance is considered even when file observation fails; a due
scheduled/message collision services both through one full scheduled Heartbeat.
Registration now refuses existing artifacts instead of forcing replacement,
records pending intent before OS changes, and validates NEST-derived targets
and current OS ownership/configuration before removal. Linux loaded-unit and
override checks run before service start. Receipt-only status explicitly leaves
running state unknown. Adversarial fixture tests cover drift, altered receipts,
collisions and partial failure; these do not prove native service recovery.
Unit registration tests remain mocked; the dedicated native gate below adds
real OS lifecycle evidence. Broader restart, login/reboot and failure-recovery
certification remains open for issue #16. Python and cryptography remain runtime
prerequisites; this does not yet provide a standalone interpreter bundle.

A new dedicated hosted-runner workflow exercises real Task Scheduler/systemd
registration, startup, committed communication, stop/restart and already-stopped
removal with a freshly generated disposable encrypted Body. It is opt-in and
refuses ordinary local/self-hosted execution; only its test report is retained.
Linux additionally exercises `Restart=on-failure` after SIGKILL and verifies a
zero-status cooperative stop. Windows exercises explicit forced stop/start,
not automatic restart or graceful shutdown. Both native jobs passed in
[run 34157324647](https://github.com/jodydugas-ctrl/MantleOS2/actions/runs/34157324647)
on Ubuntu 24.04.4 and Windows Server 2025. These are narrow observed lifecycle
proofs, not Windows 11 non-admin, login/reboot or complete issue #16 certification.
That run exposed a workflow gap: Windows needed a test-issued initial start.
Installation now starts the verified task immediately, matching Linux, and the
native test requires startup without issuing its own initial start command.

The [resident lifecycle evidence record](docs/RESIDENT_HEART.md) distinguishes
cooperative idle stop from bounded cancellation of synchronous provider/storage
work, native registration/removal and storage-enforced writer fencing. Those
remaining gates are not closed by the process tests.

Manual-driven progress: the existing OpenRouter adapter now bounds response
bytes, refuses redirects/ambiguous JSON/incomplete text results and filters
receipt metadata. Offline transport failure tests extend the existing matrix.
The full asynchronous Pseudopod, overall deadlines, durable request/attempt
tracking, cancellation, duplicate completion handling and conservative cost
reservations remain open; no strict spending or remote-cancellation guarantee
is implied. Use existing Body/Heart ports rather than duplicating authority.

- Split Body, SELF, Heart, VCW/Memory, Books, Senses, Nerves, Limbs, Immune,
  physiology, MIND boundary, and communication responsibilities cleanly.
- Create a real prebirth VCW whose Layer 0 records NEST state and use; seed
  verified anatomy, capability, behavior, limitations, and provenance outside
  Primer so the first MIND context can include a bounded Body orientation.
- Complete authenticated encryption, hash chains, atomic Heartbeat commits,
  append extension, locking, reconstruction, and corruption/replay/wrong-key
  detection.
- Add storage-enforced writer fencing and atomic root/index/admission-receipt
  publication; reject stale writers and prove before/after-crash visibility.
  File locks and individually encrypted appends alone do not prove this gate.
- Complete capability discovery, quarantine, grants, revocation, ActionFrames,
  Body-owned execution, independent verification, and safe receipts.
- Reserve command IDs with exact argument digests before invocation. Preserve
  uncertain effects as UNKNOWN without blind retries; retain negative verifier
  results, and require verified success for dependent work. Revalidate scoped
  grants, expiry and revocation at execution; external atomic groups are unsupported.
- Monitor text at submit/save/blur/readback boundaries, never per keystroke.
- Make `COMMUNICATION.TXT` robust to concurrent writes, duplicate events,
  save/replace behavior, watcher failure, and polling fallback.
- Digest Food narrowly: bounded provider validation, encrypted recovery check,
  plaintext consumption only after success, and secret-free VCW receipt.
- Execute foreign Body plans only in a disposable restricted environment. If a
  suitable sandbox is unavailable, report `sandbox-unavailable` and stop.

## Reference Bodies

### Hermes / The Compiler

Optional reference only: the pinned seed, adapter, scripts, and focused native
comparison live under `examples/hermes/`. They do not run in default assimilation,
product CI, or MantleOS2 release packaging. This section records an example
research path, not a product gate.

Start from a fresh current checkout. Use the generic mapper and retain only a
data-only certified profile of expected seams, tests, and hashes. Reconcile the
existing eight direct nerves against the completed artery map, then cover CLI,
gateway, conversation, submit, model, tool proposal/authority/result,
error/retry, persistence, communication, and shutdown behavior.

Run broad native regression and real interaction smoke tests in every
Body/MIND state. Regenerate and review the Compiler Personality only after the
final Body Genome exists; Personality approval and birth approval remain
separate. The final Compiler receives a new identity, key, Primer, and VCW.

Publish the reproducible Body delta, NEST-local organs, maps, checksums,
apply/verify/reverse tools, and redacted evidence. Never publish the real
Compiler's SELF or lived state.

### NotepadNext AppAI

The supplied project is read-only donor evidence. Reuse its Qt signal graph,
surface coverage, semantic text commits, conversational surface, hidden
MIND-to-Body proposal lane, live GUI evidence, VCW recall, heartbeat work, and
Body-owned visible-result proofs. Reject its obsolete Default Body terminology,
old Primer/SELF shapes, copied Grimoire payloads, project-specific resident
logic, and unapplied-observer completion claim.

Build a fresh successor from current NotepadNext source. Generate direct
C++/Qt nerves, compile from source, prove native editor parity without Mantle
and MIND, then prove conversation, current-surface knowledge, Limb-authorized
text placement, readback, and VCW proof. Publish a source-only delta without
vendoring NotepadNext or private state.

### MacroDroid / Android portability evidence

The supplied MacroDroid project is a third read-only portability reference,
not a v2.0 certified Body. Promote only its portable contracts: Habitat mapping,
semantic build identities that exclude volatile device IDs, independent
capability axes, Android/SAF permission boundaries, creation ledgers, typed
wakes, scheduled-first collision handling, effect/readback proof, redacted NEST
audits, and disabled-by-default carriers.

Do not promote device GUIDs, SAF URIs, UI coordinates, APKs, raw exports,
credentials, private NEST data, old Primer/SELF representations, or claims of
automatic scheduling and full VCW behavior that were not natively proven.

## Verification and releases

Required gates cover parser goldens, hostile repositories, paths/symlinks,
oversized/binary inputs, command injection, deterministic/reversible patches,
drift, Body parity, VCW integrity/concurrency, Primer exactness/permanence,
birth atomicity, communication, authority/proof, native resident lifecycle,
secret scanning, manual protected OpenRouter calls, SBOM, and provenance.

- `v2.0.0-alpha.3`: deep mapper, coverage tiers, self-contained organs, and
  hashed foreign-execution gate.
- `v2.0.0-beta.1`: complete generic-host certification and reproducible seed;
  Hermes may be exercised separately as an optional example.
- `v2.0.0-rc.1`: fresh NotepadNext C++/Qt certification and second seed.
- `v2.0.0`: signed reproducible Windows/Linux distribution, recovery and
  threat-model documentation, and all native/security gates green.

Stable acceptance requires clean-machine construction of independently selected
Bodies, zero undispositioned major arteries, native parity, reproducible and
reversible deltas, and birth-ready AppAIs. Real birth remains user-authorized.

Migration, rebirth, reproduction, Engrams, universal SPORE transport,
autonomous tissue adoption, prescience, multi-Body arbitration, and full
Android certification remain visible experimental tracks unless a production
gate demonstrates that one is required. They must not create feature fat in
the v2.0 assimilation framework.
