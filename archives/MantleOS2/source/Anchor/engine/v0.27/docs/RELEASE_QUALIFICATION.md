# SCAN v0.23 Release Qualification Contract

This document describes the **mechanical** release-hardening contract. It does not promote SCAN to production-grade by itself.

v0.23 adds regression coverage for retaining valid source-local Clang AST evidence after nonzero compiler exits, while preserving diagnostic gaps and PARTIAL compiler coverage. Compiler JSON parse size is bounded and oversized output must degrade to an explicit PARTIAL gap without suppressing fallback extraction. v0.23 also requires byte-identical canonical JSON/Markdown projections and projection hashes across two fresh unchanged scans; volatile execution timestamps do not belong in canonical projections. v0.22 added runtime-vs-reference context regression coverage for C-family comments, vendored/test/deployment/static-asset paths, and root project documentation. It also requires one-mask-per-translation-unit fallback parsing and verifies that repeated lexical NEST/receptor occurrences aggregate without losing direct evidence. v0.21 added cross-platform local-file identity regression coverage and exact revision-to-commit receipt normalization. The remaining qualification contract is inherited from v0.20.

## Bounded execution

All limits are opt-in except the existing per-file 64 MiB ceiling. A zero aggregate value disables that ceiling.

- `max_total_bytes` and `max_materialized_files` are enforced during deterministic inventory/materialization. The visible file census continues and over-budget entries remain explicit blocked anatomy.
- `max_extraction_seconds`, `max_nodes`, `max_edges`, and `max_evidence` are checked at safe extraction boundaries. SCAN never commits half of one adapter result merely to hit an exact numeric ceiling.
- external cancellation uses the same safe-boundary mechanism.
- a bounded stop emits a `scan_budget` finding and marks remaining parser-eligible files `PARTIAL` with `parser_state=BUDGET_STOPPED`.

A budget stop is therefore a coverage statement, not a successful-completion claim.

## Canonical store corruption and schema policy

`scan_index.sqlite` is a **derived canonical scan artifact**, not specimen source. SCAN v0.20 retains SQLite `PRAGMA user_version=1`.

On a new scan:

1. the existing database is opened and `PRAGMA quick_check` is executed;
2. a corrupt database is quarantined alongside the output using a timestamped `.corrupt.*.sqlite` name;
3. a fresh canonical store is built from the specimen bytes;
4. the scan result records `store_recovery` so recovery is not silent.

Read-only consumers do not auto-rebuild a corrupt database. They fail instead, preserving the damaged artifact for diagnosis.

Compatible legacy schema version `0` is promoted. If the legacy current-map table shape is incompatible, derived map tables are rebuilt while a compatible content-addressed extraction cache may survive. A database declaring a schema newer than this engine supports is refused rather than downgraded.

## Package self-audit

`scan-body self-audit <package-root>` validates:

- `PACKAGE_MANIFEST.json` schema;
- exact file presence, byte counts, and SHA-256 values;
- absence of untracked regular package files (ignoring Python cache artifacts);
- engine version agreement between runtime, manifest, and `pyproject.toml`.

With `--scan-output`, it also validates projection hashes and `scan_index.sqlite` with SQLite quick-check.

`scan-body package-manifest <package-root>` regenerates the package manifest deterministically from regular package files.

## Mechanical-independence qualification

`scan-body qualify <package-root>` performs a fresh scanner-owned C++/Qt fixture scan while common LLM API-key environment variables are removed. The qualification then requires:

- package self-audit PASS;
- canonical SQLite and all standard projections emitted;
- integrity audit with zero ERROR issues;
- projection-manifest verification PASS;
- successful execution of the required release query surface.

The release query set covers:

- unresolved human surfaces;
- subprocess/NEST boundaries;
- extension receptors;
- external-write paths;
- routes with explicit UNKNOWN/PARTIAL/BLOCKED state;
- NEST-dependent human actions;
- disconnected handlers;
- high-connectivity junctions;
- dynamic registrations;
- hidden-surface candidates;
- capabilities with no known human route;
- authentication/permission-touching pathways.

A query is accepted when it executes mechanically against the canonical database. A zero-row result can be correct for a specimen and must not be converted into a fabricated finding.

## What this qualification does not prove

It does not replace:

- full pinned NotepadNext calibration (PR5);
- blind H-001 transferability after candidate freeze (PR6);
- source-blind reconstruction proof (PR7);
- large-repository performance/resume measurements;
- cross-platform Python/install certification.
## Parser/adaptor fault containment

A supported scan must survive an ordinary exception from one extraction adapter without dropping the remainder of the specimen. The engine records the affected adapter, version, error class/message, and file as a `parser_failure`, downgrades that file to `PARTIAL`, and continues other independent extraction work. Such a failure is never cached as a successful result.

`MemoryError` remains fatal because continuing after process-level memory exhaustion would make integrity claims unsafe. Adapter-native malformed-input handling may return its own `parser_gap`/`BLOCKED` result when it can do so deterministically.

