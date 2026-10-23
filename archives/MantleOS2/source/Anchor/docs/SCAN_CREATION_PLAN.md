# SCAN CREATION PLAN
Version: 0.32
Status: ACTIVE LIVING ROADMAP
Canonical public project: this repository's `Anchor/` directory
Companion files: `ANCHOR_CODING_PROMPT.md`, `SCAN_PROTOCOL.md`, `SCAN_REPORT.md`

## v0.32 frozen v0.26 surface-denominator checkpoint

Engine v0.26 is frozen under `engine/v0.26/` and `releases/v0.26/`. It carries the v0.25 adaptive/bounded engine forward and generically distinguishes ordinary Qt object references from proven human surfaces while limiting CLI consumers to proven `QCommandLineParser` receivers.

The final package passes 144 development and 144 clean-package tests, with three Windows symlink-privilege skips in each run; package self-audit is 83/83; a fresh Python 3.13.13 wheel install and 12/12-query LLM-disabled qualification pass. Two exact manifest-backed NotepadNext scans emitted 21 byte-identical files and zero canonical database-row differences. Cache proof reports 4,186 hits, zero misses, and no canonical/workbench drift. Final certification independently verifies 12/12 files with zero issues.

All 330 declared/factory surfaces and their v0.25 closure states are preserved. The denominator removes 108 false references—37 metadata-derived pseudo-options and 71 ordinary UI-object accesses—while retaining all 147 QActions, four genuine CLI options, and 50 proven signal-sender references. Surface closure is now 310 bound / 59 partial / 11 unresolved of 380; effect closure is 87 closed / 282 partial / 11 unresolved. Compiler evidence remains 378/394 translation units (84 `MAPPED`, 294 `PARTIAL`, 16 unavailable). PR5 remains **CALIBRATION PARTIAL** while the 11 unresolved, 59 partial, lifecycle, persistence, dynamic-route, capability, platform, and behavioral-reconstruction gaps remain. H-001 remains frozen and source-uninspected.

## v0.30 frozen v0.23 GitHub synchronization checkpoint

Engine v0.23 is frozen and packaged under `engine/v0.23/` and `releases/v0.23/`. The exact pinned NotepadNext compiler-enabled, LLM-disabled v0.23 calibration sealed and independently verified 12/12 manifest files. Compiler AST recovery advanced from 0/394 translation units in v0.22 to 83 mapped plus 74 partial in v0.23, but 237 units remain unavailable or bounded and 311 parser gaps are explicit. Mechanical certification is PASS; PR5 semantic calibration remains PARTIAL. No H-001 source inspection, holdout scan, external-agent reconstruction, or production certification has been performed. Further refinement is paused for this repository synchronization; the next loop remains generic fixes, fresh sealed calibration, second clean determinism/cache run, then candidate freeze and untouched holdout.

## v0.29 PR5 cold-calibration checkpoint (historical baseline)

The exact pinned NotepadNext repository is acquired and verified at commit `f57db52d6760a2ce4149a37190c3adaa586845f5`, tree `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`. The accepted acquisition package preserves all 1,928 provider blobs byte-for-byte and is sealed at SHA-256 `4a1343f4f56500ba850162039e7483e2f17f894be6493f5afbaacdf25c2c44a3`.

The authentic Engine v0.20 wheel/release/cold-runner lineage was recovered and verified. A cold LLM-disabled scan completed over 1,928/1,928 files, its 213,474,077-byte certification package independently verified 12/12 files, and the package is sealed at SHA-256 `6c0d476e2dd7a63481cf388e6d654798ffa26f8c72ce9760a8bd60667b075ce3`. Oracle comparison advances M4/PR5 to **COLD SCAN PASS / CALIBRATION PARTIAL**. The next loop admits only generic scanner improvements followed by a new sealed rerun.

## Purpose

Build SCAN into a reusable evidence-first software scanner capable of describing an application deeply enough that a separate coding agent can reproduce its human control surfaces and effective abilities with very high fidelity, including obscure, dynamic, framework-native, conditional, extension-provided, and easter-egg-like behavior when evidence supports it.

SCAN is not an AppAI birth/assimilation system. The reusable lesson taken from those systems is that an application's BODY is only part of its effective organism; its NEST/environment may supply capabilities, boundaries, and surfaces that must also be mapped.

## Governing architecture

SCAN uses one canonical normalized evidence/body graph and many projections.

```text
IMMUTABLE SPECIMEN
      |
      v
ACQUISITION + VERIFICATION
      |
      v
MECHANICAL EXTRACTION
      |
      v
CANONICAL EVIDENCE GRAPH / DATABASE
      |
      +--> Machine Body Map
      +--> Evidence Catalog
      +--> Completeness Vector
      +--> Control Surface Map
      +--> Artery Map
      +--> Nerve Map
      +--> NEST Capability Map
      +--> Human Scan Report
      +--> Reconstruction Anchor Map
```

The projections are not independent authorities. They share the same object IDs and relationships.

## Evidence dependency model

Evidence is a first-class object, not just a string like `DIRECT`.

Preferred proof direction:

