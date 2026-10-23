# SCAN PROTOCOL
Version: 0.32
Mode: Progressive / Read-Only by default
Primary test specimen: NotepadNext
Companion governance file: ANCHOR_CODING_PROMPT.md

## Mission

Perform a software **SCAN**: a non-destructive, code-first examination of a software repository that reconstructs as much of the visible software entity as deterministic evidence allows.

Treat the software as a biological entity only as an analytical aid. The goal is not metaphor for its own sake. The goal is to reveal anatomy, circulation, boundaries, control pathways, surfaces, unusual structures, and safe observation points that ordinary documentation may overlook.

The scanner should eventually do most of this work without an LLM.

The LLM's primary role is to help build or improve deterministic scanner tooling and, later, interpret the completed evidence map. Do not use prose reasoning as a substitute for data that code can obtain.

**Primary purpose:** scan the software and preserve the evidence-rich body map.

**Secondary uses:** derive lifecycle models, behavior contracts, capability maps, control-surface maps, NEST coupling maps, and Specimen Reconstruction Anchors that can guide a future coding agent in recreating the application's control surfaces and effective abilities with the highest fidelity the evidence supports. These derived products must remain downstream of the scan and traceable to it.

SCAN is not intended to birth an AppAI or migrate an agent into a host. Prior AppAI/NEST examples are useful because they expose the importance of substrate and environment, but SCAN's goal is software radiology and evidence-backed reconstruction fidelity.

Before beginning, read and obey every active anchor in `ANCHOR_CODING_PROMPT.md`.

## v0.32 surface-denominator and evidence-preservation boundary

The frozen v0.26 scanner keeps canonical scanning mechanical and LLM-disabled. Compiler processes must be bounded while running, not merely checked after an unbounded capture: stdout and stderr are drained concurrently, retained AST JSON is capped, and timeout/output-limit recovery may use only a mechanically source-derived declaration filter. Filtered compiler results remain `PARTIAL`, and generic fallback extraction must continue when recovery cannot establish a valid AST.

Process-local parser identities, scheduling races, wall-clock values, and unordered case-equivalent tokens must not enter canonical stable IDs or projections. Two fresh scans of unchanged manifest-backed bytes must match byte-for-byte and at the canonical database-row level. A warm-cache proof must reproduce the same canonical evidence.

Adaptive substrate assessment occurs only after canonical outputs are sealed. It may emit an inert workbench describing unsupported languages or structural gaps, but generated adapters are never trusted, imported, or executed automatically. Promotion requires generic fixtures, frozen-baseline regression, two deterministic rescans, integrity gates, and adversarial review. Specimen-specific names, oracle conclusions, and answer-key logic remain prohibited.

Human-surface classification must distinguish evidence from denominator admission. Ordinary UI-object references remain graph evidence but do not become human entrances merely because code reads or configures them. A declaration-less Qt reference may enter the denominator when a signal connection proves it is a sender. Similarly named consumer methods such as `.value(...)` or `.isSet(...)` become CLI evidence only when their receiver is proven to be a command-line parser. Denominator corrections must preserve all established declared/factory surfaces and their closure states, and must pass two fresh sealed reruns plus cache and certification parity.

## v0.29 PR5 cold-scan and calibration boundary

The pinned NotepadNext specimen was acquired and sealed independently of the manual oracle. Required identity is commit `f57db52d6760a2ce4149a37190c3adaa586845f5`, tree `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`. All 1,928 provider blobs were verified and preserved in the accepted exact acquisition package, SHA-256 `4a1343f4f56500ba850162039e7483e2f17f894be6493f5afbaacdf25c2c44a3`.

The operator completed the required cold sequence:

1. recover and hash-verify the authentic Engine v0.20 wheel, engine package, and `RUN_PR5_NOTEPADNEXT_COLD_v020.ps1` lineage;
2. run the cold, LLM-disabled mechanical certification against the complete pinned checkout;
3. seal the scan outputs, logs, receipts, package manifest, engine/wheel identities, commit, tree, and source-archive digest;
4. independently verify the sealed package;
5. only then exposed the preserved manual NotepadNext oracle for discrepancy classification.

The authenticated v0.20 run completed with LLM access disabled, 1,928/1,928 materialized files, zero unavailable content files, zero parser failures, and a mechanically valid certification package at SHA-256 `6c0d476e2dd7a63481cf388e6d654798ffa26f8c72ce9760a8bd60667b075ce3`. Independent verification passed 12/12 files with zero issues. Post-seal comparison therefore advances PR5 to **COLD SCAN PASS / CALIBRATION PARTIAL**. Generic scanner corrections may follow; NotepadNext-specific recognizers remain prohibited.

## v0.20 Stage 1 architecture contract

SCAN formally adopts the Scanner Architecture and Stage 1 Implementation Directive as its execution model. For supported static-scanning substrates, **ordinary D0-D3 / Stage 1-2 work must remain mechanically executable with the LLM unavailable**. The scanner may use parsers, AST/CST/compiler metadata, build files, UI resources, repository topology, graph algorithms, control/data-flow evidence, manifests, configuration, and runtime/environment inspection, but repeatable enumeration and relationship discovery belong in reusable code.

A v1 candidate therefore needs a mechanical-independence qualification run that disables LLM assistance and still produces the canonical database, evidence/projection artifacts, completeness vector, integrity audit, closure maps, and core mechanical queries. LLM interpretation may then operate on selected evidence and graph neighborhoods without rereading the repository.

The supported query surface should mechanically answer, where applicable: human-facing actions with no handler; subprocess/NEST boundaries; extension receptors; external-write paths; routes becoming UNKNOWN; NEST-dependent actions; disconnected handlers; highly connected junctions; dynamic registrations; hidden-surface candidates; capabilities with no known human route; and authentication/permission-touching pathways.

Repository size is explicitly an engineering problem: content hashing, cache reuse, dependency-aware invalidation where practical, normalized graph storage, bounded resource use, resumability, and targeted deepening are release concerns rather than optional optimizations.


## v0.18 agent-facing certification and handoff

A local specimen may now be scanned into a sealed machine-verifiable evidence handoff with `scan-body certify`. The certification path uses the ordinary read-only scanner, removes common LLM credentials, verifies the exact SCAN release package, runs integrity/projection/query gates, records the specimen fingerprint and resource policy, and seals the emitted evidence bytes in `CERTIFICATION_MANIFEST.json`. `scan-body certify-manifest` applies the same gate to provider/source manifests while preserving repository/commit/tree acquisition provenance. `scan-body verify-certification` re-hashes the sealed files and re-validates canonical projection/database integrity after transfer.

The receipt separates **mechanical integrity** from **coverage**. `state=PASS` means the evidence handoff passed the mechanical gates. It never means all specimen behavior is known. The consuming agent must still inspect the completeness vector, unresolved surfaces, parser/acquisition gaps, NEST provenance, and explicit `UNKNOWN/PARTIAL/BLOCKED` states. A valid partial scan is evidence; it is not permission to fill its holes with plausible prose.

Measured v0.18 release status: **94/94 tests PASS** in both development and a fresh extracted release package; package self-audit verifies **60/60 tracked files**; LLM-disabled qualification executes **12/12 required queries**. The v0.18 wheel installs in a fresh Python 3.13.5 virtual environment, and the installed `scan-body` CLI successfully creates and independently verifies a sealed certification bundle.

## v0.17 parser/adaptor fault containment and resume

Ordinary extraction must isolate an unexpected adapter exception to the affected file/adapter when safe to do so. SCAN records a first-class `parser_failure`, adapter/version/error provenance, and explicit `PARTIAL` file coverage, then continues independent adapters/files. A failed extraction is never cached as success. `MemoryError` remains fatal rather than being downgraded to a recoverable parser gap.

A deliberately budget-limited partial scan may be rerun unbounded in the same output directory. Valid content/version cache entries from the partial pass are reusable, while earlier `PARTIAL` coverage is recomputed from the current run rather than treated as authority.

Measured v0.17 regression status: **90/90 PASS** in the development tree and a fresh extracted release package. Package self-audit verifies **58/58** tracked files with zero issues; LLM-disabled qualification executes **12/12** required mechanical queries.

## v0.16 PR1/PR8 release qualification and aggregate budgets

Aggregate byte/file/time/node/edge/evidence budgets and injected cancellation stop at safe boundaries and preserve explicit incomplete coverage. The derived SQLite store has an explicit schema version and corruption policy: scan-time corruption is quarantined and cleanly rebuilt from specimen evidence, while read-only consumers fail rather than silently replacing the damaged artifact.

The release CLI provides deterministic package manifests, package/projection self-audit, and an LLM-disabled qualification run. The required mechanical query surface includes unresolved human surfaces, subprocess/NEST boundaries, extension receptors, external writes, UNKNOWN/PARTIAL/BLOCKED routes, NEST-dependent actions, disconnected handlers, high-connectivity junctions, dynamic registrations, hidden-surface candidates, capabilities without known human routes, and authentication/permission pathways.

## v0.15 asynchronous event/capability closure

Mechanically observed `QtConcurrent::run(...)` work becomes explicit async-task anatomy. Assigned futures can link through `QFutureWatcher::setFuture(...)`, watcher `finished` events, and observed continuations, allowing deep effect closure to cross supported asynchronous boundaries. Missing future origins or continuations remain explicit `PARTIAL` references rather than inferred behavior.

