# SCAN Engine v0.21 Candidate Report

Report state: **PR5 RECALIBRATION COMPLETE / SUPERSEDED BY v0.22 — NOT A v1 RELEASE**

## Candidate identity

- Engine: `0.21.0`
- Source package manifest: `45e9198180c5084dd4687611f6832456dd79933dd61ac0eaa0c33292172cd856`
- Engine ZIP: `d1b850a5063c9e95db34254f5a901447ef95ee0526f166ca8ead1fac0c898f18`
- Wheel: `c232d53b0ed0badcc91b508e2053b472c8cf5afd28b66371bcc65548fa27c012`
- Freeze receipt: `FROZEN_CANDIDATE_RECEIPT.json`

## Generic PR5 corrections

1. Windows manifest identity comparison no longer treats incomparable `lstat`/`fstat` creation-time values as evidence that unchanged source bytes changed. Device, inode, size, and modification time remain guarded; non-Windows systems retain creation-time comparison.
2. A provider manifest whose exact hexadecimal revision is the commit identity now populates `specimen.commit_sha` in the sealed receipt instead of retaining the value only as a generic revision.
3. Direct source-declared C++ receiver types can support conservative typed fallback effects, persistence operations, NEST boundaries, extension receptors, and capability factories when compiler AST context is unavailable. The evidence distinguishes compiler-derived from source-declared receiver types.
4. Generic documentation, localization, build/workflow metadata, vendored source references, and environment examples retain their URL/extension evidence as repository references without being promoted to application-runtime NEST boundaries.
5. Relative compilation-database paths use platform-independent POSIX normalization in compiler context.

No NotepadNext repository name, path, action identity, or oracle-specific conclusion is embedded in the extraction rules.

## Qualification before PR5 rerun

- Python 3.12 clean-package tests: 115/115 pass; 12 compiler-dependent tests skip because Clang is absent from the qualification host.
- Package self-audit: 68/68 pass, zero issues.
- LLM-disabled release qualification: 12/12 required queries pass; integrity MAPPED with zero errors.
- Fresh Python 3.12 wheel installation: pass; installed metadata and runtime both report `0.21.0`.
- Extracted engine ZIP self-audit: 68/68 pass, zero issues.
- Exact v0.20 NotepadNext inventory re-read on Windows: 1,928/1,928 files materialized with no false `SOURCE_CHANGED` states.
- Generic-token reclassification probe on the exact specimen: runtime NEST candidates fell from 3,586 to 642 while 3,011 non-runtime tokens remained preserved as repository-reference evidence.

## PR5 recalibration admission

- Repository: `dail8859/NotepadNext`
- Commit: `f57db52d6760a2ce4149a37190c3adaa586845f5`
- Tree: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`
- Source manifest: `8fca5eb6edcbf9ec2a23e38b1792ad6bc40e0a3adda7b52715ece8cde661152f`
- Exact acquisition ZIP: `4a1343f4f56500ba850162039e7483e2f17f894be6493f5afbaacdf25c2c44a3`
- Original v0.20 cold baseline remains immutable at certification SHA-256 `6c0d476e2dd7a63481cf388e6d654798ffa26f8c72ce9760a8bd60667b075ce3`.

The v0.21 run is an oracle-informed **generic calibration rerun**, not a second source-blind baseline. Its extraction remains LLM-disabled and its outputs will be sealed before comparison.

## Sealed PR5 v0.21 result

- Certification: PASS; independent verification 12/12 PASS, zero issues.
- Bundle: 213,930,824 bytes; SHA-256 `33a59fec68bca47d546eab8517de99e7a31c726d107db6bb1db101778432e0bd`.
- Runtime: 1:34:53 wall clock; maximum resident set 3,897,472 KiB.
- Same exact provider tree, repository, commit, 1,928 files, and 1,928 materialized files as v0.20.
- Receipt commit population: fixed (`f57db52d6760a2ce4149a37190c3adaa586845f5`).
- Persistence operations: 0 to 17, all direct source-declared `QSettings` receiver operations in `SessionManager.cpp`.
- Closed effect routes: 109 to 112; partial effect routes: 297 to 294.
- NEST boundaries: 4,232 to 1,310; grouped capabilities: 1,924 to 214.
- Human-surface closure remained 347 bound / 59 partial / 82 unresolved.
- Compiler AST remained blocked for 394 translation units because Clang/build context was unavailable.

PR5 therefore remained **CALIBRATION PARTIAL**. Inspection of the retained 1,310 boundaries found a generic path-role omission (`thirdparty/`) plus C++ comment/literal token inflation. Those reusable findings admitted v0.22.

## Post-freeze packaging audit

The v0.21 engine ZIP contained 51 untracked Python bytecode/cache entries because its source directory was tested before archiving. All 68 manifest-tracked source files remained byte-correct, the package self-audit passed under its documented cache-ignore rule, and the certification runtime loaded from the exact wheel rather than those cache files. The sealed evidence remains mechanically valid, but the distribution artifact fails clean-release hygiene and is not accepted as a production candidate. v0.22 is built from a fresh manifest-only copy before any test imports and verifies zero bytecode entries.
