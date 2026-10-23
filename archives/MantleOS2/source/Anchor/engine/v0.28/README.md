# SCAN Engine v0.28

Status: **integration candidate — not release-qualified**.

v0.28 advances the v0.27 evidence-first scanner into a closed reconstruction-verification loop while preserving the A1-A8 governance contract. The v0.27 scanner is the base; its newer Qt routing, bounded extraction, evidence graph, NEST model, reconstruction-trial machinery, and certification code remain the authority for Stage 1.

This candidate intentionally has **no `PACKAGE_MANIFEST.json` yet**. The copied v0.27 manifest was removed because its hashes and version would be false after modification. A new manifest must be generated only after the v0.28 bytes and tests are final.

## What v0.28 adds

### Anchor Code 0.9

`scan/anchor_code.py` projects the canonical semantic graph into a deterministic, line-oriented Anchor Code representation.

The projection preserves the evidence firewall:

- static graph relations are marked as statically derived rather than observed runtime behavior;
- `UNKNOWN`, `PARTIAL`, and `BLOCKED` coverage survive;
- source evidence remains traceable;
- the projection is downstream of `scan_index.sqlite` and cannot rewrite canonical evidence.

Command:

```bash
scan-body anchor-code .scan/scan_index.sqlite --out-dir .scan
```

### Portable Anchor Blueprint

`scan/agent_blueprint.py` emits one Markdown handoff for a coding agent. It includes the evidence-supported human surface, state/routing anatomy, effects and NEST boundary, build/dependency anatomy, explicit uncertainty, and an embedded machine-readable conformance manifest.

Command:

```bash
scan-body anchor-blueprint .scan/scan_index.sqlite
```

The Blueprint is a derived reconstruction artifact, not a replacement authority for the canonical evidence graph.

### Fresh-scan reconstruction conformance

`scan/conformance.py` implements the important authority separation learned in the terminal branch:

`Blueprint -> coding agent -> candidate -> fresh SCAN -> mechanical comparison`

A coding agent does not certify its own implementation. SCAN rescans the candidate read-only and compares the mechanically recovered contracts with the source Blueprint.

Command:

```bash
scan-body conform "Example Anchor Blueprint.md" ./candidate --out ./conformance
```

Static conformance does not claim pixel, runtime, timing, network, or performance equivalence.

### Static HTML/CSS human-surface extraction

`scan/adapters/web_frontend.py` adds deterministic browser-surface extraction for HTML and CSS without executing the specimen.

It maps:

- buttons, inputs, selects, textareas, links, summaries, and canvas surfaces;
- stable label / aria / associated-label identity;
- inline DOM event bindings;
- stylesheet selectors and declarations as visual contracts.

A canvas is treated as a **presented surface by default**. It becomes an actionable input surface only when human-event evidence supports that classification. This mirrors v0.26's Qt surface-denominator correction: visible does not automatically mean actionable.

## Preserved v0.27 behavior

v0.28 is based on the v0.27 tree rather than the older terminal scanner core. In particular, the v0.27 Qt `QEvent::FileOpen` correction is retained: a file-open surface is bound only when the evidence is inside the actual enclosing `event()` implementation.

The GitHub NEST vocabulary is also retained. Terminal-derived reconstruction contracts recognize both historical `environment_boundary` objects and the current `nest_boundary` representation, but v0.28 does not replace A8's NEST model.

## Qualification state

This branch is deliberately **not frozen** and **not certified**.

Before promotion:

1. add/port focused tests for Anchor Code, Blueprint, conformance, and web surfaces;
2. run the full v0.28 regression suite;
3. rerun the frozen calibration specimens and compare against v0.27;
4. verify deterministic duplicate scans;
5. inspect newly closed web routes for false joins;
6. regenerate `PACKAGE_MANIFEST.json` from the final bytes;
7. run package/self-audit and release qualification;
8. update project-level evidence/report documents with only executed results.

Until those gates are complete, v0.26 remains the latest frozen release and v0.28 remains an integration candidate.
