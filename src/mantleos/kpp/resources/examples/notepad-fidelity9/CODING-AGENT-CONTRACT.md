> **2026-11-13 economy/end-state clarification:** The original automatic +1-per-advance rule is superseded at a covered Chase endpoint. See `CHASE-END-STATE-REVIEW.md` and `LOGICAL-INTERPRETATION.md`. Nine AnchorApplications, 19 additional contract GateConditions (17 runtime + 2 lifecycle), and 27 draft obligations are three separate counts. No native KPP Gate schema is claimed.

# Fidelity 9 — Coding-agent blueprint and truth gates

## Authority and order

**Draft truth input:** `anchorforge-spec.json` (`anchorforge.organ-spec/1`). **Build conformance overlay:** `blueprint-manifest.json`. **Implementation:** nine mapped `.py` Anchor modules. **Local evidence:** full `test_*.py` regression suite, and `python notepad_blueprint_gate.py --verify`. **Acceptance authority:** Baker alone. The implementation does not derive authority from merely passing tests.

Before coding, a coding agent MUST read the full draft specification and manifest. It MUST treat all 27 mandatory obligations as cumulative and preserve all 181 inherited tests, or explicitly flag any proposed exception for human/Baker review before claiming readiness. Altering the spec, manifest, test set and runtime in concert does **not** constitute independent review or Baker authorization. No agent may certify its own revision as a formally approved truth.

## Canonical responsibilities / state

| Anchor | Type | Exclusive truth |
|---|---|---|
| `BH-EDITOR-INPUT` | BlackHole | Preserve observed intent without interpreting or executing it |
| `N-DOCUMENT` | Neutral | Sole authoritative document text, revision, clean baseline / dirty derivation |
| `WH-COMMAND-GUARD` | WhiteHole | Authorize and dispatch untrusted runtime commands and opt-in host effects |
| `N-EDIT-HISTORY` | Neutral | Sole bounded undo/redo stacks and expected revision |
| `N-EDITOR-SURFACE` | Neutral | Transient Tk view/dialog state; route GUI intents through BH then runtime WH |
| `N-FILE-SESSION` | Neutral | Active path/digest; authorized UTF-8 open/new/save effects and baseline handshake |
| `N-CLIPBOARD-SELECTION` | Neutral | Selection range semantics and injected clipboard callback capability |
| `N-SEARCH-REPLACE` | Neutral | Stateless literal match/replace calculations, no second text or history store |
| `WH-BLUEPRINT-GATE` | WhiteHole | Offline candidate-build conformance checks; no document state or runtime dispatch |

Runtime entry: `N-EDITOR-SURFACE -> BH-EDITOR-INPUT -> WH-COMMAND-GUARD -> relevant Neutral owner`. `WH-BLUEPRINT-GATE` audits declared boundaries at build time and must not be inserted into the editor's per-keystroke path.

## Every `advance`: required agent procedure

1. **Stop when the Chase target is met.** Do not automatically increase Anchor count merely because the Baker says `advance`: first evaluate whether the completed output has a distinct unmet Anchor responsibility. If a new Anchor is genuinely needed in a future feature advance, introduce exactly one, preserving existing identities. Never reduce the existing count or leave an Anchor without meaningful truth. Reconfigure existing Anchors/Gates where that is more economical.
2. Recalculate all Anchors globally: identify the complete state graph, ownership, host effects, prerequisites and redundancies. Reassign relationships or rebuild code where justified by simplicity, coverage and preservation. Do not rewrite stable code merely to show activity.
3. Identify prior behavioral truths and any phase-specific assertions intentionally superseded. Describe the *reason* and tests for each exception; no silent regressions.
4. Update the draft specification, manifest, the design and tests together, preserving recognized prior obligation/test IDs unless reviewed. Adjust manifest fidelity and source maps as appropriate for the new round.
5. Run `python notepad_blueprint_gate.py --verify` against the **integrated output**. Check the source/flow map, protected writers, allowed runtime actions, guarded effects and test identities; then execute the test suite. A `valid` static report is not the same as a passing runtime suite.
6. Record the evidence, formal tool limitations, remaining Chase targets and Baker-acceptance status in `status.json` and design review. Offer the artifact for Baker review, not a claim of automatic completion.

