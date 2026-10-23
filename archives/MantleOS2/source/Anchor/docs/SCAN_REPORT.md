# NOTEPADNEXT SOFTWARE BODY SCAN
Working Report Version: 0.32
SCAN Protocol: 0.32
Status: COLD SCAN PASS / CALIBRATION PARTIAL
This file is intended to be edited in place as deterministic SCAN coverage increases.

**Current project-state note (v0.32 checkpoint):** the v0.20 cold LLM-disabled NotepadNext certification remains the immutable pre-oracle baseline. Frozen Engine v0.26 generically corrects the v0.25 surface denominator while preserving all declared/factory surface states. Two exact manifest-backed scans were byte- and row-identical; the final installed-wheel certification independently verified 12/12 files. Compiler evidence remains 84 mapped plus 294 partial of 394 translation units, with 16 unavailable and 331 explicit parser gaps. PR5 remains PARTIAL, not converged: human-surface closure is now 310 bound, 59 partial, and 11 unresolved of 380. H-001 is frozen and source-uninspected. Earlier sections remain chronology, not current gate claims. See `releases/v0.26/SCAN_v0.26_REPORT.md` and `releases/v0.26/PR5_CALIBRATION_REPORT_v026.md`.

## 0. Current authoritative v0.26 calibration result

- Exact identity: `dail8859/NotepadNext@f57db52d6760a2ce4149a37190c3adaa586845f5`, tree `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`.
- Acquisition: 1,928/1,928 provider blobs, 20,875,384 verified bytes, oracle unused.
- Determinism: two fresh manifest scans emitted 21/21 byte-identical files and zero canonical database-row differences; warm-cache proof recorded 4,186 hits / 0 misses without evidence drift.
- Mechanical body: 124,959 nodes, 139,431 edges, 137,559 evidence records, 408,862 semantic objects, 1,015,328 semantic relations.
- Compiler evidence: 84 `MAPPED`, 294 valid-but-`PARTIAL`, 16 unavailable of 394 translation units; 331 explicit parser gaps.
- Integrity: `PARTIAL`, 13 WARN-only orphan-evidence issues, zero ERRORs.
- Human surfaces: 380 total; 310 bound, 59 partial, 11 unresolved. All 330 declared/factory surfaces retain their v0.25 states; only 108 false reference candidates were removed.
- Effect closure: 87 closed, 282 partial, 11 unresolved; feedback observed for 59 surfaces.
- Packaging: reproducible source ZIP SHA-256 `4e262e4780a89802dd9ea3ebc390df18bafc3972eaa400cc2d21f0b7550960ba`; reproducible wheel SHA-256 `0fe02da00a32a5074d39b7120b4d41c8a2fbd482b02dac8863ccd1cb08209e41`.
- Sealed certification: 277,456,091 bytes, SHA-256 `4c3fa6b8438832533864b859ddbd51d7343d30c951d7d0e1aaad831c83c27dcc`; independent verification 12/12 PASS, zero issues.
- Adaptive assessment: deterministic inert workbench opened for Lua and Python substrate gaps; no generated candidate code was executed or promoted.

Gate decision: **mechanical certification PASS; PR5 calibration PARTIAL**. The next admissible loop is generic analysis of the remaining 11 unresolved and 59 partial surfaces followed by two fresh sealed reruns. No NotepadNext-specific rule is admissible.

## 0A. Immutable v0.20 PR5 cold result

- Exact identity: commit `f57db52d6760a2ce4149a37190c3adaa586845f5`, tree `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`.
- Acquisition: 1,928/1,928 provider blobs, 20,875,384 verified bytes, zero unavailable files; exact acquisition SHA-256 `4a1343f4f56500ba850162039e7483e2f17f894be6493f5afbaacdf25c2c44a3`.
- Cold execution: authenticated SCAN Engine 0.20.0, LLM disabled, oracle unused, no budget stop, zero parser failures.
- Sealed certification: 213,474,077 bytes; SHA-256 `6c0d476e2dd7a63481cf388e6d654798ffa26f8c72ce9760a8bd60667b075ce3`; independent verification 12/12 PASS with zero issues.
- Mechanical body: 101,138 nodes, 109,282 edges, 109,072 evidence records, 326,026 semantic objects, 808,588 semantic relations.
- Oracle comparison: exact 139 MainWindow QActions and 137 routed actions; both known unrouted/disabled anomalies match; 60-second auto-save recurrence maps.
- Honest gaps: 394 parser gaps, no compiler AST coverage for 394 translation units, lifecycle UNKNOWN, persistence 1 provider/0 operations, 82 unresolved and 59 partial human routes, noisy/partial NEST classification, long runtime, Windows manifest identity incompatibility, and missing commit population in the native receipt.

Gate decision: **mechanical certification PASS; PR5 calibration PARTIAL**. Only generic corrections followed by fresh sealed reruns may advance this gate. See `evidence/pr5/PR5_CALIBRATION_REPORT.md` and `evidence/pr5/PR5_COLD_SCAN_RECEIPT.json`.

## 1. Specimen Identity

Repository: `https://github.com/dail8859/NotepadNext`

Pinned commit:

`f57db52d6760a2ce4149a37190c3adaa586845f5`

Pinned Git tree SHA:

`f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`

Commit date observed through repository metadata: 2026-08-30

Commit message: `Update translation files`

Default branch observed: `master`

SCAN boundary for the authoritative v0.29 result: read-only static scanning of verified repository bytes. No NotepadNext code was executed or modified.

Current progressive depth is mechanically expressed by the sealed completeness vector. Human surfaces and several Qt routes are mapped or partial; compiler-assisted structure is blocked, lifecycle is unknown, and persistence/NEST closure remains partial. No D5 experimental mode has been authorized or performed.

Evidence status:

- Repository identity: DIRECT
- Commit identity: DIRECT
- Source observations below: DIRECT
- Structural conclusions: INFERRED where explicitly labeled
- Reusable scanner engine: IMPLEMENTED v0.18 / MECHANICALLY TESTED
- Exact whole-repository NotepadNext acquisition: PASS; 1,928/1,928 provider blobs verified
- Full deterministic whole-repository NotepadNext scanner run: PASS for cold mechanical certification
- Manual-vs-machine calibration: PARTIAL; generic convergence work remains
- Full-body coverage claim: NOT MADE

This is therefore a sealed full-body mechanical scan record, but not a claim of complete semantic or behavioral reconstruction.

---

## 2. Current Coverage

Current state: **PARTIAL**

Evidence already examined includes:

- repository tree metadata,
- `src/main.cpp`,
- `src/NotepadNextApplication.cpp`,
- `src/dialogs/MainWindow.cpp`,
- `src/EditorManager.cpp`,
- `src/SessionManager.cpp`,
- `src/ScintillaNext.cpp`,
- `src/dialogs/MainWindow.ui`,
- `src/dialogs/FindReplaceDialog.ui`,
- `src/dialogs/PreferencesDialog.ui`,
- `src/dialogs/ColumnEditorDialog.ui`,
- `src/dialogs/MacroRunDialog.ui`,
- `src/dialogs/MacroSaveDialog.ui`,
- `src/dialogs/MacroEditorDialog.ui`,
- `src/widgets/QuickFindWidget.ui` and `QuickFindWidget.cpp`,
- `src/widgets/TabsQuickActionsBar.cpp`,
- `src/docks/FolderAsWorkspaceDock.ui/.cpp`,
- `src/docks/FileListDock.ui/.cpp`,
- `src/docks/SearchResultsDock.ui/.cpp`,
- `src/docks/LuaConsoleDock.ui/.cpp`,
- `src/docks/EditorInspectorDock.ui/.cpp`,
- `src/docks/LanguageInspectorDock.ui`,
- `src/docks/DebugLogDock.ui`,
- `src/DockedEditor.cpp`,
- visible `src/` inventory evidence,
- selected repository search evidence around Qt application and event wiring.

Important limitation:

The complete pinned repository has now passed through the engine, but the cold completeness vector retains explicit PARTIAL, BLOCKED, and UNKNOWN dimensions. Mechanical enumeration is not semantic convergence; compiler/type dispatch, lifecycle, persistence, dynamic families, effect/capability classification, and some human routes remain incomplete.

This limitation is intentional. Missing understanding is not being replaced with an estimate.

### 2.1 Scanner Engine Implementation Checkpoint

TOOLING STATUS, not specimen evidence: SCAN now contains a reusable Stage 1 engine under `scan_engine/` rather than relying on disposable scripts or manual LLM repository walks. The current **v0.20** implementation provides:

- recursive read-only local file inventory;
- SHA-256 content hashing for materialized bytes;
- stable machine IDs;
- normalized SQLite storage for files, nodes, edges, evidence, findings, extraction cache, canonical semantic objects/relations, and completeness dimensions;
- content-hash plus adapter-version extraction caching;
- JSON Machine Body Map export and mechanical Markdown summary;
- first-class evidence objects with source location/extractor provenance;
- canonical cross-object semantic/evidence graph with stable IDs;
- lossless `evidence_graph.json`, `evidence_catalog.json`, and `completeness_vector.json` projections;
- data-only semantic overlay ingestion for interpretations/behaviors/capabilities/reconstruction anchors;
- mechanical `why` and `impact` provenance/dependency traversal;
- provider source-manifest ingestion for remote repositories;
- hybrid manifest scans in which only exact locally materialized paths are parser-eligible;
- explicit acquisition states that distinguish provider-visible metadata from available content bytes;
- reusable read-only GitHub acquisition that resolves an exact ref, records commit/tree identity, falls back to an explicit tree walk when a recursive tree is truncated, retrieves Git blobs, verifies canonical Git blob SHA-1, and records SCAN SHA-256 separately;
- scanner-owned inert content storage and verified blob cache;
- explicit `BLOCKED`, `HASH_MISMATCH`, `EXTERNAL_REFERENCE`, and `SYMLINK_REFERENCE` handling;
- structured machine-readable acquisition failure output instead of raw tracebacks;
- Qt `.ui` extraction for actions/widgets/menu/toolbar membership and properties;
- C++/Qt extraction for includes, function candidates, QAction references, direct signal-to-method and signal-to-lambda wiring, `connectEditorAction` helper-mediated dispatch, conservative QTimer recurrence, dynamic action registrations, programmatic shortcuts, platform guards, NEST-boundary candidates, and extension-receptor candidates;
- CMake target/dependency extraction;
- generic text boundary candidates;
- graph degree/SCC metrics;
- built-in mechanical queries including surfaces, surfaces without discovered handlers, recurrence, subprocess/NEST boundaries, extension candidates, dynamic registrations, partial/unknown nodes, `acquisition-gaps`, evidence, semantic objects/relations, and completeness;
- Qt `.ui` evidence line-location recovery for declarations where mechanically available;
- common interactive Qt widget census, Designer `<connections>`, and Designer QAction shortcuts;
- generic `ui->objectName` surface references with uniqueness-gated cross-file resolution;
- dynamic QAction and QShortcut identity preserved through event wiring;
- QCommandLineParser option/positional surfaces plus literal consumers;
- Qt event-override entrances for drag/drop, keyboard, pointer, context-menu, close, focus, and file-open patterns;
- ambiguity-preserving resolution findings rather than guessed cross-file bindings;
- stable-ID duplicate merging so declarations/references retain combined evidence;
- bounded graph-based human-surface closure and denominator subdimensions by surface type;
- optional compiler-assisted Clang AST extraction using a fixed scanner-selected executable and safe compile-context flags only;
- brace-aware fallback C++ function/call extraction when compiler context is unavailable;
- sender-scoped Qt signal-event identity that prevents unrelated controls sharing one signal type from inheriting each other's handlers;
- project-local call references/resolution with ambiguity preserved rather than guessed;
- first-class state-change, effect, feedback, and function-context NEST/extension links;
- `effect_closure.json` plus `deep-closure`, `calls`, `effects`, and `state-changes` mechanical queries;
- `cpp-compiler-ast` and `human-surface-effect-closure` completeness dimensions;
- bounded compile-database discovery and compile-context-sensitive compiler extraction-cache keys;
- compiler-derived C++ types/inheritance, signatures, override/overload/template origin, and virtual-dispatch candidates;
- compiler-typed Qt/NEST effect synthesis for supported settings/clipboard/filesystem/process/network/IPC/printing APIs;
- preprocessor macro/conditional provenance and Qt generated-code receptors/contracts without executing generators;
- Scintilla/Lexilla command/notification/lexer coupling as framework-owned capability evidence;
- `cpp-type-dispatch`, `conditional-compilation`, `qt-generated-code`, and `scintilla-lexilla-coupling` completeness dimensions.
- programmatic Qt interactive-widget census for common `new QWidgetSubclass(...)` patterns;
- sender identity reuse so programmatic widgets participate in ordinary Qt signal closure;
- bounded connect-lambda body attribution so fallback calls/effects/feedback inside the lambda attach to the lambda handler;
- explicit `setReadOnly(true)` classification as a presented/read-only surface rather than an actionable input denominator item;
- keyed QAction registry extraction as stable semantic action identities;
- clone-route `surface_instance` objects so one semantic action can have multiple menu/context/shortcut carriers without inflating behavior count;
- `QAction::data()` payload equality/prefix dispatch as explicit dispatch cases;
- bounded indexed dynamic action families with retained bound expressions;
- orphan semantic-action and duplicate keyed-dispatch findings;
- CMake contradictory guard/compile-definition findings that preserve both source facts without silently choosing intent.
- sealed specimen-certification receipts/manifests and independent post-transfer verification for agent handoff, with mechanical integrity explicitly separated from coverage completeness.
- QtConcurrent/QFutureWatcher async-task, future-delivery, finished-event, and continuation closure with unresolved origins retained as PARTIAL;
- aggregate byte/file/time/node/edge/evidence budgets plus safe-boundary cancellation with explicit `scan_budget` evidence;
- derived SQLite schema/corruption policy with scan-time quarantine/rebuild and non-silent read-only failure;
- deterministic package/projection self-audit and an LLM-disabled 12-query release qualification;
- ordinary adapter exception containment as first-class `parser_failure` / PARTIAL file coverage while retaining fatal `MemoryError`;
- budget-stop resume validation and packaged wheel deployment validation.

- qmake `.pro`/`.pri`/`.prf` build-topology extraction with conditional declarations kept UNKNOWN until evaluated;
- Qt `.qrc` resource collections/assets without executing `rcc`;
- legacy Qt `SIGNAL()/SLOT()` sender-scoped event/handler wiring;
- `QTimer::singleShot(..., SLOT(...))` delayed-dispatch anatomy;
- multimedia `QSound`/`QSoundEffect` playback as NEST-coupled effect plus observable feedback;
- conservative QWidget repaint feedback from `update()`/`repaint()`;
- removal of ordinary `addMenu()`/`addAction()` from generic extension-receptor heuristics.

