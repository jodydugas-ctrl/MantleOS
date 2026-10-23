# SCAN Engine v0.26 release report

Status: **mechanical release PASS / PR5 calibration PARTIAL**

Engine v0.26 is a generic surface-denominator correction over frozen v0.25. Ordinary Qt UI-object accesses remain evidence but no longer become human-surface candidates unless they are proven signal senders. CLI consumer calls are admitted only when tied to a proven `QCommandLineParser`. No NotepadNext-specific names, expected counts, or oracle conclusions are present in the implementation.

## Verification summary

- Development regression: 144 passed, three expected Windows symlink-privilege skips.
- Clean extracted source package: 144 passed, three expected skips.
- Package self-audit: 83/83 PASS.
- Release qualification: 12/12 queries PASS, projection audit PASS, model environment disabled.
- Two exact cold calibrations: 21/21 files byte-identical and zero canonical database-row differences.
- Warm cache: 4,186 hits / 0 misses; no evidence, workbench, or canonical-row drift.
- Fresh Python 3.13.13 installed-wheel certification: PASS; independent verification 12/12, zero issues.

## NotepadNext calibration

- Files: 1,928 materialized / 0 unavailable.
- Graph: 124,959 nodes; 139,431 edges; 137,559 evidence records.
- Semantics: 408,862 objects; 1,015,328 relations.
- Surface closure: 380 total; 310 bound, 59 partial, 11 unresolved.
- Effect closure: 87 closed, 282 partial, 11 unresolved; feedback observed for 59.
- Integrity: PARTIAL with 13 WARN and zero ERROR.
- Compiler evidence: 84 MAPPED, 294 PARTIAL, 16 unavailable; 331 parser gaps.

Compared with v0.25, all 330 declared/factory surfaces and their states are preserved. The denominator removes only 108 false reference candidates: 37 metadata-derived pseudo-options and 71 ordinary UI-object accesses. All 147 QActions and the four genuine CLI options remain.

## Artifact identities

- Source ZIP: 237,377 bytes, SHA-256 `4e262e4780a89802dd9ea3ebc390df18bafc3972eaa400cc2d21f0b7550960ba`.
- Wheel: 157,385 bytes, SHA-256 `0fe02da00a32a5074d39b7120b4d41c8a2fbd482b02dac8863ccd1cb08209e41`.
- Package manifest: SHA-256 `15c32c4ec93f52522ab1b73ef6fbeae9f192ee8e022b1b274991039c8dc5a98e`.
- Qualification: SHA-256 `a2df16619f3055538829e6c7e2f098cf42ce99e6609504fe1cb4854ed34dfdbf`.
- Certification receipt: SHA-256 `6e5c3abb7ad8d739d2033ef07c9effcc4d2fbb07ca9adf85fdba084e3c54b03b`.
- Certification manifest: SHA-256 `1cb7ab73122d5c142bf8b065265ac4837db876ad0becc58dcbdc9470923f30b7`.
- Private certification bundle: 277,456,091 bytes, SHA-256 `4c3fa6b8438832533864b859ddbd51d7343d30c951d7d0e1aaad831c83c27dcc` (not published in Git).

PR5 remains PARTIAL. External-agent reconstruction, H-001 blind holdout, and final production certification have not been performed.