## v0.27 M6A source-blind reconstruction-trial contract

M6A turns a reconstruction-aware certification into a reproducible static experiment without exposing the original source to the reconstruction agent. The experiment has two sealed inputs with intentionally different authority:

- **public challenge** — may be given to the reconstruction agent; contains sanitized behavior/anchor contracts, completeness states, source-free human-surface requirements, required closure strength, and MAPPED effect/capability terminal signatures;
- **private evaluator** — must remain outside the reconstruction-agent context; contains exact mechanically derived expectations, lineage hashes, and scoring internals.

The public challenge must not contain original specimen source bytes, source evidence excerpts, original source paths, the canonical SQLite database, evidence catalog/graph payloads, or the private evaluator. Blindness is not permission to hide scoring criteria: every mechanically scorable requirement used for a binary reconstruction decision must have a source-free representation in the public challenge. PARTIAL/BLOCKED/UNKNOWN source terminals may be disclosed as uncertainty but may not become required binary-failure conditions.

A reconstruction submission is bound to one challenge ID and records source-isolation facts. If the submission states that original source, the parent certification, the private evaluator, or repository/network source lookup was used, the trial is invalid before candidate scanning. This declaration is not proof of sandboxing; external enforcement level stays explicit.

The candidate is scanned mechanically and compared by recoverable behavior structure rather than source similarity. The current static scorer may compare human-visible surface text/type, binding closure, effect closure, and MAPPED terminal effect/capability/boundary signatures. Per-anchor states and attribution are authoritative; any aggregate fidelity score is convenience only.

Mismatch attribution must distinguish at least:

- `RECONSTRUCTION_AGENT` — strong source requirement, adequate candidate scan, required signature absent;
- `SEMANTIC_IR` — promoted anchor has no mechanically scorable reconstruction signature;
- `SCANNER_CANDIDATE_COVERAGE` — candidate scan coverage is too weak for a strong judgment;
- `UNRESOLVED_SOURCE_UNCERTAINTY` — original evidence is partial, contradicted, or otherwise insufficient for a binary failure claim;
- `PASS` — mechanically scorable requirement recovered.

The scored candidate bytes, submission, candidate scan, scorecard, receipt, and lineage are sealed in a trial manifest and must support independent tamper verification.

This establishes M6A static proof infrastructure only. It does not execute the reconstructed application and therefore does not complete PR7. Full M6/PR7 requires a capable external source-blind coding agent and behavior-level surrogate evaluation. Any runtime stimulation belongs to separately authorized M6B/D5 work under A1.

## v0.26 M5 semantic-promotion and reconstruction-lineage contract

After deterministic evidence exists, an external human or LLM may propose `INTERPRETATION`, `BEHAVIOR`, `ARTERY`, `NERVE`, `CAPABILITY`, and `RECONSTRUCTION_ANCHOR` objects. Proposal generation is not evidence acquisition and does not bypass Stage 8 interpretation discipline. Promotion into the canonical graph is a deterministic gate.

For M5 promotion:

- validation must be non-mutating;
- every promoted semantic claim must have a positive proof path to a first-class evidence object;
- a Reconstruction Anchor must receive typed `supports_anchor` support from a behavior, artery, nerve, or capability object;
- promoted behavior contracts record at least trigger, observable response, and uncertainty;
- promoted anchors record a reconstruction property, observable fidelity test, and uncertainty;
- a MAPPED anchor may not depend on PARTIAL/BLOCKED/UNKNOWN proof objects and may not hide a visible contradiction;
- rejected proposals remain outside the canonical graph;
- successful semantic bundles commit atomically and refresh evidence/completeness/integrity/reconstruction projections.

`reconstruction_contract.json` is a derived projection. A future agent should use its canonical IDs with `why` and `impact` rather than treating the projection text as independent authority.

A reconstruction-aware sealed handoff must never modify its parent certification. The parent mechanical handoff is first independently verified; the semantic proposal is applied to a copied canonical store only after validation; the child handoff is resealed; and the child receipt records SHA-256 identities for the parent receipt and certification manifest.

Read-only canonical inspection must be byte-preserving. SCAN opens sealed SQLite stores in immutable read mode for ordinary queries/audits so evidence inspection does not create WAL/SHM sidecars or invalidate the handoff.

This contract establishes M5 mechanism readiness. It does not complete M6/PR7 until a genuinely source-blind reconstruction agent builds a surrogate and fidelity discrepancies are scored.

## v0.14 PR1 byte-boundary hardening

The first release-hardening slice protects the transition from visible specimen entries to parser-eligible bytes:

- a local scan root must be a real directory, not a symlink alias;
- local file/directory symlinks remain visible as `SYMLINK_REFERENCE` and are never followed for parser input;
- non-regular/special entries are explicit blocked anatomy;
- local reads use identity/size/timestamp checks and no-follow semantics where supported, then the extraction reread must match the inventoried SHA-256;
- manifest paths reject parent traversal and symlinked local components before parsing;
- `RESOURCE_LIMIT` is an explicit coverage state when a local/manifest file or provider blob exceeds the configured ceiling;
- the default per-item ceiling is 64 MiB and can be deliberately raised or disabled (`0`) by the operator;
- GitHub provider blobs declared above the ceiling are not requested.

These controls protect evidence provenance and resource use. They do not imply that an oversized or linked item is semantically unimportant; the item stays in the ledger and may be revisited under a changed explicit policy. v0.14 regression status is **72/72 PASS** in both development and clean-package runs.

## v0.13 semantic-action and build-contradiction refinement

SCAN must distinguish **semantic behavior identity** from **physical control instances** when a framework allows one action to be cloned into multiple menus, context menus, shortcut carriers, or platform-native surfaces. For keyed Qt action registries, the mechanical layer should preserve:

- a stable semantic action identity for the registry key;
- each physical/alternate route as a separate surface instance or family;
- payload-key dispatch cases when `QAction::data()` or equivalent discriminator selects behavior;
- bounded dynamic action families when indexed runtime slots are mechanically visible;
- explicit candidate gaps for registry actions whose dispatch is not recovered;
- duplicate discriminator branches as anomalies without assuming intent or runtime reachability.

Build logic must preserve contradictory evidence rather than silently reconcile it. A compile definition asserted inside a guard that mechanically states the opposite condition is recorded as a contradiction finding with both source facts. Static contradiction is not automatically promoted to a runtime failure; configured-build behavior remains a separate evidence question.

qView is a development oracle for these mechanisms, not the final PR6 holdout, because its source was manually inspected before this implementation refinement. A later production-grade transferability gate therefore requires at least one substantial unfamiliar C++/Qt holdout whose answers are not manually supplied before the candidate scan.

### Frozen PR6 holdout H-001

Project v0.20 reserves **DB Browser for SQLite** (`sqlitebrowser/sqlitebrowser`) as PR6 holdout H-001. The holdout is pinned at commit `4a7359d5c349ca0bc446f94922ec9561fcf50b96`, tree `1ad501f60616ebd644a7e86a92fb9d22666b3e2c`. At freeze time only repository/commit/tree metadata were inspected; source files and expected behavior denominators were deliberately not manually analyzed.

Until the v1 candidate scanner is frozen for certification, do not manually inspect H-001 source to create expected-answer hints. Permitted pre-scan handling is limited to identity/provenance verification and acquisition mechanics. The candidate scan itself may of course read the pinned specimen mechanically. Human/LLM comparison begins only after the cold scan artifacts are sealed.

If H-001 becomes unusable for reasons unrelated to scanner quality, record the reason and freeze a replacement before source analysis. Do not quietly substitute an already-studied specimen.

## Implementation architecture contract

SCAN is implemented as a **reusable scanning product**, not as a sequence of disposable repository-reading scripts. The architectural split is:

```text
STAGE 1 — DISCOVERY / CENSUS / EXTRACTION
mostly deterministic code, little or no LLM

STAGE 2 — STRUCTURAL SYNTHESIS
code + graph algorithms + conservative heuristics
LLM only where ambiguity materially benefits from interpretation

STAGE 3 — SEMANTIC INTERPRETATION
LLM reasons over compressed evidence, graph neighborhoods, anomalies, and unresolved seams

STAGE 4 — DEEPENING
targeted additional scans driven by unresolved questions

STAGE 5 — EXPERIMENTAL VALIDATION
separately authorized isolated tests/harnesses when static evidence cannot resolve behavior
```

These implementation-stage names are responsibilities, not replacements for the D0-D5 scan-depth ladder later in this protocol.

The scanner's conceptual model is language-agnostic, but extraction is language- and framework-aware:

**COMMON ANATOMICAL SCHEMA + SUBSTRATE-SPECIFIC ADAPTERS -> QUERYABLE MACHINE BODY MAP**

A C++ callback, Python decorator, Rust trait registration, Java/Kotlin Android intent, JavaScript event emitter, plugin manifest, or Qt signal may represent comparable anatomical concepts while requiring different extraction machinery. Preserve that distinction.

