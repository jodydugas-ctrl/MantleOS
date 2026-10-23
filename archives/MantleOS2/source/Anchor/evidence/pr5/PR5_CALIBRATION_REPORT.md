# PR5 NotepadNext Cold Calibration Report

Report version: 0.1
SCAN Engine: 0.20.0 (authenticated original)
Project lineage: 0.27 release / 0.28 acquisition checkpoint
Specimen: `dail8859/NotepadNext@f57db52d6760a2ce4149a37190c3adaa586845f5`
Git tree: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`
Cold-scan verdict: **MECHANICAL CERTIFICATION PASS / PR5 CALIBRATION PARTIAL**

## Admission and evidence boundary

The original v0.20/v0.27 release artifacts were recovered and authenticated before execution:

| Artifact | SHA-256 | Result |
|---|---|---|
| `Copper-Marrow-Lantern_v0.27.zip` | `f9590271c0c8cca16993e548667dcf9536c4a04c2be33590e83d302bac7cddb0` | PASS |
| `SCAN_ENGINE_v0.20.zip` | `6dce99a4ed924d9e370a29367e7a59845f2eefac5414cb3403e873b8577f9af1` | PASS |
| `scan_software_body-0.20.0-py3-none-any.whl` | `573ce1c0a0ea7e5bc0039ce954209e983ba3d373e73b9301baf282fd559076fa` | PASS |
| `RUN_PR5_NOTEPADNEXT_COLD_v020.ps1` | `138d36ff1abd6831587f3178e844ae42bfaec87220a79cc932b3710c5ca46def` | PASS |

The project handoff verified 25/25 manifest-tracked payloads. The source bridge verified 1,928/1,928 provider blobs (20,875,384 bytes) by declared size and canonical Git blob SHA-1, plus SHA-256 where the provider acquisition had already supplied one. The manual oracle was not consulted until after the cold certification bundle was sealed.

The GitHub per-blob REST acquisition reached its anonymous rate limit after 118 blobs and truthfully stopped with 1,810 blocked blobs. The remaining exact bytes were materialized from the already verified local Git object database with `git cat-file`; the original GitHub API tree manifest remained the provider denominator. A first attempted Windows `git archive` export was rejected because checkout filters changed line endings in 1,823 blobs. No transformed bytes entered the accepted scan.

## Sealed cold result

| Measure | Result |
|---|---:|
| Files / materialized files | 1,928 / 1,928 |
| Content-unavailable files | 0 |
| Budget triggered | no |
| Nodes | 101,138 |
| Edges | 109,282 |
| Evidence records | 109,072 |
| Semantic objects | 326,026 |
| Semantic relations | 808,588 |
| Certification | PASS |
| Independent verification | 12/12 files PASS, 0 issues |
| Certification bundle | 213,474,077 bytes |
| Certification SHA-256 | `6c0d476e2dd7a63481cf388e6d654798ffa26f8c72ce9760a8bd60667b075ce3` |
| Exact acquisition bundle | 7,336,255 bytes |
| Acquisition SHA-256 | `4a1343f4f56500ba850162039e7483e2f17f894be6493f5afbaacdf25c2c44a3` |

The execution state is `COMPLETE_WITH_EXPLICIT_COVERAGE_VECTOR`. Mechanical integrity passed; this is not a claim of complete semantic understanding.

## Oracle comparison

| Calibration dimension | Manual oracle | Cold v0.20 result | Classification |
|---|---|---|---|
| MainWindow QAction denominator | 139 | 139 | PASS |
| MainWindow actions with route evidence | 137 | 137 | PASS |
| `actionFindInFiles` | visible, no implementation reference found | present, 0 route edges | PASS |
| disabled unimplemented placeholder | visible but disabled/non-actionable | `enabled=false`, 0 route edges | PASS |
| auto-save recurrence | `autoSaveTimer`, 60 seconds | MAPPED, interval `60 * 1000` | PASS |
| additional timer | URL-finder timer expected from source | discovered, PARTIAL | PASS/PARTIAL |
| dynamic/runtime actions | recent files, languages, macros, opened tabs, dock toggles, custom shortcuts | recent-files and MainWindow runtime QAction outputs plus 21 registrations discovered; family/behavior closure incomplete | PARSER/CLOSURE GAP |
| whole human surface | layered UI, programmatic, gesture, CLI, OS, hidden/developer surfaces | 488 input surfaces; 347 bound, 59 partial, 82 unresolved | PARTIAL |
| C/C++ compiler/type evidence | required for exact dispatch and platform closure | 394 translation units; compiler AST 0; type dispatch UNKNOWN | COMPILER-CONTEXT GAP |
| persistence | files, settings, recent files, session restoration | 1 provider, 0 persistence operations | PARSER/SEMANTIC GAP |
| lifecycle | startup/open/close/session routes known manually | lifecycle completeness UNKNOWN | SEMANTIC-PROMOTION GAP |
| NEST/capabilities | Qt/OS/filesystem/settings/clipboard/printing/process/network/IPC/Scintilla/Lexilla/Lua | 4,232 candidate boundaries and 112 effects, but capability provenance PARTIAL and typed effects 0; substantial build/vendor URL noise | CAPABILITY CLASSIFICATION GAP |
| parser coverage | complete bytes should be parser-eligible | 81 PARTIAL files, 394 parser gaps, 0 parser failures | PARSER GAP |
| reconstruction anchors | post-calibration promoted contracts required | 0 in cold mechanical parent, as expected | NEXT PHASE, NOT COLD FAILURE |

The exact 139/137 match is strong evidence that v0.20's denominator-driven Qt action discovery and helper-mediated binding closure generalized to the real specimen. The remaining gaps prevent declaring PR5 converged or SCAN production-ready.

## Generic corrective work admitted by PR5

1. Provide bounded, reproducible compiler/build context so real C++ translation units can receive compiler-assisted type and dispatch evidence without executing untrusted specimen build scripts.
2. Improve persistence-operation extraction for Qt settings, session state, recent-file state, and file-commit paths.
3. Reduce generic NEST false-positive noise from build/vendor/workflow URLs and distinguish application-runtime boundaries from repository metadata.
4. Promote mechanically supported lifecycle and high-value behavior contracts after validation while leaving the sealed parent immutable.
5. Close the 82 unresolved human routes and 59 partial routes generically, prioritizing dynamic action families, Designer references, OS file-open, dialogs, and direct-manipulation surfaces.
6. Profile and optimize large-project cross-file analysis. The successful full pass required well over one hour on this host and produced a 213 MB handoff.
7. Fix the generic Windows local-manifest identity guard: Python/Windows reports different `ctime` semantics through `lstat` and `fstat`, causing unchanged files to be labeled `SOURCE_CHANGED`. The unmodified v0.20 cold run therefore required Linux/WSL.
8. Correct receipt population so the pinned commit is emitted in `specimen.commit_sha` rather than only retained as `revision` in the source manifest and external PR5 receipt.

Only generic engine changes are admissible. No NotepadNext name, path, action identifier, or oracle conclusion may be hard-coded into extraction logic.

## Gate decision

PR5 advances from **ACQUISITION PASS / COLD SCAN NOT PASSED** to **COLD SCAN PASS / CALIBRATION PARTIAL**.

The next critical-path step is a generic v0.21 calibration release addressing the highest-value gaps above, followed by a fresh sealed NotepadNext rerun and comparison. Candidate freeze, genuinely independent M6B reconstruction, untouched H-001 blind holdout, and final production certification remain downstream gates.
