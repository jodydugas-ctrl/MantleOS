# REFLEX/0.1 — M0 semantic review packet

**State:** candidate for maintainer/Baker review, **NOT accepted or installed**.
**Date:** 23 October 2026. **Scope:** offline `anomaly-basic` experiment only.

## What is fixed in this candidate

1. **Book identity:** exact `reflex` / `0.1` / `anomaly-basic` and schema `mantle.reflex-ir/0.1`. Every other Book is refused.
2. **Canonical JSON:** sorted UTF-8 keys, no insignificant whitespace, NFC strings only, integer numbers (bounded), strict duplicate-member refusal, SHA-256 integrity binding. Canonicalization is deliberately narrower than RFC 8785 JCS; do not claim JCS compatibility.
3. **Types:** `Int` (signed 32-bit), synthetic `GeoFix` and rectangular `Region`; no hidden unit conversions. Other roadmap types are reserved for later editions.
4. **Unknown:** strong Kleene `TRUE/FALSE/UNKNOWN`; missing numeric operands evaluate `UNKNOWN`; the explicit `known` predicate alone can test absence. Missing/stale/future/low-quality positions or missing regions never produce `NORMAL` from the example geospatial rule.
5. **Guards:** `fresh` accepts injected clock minus timestamp in inclusive `[0,max_age_seconds]`; `quality_at_least` means `accuracy_m <= max_accuracy_m`; any non-TRUE guard overrides predicate to UNKNOWN.
6. **Results:** four output enums, no side effects. `REQUEST_REVIEW` and `review_requested=true` are report fields only, never messaging, a review queue, privileges, admission or installation.
7. **Declared capabilities:** exact `read:<referenced input>` strings. Capabilities describe required access, not a host permission grant.
8. **Limits:** 1..256 AST/precondition nodes, 1..512 instructions, <=65536 raw JSON source bytes, <=65536 framed payload bytes; per-program canonical envelope size and result-size caps; host elapsed-time/allocation isolation remains out of scope.
9. **ABI:** `RFX1` + 32-bit length + 256-bit digest + full canonical bytecode JSON. Decoder recompiles exact typed IR before allowing execution. This does **not** authenticate publisher or operator identity.
10. **Evidence:** golden source and compiled binary SHA-256 pins in `examples/reflex_book/golden_hashes.json`; independent AST evaluator/VM agreement, 250 seeded differential cases, 10,000 repeated identical runs, fixed stable-refusal checks.

## Review decisions that remain open

| Decision | Candidate stance | Resolution needed |
| --- | --- | --- |
| True spatial semantics | Blocked; conservative synthetic rectangle approximation; not a real geofence | Mathematical specification + independent geometry review |
| Explicit `known` on missing values | Returns FALSE; this is the one intentional absence test | Security/semantic reviewer accepts or narrows use |
| Canonical Unicode across runtimes | Python NFC + UTF-8 and deterministic key ordering | Cross-platform Python and external implementation vectors |
| Signature/authenticated review | Not implemented; SHA-256 is integrity only | M3 authority and admission design |
| Portability/host process isolation | Python 3.11+, no sandbox claim | M6 performance and resource guard benchmarks |
| Integration with Body/KPP | No production updates; existing Body profiles exclude REFLEX | Separate maintainer/KPP Baker review and new construction path |
| Error code compatibility | Stable in this prototype and test suite, not a forever ABI promise | Version freeze decision |
| Input byte cap interpretation | Canonical envelope bytes are capped per program; raw source capped separately globally | Confirm exact transport-vs-IR budget convention |

## Exit gate evidence (current local scope)

- [x] Normative proposed semantics, refusal register and explicit limitations documented in `SPEC.md`.
- [x] At least 15 synthetic vectors: 20 scenario vectors, pinned byte hashes for two programs.
- [x] Strict AST parsing, type checks, rights checks, unsigned integrity binding and standalone CLI.
- [x] Independent source evaluator and VM pass a seeded 250-case differential corpus.
- [x] No implicit install or host effects; deliberate `admission.install()` denial.
- [x] 10,000 identical VM executions of synthetic input with network socket stubbed to fail.
- [ ] Maintainer/Baker accepts the normative edition, uncertainty policy, and refusal registry.
- [ ] Existing MantleOS/KPP repository-wide tests run in the target Git checkout.
- [ ] Platform matrix, independent compiler implementation, wall-time/memory sandboxing.

**Proposed review result:** `READY_FOR_M0_REVIEW`, not `M0_APPROVED`, `M1_COMPLETE`, or `QUALIFIED`.

## Reviewer reproduction

```bash
python -m unittest discover -s tests -v
python -m experiments.reflex_book.cli validate examples/reflex_book/location_rule.json
python -m experiments.reflex_book.cli compile examples/reflex_book/location_rule.json --output .work/location.rfx
python -m experiments.reflex_book.cli verify .work/location.rfx
python -m experiments.reflex_book.cli run .work/location.rfx --input examples/reflex_book/location_stale.json
python -m experiments.reflex_book.tools.record_test_receipt
```

All commands run from the repository root, Python 3.11+ stdlib only. `verify` verifies integrity, **never approval**.