Every repeatable scan operation should become reusable SCAN machinery: inventory modules, parsers/adapters, indexes, graph operations, caches, boundary detectors, extension detectors, or CLI queries. If a specimen exposes a weakness, improve the scanner instead of repeatedly compensating with one-off manual passes.

The reusable implementation lives under `scan_engine/`. The current v0.20 baseline provides recursive local inventory, SHA-256 content hashing, stable evidence IDs, a normalized SQLite index, JSON Machine Body Map export, content-hash extraction caching, Qt `.ui` extraction, C++/Qt structural extraction, CMake extraction, generic boundary candidates, graph metrics, mechanical query commands, provider-manifest/hybrid acquisition, and a reusable read-only GitHub acquisition driver. The GitHub driver resolves an exact ref to immutable commit/tree identities, walks the complete provider tree with a non-truncated fallback, fetches Git blobs into scanner-owned storage, verifies canonical Git blob SHA-1 before materialization, records SCAN SHA-256 separately, and preserves blocked/external/symlink states instead of pretending they were parsed. The evidence layer retains first-class source-digest-aware evidence, typed semantic overlays, integrity auditing, proof-path validation, stable-ID repeatability tests, multidimensional completeness, and projection hash manifests. M3A surface extraction covers Qt Designer connections/shortcuts, generic interactive widgets, dynamic QAction/QShortcut identity, CLI controls/consumers, event overrides, uniqueness-gated cross-file resolution, and denominator closure. M3B adds compiler-assisted Clang AST evidence, brace-aware fallback function/call regions, sender-scoped Qt signal identity, project-local call resolution, explicit state/effect/feedback objects, compile-context-sensitive caching, type/inheritance/override/overload/template/virtual-dispatch evidence, generated-Qt/conditional contracts, and Scintilla/Lexilla capability coupling. The v0.9 M3C layer adds mechanically visible guards/loops/early exits/exception paths, typed permission/environment/cancel/error/lock semantics, first-class persistence operations and conservative state-to-persistence candidates, typed plugin/script/dynamic-library receptors and potential capability factories, dedicated capability-provenance completeness dimensions, and `nest_capability_map.json`. The v0.10 transferability refinement additionally recognizes common programmatic Qt interactive-widget instances as human surfaces, attributes fallback call/effect/feedback evidence inside common connect-lambda bodies to the lambda handler, and removes explicit `setReadOnly(true)` widgets from the actionable input denominator while retaining them as presented surfaces. The v0.11 refinement adds qmake build-topology extraction, Qt `.qrc` resource anatomy, legacy `SIGNAL()/SLOT()` binding, `QTimer::singleShot(..., SLOT(...))` delayed dispatch, multimedia playback capability/feedback evidence, conservative repaint feedback, and removes the false extension inference previously attached to ordinary `addMenu()`/`addAction()` calls. The v0.12 refinement adds direct class-member type extraction for conservative fallback resolution, uniqueness-gated cross-file receiver typing, main-translation-unit provenance filtering for compiler-emitted declarations, and assignment-target state extraction that excludes RHS/local-object member reads from specimen state. The v0.13 refinement adds semantic QAction identity separate from physical clone routes, payload-key dispatch cases, bounded dynamic QAction families, dispatch-gap and duplicate-dispatch findings, and direct CMake self-contradiction findings. The v0.14 hardening layer rejects symlink roots, records internal symlinks/special files without following them, verifies local file identity/digest across census-to-parse rereads, rejects manifest traversal/symlink materialization, and applies explicit configurable per-file/provider-blob resource ceilings. v0.15 adds explicit Qt concurrent-task/watcher/continuation closure. v0.16 adds aggregate scan budgets/cancellation, SQLite corruption/schema policy, deterministic package/projection self-audit, and the LLM-disabled 12-query release qualification. v0.17 adds parser/adaptor fault isolation, resume-after-budget regression coverage, wheel deployment validation, and measured larger-fixture cache behavior. v0.18 adds sealed LLM-disabled specimen certification, transfer manifests, independent certification verification, and an agent-integration trust contract that separates evidence integrity from coverage completeness. v0.19 adds evidence-gated reconstruction proposal validation/promotion, reconstruction-contract projection, immutable read-only SQLite inspection, and lineage-preserving reconstruction-aware child certification. v0.20 adds source-free public/private reconstruction-trial splitting, challenge-bound source-isolation declarations, static candidate rescanning, source-free scoring requirements, failure attribution, sealed trial receipts, and deterministic challenge packaging. It remains below a production-grade claim until the open specimen/reconstruction/holdout gates pass.


## Canonical evidence graph and projection contract

SCAN must converge on **one evidence-backed structural graph expressed through multiple projections**, not a loose collection of JSON reports that merely appear correlated.

The current canonical store is `scan_index.sqlite`. Friendly artifacts such as the Machine Body Map, Artery Map, Nerve Map, Control Surface Map, NEST Capability Map, Evidence Catalog, Completeness Vector, and Reconstruction Anchor Map are projections of the same identities and relations. They must not become independent authorities.

Canonical object classes may include:

- specimen
- file/source artifact
- evidence
- symbol/anatomical object
- graph-relation claim
- finding/anomaly
- behavior
- lifecycle state/transition
- artery
- nerve
- control surface
- capability/NEST boundary
- interpretation
- reconstruction anchor

Each object must have a stable globally unique ID within the specimen/revision knowledge graph. Extraction-generated IDs should be deterministic where practical. Higher-stage semantic objects may use explicit stable IDs such as `BEH-*`, `ART-*`, `NERVE-*`, `CAP-*`, `IN-*`, and `RA-*`. Human-friendly prefixes are conventions; referential integrity is mandatory.

Evidence is itself an object. A certification-grade evidence record should preserve, when available:

- evidence ID;
- evidence class;
- source file/object ID;
- repository path;
- exact line/range or structural locator;
- extractor/adapter and version;
- source digest/revision;
- optional bounded excerpt;
- claims/relations it supports or contradicts.

Typed relationships should make semantic dependencies explicit. Core vocabulary includes `supports`, `derived_from`, `contradicts`, `enters`, `observed_by`, `requires`, and `supports_anchor`, in addition to substrate-specific structural relations such as `calls`, `contains`, or `dispatches_to`. The relation vocabulary may grow when a new specimen demands it.

The preferred proof direction is:

```text
SOURCE ARTIFACT
    -> EVIDENCE
        -> EXTRACTED OBJECT / GRAPH RELATION
            -> BEHAVIOR / CAPABILITY / ARTERY / INTERPRETATION
                -> RECONSTRUCTION ANCHOR
```

This is a DAG, not necessarily a single chain. Multiple independent evidence objects may support one claim, one evidence object may support many claims, and contradiction edges must remain visible.

The scanner must support the two inverse provenance questions:

```text
scan-body why <database> <semantic-object-id>
scan-body impact <database> <source-or-evidence-id>
```

`why` walks backward to the evidence and source artifacts that justify a semantic object. `impact` walks forward to the claims, interpretations, capabilities, behaviors, and reconstruction anchors that depend on evidence.

Semantic interpretation may be ingested as a **data-only overlay** that references existing canonical object IDs. Import must reject dangling references. An interpretation or reconstruction anchor never becomes `DIRECT` merely because it was imported into the graph.

### Refinement Gate R1: evidence and closure integrity

Before semantic sophistication grows further, SCAN must be able to audit the knowledge structure it already created. The current refinement gate requires reusable mechanical checks rather than prose review.

The scanner should expose at least:

```text
scan-body audit <database> [--strict]
scan-body closure <database>
```

The integrity audit should detect, when mechanically applicable:

- dangling semantic relation endpoints;
- missing or non-evidence objects referenced as evidence;
- evidence with no valid source artifact;
- evidence whose pinned source digest disagrees with the current source-file object;
- orphan evidence that supports no extracted or semantic claim;
- important semantic claims with no positive path to first-class evidence;
- reconstruction anchors with no evidence path;
- invalid completeness-parent/evidence references;
- cycles in positive proof relations.

The audit must not silently repair these states. A reconstruction anchor with no positive evidence path is an integrity error, not merely low confidence.

Human-surface closure is a separate measurement. A discovered control is `BOUND` only when a handler is mechanically reachable; it is `PARTIAL` when a route exists but closure is incomplete; it is `UNRESOLVED` when no actionable route is established. Framework-native behavior may remain unresolved until an adapter proves it. This state describes scanner knowledge rather than application quality.

Projection coherence is also part of R1. Friendly maps are generated from the canonical store and should be accompanied by a manifest of byte counts and SHA-256 hashes. Any operation that changes the semantic graph must refresh affected projections and their manifest so stale views cannot masquerade as current scan truth.

`why` should report whether it actually reached evidence and source files. `impact` should report important downstream dependents such as reconstruction anchors. Stable IDs should be repeatable across clean scans of unchanged facts.

### M3A breadth gate: denominator-driven human-surface closure

After R1 establishes evidence/projection integrity, the first extraction-breadth gate expands what counts as a mechanically discoverable human entrance. The scanner should not start from handlers it already knows. It should census surface declarations/factories first and then attempt closure.

The v0.6 baseline adds reusable support for:

- common interactive Qt Designer widgets in addition to QAction;
- Designer-authored `<connections>` as executable signal/handler wiring;
- QAction shortcuts declared in `.ui` and QShortcut objects created in C++;
- generic `ui->objectName` references and unique cross-file object-name resolution;
- dynamic QAction variables whose creation identity is preserved through later `connect(...)` wiring;
- QCommandLineParser option/positional surfaces and literal consumers;
- drag/drop, keyboard, pointer, context-menu, close, focus, and file-open event entrances;
- explicit resolution-gap findings when an object/handler name is ambiguous;
- stable-ID duplicate merging so declarations and references accumulate evidence instead of overwriting one another;
- bounded route traversal through aliases/resolution edges, signals, commands, and handlers;
- denominator summaries and nested completeness dimensions by discovered surface type.

Cross-file matching must be uniqueness-gated. A name collision is evidence of ambiguity, not permission to choose the most convenient target. Framework-native behavior that is not yet mechanically closed remains `PARTIAL` or `UNRESOLVED`.

M3A is a breadth mechanism, not certification. The next M3 work must deepen C/C++ symbol/call/state/effect analysis and framework-native Scintilla/Lexilla behavior before whole-application reconstruction claims are appropriate.

### M3B deep structural/effect closure baseline

M3B distinguishes **binding closure** from **semantic/effect closure**. Discovering the first handler is not enough to claim that SCAN understands what a human action ultimately does. Where supported, the scanner should continue mechanically through project-local calls until it reaches one or more consequence or feedback terminals.

The v0.7 baseline provides:

- optional compiler-assisted C/C++ AST extraction through a fixed local Clang executable;
- `compile_commands.json` consumption strictly as data, with a narrow parser-context whitelist rather than replaying specimen compiler commands;
- explicit parser-gap evidence when compiler context is absent or incomplete, while conservative fallback extraction continues;
- brace-aware fallback function regions and call references with comments/literals masked before structural matching;
- project-local call resolution only when qualified/context identity or global uniqueness supports it;
- sender-scoped Qt signal-event identity so controls sharing the same signal type do not inherit each other's handlers;
- direct/member state-change evidence where mechanically supportable;
- effect objects for supported filesystem/process/network/settings/desktop operations and explicit PARTIAL candidates for weaker receiver-only matches;
- feedback objects for supported dialogs/status/title/tooltip paths;
- function-context links to NEST boundaries, extension receptors, presented dialogs, CLI consumers, state changes, effects, and feedback;
- `effect_closure.json` and `scan-body deep-closure` for bounded surface -> handler -> call -> consequence traversal;
- a `cpp-compiler-ast` completeness dimension that keeps compiler-context gaps visible.

The deep-closure state is interpreted conservatively:

- `CLOSED`: a bound human entrance reaches at least one mechanically supported state/effect/NEST/extension/presented-surface/feedback terminal;
- `PARTIAL`: a binding/structural route exists but no supported terminal has yet been established;
- `UNRESOLVED`: the actionable binding itself remains unresolved.

Presented/output surfaces are terminals, not additional entry-binding denominator items unless a deeper adapter separately models their internal controls. Event objects that represent Qt signal emissions must preserve sender identity; one generic signal-type node must not create false cross-wiring among unrelated controls.

Compiler assistance does not yet satisfy the full production C++ depth gate. Translation units may remain compiler-AST `PARTIAL`/`BLOCKED` when headers, generated files, defines, or build context are unavailable. v0.8 improves overload/type/virtual/template/conditional/generated-Qt and Scintilla/Lexilla evidence, but whole-program dispatch, macro-expanded branch semantics, generated artifact bytes, deep CFG/data flow, and complete framework-native human behavior remain incomplete.

### M3B-2 compiler/type/framework closure baseline

v0.8 adds a stronger deterministic bridge between compiler structure and effective application behavior:

- compile databases are discovered through a bounded repository/build-tree search rather than assumed to exist at repository root;
- the compiler adapter cache key includes a digest of whitelisted parse context so changed defines/include paths cannot reuse stale AST evidence;
- C++ types, inheritance, polymorphism, method signatures, override relationships, overload identity, template origins, and virtual-dispatch candidates are first-class evidence when Clang can prove them;
- compiler-typed Qt API calls may emit MAPPED effect/feedback/NEST objects for supported filesystem, settings, clipboard, process, network, IPC, printing, and UI-feedback families;
- fallback preprocessing records macro definitions and conditional directives without claiming branch truth;
- Qt meta-object/plugin/interface macros and CMake AUTOMOC/AUTOUIC/AUTORCC plus `.ui`/`.qrc` inputs become generated-code contracts without executing specimen generators;
- Scintilla `SCI_*` commands, `SCN_*` notifications, and Lexilla lexer receptors become framework capability/event objects with BODY/NEST provenance rather than fake human surfaces;
- cross-file C++ type references resolve only when project identity is unique.

The compiler/type layer must preserve uncertainty. A `virtual_dispatch_candidate` is not a proven runtime target. A generated-code receptor is not proof that generated bytes were scanned. A Scintilla capability is not automatically a human-facing control. Those distinctions remain visible in coverage and relation types.


### M3C NEST/persistence/extension/error closure baseline

v0.9 deepens the effective-capability boundary around the structural routes already established by M3B. It keeps environmental possibility, BODY coupling, authorization, current use, and observed runtime success as separate evidence states.

The v0.9 baseline provides:

- a dedicated C/C++ control-flow adapter for mechanically visible `if`/`switch` guards, loops, early exits, try/catch/throw anatomy, and explicit retry/backoff candidates;
- compiler-typed permission, environment, cancellation, error/status, lock, subprocess, network, IPC, settings, and related NEST effects where supported signatures are available;
- first-class `persistence_operation` objects for supported settings/save/lock operations;
- conservative `persistence_candidate` relations when a state mutation precedes a typed persistence operation in the same function, explicitly `PARTIAL` until value-level data flow is proven;
- compiler-typed plugin, dynamic-library, JavaScript, and Lua extension receptors;
- `capability_factory` objects with `POTENTIAL` provenance when runtime-loaded/evaluated material may create capabilities that cannot be statically enumerated;
- narrow source-level extension receptors when compiler context is unavailable, without upgrading them to typed proof;
- explicit completeness dimensions for capability provenance, persistence paths, guard/error/cancel paths, permission guards, and extension receptors;
- a dedicated `nest_capability_map.json` projection grouping capability families, effects, NEST boundaries, extension receptors, potential factories, persistence objects, and control/error anatomy;
- mechanical `persistence`, `guards`, `permissions`, and `capabilities` queries.

M3C preserves several conservative invariants. A persistence-capable provider is not proof that a particular state is durable. A retry-looking loop is not a proven retry policy. A plugin/script receptor is not proof that a particular extension is installed. A typed BODY-to-NEST call establishes coupling evidence, not runtime authorization or successful execution.

The Machine Body Map schema for this baseline is `scan-machine-body-map/0.9`.

### Calibration-driven transferability refinement

Once the mechanism-family baseline exists, a real external specimen may expose a gap that synthetic fixtures did not reveal. Such a miss should be treated as a reusable scanner calibration problem rather than patched with specimen names.

The first transferability micro-calibration, TR-001, uses an exact Git blob from an unrelated Qt Widgets teaching repository. A cold v0.9 scan discovered zero human surfaces because the program constructs its widgets directly in C++ rather than through a `.ui` form. v0.10 therefore adds generic programmatic interactive-widget census, sender-identity reuse, lambda-local consequence attribution, and read-only output-surface classification.

A transferability calibration is accepted only when:

- specimen bytes are independently pinned and verified;
- the cold scanner result is preserved;
- the miss can be stated without knowing the desired answer in advance;
- the fix is reusable and not keyed to specimen-specific names;
- regression tests encode the general class of failure;
- rerunning the external specimen demonstrates the intended improvement;
- remaining gaps stay explicit.

A small external specimen can prove the calibration loop works, but it does not by itself satisfy the full PR6 transferability gate. A larger unrelated C++/Qt application remains required.

The second transferability calibration, **TR-002**, expands the test to the pinned `tashaxing/QtWuziqi` repository at commit `f4a8700699fce1b4d4a9d07e4618045c57ad3666`, tree `56bb172f66e8b22e071bf45bfa4e7d14815bd4bd`. The provider tree contains 12 blobs and is not truncated. Seven exact text blobs are materialized and provider-digest verified in the local scanner runtime; five provider-visible blobs remain `METADATA_ONLY`, including `GameModel.cpp` and four media assets, because the connector-to-local byte seam still cannot bulk-materialize them. The missing files remain in the denominator and are not parser-fed.

The cold v0.10 scan of that exact hybrid manifest exposed generic misses rather than specimen-specific defects: legacy Qt `SIGNAL()/SLOT()` wiring left both QAction controls unresolved; qmake and `.qrc` anatomy were not represented; delayed `QTimer::singleShot(..., SLOT(...))` dispatch was absent; multimedia playback/repaint feedback was shallow; and ordinary menu/action construction created false extension-receptor candidates. v0.11 repairs those classes generically. On the same verified materialized subset, surface binding improves from `2 BOUND / 2 UNRESOLVED` to `4 BOUND / 0 UNRESOLVED`, and deep effect closure improves from `0 CLOSED / 2 PARTIAL / 2 UNRESOLVED` to `4 CLOSED / 0 PARTIAL / 0 UNRESOLVED` for the currently visible surface denominator. qmake dependencies/inputs, three Qt resource assets, one single-shot delayed route, and multimedia playback effects also become first-class evidence.