## Current offline gate's explicit limits

The gate uses source-level Python AST checks and a preservation registry. It can detect missing identities, changed literal role declarations, changed declared state owners, missing obligation dependencies or flow endpoints, selected duplicate state writes, direct known host calls in unauthorized source modules, removed inherited test method names, and runtime action-allowlist drift.

It **cannot** prove semantic correctness, exhaustive effect confinement, test quality, or authorization against a hostile party able to edit all the gate and manifest files. It does not sign artifacts, sandbox execution, run AnchorForge's native review, execute KPP's full satisfaction workflow or obtain the Baker's approval. Human review and cumulative executed tests remain necessary.


## Fidelity 9 next-step economy / logical shell addendum

- AnchorApplication count stays at **nine**. No new canonical type, responsibility, runtime state owner, effect authority or Anchor is created.
- Detailed existing GateCondition clauses stay at **19**: seventeen verb clauses and two cross-cutting clauses. `GATE-ECONOMY.json` groups them under nine candidate independent Gate responsibilities, with exact clause ID traceability and many-to-many action participation. No new Gate is created.
- The **project optimization rule** jointly minimizes necessary Anchors and Gates while retaining measurable state, transition, host effects, failure and output truths. It does not override the immutable source-pinned `N-RULE-ECONOMY` singularity.
- `logical_engine.py` provides source-independent, deterministic interpretation of the command contract for testing/visualization. It is a test aid, NOT a new Anchor, KPP admission, LLM invocation, or native `.anchor` execution profile.
- `logical_shell.py` projects the interpreter state in a lightweight browser surface; all file/clipboard actions remain explicitly virtual except user-chosen browser file reads/download requests.
- A receiving LLM should be tested blindly against packets from `reasoning_prompt()`, without access to Python implementations or expected answers. Independent model accuracy is still **unverified**.


## Current blind frontier-model trial addition (no new Anchor/Gate)

The new `blind_trial.py` plus `test_blind_trial.py` are **evaluation utilities**,
not Anchor applications, GateConditions, new runtime rules, or authoritative
host permissions. They prepare model-only packets from the reviewed proposed
logical contract and test them against a private reference answer key. Do not
mistake a `control` submission for a separate model run, and never expose
`blind_private/private-key.json` or application source to the interpreting model.
Never count benchmark tooling as new fidelity. An actual independent frontier-model
interpretation result remains open until executed and scored with provenance.

## NEW — v2 blind contract improvements from external-agent feedback

The externally reported 41 predictions (31 success / 10 rejected) have **not** been independently scored: the actual `responses.jsonl` content was not available with the supplied transcript. The aggregates match our reference key, but they are not accuracy evidence.

`blind_public/challenge.json` is now `notepad.blind-logic-challenge/2`, with:

- A **complete** nine-family/19-condition `gate_registry`, including build-time and UI clauses absent from the directly exercised runtime subset.
- An explicit `result_contract` naming allowed JSON result variants and allowed kinds per command; `DocumentSnapshot` is descriptive prose, not an output literal.
- An explicit trusted virtual file-session comparison observation for every trial, so Save conflict status never depends on a hidden hash calculation. No host success is assumed from this observation.
- Strict result-kind, result-field, count, and selection validation in the private evaluator.

All 41 stimuli, preexisting trial fields, and sealed expected answers remain identical to v1. We changed the public challenge fingerprint, not the behavioral target. See `AGENT-FEEDBACK-RECONCILIATION.md` and `CHALLENGE-COMPATIBILITY-LEDGER.json`. The public model-only ZIP must be distributed separately from this complete package.
