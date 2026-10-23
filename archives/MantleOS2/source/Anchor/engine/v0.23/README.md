# SCAN Engine v0.23

Reusable evidence-first scanner for the SCAN project.

SCAN is a **scanning engine first and an LLM reasoning system second**. It inventories immutable specimen bytes, runs substrate-specific extraction adapters, stores fine-grained evidence, and builds a normalized cross-object evidence graph before semantic interpretation. `scan_index.sqlite` is canonical. JSON and Markdown files are projections of that store.

## What changed in v0.23

v0.23 retains a valid, source-local Clang JSON AST when compiler diagnostics cause a nonzero exit, while recording both the parser result and compiler coverage as `PARTIAL`. This is a generic recovery path for incomplete dependency/build environments: no diagnostic is hidden, conservative fallback extraction still runs, and invalid or absent AST output remains an explicit parser gap. Compiler execution has a five-second per-translation-unit ceiling and compiler JSON has a 64 MB parse ceiling so pathological trees cannot consume unbounded time or parser memory; a bounded AST remains a visible PARTIAL gap and fallback extraction continues. The completeness vector distinguishes fully mapped compiler ASTs from diagnostically recovered partial ASTs. v0.23 also removes volatile wall-clock and elapsed-time fields from canonical projections and requires two fresh unchanged scans to emit byte-identical JSON/Markdown projections and projection hashes.

## What changed in v0.22

v0.22 continues the generic PR5 calibration loop after the sealed v0.21 rerun. Generic boundary and extension recognizers now distinguish executable C-family tokens from comments and literal bodies. Vendored source roots (including the common `thirdparty` spelling), tests/fixtures, installer/deployment material, static assets, and root project-license/readme records retain direct repository-reference evidence without being promoted to application-runtime NEST seams. Literal URLs in application source remain explicit runtime candidates through the generic adapter, while typed Qt/source identifiers continue to generate framework boundary evidence. Repeated lexical boundary/receptor occurrences are aggregated into one translation-unit/capability object with every direct occurrence retained as evidence and function-level edges preserved.

The C++ fallback now masks each translation unit once and shares that immutable same-offset view across class, function, call, declaration, assignment, boundary, and extension recognizers. The exact 1,928-file PR5 adapter probe fell from more than ten minutes without completing to about 41 seconds after this change. The generic adapter likewise uses precomputed line offsets instead of rescanning the entire file for every token.

## What changed in v0.21

v0.21 begins the generic PR5 calibration-correction loop. Local byte reads now preserve the no-follow and path-to-handle identity guard without comparing incompatible Windows `lstat`/`fstat` ctime semantics. Manifest-backed scans normalize an exact hexadecimal `revision` into `commit_sha` when the manifest does not repeat that value, so certification receipts retain the pinned commit identity. Direct local/parameter receiver declarations can now support typed persistence and extension effects when compiler context is unavailable, and generic URL/environment/extension tokens in documentation, workflows, build metadata, localization, and vendored source remain repository evidence without being inflated into application-runtime NEST boundaries.

## What changed in v0.20

v0.20 establishes **M6A source-blind reconstruction-proof infrastructure**. A verified reconstruction-aware certification can now be split into a source-free public challenge and a private evaluator. A reconstruction candidate is rescanned and scored against mechanically derived reconstruction signatures without comparing original and reconstructed source code.

New reusable behavior:

- `scan-body prepare-reconstruction-trial` emits separately sealed public challenge and private evaluator packages;
- the public challenge mechanically excludes original source bytes, the canonical SQLite database, evidence catalogs/graphs, source excerpts, original source paths, and the evaluator;
- the public challenge **does include source-free scoring signatures** needed for a fair reconstruction: visible surface text/type, required binding/effect closure, and MAPPED terminal effect/capability signatures;
- the reconstruction agent must submit a challenge-bound source-isolation declaration; admitted original-source, parent-certification, evaluator, or network-source access invalidates the trial before candidate scanning;
- `scan-body score-reconstruction-trial` rescans the candidate and compares human-facing surface text/type, binding closure, effect closure, and MAPPED terminal capability/effect signatures;
- mismatch attribution distinguishes `RECONSTRUCTION_AGENT`, `SEMANTIC_IR`, `SCANNER_CANDIDATE_COVERAGE`, and `UNRESOLVED_SOURCE_UNCERTAINTY`;
- weak/contradicted original evidence is never converted into a strong reconstruction-agent failure;
- the scored candidate, candidate scan, submission, scorecard, receipt, and lineage are sealed in `TRIAL_MANIFEST.json`;
- `scan-body verify-reconstruction-trial` detects post-score tampering;
- public challenge ZIP generation is deterministic for the same certified parent;
- regression coverage expands from 102 to **111 passing tests** before release qualification.

