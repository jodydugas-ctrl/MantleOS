# Hermes AppAI Resident Implementation Plan

> **Historical plan:** retained as implementation provenance. Current architecture, status,
> authority, temporary-directory, and verification requirements live in `README.md`,
> `docs/MIND_READINESS.*`, and the executable tests; they override stale task wording below.

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Turn the standalone Hermes Mantle Addon into an additive, fail-open MantleOS resident that gives Hermes a deterministic nine-organ Body, durable VCW memory, SELF/OTHER boundaries, action proofs, immunity, metabolism, lineage, and Stage-1 certification before any explicit MIND fusion.

**Architecture:** Use Mantle Path B (`@BG:h` / Hospitari) rather than rewriting Hermes. Hermes remains the cognitive host; the addon registers native Hermes plugin hooks and tools while a vendored Mantle autonomic Body wraps it. Each Hermes profile maps to a resident resolved at invocation time. Phase 1 runs deterministically without an LLM; a bounded MIND requires fresh Stage-1 evidence plus separate, target-bound operator and guardian approvals.

**Tech Stack:** Python 3.11+ standard library, Hermes plugin APIs (`register_tool`, `register_hook`, `register_command`), vendored Mantle OS 1.2.0, `unittest`, JSON receipts, VCW PNG cube persistence.

---

## 1. Binding interpretation and non-negotiable invariants

This is not merely a collection of Mantle CLI wrappers. The plugin is intended to add a real AppAI nervous system around Hermes wherever the host surface permits.

### Preserved host behavior

- Do not patch or modify Hermes core.
- All integration is through documented plugin APIs.
- Hook failures are caught, converted to Immune events when possible, and otherwise fail open.
- Disabling/removing the plugin restores ordinary Hermes behavior.
- Existing Hermes memory, sessions, approvals, tools, and provider routing remain authoritative at the host layer.

### AppAI laws

- Body before brain.
- Stage 1 before MIND readiness; readiness is not fusion authority.
- Separate target-bound operator and guardian decisions are both required for MIND fusion.
- All inbound signals observable through Hermes plugin hooks enter through Senses.
- All model-requested tool effects observable through Hermes plugin hooks pass through Limbs.
- Every captured failure or refused action becomes an Immune event.
- MIND output is inferred/OTHER until independently verified and promoted by Body policy.
- Secrets, raw credentials, unredacted prompts, and raw OTHER code never enter durable VCW memory.
- Capacity triggers metabolism, never rebirth.
- Rebirth is explicit and lineage-preserving.
- Every action record carries provenance and an Action Execution Proof (AEP).

### Honest limitations

Do not claim “Hermes is a full AppAI” until an inventory proves coverage and Stage 1 passes. The honest intermediate label is **Hermes AppAI resident**. Plugin hooks cannot necessarily observe:

- host startup behavior before plugins load;
- effects performed outside Hermes's registered tool dispatcher;
- private provider internals;
- gateway/platform events for which Hermes exposes no plugin hook;
- pre-existing host state created before residency.

Unobservable surfaces stay external host tissue or are recorded as gaps in the signed inventory. They must never be silently labeled as covered organs.

---

## 2. Proposed organ map

| Mantle organ | Hermes surface | Deterministic responsibility |
|---|---|---|
| Heart | `on_session_start`, `pre_llm_call`, `on_session_end`, `on_session_finalize` | pulse sequencing, liveness, checkpoint requests, stalled-turn detection |
| Genome | addon primer/policy files and Body identity | identity, commandments, plugin/Mantle versions, host fingerprint, lineage, DNR |
| Nervous | normalized hook-event bus and context assembler | typed routing, correlation IDs, stable context snapshots, references |
| Senses | `pre_llm_call`, `pre_tool_call`, session hooks | redact/classify/record observable inbound user, session, and tool-intention signals |
| Immune | hook exception boundary, policy guards, integrity scans | quarantine, refusal, integrity faults, secret boundary, audit findings |
| Limbs | `pre_tool_call`, `post_tool_call`, approval hooks | effect lifecycle, actor/authorship, method/result/reason/evidence, AEP |
| Memory | Mantle VCW bands and metabolism | append-only observed facts/events/discoveries; veil, compaction, persistence |
| Brain | dormant Phase-1 socket; optional `pre_llm_call`/`post_llm_call` adapter | inferred thoughts/intentions only; no direct facts/effects/identity keys |
| Reproduction | vault/egg/rebirth tools added after Stage 1 | sealed seed, lineage, explicit reconstruction, no implicit replication |