TR-002 remains a **partial PR6 result** in its original v0.11 state because five blobs were acquisition gaps and the unavailable `GameModel.cpp` contained important gameplay/AI state behavior. A successful closure ratio over the materialized surface denominator must never be generalized into whole-organism completeness while those gaps remain.

### Transferability provenance/state refinement TR-002B

A later provider-blob read made the exact `GameModel.cpp` bytes available and Git-object verification succeeded before parsing. This raised the materialized denominator to eight text files while four binary media blobs remained metadata-only. The new body region exposed three generic scanner defects: compiler/system-header declarations were being emitted as if they belonged to the main source file, fallback calls such as `game->actionByPerson()` could not use the direct member declaration `GameModel *game` to recover a unique cross-file receiver type, and assignment-state extraction could confuse RHS reads such as `pointPair.first` with specimen state writes.

v0.12 therefore applies three conservative rules:

- compiler AST data may be used internally for resolution, but declarations emitted as source-owned BODY anatomy must originate in the main translation unit rather than an included/system header;
- a fallback receiver may inherit a static type from a directly declared class member only when owner/member/type/target resolution is unique; ambiguity is a gap, not a guess;
- compiler state mutation is extracted from the assignment target only, and the target member chain must be rooted in `this`. Reads or writes on unrelated local objects are not silently promoted to specimen state.

On the same exact verified bytes, the scanner drops from the polluted 5,389-node cold v0.11 graph to a 443-node v0.12 graph while gaining deeper MainWindow-to-GameModel state closure. False `first`/`second` mutations disappear. This is treated as a provenance correction, not as loss of specimen evidence. Four binary blobs and incomplete Qt compiler context remain explicit gaps.

### Completeness vector contract

SCAN does not use one global completion percentage as an authority. Coverage is represented as named dimensions and, where useful, nested subdimensions. Example dimensions include acquisition, file census, parser coverage, symbol graph, call graph, event graph, human surfaces, dynamic/framework-native surfaces, lifecycle, persistence, NEST coupling, extension receptors, hidden-function analysis, authority closure, and reconstruction-anchor traceability.

Each dimension uses explicit coverage states. A shallow scan can therefore be complete in identity and acquisition while still `UNKNOWN` in native-framework behavior or hidden-function semantics. This directly guides where the next unit of scan time should be spent.

---

# INPUTS

Required:

- repository URL or local read-only repository
- exact revision when available

Optional:

- operator-provided scope
- existing scanner executable or source
- language-specific parsers
- prior scan for comparison
- operator time/depth budget
- NEST/environment description or inventory
- explicit authorization for deeper experimental modes when desired

For the current reference run:

- Repository: `https://github.com/dail8859/NotepadNext`
- Pinned commit: `f57db52d6760a2ce4149a37190c3adaa586845f5`

Never silently switch revisions during a scan.

---

# NON-DESTRUCTIVE BOUNDARY

Ordinary SCAN mode:

- MAY clone or copy the repository into scanner-owned storage.
- MAY read files.
- MAY hash files.
- MAY parse source.
- MAY inspect Git metadata.
- MAY create derived scan artifacts outside the specimen.
- MAY run scanner-owned parsers and analysis code against specimen bytes.
- MUST NOT edit specimen files.
- MUST NOT commit or push.
- MUST NOT insert hooks.
- MUST NOT execute the specimen's application code, build scripts, tests, installers, plugins, macros, or project-supplied binaries.
- MUST NOT interpret a build command as permission to run it.
- MUST NOT write generated artifacts into the specimen tree unless the operator explicitly authorizes a separate mode.

If a tool would cross this boundary, stop that operation and record the limitation.

### Separately authorized deep experimental mode

A user may explicitly authorize deeper experiments after or alongside static analysis. In that mode SCAN may, in scanner-owned isolated storage:

- build or execute a controlled copy of the specimen,
- construct minimal harnesses or mocks,
- recreate a small code fragment to test a semantic hypothesis,
- compile or run reconstructed fragments,
- provide controlled stimuli and measure responses,
- or compare predicted behavior with observed runtime behavior.

The canonical pinned specimen remains immutable. Every experiment must record exactly what was original, copied, reconstructed, generated, mocked, executed, or inferred. Reconstructed behavior is evidence about a hypothesis; it is not silently promoted to DIRECT evidence about the original program.

Authorization is mode-specific. A larger time budget does not itself authorize execution or modification.

---

# CORE OPERATING RULE

Use this order:

**FREEZE -> ACQUIRE -> VERIFY -> CENSUS -> PARSE -> GRAPH -> TRACE -> LIFECYCLE -> HUMAN SURFACES -> NEST -> CIRCULATION -> NERVES -> ANOMALIES -> DEEPEN -> INTERPRET -> REPORT -> DERIVE**

Do not jump to biological interpretation before building structural evidence.

---

# STAGE 0: FREEZE THE SPECIMEN

Record:

- repository identity
- requested branch/tag if relevant
- exact commit SHA
- tree SHA when available
- scan timestamp
- scanner version
- content fingerprint
- whether Git submodules are present
- whether large-file pointers, missing blobs, or external generated assets create visibility gaps


The report must make clear exactly what was scanned.

---

# STAGE 0A: ACQUIRE AND VERIFY THE VISIBLE BODY

Acquisition is a first-class scan stage. Do not assume that repository visibility and content-byte availability are the same thing.

The acquisition layer should, where practical, create a machine-readable source ledger containing:

- provider/repository identity,
- pinned revision and provider tree identity,
- every visible in-scope path,
- provider object ID or digest when available,
- declared size/type/mode when available,
- whether exact bytes have been materialized into scanner-owned storage,
- scanner-computed content digest when bytes are available,
- acquisition provider/method,
- and an explicit acquisition state.

Recommended acquisition states include:

- `LOCAL_BYTES` or equivalent: verified bytes are directly available;
- `MANIFEST_MATERIALIZED`: provider-ledger entry has matching locally materialized bytes;
- `METADATA_ONLY`: the provider establishes that the object exists but its bytes are not available to the scanner runtime;
- `BLOCKED`: acquisition was attempted but an external limitation prevented obtaining required bytes.

Provider object digests and scanner content digests are not interchangeable. For example, a Git object SHA-1 identifies a provider object, while SCAN's SHA-256 is computed from bytes actually presented to the scanner. Preserve both when available.

A metadata-only object is part of the visible-body ledger but is **not parser-eligible**. Do not feed fabricated, estimated, or manually summarized content to source adapters merely to make the coverage table look complete. Its content coverage remains PARTIAL or BLOCKED until exact bytes are acquired.

Remote/provider acquisition should itself become reusable scanner machinery. If a connector can enumerate repository metadata but cannot hand bytes to the scanner runtime, record the transport seam as an acquisition-layer limitation rather than compensating with one-off LLM copy/paste of individual files.

The current GitHub adapter provides this reusable path:

```text
scan-body acquire-github OWNER/REPO --ref EXACT_REF --out SCANNER_OWNED_DIR [--strict]
scan-body scan-manifest SCANNER_OWNED_DIR/source_manifest.json --content-root SCANNER_OWNED_DIR/content --out SCAN_DIR
```

A failed provider transport must terminate the acquisition command with a non-zero status and a concise machine-readable `BLOCKED` record. It must not emit a parser result or quietly fall back to a moving branch. A successful provider blob transfer must pass provider-digest verification before source adapters are eligible to consume it. For Git, retain the provider Git object SHA separately from SCAN's byte SHA-256.

Provider blobs, external references, and full visible-body materialization are different completion concepts. A repository may have all directly fetchable provider blobs verified while still containing gitlinks/submodules, symlink references, LFS pointers, generated assets, or other external anatomy requiring separate accounting. Do not collapse these states into one boolean named "complete."

The full Stage 1 content gate is eligible to pass only when every in-scope object is either materialized and verified for supported parsing or explicitly accounted for as an acquisition/parser gap.

---

# STAGE 1: WHOLE-BODY CENSUS AND MECHANICAL EXTRACTION

Stage 1 must be predominantly mechanical. A large repository should mostly mean more files, nodes, edges, registrations, surfaces, and seams for the scanning engine to index. It must not mean asking an LLM to contemplate every file or function individually.

Walk the complete visible tree and feed supported artifacts through reusable scanner adapters.

For every file, record at minimum:

- relative path
- byte size or provider-declared size when available
- provider object identity/digest when available
- content hash computed from verified bytes when available
- content-availability and acquisition state
- extension / detected type
- likely language or artifact class
- first-party / vendored / generated / documentation / resource / build / unknown status
- planned parser
- coverage state
- limitations

Detect, when possible:

- programming languages
- build systems
- package/dependency manifests
- entry-point candidates
- GUI description files
- resources
- scripts
- tests
- generated sources
- vendored dependencies
- binary artifacts
- configuration
- translations
- database/schema files
- protocol/schema definitions

Do not infer language solely from repository description or filename when content evidence can improve detection.

No relevant file disappears simply because the scanner cannot parse it.