M6A is intentionally static. It does not execute the reconstructed candidate and therefore does not complete PR7 by itself. Full PR7 still requires a genuinely source-blind external coding agent and behavior-level surrogate evaluation. See `docs/RECONSTRUCTION_TRIAL.md`.

### M6A reconstruction workflow

```text
verified reconstruction certification
        |
        +--> public challenge.zip ------> source-blind coding agent
        |                                  |
        |                                  v
        |                            reconstructed candidate
        |                                  |
        +--> private evaluator ------------+
                                           |
                                           v
                            scan-body score-reconstruction-trial
                                           |
                         +-----------------+-----------------+
                         |                 |                 |
                    candidate scan     scorecard        attribution
                         |                 |                 |
                         +-----------------+-----------------+
                                           |
                                           v
                                  sealed trial receipt
```

## What changed in v0.19

v0.19 establishes the first **M5 auditable semantic-synthesis and reconstruction-promotion gate**. SCAN still does not ask an LLM to become the scanner. A human or LLM may author a reconstruction proposal, but promotion into the canonical graph is mechanical and evidence-gated.

New reusable behavior:

- `scan-body validate-reconstruction` validates an external semantic proposal without mutating `scan_index.sqlite`;
- `scan-body promote-reconstruction` accepts only proposal objects whose positive proof chains reach first-class source evidence;
- promoted reconstruction anchors require typed support from a `BEHAVIOR`, `ARTERY`, `NERVE`, or `CAPABILITY` object rather than unsupported prose;
- behavior contracts require explicit trigger, observable response, and uncertainty fields; reconstruction anchors require a testable property, fidelity test, and uncertainty field;
- a `MAPPED` reconstruction anchor is rejected when its proof chain contains `PARTIAL`, `BLOCKED`, or `UNKNOWN` support, or when visible contradictory evidence reaches the anchor;
- rejected proposals do not mutate the canonical semantic graph; successful semantic bundles are committed atomically;
- `reconstruction_contract.json` is exported as a projection of the canonical graph and carries anchor IDs, behavior IDs, proof status, source/evidence IDs, contradictions, fidelity tests, and the completeness vector;
- `scan-body certify-reconstruction` derives a new sealed reconstruction-aware handoff from an already verified mechanical certification. The parent certification remains byte-for-byte immutable and is recorded by SHA-256 in the child receipt;
- read-only SCAN commands now open the SQLite index using immutable read mode so `query`, `why`, `impact`, `object`, audit/closure inspection, and certification verification cannot create WAL/SHM sidecars or silently alter sealed bytes;
- SQLite failure paths now close failed connections before propagating errors, eliminating the prior resource-warning leak;
- regression coverage expands to **102 passing tests** for this slice.

The authority boundary is deliberate: external semantic generation may propose meaning, but SCAN only certifies the proposal's typed structure, evidence reachability, coverage discipline, contradiction visibility, canonical promotion, and sealed lineage. Promotion never upgrades an interpretation to `DIRECT` evidence.

### M5 reconstruction workflow

```text
mechanically certified SCAN handoff
        |
        v
external human/LLM reconstruction proposal
        |
        v
scan-body validate-reconstruction
        | PASS only
        v
scan-body promote-reconstruction
        |
        +--> canonical BEHAVIOR / ARTERY / NERVE / CAPABILITY / RA objects
        +--> reconstruction_contract.json
        |
        v
scan-body certify-reconstruction
        |
        v
new sealed child handoff + parent SHA-256 lineage
```

A child certification is not permission to forget the parent. The parent is the immutable mechanical evidence body; the child adds a mechanically validated semantic layer that remains traceable back to it.

## What changed in v0.18

v0.18 added the agent-facing specimen-certification protocol: `certify`, `certify-manifest`, `verify-certification`, sealed certification manifests/receipts, and the rule that certification PASS means mechanically trustworthy evidence bytes—not complete understanding. Provider-backed certification preserves repository/commit/tree provenance instead of flattening exact-revision acquisition into anonymous local files.

## What changed in v0.17

v0.17 hardens parser/adaptor fault containment and resume behavior. A malformed artifact or one adapter exception must not erase the rest of an otherwise readable specimen. This is a PR1 refinement; it does not turn missing parser evidence into successful coverage.