### Hook-to-signal mapping

| Hermes hook | Mantle signal |
|---|---|
| `on_session_start` | `session.started` → Heart/Senses |
| `pre_llm_call` | redacted `turn.received` → Senses; pulse/context assembly → Heart/Nervous |
| `pre_tool_call` | `effect.intended` → Senses/Limbs; policy refusal → Immune |
| `pre_approval_request` | `effect.approval_requested` → Limbs |
| `post_approval_response` | `effect.approval_decided` → Limbs/Immune |
| `post_tool_call` | `effect.completed` → Limbs AEP; error result → Immune |
| `post_llm_call` | inferred `mind.response` → Brain/thoughts only when fused |
| `on_session_end` | `turn.ended` → Heart checkpoint |
| `on_session_finalize` | final checkpoint and sealed residency receipt |
| `subagent_start` / `subagent_stop` | delegated limb lifecycle with parent/child provenance |

---

## 3. Storage and identity model

- Runtime state root is configurable; default after installation: `$HERMES_HOME/mantle/`.
- During development and tests, all writes stay under `/home/aibox/Hermes Mantle Addon/.runtime/` or an OS-safe temporary sandbox explicitly created for verification.
- One resident Body per Hermes profile by default; session IDs are recorded as contexts within that Body rather than minting a new identity each turn.
- A profile/body identity key stays in Body-owned storage and is never exposed to the model.
- VCW bands use Mantle's standard atlas, including the Reproduction organ.
- Raw user prompts and tool arguments are not persisted by default. Durable records contain redacted classifications, hashes, bounded summaries, result status, and provenance.
- Host state remains host-owned. The VCW stores observations and proofs, not a replacement copy of Hermes's session database.

---

## 4. Implementation sequence

### Task 1: Freeze the current vertical slice as a baseline

**Objective:** Preserve the working `mantle_status` behavior before restructuring.

**Files:**
- Modify: `tests/test_tools.py`
- Create: `tests/test_plugin_manifest.py`

**Step 1: Write a failing manifest contract test**

Assert that the manifest names the addon, declares every registered tool/hook exactly once, and does not advertise unimplemented organs.

**Step 2: Run the focused test**

Run:

```bash
python3 -m unittest tests.test_plugin_manifest -v
```

Expected: FAIL because no manifest-parity helper exists.

**Step 3: Add the smallest parsing helper in the test support layer**

Use standard-library line parsing; do not introduce PyYAML solely for tests.

**Step 4: Run all current tests**