Stage 1 implementation requirements:

- use stable file and evidence IDs;
- hash content so unchanged extraction can be reused;
- maintain a normalized queryable evidence graph/database rather than only prose output;
- record scanner and adapter versions;
- cache extraction by content hash plus adapter version where practical;
- support resumable scans;
- preserve parser failures and unsupported substrates as explicit coverage records;
- separate fine-grained evidence from higher-order summaries and projections;
- avoid name-pattern heuristics as the sole basis for anatomy when structural evidence is available;
- allow language/framework-specific adapters to emit a common normalized schema;
- keep the scan specimen read-only;
- never count provider metadata as successful source parsing when exact bytes were not materialized;
- expose acquisition gaps through machine queries independently from parser/semantic gaps;
- make evidence objects and claim dependencies mechanically traversable;
- export a multidimensional completeness vector;
- keep all projection files tied to the same canonical cross-object IDs.

Stage 1 should mechanically discover candidates for human surfaces, commands/actions, handlers, interfaces, state, persistence, event pathways, extension receptors, plugin/add-on factories, framework behavior, environmental inputs/outputs, unusual pathways, feedback seams, and capability boundaries. It need not semantically explain them yet.

The Stage 1 engine should be able to answer purely mechanical questions without invoking an LLM, including examples such as: surfaces with no discovered binding, subprocess boundaries, extension-receptor candidates, dynamic registrations, NEST boundary candidates, partial/unknown paths, and files or regions lacking parser coverage.

---

# STAGE 2: STRUCTURAL PARSING

Use the strongest deterministic parser practical for each supported substrate. The common body-map model is language-agnostic; the scanners are not language-blind.

Preferred order:

1. compiler-grade or established syntax parser / AST
2. tree-sitter or equivalent structural parser
3. language-aware token parser
4. conservative fallback recognizer
5. explicit BLOCKED coverage

Extract where supported:

- namespaces/modules/packages
- classes/structs/types
- functions/methods
- declarations and definitions
- parameters and return types
- globals/constants
- imports/includes
- inheritance/composition
- function calls
- callbacks
- event registration
- signals/slots
- helper-mediated event wiring and wrapper dispatch
- dispatch tables
- command registrations
- routes/endpoints
- file/network/process/storage APIs
- state mutation sites
- error/validation boundaries
- resource references
- build target relationships

Preserve exact source locations and extraction provenance. Normalize comparable concepts into the common Machine Body Map while retaining substrate-specific attributes needed for later drill-down.

Do not remove a symbol merely because its purpose is unknown.

---

# STAGE 3: BUILD MACHINE GRAPHS

Build explicit graph structures from deterministic evidence.

At minimum attempt:

1. FILE / MODULE DEPENDENCY GRAPH
2. SYMBOL GRAPH
3. CALL GRAPH
4. EVENT / SIGNAL / CALLBACK GRAPH
5. BUILD / RESOURCE GRAPH
6. LOOP INVENTORY

Where supported, add:

- state-flow graph
- data-flow graph
- persistence graph
- IPC/message graph
- network graph
- UI surface -> handler graph
- configuration influence graph

Edges must carry evidence and source locations where practical. Store graph structures in a form that supports machine queries, incremental refinement, centrality/SCC analysis, neighborhood extraction, and targeted deepening without an LLM rereading the repository.

Do not stop at framework syntax such as direct `connect(...)` calls. Follow project-defined helper functions, templates, wrappers, factories, registration utilities, and dispatch abstractions when they carry events or control from one surface to another. A helper-mediated edge is still part of the organism's circuitry.

Distinguish an exact resolved edge from a candidate or ambiguous edge.

---

# STAGE 4: LOOP AND RECURRENCE ANALYSIS

Locate every loop visible to supported parsers.

Do not treat every loop as a major artery.

Record:

- loop location
- enclosing symbol
- syntax / recurrence mechanism
- direct calls or events inside it
- candidate termination condition
- known inputs and outputs
- whether it is local computation or participates in a recurring system pathway

Also detect recurrence that is not written as `for` or `while`, such as:

- framework event loops
- schedulers
- recurring timers
- single-shot/debounce timers that repeatedly re-arm from events
- callback cycles
- recursive dispatch
- queue consumers
- retry loops
- message pumps
- polling
- observer cycles

Use graph algorithms where useful to find strongly connected components and recurrent pathways.

---

# STAGE 4A: LIFECYCLE RECONSTRUCTION AND STATIC BEHAVIOR SIMULATION

Reconstruct how the software can move through meaningful states over its lifetime without executing the specimen.

The scanner should identify lifecycle states, transitions, triggers, guards, side effects, persistence effects, cancellation paths, and error branches from deterministic evidence. Examples include process birth, initialization, ready/idle state, document creation, open, edit, save, session checkpoint, close, shutdown, and restart/restore.

Where practical, construct a machine-readable state-transition model. Each transition should preserve:

- source state,
- trigger or stimulus,
- guard/precondition,
- structural path through the code,
- resulting state,
- externally observable effect,
- durable state effect,
- relevant artery candidates,
- evidence class,
- and unresolved dynamic behavior.

Perform **static behavior simulation** by traversing the reconstructed call/event/state graphs with explicit scenarios. This is not execution of the host application. It is deterministic path reasoning over extracted structure.

For a desktop GUI application, baseline scenarios should be attempted when applicable:

- cold start with no user files,
- cold start with file arguments,
- startup with prior session restoration,
- secondary-instance launch while a primary instance exists,
- create a new document,
- edit a document,
- save and save-as,
- reload,
- recurring autosave/checkpoint behavior,
- close with clean buffers,
- close with unsaved buffers,
- cancellation of shutdown,
- normal shutdown,
- restart and restoration,
- operating-system file-open events,
- and workspace/folder-driven file opening.

Do not invent outcomes when dynamic dispatch, framework behavior, unresolved calls, or external dependencies prevent static proof. Mark those transition segments UNKNOWN or PARTIAL.

A statically reconstructed path is evidence of an implemented pathway, not proof that every runtime environment will exercise it successfully.

---

# STAGE 4B: HUMAN INTERACTION SURFACE MAPPING

Construct a complete evidence-backed map of the interfaces through which a human can perceive or influence the application.

The scanner must attempt to enumerate every applicable human-facing surface, including static and dynamically created UI, menus, menu items, toolbars, buttons, tabs, editor regions, dialogs, context menus, keyboard shortcuts, mouse/touch gestures, drag-and-drop targets, file associations, command-line inputs, operating-system events, accessibility routes, and other user-accessible controls.

For every discovered action or affordance, construct a semantic pathway of the form:

**HUMAN SURFACE -> AFFORDANCE -> USER ACTION -> EVENT/COMMAND -> DISPATCH/HANDLER -> INTERNAL PATHWAY -> STATE CHANGE OR EFFECT -> USER FEEDBACK**

Preserve, where determinable:

- stable surface/action identity,
- visible label, icon, shortcut, gesture, or external invocation,
- parent surface and navigation route,
- visibility, enablement, checked/selected, modal, and platform guards,
- event/signal/command emitted,
- helper-mediated or indirect dispatch,
- handler and downstream calls,
- state mutation and external side effects,
- success, cancellation, and error outcomes,
- user-visible feedback,
- alternate routes that converge on the same semantic behavior,
- sensory/afferent nerve candidates,
- motor/efferent nerve candidates,
- and coverage/evidence state.

Do not equate labels with behaviors. The text `Save` is evidence about an affordance, but the behavioral identity must be established by its connected path. Conversely, an important behavior must not disappear because its control lacks a convenient label or is constructed dynamically.

Group alternate human routes when they converge on the same semantic behavior. For example, a File-menu Save item, a keyboard shortcut, and a toolbar icon may be separate surface entrances into one SAVE CURRENT DOCUMENT behavior. Preserve the individual entrances as well as the shared behavior identity.

The scanner must follow project-defined helpers, templates, wrappers, action factories, signal mappers, command registries, reflection, generated UI wiring, and framework conventions when they mediate a human action. A direct `connect(...)` parser is not sufficient if the application uses higher-level dispatch abstractions.

Candidate nerves should distinguish direction:

- **afferent/sensory**: observe action, state, result, or feedback,
- **efferent/motor**: a future separately authorized agent could cause the same semantic action available to a human.

Ordinary SCAN records candidate motor points but never invokes them.

A surface coverage ledger must make missing human-interface coverage explicit. A completed scan must not claim complete user-behavior coverage while interface regions, dynamic action factories, shortcuts, or dispatch helpers remain UNKNOWN.

---

# STAGE 4C: NEST / ECOSYSTEM AND CAPABILITY-COUPLING MAP

Map the relevant environment outside the specimen that materially changes what the software can perceive, invoke, persist, communicate with, or cause.

The NEST may include, where applicable:

- operating-system services and event facilities,
- language/runtime/framework services,
- host applications or automation substrates,
- filesystems and storage grants,
- installed commands or tools,
- device APIs and hardware,
- network interfaces,
- cloud or repository services,
- environment variables and configuration,
- permissions, entitlements, sandbox rules, and credentials boundaries,
- plugin/add-on/extension mechanisms,
- IPC, sockets, message buses, or shell facilities,
- and other external providers consumed by the specimen.

