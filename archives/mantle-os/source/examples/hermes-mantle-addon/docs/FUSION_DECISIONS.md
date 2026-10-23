# Operator and Guardian Decisions

**Target:** `mantle-os` v0.4.0 (`Hermes.Mantle.AppAI`)

**Recorded:** 2026-07-15T14:32:35-03:00

**Machine-readable record:** [`FUSION_DECISIONS.json`](FUSION_DECISIONS.json)

## Effective decision

| Surface | Decision |
|---|---|
| Mantle OS 1.3.0 software release | **APPROVED** |
| Current deterministic Phase-1 runtime | **APPROVED** |
| Twelve fail-open observer hooks and bounded tools | **APPROVED** |
| Dormant Phase-2 implementation and offline acceptance | **APPROVED** |
| Production MIND fusion | **DEFERRED — NOT AUTHORIZED** |
| Reproduction activation | **DEFERRED — NOT AUTHORIZED** |

The code is technically ready for release. Release approval is not fusion approval. A production
resident must independently satisfy the runtime authority protocol.

## Evidence considered

- Addon Stage-1: 14/14.
- Framework Stage-1: 20/20 rows and 90/90 runtime/security invariants.
- Containment: C-01 through C-11.
- Complete 146-file vendored framework snapshot.
- Owner-only, symlink-safe atomic persistence.
- Exactly one fixed 600-second scheduler per fused resident.
- Hermes-owned provider/model/auth routing through `PluginContext.llm`.
- One bounded addon dispatch, host-owned fallback/retries, timeout, rolling token/cost budgets, and redacted receipts.
- Authenticated offline attach → heartbeat → defuse → post-defusion Stage-1 PASS.

## Operator decision

**Software release: APPROVED. Production MIND fusion: DEFERRED.**

The request to complete and publish the release authorizes repository, package, documentation,
and GitHub publication work. It does not provide a cryptographic approval bound to a concrete
resident identity and Body fingerprint.

## Guardian decision

**Software release: APPROVED. Production MIND fusion: DEFERRED.**

Publishing dormant, fail-closed capability is acceptable because absent, shared, malformed, or
tampered authority public keys/signatures cannot attach cognition, and the verifier has no private
signing material. Defusion remains authority-free.

Before production fusion, the guardian requires:

1. a fresh 14/14 addon and 90/90 framework Stage-1 PASS on the target resident;
2. a fresh `READY` report bound to that resident and Body fingerprint;
3. a signed operator `APPROVED` record from the configured operator key;
4. a separately signed guardian `APPROVED` record from the configured guardian key;
5. explicit reproduction denial.

## Decision invariant

> Release approval, enthusiasm, roadmap continuation, runtime approval, technical certification,
> or a `READY` engineering report must never be interpreted as production MIND-fusion authority.
