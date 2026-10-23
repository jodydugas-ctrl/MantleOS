# Grimoire Dual-Edition Research Pilot

The bounded serial pilot completed on 2026-07-31 against Mantle OS 1.5.0.

Machine report: `.artifacts/research-pilot/grimoire-dual-edition-report.json`

Report SHA-256: `4a8ae7cd1ae2dd36abc095a5d0285a40645dfb58a2a02d7d02df0df87acfd932`

Protocol

- Profile: `grimoire-dual-edition`
- Protocol hash: `sha256:8c14d4c4d2047220a64fa9339bb730ed57d3080044719da2279133b0400c57d8`
- Mutable surface: `src/mantle/vcw/grimoire_editions/v010.py` only.
- Immutable inputs: the frozen v0.9 edition, canonical v0.10 edition, independent verifier, and Grimoire invariants.
- Evaluator identity: `mantle-research-grimoire-dual-edition-v1`.
- Independent verifier: `PASS`; differences: `0`.
- v0.9 vectors: `3`; v0.10 vectors: `5`; authority drift: `0` for both.

Results

| Experiment | State sequence | Candidate hash | Outcome |
|---|---|---|---|
| `pilot-eligible` | PROPOSED → MATERIALIZED → RUNNING → MEASURED → ELIGIBLE | `sha256:5949a0f459a9255725e0ded5aafc5868014e2dd2932fe1382710f743e9f0ed9d` | eligible, not adopted |
| `pilot-discarded` | PROPOSED → MATERIALIZED → RUNNING → MEASURED → DISCARDED | same candidate hash | intentional hard-gate control |
| `pilot-crashed` | PROPOSED → MATERIALIZED → RUNNING → CRASHED | same candidate hash | bounded process timeout; no changed paths |

The crash control reported `timed_out: true`, `output_limited: false`, and `changed_paths: []` under the fixed process budget. Discarded artifacts were not preserved because no preserve-artifact policy was requested.

Authority proof

- Production pilot adoption: `false`. Eligibility did not alter the active decoder or any canonical source.
- Separate fixture path: `AUTHORIZED` → `ADOPTED` succeeded only with an explicit operator receipt and recorded `automatic: false`.
- No parallel research wave was started; it was not authorized.

This report is derived from the append-only JSON ledger. The canonical ledger remains authoritative; the Grimoire projection is secondary and cannot mint adoption authority.
