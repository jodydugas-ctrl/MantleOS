# SCAN Adaptive Substrate Assimilation

Status: experimental implementation on the post-v0.23 development branch. This mechanism implements A1-A4, A7, and A8; it does **not** add a ninth governance anchor.

## Purpose

SCAN must not become permanently limited to the languages and frameworks its original authors anticipated. When a frozen specimen exposes an unsupported runtime language, parser failure, unresolved control surface, missing effect path, or structural resolution gap, the system should turn that surprise into reusable scanner knowledge.

This is called **adaptive substrate assimilation**.

The LLM is useful here because it can reason about an unfamiliar framework and author the reusable extraction machinery that conventional code does not yet contain. The LLM is not allowed to substitute interpretation for evidence. Its output is scanner code, tests, and hypotheses; the resulting scanner must still discover facts mechanically.

## Cycle

1. **FREEZE** — preserve exact specimen identity (repository/revision/tree/content fingerprint).
2. **SCAN** — run the current deterministic scanner unchanged.
3. **DETECT** — mechanically identify unsupported runtime languages, parser failures, unresolved surface routes, incomplete effect closure, and ambiguous structural resolutions.
4. **PACKAGE** — automatically create an inert `assimilation/` workbench containing:
   - `assimilation_request.json`
   - `evidence_samples.json`
   - `candidate_adapter.py`
   - `candidate_probe.py`
   - `test_candidate_adapter.py`
   - `LLM_ASSIMILATION_TASK.md`
   - `promotion_gate.json`
   - `WORKBENCH_MANIFEST.json`
5. **ADAPT** — an authorized LLM/coding agent edits only scanner-owned candidate machinery. It may inspect the pinned source but must not execute, import, build, instrument, or stimulate the specimen during ordinary assimilation.
6. **REGRESS** — run the existing SCAN regression suite. Existing substrate competence may not be traded away for the new specimen.
7. **RESCAN** — compare the frozen baseline against the candidate adapter on the same exact specimen.
8. **DETERMINISM** — run the candidate scan twice from a fresh state and require byte-identical canonical projections.
9. **ADVERSARIAL ROUTE CHECK** — inspect newly closed human/effect routes for false joins. A lower honest closure score is preferable to contaminated closure.
10. **GENERALIZE** — every learned rule must be encoded generically and fixture-tested. Specimen filenames, UI labels, symbol names, IPC channels, expected counts, and known answers are forbidden as extraction rules.
11. **PROMOTE** — move the candidate into the trusted scanner only after the promotion gate passes. Preserve the baseline and calibration evidence.
12. **REUSE** — the next specimen using the same substrate receives the new adapter mechanically, without requiring another full-repository LLM reading pass.

## Authority boundaries

Adaptive assimilation does not alter the A2 split:

- deterministic code owns discovery, enumeration, parsing, measurement, graph construction, classification, and closure;
- an LLM may diagnose why existing code is blind and author candidate scanner code;
- generated candidate code is never automatically executed by an ordinary scan;
- candidate code has no authority to promote semantic claims merely because they are plausible;
- canonical evidence from the baseline scan remains immutable with respect to the assimilation workbench;
- promotion requires tests, determinism, provenance, and evidence-backed improvement.

## Anti-overfit rule

A specimen is a calibration instrument, not an answer key.

An adapter learned from specimen X is acceptable only if its rules describe a language/framework mechanism that could operate on specimen Y without knowing X existed. If removing all specimen-specific names makes the rule impossible to express, the rule is not ready for promotion.

## Lessons captured from the Moji calibration

The Electron/React/TypeScript flexibility calibration established several transferable rules now encoded in the scanner development branch:

- TypeScript/JavaScript require AST-based structural extraction rather than generic text matching.
- React `memo(...)` and hook-assigned functions such as `useCallback(...)` must preserve semantic function identity.
- Physical JSX controls require source-location identity; equal labels do not prove they are the same surface.
- Repeated API invocations require source-location call-site identity; equal callees do not prove they are the same pathway.
- Electron `contextBridge` and typed IPC form useful cross-process artery seams.
- BODY capability must remain distinct from Electron/Node/OS NEST capability.
- React state mutation can be a legitimate terminal for an action that does not cross the NEST.
- dependency/lock/build metadata must not be promoted into runtime NEST boundaries merely because it contains URLs or package names.
- framework summary edges are acceptable only when the detailed evidence path already exists; they may compress provenance but not invent it.

The most important calibration lesson was negative: an intermediate adapter increased apparent effect closure by incorrectly merging unrelated `ipcRenderer.invoke(...)` call sites. The increase was rejected, the identity rule was corrected, and a regression test was added. Adaptive assimilation therefore optimizes for **truthful transferable coverage**, not monotonically increasing scores.