New reusable behavior:

- unexpected ordinary adapter exceptions are isolated to the affected artifact/adapter and emitted as first-class `parser_failure` findings with adapter/version/error provenance;
- the affected file is downgraded to explicit `PARTIAL` parser coverage and retains structured `adapter_failures` metadata;
- other adapters for the same file and other files continue, so a local parser defect does not silently remove unrelated anatomy;
- adapter failures are not cached as successful extraction;
- `MemoryError` remains fatal rather than being mislabeled as a recoverable source/parser gap;
- existing adapter-native malformed-input handling (for example malformed Qt `.ui` XML) remains explicit `BLOCKED`/`parser_gap` evidence;
- a budget-limited scan can be rerun unbounded in the same output directory, reuse previously valid extraction-cache entries, and complete without treating the earlier partial state as authoritative;
- regression coverage expands from 85 to **90 passing tests** after this slice.

The default policy is deliberately asymmetric: recover from *local parser failures* while refusing to downgrade process-level memory exhaustion. The result is more robust without turning catastrophic runtime conditions into misleading PARTIAL coverage.


## What changed in v0.16

v0.16 is a PR1/PR8 release-hardening slice. It does not change SCAN's governing anatomy model. It makes bounded execution, corruption recovery, package verification, and mechanical release qualification explicit and testable.

New production-oriented behavior:

- aggregate local/manifest byte and materialized-file ceilings preserve the full visible census while marking over-budget entries as explicit `RESOURCE_LIMIT_TOTAL_BYTES` / `RESOURCE_LIMIT_TOTAL_FILES`;
- extraction time/node/edge/evidence ceilings stop only at safe file/adapter boundaries so a partially committed adapter result cannot corrupt the canonical graph;
- injected cancellation produces a normal partial SCAN package with a first-class `scan_budget` finding instead of pretending completion or discarding already measured evidence;
- budget-limited parser-eligible files remain present and are downgraded to explicit `PARTIAL` parser coverage;
- the canonical SQLite store now runs `PRAGMA quick_check` on open. During a new scan, a corrupt derived index is quarantined and cleanly rebuilt; read-only consumers do **not** silently replace a corrupt database;
- SQLite `user_version=1` establishes the first explicit derived-store schema contract. Compatible legacy v0 stores are promoted; incompatible current-map tables are deterministically rebuilt rather than guessed forward; newer unknown schemas are refused;
- the CLI now exposes the production acceptance query surface for external writes, UNKNOWN routes, NEST-dependent actions, disconnected handlers, high-connectivity junctions, hidden-surface candidates, capabilities with no human route, and authentication/permission pathways;
- `scan-body self-audit` verifies package bytes and optional emitted projection bytes;
- `scan-body package-manifest` deterministically regenerates the release manifest;
- `scan-body qualify` runs a packaged mechanical qualification with common LLM credentials removed, verifies canonical outputs/integrity/projection hashes, and executes all required release queries;
- regression coverage expands from 76 to **85 passing tests** in the development tree.

The qualification fixture is scanner-owned and synthetic. Passing it proves the release machinery and query surface execute coherently; it does not substitute for PR5 NotepadNext calibration, PR6 H-001 blind transferability, or PR7 reconstruction proof.

### Aggregate budget controls

Local and manifest scans accept these optional ceilings (all `0` means disabled):

```text
--max-total-bytes
--max-materialized-files
--max-extraction-seconds
--max-nodes
--max-edges
--max-evidence
```

Per-file `--max-file-bytes` remains independent. Aggregate inventory byte/file ceilings are hard. Extraction time/graph ceilings are checked between files/adapters so canonical graph writes stay atomic at that unit.

### Release verification commands

```text
scan-body package-manifest <package-root>
scan-body self-audit <package-root> [--scan-output <scan-dir>]
scan-body qualify <package-root> [--out qualification.json]
```

`self-audit` verifies exact packaged file sizes/SHA-256 values, engine/`pyproject` version agreement, projection hashes, and SQLite quick-check state. `qualify` additionally performs a fresh mechanical scan with common LLM API-key variables removed and runs the production query-acceptance surface.

## What changed in v0.15

v0.15 closes a generic asynchronous-control-flow gap exposed by the qView transferability work. The change remains code-first and evidence-first: the scanner records only mechanically observed launch, watcher, event, and continuation relationships, while missing launch/continuation evidence stays `PARTIAL`. No qView-specific action, class, or file names are embedded in the mechanism.

