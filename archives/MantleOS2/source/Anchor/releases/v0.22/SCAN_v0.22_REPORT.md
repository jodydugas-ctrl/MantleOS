# SCAN Engine v0.22 Calibration Release Report

Release status: **AUTHENTICATED / PR5 RECALIBRATION PASS / SUPERSEDED FOR CONVERGENCE**  
Engine version: `0.22.0`  
Specimen: `dail8859/NotepadNext@f57db52d6760a2ce4149a37190c3adaa586845f5`  
Tree: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`

## Purpose

v0.22 is the second generic correction release admitted by the immutable v0.20 cold calibration. It removes repository-reference and lexical repetition noise from NEST/extension discovery without adding any NotepadNext-specific identifier, path, or expected answer. The v0.20 certification remains the pre-oracle baseline.

## Frozen engine artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `SCAN_ENGINE_v0.22.zip` | 195,729 | `a97d5992a08c2cda93f0ff67a1b1fd0f20c732fec0161656894421e883e1b689` |
| `scan_software_body-0.22.0-py3-none-any.whl` | 123,843 | `391c886835cc5f5317bd7c8c5962f918b3ee5ceeefefcd7cf7201efbf5b190d6` |

The engine ZIP contains zero bytecode files. Its extracted manifest audit verifies 68/68 tracked files. A fresh Python 3.12 environment installed the wheel and reported version `0.22.0`.

## Qualification

- clean development and extracted-package suite: 119 tests passed, 12 skipped in WSL because Clang was unavailable;
- installed-wheel release qualification: 12/12 required LLM-disabled queries passed, integrity `MAPPED`, zero integrity errors;
- focused Windows Python 3.12 + LLVM suite: 18/18 compiler, Qt/type, and NEST tests passed;
- exact 1,928-file adapter probe: 41.03 seconds, zero adapter errors;
- package manifest: 68/68 files verified.

## Sealed PR5 recalibration

| Measure | Result |
|---|---:|
| Certification | PASS |
| Independent verification | 12/12 files PASS, zero issues |
| Runtime | 33m 16.30s |
| Maximum resident set | 3,859,504 KiB |
| Bundle bytes | 211,978,694 |
| Bundle SHA-256 | `b31393f7596573453e41089128db0520aeace9284dfd5a97e6bad6ca5cfab25e` |
| Files / materialized files | 1,928 / 1,928 |
| Nodes / edges / evidence | 99,221 / 108,485 / 108,230 |
| Semantic objects / relations | 322,470 / 802,226 |

The receipt correctly retains repository, commit, tree, provider-tree fingerprint, manifest acquisition mode, and `LLM_environment=DISABLED`. No acquisition, parser-failure, budget, or integrity-error condition invalidated the certification. The completeness vector remains explicit: 19 MAPPED, 33 PARTIAL, 4 UNKNOWN, and 1 BLOCKED dimensions.

## Calibration result

Relative to v0.20, v0.22 changes the relevant measurements as follows:

| Dimension | v0.20 | v0.22 | Result |
|---|---:|---:|---|
| NEST boundaries | 4,232 | 84 | -98.0% noise/duplication |
| capability objects | 1,924 | 17 | -99.1% noise/duplication |
| extension receptors | 1,971 | 410 | -79.2% noise/duplication |
| effects | 112 | 134 | +22 retained typed/source effects |
| persistence objects | 1 | 18 | +17 QSettings operations |
| effect closure closed/partial/unresolved | 109/297/82 | 112/294/82 | +3 closed |
| surface binding bound/partial/unresolved | 347/59/82 | 347/59/82 | invariant |
| compiler AST mapped | 0/394 | 0/394 | still blocked in WSL context |

Relative to v0.21, v0.22 preserves every surface, effect-closure, persistence, and effect total while reducing NEST boundaries by 93.6% and extension receptors by 78.5%. This demonstrates that the removed objects were generic context/repetition noise rather than recovered behaviors.

## Decision

v0.22 passes its intended generic calibration objective and is a valid sealed evidence lineage. It does **not** complete PR5: compiler coverage remains 0/394, lifecycle remains UNKNOWN, and human closure remains 347 bound / 59 partial / 82 unresolved. It is therefore superseded for convergence by the v0.23 compiler-context recovery work and must not be labeled a v1 candidate.

