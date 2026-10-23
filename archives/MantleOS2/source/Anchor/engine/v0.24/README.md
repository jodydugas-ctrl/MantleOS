# SCAN Engine v0.24 development

Status: **development / calibration candidate**, not a frozen release.

This tree carries the reusable SCAN v0.23 mechanical evidence architecture forward while adding the first cross-substrate flexibility work learned from the frozen Moji Electron/React/TypeScript calibration.

The v0.23 tree remains historical and unchanged. Nothing in this directory changes the active A1-A8 governance anchors.

## What v0.24 adds

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

## Development gates

The v0.24 calibration workflow requires:

1. `engine/v0.23` is byte-for-byte unchanged relative to `main`.
2. The full v0.24 regression suite passes.
3. The specimen commit and tree identity match the frozen calibration target.
4. The scanner does not install or execute the specimen.
5. LLM credentials are blank during mechanical scanning.
6. Two fresh adapted runs produce byte-identical canonical projections.
7. Two fresh runs produce byte-identical assimilation workbenches.
8. Canonical integrity reports contain zero ERROR issues.
9. Newly learned scanner rules are generic and fixture-tested.
10. The package manifest is regenerated from the final v0.24 bytes before release qualification.

## Running

Install the development scanner:

```bash
python -m pip install -e Anchor/engine/v0.24
```

For TypeScript/JavaScript AST extraction, provide a scanner-owned TypeScript installation and point `SCAN_TYPESCRIPT_MODULE` at it. The scanner must not resolve that parser from specimen dependencies.

Then scan normally:

```bash
scan-body scan /path/to/specimen --out .scan --specimen-id my-specimen
```

Canonical evidence remains in the normal SCAN outputs. If further adaptation is warranted, `.scan/assimilation/` is created automatically.

## Release note

`PACKAGE_MANIFEST.json` in the development tree is provisional until the v0.24 calibration workflow regenerates it from the final candidate bytes. Do not treat this development directory as a sealed certification package until release qualification explicitly passes.