```bash
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 5: Commit checkpoint**

```bash
git add tests
git commit -m "test: freeze initial plugin contract"
```

Before committing, remove generated `.runtime/` and `__pycache__/` artifacts and review `git diff --check`.

### Task 2: Produce the Phase-0 Hermes inventory without host mutation

**Objective:** Generate the required read-only APP_INVENTORY and organ map for the Hermes host.

**Files:**
- Create: `docs/assimilation/APP_INVENTORY.md`
- Create: `docs/assimilation/hermes_organ_map.json`
- Create: `docs/assimilation/host_census.json`
- Create: `tests/test_inventory.py`

**Step 1: Write a failing inventory-schema test**

Require sections for host purpose/runtime/entry points, preserved behavior, observable surfaces, secret boundaries, proposed bands, controls, gaps, and signoff with `files_modified=0`.

**Step 2: Run the test and confirm schema failure**

```bash
python3 -m unittest tests.test_inventory -v
```

**Step 3: Run read-only Mantle assimilation**

Scan `/home/aibox/.hermes/hermes-agent` without executing host source. Direct all output into `docs/assimilation/`. Record a before/after hash census of host tracked files and prove zero changes.

**Step 4: Manually reconcile scanner output with documented Hermes plugin hooks**

Mark unsupported or unobservable surfaces as explicit gaps; do not force every host symbol into Mantle vocabulary.

**Step 5: Run the inventory test and census verification**

Expected: PASS with `files_modified=0`.

**Step 6: Commit checkpoint**

```bash
git add docs/assimilation tests/test_inventory.py
git commit -m "docs: map Hermes host for AppAI residency"
```

### Task 3: Introduce explicit resident configuration and Primer

**Objective:** Define identity, authority, DNR, budgets, redaction policy, and feature gates as data.

**Files:**
- Create: `mantle_addon/config.py`
- Create: `mantle_addon/primer.py`
- Create: `config/defaults.json`
- Create: `tests/test_config.py`
- Modify: `__init__.py`

**Required defaults:**

```json
{
  "body_enabled": true,
  "mind_enabled": false,
  "storage_root": null,
  "dnr": "none",
  "record_raw_prompts": false,
  "record_raw_tool_args": false,
  "max_event_chars": 4096,
  "checkpoint_each_turn": true
}
```

**TDD cycle:**

1. Test deterministic config resolution and rejection of unknown/unsafe fields.
2. Verify RED.
3. Implement immutable config dataclass and Primer builder.
4. Verify GREEN.
5. Test that `mind_enabled=true` without a Stage-1 receipt is rejected.
6. Verify RED, implement the gate, verify GREEN.

### Task 4: Build the resident Body factory

**Objective:** Create/load a Mantle `Organism` for one Hermes profile without invoking an LLM.

**Files:**
- Create: `mantle_addon/body.py`
- Create: `mantle_addon/storage.py`
- Create: `tests/test_body.py`

**Behavior:**

- Birth uses a deterministic Primer declaration but fresh Body-owned identity material.
- Existing residency loads rather than rebirths.
- The nine organ contracts are present.
- Runtime paths cannot escape the configured root.
- Birth/load/checkpoint makes no network or model call.

**TDD:** one test per behavior, RED → minimal implementation → GREEN.

### Task 5: Add the normalized deterministic event bus

**Objective:** Keep Hermes-specific callback shapes out of organ logic.

**Files:**
- Create: `mantle_addon/events.py`
- Create: `tests/test_events.py`

Define a frozen event record with:

```text
event_id, event_type, timestamp, session_id, turn_id, task_id,
actor, authorship, payload, provenance, classification
```

Requirements:

- Stable serialization.
- Secret-like values redacted before event creation.
- Missing optional correlation fields are explicit, not guessed.
- Event-handler faults produce an Immune record and do not re-raise into Hermes.

### Task 6: Implement Senses

**Objective:** Route every observable inbound hook signal through one redacting/classifying boundary.

**Files:**
- Create: `mantle_addon/organs/senses.py`
- Create: `mantle_addon/redaction.py`
- Create: `tests/organs/test_senses.py`

Classify deterministic categories such as `REFLEX`, `ROUTINE`, and `SIGNIFICANT`. Persist one bounded/redacted senses entry per accepted signal. Test API-key patterns, authorization headers, file paths, huge inputs, empty inputs, and repeated inputs.

### Task 7: Implement Heart and Nervous System

**Objective:** Create a deterministic pulse and context snapshot independent of the model.

**Files:**
- Create: `mantle_addon/organs/heart.py`
- Create: `mantle_addon/organs/nervous.py`
- Create: `tests/organs/test_heart.py`
- Create: `tests/organs/test_nervous.py`

Pulse order:

```text
tick → drain senses → assemble context → run reflexes → immune scan → checkpoint
```

Tests must prove registration-order determinism, dangling-reference immunity, and continued operation when one reflex fails.

### Task 8: Implement Limbs and Action Execution Proofs

**Objective:** Observe, gate, and prove Hermes tool effects without replacing the host dispatcher.

**Files:**
- Create: `mantle_addon/organs/limbs.py`
- Create: `mantle_addon/aep.py`
- Create: `tests/organs/test_limbs.py`

AEP fields:

```text
action_id, attempted, ok, method, ref, reason, actor,
authorship, timestamp, evidence[]
```

Rules:

- `pre_tool_call` creates INTENTION/DELEGATED lifecycle records.
- Approval hooks append approval evidence.
- `post_tool_call` creates NOTIFIED/COMPLETED and final AEP.
- Arguments/results are redacted and bounded before persistence.
- Missing completion becomes an explicit unresolved action, never a fabricated success.
- Existing Hermes approval decisions remain authoritative.

### Task 9: Implement Immune boundaries

**Objective:** Turn integrity failures, hook faults, refusals, secret leakage attempts, and malformed tool results into append-only immune events.

**Files:**
- Create: `mantle_addon/organs/immune.py`
- Create: `mantle_addon/policy.py`
- Create: `tests/organs/test_immune.py`

Start in observer mode. Only block a tool call when a narrow, deterministic, operator-configured policy returns a concrete violation. The first release must not invent a second opaque approval system.

### Task 10: Add durable Memory and metabolism

**Objective:** Persist bounded organism evidence in Mantle's VCW while retaining veil, integrity, and capacity behavior.

**Files:**
- Create: `mantle_addon/organs/memory.py`
- Create: `mantle_addon/checkpoint.py`
- Create: `tests/organs/test_memory.py`

Tests must prove:

- append-only hashed entries;
- no raw secrets/prompts/tool args by default;
- staged save → verify → atomic replace;
- load round-trip;
- pressure invokes metabolism rather than rebirth;
- tombstoned/private/quarantined data stays veiled;
- corrupted staged output cannot replace a healthy cube.

### Task 11: Wire Phase-1 Hermes hooks

**Objective:** Register the Body-facing hooks while Brain remains dormant.

**Files:**
- Create: `mantle_addon/hooks.py`
- Modify: `__init__.py`
- Modify: `plugin.yaml`
- Create: `tests/test_hooks.py`

Register only deterministic Phase-1 hooks initially:

```text
on_session_start, pre_llm_call, pre_tool_call,
pre_approval_request, post_approval_response,
post_tool_call, on_session_end, on_session_finalize,
subagent_start, subagent_stop
```

Do not register `post_llm_call` as a Brain writer until Stage 1 passes and fusion is explicitly enabled. `pre_llm_call` may pulse the Body, but Phase 1 must not depend on model output.

### Task 12: Add body inspection and diagnostic tools

**Objective:** Let Hermes and the operator inspect the organism through Body APIs rather than raw VCW mutation.

**Files:**
- Modify: `schemas.py`
- Modify: `tools.py`
- Modify: `__init__.py`
- Modify: `plugin.yaml`
- Create: `tests/test_diagnostic_tools.py`

Add read-only tools:

```text
mantle_status
mantle_vitals
mantle_inspect_body
mantle_read_band
mantle_diagnose
```

All handlers return JSON strings, catch exceptions, and accept `**kwargs`. `mantle_read_band` enforces the veil and never exposes identity keys or raw quarantined entries.

### Task 13: Build a deterministic addon-specific Stage-1 gate

**Objective:** Certify the resident integration, not merely upstream Mantle in isolation.

**Files:**
- Create: `mantle_addon/audits/stage1.py`
- Create: `mantle_addon/audits/invariants.py`
- Create: `tests/audits/test_stage1.py`
- Modify: `schemas.py`, `tools.py`, `__init__.py`, `plugin.yaml`

Minimum rows:

- all nine organs present with validated contracts;
- Body starts and pulses without model/network access;
- Brain dormant and no `post_llm_call` writer in Phase 1;
- Senses is the observable inbound boundary;
- Limbs produces AEPs for observable tool effects;
- hook exceptions fail open and become Immune events;
- secret redaction precedes persistence;
- VCW integrity and checkpoint round-trip;
- capacity invokes metabolism, not rebirth;
- host census unchanged;
- plugin disable/removal leaves host behavior intact;
- no unresolved Grimoire hard-fails.

Add `mantle_audit_resident` and tamper tests proving the gate catches hash, Primer, seal, and hook-boundary violations.

### Task 14: Add explicit MIND readiness, not fusion

**Objective:** Report whether Hermes's existing LLM can be attached as the resident's bounded MIND.

**Files:**
- Create: `mantle_addon/mind/readiness.py`
- Create: `tests/mind/test_readiness.py`
- Add: `mantle_mind_readiness` tool

Readiness requires a fresh Stage-1 PASS and no open hard-fails. The output is a report only. It must not change hooks, config, memory, or cognition state.

### Task 15: Add separately authorized MIND fusion

**Objective:** Allow Hermes's model to extend the certified Body while remaining contained.

**Files:**
- Create: `mantle_addon/mind/adapter.py`
- Create: `mantle_addon/mind/containment.py`
- Create: `tests/mind/test_containment.py`
- Modify: `mantle_addon/hooks.py`

Only after fresh Stage-1 evidence and explicit target-bound operator and guardian approvals:

- register/use `post_llm_call` as a Brain/thoughts writer;
- classify model output as inferred and unverified;
- prevent direct fact promotion;
- prevent MIND ownership of identity, persistence, effect completion, or approval;
- keep Body reflexes and tool guards functional if the model is unavailable;
- re-run all Stage-1 rows plus Stage-2 containment rows.

Fusion must be reversible by setting `mind_enabled=false`; disabling cognition must not damage the Body.

### Task 16: Add Reproduction only after certification and separate reproduction authority

**Objective:** Support sealed seed/vault/egg workflows without leaking Hermes secrets or treating provider caches as storage.

**Files:**
- Create: `mantle_addon/organs/reproduction.py`
- Create: `tests/organs/test_reproduction.py`
- Add gated tools for export/verify/reconstruct

Requirements:

- separate Ovipositio and Resurgere receipts;
- dry seed contains no API keys, auth pools, raw prompts, provider cache, or raw OTHER;
- DNR enforced;
- reconstruction stops at certified Body plus MIND-readiness report;
- no automatic fusion;
- lineage and destination receipts preserved.

---

## 5. Verification strategy

### Focused tests

Use standard-library `unittest` so core verification has no third-party dependency:

```bash
python3 -m unittest discover -s tests -v
```

### Real Hermes plugin discovery

For each registration change, create an OS-generated temporary Hermes home and project-plugin sandbox with a `hermes-verify-` prefix, enable project plugins explicitly, load with Hermes's actual `PluginManager`, and assert registered tools/hooks. Do not install the development plugin into the user's active profile.

### Stage-1 certification

Run the addon-specific gate plus upstream Mantle gates against the vendored snapshot. Keep all test outputs and temporary organism state inside `.runtime/` during development.

### Host do-no-harm proof

Before and after every assimilation/wiring milestone:

- hash the Hermes host's tracked files;
- assert byte-for-byte equality;
- record `files_modified=0` in the residency receipt.

### Failure proofs

Tests must deliberately break:

- Primer integrity;
- VCW hash/seal;
- redaction boundary;
- hook fail-open behavior;
- Brain dormancy;
- AEP completion;
- DNR/reconstruction policy.

Each tamper must produce a non-green gate.

---

## 6. Risks and tradeoffs

1. **Hook coverage is not total host coverage.** Record gaps honestly and avoid a false “full AppAI” claim.
2. **Duplicate memory systems.** Mantle VCW complements Hermes sessions/memory; it must not silently replace or mirror all host content.
3. **Prompt privacy.** Default to classifications, hashes, and bounded redacted summaries rather than raw text.
4. **Tool overhead.** Keep callbacks deterministic and cheap; defer deep integrity scans to checkpoints.
5. **Fail-open vs. security blocking.** Instrumentation faults fail open; explicit deterministic operator policy may still block a dangerous action.
6. **Vendored drift.** Add a provenance file and explicit update command later; never silently pull upstream at runtime.
7. **Profile identity.** Resolve the active Hermes profile through documented APIs; never infer identity from filesystem names alone when unavailable.
8. **Existing MIND.** Hermes already has an LLM, but residency must first prove the same plugin works with Brain dormant.

---

## 7. Decisions established by the operator

- The addon should add AppAI organs and systems to Hermes, not merely expose Mantle commands.
- It should follow full AppAI rules wherever the Hermes plugin surface permits.
- Work remains confined to `/home/aibox/Hermes Mantle Addon` during development.
- Mantle's canonical Grimoire is governing design intent.

## 8. Open operator decisions before implementation reaches those boundaries

These do not block Phase 0 or deterministic Body work:

- Whether one Body belongs to each Hermes profile or each named Hermes agent instance; default proposed: one per profile.
- Whether any raw prompt content may ever be retained; default proposed: no.
- Whether deterministic policy may block existing Hermes tools in the first release; default proposed: observer-only until explicitly enabled.
- Whether reproduction/export ships in version 1 or follows after Stage-2 containment; default proposed: after Stage 1, before optional fusion only if separately requested.

---

## 9. Completion definition

The addon is eligible to call the Hermes resident a certified AppAI only when:

1. the signed Phase-0 inventory records zero host changes;
2. all nine organ contracts are present;
3. the resident pulses and persists with no model/network dependency;
4. observable inbound/effect/failure boundaries map to Senses/Limbs/Immune;
5. VCW integrity, veil, metabolism, identity, and lineage pass;
6. tamper tests prove the gate catches violations;
7. the addon-specific Stage-1 gate passes with no hard-fails;
8. disabling the plugin leaves Hermes behavior intact;
9. any unsupported host surfaces remain explicit gaps;
10. MIND readiness and fusion remain separate operator-controlled states.
