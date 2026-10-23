# SCAN Engine v0.26

Status: **frozen calibration release**. Mechanical release and PR5 certification gates pass; semantic calibration remains `PARTIAL`.

This tree carries the frozen SCAN v0.25 adaptive/bounded engine forward and corrects the generic human-surface denominator without hiding real interactive controls.

The v0.23-v0.25 trees remain historical and unchanged. Nothing in this directory changes the active A1-A8 governance anchors.

## What v0.26 carries forward from v0.25

### TypeScript / React / Electron extraction

The scanner now has generic, specimen-independent machinery for:

- TypeScript/JavaScript AST extraction through a scanner-owned parse-only TypeScript probe;
- function/class/import/call structure;
- React JSX human surfaces and event entrances;
- React component prop routing;
- `memo(...)`, hook-assigned functions such as `useCallback(...)`, and React state transitions;
- source-location identity for physical JSX controls;
- source-location identity for repeated API call sites;
- Electron `contextBridge`, preload APIs, typed IPC channels, and main-process registrations;
- BrowserWindow and application lifecycle seams;
- Node/Electron filesystem, native dialog, shell/browser, update, userData, and export effects;
- electron-builder/file-association and packaging metadata;
- BODY/NEST distinction across renderer, preload, main process, Node, Electron, and operating-system capability.

These adapters contain no Moji-specific filenames, labels, symbols, channel names, expected counts, or behavior answers.

### Adaptive substrate assimilation

Ordinary `scan-body scan` now keeps canonical Stage 1 scanning deterministic and LLM-free, then performs a secondary gap assessment.

If the completed scan exposes an unsupported runtime language, parser failure, unresolved human route, incomplete effect path, or structural resolution gap, SCAN creates an inert `assimilation/` workbench beside the canonical scan output.

The workbench includes:

- `assimilation_request.json`
- `evidence_samples.json`
- `candidate_adapter.py`
- `candidate_probe.py`
- `test_candidate_adapter.py`
- `LLM_ASSIMILATION_TASK.md`
- `promotion_gate.json`
- `WORKBENCH_MANIFEST.json`

Generated candidate code is **never executed automatically**. It is a coding handoff for an authorized LLM/human agent. Promotion into the trusted scanner requires regression tests, a frozen baseline comparison, two fresh deterministic rescans, evidence/integrity gates, and adversarial review of newly closed routes.

See [`docs/ADAPTIVE_ASSIMILATION.md`](docs/ADAPTIVE_ASSIMILATION.md).

## Why this preserves A2

The LLM may recognize an unfamiliar framework and write reusable scanner code. It does not become the scanner.

The cycle is:

`unknown substrate -> deterministic gap evidence -> LLM/coding adaptation -> reusable adapter -> tests -> deterministic rescan -> evidence-backed promotion`

Facts still enter the canonical graph through reusable mechanical extractors. The assimilation workbench remains secondary engineering output and cannot rewrite the evidence produced by the baseline scan.

## Calibration specimen

The development calibration is pinned to:

- Repository: `alexishida/Moji`
- Commit: `7793dbabc880a950b5003dcfd57c1222b279b807`
- Git tree: `b4e0e6a4d2010a6d584f40b01ab5ffad7bf18fea`

Moji is used as a calibration instrument, not an answer key. The scanner rules must transfer to unrelated Electron/React/TypeScript projects.

One important negative result is preserved in the tests: an early adapter merged repeated `ipcRenderer.invoke(...)` calls that shared a callee name, falsely connecting unrelated human actions and filesystem effects. v0.24 therefore treats raw call sites as source-location identities and allows higher-level aggregation only after provenance-safe extraction.

## What v0.25 added

### Bounded Clang AST recovery

Clang stdout and stderr are drained concurrently so a compiler process cannot deadlock on a full pipe. Full AST output is retained only up to the configured parse ceiling. If the full translation-unit dump times out or crosses that ceiling, SCAN derives one declaration filter mechanically from the source, retries with the same bounded runner and a separately bounded four-times-longer recovery window, and marks any recovered compiler evidence `PARTIAL`.

If bounded recovery cannot produce a valid AST, the generic C++/Qt adapter remains available as the fallback. The recovery path never runs specimen code and contains no specimen-specific names or expected answers.

### Deterministic compiler evidence

Clang's process-local pointer identifiers are used only while resolving a single in-memory AST. They are never persisted and never contribute to stable output identifiers. Call-site identity instead uses deterministic source offsets and excerpts. Bounded recovery records its configured limits and outcome without persisting the scheduler-dependent race between a timeout and an output-limit kill.

Case-equivalent capability tokens now use a total ordering, removing another platform-dependent projection difference.

## What v0.26 adds

### Evidence-preserving surface classification

Ordinary C++/Qt `ui->object` accesses remain first-class `ui_object_reference` evidence, but they no longer enter the human-surface denominator merely because an object was read during setup or state synchronization. A declaration-less UI reference is promoted to a `surface_reference` only when it is proven to be the sender in a Qt signal connection. This preserves connected controls that lack a declaration while excluding labels, menus, setup containers, and other non-interactive object observations.

Command-line consumers such as `.value(...)`, `.isSet(...)`, and `.positionalArguments()` are classified as CLI evidence only when their receiver is proven to be a `QCommandLineParser` variable or parameter. Unrelated application objects with similarly named methods no longer create pseudo-options.

These rules are generic and fixture-tested. They contain no NotepadNext-specific names, paths, counts, or oracle conclusions.

## Release gates

The v0.26 calibration verified:

1. Frozen `engine/v0.23` through `engine/v0.25` remain unchanged.
2. The full v0.26 regression suite passes: 144 tests, with three expected Windows symlink-privilege skips.
3. The specimen commit and tree identity match the frozen calibration target.
4. The scanner does not install or execute the specimen.
5. LLM credentials are blank during mechanical scanning.
6. Two fresh exact-manifest runs produce byte-identical canonical projections and identical canonical database rows.
7. All 330 non-reference surfaces retain their v0.25 binding/effect states and terminal/feedback counts.
8. Canonical integrity reports contain zero ERROR issues.
9. Newly learned scanner rules are generic and fixture-tested.
10. The package manifest is regenerated from the final v0.26 bytes before release qualification.

## Running

Install the frozen scanner:

```bash
python -m pip install -e Anchor/engine/v0.26
```

For TypeScript/JavaScript AST extraction, provide a scanner-owned TypeScript installation and point `SCAN_TYPESCRIPT_MODULE` at it. The scanner must not resolve that parser from specimen dependencies.

Then scan normally:

```bash
scan-body scan /path/to/specimen --out .scan --specimen-id my-specimen
```

Canonical evidence remains in the normal SCAN outputs. If further adaptation is warranted, `.scan/assimilation/` is created automatically.

## Release note

The two accepted v0.26 cold scans are byte- and row-identical. The surface denominator contracts from 488 to 380 solely by removing 108 false reference surfaces: 37 metadata-derived pseudo-options and 71 ordinary UI-object accesses. All 327 declared human surfaces, three factory outputs, 147 QActions, four real CLI options, and their established closure states remain unchanged. Mechanical certification is PASS; 59 partial and 11 unresolved surfaces plus compiler, lifecycle, persistence, capability, platform, and reconstruction gaps keep PR5 calibration PARTIAL. Frozen artifacts and receipts are under [`../../releases/v0.26/`](../../releases/v0.26/).
