# Review checklist — isolated REFLEX experiment

## Path guard

Expected additions: `experiments/reflex_book/`, `examples/reflex_book/`, `tests/reflex_book/`, `docs/reflex/`. No files under `src/mantleos/`, `archives/`, or pinned `src/mantleos/kpp/`; no replacement of repository-root README or existing `tests/__init__.py`.

## Independent review

- [ ] Reviewer confirms interpretation of `known`, missing numeric inputs, guard priority, bounds and outcome mapping.
- [ ] Reviewer examines the semantic specification, disassembler outputs and golden binary hashes.
- [ ] Reviewer reviews the `geo_outside` approximation as a synthetic-only teaching case.
- [ ] Reviewer runs all new tests plus preexisting repository-wide suites on a clean checkout.
- [ ] Reviewer confirms no external data access, model calls, patient data, authority mutation, or auto-install.
- [ ] Reviewer records accept/reject decision with commit and test-receipt digests.
- [ ] Separate Baker/operator gate remains required before any MantleOS tissue or KPP promotion.

## PR description template

**Title:** `[experiment] REFLEX/0.1 M0 semantic review and M1 adversarial hardening`

**Scope:** standard-library deterministic JSON-to-bounded bytecode experiment, strict checker, synthetic corpus, reproducible local checks and review packet. **No production runtime integration.**

**Risks:** non-geodesic synthetic location example; no wall-time sandbox, trust signatures, approval/installation path, or operator grant; no body-wide regression evidence until CI or local maintainer execution.

**Acceptance:** check review packet and receipt; leave as draft/experimental until reviewed; do not merge as a qualified profile.

## Additional M3 admission review checks (24 October 2026)

- [ ] Confirm M0 semantic questions accepted, or explicitly keep this experimental.
- [ ] Inspect HMAC issuer key trust boundary and candidate/reviewer separation.
- [ ] Confirm exact binary, test-receipt and dependency digest pinning.
- [ ] Review SQLite atomic install, audit tamper refusal and refusal logging.
- [ ] Confirm staleness quarantine cannot be undone by restoring an old version label.
- [ ] Confirm rollback refuses revoked, stale and expired candidates.
- [ ] Run `python -m experiments.reflex_book.tools.record_m3_test_receipt` in a real target checkout.
- [ ] Verify full MantleOS tests and KPP pin checks without rewriting KPP-owned files.
- [ ] Do not merge REFLEX as an Anchor profile or call it qualified as a side effect of passing tests.
