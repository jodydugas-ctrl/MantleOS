# REFLEX/0.1 — M3 evidence and admission review

**Status:** `READY_FOR_M3_TECHNICAL_REVIEW`, **not** `M0_APPROVED`, `M3_ACCEPTED`, `QUALIFIED`, or `INSTALLED_IN_MANTLEOS`.
**Date:** 24 October 2026. **Scope:** synthetic/offline isolated Python experiment.

## What this increment builds

- `evidence.py`: canonical, content-bound candidate manifest. Binds Book + edition, exact IR digest and compiled binary digest, input schema, output/result schema, capability strings, budgets, claimed test receipt bytes, evidence labels, baseline version digests, proposer, optional predecessor and compiler/VM versions. Manifest hashes are integrity, never approval.
- `admission.py`: operator-side HMAC-SHA256 experimental receipts. A separately controlled trusted host injects issuer secrets, the clock, and approved scope. Signer must differ from proposer. Receipts bind candidate digest, exact read-only capabilities, baseline versions, validity window and the **isolated registry** scope. HMAC only authenticates the holder of the trusted local secret; not an identity certificate or production authorization.
- `registry.py`: standalone transactional SQLite **simulation** with `INSTALL`, `ACTIVATE`, `EXECUTE`, `DISABLE`, `REVOKE`, `ROLLBACK`, `STALE`, and `REFUSED` events. It retains exact checked artifacts and a SHA-256 append-only chain; SQLite transactions publish artifact and audit entry together. Tamper checks refuse altered event rows and altered blobs. Failed host admission attempts are logged by refusal code, without rejected payloads.
- When current host baseline digests differ from the signed manifest, running is refused and that candidate is quarantined as `STALE` until a new review/candidate is issued. `REVOKE` disables an active candidate. Rollback requires a previously active, non-revoked, non-stale artifact and a **currently valid** matching approval. Expired or untrusted receipts cannot be bypassed via rollback.
- VM is unchanged: no network, no external effects, no direct sensor calls, no model calls, no host privileges. A report containing `review_requested=true` is never a review action.

## Contract boundaries and limitations

1. **No production installation.** `admission.install(candidate)` intentionally still refuses with `E_AUTHORITY`. Only `ExperimentalRegistry.install(...)` exists; its output explicitly says `production_body_authorized=false`. No edits to `src/mantleos`, archived sources, KPP pins, keys, PRIMER or Skin.
2. **Trust is not self-asserted.** Compiler output, good tests, a hash, a manifest, a signed-looking receipt without a matching trusted host key, and any model-authored prose cannot issue operator authority. The demo key is publicly visible and **not a real credential**.
3. **Evidence is submitted data, not attestation.** The reference candidate binds an earlier M0 receipt's bytes. That receipt is not magically upgraded to a verified M3 qualification result. Reviewer must independently inspect the test transcript and sign only if warranted.
4. **Host remains privileged.** Registry APIs and operator credential holders are trusted Python host code, not adversarial sandboxes. A process with filesystem/DB administrator privileges can rewrite the entire SQLite database, replay events with new hashes, drop triggers, or read local key material if the host exposes it. The audit chain is unanchored SHA-256, not external notarization.
5. **No production memory fork.** The local SQLite database is a disposable test fixture, not MantleOS Engram, Body registry, KPP Pantry or a canonical new memory layer. Adoption requires the reviewed Body transaction and Engram interfaces.
6. **Clock and dependencies are host-injected.** Execution receives `now_utc`, `current_baselines`, and `trusted_issuers` separately. Mismatches refuse; malicious host injection lies outside the prototype threat model.
7. **Static budget and isolation limits remain.** Host wall-clock timeout, allocation isolation, cross-process sandboxing, interrupted-power WAL recovery and cross-platform SQLite concurrency benchmarks have not been qualified.
8. **Spatial mathematics remains synthetic.** `outside_region` uses the M0 demonstration approximation, not a clinical-grade geofence. No patient/caregiver data or communications are present.
9. **M0 semantic freeze is pending.** The previous reviewer questions (geometry, Unicode portability, missing-input semantics and resource budgets) remain pending and are not silently declared resolved here.

## Lifecycle / gates

```text
Candidate (UNTRUSTED)
   -> exact compiler+evidence verification
   -> separate trusted-host operator receipt + expiry + capabilities + dependency pins
   -> INSTALL [isolated registry only; does not activate]
   -> ACTIVATE [recheck all admission constraints]
   -> EXECUTE [verify again; report only; append hashed trace reference]
   -> DISABLE or REVOKE
   -> ROLLBACK [only after rechecking earlier candidate's current authorization]
   -> STALE [irreversible quarantine after baseline mismatch]
```

Every refused host admission operation with a valid injected clock records a bounded `REFUSED` audit event. Invalid preprocessing without registry involvement cannot be guaranteed to appear in that registry's history. A corrupt or unwritable ledger refuses new work rather than pretending that it was recorded.

## Evidence/reviewer checklist

- [x] Immutable content-bound candidate and exact binary/evidence validation.
- [x] Separate HMAC-key review receipt with independence, scope, expiry, and rights pinning.
- [x] Approved-but-inactive and active revisions are distinct states.
- [x] Stale dependency quarantine, revocation, disable and rollback checks.
- [x] Atomic install transaction and crash-injection rollback test.
- [x] Append-only chained audit records and tamper refusal.
- [x] Adversarial tests: forged MAC, changed rights, stale baseline, changed issuer, expired receipt, DB modification.
- [x] Existing M0/M1/M2 prototype conformance preserved; 10,000 repeat test still runs.
- [ ] Maintainer accepts M0/Book semantics and these M3 trust assumptions.
- [ ] Baker or designated reviewer independently accepts evidence and approves a real integration path.
- [ ] Full MantleOS repository and KPP-pinned regression suites execute in the target checkout.
- [ ] Trusted-key distribution, external audit-head anchoring and HMAC/issuer revocation design reviewed.
- [ ] Production persistence/admission reuse of Engram transactions designed and tested.

**Next evidence gate:** M4 raw carrier round-trip and corruption negatives, after M3 review. A real Body profile and any KPP promotion remain future, separately authorized work.