```text
SOURCE FILE / ARTIFACT
    -> EVIDENCE OBJECT
        -> EXTRACTED OBJECT OR GRAPH RELATION
            -> BEHAVIOR / ARTERY / CAPABILITY / INTERPRETATION
                -> RECONSTRUCTION ANCHOR
```

The graph may branch and merge. Multiple evidence objects may support one claim. Later evidence may `contradicts` an interpretation without deleting earlier records.

Every certification-grade reconstruction anchor must support:

```text
scan-body why <db> <RA-ID>
```

and every important evidence object must support the inverse:

```text
scan-body impact <db> <EV-ID>
```

## Stable identity

Every canonical object receives a globally unique stable ID within the specimen/revision graph. Deterministic extraction IDs should remain stable while the represented source fact is unchanged. Higher-stage semantic objects may use explicit IDs such as:

- `BEH-*` behavior
- `ART-*` artery
- `NERVE-*` nerve
- `CAP-*` capability
- `IN-*` interpretation
- `RA-*` reconstruction anchor

Identity stability matters more than the exact prefix convention.

## Completeness model

SCAN does not use one global completion percentage as authority. It uses a vector of dimensions and subdimensions with states such as `MAPPED`, `PARTIAL`, `BLOCKED`, `NOT_APPLICABLE`, and `UNKNOWN`.

Typical dimensions include specimen identity, acquisition, file census, parser coverage, symbols, call graph, event graph, lifecycle, persistence, human surfaces, framework-native surfaces, NEST coupling, extension receptors, hidden-function analysis, authority closure, and reconstruction-anchor traceability.

The vector tells the scanner where deeper work is worth spending time.

## Development milestones

### Architecture Directive Integration — ESTABLISHED IN PROJECT v0.20

The Scanner Architecture and Stage 1 Implementation Directive is adopted as the implementation contract: Stage 1 is predominantly mechanical; recurring operations become reusable scanner machinery; fine evidence is compressed upward into higher-order anatomy without losing provenance; repository scale is handled through indexing/caching/resume/resource controls; and LLM work begins after the mechanical evidence map exists. This integration adds no governance anchor and does not change A1-A8.

Production qualification now includes an **LLM-disabled mechanical-independence run** plus a machine-query acceptance suite. A supported scan must still inventory, extract, connect, project, audit, report closure, and answer core provenance/coverage queries without an LLM service.

### M0 — Governance / immutable specimen — ESTABLISHED

A1-A8, evidence classes, read-only default mode, pinned revision identity, progressive D0-D5 depth, and separately authorized experiments.

### M1 — Reusable Stage 1 substrate — IMPLEMENTED BASELINE

Local/manifest acquisition, hashing, stable IDs, SQLite indexing, extraction cache, Qt UI/C++/CMake adapters, graph basics, coverage-gap queries, and reusable exact-revision GitHub acquisition.

The earlier direct-Python network path remained blocked, but project v0.28 crossed the acquisition seam through a verified Git clone/archive path. The exact commit/tree bytes are now locally available; the authentic v0.20 execution bundle is the remaining cold-run dependency.

### M2 — Evidence Graph / Cross-Object Identity — IMPLEMENTED AND R1-REFINED IN ENGINE v0.5

Implemented:

- canonical `semantic_objects` and `semantic_relations`;
- first-class evidence objects;
- addressable structural-relation claims;
- typed relation vocabulary;
- `completeness_dimensions`;
- `evidence_graph.json`, `evidence_catalog.json`, and `completeness_vector.json` projections;
- semantic overlay ingestion with dangling-reference rejection;
- `why`, `impact`, and object inspection queries;
- exact Qt `.ui` declaration line evidence where mechanically recoverable.

Controlled regression status after R1 refinement: **20/20 PASS**.

A controlled proof-chain demonstration successfully traverses:

```text
RA-DEMO-001
 <- IN-DEMO-001
 <- discovered Save surface
 <- DIRECT evidence
 <- MainWindow.ui
```

and the inverse evidence-impact traversal reaches the anchor again.

### M3 — Extraction breadth / closure machinery — BASELINE COMPLETE THROUGH M3C; REAL-PROJECT DEPTH CONTINUES

The first refinement gate, **R1 evidence/projection/closure integrity**, is now implemented in engine v0.5 before broadening extraction further. R1 adds stable-ID repeatability tests, typed semantic-overlay relations, source-digest-aware evidence objects, `audit`, `closure`, proof-path validation, orphan/dangling/cycle detection, nested surface-binding completeness, and projection hash manifests. Reconstruction anchors without a positive path to first-class evidence are mechanically reported as integrity errors.

Controlled R1 result: 20/20 regression tests pass. A two-surface Qt fixture produces one mechanically BOUND Save action and one deliberately UNRESOLVED Ghost action; integrity remains clean because unresolved scanner knowledge is preserved as closure state rather than fictionalized as a handler. `why RA-R1-SAVE` reaches source evidence and file provenance, and `impact` from the Save evidence reaches the reconstruction anchor.

