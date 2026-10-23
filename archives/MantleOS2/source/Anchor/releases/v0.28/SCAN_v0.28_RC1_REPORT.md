# SCAN Engine v0.28 RC1 report

Status: **release candidate RC1 ready for review**.

v0.28 is feature-frozen. No new extraction, reconstruction, or refinement capabilities were added during release hardening. The sealed package contains the v0.27 evidence/certification core plus the already-integrated Anchor Code, portable Blueprint/conformance, static web surface extraction, and bounded refinement orchestration.

## Release qualification

- Regression suite: **158 passed, 0 failed**.
- Committed package manifest: **90/90 files verified**, zero audit issues.
- Mechanical qualification with common LLM credentials disabled: **PASS**.
- Required release query surface: **12/12 PASS**.
- Projection self-audit: **PASS**.
- Qualification integrity errors: **0**.
- Fresh Python 3.13 wheel installation and installed-wheel query qualification: **PASS**.
- Reproducible wheel build with `SOURCE_DATE_EPOCH=315532800`: **PASS**; two independent builds are byte-identical.

## Frozen calibration

A frozen v0.27→v0.28 calibration passed at scanner commit `4c16827fffc64b837bec2d1b781cf6aca39e6b7c`.

- NotepadNext: 380 → 380 actionable human surfaces.
- Moji: 103 → 103 actionable human surfaces.
- New actionable static-web surfaces: **0** on both specimens.
- Existing surface states preserved: **yes**.
- Existing effect states preserved: **yes**.
- NEST projection preserved: **yes**.
- Integrity errors: **0** on both.
- Duplicate v0.28 cold scans and reconstruction projections: **deterministic PASS**.

The successful calibration remains applicable to the sealed runtime scanner: comparison from that calibration commit to the package payload commit shows **no changes under `scan/`**. The only later additions inside `engine/v0.28` were `tests/test_v028_refinement_loop.py` and `PACKAGE_MANIFEST.json`.

## Artifact identities

- Wheel: 182,198 bytes — SHA-256 `87fe51d3241d3b21627261bdb7db3ab5ad4bd69ac0b6a9de5d4fa9ccbb78aa79`.
- sdist: 198,535 bytes — SHA-256 `43fb8f46a1943a77cb55e73ac469049cdd408f28ec104ece3d2f89f65a17bd70`.
- Deterministic source ZIP: 270,417 bytes — SHA-256 `6e7d4553a07d843689ae9589b304765eea61b1cf265bebd45cc1e971e39fc9f0`.
- Package manifest — SHA-256 `a03048a4bc54e346313f5bd32e9fb5281ee5686a18e98bd55fcc0009ebfd861e`.

## Release boundary

This report promotes v0.28 to **RC1 ready for review**, not to a published final release. No merge to `main`, Git tag, or GitHub Release is asserted here. Those are the next release-management actions after review of this sealed evidence set.