MEASURED current scanner regression status: Engine v0.20 passes **111/111 tests** in the development tree and in a clean extraction of the packaged release. The clean package self-audit verifies **67/67 tracked files** with zero issues; the LLM-disabled release qualification passes **12/12 required mechanical queries**. A fresh Python 3.13.5 virtual environment installs the v0.20 wheel and successfully completes the agent-facing chain: mechanical parent certification PASS -> reconstruction-aware child certification PASS -> public/private reconstruction-trial split PASS -> challenge-only controlled candidate generation -> private candidate scoring PASS -> sealed trial verification PASS. The controlled candidate satisfies **1/1 scorable anchor with fidelity_score 1.0**, while parent and semantic child certifications independently remain valid afterward. The challenge exposes source-free scoring requirements but contains no original source bytes/paths/excerpts, canonical database, evidence graph/catalog, or private evaluator. This is tooling evidence, not NotepadNext specimen evidence and not the capable external-agent PR7 proof. The earlier 321-file load fixture remains the current development load baseline (4.5326 s cold / 0.5398 s warm, 1,542 cache hits / 0 misses).

### 2.2 Calibration Run CR-001: Full pinned NotepadNext Stage 1 attempt

The planned calibration run was started against repository `dail8859/NotepadNext`, commit `f57db52d6760a2ce4149a37190c3adaa586845f5`, tree `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`.

**Result: BLOCKED at acquisition transport before full Stage 1 content parsing.**

The connected GitHub provider can enumerate and read the pinned repository and individual text files, but the current execution boundary does not expose the complete pinned archive as local scanner-readable bytes. The local Stage 1 engine therefore cannot truthfully hash and parse the complete repository body in this run. SCAN did **not** substitute estimates, copy individual files through the LLM, switch to the default branch, or treat provider metadata as parsed source.

This failure exposed a general scanner requirement rather than a NotepadNext-specific exception: **repository visibility and byte materialization are separate evidence states**. The scanner was consequently upgraded from v0.1 to v0.2 so a provider can supply a source manifest even when not all blobs have crossed the acquisition seam. Metadata-visible files remain in the ledger as `PARTIAL / METADATA_ONLY`; only verified materialized bytes are eligible for source adapters.

A real metadata-only calibration subset was then run through v0.2 for three previously identified pinned provider objects:

| Path | Provider object | Acquisition | Coverage | Parser run |
|---|---|---|---|---|
| `src/dialogs/MainWindow.cpp` | `426eb5356119d2e56950f66e5affbda9ba9f4f79` | METADATA_ONLY | PARTIAL | no |
| `src/dialogs/MainWindow.h` | `b79b0b83679fdf03bc70563b152d7cd78522d643` | METADATA_ONLY | PARTIAL | no |
| `src/dialogs/MainWindow.ui` | `f947946e36d0e3f5bee0b9e7c489344ad54c5412` | METADATA_ONLY | PARTIAL | no |

MEASURED output of that subset manifest run:

