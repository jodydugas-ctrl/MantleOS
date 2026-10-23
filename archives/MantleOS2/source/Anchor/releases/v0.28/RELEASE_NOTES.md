# SCAN v0.28.0

SCAN v0.28.0 closes the reconstruction-verification loop while preserving the evidence-first A1–A8 contract.

## Release highlights

- deterministic Anchor Code 0.9 projection from canonical SCAN evidence;
- portable evidence-bound Anchor Blueprint with embedded machine-readable conformance contracts;
- fresh-scan reconstruction verification: coding agents may build, but SCAN independently rescans and judges conformance;
- static HTML/CSS human-surface and visual-contract extraction without specimen execution;
- bounded SCAN-verified refinement orchestration with regression, no-change, no-progress, oscillation, error, and iteration-budget stops;
- v0.27 Qt and NEST evidence corrections preserved.

## Qualification

- **158 tests passed, 0 failed**
- package manifest: **90/90 files verified**
- LLM-disabled mechanical qualification: **PASS**
- release query surface: **12/12 PASS**
- integrity errors: **0**
- fresh Python 3.13 installed-wheel qualification: **PASS**
- frozen NotepadNext/Moji calibration: **PASS**
- duplicate cold scans and reconstruction projections: **deterministic PASS**
- reproducible wheel builds: **PASS**

Frozen calibration preserved the established actionable-surface denominator:

- NotepadNext: **380 → 380**
- Moji: **103 → 103**
- new actionable static-web surfaces: **0** on both
- existing surface/effect states and NEST projection preserved
- integrity errors: **0**

## Published assets

The GitHub Release publishes only artifacts that the release workflow can reproduce deterministically:

- Python wheel — sealed SHA-256 `87fe51d3241d3b21627261bdb7db3ab5ad4bd69ac0b6a9de5d4fa9ccbb78aa79`
- deterministic source ZIP — rebuilt twice and required to be byte-identical before publication
- `PACKAGE_MANIFEST.json` — SHA-256 `a03048a4bc54e346313f5bd32e9fb5281ee5686a18e98bd55fcc0009ebfd861e`
- `SHA256SUMS.txt` — authoritative checksums for the published release assets

The RC qualification also built an sdist successfully, but separate sdist builds did not preserve a stable archive hash, so the sdist is intentionally **not** published as a sealed release asset.

Detailed qualification and frozen-calibration evidence is preserved under `Anchor/releases/v0.28/`.