A release regression also verifies **resume-after-budget**: a deliberately bounded partial run can be followed by an unbounded rerun in the same output directory, reuse valid cache entries from the first pass, and reach a clean full result.
## Wheel installation check

The release process builds a `py3-none-any` wheel and validates it in a fresh Python 3.13 virtual environment. The wheel must install without SCAN runtime dependencies, expose the `scan-body` console entry point, perform a mechanical scan, pass projection verification, and execute all 12 required release queries.

Source-tree installation in an otherwise empty virtual environment may still require a PEP 517 build backend such as `setuptools`; the wheel is therefore the deployable release artifact rather than relying on network acquisition of a build backend at install time.

## Current measured load/resume checkpoint

See `PERFORMANCE_BASELINE.md`. In the current Python 3.13.5 environment a scanner-owned 321-file C++/Qt-ish tree completed in 4.5326 seconds cold and 0.5398 seconds warm. The unchanged warm pass produced 1,542 extraction-cache hits and 0 misses with `MAPPED / 0` integrity issues. This is a development baseline, not a cross-platform SLA or a substitute for a large real-application benchmark.



## Agent-facing specimen certification

`scan-body certify <package-root> <specimen-root> --out <cert-dir> [--bundle <zip>]` is the v0.18 handoff gate for embedding SCAN inside another agent. It performs a fresh local scan with common LLM credentials removed, verifies the release package, runs canonical integrity/projection/query gates, writes `certification_receipt.json`, seals every emitted artifact in `CERTIFICATION_MANIFEST.json`, and can emit a stable-order ZIP bundle.

The receipt intentionally separates **mechanical trust** from **coverage completeness**. Top-level `state=PASS` means the evidence handoff passed mechanical integrity gates. It never means the specimen is fully understood. `coverage.execution_state`, the multidimensional completeness vector, acquisition gaps, parser failures, parser gaps, and budget status remain explicit inputs to the consuming agent's decision.

`scan-body certify-manifest <package-root> <source-manifest> --content-root <verified-bytes> --out <cert-dir>` applies the same gate without discarding provider/repository/commit/tree provenance from exact-revision acquisition.

`scan-body verify-certification <cert-dir>` re-hashes every sealed file and re-validates the projection manifest/database. A byte change after certification therefore invalidates the handoff without requiring an LLM to notice the drift.

The certification directory contains only SCAN-owned outputs and receipts; the specimen source is not copied into the handoff by this command. This keeps evidence transport separate from source transport and preserves the ordinary read-only specimen boundary.


## M5 semantic-promotion qualification

v0.19 adds a stricter gate between interpretation and canonical reconstruction requirements. Release regressions require:

- validation is non-mutating;
- unsupported anchors are rejected before canonical insertion;
- every promoted claim reaches first-class evidence;
- every promoted anchor has typed semantic support and a fidelity test;
- MAPPED coverage cannot escalate weaker or contradicted support;
- successful promotion refreshes `reconstruction_contract.json` and the projection manifest;
- semantic object/relation/completeness writes commit atomically as one bundle;
- a verified mechanical certification can produce a separately sealed reconstruction-aware child handoff while the parent bytes remain unchanged;
- the child receipt records parent manifest/receipt SHA-256 lineage;
- read-only canonical inspection is byte-preserving and does not create SQLite WAL/SHM sidecars.

This gate proves evidence-backed promotion discipline. It does not prove the proposed interpretation is the only reasonable semantic reading, and it does not substitute for PR7's source-blind reconstruction experiment.


## M6A reconstruction-trial qualification

v0.20 adds the first reproducible blind-reconstruction experiment boundary. Release regressions require:

- a verified reconstruction certification splits into a deterministic public challenge and a separately sealed private evaluator;
- the public challenge contains no original specimen source bytes, canonical SQLite database, evidence catalog/graph, source evidence excerpts, original local source paths, or evaluator payload;
- the public challenge publishes the source-free scoring requirements necessary for a fair test, while private evaluator IDs/lineage/scoring internals remain withheld;
- challenge and evaluator manifests detect tampering;
- a submission is bound to exactly one challenge and any admitted original-source/parent/evaluator/network-source access invalidates the trial before scanning;
- a source-blind candidate with the mechanically expected surface route can score PASS;
- omission of a strongly evidenced surface on an adequately scanned candidate is attributed to `RECONSTRUCTION_AGENT`;
- source uncertainty and candidate scanner uncertainty remain distinct attribution states;
- the scored candidate and candidate scan are sealed in a trial manifest and later tampering is detected;
- deterministic challenge generation produces byte-identical public ZIPs for an unchanged parent certification.

This gate is **M6A static reconstruction proof infrastructure**, not full PR7. The current evaluator does not execute the reconstructed application. Runtime behavior tests require separately authorized isolated execution and remain future M6B work under A1. A full PR7 pass also requires an external capable coding agent that has not seen the original source.