- Machine Body Map schema: `scan-machine-body-map/0.2`
- scanner engine: `0.2.0`
- provider-tree fingerprint: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`
- files accounted for: **3**
- materialized files: **0**
- metadata-only files: **3**
- coverage: **3 PARTIAL**
- acquisition state: **3 METADATA_ONLY**
- extraction nodes/edges/evidence: **0 / 0 / 0**, intentionally, because no exact source bytes were supplied to adapters
- acquisition findings: **1 aggregate acquisition-gap finding**
- `acquisition-gaps` query: correctly returns all three provider-visible, non-materialized files.

This is a calibration of the **acquisition semantics**, not a substitute for the requested full-body NotepadNext scan. The known manual QAction, dynamic-surface, helper-dispatch, Lua, timer, lifecycle, and NEST findings remain calibration questions until the exact pinned repository bytes can be processed mechanically by the Stage 1 engine.

### 2.3 Calibration plan execution status

| Planned step | CR-001 status | Evidence consequence |
|---|---|---|
| Acquire exact pinned specimen | PARTIAL / BLOCKED | revision/tree visible; complete local bytes unavailable |
| Run Stage 1 over whole body | BLOCKED | not eligible to claim full content census or parser coverage |
| Use manual baseline as calibration set | PRESERVED | baseline retained but not injected into scanner extraction |
| Generate discrepancy report | PARTIAL | acquisition discrepancy established; anatomy comparison awaits full machine run |
| Improve reusable scanner and rerun | PASS for acquisition layer | v0.2 manifest/hybrid acquisition and gap query implemented; regression suite 4/4 pass |
| Require convergence before deeper semantics | ACTIVE | full calibration gate remains closed |

**CR-001 resume condition at that checkpoint:** obtain the exact pinned repository tree as scanner-readable local bytes, or provide a reusable provider acquisition driver capable of transferring those exact blobs into scanner-owned storage. That driver is now implemented in v0.3; CR-002 below tests the next boundary.

### 2.4 Calibration Run CR-002: Reusable GitHub acquisition driver

CR-002 implemented the next planned step rather than asking the LLM to manually shuttle repository files. The v0.3 `acquire-github` path now resolves an explicitly supplied GitHub ref to immutable commit/tree identities, enumerates the provider tree, retrieves each ordinary blob through Git's object API, verifies Git's canonical blob SHA-1 before materialization, records a separate SCAN SHA-256, and writes only into scanner-owned inert storage. Gitlinks/submodules and symlink references remain explicit non-parser-eligible anatomy instead of being followed implicitly.

The acquisition report intentionally distinguishes:

- directly fetchable provider blobs whose bytes were verified;
- visible entries that were actually materialized;
- blocked blob transfers;
- external/gitlink/symlink references that require separate accounting.

The command was then executed locally against the exact NotepadNext pin:

`dail8859/NotepadNext @ f57db52d6760a2ce4149a37190c3adaa586845f5`

**Local execution result: BLOCKED by execution-environment network transport before the first GitHub REST response.** The Python runtime reported DNS name-resolution failure for `api.github.com`. v0.3 now converts that failure into a concise structured acquisition record with `stage=ACQUIRE`, `provider=github`, `acquisition_state=BLOCKED`, the exact repository/ref, and a non-zero exit status instead of emitting a raw Python traceback. No parser was run and no specimen result was fabricated.

This is an environment limitation, not evidence that the provider revision is absent. The connected GitHub repository interface independently continues to expose the exact pinned source. For example, the pinned `NotepadNextApplication.cpp` contains a direct `QTimer::timeout` connection to `NotepadNextApplication::saveSession` followed by `autoSaveTimer.start(60 * 1000)`, and also contains both direct method-pointer and lambda-style Qt `connect(...)` forms. Those exact source forms motivated reusable v0.3 parser regression cases rather than NotepadNext-specific function-name rules.

MEASURED v0.3 regression status after these changes: **9/9 PASS**. The tests establish that the acquisition algorithm can verify/materialize exact provider blobs under a deterministic fake transport, refuses mismatched bytes, survives GitHub recursive-tree truncation by explicit walking, emits structured failure when transport is unavailable, resolves common Qt method/lambda handler edges, and recognizes a timer as recurrence only when its sender is structurally connected to `QTimer::timeout`.

CR-002 therefore closes the **scanner design gap** identified by CR-001, but it does not yet close the **current runtime transport gap**. The full NotepadNext Stage 1 body scan remains unperformed in this container.

### 2.5 Current calibration gate

| Gate | Current status | Meaning |
|---|---|---|
| Exact specimen identity | PASS | pinned commit/tree already established |
| Reusable provider acquisition algorithm | PASS | implemented in v0.3 and covered by regression tests |
| Provider-byte integrity verification | PASS in regression | Git object SHA verified before parser eligibility; SHA-256 separately recorded |
| Live whole-repository transfer in this runtime | BLOCKED | Python runtime cannot resolve/reach GitHub |
| Full NotepadNext Stage 1 census/parser run | BLOCKED downstream | cannot begin until exact bytes cross the acquisition seam |
| Manual-vs-machine anatomy discrepancy run | WAITING | requires full machine extraction |
| Calibration convergence | OPEN | no completeness claim |

**Historical resume condition (satisfied in project v0.28):** acquire or supply the exact pinned repository archive/folder as scanner-readable bytes. The source is now materialized and sealed; the remaining resume condition is recovery and verification of the authentic Engine v0.20 execution bundle, followed by cold scanning and sealing before comparison.

### 2.6 Evidence Graph Milestone EG-001

A review of the illustrative `MantleOS2_SCAN_Example_v0.1.zip` identified an important product-shape improvement: the package's separate body, artery, nerve, control-surface, NEST, and reconstruction views should become projections of **one canonical graph**, with evidence as a first-class object and reconstruction anchors mechanically traceable to source.

MEASURED package-review input: the supplied example ZIP contains nine manifest-tracked payload files plus `MANIFEST.json`; all nine tracked payloads match the manifest byte counts and SHA-256 digests, and every JSON artifact parses successfully. This validates the example package's transport integrity, not its specimen-level claims.

SCAN Engine v0.4 implements the first reusable evidence-graph substrate:

- `semantic_objects` gives files, evidence, anatomical structures, graph-relation claims, findings, interpretations, behaviors, capabilities, arteries, nerves, and reconstruction anchors one referential space;
- `semantic_relations` carries typed cross-object relationships;
- `completeness_dimensions` represents coverage as a vector rather than one percentage;
- source evidence becomes queryable objects with source locators and extractor identity;
- extracted structural edges are addressable claims whose supporting evidence can be queried;
- `ingest-knowledge` adds data-only semantic overlays but rejects dangling references;
- `why` walks backward from a semantic object/anchor to supporting evidence/source;
- `impact` walks forward from source/evidence to dependent claims and anchors;
- `evidence_graph.json`, `evidence_catalog.json`, `completeness_vector.json`, and the Machine Body Map are projections of the same canonical SQLite store.

A controlled two-file Qt fixture was used to validate the new mechanism. The Stage 1 scan produced 2 materialized files, 8 extracted nodes, 4 extracted edges, 8 evidence records, 23 canonical semantic objects, 40 semantic relations, and 13 completeness dimensions. A data-only overlay then added one interpretation and one reconstruction anchor. `why RA-DEMO-001` traversed backward through the interpretation and discovered Save surface to a DIRECT evidence object at `MainWindow.ui`; `impact <that-evidence-id>` traversed forward through the same surface and interpretation to `RA-DEMO-001`.

**EG-001 verdict: PASS for mechanism / NOT YET APPLIED TO COMPLETE NOTEPADNEXT BODY.** The v0.4 suite is **12/12 PASS**. This proves that SCAN can mechanically represent and traverse proof dependencies on controlled inputs. It does not upgrade the NotepadNext specimen coverage while the whole pinned body remains unavailable to the local scanner runtime.

### 2.7 Refinement Gate R1-001: Evidence integrity and denominator closure

R1-001 refined the evidence graph before expanding semantic interpretation. Engine v0.5 adds reusable integrity auditing, source-digest-aware evidence objects, typed semantic-overlay relations, stable-ID repeatability testing, proof-path validation, positive proof-cycle detection, human-surface closure, nested completeness dimensions, and projection hash manifests. Semantic-overlay ingestion now refreshes affected projections and their manifest so the canonical database cannot quietly diverge from friendly output files.

A controlled two-file Qt specimen was used. It deliberately contains two QAction surfaces: `actionSave`, which is connected through `QAction::triggered` to a save handler, and `actionGhost`, which is declared but has no handler. This is scanner tooling evidence, not NotepadNext specimen evidence.

MEASURED R1-001 output before semantic overlay:

- files: **2**;
- extraction nodes: **9**;
- extraction edges: **4**;
- first-class evidence records: **9**;
- canonical semantic objects: **25**;
- semantic relations: **43**;
- completeness dimensions: **16**.

After adding one supported interpretation and `RA-R1-SAVE`, the strict integrity audit reports **MAPPED / 0 issues**. Surface closure reports **PARTIAL: 2 surfaces, 1 BOUND, 1 UNRESOLVED**. This is the intended result: an unresolved control remains visible without being misclassified as corruption or silently assigned a handler. `why RA-R1-SAVE` returns `proof_complete=true` and reaches both first-class evidence and its source file; `impact` from the Save evidence reaches `RA-R1-SAVE`. All projection hashes verify after overlay refresh.

The v0.5 scanner self-scan accounts for **29 files, 57 extraction nodes, 22 edges, 56 evidence records, 165 canonical semantic objects, and 281 semantic relations**. Its evidence-integrity audit is **MAPPED / 0 issues** while its own human-surface closure remains PARTIAL, correctly exposing extraction breadth still to be improved.

**R1-001 verdict: PASS for refinement mechanism / EXTRACTION BREADTH STILL PARTIAL.** The v0.5 regression suite is **20/20 PASS**. The next active work is not additional semantic abstraction; it is M3 denominator-driven extraction breadth and closure.

### 2.8 M3A Surface Breadth Gate SB-001

SB-001 advances M3 from proof-graph integrity into denominator-driven human-surface extraction. Engine v0.6 deliberately begins from declared/factory surfaces and attempts to resolve their routes rather than starting from known handlers.

Implemented reusable mechanisms include Qt Designer `<connections>`, explicit QAction shortcut surfaces, broader interactive Qt widgets, generic `ui->objectName` references, uniqueness-gated cross-file resolution, dynamic QAction/QShortcut identity, QCommandLineParser option/positional controls and consumers, event-override entrances, ambiguity findings, stable-ID duplicate merging, and bounded closure traversal through aliases, signals, routes, and handlers.

MEASURED controlled M3A fixture:

- 3 materialized files;
- 37 extraction nodes;
- 27 structural edges;
- 37 evidence records;
- 105 canonical semantic objects;
- 235 semantic relations;
- 24 completeness dimensions;
- integrity audit: **MAPPED / 0 issues**;
- human-surface denominator: **11 surfaces, 10 BOUND, 1 UNRESOLVED**.

The unresolved control is a deliberately declared CLI positional surface whose fixture does not consume `positionalArguments()`. It remains visible rather than being inferred away. The denominator is broken down by surface type, so QAction, QPushButton, QShortcut, CLI option, CLI positional, drag/drop, keyboard-shortcut, and cross-file-reference closure can be inspected separately.

The v0.6 regression suite is **28/28 PASS**. New tests cover unique and ambiguous Qt object-name resolution, Designer wiring, shortcut routes, dynamic-action identity, QShortcut routing, CLI consumers, event entrances, duplicate-object evidence merging, and nested surface-type completeness.

A v0.6 self-scan accounts for **31 files, 58 extraction nodes, 23 edges, 57 evidence records, 170 canonical semantic objects, and 300 semantic relations**. Its evidence-integrity audit is **MAPPED / 0 issues**. Its own human-surface closure remains PARTIAL, correctly demonstrating that M3 breadth is not yet complete.

**SB-001 verdict: PASS for M3A mechanism / NOT A NOTEPADNEXT CERTIFICATION.** The exact complete pinned NotepadNext body still has not crossed the acquisition seam in this runtime, so no full-body specimen coverage is being inferred from these scanner tests.

### 2.9 M3B-001 Deep Structural / Effect Closure

M3B-001 advances SCAN from first-handler closure toward consequence closure. Engine v0.7 introduces an optional compiler-assisted Clang AST path and a brace-aware source fallback, then follows mechanically resolved project-local calls toward state mutation, NEST effects, extension boundaries, presented surfaces, and visible feedback.

The compiler path is deliberately constrained. SCAN invokes a fixed local Clang executable with `-fsyntax-only`/AST-dump behavior; it does **not** execute compiler commands contained in the specimen. `compile_commands.json` contributes only whitelisted parser context such as include paths, defines, language mode, and standard. Response files, forced includes, output options, plugins, `-Xclang`, `-load`, and similar specimen-supplied command fragments are not replayed. Compiler parse failure becomes an explicit parser gap and the conservative fallback may continue.

During M3B validation, a controlled fixture exposed two real scanner defects and both were repaired before this milestone was accepted:

1. Qt signal events had been identified only by signal type, which could allow two unrelated QActions using `QAction::triggered` to share downstream handlers. v0.7 scopes signal-event identity to the sender so unrelated controls cannot cross-wire mechanically.
2. Fallback function matching allowed newline whitespace in a return-type span, causing parser variants to disagree about a function's start line and therefore split one function into two stable identities. The fallback recognizer now restricts that portion to horizontal whitespace, allowing compiler and fallback evidence for unchanged functions to converge.

A third refinement separates presented/output surfaces from actionable entrance denominators. A message dialog opened by a handler remains a human-facing feedback terminal, but it is not counted as a new independent binding entrance unless a deeper adapter models its internal controls.

MEASURED controlled M3B fixture after these repairs:

- 2 materialized files;
- 37 extraction nodes;
- 41 structural edges;
- 39 evidence records;
- 0 findings;
- 120 canonical semantic objects;
- 297 semantic relations;
- 19 completeness dimensions;
- integrity audit: **MAPPED / 0 issues**;
- QAction entry denominator: **3**;
- binding closure: **2 BOUND / 0 PARTIAL / 1 UNRESOLVED**;
- deep consequence closure: **2 CLOSED / 0 PARTIAL / 1 UNRESOLVED**;
- feedback reached from **2** bound actions;
- compiler-AST dimension on the controlled translation unit: **MAPPED**.

`actionSave` follows its sender-scoped event to `MainWindow::saveFile()`, through `persistDocument()`, to a `QFile::rename(...)` filesystem-write effect, state mutation, filesystem NEST evidence, and status feedback. `actionInfo` reaches modal-message feedback. The deliberately unbound `actionGhost` remains UNRESOLVED.

The v0.7 regression suite is **37/37 PASS**. New coverage includes compiler AST enrichment, safe compile-database filtering, deep call/effect/state/feedback closure, sender-scoped Qt events, compiler/fallback function-identity convergence, and presented-surface denominator separation.

**M3B-001 verdict: PASS FOR BASELINE MECHANISM / DEEPENING STILL REQUIRED / NOT A NOTEPADNEXT CERTIFICATION.** The full pinned NotepadNext bytes remain unavailable to the local scanner runtime, and real Qt compiler-context closure, virtual/template/macro/generated-code resolution, Scintilla/Lexilla-native behavior, and broad persistence/NEST semantics are not yet complete.

A v0.7 self-scan after packaging cleanup accounts for **35 files, 74 extraction nodes, 37 edges, 72 evidence records, 221 canonical semantic objects, and 410 semantic relations**. Its strict evidence-integrity audit is **MAPPED / 0 issues**. A second unchanged scan reports **41 extraction-cache hits / 0 misses**. Its own deep effect closure remains PARTIAL, and its bundled C++ fixtures leave the `cpp-compiler-ast` dimension BLOCKED because those Qt fixture translation units intentionally lack a real Qt compiler environment. Both states remain visible rather than being promoted to success.

### 2.10 M3B-2-001 Compiler / Type / Framework Closure

M3B-2-001 advances the deep-closure layer from mostly call/name structure toward compiler-supported type and framework provenance. Engine v0.8 introduces bounded compile-database discovery, context-sensitive compiler-cache keys, type/inheritance/override/overload/template/virtual-dispatch evidence, compiler-typed Qt/NEST effects, preprocessor and Qt generated-code contracts, and Scintilla/Lexilla capability coupling.

MEASURED controlled M3B-2 fixture:

- 3 files;
- 34 extraction nodes;
- 23 structural edges;
- 31 first-class evidence records;
- 92 canonical semantic objects;
- 199 semantic relations;
- 23 completeness dimensions;
- evidence-integrity audit: **MAPPED / 0 issues**;
- human entry denominator: 2 QAction surfaces;
- deep closure: **1 CLOSED / 0 PARTIAL / 1 UNRESOLVED**.

The Save action closes through a handler to a compiler-typed `QSettings::setValue` effect and a MAPPED settings/NEST boundary. The deliberate Ghost action remains UNRESOLVED. The same fixture contains `Q_OBJECT`, CMake AUTOMOC/AUTOUIC declarations, and a Scintilla command; these appear as generated-code/framework coupling evidence and are not misrepresented as application-owned controls.

The v0.8 regression suite is **43/43 PASS**. New coverage includes nested compile-database discovery, parse-context cache invalidation, overload-safe call identity, virtual/override dispatch candidates, template-specialization provenance, compiler-typed Qt-like effects, preprocessor/Qt code-generation contracts, and Scintilla/Lexilla coupling.

A v0.8 self-scan accounts for **39 files, 81 extraction nodes, 42 edges, 77 evidence records, 242 canonical semantic objects, and 451 semantic relations**, with **24 completeness dimensions** and **MAPPED / 0 integrity issues**. A second unchanged run reports **47 extraction-cache hits / 0 misses**. Its bundled C++ fixture translation units still leave compiler-AST coverage BLOCKED where the real external Qt build context is absent; this remains visible.

**M3B-2-001 verdict: PASS FOR BASELINE MECHANISM / PR2-PR4 DEPTH STILL OPEN / NOT A NOTEPADNEXT CERTIFICATION.** Whole-program virtual/interface closure, macro-expanded branch truth, generated Qt artifact bytes, deep CFG/data-flow/persistence/error paths, and complete Scintilla/Lexilla human-behavior mapping are not yet complete. The exact pinned NotepadNext bytes are still unavailable to the local scanner runtime.


### 2.11 M3C-001 NEST / Persistence / Extension / Error Closure

M3C-001 advances SCAN from structural and compiler-aware consequence mapping toward explicit effective-capability provenance. Engine v0.9 records mechanically visible guard/error/cancel/retry anatomy, typed permission/environment/status/lock effects, first-class persistence operations, dynamic extension receptors, and potential runtime capability factories while preserving the A8 distinction between environmental possibility, BODY coupling, authorization, current use, and observed runtime success.

MEASURED controlled M3C fixture:

- 2 files;
- 89 extraction nodes;
- 84 structural edges;
- 77 first-class evidence records;
- 136 canonical semantic objects;
- 327 semantic relations;
- 27 completeness dimensions;
- evidence-integrity audit: **MAPPED / 0 issues**;
- human entry denominator: 3 QAction surfaces, **2 BOUND / 1 UNRESOLVED**;
- deep consequence closure: **2 CLOSED / 0 PARTIAL / 1 UNRESOLVED**;
- NEST capability projection: 4 capability groups, 5 typed effects, 10 boundaries, 9 extension receptors, 1 `POTENTIAL` capability factory, 3 persistence objects, and 16 guard/error/retry objects.

The controlled routes exercise a settings-persistence path, a file-permission/availability check, subprocess cancellation, dynamic plugin loading/instance creation, retry-like control flow, and an exception path. The deliberate Ghost action remains UNRESOLVED. `capability-provenance`, `persistence-paths`, `guard-error-cancel`, `permission-guards`, and `extension-receptors` remain explicitly **PARTIAL** because the fixture proves mechanism coverage, not complete application semantics.

The v0.9 regression suite is **50/50 PASS**, and a clean extraction of the packaged release passes the same **50/50** suite. A v0.9 self-scan accounts for **42 files, 110 extraction nodes, 42 structural edges, 106 evidence records, 303 canonical semantic objects, and 541 semantic relations**, with **28 completeness dimensions** and **MAPPED / 0 integrity issues**. A second unchanged run reports **52 extraction-cache hits / 0 misses**.

**M3C-001 verdict: PASS FOR M3C BASELINE MECHANISM / PR2-PR4 REAL-PROJECT DEPTH STILL OPEN / NOT A NOTEPADNEXT CERTIFICATION.** Whole-program CFG/data flow, exact state-to-durable-value proof, generated Qt artifact bytes, complete platform/error semantics, and full framework-native human behavior remain calibration targets. The exact pinned NotepadNext bytes are still unavailable to the local scanner runtime.

### 2.12 PR6A Transferability Calibration TR-001

TR-001 is the first calibration-driven refinement against an unrelated real Qt specimen rather than a synthetic fixture or the NotepadNext baseline.

Exact specimen:

- repository: `tdelphi1981/BILB2000-Yazilim-Gelistirme-II-Ders-Icerigi`;
- pinned revision: `40d3a69287e8d5ebbcf0d037aa21734b181ef520`;
- scoped application: `kod_ornekleri/bolum05/unite2/03_durum_cubugu_dock.cpp`;
- provider Git blob SHA-1: `1d4e3387582dad4dd474fcb8bcb8579185c74387`;
- byte count: **6870**;
- SCAN SHA-256: `7a35457a94bfe552a54efb7ba429216dfa578e6ad79706f97c79a3c9308c3bba`.

The materialized bytes were verified by recomputing Git's canonical blob SHA before scanning. The specimen was not executed.

Cold v0.9 scan:

- 1 file;
- 72 nodes;
- 74 edges;
- 65 evidence records;
- 214 semantic objects;
- 498 semantic relations;
- 26 completeness dimensions;
- integrity **MAPPED / 0 issues**;
- human input surfaces: **0**.

The zero-surface result exposed a real transferability miss: this application constructs `QListWidget` and `QTextEdit` controls programmatically instead of through a `.ui` form, and routes the list signal into a lambda.

Reusable v0.10 corrections:

- common programmatic Qt interactive widgets become first-class human surfaces;
- connect sender identity reuses those surface objects;
- calls/effects/feedback inside common connect-lambda bodies are attributed to the lambda handler rather than only the enclosing outer function;
- explicit `setReadOnly(true)` widgets are retained as presented output surfaces instead of actionable input denominator items.

Refined v0.10 scan:

- 1 file;
- 74 nodes;
- 74 edges;
- 68 evidence records;
- 219 semantic objects;
- 504 semantic relations;
- 28 completeness dimensions;
- integrity **MAPPED / 0 issues**;
- actionable input surfaces: **2**;
- presented/read-only surfaces: **1**;
- binding closure: **1 BOUND / 1 UNRESOLVED**;
- deep effect closure: **1 CLOSED / 1 UNRESOLVED**;
- the bound QListWidget route reaches lambda-local UI effect candidates and status-bar feedback.

The read-only log QTextEdit is no longer counted as an input control. The editable central QTextEdit remains UNRESOLVED because native QTextEdit editing behavior is not yet modeled as framework-native closure. QDockWidget move/close/float chrome and child list-item affordances also remain open calibration targets.

Compiler AST coverage on this specimen is `BLOCKED` because the local runtime lacks Qt headers/build context (`QApplication` cannot be resolved). The fallback scanner remains active; the compiler gap is not hidden.

**TR-001 verdict: PASS FOR TRANSFERABILITY-DRIVEN REFINEMENT / PR6 PARTIAL.** The result demonstrates that an unrelated real specimen can expose a scanner weakness, drive a generic repair, and improve the rerun without specimen-specific naming. A larger unrelated C++/Qt application is still required before PR6 can pass.

### 2.13 PR6B Transferability Calibration TR-002

TR-002 expands transferability testing from a single Qt source file to a complete provider-visible repository tree.

Exact specimen identity:

- repository: `tashaxing/QtWuziqi`;
- pinned commit: `f4a8700699fce1b4d4a9d07e4618045c57ad3666`;
- pinned Git tree: `56bb172f66e8b22e071bf45bfa4e7d14815bd4bd`;
- provider tree entries: **12 blobs**, recursive tree `truncated=false`.

Local acquisition is deliberately hybrid because the current connector/runtime seam cannot bulk-materialize arbitrary GitHub blobs into scanner-owned storage. Exact provider-digest-verified bytes are materialized for seven text files: `GameModel.h`, `QtWuziqi.pro`, `README.md`, `main.cpp`, `mainwindow.cpp`, `mainwindow.h`, and `resource.qrc`. Five provider-visible blobs remain `PARTIAL / METADATA_ONLY`: `GameModel.cpp`, `pic/wuziqi.gif`, and three WAV resources. Those files remain in the denominator and are not parser-fed.

The materialized source establishes, among other things, two programmatically created QActions wired through legacy `SIGNAL(triggered())` / `SLOT(...)`, custom `mouseMoveEvent` and `mouseReleaseEvent` entrances, a delayed `QTimer::singleShot(kAIDelay, ..., SLOT(chessOneByAI()))` route, QMessageBox feedback, QSound playback, a qmake project declaration, and an RCC resource catalog. `GameModel.cpp` is intentionally not summarized into scanner evidence while its exact local bytes are unavailable.

Cold v0.10 result on the same verified manifest/materialized subset:

- files accounted for: **12**; materialized: **7**; metadata-only: **5**;
- 155 nodes, 145 edges, 150 evidence records;
- 466 semantic objects, 1,040 semantic relations, 28 completeness dimensions;
- integrity **MAPPED / 0 issues**;
- human surfaces: **4**;
- binding closure: **2 BOUND / 2 UNRESOLVED**;
- deep effect closure: **0 CLOSED / 2 PARTIAL / 2 UNRESOLVED**;
- both QActions unresolved because legacy SIGNAL/SLOT wiring was not represented;
- qmake and `.qrc` structure absent from the anatomical graph;
- NEST capability projection contained no typed effects from the application route.

Reusable v0.11 corrections:

- qmake build topology with conditional dependency provenance;
- Qt resource collections/assets from `.qrc`;
- legacy sender-scoped SIGNAL/SLOT event/handler wiring;
- single-shot timer delayed dispatch;
- multimedia playback effect/feedback and conservative repaint feedback;
- ordinary menu/action creation removed from extension-receptor heuristics.

Refined v0.11 result on the same verified subset:

- 12 files accounted for; 7 materialized; 5 metadata-only;
- **189 nodes, 193 edges, 162 evidence records**;
- **560 semantic objects, 1,315 semantic relations, 28 completeness dimensions**;
- integrity **MAPPED / 0 issues**;
- binding closure: **4 BOUND / 0 UNRESOLVED**;
- deep effect closure: **4 CLOSED / 0 PARTIAL / 0 UNRESOLVED** for the currently materialized input denominator;
- qmake anatomy: 1 build file, 1 target, 5 ordinary build inputs, 1 generated RCC input, 4 dependency registrations including conditional Qt Widgets;
- Qt resource anatomy: 1 resource collection and 3 declared assets;
- recurrence: 1 mapped `QTimer::singleShot` delayed-dispatch source;
- NEST/capability projection: 3 capability groups / 4 multimedia playback effects;
- false extension-receptor candidates from ordinary `addMenu`/`addAction` are removed.

The v0.11 regression suite is **57/57 PASS**, and the clean extracted release package passes the same **57/57** suite. A v0.11 self-scan accounts for **45 files, 97 nodes, 41 edges, 93 evidence records, 279 semantic objects, and 501 semantic relations**, with 28 completeness dimensions and **MAPPED / 0 integrity issues**. A second unchanged self-scan reports **55 cache hits / 0 misses**.

**TR-002 verdict at v0.11: PASS FOR SECOND TRANSFERABILITY-DRIVEN REFINEMENT / PR6 STILL PARTIAL.** This specimen exposed a distinct class of real-project misses and drove reusable repairs. Subsequent TR-002B materializes `GameModel.cpp` and supersedes the specific five-gap/GameModel-unavailable state while preserving this cold-run history.


### 2.14 PR6B2 Transferability Refinement TR-002B

TR-002B continues the same exact pinned QtWuziqi specimen after the provider blob for `GameModel.cpp` became locally available. The file is 13,124 bytes and verifies to Git blob SHA `f364fb14ddcd63864934757c8d915c52c9eeb569` before parser eligibility. Acquisition therefore becomes **8 materialized / 4 metadata-only**, with only the GIF and three WAV files still unavailable as bytes.

The first v0.11 full-text pass exposed a serious provenance defect rather than a success: Clang's JSON AST included declarations from C++/C system headers and v0.11 emitted many of them as though they were anatomy owned by `GameModel.cpp`. The graph inflated to **5,389 nodes, 3,967 edges, 5,256 evidence records, 14,665 semantic objects, and 32,276 semantic relations**. The newly visible code also exposed a fallback resolution gap at the `MainWindow::game` member and assignment-state false positives where RHS `std::pair` reads could appear as mutations named `first` or `second`.

Reusable v0.12 corrections:

- compiler definitions emitted as BODY anatomy must originate in the main translation unit; header declarations remain available internally for lookup without being misattributed to the source file;
- fallback C++ extraction records direct class data members and declared/static type;
- uniquely proven member static types may resolve cross-file receiver calls, while ambiguous matches remain findings;
- compiler state-change extraction examines only the assignment target and requires a member chain rooted in `this`.

Refined v0.12 result on the same exact verified bytes:

- 12 files accounted for; **8 materialized / 4 metadata-only**;
- **443 nodes, 474 edges, 422 evidence records**;
- **1,355 semantic objects, 3,255 semantic relations, 28 completeness dimensions**;
- integrity **MAPPED / 0 issues**;
- surface binding **4 BOUND / 0 unresolved**;
- deep effect closure **4 CLOSED / 0 partial / 0 unresolved** for the current surface denominator;
- 18 compiler-backed specimen state-change records;
- false `first` / `second` state-change records: **0**;
- pointer-event paths can now reach GameModel BODY state including `gameMapVec`, `playerFlag`, `scoreMapVec`, and `gameType` where mechanically supported;
- unchanged rerun: **28 cache hits / 0 misses**.

The reduction from 5,389 to 443 nodes is classified as a source-provenance correction, not evidence loss. External/system declarations are not part of the scanned source BODY merely because the compiler AST needs them.

The v0.12 regression suite is **60/60 PASS**, and a clean extracted package passes the same **60/60** suite. The v0.12 self-scan accounts for **45 files, 94 nodes, 41 edges, 90 evidence records, 273 semantic objects, and 492 semantic relations**, with 28 completeness dimensions and **MAPPED / 0 integrity issues**. A second unchanged self-scan reports **55 cache hits / 0 misses**.

**TR-002B verdict: PASS FOR PROVENANCE AND CROSS-FILE STATE-CLOSURE REFINEMENT / PR6 STILL PARTIAL.** Four binary blobs remain acquisition gaps, full Qt compiler/build context is still incomplete, this specimen remains modest in scale, and M4 NotepadNext calibration remains externally blocked.

### 2.15 PR6C qView Development Oracle O-003 and v0.13 Refinement

qView (`jurplel/qView@c5eca1c7176549e0f0718d11201547ddcdb1f8c9`) was selected as a substantially larger unfamiliar C++/Qt specimen. Exact source inspection in this chat occurred before a complete local cold SCAN could be executed, so qView is now classified as a **development oracle**, not as the final blind PR6 holdout. This preserves scientific honesty: qView may drive generic scanner improvements, but it cannot later be presented as an untouched transferability exam.

The oracle exposed several generic requirements: semantic QAction identity must remain separate from physical clones; `QAction::data()` payloads may select behavior through keyed dispatch; Recent/Open-With style indexed controls form bounded dynamic families; registry actions with no recovered keyed route must remain visible; duplicate keyed branches are static anomalies; and build definitions may contain directly contradictory feature-state evidence.

Engine v0.13 implements those classes generically. A scanner-owned three-file fixture recovered `semantic_action` identities, a cloned `surface_instance`, a bounded `dynamic_surface_family`, keyed equality/prefix `dispatch_case` objects, an orphan semantic-action candidate, a duplicate-dispatch anomaly, and a CMake build-condition contradiction. The fixture measured **3 files, 49 nodes, 35 edges, 46 evidence records, 138 semantic objects, 290 semantic relations, 27 completeness dimensions**, with **MAPPED / 0 integrity issues**.

The complete v0.13 suite is **66/66 PASS** in both the development tree and a clean extracted package. The package manifest has 45 tracked payload files and verifies with zero digest/length mismatches. The v0.13 self-scan accounts for **46 files, 94 nodes, 41 edges, 90 evidence records, 274 semantic objects, and 493 semantic relations**, with 28 completeness dimensions and **MAPPED / 0 integrity issues**. An unchanged second self-scan reports **56 cache hits / 0 misses**.

**O-003 verdict: PASS FOR v0.13 SEMANTIC-ACTION / BUILD-CONTRADICTION MECHANISMS / PR6 STILL PARTIAL.** Production certification now requires a separate frozen large C++/Qt holdout that has not been manually analyzed before the candidate scan.

### 2.16 PR6 Holdout H-001 Reservation (Project Certification State; not NotepadNext evidence)

Project v0.20 reserves DB Browser for SQLite (`sqlitebrowser/sqlitebrowser`) as the final PR6 blind holdout at commit `4a7359d5c349ca0bc446f94922ec9561fcf50b96`, tree `1ad501f60616ebd644a7e86a92fb9d22666b3e2c`. Only repository/commit/tree metadata were inspected before freeze. No source-level oracle, expected action denominator, capability inventory, or behavior map has been authored.

H-001 must remain source-uninspected by the human/LLM calibration process until the v1 candidate scanner is frozen and its cold scan artifacts are sealed. The candidate's mechanical scanner may read the pinned source during that cold scan. This reservation prevents qView's development-oracle role from contaminating the final transferability certificate.

This section records SCAN project certification state only. It contributes no NotepadNext specimen coverage.

### 2.17 PR1A Byte-Boundary Hardening RH-001 (Project Engine State; not NotepadNext evidence)

SCAN Engine v0.14 hardens local/provider byte admission without changing the NotepadNext specimen claims. Symlink roots are rejected; internal symlink and special entries are ledgered but not parsed; local bytes are identity/digest checked between census and extraction; manifest traversal/symlink materialization is blocked; and configurable per-item resource ceilings create explicit `RESOURCE_LIMIT` gaps instead of silent omission. GitHub provider blobs above the configured bound are rejected before fetch.

Regression status: **72/72 PASS** in development and clean-package runs. Package `SCAN_ENGINE_v0.14.zip` SHA-256 is `5ba2990d5dd2b1330232f31b451c49ffd956e4791412cc931d831db0c04c1342`. v0.14 self-scan reports **47 files, 94 nodes, 41 edges, 90 evidence records, 275 semantic objects, 494 semantic relations, 28 completeness dimensions, MAPPED / 0 issues**, and an unchanged rerun gives **57 cache hits / 0 misses**.

**RH-001 verdict: PASS FOR FIRST PR1 HARDENING SLICE / PR1 AND PR8 REMAIN PARTIAL.** This section is project-engine evidence only and contributes no NotepadNext coverage.

---

## 3. Initial Whole-Body Census

DIRECT evidence establishes that the project contains a native C++/Qt application structure with CMake build files.

Observed source/artifact families include:

- C++ source and headers
- Qt application code
- CMake build definitions
- deployment material for Linux, macOS, and Windows
- translations
- resources
- documentation
- bundled Windows libraries
- editor-related code
- Lua-related integration
- Scintilla/Lexilla-related integration

Representative observed source files include:

- `src/main.cpp`
- `src/NotepadNextApplication.cpp`
- `src/ApplicationSettings.cpp`
- `src/ApplicationSettings.h`
- `src/EditorManager.cpp`
- `src/dialogs/MainWindow.cpp`
- `src/TranslationManager.cpp`
- `src/ColorPickerDelegate.cpp`
- `src/widgets/TabsQuickActionsBar.cpp`

These examples are not a complete body inventory.

Coverage classification for the unexamined repository remainder: UNKNOWN pending deterministic census.

---

## 4. Entry and Lifecycle Anatomy

### 4.1 Primary entry point

DIRECT: `src/main.cpp` contains `int main(int argc, char *argv[])`.

The entry sequence observed there:

1. Configures Qt message formatting.
2. Sets organization/application identity.
3. Sets the default `QSettings` format to INI.
4. Constructs `NotepadNextApplication`.
5. Checks whether the process is the primary application instance.
6. Primary instance calls `app.init()`.
7. Primary instance enters `app.exec()`.
8. Secondary instance sends information to the primary instance.
9. Secondary instance exits.

### 4.2 Biological interpretation

INFERRED: the primary-instance path is a strong candidate for the organism's core lifecycle trunk.

`main()` is not itself the entire "heart". It appears to establish and enter the framework-managed Qt event circulation through `app.exec()`.

The event loop should be treated as a major artery candidate until the complete graph confirms how application events branch through the rest of the body.

### 4.3 Secondary-instance pathway

DIRECT evidence from `main.cpp` and `NotepadNextApplication.cpp` shows a secondary process can package its arguments, send them to the primary instance, and close.

The primary application has a receiver path:

`SingleApplication::receivedMessage`
-> `NotepadNextApplication::receiveInfoFromSecondaryInstance`
-> parse received command-line arguments
-> `openFiles(...)`

INFERRED biological interpretation: this is a distinct inter-process sensory/input pathway feeding work into the already-running primary organism.

---

## 4.4 Reconstructed lifecycle state model

The following is a static reconstruction from implementation evidence. It is not a runtime trace.

### L0: Process birth

`main()` configures application identity and settings defaults, then constructs `NotepadNextApplication`.

Transition splits on whether this process is the primary instance.

### L1A: Primary initialization

DIRECT evidence in `NotepadNextApplication::init()` shows the primary path initializes application settings, translation management, Lua state, recent-file management, editor management, session management, application decorators, the main window, focus/application-state wiring, and secondary-instance message handling.

It also executes the resource script `:/scripts/init.lua` and initializes `LuaExtension`.

### L1B: Secondary forwarding

A secondary instance serializes its arguments, sends them to the primary through the single-application message channel, and exits. The primary decodes those arguments and routes positional files into `openFiles(...)`.

### L2: Restore and startup inputs

If configured to restore the previous session, `SessionManager::loadSession(window)` runs during initialization.

Command-line positional files are then opened. If `-n` is supplied for the first file, the application attempts to position that editor at the requested line.

If no editor exists after startup inputs/session restoration, `window->newFile()` creates an empty document.

The window restores its saved state, optionally opens a workspace from `--workspace`, then is shown.

### L3: Steady-state event circulation

After `init()` returns, `main()` enters `app.exec()`. The Qt event loop becomes the principal recurring control circulation.

`MainWindow` connects a broad GUI action surface into document/editor handlers, including new, open, reload, close, exit, save, save-as, save-all, rename, editor transformations, recent files, workspace operations, and many direct Scintilla actions.

### L4: Editor birth and management

`EditorManager::createEditor(...)` or `createEditorFromFile(...)` creates a `ScintillaNext` buffer, passes it through `manageEditor(...)`, performs editor setup/decorator attachment, and emits `editorCreated`.

The manager also propagates settings changes across existing editors, making settings-to-editor fan-out a persistent regulatory pathway.

### L5: Document mutation and save

A save action reaches the current editor through MainWindow save handlers. `ScintillaNext::save()` emits `aboutToSave`, writes current buffer bytes to the file path, updates the timestamp, establishes a save point, clears temporary status, and emits `saved` on success.

`saveAs(...)` follows a comparable path but can assign a new file identity and emit `renamed`.

### L6: Periodic session checkpoint

DIRECT evidence shows `QTimer::timeout` is connected to `NotepadNextApplication::saveSession`, and the timer is started with `60 * 1000` milliseconds.

This produces a recurring one-minute checkpoint pathway. `saveSession()` updates recent-file state, saves application settings, then delegates the session body to `SessionManager::saveSession(window)`.

`SessionManager` clears prior session storage, classifies editor buffers as saved files, unsaved files, temporary files, or none, and stores enabled classes plus the current editor index. Unsaved and temporary buffer contents may be copied into the application session directory.

### L7: Close gate

`MainWindow::closeEvent(...)` asks `SessionManager` which editors will be preserved in the session. Editors not covered by session persistence are sent through `checkEditorsBeforeClose(...)`.

If that check fails, the close event is ignored and shutdown is cancelled. If it succeeds, `MainWindow` emits `aboutToClose()` and accepts the close event.

The exact user-dialog behavior inside all close branches remains PARTIAL in this working scan.

### L8: Shutdown persistence

`MainWindow::aboutToClose` is connected to both MainWindow settings persistence and `NotepadNextApplication::saveSession`. Application-level `aboutToQuit` is connected to `NotepadNextApplication::saveSettings`.

This creates overlapping shutdown checkpoint paths before process death.

### L9: Restart / restoration

`SessionManager::loadSession(...)` reads stored session entries and reconstructs supported saved-file, unsaved-file, and temporary-buffer editors. It also restores current-editor selection and view details such as first visible line, caret position, and bookmarks where recorded.

This closes the lifecycle loop: runtime editor state can be transformed into durable session state and later reconstructed into live editor state.

---

## 4.5 Static lifecycle test matrix

| Test | Stimulus | Expected static pathway | Current evidence state |
|---|---|---|---|
| LT-01 | Cold start, no prior session, no files | `main -> init -> no editors -> newFile -> show -> exec` | PARTIAL/DIRECT |
| LT-02 | Cold start with file arguments | parser -> `openFiles` -> `MainWindow::openFile`/open-list path -> editor | PARTIAL |
| LT-03 | Secondary instance while primary exists | serialize args -> sendMessage -> `receivedMessage` -> decode -> `openFiles` -> secondary exits | DIRECT |
| LT-04 | Previous session enabled | `init -> loadSession` -> rebuild supported editors -> restore active editor/view state | DIRECT |
| LT-05 | One minute elapses in steady state | `QTimer::timeout -> saveSession -> SessionManager::saveSession` | DIRECT |
| LT-06 | New buffer edited then saved | GUI save action -> MainWindow save path -> `ScintillaNext::save/saveAs` -> disk write -> save point | PARTIAL/DIRECT |
| LT-07 | Close with non-session-covered unsaved editor | `closeEvent -> checkEditorsBeforeClose`; rejection cancels close | DIRECT for gate, PARTIAL for dialogs |
| LT-08 | Normal close | close gate succeeds -> `aboutToClose` -> session/window settings save -> close accepted -> `aboutToQuit` settings path | DIRECT/PARTIAL ordering |
| LT-09 | Restart after stored session | startup -> `loadSession` -> restore saved/unsaved/temp buffers and view metadata | DIRECT |
| LT-10 | macOS file-open event | application `event(QEvent::FileOpen)` -> `openFiles` | DIRECT |

These tests are currently **static simulations**: graph/path assertions against code evidence. Runtime success, timing, UI presentation, operating-system integration, and error behavior are not yet measured.

---

## 5. Initial Circulatory Map

The following arteries are **candidates**, not yet a complete artery census.

### ARTERY-CANDIDATE A-001: Qt application event circulation

Origin/root:
- `main()`
- primary `NotepadNextApplication`

Key transition:
- `app.init()`
- `app.exec()`

Carries:
- framework events
- application events
- GUI event dispatch
- lifecycle notifications

Evidence:
- DIRECT source evidence in `src/main.cpp`
- Qt event wiring visible in `src/NotepadNextApplication.cpp`

Confidence:
- HIGH that this is a major control artery
- UNKNOWN complete downstream coverage

Potential nerve-access candidates:
- immediately before `app.exec()`
- application-level `event(QEvent*)`
- central signal/slot dispatch seams
- application state change connection

No nerve has been inserted.

---

### ARTERY-CANDIDATE A-002: Secondary-instance message artery

Origin:
- secondary NotepadNext process

Observed route:
- `sendInfoToPrimaryInstance()`
- `sendMessage(buffer)`
- `SingleApplication::receivedMessage`
- `receiveInfoFromSecondaryInstance(...)`
- `openFiles(...)`
- main-window file-open path

Carries:
- command-line argument information
- file-open requests

Evidence:
- DIRECT source evidence in `src/main.cpp`
- DIRECT source evidence in `src/NotepadNextApplication.cpp`

Potential nerve-access candidates:
- `sendInfoToPrimaryInstance()`
- `receivedMessage` signal boundary
- `receiveInfoFromSecondaryInstance(...)`
- `openFiles(...)`

Diagnostic value:
- HIGH for observing work entering an existing primary instance

---

### ARTERY-CANDIDATE A-003: Editor creation/closure -> recent-file state

DIRECT source connections observed during application initialization:

`EditorManager::editorCreated`
-> recent-file list update logic

`EditorManager::editorClosed`
-> recent-file list update logic

Carries:
- editor lifecycle state
- recent-file membership changes

Potential nerve-access candidates:
- `EditorManager::editorCreated`
- `EditorManager::editorClosed`
- recent-file manager mutations

Status:
- pathway observed
- larger persistence relationship not yet fully mapped

---

### ARTERY-CANDIDATE A-004: Shutdown persistence

DIRECT:

`NotepadNextApplication::aboutToQuit`
-> `NotepadNextApplication::saveSettings`

Also observed:
`saveSession()` iterates opened editors, updates recent files, saves settings, and calls the session manager to save the session.

INFERRED:
This is likely part of a persistence artery carrying live editor/application state toward durable state.

Complete persistence graph: UNKNOWN.

---

### ARTERY-CANDIDATE A-005: Periodic session-checkpoint artery

Origin:
- `QTimer autoSaveTimer`

Observed route:
- `QTimer::timeout`
- `NotepadNextApplication::saveSession()`
- recent-file update
- application settings save
- `SessionManager::saveSession(window)`
- settings/session-directory persistence

Recurrence:
- timer started at `60 * 1000` milliseconds

Carries:
- editor/session state toward durable recovery state

Potential nerve-access candidates:
- timer timeout seam
- `NotepadNextApplication::saveSession()`
- `SessionManager::saveSession(...)`
- per-editor session classification
- session storage writes

Status:
- DIRECT pathway evidence
- runtime timing not measured

Additional recurrence evidence: `URLFinder` owns a 200 ms single-shot `QTimer` that is repeatedly started by editor resize, reload, vertical-scroll, text-modification, and zoom events, then calls `findURLs()`. This is not a global heartbeat, but it is a recurring event-driven micro-loop and is a useful scanner test for debounce-style physiology. MainWindow also contains a delayed startup update-check timer.

---

## 6. Initial Nerve-Access Map

These are observation candidates only.

| Nerve Candidate | Artery | Source seam | Possible observation | Status |
|---|---|---|---|---|
| N-001 | A-001 | `NotepadNextApplication::event(QEvent*)` | application-level incoming event types | candidate |
| N-002 | A-001 | `applicationStateChanged` connection | foreground/background application state | candidate |
| N-003 | A-002 | `SingleApplication::receivedMessage` connection | secondary-instance arrivals | candidate |
| N-004 | A-002 | `receiveInfoFromSecondaryInstance(...)` | decoded secondary arguments | candidate |
| N-005 | A-002 | `openFiles(...)` | requested files entering window-open path | candidate |
| N-006 | A-003 | `EditorManager::editorCreated` | editor creation | candidate |
| N-007 | A-003 | `EditorManager::editorClosed` | editor closure | candidate |
| N-008 | A-004 | `aboutToQuit -> saveSettings` | persistence transition at shutdown | candidate |
| N-009 | A-005 | `QTimer::timeout` | periodic checkpoint trigger | candidate |
| N-010 | A-005 | `SessionManager::saveSession(...)` | session classification and persistence activity | candidate |
| N-011 | document-save artery | `ScintillaNext::aboutToSave/saved` | document-save boundary and outcome | candidate |

No candidate above has been instrumented or runtime-verified.

---

## 7. Sensory / Input Surfaces Observed So Far

DIRECT:

`NotepadNextApplication` parses command-line inputs including:

- positional files
- `--translation`
- `--reset-settings`
- `-n` line number
- `--workspace`

DIRECT:

On macOS-style file-open events, `NotepadNextApplication::event(QEvent*)` handles `QEvent::FileOpen` and routes the file into `openFiles(...)`.

DIRECT:

Secondary application instances can transmit their arguments to the primary instance.

GUI control surface coverage remains UNKNOWN pending complete `.ui`, QAction, signal/slot, and MainWindow mapping.

---

## 8. State and Persistence Structures Observed So Far

DIRECT source evidence identifies:

- `ApplicationSettings`
- `RecentFilesListManager`
- `EditorManager`
- `SessionManager`

Observed initialization establishes these as long-lived application-level structures.

DIRECT:

Application settings use Qt settings infrastructure.

DIRECT:

The application can reset settings, back up the prior settings file, and clear settings when the command-line reset option is supplied.

DIRECT:

The application can restore a previous session depending on settings.

DIRECT:

Recent file state is loaded and saved through application settings.

Full durable-state anatomy: PARTIAL.

---

## 9. Embedded Language / Extension Anatomy

DIRECT:

`NotepadNextApplication::init()` constructs a `LuaState`, executes `:/scripts/init.lua`, and initializes `LuaExtension`.

DIRECT:

Language-related operations query or execute Lua logic, including:

- dialog filters
- language lists
- language setup
- language keywords
- language detection by extension
- language detection by contents

INFERRED:

Lua is not merely incidental data. It participates in application behavior related to editor/language configuration.

This is an important subsystem for the later full scan because meaningful behavior may exist in Lua resources even when a C++-only scanner would miss it.

Coverage of Lua scripts and C++/Lua call relationships: UNKNOWN.

---

## 10. GUI / Event Anatomy Observed So Far

DIRECT repository search evidence shows `src/dialogs/MainWindow.cpp` contains Qt `connect(...)` wiring from `QAction::triggered` signals into handlers/lambdas.

One observed example connects a "copy full path" action to code that reads the current editor file path and places text on the application clipboard.

INFERRED:

The MainWindow signal/slot graph is likely one of the richest circulatory regions in the application.

A complete SCAN should parse all Qt Designer actions, `.ui` files, direct `connect(...)` calls, helper wiring, shortcuts, menus, toolbars, and their downstream editor operations.

DIRECT evidence in `MainWindow.h` shows that `connectEditorAction(...)` template helpers convert `QAction::triggered` events into calls on the current `ScintillaNext` editor. Many editing commands are wired through this abstraction. Therefore a scanner that recognizes only literal `connect(...)` edges in `.cpp` files would systematically under-map the GUI motor pathways.

Current GUI artery map: PARTIAL.

---

## 10.1 Human Interaction Map: first mapped pathways

Status: PARTIAL. This is not yet a complete user-surface census.

The current source evidence establishes that NotepadNext exposes multiple human control surfaces and that several distinct surfaces converge on shared semantic behaviors. SCAN must preserve both the individual human entrances and the internal behavior they reach.

### HIM-B001: SAVE CURRENT DOCUMENT

Human-facing entrance currently established:

`MainWindow -> File/Save QAction -> QAction::triggered -> MainWindow::saveCurrentFile() -> MainWindow::saveFile(currentEditor())`

If the current editor is not yet a file, the route diverts into the Save As dialog. If it is a file and needs saving, the path reaches `ScintillaNext::save()`, which emits `aboutToSave`, writes the current buffer, updates timestamp/save-point state, clears temporary status when appropriate, and emits `saved` on success.

Surface evidence: DIRECT.
Internal save path: DIRECT.
Exact menu placement, shortcut, icon, and all alternate Save entrances: PARTIAL until `.ui` and shortcut resources are completely mapped.

Candidate sensory nerves:

- QAction trigger boundary,
- `MainWindow::saveCurrentFile`,
- `ScintillaNext::aboutToSave`,
- disk-write boundary,
- `ScintillaNext::saved`,
- dirty/save-enabled UI transition.

Candidate motor nerves for a future separately authorized control mode:

- semantic QAction trigger,
- `MainWindow::saveCurrentFile` command boundary.

No motor nerve has been invoked.

### HIM-B002: CREATE NEW DOCUMENT

DIRECT source evidence maps `ui->actionNew` through `QAction::triggered` into `MainWindow::newFile()`. `newFile()` obtains a new editor from `EditorManager::createEditor(...)`; `EditorManager::manageEditor(...)` configures and registers that `ScintillaNext` instance and emits `editorCreated`.

This demonstrates a complete-enough initial human-surface-to-editor-birth pathway for static mapping. Exact shortcut/icon placement remains to be inventoried.

### HIM-B003: OPEN DOCUMENT

Multiple entrances are already visible:

- File/Open QAction -> `MainWindow::openFileDialog()` -> selected files -> `openFileList(...)`,
- recent-file menu request -> `MainWindow::openFile(...)`,
- Folder-as-Workspace double-click -> `MainWindow::openFile(...)`,
- command-line positional file -> application `openFiles(...)` -> `MainWindow::openFile(...)`,
- secondary-process message -> decoded positional arguments -> `openFiles(...)`,
- operating-system file-open event -> `openFiles(...)`.

These routes converge on document-open behavior and should be grouped under one semantic behavior while retaining their distinct surface origins. The open path checks whether a file is already represented by an editor, can ask the user whether to create a missing file, and otherwise obtains a file-backed editor through `EditorManager::createEditorFromFile(...)`.

This is the first clear example of **behavioral equivalence across heterogeneous human surfaces**.

### HIM-B004: EDITOR COMMAND DISPATCH

NotepadNext uses `MainWindow::connectEditorAction(...)` template helpers to connect many `QAction::triggered` inputs to methods on the currently active `ScintillaNext` editor. Examples observed include undo, redo, cut, copy, paste, select-all, case conversion, indentation, duplicate/move lines, folding, and other editor operations.

This is a critical scanner test. A parser that recognizes only literal direct Qt `connect(...)` patterns will under-map the user interface because the helper itself creates a family of human-action-to-editor-method edges. SCAN must resolve these helper-mediated edges and preserve the concrete action/method pair for each instantiation.

### HIM-B005: EXIT / CLOSE APPLICATION

DIRECT: the Exit QAction routes to `MainWindow::close()`. `MainWindow::closeEvent(...)` checks editors that will not be protected by session persistence. If unsaved state requires intervention, the close operation can be rejected. Only after the close gate succeeds does the window emit `aboutToClose`, feeding persistence/shutdown behavior.

This means the human action EXIT is not merely a call to terminate. Its semantic behavior includes a guard, possible user decision/cancellation, persistence, and eventual shutdown. Those branches belong in the Human Interaction Map.

### Human-surface coverage still UNKNOWN

The scan has not yet enumerated every `.ui` action, menu hierarchy, toolbar, context menu, custom shortcut, dialog control, dock action, drag/drop behavior, mouse gesture, editor notification, platform-specific control, accessibility route, or dynamically constructed action. No claim of complete human-interface coverage is made.

---

## 10.2 Human Surface Census Pass 1

Status: **PARTIAL / SUBSTANTIAL STATIC COVERAGE**

This pass deliberately widened the scan from named application functions to the surfaces a human can actually touch. The main finding is that NotepadNext does not have a single GUI surface. Its human interface is a layered control system containing declarative Qt Designer surfaces, programmatically created controls, dynamically populated menus, editor-native gestures, keyboard-only routes, context menus, command-line entrances, operating-system events, and hidden diagnostic/developer surfaces.

### 10.2.1 Measured surface anatomy

CORRECTED DIRECT CENSUS from the complete pinned `MainWindow.ui`:

- **139 explicit `QAction` objects** are declared in the main window UI definition.
- The earlier Pass 1 count of 70 was produced from partial inspection and is withdrawn. This correction is itself a useful SCAN result: broad discovery can undercount a surface even when the source looks familiar, so closure must be driven from a complete declaration ledger rather than spot checks.
- 9 top-level menu families are present: File, Edit, Search, View, Encoding, Language, Settings, Macro, and Help.
- 22 action placements are present on the main toolbar.
- the main window accepts drag/drop input.
- a dedicated `pushExitFullScreen` button exists in addition to the normal fullscreen action.

DIRECT repository census evidence currently identifies at least 15 Qt `.ui` definitions across the examined application-facing `dialogs`, `docks`, and `widgets` regions. These include the main window, Find/Replace, Preferences, Column Mode, three macro dialogs, Quick Find, and seven dock surfaces. This count is a current visible-region census, not yet a repository-wide proof that no other UI description exists.

### 10.2.2 Main semantic action families

The main-window action surface currently resolves into these user capability families:

**File/document lifecycle:** New, Open, Open Folder as Workspace, Reload, Save, Save As, Save Copy As, Save All, export HTML/RTF, Rename, Close, Close All, Close Except Active, Close Left, Close Right, Move to Trash, Print, Recent Files operations, and Exit.

**Editing and transformation:** Undo/Redo, Cut/Copy/Paste/Delete, Select All/Next, path/name/directory copy, HTML/RTF copy, indentation, case conversion, EOL conversion, line duplication/splitting/joining/movement/removal/sorting, comments, Base64 and URL transforms, and Column Mode.

**Search/navigation/marking:** Find, Find Next/Previous, selected-text searches, Replace, Quick Find, Go to Line, search-and-bookmark, mark styles, bookmarks, bookmark navigation, and bookmark-based cut/copy/delete.

**View/editor presentation:** Fullscreen, whitespace/EOL/all-character/indent-guide/wrap-symbol toggles, Word Wrap, zoom, folding/unfolding by level, split editor views, tab navigation, and overtype mode.

**Settings/language/macro/help:** Preferences, dynamically generated language selection, macro recording/playback/save/run/edit plus dynamic saved macros, update checking, About surfaces, Debug Info, and dynamically inserted diagnostic dock toggles.

The Encoding menu currently contains a disabled placeholder indicating that the feature is not implemented. SCAN must preserve this as a **visible but non-actionable surface state**, rather than pretending that every displayed menu item is an executable capability.

### 10.2.3 Dynamic surfaces that a static `.ui` parser alone would miss

DIRECT source evidence identifies several surfaces constructed or mutated after `setupUi()`:

1. **Recent Files menu.** It is rebuilt when opened; file entries are generated from current recent-file state and emit a file-open request into `MainWindow::openFile()`.
2. **Language menu.** Language names come from the application's Lua-backed language registry. `MainWindow::setupLanguageMenu()` creates checkable `QAction` objects at runtime, groups them alphabetically, and routes them through `languageMenuTriggered()`.
3. **Macro menu.** Saved macros are appended dynamically whenever the Macro menu is opened, and selecting a generated entry replays that macro on the current editor.
4. **Opened-tabs menu.** `TabsQuickActionsBar` creates a popup whose entries are rebuilt from the current editor list and route selection into `switchToEditor()`.
5. **Dock visibility actions.** Search Results, Folder as Workspace, File List, Lua Console, Language Inspector, Editor Inspector, and Debug Log surfaces are added to menus programmatically through dock `toggleViewAction()` objects.
6. **User-defined shortcuts.** `applyCustomShortcuts()` reads the `Shortcuts` settings group and can replace the static shortcut set of matching actions at runtime.
7. **Platform-specific surfaces.** Windows builds expose Show in Explorer and Open Terminal Here behavior and assign `Alt+F4` to Exit; other platforms use the framework Quit sequence.

This establishes a scanner rule through evidence: **surface discovery must combine UI-definition parsing with constructor/event-wiring analysis and state-dependent dynamic action discovery.**

### 10.2.4 Non-menu gestures and direct-manipulation surfaces

DIRECT evidence currently maps these human routes outside ordinary menu clicks:

- editor tabs have close buttons;
- middle mouse can close a tab;
- tab dragging/reordering is enabled by the docking framework;
- a tab's custom context menu routes into `MainWindow::tabBarRightClicked(...)`;
- double-clicking a docked-editor title bar emits a new-document request;
- the main window accepts drag/drop input;
- the editor itself exposes a custom context menu whose behavior depends on the clicked caret/selection position;
- the status bar's EOL label exposes a custom context menu that opens the EOL conversion menu;
- search-result activation jumps to the corresponding editor/range;
- workspace-tree double-click opens a file;
- File List item click switches the active editor;
- Quick Find responds to text entry, Return, Shift+Return, Escape, focus changes, and toggle buttons;
- the Lua Console responds to Return to execute, Up/Down for history, and Escape to clear its input/history position.

These routes demonstrate why a human-surface scanner must examine event filters, framework configuration, item-activation signals, and mouse/keyboard handlers in addition to QAction wiring.

### 10.2.5 Dialog surfaces discovered

**Find/Replace** exposes editable Find/Replace inputs, Normal/Extended/Regular Expression search modes, regex-newline control, transparency controls, and direct commands including Find, Count, Replace, Replace All, Replace All in Opened Documents, Find All in Opened Documents, Find All in Current Document, Mark All, Clear Marks, Copy Marked Text, and Close.

**Preferences** exposes controls for menu/toolbar/status visibility, session restoration and sub-options, search-result behavior, translation, exit-on-last-tab behavior, font and size, default line endings, URL highlighting, line numbers, auto-completion, and default-directory policy. This surface modifies the conditions under which future user actions and lifecycle behavior occur, so it belongs in both the Human Interaction Map and the regulation/state map.

**Column Mode** exposes text insertion and numeric-sequence configuration with Start and Step values plus OK/Cancel.

**Macro Run** exposes macro selection, run-to-end-of-file versus fixed repetition, a count from 1 to 999,999,999, Run, and Cancel.

**Macro Save** exposes a macro name and a shortcut editor. The OK action begins disabled and the dialog can accept/reject.

**Macro Editor** exposes macro selection, name and shortcut editing, macro-step inspection and manipulation, copy/delete macro controls, and insert/delete/reorder step controls.

### 10.2.6 Dock and diagnostic surfaces

**Folder as Workspace** exposes a filesystem tree, double-click-to-open, and a gear menu controlling Size, Type, Date Modified, and Hidden-file visibility. The visibility choices are persisted through settings.

**File List** exposes the current editor population as selectable rows, a settings menu for sorting by file name, and saved/unsaved visual state through icons. Selecting a row switches the active editor.

**Search Results** exposes a result tree, result activation, Copy All, Escape-to-close, and a dynamically constructed context menu with Copy, Collapse All, Expand All, Delete Entry, and Delete All.

**Editor Inspector** is primarily afferent: it displays live position, selection, document, view, and fold state and refreshes from editor UI events. Its tree is not directly editable in the examined UI.

**Language Inspector** exposes lexer/language/property/keyword/style information. The exact mutability of every property/style cell remains PARTIAL until its implementation file is fully traced.

**Debug Log** exposes a selectable, read-only rolling text surface capped at 1000 blocks in the UI definition.

**Lua Console** is a high-leverage efferent surface. It creates a writable Scintilla input, executes the entered text through `LuaExtension::Instance().OnExecute(...)` when Return is pressed, displays output/errors, and provides command history. This means a faithful human-surface map must include developer/diagnostic interfaces even when they are hidden by default.

### 10.2.7 Surface-to-behavior map, current high-value sample

| Surface ID | Human route | Semantic behavior | Entry/event seam | Internal destination/effect | Afferent nerve candidate | Efferent nerve candidate | Coverage |
|---|---|---|---|---|---|---|---|
| HS-001 | File -> Save / Save shortcut / toolbar Save | SAVE CURRENT DOCUMENT | `QAction::triggered` | `saveCurrentFile()` -> `saveFile()` -> editor save or Save As branch | QAction trigger, `aboutToSave`, `saved`, dirty-state signal | semantic Save action / `saveCurrentFile()` | PARTIAL alternate-route enumeration |
| HS-002 | File -> New / toolbar New / tab + button / title-bar double click | CREATE NEW DOCUMENT | QAction or direct gesture signal | `MainWindow::newFile()` -> `EditorManager::createEditor()` | `editorCreated` | `newFile()` semantic boundary | SUBSTANTIAL |
| HS-003 | File -> Open / recent file / workspace double-click / CLI / secondary instance / OS file-open | OPEN DOCUMENT | heterogeneous surface events | `openFile()` / `openFiles()` -> `openFileList()` -> editor creation or existing editor activation | file-open request, editor-created/activated | semantic `openFile(...)` boundary | SUBSTANTIAL |
| HS-004 | Quick Find UI | QUICK FIND / NAVIGATE MATCHES | textChanged, toggles, Return/Shift+Return, Escape | Finder search, selection movement, highlight rendering | match count/highlight/selection state | QuickFind semantic input handlers | SUBSTANTIAL |
| HS-005 | Preferences | CHANGE APPLICATION REGULATION | checkbox/combo/font/path inputs | `ApplicationSettings` mutations alter future UI/lifecycle/editor behavior | settings-changed signals + visible control state | setting setter/action seam | PARTIAL handler trace |
| HS-006 | Search Results item activation | NAVIGATE TO SEARCH RESULT | `QTreeWidget::itemActivated` | emits `searchResultActivated`; MainWindow activates editor and range | selection/editor activation | result activation semantic seam | SUBSTANTIAL |
| HS-007 | Workspace tree double-click | OPEN DOCUMENT FROM WORKSPACE | `QTreeView::doubleClicked` | emits `fileDoubleClicked` -> `MainWindow::openFile` | fileDoubleClicked/open path | workspace item activation | SUBSTANTIAL |
| HS-008 | File List row click | SWITCH ACTIVE DOCUMENT | `QListWidget::itemClicked` | `DockedEditor::switchToEditor` | `editorActivated` and selection state | item-click/switch boundary | SUBSTANTIAL |
| HS-009 | Macro menu/dialogs | RECORD / REPLAY / MANAGE MACROS | QAction, generated menu action, dialog execute | MacroManager/Macro replay and editing | recording state/action enablement | macro semantic commands | PARTIAL |
| HS-010 | Help -> Lua Console then type + Return | EXECUTE LUA CONSOLE COMMAND | input key event Return | `runCurrentCommand()` -> `LuaExtension::Instance().OnExecute(...)` | console output/error stream | console command execution boundary | SUBSTANTIAL static trace |
| HS-011 | Tab close button / middle-click / File Close | CLOSE DOCUMENT | framework close request or QAction | close guard -> editor close -> create blank/exit branch | close request, editorClosed, prompt state | close semantic boundary | SUBSTANTIAL |
| HS-012 | Search Results context menu | MANAGE SEARCH RESULT SET | generated context-menu actions | copy/collapse/expand/delete entry/delete all | tree state/clipboard | generated QAction handlers | SUBSTANTIAL |

This table is intentionally a **behavior graph sample**, not yet the final exhaustive surface registry. The machine Body Map should ultimately contain one record for every discovered surface and link equivalent routes to a canonical semantic behavior ID.

### 10.2.8 Surface/implementation mismatch discovered

DIRECT source evidence exposes a useful anomaly in the macro workflow: `MacroSaveDialog` presents a `QKeySequenceEdit` field labeled Shortcut, and the calling MainWindow code reads `getShortcut()`, but the implementation currently contains a TODO rather than actually assigning the shortcut to the saved macro.

SCAN should preserve this as three separate truths:

- the user surface **offers** shortcut entry;
- the implementation **reads/detects** the entered shortcut;
- the examined path does **not complete** shortcut application.

This is precisely the kind of discrepancy that would disappear if SCAN inferred application behavior from interface labels alone.

### 10.2.9 Candidate nerve topology emerging from the surface census

The human surface layer reveals recurring high-information seams that could later support generic nerves:

- QAction/QShortcut trigger boundaries for discrete commands;
- `QDialog` acceptance/rejection and direct control signals for modal/non-modal workflows;
- `ApplicationSettings` changed signals for regulatory state;
- DockedEditor editor-added/activated/closed/order-changed signals for document topology;
- ScintillaNext save-point/update/selection/editor-notification seams for editor physiology;
- dynamic-menu population boundaries for state-dependent affordances;
- filesystem tree/list item activation seams for document selection;
- command-line, OS file-open, and secondary-instance message boundaries for non-GUI entrances;
- Lua Console command execution and output seams for the hidden developer control surface.

INFERRED: these recurring event boundaries may eventually allow SCAN to produce a framework-aware nerve template for Qt applications without hard-coding NotepadNext-specific function names.

### 10.2.10 Coverage conclusion for Pass 1

The scan can now demonstrate that a useful user-surface map must represent at least five dimensions simultaneously:

`surface identity -> reachability/conditions -> semantic action -> internal pathway/effect -> feedback/observation seam`

The static census is now strong enough to reveal ordinary GUI controls, equivalent entrances, dynamic menus, hidden docks, gestures, keyboard routes, and several context menus. It is **not complete**. Remaining major gaps include exhaustive mapping of every MainWindow action to a canonical behavior, complete editor-context-menu contents and guards, remaining dock implementation behavior, accessibility-specific routes, all platform-specific branches, and the large body of direct Scintilla-native keyboard/mouse editing behavior that may not be declared in NotepadNext source itself.

---

## 10.3 Preliminary NEST / Ecosystem Boundary

SCAN now distinguishes the NotepadNext body from environmental facilities that may supply or constrain effective behavior.

This section is a **preliminary boundary model**, not a completed NEST scan.

Candidate NEST or body/NEST boundary providers visible from current source evidence include:

- the Qt application/runtime and its event, widget, clipboard, file-dialog, settings, timer, and operating-system integration facilities;
- the operating system's process, filesystem, file-open/event, windowing, keyboard, mouse, and platform-specific behavior;
- SingleApplication-style inter-process communication used by secondary instances;
- Scintilla/Lexilla editor and language services, whose exact classification as bundled body versus external substrate must be established from build/dependency evidence;
- the embedded Lua subsystem and its script/resource boundary;
- persistent storage locations used for files, settings, recent-file data, and session restoration.

The important capability distinction is now explicit:

`NEST HAS FACILITY != NOTEPADNEXT CAN REACH IT != USE IS PERMITTED != NOTEPADNEXT USES IT != EFFECT HAS BEEN RUNTIME-OBSERVED`

Current evidence supports several candidate COUPLED abilities, such as file persistence through filesystem APIs, clipboard behavior through Qt/OS facilities, OS file-open handling, and secondary-instance IPC. Full provider identity, platform guards, runtime availability, and permissions remain PARTIAL or UNKNOWN.

### Extension / growth surfaces

Lua is a candidate extension/growth boundary because scripts and Lua-facing application functions may alter or extend behavior without appearing as ordinary static menu actions. The exact API exposed to Lua, script discovery rules, and whether scripts can create additional user surfaces or invoke all editor/application capabilities remain to be mapped.

Scintilla/Lexilla also require special treatment because substantial editing behavior may originate in framework/native editor machinery rather than explicit NotepadNext handlers. A faithful reconstruction cannot assume that behavior absent merely because NotepadNext source does not reimplement it.

The NEST map will therefore need to answer both:

1. What effective behavior does the NotepadNext body implement itself?
2. What behavior appears only because the body is coupled to a framework, runtime, operating-system service, or other external provider?

---

## 10.4 MainWindow Static Action Closure Pass 2

Status: **PARTIAL / STATIC REFERENCE CLOSURE ACHIEVED**

This pass tested A7 and A8 together against the exact pinned `src/dialogs/MainWindow.ui`, `MainWindow.cpp`, and `MainWindow.h`. It deliberately used the declaration set as the denominator rather than starting from handlers already known to the scanner. No NotepadNext code was executed.

### 10.4.1 Closure result

DIRECT enumeration of the complete pinned `MainWindow.ui` yields **139 unique explicit QAction definitions**. Manual source closure against the pinned MainWindow implementation gives:

- **137 / 139** actions with direct, helper-mediated, shared-handler, or platform-conditional binding evidence;
- **1 / 139** visible action with no implementation reference found: `actionFindInFiles`;
- **1 / 139** explicitly disabled placeholder: `actionThis_is_not_currently_implemented`;
- **0 / 139** silently dropped from the closure ledger.

This is a **reference/binding closure result**, not a claim that 137 behaviors are fully MAPPED. Many still require deeper effect, feedback, guard, NEST, and nerve tracing. The important result is that every declared static action now has an explicit fate.

The earlier count of 70 is therefore superseded. The undercount demonstrates why SCAN needs denominator-driven closure tests: a plausible-looking partial census can miss roughly half of a real control surface without producing an obvious error.

### 10.4.2 Complete static action ledger by capability family

| Family | Count | Static closure | Effective capability source / NEST dependency | Actions |
|---|---:|---|---|---|
| Document/window control | 7 | BOUND | Mostly body + Qt window/editor lifecycle; close/exit semantics also couple to session/settings persistence | `actionNew`, `actionExit`, `actionClose`, `actionCloseAll`, `actionCloseAllExceptActive`, `actionCloseAllToLeft`, `actionCloseAllToRight` |
| Filesystem/document I/O | 14 | BOUND | COUPLED to filesystem/storage and Qt file APIs; trash/workspace/export semantics depend on host filesystem facilities | `actionOpen`, `actionSave`, `actionSaveAs`, `actionSaveCopyAs`, `actionSaveAll`, `actionRename`, `actionReload`, `actionRestoreRecentlyClosedFile`, `actionOpenAllRecentFiles`, `actionClearRecentFilesList`, `actionMoveToTrash`, `actionOpenFolderasWorkspace`, `actionExportHtml`, `actionExportRtf` |
| Clipboard-facing | 11 | BOUND | COUPLED to Qt/system clipboard; text mutation portions also use Scintilla/editor code | `actionCut`, `actionCopy`, `actionPaste`, `actionCopyFullPath`, `actionCopyFileName`, `actionCopyFileDirectory`, `actionCopyAsHtml`, `actionCopyAsRtf`, `actionCopyURL`, `actionCutBookmarkedLines`, `actionCopyBookmarkedLines` |
| Printing | 1 | BOUND | COUPLED to Qt print stack and host printing facilities | `actionPrint` |
| Editor transforms | 37 | BOUND | Body + Scintilla/Qt editor services. Exact bundled-body versus NEST classification remains dependent on build/package census | `actionUndo`, `actionRedo`, `actionDelete`, `actionSelectAll`, `actionIncreaseIndent`, `actionDecreaseIndent`, `actionWindows`, `actionUnix`, `actionMacintosh`, `actionUpperCase`, `actionLowerCase`, `actionDuplicateCurrentLine`, `actionSplitLines`, `actionJoinLines`, `actionMoveSelectedLinesUp`, `actionMoveSelectedLinesDown`, `actionSelectNext`, `actionColumnMode`, `actionBase64Encode`, `actionURLEncode`, `actionBase64Decode`, `actionURLDecode`, `actionRemoveEmptyLines`, `actionToggleSingleLineComment`, `actionSingleLineComment`, `actionSingleLineUncomment`, `actionDeleteBookmarkedLines`, `actionRemoveDuplicateLines`, `actionRemoveConsecutiveDuplicateLines`, `actionSortLinesAsc`, `actionSortLinesDesc`, `actionSortLinesAscCaseInsensitive`, `actionSortLinesDescCaseInsensitive`, `actionSortLinesbyLengthAsc`, `actionSortLinesbyLengthDesc`, `actionReverseLineOrder`, `actionToggleOverType` |
| Search / mark / bookmark | 22 | 21 BOUND; 1 UNBOUND-CANDIDATE | Mostly body + Scintilla search/marker facilities; Find-in-Files implementation currently unresolved | `actionFind`, **`actionFindInFiles`**, `actionFindNext`, `actionFindPrevious`, `actionReplace`, `actionQuickFind`, `actionGoToLine`, `actionToggleBookmark`, `actionSearchAndBookmark`, `actionNextBookmark`, `actionPreviousBookmark`, `actionClearBookmarks`, `actionInvertBookmarks`, `actionMarkStyle1`, `actionMarkStyle2`, `actionClearStyle1`, `actionClearStyle2`, `actionMarkStyle3`, `actionClearStyle3`, `actionClearAllStyles`, `actionSelectandFindNext`, `actionSelectandFindPrevious` |
| View / navigation | 34 | BOUND | Body + Qt/Scintilla presentation/window facilities; fullscreen also couples to host window manager | `actionZoomIn`, `actionZoomOut`, `actionZoomReset`, `actionShowWhitespace`, `actionShowEndofLine`, `actionShowAllCharacters`, `actionShowIndentGuide`, `actionShowWrapSymbol`, `actionWordWrap`, `actionFullScreen`, `actionNextTab`, `actionPreviousTab`, `actionFoldLevel1`, `actionFoldLevel2`, `actionFoldLevel3`, `actionFoldLevel4`, `actionUnfoldLevel1`, `actionUnfoldLevel2`, `actionUnfoldLevel3`, `actionUnfoldLevel4`, `actionFoldAll`, `actionUnfoldAll`, `actionFoldLevel5`, `actionFoldLevel6`, `actionFoldLevel7`, `actionFoldLevel8`, `actionFoldLevel9`, `actionUnfoldLevel5`, `actionUnfoldLevel6`, `actionUnfoldLevel7`, `actionUnfoldLevel8`, `actionUnfoldLevel9`, `actionSplitHorizontal`, `actionSplitVertical` |
| Macro / settings / help | 9 | BOUND | Body + Qt; macro behavior couples to MacroManager/editor event stream; settings persist via application settings | `actionAboutQt`, `actionAboutNotepadNext`, `actionMacroRecording`, `actionPlayback`, `actionSaveCurrentRecordedMacro`, `actionRunMacroMultipleTimes`, `actionPreferences`, `actionEditMacros`, `actionDebugInfo` |
| Windows shell integration | 2 | BOUND, platform-conditional | BORROWED/COUPLED Windows NEST capability via `explorer`, `cmd`, process launching, and configured terminal command | `actionShowInExplorer`, `actionOpenTerminalHere` |
| Network update check | 1 | BOUND, platform/config-conditional | COUPLED to Windows build path, QSimpleUpdater, network availability, and external GitHub update metadata | `actionCheckForUpdates` |
| Explicit disabled placeholder | 1 | NON-ACTIONABLE / MAPPED AS ABSENCE | No effective capability established; UI explicitly marks the feature unavailable | `actionThis_is_not_currently_implemented` |

The family ledger contains **139 unique names with no duplicates**, providing a complete static denominator for this surface. Dynamic/programmatically created actions are intentionally outside this denominator and require their own closure pass.

### 10.4.3 Ghost-control anomaly candidate: Find in Files

`actionFindInFiles` is declared and placed in the Search menu as **Find in Files...**, but a repository-wide search at the pinned revision found the identifier only in `MainWindow.ui`. No explicit `connect(...)`, helper instantiation, auto-connect slot, or other implementation reference has yet been found.

Current classification: **PARTIAL / UI-IMPLEMENTATION MISMATCH CANDIDATE**. Static evidence suggests the control may be inert, but ordinary read-only SCAN has not executed the GUI, so runtime behavior is not claimed. This is exactly the kind of "ghost control" that a fidelity-oriented reconstruction must not silently turn into a working feature or silently omit. It must remain evidence-backed and unresolved until deeper evidence settles it.

By contrast, `actionThis_is_not_currently_implemented` is explicitly disabled and labeled as unimplemented. That is a mapped negative capability, not an unexplained omission.

### 10.4.4 Helper and hidden-route closure

Many editor actions do not own literal direct connections at the action site. `MainWindow::connectEditorAction(...)` is a template dispatch helper that connects `QAction::triggered` to a lambda invoking the selected method on the current `ScintillaNext` editor. Resolving its instantiations is necessary to close transformations, comments, folding, indentation, undo/redo, and related actions.

The closure pass also confirms several controls whose effective route is not obvious from the menu definition alone:

- `actionToggleOverType` is added to the window so its keyboard shortcut works even though it is not an ordinary menu placement;
- `actionNextTab` and `actionPreviousTab` gain additional Ctrl+PageDown/Ctrl+PageUp routes programmatically;
- fullscreen has a second human entrance through `pushExitFullScreen`, which triggers the same QAction;
- user settings can replace static shortcuts at runtime;
- editor and tab context menus reuse these QAction objects and can be rebuilt from settings;
- Windows shell actions exist as declared QActions but only acquire handlers under `Q_OS_WIN`.

These are evidence that **declaration closure and route closure are different dimensions**. A surface can be fully enumerated while still having multiple hidden entrances that need independent mapping.

### 10.4.5 A8 coupling observations from the same pass

Adding capability-source fields during A7 closure immediately separates behaviors that would otherwise look equivalent in a flat action list:

- Save/Open/Rename/Reload/Trash/Workspace/Export are **filesystem-coupled**;
- Cut/Copy/Paste and several Copy-* operations are **clipboard-coupled**;
- Print is **printing-subsystem-coupled**;
- Show in Explorer and Open Terminal Here are **Windows-NEST-coupled** and platform-conditional;
- Check for Updates is **network/external-service-coupled** and can be hidden/disabled by platform/configuration;
- editor transformations are implemented through NotepadNext + Scintilla/Qt, but whether those libraries belong inside the distributable body or should be modeled as NEST providers still requires build/package evidence.

This confirms the value of performing A7 and A8 closure together. A faithful copy needs to preserve the user's effective ability, while the scan separately records where the original body borrowed the muscle that produced it.

### 10.4.6 Pass verdict

**STATIC MAINWINDOW QACTION REFERENCE CLOSURE: PASS** for the declared 139-action denominator.

**COMPLETE MAINWINDOW HUMAN-SURFACE CLOSURE: NOT YET PASSING.** Dynamic action factories, dock toggle actions, context-menu variants, direct editor gestures, feedback paths, and nerve coverage are still PARTIAL.

The next test should therefore close **dynamic/programmatic MainWindow surfaces**, using factory/creation sites as denominators in the same way this pass used `.ui` QAction declarations.

---

## 11. Hidden / Unusual / Weakly Documented Structure Pass

This pass has NOT yet been completed.

The current baseline has not demonstrated a secret, easter egg, backdoor, or hidden vanity function in NotepadNext.

It **has** now demonstrated one useful unusual-surface candidate: `actionFindInFiles` is a visible Search-menu declaration for which the pinned repository search has not found a corresponding implementation reference. This is recorded as a ghost-control / UI-implementation mismatch candidate, not as an easter egg or proven runtime defect.

That does not establish absence of other hidden behavior.

The deterministic full scan must later search for:

- weakly connected functions
- obscure QAction paths
- compile-time gates
- hidden shortcuts
- developer/debug surfaces
- resource-only commands
- unusual Lua functions
- orphaned code
- conditionally reachable branches
- functionality absent from high-level documentation
- unexpected filesystem/process/network effects

Any discovered structure should first be recorded structurally before assigning a motive or label.

The goal is not merely to notice a strange function. A sufficiently deep scan should continue following reachability, guards, surfaces, state changes, effects, resources, NEST couplings, and neighboring code until it can support a semantic purpose or explicitly retain UNKNOWN. If later static passes cannot resolve an important structure and the operator authorizes deeper experiments, SCAN may recreate a minimal fragment or harness outside the specimen to test a narrow purpose hypothesis.

---

## 12. Known Scan Gaps

UNKNOWN or BLOCKED until exact whole-repository bytes are acquired and the deterministic run completes:

- total file census
- total first-party source count
- vendored/generated boundaries
- complete class/function/symbol inventory
- complete call graph
- complete Qt signal/slot graph
- generic deterministic reproduction of the completed 139-action MainWindow closure ledger
- completion of dynamic/programmatic, direct-editor, dialog/dock, and accessibility surface closure beyond Pass 2
- complete menu/toolbar/context-menu/shortcut/gesture equivalence map
- visibility and enablement guards for every user affordance
- sensory and motor nerve candidates for every mapped human behavior
- complete loop inventory
- strongly connected components
- centrality/chokepoint measurements
- persistence graph
- data-flow map
- complete file open/save arteries
- complete Scintilla interaction map
- complete Lua script inventory and call relationships
- timers and scheduler paths
- full resource graph
- hidden/unusual function pass
- candidate nerve ranking
- bounded NEST/environment census
- body <-> NEST capability-coupling graph
- intrinsic/borrowed/coupled/potential/blocked capability classification
- Lua extension-receptor and surface-growth map
- progressive D3-D4 deepening across the full specimen
- any D5 reconstruction/runtime experiments (not authorized or performed)
- machine Body Map serialization
- full Anchor Gate evidence

These gaps are part of the scan record, not defects to hide.

---

## 13. Next Deterministic SCAN Move

The creation plan has been revised around **evidence-graph traceability before blind reconstruction**. The immediate engineering sequence is now:

**EVIDENCE GRAPH BASELINE -> EXTRACTION BREADTH -> FULL NOTEPADNEXT CALIBRATION -> SEMANTIC OBJECT SYNTHESIS -> ANCHOR TRACEABILITY -> BLIND RECONSTRUCTION EXPERIMENT**

The evidence graph has passed R1, M3A denominator breadth, M3B deep/compiler/type/framework baselines, the M3C NEST/persistence/extension/error baseline, transferability refinements TR-001/TR-002/TR-002B, and qView development-oracle refinement O-003 in scanner v0.13. The exact verified NotepadNext bytes are now locally parser-eligible. The next specimen milestone is **M4 full pinned NotepadNext calibration**, pending recovery and verification of the authentic Engine v0.20 wheel/release/runner. Supporting PR2/PR3/PR4 work must not be reported as a substitute for M4.

The source gate is open, but the full NotepadNext calibration has not run. Once the authentic v0.20 execution artifacts are restored, SCAN must independently rediscover the preserved manual baseline and seal its output before receiving those facts as comparison input.

After machine calibration, every promoted NotepadNext Reconstruction Anchor must become a canonical `RECONSTRUCTION_ANCHOR` object whose `why` traversal reaches supporting source evidence. The inverse `impact` query must reveal which semantic claims and anchors depend on evidence so later contradictions or corrected extraction can propagate visibly.

Do **not** begin the blind reconstruction experiment merely because the prose report looks convincing. Begin it only when the reconstruction-anchor traceability dimension is sufficiently mapped for the behaviors selected for the experiment.

## 13.1 Secondary reconstruction products

The primary product remains the SCAN evidence itself. The reconstruction objective is to preserve NotepadNext's effective control surfaces and abilities with the highest fidelity the scan can support, including obscure, undocumented, dynamic, framework-provided, or easter-egg-like behavior if discovered.

A future recreation need not copy Qt/C++ internals unless compatibility requires them. It must, however, preserve promoted reconstruction anchors and the meaningful behavioral possibilities represented by the evidence map.

The following are early examples of **Specimen Reconstruction Anchor candidates** derived from that evidence. They are not SCAN Governance Anchors.

### RA-CANDIDATE-001: Single-primary-instance behavior

A faithful recreation should preserve the observed behavior that a secondary invocation can forward its startup arguments to an already-running primary instance and then terminate rather than becoming a second independent editor process.

Evidence state: DIRECT for the implemented pathway.

### RA-CANDIDATE-002: Session continuity

When the relevant settings enable it, a faithful recreation should preserve session continuity across process lifecycles, including supported saved files, unsaved files, temporary buffers, current-editor identity, and stored editor-view metadata.

Evidence state: DIRECT for storage/restoration mechanisms; exact user-visible equivalence remains to be behaviorally measured.

### RA-CANDIDATE-003: Empty-start document availability

After startup/session/file-input processing, if no editor exists, the application creates a new empty document before normal interactive operation.

Evidence state: DIRECT.

### RA-CANDIDATE-004: Periodic recovery checkpoint

During normal operation, the application implements a recurring session-save trigger at a one-minute interval. A recreation intended to preserve recovery semantics must not silently optimize this recovery behavior away.

Evidence state: DIRECT for configured timer and connection; runtime scheduling precision not measured.

### RA-CANDIDATE-005: Save-state transition

A successful save transitions a document buffer into a saved state by writing its current bytes, updating file timestamp state, establishing a save point, clearing temporary status where applicable, and emitting a successful-save notification.

Evidence state: DIRECT.

These candidates demonstrate the intended downstream use of SCAN. They must remain traceable to the scan and may be refined, split, merged, promoted, or rejected as coverage improves.

---

## 14. Historical Anchor Gate: Working Baseline (superseded by v0.29)

### A1 Preserve the specimen
PASS for work performed so far.
Repository evidence was read. No NotepadNext source modification was performed.

### A2 Scanning engine discovers; AI interprets
PARTIAL, with reusable machinery strengthened through CR-002.
A reusable scanner v0.9 engine now performs mechanical inventory, hashing, normalized indexing, evidence capture, caching, framework-aware extraction, graph metrics, verified GitHub acquisition, Qt Designer/direct/helper wiring recovery, timer recurrence extraction, first-class source-digest-aware evidence objects, canonical cross-object semantic relations, nested completeness vectors, semantic overlay ingestion, `why`/`impact` provenance traversal, integrity auditing, denominator-based surface closure, unique cross-file resolution, dynamic QAction/QShortcut identity, CLI/event surface extraction, stable-ID repeatability checks, and projection-manifest coherence. Its 50-test regression suite passes. The full pinned NotepadNext content map is still blocked by this runtime's outbound network transport, so A2 is not yet a full pass for this specimen.

### A3 Account for the whole visible body
NOT YET SATISFIED, but the acquisition blind spot is now explicit and the reusable acquisition mechanism exists.
The provider-visible pinned specimen can be identified, and v0.9 preserves metadata-only, blocked, external-reference, symlink-reference, and hash-mismatch states rather than dropping them. The scanner now also represents completeness as explicit anatomical dimensions rather than a single score. The GitHub driver can verify exact provider blobs before parser eligibility in an internet-enabled runtime. However, complete NotepadNext repository bytes have still not crossed the acquisition seam in this runtime, so the full body has not yet received verified content hashes and parser coverage.

### A4 Implementation evidence outranks description
PARTIAL / TOOLING MECHANISM PASS.
Current specimen claims are still based primarily on source/repository evidence and marked when inferred. Scanner v0.9 now additionally audits those evidence/claim dependencies, rejects unsupported semantic relation vocabulary, checks source-digest provenance, and mechanically distinguishes BOUND/PARTIAL/UNRESOLVED human-surface closure on controlled fixtures. The complete NotepadNext body has not yet been processed through that evidence graph, so certification-grade traceability for the specimen remains incomplete.

### A5 Biology is analytical
PASS.
Biological terms are being used to organize evidence; unsupported organs have not been invented.

### A6 Map circulation and nerves
PARTIAL.
Several candidate arteries, a recurring one-minute session-checkpoint artery, and additional nerve seams have been identified, but complete deterministic artery discovery and ranking have not yet been performed.

### A7 Map the complete human interaction surface
PARTIAL, with substantial progress in Surface Census Pass 1.
The scan now accounts for all **139 explicit MainWindow QAction declarations at static reference-closure level**, nine top-level menu families, the main toolbar, several dynamic menu families, programmatically inserted dock actions, major dialogs, workspace/file/search docks, tab gestures, Quick Find, platform-specific routes, custom shortcuts, and the hidden Lua Console control surface. Of the 139 static actions, 137 have binding/handler evidence, one (`actionFindInFiles`) is a visible action for which no implementation reference was found in the pinned repository search, and one is an explicitly disabled not-implemented placeholder. Full effect/feedback/nerve closure, direct Scintilla-native gestures, remaining dynamic surfaces, accessibility routes, and all platform branches remain unresolved, so A7 does not yet pass.

### A8 Map the NEST and effective capability boundary
PARTIAL.
Current evidence identifies candidate environmental providers and boundary seams including Qt/OS facilities, filesystem behavior, settings/persistence, clipboard, printing, process launching/cancellation, network/update checking, IPC, environment access, Scintilla/Lexilla, plugins/dynamic libraries, JavaScript, and Lua. Scanner v0.9 now emits a dedicated NEST capability projection and preserves `COUPLED`, `POTENTIAL`, `UNKNOWN`, permission/error, persistence, and extension-receptor distinctions on controlled fixtures. Static MainWindow closure still attaches preliminary capability-source/NEST classifications to the 139 declared action records by family. The complete pinned NotepadNext body has not yet been processed through the v0.9 capability graph, so A8 remains PARTIAL.

Overall status:

**BASELINE CREATED. FULL SCAN NOT YET COMPLETE.**


---

## Project Tooling Checkpoint: Engine v0.19 / Project v0.26

**This section is SCAN tooling evidence, not NotepadNext specimen evidence.**

Engine v0.19 implements the M5 reconstruction-promotion gate and immutable certification lineage. External semantic proposals are validated without mutating the canonical graph. Promoted semantic claims must reach first-class evidence, Reconstruction Anchors require typed behavior/artery/nerve/capability support plus a property/fidelity-test/uncertainty contract, MAPPED anchors cannot escalate weaker or contradicted proof, and rejected proposals leave the graph unchanged. Successful promotion emits `reconstruction_contract.json` as a canonical-ID projection.

A new `certify-reconstruction` flow verifies a sealed mechanical parent, copies the scan into a child lineage, applies only a proposal that passes the M5 gate, refreshes canonical projections, records parent receipt/manifest SHA-256 identities, and seals the derived handoff. The parent remains byte-for-byte unchanged. Read-only query/provenance/audit operations use SQLite immutable mode so inspection does not create WAL/SHM sidecars or alter the sealed database.

Measured v0.19 release evidence:

- development regression: **102/102 PASS**, no ResourceWarnings;
- fresh extracted release regression: **102/102 PASS**;
- clean package self-audit: **64/64 tracked files, 0 issues**;
- LLM-disabled release qualification: PASS;
- required mechanical query acceptance: **12/12 PASS**;
- fresh Python 3.13.5 wheel installation: PASS;
- installed-wheel mechanical parent certification: PASS;
- installed-wheel read-only `query` + `why`: parent database SHA-256 unchanged and parent certification still verifies PASS;
- external reconstruction proposal validation: PASS;
- installed-wheel reconstruction-aware child certification: PASS;
- independent child verification: PASS;
- derived receipt records parent manifest/receipt SHA-256 lineage and one promoted behavior/anchor in the controlled qualification specimen.

This advances M5 and part of PR7's infrastructure. It does **not** count as the M6/PR7 blind reconstruction experiment, and it does not change the blocked status of full pinned NotepadNext calibration.


---

## Historical Project Acquisition Checkpoint: PR5 exact bytes / Project v0.28

**This section is acquisition evidence, not SCAN output and not oracle comparison.**

On `2026-09-13T18:21:51.2836955Z`, the PR5 NotepadNext repository was cloned without checkout, detached at the required commit, verified, and archived without consulting the preserved oracle:

- repository: `https://github.com/dail8859/NotepadNext.git`;
- commit: `f57db52d6760a2ce4149a37190c3adaa586845f5` — MATCH;
- Git tree: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b` — MATCH;
- tracked files: `1,928`;
- working tree: clean;
- object integrity: `git fsck --full` PASS;
- submodules: none;
- historical Windows checkout/archive: `NotepadNext-f57db52d6760a2ce4149a37190c3adaa586845f5.zip`, SHA-256 `d808933bb774f7258750100ea5902ba0b06d1dc30ca8075b7d5c829f4290988e`;
- later calibration discovered that checkout filters transformed line endings in that historical archive, so it was rejected for the accepted cold lineage;
- accepted exact provider-blob acquisition: `NotepadNext_exact_acquisition.zip`, SHA-256 `4a1343f4f56500ba850162039e7483e2f17f894be6493f5afbaacdf25c2c44a3`.

This section records the earlier acquisition-only checkpoint. Its execution status is superseded by the authoritative v0.29 cold result at the top of this report.

The original Engine v0.20 / Project v0.27 release message supplies authoritative recovery checksums:

- project handoff SHA-256: `f9590271c0c8cca16993e548667dcf9536c4a04c2be33590e83d302bac7cddb0`;
- engine ZIP SHA-256: `6dce99a4ed924d9e370a29367e7a59845f2eefac5414cb3403e873b8577f9af1`;
- wheel SHA-256: `573ce1c0a0ea7e5bc0039ce954209e983ba3d373e73b9301baf282fd559076fa`;
- public challenge SHA-256: `ccd806213189e2b0bf0f7ec47bf3f608c41132ce6f16af7b04147ec9afdb5eee`;
- sealed M6A trial SHA-256: `d1052f9a46e666f1f538fda9f6ac8cdd5aa00d39bfaa688c6c2553516e27f737`.

The cold runner `RUN_PR5_NOTEPADNEXT_COLD_v020.ps1` must be recovered inside, and verified through, the authentic project handoff manifest. A filename match alone is insufficient.

---

## Project Tooling Checkpoint: Engine v0.20 / Project v0.27

**This section is SCAN tooling evidence, not NotepadNext specimen evidence.**

Engine v0.20 implements M6A source-blind reconstruction-trial infrastructure on top of the v0.19 M5 promotion/lineage gate. `prepare-reconstruction-trial` verifies a reconstruction-aware certification and emits two independently sealed packages: a public challenge for the reconstruction agent and a private evaluator that must remain outside the agent context. The public package excludes original specimen source bytes, evidence excerpts, original source paths, `scan_index.sqlite`, evidence catalog/graph payloads, and evaluator internals. It publishes only the reconstruction contracts, completeness states, and source-free mechanical scoring requirements needed for a fair test.

`score-reconstruction-trial` copies and scans the reconstructed candidate, compares surface text/type plus binding/effect closure and MAPPED terminal effect/capability signatures, and attributes discrepancies to reconstruction-agent, semantic-IR, candidate-scanner-coverage, or unresolved-source-evidence domains. Non-MAPPED source terminals remain visible as advisory uncertainty and do not become binary failure conditions. The candidate bytes, candidate scan, submission declaration, scorecard, receipt, and lineage are sealed in `TRIAL_MANIFEST.json`; `verify-reconstruction-trial` independently detects tampering.

Measured v0.20 release evidence:

- development regression: **111/111 PASS**;
- fresh extracted release regression: **111/111 PASS**;
- clean package self-audit: **67/67 tracked files, 0 issues**;
- LLM-disabled release qualification: PASS;
- required mechanical query acceptance: **12/12 PASS**;
- fresh Python 3.13.5 wheel installation: PASS;
- installed-wheel mechanical parent certification: PASS;
- installed-wheel reconstruction-aware child certification: PASS;
- installed-wheel public/private M6A split: PASS;
- public challenge/evaluator manifest verification: PASS;
- controlled candidate generator consumed only public challenge data and reconstructed a differently named Save QAction plus the publicly required MAPPED subprocess terminal;
- private scoring: **PASS, 1/1 anchor, fidelity_score 1.0**;
- sealed trial verification: PASS;
- parent and semantic child certifications still independently verify PASS after the trial;
- deterministic public challenge ZIP generation is regression-tested;
- deliberate evaluator/trial tampering and challenge/source-isolation violations are detected by regression tests.

This advances PR7 to **PARTIAL / M5 + M6A mechanism pass**. The controlled challenge-only generator is an infrastructure probe, not a capable external coding agent, and no reconstructed application was executed. Full PR7 still requires converged calibrated real-specimen evidence, a genuinely source-blind external coding agent, and behavior-level M6B fidelity evaluation. As of project v0.29, PR5 cold mechanical certification passes but calibration remains PARTIAL; H-001 remains frozen and uninspected.

---

## 15. Historical Anchor Gate: Project v0.29 / PR5 cold result

### A1 Preserve the specimen

PASS for the cold operation. The exact provider blobs were verified, SCAN remained read-only, and no NotepadNext code was executed or modified.

### A2 Scanning engine discovers; AI interprets

PASS for the cold boundary / PARTIAL for convergence. Engine v0.20 completed mechanically with LLM access disabled. Oracle comparison occurred only after sealing. Generic extraction and closure gaps remain.

### A3 Account for the whole visible body

PARTIAL. All 1,928 provider blobs are accounted for and materialized, but the completeness vector retains 33 PARTIAL, 4 UNKNOWN, and 1 BLOCKED dimensions, including 394 parser gaps.

### A4 Implementation evidence outranks description

PASS for certification integrity / PARTIAL for semantics. The sealed package independently verifies 12/12 files, while unsupported compiler, persistence, lifecycle, dynamic-route, and capability claims remain explicitly weak or unknown.

### A5 Biology is analytical

PASS. Anatomical language continues to organize mechanically traceable evidence without inventing unsupported organs or abilities.

### A6 Map circulation and nerves

PARTIAL. The engine emits a large evidence/call/effect graph and maps recurrence, but compiler/type dispatch, lifecycle, persistence, and several effect routes remain incomplete.

### A7 Map the complete human interaction surface

PARTIAL with a strong Qt-action checkpoint. The machine independently matches 139 MainWindow QActions and 137 routed actions, including both known anomalies. After the generic v0.26 denominator correction, the wider human-surface set contains 310 bound, 59 partial, and 11 unresolved surfaces; all 330 declared/factory surface states are preserved from v0.25.

### A8 Map the NEST and effective capability boundary

PARTIAL. The cold run finds 4,232 candidate boundaries and 112 effects, but capability provenance is PARTIAL, typed effects are absent, and build/workflow/vendor URL noise remains.

Overall status: **PR5 COLD SCAN PASS / CALIBRATION PARTIAL. SCAN v1 NOT YET COMPLETE.**
