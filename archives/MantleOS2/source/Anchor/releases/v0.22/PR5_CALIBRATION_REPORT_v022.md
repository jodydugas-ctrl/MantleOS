# PR5 NotepadNext Calibration — SCAN v0.22

Verdict: **MECHANICAL CERTIFICATION PASS / GENERIC NOISE CORRECTION PASS / PR5 STILL PARTIAL**

The exact v0.20 acquisition denominator was reused unchanged: 1,928/1,928 materialized files from `dail8859/NotepadNext`, commit `f57db52d6760a2ce4149a37190c3adaa586845f5`, tree `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`. SCAN v0.22 ran with LLM access disabled and sealed its results before this comparison.

## Authentication

- engine ZIP SHA-256: `a97d5992a08c2cda93f0ff67a1b1fd0f20c732fec0161656894421e883e1b689`;
- wheel SHA-256: `391c886835cc5f5317bd7c8c5962f918b3ee5ceeefefcd7cf7201efbf5b190d6`;
- certification bundle: 211,978,694 bytes;
- certification SHA-256: `b31393f7596573453e41089128db0520aeace9284dfd5a97e6bad6ca5cfab25e`;
- independent verification: PASS, 12/12 files, zero issues;
- runtime / max RSS: 33m16.30s / 3,859,504 KiB.

## Measured deltas

| Measure | v0.20 | v0.21 | v0.22 |
|---|---:|---:|---:|
| NEST boundaries | 4,232 | 1,310 | 84 |
| capability objects | 1,924 | 214 | 17 |
| effects | 112 | 134 | 134 |
| extension receptors | 1,971 | 1,905 | 410 |
| persistence objects | 1 | 18 | 18 |
| surface bound / partial / unresolved | 347 / 59 / 82 | 347 / 59 / 82 | 347 / 59 / 82 |
| effect closed / partial / unresolved | 109 / 297 / 82 | 112 / 294 / 82 | 112 / 294 / 82 |
| compiler AST | 0 / 394 | 0 / 394 | 0 / 394 |

All identity invariants pass: same repository, tree, provider fingerprint, materialized file count, LLM-disabled state, and certification PASS. The v0.22 reduction is therefore attributable to the generic scanner change rather than specimen drift.

## Classification

- **PASS — generic NEST classification:** comments, root documentation, vendored/test/deployment/static contexts, and repeated lexical occurrences no longer dominate runtime boundary counts.
- **PASS — evidence preservation:** direct occurrence evidence and function-level relations remain present after object aggregation.
- **PASS — prior v0.21 improvements retained:** commit receipt, Windows identity fix, 17 persistence operations, 22 additional effects, and three newly closed routes are preserved.
- **OPEN — compiler context:** WSL lacked Clang, leaving 394 parser gaps and compiler/type-dispatch BLOCKED/UNKNOWN.
- **OPEN — route and lifecycle closure:** the surface vector remains 347/59/82 and lifecycle remains UNKNOWN.
- **OPEN — semantic promotion/reconstruction:** the cold mechanical parent correctly contains no promoted reconstruction anchors.

## Gate decision

v0.22 is accepted as a successful generic calibration correction and rejected as a final candidate. PR5 remains PARTIAL. The next admitted correction is generic recovery of valid source-local compiler AST output when missing dependencies produce nonzero Clang exits, followed by a compiler-enabled sealed rerun. H-001 remains frozen and uninspected.