**M3A completed in engine v0.6: human-surface breadth and denominator-driven closure.** v0.6 adds Designer connections/shortcuts, common interactive widgets, generic `ui->objectName` references, dynamic QAction/QShortcut identity, CLI controls/consumers, event-override entrances, uniqueness-gated cross-file resolution, ambiguity findings, stable-ID duplicate merging, bounded route closure, and per-surface-type denominator dimensions. The controlled M3A suite is part of a 28/28 passing regression set.

**M3B-1 baseline completed in engine v0.7: compiler-assisted structure and deep effect closure.** v0.7 adds optional fixed-binary Clang AST extraction with safe compile-context filtering, brace-aware C++ fallback regions, sender-scoped Qt event identity, project-local call resolution, explicit state/effect/feedback objects, function-context NEST/extension links, and `deep-closure` traversal from a human entrance through calls to consequential terminals. A controlled three-QAction fixture closes two real actions through effect/feedback paths and leaves the deliberate ghost action UNRESOLVED. The full regression set is **37/37 PASS**.

**M3B-2 baseline completed in engine v0.8: compiler/type/framework closure.** v0.8 adds bounded compile-database discovery, compile-context-sensitive extraction caching, compiler-derived C++ type/inheritance/override/overload/template/virtual-dispatch evidence, typed Qt/NEST effect synthesis, preprocessor/conditional provenance, Qt generated-code contracts, and a Scintilla/Lexilla framework adapter. The controlled regression set is **43/43 PASS**.

**M3C baseline completed in engine v0.9: NEST/persistence/extension/error closure.** v0.9 adds mechanically visible guard/loop/early-exit/exception/retry anatomy, typed permission/environment/cancel/error/lock effects, first-class persistence operations, conservative state-to-persistence candidates, typed plugin/script/dynamic-library receptors, potential capability factories, dedicated capability-provenance dimensions, and `nest_capability_map.json`. The controlled M3C regression set is part of a **50/50 PASS** suite.

M3 is not "finished forever." Remaining PR2/PR3/PR4 depth work should continue whenever calibration exposes a concrete miss, especially whole-program CFG/data flow, generated Qt artifact resolution, exact persistence/value paths, richer Scintilla/Lexilla human-behavior closure, platform/error semantics on real applications, and larger-repository performance/resume behavior. Those are now calibration-driven refinements rather than a reason to postpone the next specimen milestone.

Recurring misses become reusable scanner components, never specimen-only patches unless the behavior is truly specimen-specific.

M3 refinement acceptance is denominator-driven: discovered surfaces, factories, handlers, boundaries, and other supported objects must each end with an explicit mapped/partial/blocked/unknown state. Raw node count is not a completeness claim.

### PR1A — Byte-boundary and resource hardening RH-001 — PASS / PR1 STILL PARTIAL

Engine v0.14 implements the first dedicated production-hardening slice at acquisition/local-byte ingestion: symlink roots are rejected; internal symlink/special entries remain explicit and non-parser-eligible; local reads are no-follow/identity checked and digest-verified across inventory-to-extraction rereads; manifest traversal/symlink materialization is blocked; and local/provider reads have configurable per-item resource ceilings. GitHub declared-oversize blobs are rejected before fetch.

Validation: **72/72 tests PASS** in the development tree and clean extracted package. v0.14 self-scan: **47 files, 94 nodes, 41 edges, 90 evidence records, 275 semantic objects, 494 semantic relations, 28 completeness dimensions, MAPPED / 0 integrity issues**; unchanged rerun **57 cache hits / 0 misses**.

PR1 remains PARTIAL. Remaining release-hardening work includes malformed parser/crash corpus, aggregate time/byte/node budgets and cancellation, database/projection corruption/rebuild policy, schema migration/rebuild contract, install/platform matrix, large-repository load/resume testing, and the packaged mechanical-independence/query acceptance suite.

### PR1B — Aggregate budgets, store recovery, self-audit, and LLM-disabled qualification — PASS / PR1-PR8 STILL PARTIAL

Engine v0.16 adds explicit aggregate scan ceilings/cancellation, safe-boundary partial completion, SQLite schema/corruption policy, deterministic package/projection byte verification, and the required LLM-disabled mechanical qualification/query surface. Controlled validation at that checkpoint reached **85/85 PASS**, package verification **55/55**, and required query execution **12/12**.

### PR1C — Parser fault isolation, resume, wheel deployment, and load checkpoint — PASS / PR1-PR8 STILL PARTIAL

Engine v0.17 contains ordinary adapter exceptions to the affected artifact/adapter as explicit `parser_failure` / `PARTIAL` evidence while retaining fatal process-level `MemoryError`; verifies that a budget-stopped run can resume in the same output and reuse valid cache entries; and validates wheel installation/CLI execution in a fresh Python 3.13.5 virtual environment.

Measured v0.17 release evidence:

- development regression: **90/90 PASS**;
- clean extracted release regression: **90/90 PASS**;
- clean package self-audit: **58/58 tracked files, 0 issues**;
- LLM-disabled qualification: **12/12 required queries PASS**, integrity `MAPPED / 0 ERROR`;
- installed-wheel qualification scan: projections PASS and **12/12 queries PASS**;
- scanner-owned 321-file C++/Qt-ish load fixture: **4.5326 s cold**, **0.5398 s warm**, **1,542 cache hits / 0 misses**, 963 nodes / 601 edges / 961 evidence, `MAPPED / 0` integrity issues.