New reusable async behavior:

- assigned `QtConcurrent::run(...)` launches become first-class `async_task` nodes linked from their containing function by `triggers_async`;
- unassigned `QtConcurrent::run(...)` launches remain visible as `PARTIAL` async tasks rather than being silently dropped;
- `QFutureWatcher::setFuture(...)` links a future-producing task to the watcher with `delivers_async_to`; externally supplied or otherwise unobserved futures become `async_task_reference` nodes with explicit `PARTIAL` coverage;
- existing Qt signal/slot extraction then carries the watcher through its `finished` event to the observed continuation handler;
- deep effect closure traverses `triggers_async` and `delivers_async_to`, allowing a human surface to remain traceable across a QtConcurrent/QFutureWatcher boundary to downstream state, effect, and NEST terminals;
- the C++/Qt adapter version is bumped so stale cached extraction from pre-v0.15 semantics cannot be reused silently;
- regression coverage expands from 72 to **76 passing tests**.

The Machine Body Map schema remains `scan-machine-body-map/0.9`; v0.15 adds richer evidence/edge coverage without changing the canonical schema shape or collapsing BODY and NEST capabilities.

## What changed in v0.14

v0.14 begins the PR1/PR8 production-hardening phase. It does not add a new anatomy model. It hardens the byte boundary that feeds the existing scanner so hostile or pathological local/provider inputs remain explicit evidence states instead of becoming accidental reads.

New reusable safety behavior:

- local scan roots that are symbolic links are rejected rather than silently resolved;
- file and directory symlinks inside a local specimen are accounted for as `SYMLINK_REFERENCE` anatomy and are never followed for parser input;
- special/non-regular files are recorded as blocked rather than opened;
- local files are opened with no-follow semantics where the platform provides them, checked with `lstat`/`fstat`, and reread only when identity/size/timestamps and content digest remain consistent;
- materialized manifest paths reject traversal and symlinked components before becoming parser-eligible;
- local and manifest reads have a configurable per-file byte ceiling (64 MiB default, `0` disables); oversized files become explicit `RESOURCE_LIMIT` gaps;
- GitHub acquisition has a matching configurable per-blob ceiling and refuses provider-declared oversized blobs before requesting their bytes;
- CLI exposes `--max-file-bytes` and `--max-blob-bytes` so the safety budget is operator-visible rather than hidden;
- regression coverage expands from 66 to **72 passing tests**.

These limits are safety/resource controls, not claims that files above the default are irrelevant. A blocked oversized item stays in the specimen ledger and can be rescanned with an explicitly larger budget.

The Machine Body Map schema remains `scan-machine-body-map/0.9`; v0.14 changes acquisition/read safety and explicit coverage states rather than canonical graph shape.


## v0.13 semantic-action refinement

v0.13 is a transferability refinement driven by a human-held oracle built from the pinned qView specimen `jurplel/qView@c5eca1c7176549e0f0718d11201547ddcdb1f8c9`. The qView oracle is **not** reported as a cold SCAN result. It was used to identify generic scanner mechanisms that a later holdout specimen must validate independently.

The oracle exposed three important static-analysis requirements that were not explicit enough in v0.12:

1. one semantic action may have many physical `QAction` instances through menu/context/shortcut clones;
2. action behavior may be selected by a string payload stored in `QAction::data()` rather than by a direct signal-to-handler connection;
3. build files may contain contradictory feature-state evidence that must be preserved rather than silently reconciled.

v0.13 implements these classes generically, without qView-specific action names.

## New reusable behavior

- keyed QAction registries such as `actionLibrary.insert("key", action)` become stable `semantic_action` identities;
- `addCloneOfAction(..., "key")` creates a distinct `surface_instance` linked to the semantic action, preventing clone count from inflating behavior count;
- payload dispatch from `triggeredAction->data().toStringList().first()` is represented as explicit `dispatch_case` objects for equality and `startsWith(...)` families;
- bounded indexed action families such as `"recent" + QString::number(i)` inside `for (i < bound)` become `dynamic_surface_family` objects with the static bound expression retained;
- registry actions with no mechanically observed payload dispatch remain visible as `semantic_action_dispatch_gap` candidates rather than being dropped;
- duplicate keyed dispatch branches are preserved as `duplicate_dispatch_case` anomalies without guessing whether they are intentional, unreachable, or defective;
- CMake now records `build_condition_contradiction` when a compile definition for `SYMBOL` is asserted inside an enclosing `if(NOT SYMBOL)` block; the scanner preserves both facts and does not infer the intended build state;
- adapter versions are bumped so cached extraction from older semantics is not reused silently;
- regression coverage expands from 60 to **66 passing tests**.