Do not scan an entire environment indiscriminately when only a bounded region is relevant. Start from specimen boundary calls and declared dependencies, then expand outward according to evidence and the operator's depth budget.

For each material body-to-NEST coupling, record where possible:

- NEST component/provider,
- body symbol or surface that reaches it,
- interface/protocol/API/command used,
- direction: input, output, or bidirectional,
- capability supplied,
- permission/configuration/availability guards,
- observed or inferred state,
- resulting external effect,
- relevant human surfaces,
- afferent/efferent nerve candidates,
- and evidence provenance.

Classify effective capability when useful as:

- INTRINSIC,
- BORROWED,
- COUPLED,
- POTENTIAL,
- BLOCKED,
- or UNKNOWN.

Never collapse these statements into one another:

**NEST HAS FEATURE != BODY CAN USE FEATURE != USE IS AUTHORIZED != BODY CURRENTLY USES FEATURE != EFFECT HAS BEEN OBSERVED WORKING**

### Extension receptors and surface factories

When the specimen supports plugins, add-ons, scripts, tools, dynamically registered commands, or other extensions, map the extension mechanism as a capability boundary even if no extension is currently attached.

Attempt to determine:

- discovery/loading mechanism,
- registration contract,
- lifecycle hooks,
- host services exposed to extensions,
- callbacks/events exposed by extensions,
- permissions or trust boundaries,
- commands or UI surfaces that extensions may create,
- arteries extensions can join or create,
- unload/failure behavior,
- and candidate nerve points at the host/extension seam.

Distinguish **actual attached anatomy** from **latent anatomy**: extension points capable of accepting future behavior.

---

# STAGE 5: CIRCULATORY / ARTERY ANALYSIS

Identify candidate major arteries from graph evidence.

Possible evidence includes:

- lifecycle centrality
- recurring execution
- event dispatch centrality
- high fan-in or fan-out
- paths connecting external input to state mutation
- paths connecting state to rendering/output
- persistence flows
- IPC flows
- task/queue flows
- repeated control transfer
- strong connected components
- dominator relationships
- chokepoints
- broad subsystem coverage

Do not classify arteries by name alone.

For each candidate artery, record:

- artery ID
- evidence class
- confidence
- origin
- path or graph segment
- major junctions
- loops
- data/control/event carried
- destinations/effects
- participating symbols
- dependencies
- related arteries
- open ambiguities

Classify a pathway biologically only when the evidence makes the analogy useful.

---

# STAGE 6: NERVE-ACCESS ANALYSIS

For each major artery, find candidate points where future non-destructive observation could read meaningful activity.

Potential nerve candidates include:

- function entry/exit
- event emission
- event reception
- signal/slot connection
- queue boundary
- state transition
- persistence boundary
- IPC boundary
- network boundary
- logging seam
- framework callback
- central dispatcher
- resource or document lifecycle transition

Ordinary SCAN does not insert the nerve.

For every candidate record, where determinable:

- nerve ID
- artery observed
- exact source anchor
- event or information observable
- direction: afferent / efferent / bidirectional / unknown
- estimated artery coverage
- semantic usefulness
- expected noise
- invasiveness if implemented later
- implementation difficulty
- reliability
- blind spots
- whether observation could be achieved without changing host code

Prefer a small number of high-information observation points over indiscriminate instrumentation, but do not hide uncovered arteries.

---

# STAGE 7: ANOMALY AND HIDDEN-STRUCTURE PASS

The scanner must deliberately look for code that ordinary feature documentation could miss.

Use deterministic signals such as:

- symbols not reachable from expected entry points
- weakly connected components
- code reachable only through unusual conditions
- unreferenced or obscure UI actions
- hidden shortcuts
- developer/debug commands
- compile-time feature gates
- dormant event handlers
- unusual strings/resources
- surprising network/process/filesystem effects
- orphaned functions
- rare dispatch table entries
- apparently dead code
- mismatches between documentation and implementation
- functionality present in code but absent from documented feature lists

Do not call something an easter egg, backdoor, vulnerability, or secret feature without evidence supporting that interpretation.

Record the structure first. Then attempt to establish purpose from its connectivity, guards, inputs, effects, surfaces, strings/resources, state changes, NEST couplings, and neighboring code. If the purpose remains unclear, preserve UNKNOWN rather than forcing a familiar explanation.

---

# STAGE 7A: PROGRESSIVE DEEPENING AND CONTROLLED RECONSTRUCTION EXPERIMENTS

SCAN is resumable and may operate at increasing depth. It does not need to settle every question in one pass.

A practical depth ladder is:

- **D0 Census:** identity, files, substrates, dependencies, coarse surfaces, coverage.
- **D1 Structural:** symbols, calls, events, loops, resources, build topology.
- **D2 Behavioral:** lifecycle, human surfaces, arteries, state/effect paths, candidate nerves.
- **D3 Ecological:** NEST providers, capability coupling, permissions, extension receptors, cross-boundary behavior.
- **D4 Deep static:** stronger data flow, reachability, dispatch resolution, symbolic/path analysis, generated-code tracing, rare/hidden pathway analysis.
- **D5 Experimental:** separately authorized isolated builds, runtime observation, stimulation, mocks, or reconstructed micro-experiments used to test unresolved purpose or behavior.

The user may stop after any depth. The report must state achieved depth per region rather than pretending that a shallow stop is complete.

When an unexplained structure matters, deeper passes may progressively ask:

**What exists? -> What reaches it? -> What can trigger it? -> What does it affect? -> What can the human or NEST observe? -> What purpose best fits the measured behavior?**

If static evidence remains ambiguous and D5 is explicitly authorized, SCAN may recreate the smallest practical fragment or harness needed to test a hypothesis. Preserve:

- hypothesis,
- source evidence motivating it,
- original versus reconstructed code boundary,
- inputs and environment,
- experiment procedure,
- measured result,
- limitations,
- and whether the result confirms, weakens, or leaves the hypothesis unresolved.

A reconstruction experiment is not permission to rewrite the specimen. It exists to improve the scan.

New evidence may supersede an earlier inference, but DIRECT source evidence and historical scan states must not silently disappear.

---

# STAGE 8: AI INTERPRETATION

Only after the deterministic map exists may an LLM add interpretive annotations. The LLM should consume **selected evidence**, compressed graph neighborhoods, anomaly queues, unresolved seams, and subsystem summaries rather than the raw repository by default.

For each interpretation:

- cite the machine evidence being interpreted
- mark it INFERRED unless directly supported
- explain competing interpretations when material
- preserve UNKNOWN when purpose cannot be justified

The mechanical scanner should already have answered discovery/counting/traversal questions. AI may help answer:

- Why might this structure exist?
- What biological role best describes this pathway?
- What larger application behavior does this collection of functions implement?
- Why is a particular artery important?
- Which nerve candidate is likely to be most diagnostically valuable?
- What unusual structures deserve human review?

AI must not remove unexplained structures from the scan.

AI may propose a testable hypothesis for an unresolved structure. If the operator authorizes deeper analysis, that hypothesis may feed back into Stage 7A for deterministic or experimental testing. The resulting measurement returns to the evidence map before interpretation is revised.

---

# STAGE 9: PRODUCE THE FINISHED EXAMINATION

Produce two representations.

## A. Machine Body Map

A structured format chosen by the implementation.

It must be sufficiently complete that the human report can be regenerated without rescanning the repository for ordinary interpretation changes.

It should contain provenance, file coverage, graph evidence, arteries, nerve candidates, anomalies, and unknowns.

## B. Human Body Scan Report

Render a readable report containing:

1. Specimen identity
2. Scan method and non-destructive boundary
3. Coverage and blind spots
4. Whole-body census
5. Major anatomical systems
6. Entry/lifecycle anatomy
7. Circulatory system
8. Major artery table
9. Nerve-access map
10. Human Interaction Map and surface coverage
11. NEST / ecosystem map and capability couplings
12. External sensory/input surfaces
13. Outputs/effectors
14. State and persistence structures
15. Defensive/error structures
16. Unusual, dormant, hidden, or weakly documented structures
17. Documentation-vs-implementation mismatches
18. Progressive scan depth and experiments performed
19. Explicit unknowns
20. Evidence summary
21. Anchor Gate

Do not suppress findings merely because they do not fit the expected purpose of the application.

---

# STAGE 10: DERIVE SECONDARY RECONSTRUCTION PRODUCTS

Only after the scan evidence is preserved may SCAN or a downstream tool derive a recreation-oriented model.

## Control Surface & Capability Reconstruction Map

Before reducing findings to anchors, preserve a recreation-oriented map that connects:

**human/NEST entrance -> control surface -> semantic behavior -> guards -> internal effect -> feedback -> effective capability -> NEST dependency -> fidelity test**

This map should retain obscure, hidden, dynamic, platform-specific, extension-provided, and easter-egg-like behavior when evidence supports it. The target is not merely to recreate advertised features; it is to reproduce the application's effective control surfaces and abilities closely enough that a user or agent interacting with the recreation encounters the same meaningful behavioral possibilities.

A recreation may use different internals or a different NEST mechanism when compatibility permits, but it should not silently delete a discovered capability because another implementation seems cleaner.

## Behavior Contract Map