This materially strengthens PR1/PR8 but does not substitute for a complete real large-repository performance profile, cross-platform/Python-version matrix, PR5, PR6D, or PR7.


### PR1D / PR8B — Agent-facing specimen certification and sealed handoff — PASS FOR MECHANISM / PR8 STILL PARTIAL

Engine v0.18 adds `scan-body certify`, `certify-manifest`, and `verify-certification`. A certification run verifies the SCAN release package, disables common LLM credentials, scans either a local specimen or a provider/source manifest under the selected resource policy, runs integrity/projection/query gates, records the specimen fingerprint, provider/repository/commit/tree identity when present, and coverage state, seals all emitted evidence artifacts in `CERTIFICATION_MANIFEST.json`, and can emit a stable-order ZIP handoff. The verifier detects post-scan byte drift and re-checks the projection manifest/database.

The receipt intentionally distinguishes **mechanical evidence integrity** from **specimen coverage completeness**. `PASS` does not promote PARTIAL/BLOCKED/UNKNOWN dimensions into certainty. Budget stops and acquisition/parser failures remain explicit execution/coverage facts for a consuming agent.

Measured v0.18 release evidence:

- development regression suite: **94/94 PASS**;
- fresh extracted release suite: **94/94 PASS**;
- package self-audit: **60/60 tracked files, 0 issues**;
- LLM-disabled qualification: **12/12 required queries PASS**;
- fresh Python 3.13.5 wheel install: PASS;
- installed-wheel `certify` run: PASS;
- independent `verify-certification` of the sealed handoff: PASS;
- tamper regression: PASS (modified sealed byte is detected);
- bounded certification regression: PASS (mechanically valid handoff retains explicit PARTIAL execution state).

This closes a major inter-agent trust/handoff mechanism. It does not replace PR5 calibration, the PR6 blind holdout, PR7 reconstruction proof, or the remaining real large-repository / cross-platform release matrix.

### M4 — Full pinned NotepadNext calibration — COLD SCAN PASS / CALIBRATION PARTIAL

The authentic v0.20 wheel/release/runner lineage was recovered, Stage 1 ran across the verified whole body, and the cold package was sealed and verified before comparison with the preserved manual baseline. The exact QAction denominator/routes and key anomalies generalized; compiler context, persistence, lifecycle, dynamic-route closure, NEST classification, Windows identity semantics, receipt population, and large-project performance remain generic calibration work.

Calibration questions include independent recovery of the known QAction denominator, helper-mediated editor dispatch, dynamic controls, platform/NEST boundaries, recurrence, lifecycle paths, and known anomalies. Machine-only discoveries are equally important and remain in the body map.

### PR6A — Transferability micro-calibration TR-001 — PARTIAL PASS

While M4 is blocked by complete NotepadNext byte materialization, SCAN was cold-run against an exact pinned blob from an unrelated real Qt Widgets application. The v0.9 scanner initially reported zero human surfaces because the application constructs its widgets programmatically. That miss drove reusable v0.10 improvements: programmatic interactive-widget census, sender identity reuse, lambda-local consequence attribution, and read-only presented-surface classification.

The same exact specimen then produced an evidence-clean scan with a bound/deep-closed QListWidget route, a presented read-only log widget, and an explicitly unresolved editable QTextEdit native-behavior gap. Full regression coverage is now **53/53 PASS**.

This is a **partial PR6 success**, not the full PR6 gate. A larger unrelated C++/Qt application must still be scanned end-to-end.

### PR6B — Multi-file transferability calibration TR-002 — PARTIAL PASS

SCAN was then cold-run against the exact pinned repository tree `tashaxing/QtWuziqi@f4a8700699fce1b4d4a9d07e4618045c57ad3666`, tree `56bb172f66e8b22e071bf45bfa4e7d14815bd4bd`. The provider reports 12 blobs and a non-truncated tree. The original TR-002 pass materialized seven exact text blobs and left five provider-visible blobs `METADATA_ONLY`, including `GameModel.cpp` and four media files.

The cold v0.10 pass found 4 human input surfaces but left both legacy-wired QActions unresolved, had no qmake or resource-asset anatomy, and reached no deep terminal from any of the four input surfaces. That calibration produced reusable v0.11 improvements: qmake extraction, `.qrc` resource mapping, legacy `SIGNAL()/SLOT()` binding, `QTimer::singleShot` delayed dispatch, multimedia/repaint feedback, and removal of the false extension inference attached to ordinary menu/action creation.

The v0.11 rerun on the same verified materialized subset produces **4/4 bound surfaces and 4/4 deep-closed routes**, maps qmake target/dependency/input topology, exposes three resource assets, records the timer-delayed AI route, and maps multimedia playback effects. The full v0.11 regression suite is **57/57 PASS**, including the new transferability regressions, and a clean extraction of the release package passes the same suite.