The Machine Body Map schema remains `scan-machine-body-map/0.9`; v0.13 adds richer extracted anatomy without changing the canonical schema shape.

## PR6C qView oracle status

The qView work is a **development oracle**, not a production transferability pass. Manual evidence at the pinned revision established a useful hidden exam including:

- 41 canonical static semantic QAction identities;
- two bounded 10-slot dynamic families for Recent and Open-With behavior;
- cloned menu/context/shortcut routes that must not be counted as distinct semantic behaviors;
- payload-key dispatch through `QAction::data()`;
- an orphan semantic-action candidate (`toggletitlebar`) and a duplicate `open` dispatch branch;
- asynchronous image loading/preloading through `QtConcurrent` / `QFutureWatcher`;
- platform-specific Open-With, trash/restore, ICC/profile, native-menu, and process capabilities;
- persistent settings and shortcut state;
- a direct static build-condition contradiction involving `QV_DISABLE_ONLINE_VERSION_CHECK`.

Because those facts informed v0.13 design, qView can no longer serve as the final blind holdout for PR6. It remains useful for regression comparison, but production certification needs a separate unfamiliar large C++/Qt application scanned after the v1 candidate is frozen.

## Canonical store and projections

A v0.16 scan output contains:

```text
scan_index.sqlite
machine_body_map.json
evidence_graph.json
evidence_catalog.json
completeness_vector.json
integrity_report.json
surface_closure.json
effect_closure.json
nest_capability_map.json
projection_manifest.json
stage1_summary.md
```

The projections are never independent authorities. Their IDs refer back to the same canonical database.

## Compiler-assisted C/C++ parsing

If `clang++` or `clang` is available, SCAN attempts a read-only JSON-AST parse before the conservative fallback C++ adapters. It invokes a fixed analyzer binary directly and never executes the compiler command stored by the specimen. `compile_commands.json` contributes only whitelisted parse context.

Compiler-context gaps stay explicit. The full compiler AST may be consulted internally to resolve referenced declarations and types, but declarations originating from external/system headers are not automatically emitted as source-owned BODY anatomy of the translation unit.

## Current engineering frontier

The M3 mechanism-family baseline remains complete through M3C. v0.16 retains the v0.13 semantic-action/build-state model and v0.14 byte-boundary hardening, and adds aggregate bounded-execution/cancellation, derived-store corruption recovery, deterministic package self-audit, and an LLM-disabled mechanical release qualification. It does **not** satisfy PR5, PR6, PR7, the full install/performance matrix, or the v1 production-grade claim by itself.

The next priorities are:

1. obtain the complete pinned NotepadNext bytes and execute M4 cold calibration as soon as the acquisition boundary opens;
2. finish a full qView regression comparison when exact full source/build/resource bytes can be materialized locally, but treat qView as a development specimen rather than the final blind holdout;
3. preserve H-001 (`sqlitebrowser/sqlitebrowser`) as the frozen blind holdout and scan it only after the v1 candidate is otherwise ready;
4. complete evidence-backed semantic synthesis and the blind source-free reconstruction experiment;
5. continue PR1/PR8 hardening beyond the now-tested byte/aggregate-budget/cancellation/corruption/self-audit qualification layer: malformed parser/crash corpus, archive extraction safety if archives become an input mode, larger-repository load/resume/performance, cross-platform install matrix, and final operator/schema documentation.

The project remains below the v1 quality gate until PR1-PR8 pass.


## Agent handoff certification (v0.18+)

For a local specimen whose bytes are already available, SCAN can produce a sealed evidence handoff:

```bash
scan-body certify /path/to/extracted/scan-release /path/to/specimen \
  --out specimen.scan-cert \
  --bundle specimen.scan-cert.zip \
  --specimen-id my-pinned-specimen

scan-body verify-certification specimen.scan-cert

# For a provider acquisition/source manifest:
scan-body certify-manifest /path/to/extracted/scan-release source_manifest.json \
  --content-root acquired/content --out repo.scan-cert --bundle repo.scan-cert.zip
```

The receipt's `state=PASS` certifies mechanical integrity of the evidence package, **not semantic completeness**. Consumers must inspect `coverage`, `completeness_vector.json`, unresolved surfaces, acquisition gaps, and explicit `UNKNOWN/PARTIAL/BLOCKED` states before treating a capability as established.