Describe stable behavior in implementation-neutral terms. Each behavior contract should record, where known:

- trigger or stimulus,
- required preconditions,
- observable response,
- important state transition,
- persistence effect,
- error/cancellation behavior,
- evidence references,
- and uncertainty.

## Specimen Reconstruction Anchor Map

Promote only sufficiently supported properties into reconstruction anchors. These anchors are separate from the SCAN Governance Anchors.

A reconstruction anchor should state a property that must still be true in the final recreated application. It should not prescribe an implementation unless the implementation property itself is essential to observed behavior or compatibility.

A future coding agent may invent a very different internal design, but it must preserve all active reconstruction anchors and pass behavior tests derived from the scan.

The derived map must never erase details, anomalies, or unknowns from the primary scan merely because they are difficult to reproduce.

A recreation should not be described as scan-equivalent while relevant human-surface, hidden-behavior, or effective-capability regions remain UNKNOWN. The project may aim at a perfect behavioral copy, but the evidence record must remain explicit about what has and has not been demonstrated.

---


# CREATION PLAN / IMPLEMENTATION ROADMAP

This roadmap governs development of SCAN itself. It is intentionally ordered so later semantic sophistication rests on auditable mechanical evidence.

## M0 — Governance and immutable-specimen discipline — ESTABLISHED

Maintain A1-A8, pinned specimen identity, evidence classes, read-only default operation, progressive depth, and explicit experimental authorization.

## M1 — Acquisition and Stage 1 mechanical substrate — IMPLEMENTED BASELINE / PR5 EXACT ACQUISITION PASS

Reusable local/manifest/GitHub acquisition, hashing, stable file IDs, extraction cache, SQLite index, Qt/C++/CMake adapters, coverage gaps, and graph basics exist. Continue expanding language/framework adapters instead of replacing misses with manual LLM inspection.

## M2 — Evidence Graph and cross-object identity — IMPLEMENTED / R1-REFINED IN ENGINE v0.5

Required baseline:

- canonical `semantic_objects`, `semantic_relations`, and `completeness_dimensions`;
- first-class evidence objects with source locators;
- graph-relation claims that are themselves addressable;
- typed semantic overlay ingestion;
- `why` and `impact` traversal;
- evidence, completeness, and body projections derived from one store;
- rejection of dangling semantic references;
- no authoritative global completion percentage.

Current controlled regression status: 20/20 tests pass. The R1 suite now includes integrity auditing, stable-ID repeatability, typed overlay relations, proof-cycle and source-digest checks, human-surface closure, and projection-manifest coherence. This proves mechanism, not specimen completeness.

## M3 — Extraction breadth and closure machinery — ACTIVE ENGINEERING FRONT

R1 integrity refinement now provides the measurement framework for this milestone. Broaden deterministic extraction until the scanner can account for complete native control surfaces and deeper behavior across supported ecosystems. For the NotepadNext calibration specimen this includes complete C++/Qt symbol/call/event closure, generated/dynamic surfaces, Scintilla-native interactions, resources, settings influence, filesystem/process/network boundaries, lifecycle/persistence, and unresolved helper/framework dispatch.

Use denominator-driven closure rather than raw node counts. Every recurring miss becomes reusable scanner machinery.

## M4 — NotepadNext calibration convergence — COLD SCAN PASS / CALIBRATION PARTIAL

The authenticated v0.20 engine scanned the full pinned body mechanically before the preserved manual calibration set was opened. It independently recovered the 139 MainWindow QAction denominator, 137 routed actions, the two known anomalies, and the 60-second auto-save recurrence. It also preserved explicit gaps: 394 parser gaps, unavailable compiler AST context, incomplete dynamic/lifecycle/persistence closure, and noisy/partial NEST capability classification. M4 remains active until generic improvements converge on a fresh sealed rerun. New machine findings are retained even when the manual baseline missed them.

## M5 — Evidence-backed semantic synthesis and reconstruction anchors

Derive behaviors, arteries, nerves, capabilities, and interpretations as canonical graph objects. Promote a reconstruction anchor only when its dependency graph reaches adequate source evidence and unresolved contradictions are visible. Every anchor must pass a mechanical `why` query.

## M6 — Blind reconstruction experiment — M6A STATIC INFRASTRUCTURE PASS / FULL M6 OPEN

Engine v0.20 implements the M6A experiment boundary: a verified semantic certification can be split into a source-free public challenge and private evaluator, candidate submissions are challenge-bound, reconstructed candidates are rescanned, mechanically recoverable signatures are scored without source comparison, mismatch attribution is explicit, and complete trial artifacts are sealed for independent verification.

M6A scoring currently covers static human-surface/binding/effect signatures and therefore proves the experiment machinery rather than complete application equivalence. The controlled release proof uses a challenge-only generator to exercise the boundary; it is deliberately **not** counted as the capable external coding-agent proof required by PR7.

Full M6 remains:

- hand only the public challenge to a capable coding agent that has not seen the original source;
- enforce or independently attest filesystem/network source isolation;
- construct a surrogate from the SCAN package;
- measure visible controls and alternate routes, behavior/effects/feedback, lifecycle/persistence, failure/cancel/error semantics, NEST-derived abilities, dynamic/extension surfaces, obscure behavior, and selected platform behavior;
- add separately authorized M6B runtime/behavior evaluators where static evidence cannot establish equivalence;
- classify each mismatch as scanner discovery/extraction, semantic synthesis, reconstruction IR/anchor, coding-agent implementation, candidate-scanner coverage, or intentionally unresolved source uncertainty;
- feed recurring scanner/IR failures back into reusable SCAN machinery rather than patching one surrogate.

## M7 — Progressive deepening and experimental validation

Use the D0-D5 depth ladder to investigate unresolved regions. When explicitly authorized, build isolated harnesses or reconstructed fragments to determine obscure purpose, validate framework behavior, or test competing hypotheses. Evidence from experiments remains separately classified and never rewrites original source evidence.

### Milestone rule

A later milestone may begin while an earlier one is partially blocked if the work is reusable and does not pretend the blocked evidence exists. However, certification-grade reconstruction may not bypass unresolved acquisition, evidence provenance, or traceability gates.

# NOTEPADNEXT REFERENCE QUESTIONS

For the reference specimen, the deterministic scan should eventually be able to answer questions such as:

- What is the true application lifecycle from `main()` into the Qt event loop?
- Can every human-facing control be traced to its semantic behavior and internal effect?
- Which actions have multiple human routes such as menu, shortcut, toolbar, context menu, drag/drop, CLI, or OS event?
- For each user action, where are the best sensory and motor nerve candidates?
- How do secondary instances communicate with the primary instance?
- What are the major GUI event arteries?
- How do QAction triggers reach editor operations?
- How do file-open requests reach editor/document state?
- Where are save/write pathways?
- How are settings and sessions persisted?
- How does the editor engine interact with Scintilla/Lexilla?
- How is Lua used and what application behavior can it influence?
- What timers, event filters, callbacks, and recurring loops exist?
- Which functions or surfaces appear weakly documented or unusual?
- Are there reachable behaviors not represented in the high-level project description?
- Which effective abilities belong to NotepadNext itself and which are borrowed or coupled through Qt, Scintilla/Lexilla, the operating system, filesystem, IPC facilities, or other NEST components?
- Which extension or scripting boundaries can grow new surfaces or capabilities?
- For an obscure or apparently easter-egg-like pathway, how deeply can SCAN establish purpose before experimental testing becomes necessary?
- Where could a future observer attach the fewest high-value nerves to see the most important arteries?

These are questions to drive evidence collection, not conclusions to assume.

---

# COMPLETION STANDARD

A scan is not complete because a report was produced.

Completion requires:

- specimen identity is stable,
- relevant files are accounted for,
- coverage gaps are explicit,
- structural maps are reproducible,
- meaningful lifecycle states and transitions are reconstructed where evidence permits,
- applicable human-facing surfaces and actions have explicit coverage states,
- mapped user actions are traceable from affordance through effect and feedback where evidence permits,
- static behavior scenarios distinguish proven paths from unresolved runtime behavior,
- relevant NEST providers and body/NEST capability couplings have explicit coverage states,
- environmental possibility is distinguished from demonstrated or authorized capability,
- scan depth and any experiments are recorded with provenance,
- obscure or hidden structures are preserved even when purpose remains UNKNOWN,
- major arteries are evidence-backed,
- nerve candidates are mapped without insertion,
- unusual structures are retained,
- repeatable discovery operations live in reusable scanner modules/adapters rather than disposable scripts,
- the Machine Body Map is queryable without an LLM rereading the repository,
- stable IDs, extraction provenance, and cache/resume state are preserved,
- evidence is represented as first-class objects with source/extractor provenance where exact evidence is available,
- semantic claims and reconstruction anchors retain typed references into the canonical evidence graph,
- selected reconstruction anchors can answer `why` mechanically and important evidence can answer `impact`,
- completeness remains visible by anatomical dimension rather than being hidden behind one aggregate percentage,
- projection files retain canonical cross-object IDs and cannot silently drift into separate authorities,
- interpretations are separated from observations,
- and every active anchor passes the final Anchor Gate.

If complete coverage is impossible, report an honest partial scan rather than inventing completeness.