PR6 remains **PARTIAL**, not passed: five blobs are not parser-eligible, `GameModel.cpp` contains important unscanned gameplay/AI state behavior, Qt compiler context remains incomplete, and this specimen is still small. The key result is that a second unrelated organism exposed different generic weaknesses and the scanner improved without specimen-specific rules.

### PR6B2 — Provenance and cross-file state refinement TR-002B — PARTIAL PASS

An exact provider blob later made `GameModel.cpp` locally materializable and Git-object verification passed. The hybrid specimen therefore advanced to **8 materialized / 4 metadata-only binary blobs** without changing pinned commit or tree identity. The added source immediately exposed a compiler provenance failure: v0.11 emitted large amounts of system-header declaration anatomy, inflating the graph to 5,389 nodes. It also exposed a fallback receiver-type gap at `game->actionByPerson()` / `game->actionByAI()` and false state mutations from RHS member reads such as `pointPair.first`.

v0.12 repairs those classes generically by restricting compiler-emitted declarations to the main translation unit, recording direct class data members with declared/static type, using unique member static types for conservative cross-file fallback resolution, and extracting state mutation only from `this`-rooted assignment targets. The same verified bytes now produce **443 nodes, 474 edges, 422 evidence records, 1,355 semantic objects, and 3,255 semantic relations**, with **MAPPED / 0 integrity issues**, **4/4 bound surfaces**, and **4/4 deep-closed routes**. MainWindow pointer routes can now reach GameModel state such as `gameMapVec`, `playerFlag`, `scoreMapVec`, and `gameType`; false `first` / `second` state records are absent.

The v0.12 regression suite is **60/60 PASS** in both the development tree and a clean extracted package. Unchanged QtWuziqi rerun reports **28 cache hits / 0 misses**. PR6 remains **PARTIAL** because four binary blobs are still acquisition gaps, Qt compiler context is incomplete, and a substantially larger unrelated application is still required.

### PR6C — qView development oracle O-003 / semantic-action refinement — MECHANISM PASS, PR6 PARTIAL

The pinned qView source was manually inspected before a complete local cold SCAN could be executed. qView is therefore retained as a **development oracle**, not counted as the final blind transferability holdout. Its value is to expose generic scanner requirements without allowing later certification to pretend the specimen was unseen.

Oracle-driven v0.13 mechanisms include:

- stable semantic QAction identities separate from physical clone routes;
- `surface_instance` objects for cloned routes;
- payload-key equality/prefix dispatch cases;
- bounded indexed `dynamic_surface_family` objects;
- explicit semantic-action dispatch gaps;
- duplicate-dispatch anomaly preservation;
- direct CMake build-condition contradiction findings.

Controlled v0.13 validation is **66/66 PASS** in the development tree and clean package. A dedicated fixture produces the expected semantic-action/build findings with `MAPPED / 0` integrity issues. v0.13 self-scan is clean and an unchanged rerun reports **56 cache hits / 0 misses**.

Because qView informed the implementation, PR6 final acceptance now explicitly requires a **frozen holdout**: at least one substantial unfamiliar C++/Qt application whose source is not manually analyzed before the v1 candidate scan.

### PR6D — Frozen blind transferability holdout H-001 — RESERVED / UNSCANNED

The final PR6 blind holdout is now reserved before source analysis:

- repository: `sqlitebrowser/sqlitebrowser` (DB Browser for SQLite);
- pinned commit: `4a7359d5c349ca0bc446f94922ec9561fcf50b96`;
- pinned tree: `1ad501f60616ebd644a7e86a92fb9d22666b3e2c`;
- freeze state: repository/commit/tree metadata only; source and expected-answer denominators intentionally **not manually inspected**.

H-001 is not to be used for iterative scanner development before the v1 candidate is frozen. The candidate scanner will perform the first cold source-level examination. Only after those artifacts are sealed may human/LLM review inspect the source and score what SCAN recovered, missed, or misclassified. This prevents qView-style oracle knowledge from contaminating the final transferability certificate.

A replacement holdout is allowed only if H-001 becomes unusable for an external reason; the replacement must be frozen before source analysis and the substitution reason recorded.

### M5 — Semantic synthesis / auditable reconstruction anchors — PROMOTION MECHANISM PASS IN ENGINE v0.19

Engine v0.19 establishes a deterministic gate between semantic proposal generation and canonical reconstruction authority. Humans or LLMs may propose interpretations, behaviors, arteries, nerves, capabilities, and Reconstruction Anchors, but a proposal is promoted only when SCAN can mechanically verify its proof structure.

Implemented M5 mechanism:

- non-mutating `validate-reconstruction`;
- typed proposal schema `scan-reconstruction-proposal/0.1`;
- every promoted claim must reach first-class evidence;
- each Reconstruction Anchor requires typed behavior/artery/nerve/capability support;
- behavior contracts require trigger / observable response / uncertainty;
- Reconstruction Anchors require property / fidelity test / uncertainty;
- MAPPED anchors cannot escalate PARTIAL/BLOCKED/UNKNOWN support or hide visible contradictions;
- rejected proposals leave the canonical graph unchanged;
- successful semantic bundles commit atomically;
- `reconstruction_contract.json` preserves anchor/behavior IDs, proof reachability, source/evidence IDs, contradictions, fidelity tests, and current completeness state;
- `certify-reconstruction` produces a separately sealed child handoff from a verified parent and records parent receipt/manifest SHA-256 lineage;
- sealed/read-only graph inspection uses SQLite immutable mode so ordinary queries do not mutate evidence bytes.

Measured v0.19 mechanism evidence: **102/102 development tests PASS**, **102/102 clean-package tests PASS**, package self-audit **64/64**, LLM-disabled release qualification PASS, required queries **12/12 PASS**, and a fresh installed wheel successfully produced and independently verified both a mechanical parent certification and a reconstruction-aware child certification while preserving the parent DB SHA-256 across read-only `query`/`why` inspection.

Acceptance gate for each selected anchor remains:

- stable RA identity;
- typed incoming semantic relations;
- supporting behavior/pathway/capability objects;
- source evidence objects with exact locators where available;
- visible contradictory/uncertain evidence;
- successful mechanical `why RA-*` traversal;
- meaningful `impact EV-*` traversal.

**M5 mechanism is now established; M5 specimen-level semantic completion remains dependent on complete calibrated specimen evidence.** The controlled qualification anchor proves the gate, not NotepadNext reconstruction completeness.

### M6 — Blind reconstruction experiment — M6A STATIC INFRASTRUCTURE PASS / FULL M6 OPEN

Engine v0.20 establishes the first reproducible source-blind trial infrastructure:

- `prepare-reconstruction-trial` verifies a reconstruction-aware certification and splits it into a deterministic public challenge plus private evaluator;
- the public challenge excludes original source bytes/paths/excerpts, the canonical database, evidence catalogs/graphs, and evaluator internals, while publishing the source-free mechanical requirements needed for a fair reconstruction;
- challenge-bound submissions record source/network/evaluator access and are rejected before scanning if forbidden access is admitted;
- `score-reconstruction-trial` rescans the reconstructed candidate and compares human-surface text/type, binding/effect closure, and MAPPED terminal effect/capability signatures rather than source code;
- mismatch attribution distinguishes reconstruction-agent, semantic-IR, candidate-scanner-coverage, and unresolved-source-evidence domains;
- PARTIAL source terminals remain advisory and do not penalize a candidate that satisfies every MAPPED requirement;
- candidate bytes, scan outputs, scorecard, receipt, and lineage are sealed in a trial manifest;
- `verify-reconstruction-trial` detects post-score tampering;
- deterministic challenge generation is regression-tested.

Measured v0.20 release evidence: **111/111 development tests PASS**, **111/111 clean-package tests PASS**, package self-audit **67/67**, LLM-disabled query qualification **12/12**, and a fresh installed wheel successfully completed mechanical parent certification -> reconstruction-aware child certification -> public/private trial split -> challenge-only controlled candidate generation -> private scoring -> sealed trial verification with **1/1 anchor PASS and fidelity_score 1.0**. The controlled generator consumed only public challenge data, but it is not a capable external coding agent and therefore does not complete PR7.

Full M6 still requires handing only the public challenge to a capable external coding agent that has never seen the original source, then measuring fidelity across:

- visible controls and alternate routes;
- behavior/effects/feedback;
- lifecycle and persistence;
- failure/cancel/error semantics;
- NEST-derived abilities;
- dynamic and extension-created surfaces;
- obscure/easter-egg behavior;
- platform-specific behavior selected for the test.

For every mismatch, classify whether the failure lies in scanner extraction, semantic synthesis, reconstruction IR/anchors, candidate scanner coverage, the coding agent, or unresolved source uncertainty. Runtime behavior testing is M6B and remains separately authorized under A1.

### M7 — Progressive deepening / controlled experiments

Use D0-D5 depth selectively. If static evidence cannot resolve purpose and the user authorizes deeper work, SCAN may build isolated harnesses, reconstructed fragments, or controlled copies to test hypotheses. Experimental evidence remains clearly distinct from original source evidence.

## Current route to the v1 quality gate

As of engine v0.26 / project v0.32, the strongest implemented areas are the deterministic/evidence substrate, graph integrity, exact acquisition semantics, bounded compiler recovery, adaptive substrate handoff, evidence-preserving human-surface classification, deep call/effect closure, and sealed certification. The full NotepadNext calibration confirms those strengths and makes the largest remaining engineering risk concrete: **PR3/PR4 closure of the 11 unresolved and 59 partial real surfaces, persistence, lifecycle, dynamic-route, and capability closure**, followed by semantic convergence, reconstruction proof, and holdout certification.

The recommended order from here is:

1. classify and close the remaining 11 unresolved and 59 partial surfaces with generic rules and adversarial fixtures, then repeat the sealed manifest calibration until the agreed convergence threshold is met;
2. use the established M5 promotion gate on calibrated specimen evidence and promote only source-traceable reconstruction contracts;
3. use the M6A split/scoring infrastructure with a capable external source-blind coding agent, then add separately authorized M6B behavior evaluation and close scanner/semantic-IR/anchor-caused mismatches;
4. complete PR1/PR8 security, malformed-input, resource-limit, install, schema/rebuild, load/resume, cross-platform, performance, mechanical-independence, and operator-documentation gates;
5. freeze the v1 candidate, then run PR6 H-001 (`sqlitebrowser/sqlitebrowser`) cold with no manual source-answer seeding;
6. execute the final packaged-byte certification sweep across release fixtures/specimens.

The project remains deliberately below the v1 claim until all PR1-PR8 gates pass.

## Definition of "production-ready" for SCAN v1

SCAN is intentionally open-ended, so v1 needs a finite quality boundary. The recommended v1 claim is **certification-grade static scanning for C++/Qt desktop applications, with an adapter architecture that preserves explicit `UNKNOWN`/`BLOCKED` coverage for unsupported substrates**. v1 should not claim universal-language completeness.

A v1 release is ready only when all of the following gates pass:

### PR1 — Deterministic core integrity

- canonical database/projection integrity audit returns no ERRORs on release fixtures;
- stable IDs and exported projections are reproducible for unchanged specimen bytes;
- corrupted manifests, hash mismatches, malformed source, ambiguous names, symlinks/external references, and parser failures stay explicit;
- schema/version migration or clean-rebuild behavior is documented and tested;
- archive/path traversal, pathological file size, decoding, and resource-limit cases are hardened.
- the supported D0-D3 / Stage 1-2 path passes with LLM access disabled, producing canonical evidence/projections/audit/closure/query outputs deterministically.

### PR2 — C++/Qt structural depth

- compiler-grade or established parser/AST integration replaces regex as the primary C/C++ symbol/call mechanism;
- declarations/definitions, overloads, templates, lambdas, signal/slot connections, helper dispatch, virtual/interface calls, macros/conditional compilation, and generated Qt code have explicit resolution states;
- CFG/call/state/effect evidence is sufficient to trace important control paths beyond the first handler.

### PR3 — Human-surface and framework closure

- Qt actions, widgets, menus, toolbars, dialogs, docks, context menus, shortcuts, gestures, drag/drop, CLI, OS events, accessibility-relevant surfaces where exposed, and dynamic factories are denominator-accounted;
- Scintilla/Lexilla native keyboard/mouse/editing behavior is mapped as body or NEST-supplied capability with provenance;
- each supported surface has explicit entry -> route -> effect/state -> feedback closure or a visible gap.

### PR4 — NEST, persistence, and extension depth

- filesystem, settings, clipboard, process, printing, network, IPC, environment, platform guards, permissions, extension/script/plugin receptors, and persistence pathways are mapped with capability provenance;
- intrinsic/borrowed/coupled/potential/blocked/unknown capability states are mechanically supportable where evidence permits.

### PR5 — Full pinned-specimen calibration

- the complete pinned NotepadNext bytes are acquired and hashed;
- a cold full-body scan runs without using the manual baseline as hints;
- mechanical results are compared against the preserved manual baseline, including the known QAction denominator, helper-mediated routes, dynamic controls, recurrence, CLI/OS surfaces, NEST boundaries, and anomalies;
- every discrepancy either improves reusable machinery or remains an explicit unresolved limitation;
- a second clean run demonstrates deterministic stability/cache behavior.

### PR6 — Transferability calibration

Current status: **PARTIAL**. TR-001 and TR-002B prove transferability-driven refinement on unrelated specimens. qView O-003 strengthens the engine but is now a development oracle because its source informed v0.13. Final PR6 therefore requires a separate frozen holdout.

- qView is retained as a development/regression specimen rather than counted as the final blind test;
- H-001 is frozen as `sqlitebrowser/sqlitebrowser@4a7359d5c349ca0bc446f94922ec9561fcf50b96` / tree `1ad501f60616ebd644a7e86a92fb9d22666b3e2c`, with no source-answer analysis before the candidate cold scan;
- H-001 is scanned end-to-end only after the v1 candidate is frozen, then independently reviewed/scored;
- synthetic adversarial fixtures continue to exercise ambiguous/dynamic/hidden/conditional paths.

### PR7 — Reconstruction proof

- selected behaviors/arteries/nerves/capabilities become source-traceable semantic objects;
- every promoted reconstruction anchor passes `why RA-*` to first-class evidence and meaningful inverse `impact`;
- a blind coding agent that never sees source reconstructs a surrogate from the SCAN package;
- mismatches are classified as scanner, semantic-IR, reconstruction-anchor, coding-agent, or unresolved-evidence failures and fed back into SCAN.

### PR8 — Release engineering

- installable package/CLI with pinned supported Python versions;
- documented schemas, command reference, example scan, failure semantics, depth modes, and non-destructive boundary;
- performance/load/resume testing on repositories materially larger than the fixtures;
- deterministic package manifest and self-audit command suitable for handoff between machines/agents.
- a mechanical query acceptance suite covers unresolved surfaces, subprocess/NEST boundaries, extension receptors, external-write paths, UNKNOWN routes, NEST-dependent actions, disconnected handlers, high-connectivity junctions, dynamic registrations, hidden-surface candidates, capability-without-human-route, and permission/authentication pathways where applicable.

