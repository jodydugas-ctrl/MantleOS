# Hermes Mantle Addon — MIND Readiness Report

**Target:** `mantle-os` v0.4.0 (`Hermes.Mantle.AppAI`) on Mantle OS 1.3.0

**Recorded:** 2026-07-15T14:32:35-03:00

**Machine-readable report:** [`MIND_READINESS.json`](MIND_READINESS.json)

**Software engineering verdict:** **READY**

**Production MIND fusion authorized:** **NO**

**Reproduction activation authorized:** **NO**

## Executive finding

B-01 through B-08 are technically resolved. The addon now has a reversible fusion lifecycle,
one fixed 600-second cognitive scheduler per fused resident, Hermes-owned model routing,
bounded token/cost and outage controls, redacted usage receipts, and an authenticated dual-role
authority provider. A controlled offline acceptance test proves:

1. authenticated operator and guardian signatures are both required;
2. the MIND attaches without replacing the Body;
3. one scheduled cognitive heartbeat runs through the host-model abstraction;
4. defusion is authority-free and preserves the resident;
5. the defused resident re-passes all 14 addon rows and all 90 framework invariants.

`READY` means the software can be released. It does **not** authorize production fusion. A
concrete deployment still needs a fresh resident-bound Stage-1 receipt and readiness report,
plus separate fresh operator and guardian approvals authenticated with distinct configured
credentials. No production approval or credential is included in the repository.

## Evidence matrix

| Evidence | Result |
|---|---:|
| Addon Stage-1 probes | **14/14 PASS** |
| Framework gate rows | **20/20 PASS** |
| Framework security invariants | **90/90 PASS** |
| Addon unit tests | **127 PASS** |
| Containment receipt | **11/11 PASS** |
| Real Hermes observer hooks | **12** |
| Complete non-addon vendor snapshot | **146/146 aligned** |
| Owner-only symlink-safe persistence | **PASS** |
| Raw payload exclusion | **PASS** |
| Technical fusion lifecycle acceptance | **PASS (offline host facade)** |
| Operator production-fusion decision | **DEFERRED** |
| Guardian production-fusion decision | **DEFERRED** |

## Resolved blockers

### B-01/B-02 — Complete evidence and fail-closed transition

The framework passes 20/20 Stage-1 rows and 90/90 runtime/security invariants. The transition
requires a complete, fresh, target-bound receipt and `READY` report. Caller-authored approval
JSON remains evidence only until the authority provider authenticates both signatures.

### B-03 — Reversible runtime fusion lifecycle

`ResidentRuntime` transactionally attaches cognition, records redacted BODY-authored receipts,
refuses replacement, rolls back failed commits, defuses idempotently without authority, and
recovers unexpected fused state before accepting hooks. The controlled acceptance path includes
a post-defusion Stage-1 rerun.

### B-04 — Natural ten-minute cognitive heartbeat

`CognitiveScheduler` owns exactly one daemon per fused resident and fixes the natural interval at
600 seconds. Duplicate starts are inert. Observer hooks execute `Heart.body_pulse()`, which keeps
the autonomic Body alive without invoking cognition. Significant/distress wakes are queued as
additional pulses and never reset or replace the natural deadline.

### B-05 — Hermes-native provider routing

The addon receives `PluginContext.llm` and calls its supported `complete()` facade without
provider/model/profile overrides. Hermes owns active provider/model resolution, authentication,
fallback, and credentials. The addon no longer contains a bespoke HTTP or API-key transport.

### B-06 — Budget and outage policy

`CognitionPolicy` bounds output tokens, rolling token and cost use, request timeout, and concurrent
calls. The addon makes one dispatch and never nests retries around Hermes's host-owned fallback
and retry policy. Unknown usage is charged conservatively. Exhausted budgets and outages fail open
to the Body while producing receipts that contain only status,
route labels, usage, cost, attempt count, error type, and timestamp—never prompts, responses,
credentials, or raw exception text.

### B-07 — Authenticated dual authority

`Ed25519AuthorityProvider` requires independent operator and guardian key IDs and public keys,
verifies both target-bound signatures, and minimizes the receipt passed to the core Brain.
Private signing keys never enter the addon process, so verifier material cannot mint approvals.
Missing, shared, malformed, or tampered authority fails closed. No approval or key is bundled.

### B-08 — Evidence is not authority

Stage-1, containment, and this `READY` report are technical evidence. None grants production
fusion authority. Reproduction remains false and requires a separate future design and decision.

## Gate rationalization

The former `OPT-*` repository-optimization ledgers and `VERS-1` snapshot were removed from the
organism's security invariant count. They measured mutable project-management artifacts and made
routine source changes fail certification without detecting a runtime/security regression. The
optimization audit remains available as advisory release tooling. Package/module version
alignment is checked directly during build and installed-artifact verification.

## Deployment activation requirements

1. Generate a fresh Stage-1 PASS on the concrete resident.
2. Generate a fresh `READY` report bound to that resident identity and Body fingerprint.
3. Configure distinct operator and guardian Ed25519 public keys and key IDs; keep each private
   signing key outside the addon process with its independent signer.
4. Obtain fresh target-bound signed `APPROVED` records from both roles.
5. Keep reproduction explicitly false.

> **Release the software when its clean-checkout gates pass. Do not fuse a production MIND merely
> because this engineering report is READY.**
