# Anchor transition-trace/1 — proposed cross-project evidence format

**Status: REVIEW PROPOSAL.** This is neither a new canonical KPP syntax nor a native executable Anchor profile. No Baker acceptance or host authority is implied.

## Why
Notepad Fidelity 9 demonstrated a process for recalculating Anchors, preserving prior truths, and separating predicted behavior from verified execution. This format makes the *sequence* inspectable without inheriting any one app's Python implementation.

## Envelope (exact top-level keys)
- schema: anchor.transition-trace/1
- authority: NONE
- baker_acceptance: NOT_GRANTED
- contract_ref: nonempty string referencing the applicable proposed application contract
- initial_state: JSON object
- steps: 1–256 ordered steps
- final_state: JSON object

Each step contains exactly id, stimulus, before, gate, transition, after, effects, output, evidence.
- stimulus: {action: identifier, payload: object}.
- gate: {family: identifier, decision: admit|reject|undetermined, clauses: nonempty unique ID array}. The decision is a *recorded claim*, never automatic permission.
- transition: changed|unchanged|undetermined; after: object, or null only for terminal undetermined.
- effects: list of {id, status, evidence_ref}. Status is predicted|observed-success|observed-failure|unknown. An observed status requires a nonempty evidence_ref, but the validator cannot authenticate that reference.
- output: arbitrary JSON object or null; a pinned command-specific result contract must specify its meaning.
- evidence: {kind: reference|model|host|reviewer|none, ref: string|null}. These labels are not verified provenance.

## Validation invariants
- Maximum 2 MB UTF-8 input; no duplicate JSON members or non-finite JSON constants.
- A step's before snapshot equals the previous known state using type-sensitive canonical JSON equality (a boolean is not an integer).
- changed and unchanged labels match the declared snapshot comparison; reject cannot commit a state change.
- An undetermined step must be terminal, use after=null, and leave final_state at the last known snapshot.
- Observed effect references must be present but must be independently corroborated by an operator.
- No host effects are performed, no application grammar is inferred, no model score is awarded, and no Baker acceptance is granted.

## Usage
From a KPP checkout:
- PYTHONPATH=src python -m mantleos.anchor_transition examples/notepad-transition-trace.json
- PYTHONPATH=src python -m unittest discover -s tests -p 'test_anchor_transition.py' -v
- AnchorForge Studio → Transition Lab runs this validator through the existing native Python bridge.

The example is a *synthetic demonstration*, not an externally scored LLM answer or a replacement for LOGICAL-CONTRACT.json.

## What remains before admission
Review a pinned command/result contract grammar, Gate registry linkage, witness trust model, negative and cross-language conformance corpus, evidence freshness, and Baker approval. Separate validation of trace structure from correctness of the behavior claimed by the trace.