Only after PR1-PR8 pass should SCAN v1 be called "production-ready" in the project's quoted sense. Later language/framework adapters can expand scope without weakening the v1 C++/Qt quality claim.

## Current production-grade assessment at engine v0.26 / project v0.32

The architecture is mature enough that the remaining work is mostly **certification, depth closure, and release hardening**, not invention of the basic SCAN model. However, the highest-consequence proof gates are still open, so the project must not yet be called production-grade.

Current gate assessment:

- **PR1 Deterministic core integrity: VERY STRONG PARTIAL, HARDENING ACTIVE.** Canonical evidence graph, stable IDs, audits, projection/package manifests, digest validation, ambiguity preservation, reproducible cache behavior, symlink/path controls, source-reread verification, per-item and aggregate budgets/cancellation, SQLite corruption/schema policy, parser exception containment, and resume-after-budget behavior are working. Remaining: broader malformed/adversarial corpus beyond current cases, archive-ingest safety if archives become an input mode, more schema migration history as schemas evolve, and broader platform/Python-version testing.
- **PR2 C++/Qt structural depth: STRONG PARTIAL.** Compiler-assisted extraction, fallback structure, overload/type/receiver resolution, semantic QAction identity, payload dispatch, generated-code contracts, and deep effect closure exist. Remaining: stronger whole-program CFG/data flow, macro/generated-code closure, more template/virtual dispatch cases, and more exact value propagation.
- **PR3 Human surface/framework closure: PARTIAL TO STRONG PARTIAL.** Designer/programmatic widgets, actions, shortcuts, events, dialogs, dynamic families, CLI, drag/drop and several framework routes are represented. Remaining: accessibility-relevant surfaces where exposed, broader native/framework behavior, exact alternate-route equivalence, and stronger Scintilla/Lexilla user-behavior closure.
- **PR4 NEST/persistence/extensions: STRONG PARTIAL.** Typed boundaries, persistence, guards, error/cancel/retry, platform conditions, extension receptors and capability states exist. Remaining: more exact cross-platform configured-build semantics and end-to-end provider/effect closure on full real applications.
- **PR5 Full pinned NotepadNext calibration: MECHANICAL PASS / CALIBRATION PARTIAL.** Exact commit/tree bytes were verified, v0.26 completed two byte-identical LLM-disabled manifest scans plus a 4,186-hit/0-miss cache proof, and the final installed-wheel result independently verifies 12/12 files. The corrected denominator preserves all declared/factory surfaces and reports 310 bound / 59 partial / 11 unresolved of 380. Compiler evidence covers 378/394 translation units, while real-route closure, persistence, lifecycle, dynamic-route, capability, platform, and semantic-convergence gaps remain.
- **PR6 Transferability: PARTIAL, HOLDOUT FROZEN.** Multiple unrelated specimens have improved the scanner. qView remains a development oracle. H-001 (DB Browser for SQLite) is now frozen before source analysis and reserved for the final blind candidate scan.
- **PR7 Reconstruction proof: PARTIAL / M5 + M6A MECHANISM PASS.** Evidence-gated behavior/anchor promotion, fidelity-test contracts, contradiction/coverage discipline, immutable certification lineage, deterministic public/private blind-trial splitting, source-free scoring requirements, candidate rescanning, mismatch attribution, sealed trial verification, and installed-wheel challenge-only controlled reconstruction scoring are working. Remaining: apply the pipeline to complete calibrated real-specimen evidence, use a capable external coding agent under genuine source isolation, and complete behavior-level M6B fidelity evaluation.
- **PR8 Release engineering: VERY STRONG PARTIAL.** Deterministic package/projection byte audits, 144-test clean-package qualification, reproducible ZIP/wheel builds, fresh Python 3.13.13 installation, aggregate budgets/cancellation, resume regression, LLM-disabled 12-query qualification, sealed specimen/reconstruction/trial certification and verification, immutable read-only inspection, and full 1,928-file cold/warm evidence are working. Remaining: broader supported Python/platform matrix, final operator/schema documentation sweep, and final candidate certification after PR5/PR7 and the frozen PR6 holdout.

A useful way to state readiness is: **the scanner architecture and cold-certification mechanics are advanced, but calibration has not converged enough for the v1 production-grade label.** PR5 generic convergence and the external-agent/M6B portions of PR7 are the two largest proof gates; real-world PR1/PR8 qualification depth and the frozen PR6 holdout are the other release blockers.

## Product acceptance principle

The target is not "a good summary of an application." The target is a transferable evidence substrate from which another system can determine:

- what the application exposes to humans;
- what semantic abilities those controls provide;
- what hidden or unusual abilities also exist;
- how actions travel through the body;
- what the application depends on from its NEST;
- what the user observes afterward;
- what remains unknown;
- and why every reconstruction requirement exists.

When that structure is strong enough, reconstruction becomes a testable engineering problem instead of an exercise in prose imitation.
