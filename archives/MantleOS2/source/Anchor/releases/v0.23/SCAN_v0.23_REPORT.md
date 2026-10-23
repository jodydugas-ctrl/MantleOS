# SCAN Engine v0.23 Release Report

Release status: **FROZEN FOR PR5 COMPILER-ENABLED CALIBRATION**  
Engine version: `0.23.0`  
Specimen target: `dail8859/NotepadNext@f57db52d6760a2ce4149a37190c3adaa586845f5`  
Tree: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`

## Purpose

v0.23 is a generic PR1/PR2 correction admitted by the sealed v0.22 calibration. It recovers valid source-local Clang JSON AST evidence even when unavailable dependencies make Clang exit nonzero, while retaining the diagnostic as a `PARTIAL` parser gap. Invalid, absent, timed-out, or oversized compiler output is never promoted. Fallback C++/Qt extraction continues for every bounded compiler region.

The release also removes volatile wall-clock and elapsed-time values from canonical projections. Two fresh unchanged scans must now emit byte-identical JSON/Markdown projections and projection manifests.

## Safety and resource bounds

- Clang is invoked directly with a read-only, whitelisted parse context; specimen build scripts, response files, plugins, generated commands, and linker steps are not executed.
- Compiler time is limited to five seconds per translation unit.
- JSON AST parsing is limited to 64,000,000 bytes per translation unit.
- Oversized compiler output becomes an explicit `PARTIAL` parser gap.
- Source-local provenance filtering remains mandatory; declarations from included headers are not attributed to the main source file.

## Frozen artifacts

| Artifact | Bytes | SHA-256 | Reproducibility |
|---|---:|---|---|
| `SCAN_ENGINE_v0.23.zip` | 196,917 | `9f0caf7b74abd98d6fcd730eca31cf050447f4fef3cbf88e59691152b9dfe168` | second independent build byte-identical |
| `scan_software_body-0.23.0-py3-none-any.whl` | 124,217 | `2888ac5a4c47e078d5360e1aa13fe4e2bdfe45db87b680954648222387c65472` | second fixed-epoch build byte-identical |

The manifest-only source contains 68 tracked files plus `PACKAGE_MANIFEST.json`, with zero bytecode files. Package-manifest SHA-256: `2bbf4180867fa563367f92fe894c3d0ed7fadd09dfde2206b3ec83c1119f05de`.

## Qualification

- development suite: 122 tests PASS, 3 Windows privilege-dependent symlink tests skipped;
- clean extracted ZIP suite: 122 tests PASS, same 3 skips;
- extracted package audit: 68/68 PASS, zero issues;
- fresh Python 3.12.14 wheel installation: PASS, runtime version `0.23.0`;
- LLM-disabled release qualification: 12/12 required queries PASS, integrity `MAPPED`, zero integrity errors;
- fresh unchanged projection determinism: PASS, byte-identical JSON/Markdown projections and projection hashes.

## Whole-specimen compiler probe

The frozen generic adapter was measured over all 394 authenticated NotepadNext C/C++ translation units using Windows Clang 22.1.5, a five-second compiler ceiling, and a 64 MB JSON parse ceiling:

| Measure | Result |
|---|---:|
| Complete compiler ASTs | 83 |
| Recovered diagnostic/partial ASTs | 74 |
| Explicit unavailable/bounded gaps | 237 |
| Valid AST coverage | 157 / 394 |
| Compiler nodes / edges / evidence | 11,092 / 10,494 / 10,934 |
| Parser gaps | 311 |
| Runtime | 1,125.812 seconds |
| Largest observed AST JSON | 516,776,119 bytes |

The largest bounded outputs originate mainly in vendored Scintilla/Lexilla translation units. They remain covered by conservative fallback and explicit compiler gaps rather than consuming unbounded parser memory.

## PR5 completed sealed calibration

The exact frozen wheel/package completed the compiler-enabled, LLM-disabled, manifest-backed NotepadNext certification on Windows. The 238,559,287-byte sealed bundle has SHA-256 `00a0d49bcf5914512a787e75ca99245fe6e498fc1b16ac79e17bc54ef762c6b3`. The receipt states mechanical PASS, 12/12 required queries PASS, 1,928/1,928 files materialized, zero integrity errors, and zero parser failures. A fresh read-only verification of the certification directory independently verified 12/12 manifest files, projection PASS, and zero issues.

The v0.22-to-v0.23 comparison preserves the exact provider tree/fingerprint and LLM-disabled mechanical PASS on both sides. The compiler dimension advanced from BLOCKED (0 mapped ASTs) to PARTIAL (83 mapped and 74 partial ASTs out of 394 translation units); 237 remained unavailable or resource-bounded, with 311 explicit parser gaps. Human-surface closure did not advance: 347 bound, 59 partial, 82 unresolved; effect closure remained 112 closed, 294 partial, 82 unresolved. NEST boundary count changed from 84 to 85. Consequently the PR5 gate remains **calibration PARTIAL**, not semantic convergence or production certification. The immutable v0.20 cold baseline and untouched H-001 holdout are unchanged.
