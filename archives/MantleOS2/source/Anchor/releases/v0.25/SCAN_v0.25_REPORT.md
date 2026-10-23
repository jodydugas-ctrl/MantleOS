# SCAN Engine v0.25 Release Report

Release status: **FROZEN FOR CONTINUED PR5 CALIBRATION**  
Engine version: `0.25.0`  
Specimen target: `dail8859/NotepadNext@f57db52d6760a2ce4149a37190c3adaa586845f5`  
Tree: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`

## Purpose

v0.25 combines the merged v0.24 adaptive-substrate work with the generic bounded-Clang and determinism corrections learned from the v0.23 NotepadNext calibration. The historical v0.23 and v0.24 trees remain unchanged.

The Clang adapter now drains stdout and stderr concurrently, caps retained AST JSON at 64 MB, and retries an oversized or timed-out full translation-unit dump with one source-derived declaration filter. Filtered recovery is always marked `PARTIAL`; conservative C++/Qt fallback continues. Process-local Clang pointer IDs no longer enter stable IDs or persisted attributes, and case-equivalent capability tokens have a total deterministic order.

The v0.24 TypeScript/React/Electron adapters and inert adaptive-assimilation workbench are retained. Generated candidate code is never executed automatically and cannot rewrite canonical evidence.

## Frozen artifacts

| Artifact | Bytes | SHA-256 | Reproducibility |
|---|---:|---|---|
| `SCAN_ENGINE_v0.25.zip` | 235,099 | `dbc929892b26bf3d2d61916d8a9e18e0a70a32d3d9a37cb1692ec6ba98dbf6c3` | second independent build byte-identical |
| `scan_software_body-0.25.0-py3-none-any.whl` | 156,608 | `627837b08d6d7d5268edd142baac33cf6b4a285e7225afc8099d2aae620a3dc6` | second fixed-epoch build byte-identical |

The package manifest contains 83 tracked files and self-audits 83/83 with zero issues. Package-manifest SHA-256: `9eaa29ca54e651c65ce61774d98468d028dff959032024e2ccc5201abea3822e`.

## Qualification

- development suite: 140 PASS, 3 Windows privilege-dependent symlink tests skipped;
- clean extracted ZIP suite: 140 PASS, the same 3 skips;
- fresh Python 3.13.13 wheel installation: PASS, runtime version `0.25.0`;
- LLM-disabled release qualification: PASS, 12/12 required queries;
- two fresh manifest-backed scans: 21/21 emitted files byte-identical;
- canonical SQLite comparison: zero missing IDs and zero changed rows across six evidence/semantic tables;
- cache proof: 4,186 hits, 0 misses, eight cache-independent projections and nine workbench files identical.

## PR5 compiler and body result

The exact 1,928-file NotepadNext manifest was scanned twice without oracle input or specimen execution. Each run emitted:

- 125,066 nodes;
- 139,567 edges;
- 137,629 evidence records;
- 409,175 semantic objects;
- 1,016,189 semantic relations;
- 57 completeness dimensions.

Of 394 C/C++ translation units, compiler evidence is `MAPPED` for 84 and valid-but-`PARTIAL` for 294; 16 remain unavailable to Clang and retain fallback coverage. The scan records 331 explicit parser gaps. This is materially broader compiler evidence than v0.23, but it is not complete compiler or semantic closure.

Integrity remains `PARTIAL` with 13 WARN-only orphan-evidence findings and zero ERRORs. Human-surface closure remains 347 bound, 59 partial, and 82 unresolved out of 488. Effect closure remains 112 closed, 294 partial, and 82 unresolved, with feedback observed for 59 surfaces. The adaptive assessment opens an inert, deterministic workbench for Lua and Python substrate gaps.

## Sealed certification

The final packaged engine completed an LLM-disabled manifest certification under Python 3.13.13. Independent verification passed 12/12 certification files and all projection checks with zero issues. Its ten canonical scan projections and six canonical database tables are identical to the accepted cold run.

The unpublished 277,741,620-byte certification bundle is identified by SHA-256 `0834f44051ce7cf012c391e113905cbccf28754fd6143bd9388c16f7007a7fee`. The bundle is excluded from Git because of size; its receipt, manifest, and verifier output are tracked here.

## Gate decision

Mechanical certification and deterministic packaging: **PASS**. PR5 calibration: **PARTIAL**. v0.25 is a stronger frozen calibration candidate, not SCAN v1 production completion. The next generic calibration target is the inflated human-surface denominator, especially non-interactive `ui->objectName` references and metadata-derived CLI pseudo-options. H-001 remains frozen and source-uninspected.
