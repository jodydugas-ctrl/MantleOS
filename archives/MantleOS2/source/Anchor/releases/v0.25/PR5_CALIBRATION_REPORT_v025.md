# PR5 calibration report — SCAN v0.25

## Decision

**Mechanical PASS / calibration PARTIAL.** The v0.25 package is deterministic, independently verifiable, and substantially improves compiler coverage. It does not yet justify a semantic-convergence or production-ready claim.

## Accepted evidence

- Exact source: 1,928/1,928 provider blobs at commit `f57db52d6760a2ce4149a37190c3adaa586845f5`, tree `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`.
- Oracle use during scan: none.
- Two fresh scans: all 21 emitted files byte-identical; canonical database rows identical.
- Cache reuse: 4,186 hits, zero misses; canonical evidence and adaptive workbench unchanged.
- Compiler evidence: 84 `MAPPED`, 294 `PARTIAL`, 16 unavailable of 394 translation units.
- Integrity: 13 WARN, zero ERROR.
- Certification: PASS; independent verification 12/12 files, zero issues.

## Remaining generic calibration gaps

1. The human-surface denominator still contains 82 unresolved and 59 partial entries. A large share of unresolved entries are generic `ui_object_reference` observations that duplicate declarations or represent non-interactive labels, menus, and setup containers.
2. Metadata calls such as importer `.value(...)` patterns can resemble CLI option surfaces and inflate the denominator.
3. Compiler evidence is still partial for 294 translation units and absent for 16; filtered AST recovery must not be confused with full translation-unit proof.
4. Lifecycle, persistence/value flow, dynamic route closure, capability classification, platform behavior, and behavioral reconstruction remain incomplete.
5. Lua and Python appear as unsupported runtime substrates and correctly produce an inert adaptive workbench rather than invented conclusions.

## Next admissible work

Refine surface classification generically, add adversarial fixtures, rerun the exact manifest-backed calibration twice, and accept the change only if it reduces false denominator entries without hiding real interactive surfaces. Do not add NotepadNext-specific names or oracle answers. Keep H-001 untouched until the candidate-freeze and blind-holdout gate.
