# PR5 calibration report — SCAN v0.26

## Decision

**Mechanical PASS / calibration PARTIAL.** v0.26 corrects the generic human-surface denominator and is deterministic, independently verifiable, and package-qualified. It does not yet justify semantic-convergence or production-ready claims.

## Accepted evidence

- Exact source: 1,928/1,928 provider blobs at commit `f57db52d6760a2ce4149a37190c3adaa586845f5`, tree `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`.
- Oracle use during scan: none; model-provider credentials disabled.
- Regression: 144/144 development tests and 144/144 clean-package tests pass; three Windows symlink-privilege cases skip.
- Two fresh cold scans: all 21 emitted files byte-identical and all canonical database rows identical.
- Cache reuse: 4,186 hits, zero misses; eight cache-independent projections, nine workbench files, and all canonical database rows unchanged.
- Final installed-wheel certification: PASS under Python 3.13.13; independent verification 12/12 files with zero issues.
- Source ZIP and wheel reproduce byte-for-byte across independent builds.

## Denominator correction

The v0.25 denominator contained 488 surfaces: 327 declared human surfaces, three factory outputs, and 158 reference-only candidates. v0.26 preserves every declared/factory surface and its closure state while reducing reference-only candidates to 50 proven Qt signal senders.

The 108 removed candidates are exactly:

- 37 pseudo-CLI options produced by unrelated objects exposing `.value(...)` or `.isSet(...)` methods; and
- 71 ordinary `ui->object` accesses that remain evidence but are not independently proven user entrances.

The retained reference candidates all carry signal-emission routes: 46 are bound and four partial. All 147 QActions remain. The real CLI set remains exactly four bound options: `--n`, `--reset-settings`, `--translation`, and `--workspace`.

Surface closure is now 380 total: 310 bound, 59 partial, and 11 unresolved. Effect closure is 87 closed, 282 partial, and 11 unresolved, with feedback observed for 59 surfaces. All 330 non-reference surfaces retain their v0.25 binding/effect states, terminal counts, and feedback counts; the changed totals are solely the removed false references.

## Certification audit note

One pre-release certification attempt correctly failed package self-audit because its package root was a wheel-build staging directory containing transient `build/` and `.egg-info` output. Its scan and 12-file seal matched, but it was rejected and excluded from release claims. The authoritative certification used a pristine extraction of the deterministic source ZIP, passed 83/83 package self-audit before execution, and then passed certification and independent verification.

## Remaining generic calibration gaps

1. Eleven candidate surfaces remain unresolved and 59 are partial; each requires generic route/closure analysis rather than specimen-specific rules.
2. Effect closure remains partial for 282 surfaces, including lifecycle, persistence/value-flow, dynamic dispatch, feedback, platform, and capability boundaries.
3. Compiler evidence remains 84 `MAPPED`, 294 `PARTIAL`, and 16 unavailable of 394 translation units, with 331 explicit parser gaps.
4. Lua and Python remain unsupported runtime substrates and correctly produce an inert adaptive workbench rather than invented conclusions.
5. External-agent reconstruction (M6B), the untouched H-001 blind holdout, and final production certification remain open.

## Next admissible work

Classify the 11 unresolved and 59 partial surfaces generically, prioritizing real QAction/UI routes and OS event entrances. Continue only with reusable rules and adversarial fixtures, then repeat the exact two-run sealed calibration. Do not add NotepadNext-specific names or oracle answers. Keep H-001 frozen and source-uninspected until candidate freeze follows an accepted PR5 convergence result.
