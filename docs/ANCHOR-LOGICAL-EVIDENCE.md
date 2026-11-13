# Anchor logical interpretation evidence (optional, experimental)

This component is shared infrastructure for KPP and MantleOS. It **does not redefine** the canonical BlackHole, Neutral and WhiteHole meanings. It does not add an Anchor type, a Gate, a runtime, model SDK, compiler backend or permission. A recipe's historical `anchors` array remains **acceptance obligations**, not automatically `anchor.application/1` objects. `anchor.design/1` remains a separate design contract.

## Purpose

Evaluate whether a model or other interpreter **predicts** state transitions consistently with a reviewed, sealed reference key given a *model-facing* Anchor/Gate stimulus contract. Prediction agreement, actual software execution, and Baker acceptance are different layers of evidence. A control generated from the key checks the scorer, **not model competence**.

- Operator authors and versions the public challenge with an explicit response envelope, state fields, allowed results, preconditions and Gate clauses.
- Operator independently produces and retains a sealed expected-answer key with `challenge_sha256 = SHA256(canonical challenge JSON)` and a `trial_count`. Each `answers` entry contains `trial_id` and `expected` response sans `trial_id`, or the legacy flattened form.
- A model sees **only** the challenge. Each `trial` has a stable `id`, `stimulus`, and any needed modeled-host observations. Expected values, scenario labels, private hashes/keys, or reference code remain off the model side.
- Model returns bounded JSONL records with the exact declared response fields. Canonical JSON uses sorted keys, compact separators and UTF-8.
- `python -m mantleos.anchor_logic_evidence --challenge PUBLIC.json --key PRIVATE.json --responses MODEL.jsonl --out NEW-REPORT.json` validates formats, checks the challenge/key binding and compares state/result/outcome/Gate families per trial.

`reason` is validated only as **empty for success or non-empty for rejection/undetermined**. English correctness isn't scored; the report explicitly excludes that text from the field accuracy count. Generic state projection fields are compared exactly; this module does not know application-specific dirty/revision/undo laws. Domain checkers (and actual runtime tests) must test those. The report never claims a model was independently run without separately supplied provenance.

## Compatibility and architecture economy

The optional library can score an existing `notepad.blind-logic-challenge/2` packet and its paired sealed key **without changing** any Notepad Anchor, Gate, or KPP recipe. Caller must supply the source-appropriate key. There is no automatic migration of existing recipes/workspaces. If the contract changes, version it and regenerate a sealed key. Keep the public package and key in disjoint access locations.

Minimum baseline: structural validation of the packet and response; reference-control scoring; negative mutation scoring; independent model trials (if available); separately scoped implementation/conformance tests. This is an upstreamed *evidence utility*, not a proof of universal logical executability.

## Anchor vocabulary for consuming agents

- **AnchorDefinition:** immutable shared type/singularity from `mantleos.anchors`.
- **AnchorApplication:** a contextual application of a shared definition, identified explicitly.
- **GateCondition:** an independently testable requirement, possibly spanning several AnchorApplications; Gates are not a fourth Anchor type.
- **RecipeObligation:** mandatory/optional acceptance requirement (`recipe.anchors` is its legacy wire name).
- **LogicalTrial:** initial modeled state + stimulus + trusted modeled-host observations, interpreted against the applicable Anchors and Gates.
- **Effect evidence:** an observed/verified host receipt, never merely a predicted transition.

Prefer revising existing Anchors and Gates to achieve coverage before adding more. Minimality must preserve explicit failures, authority, state ownership and independently testable outcomes. Frontier models are the intended setting; the contracts remain provider-independent.
