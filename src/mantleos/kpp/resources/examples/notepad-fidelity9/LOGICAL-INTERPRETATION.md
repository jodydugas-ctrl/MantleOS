# Notepad — LLM logical interpretation contract (Fidelity 9)

**Purpose:** A receiving LLM should be able to explain or predict the response of the nine-Anchor Notepad to a stated stimulus **from the contracts**, without reading or executing Python application code. The Python implementation remains a comparison target, **not** the source of truth for the logical answer.

**Status:** Proposed local contract, not a released `anchor.design`, `kpp.recipe`, GateCondition schema or executable `.anchor` profile. `LOGICAL-CONTRACT.json` is the detailed machine-readable companion. The 32 cases in `LOGICAL-TRACE-CORPUS.json` are expected observations and can be used as a held-out reasoning prompt; they are not actual proof of another LLM's ability.

## Canonical layers — do not conflate them

- `AnchorDefinition`: BlackHole receives declared input; Neutral applies declared relationships; WhiteHole enforces declared boundaries.
- `AnchorApplication`: the **nine** named project responsibilities. They own/receive/guard, but are **not** KPP recipe obligations.
- `GateCondition`: the **19** separately identified conditions (17 runtime command gates and two additional GUI/build gates) in `LOGICAL-CONTRACT.json`. Each names the involved AnchorApplications; these do not create additional Anchors or grant host authority.
- `RecipeObligation`: the **27** cumulative draft obligations in `anchorforge-spec.json`. They describe measurably required results. They are not equivalent to the nine applications or 19 contract Gates.
- `LogicalTransition`: a proposed contract interpretation of a command under a known state, boundary predicates, and confirmed host observations.
- `ExecutableAnchorProgram`: an `.anchor` in a qualified execution profile. `Notepad.anchor.txt` in this package is **not** such a program.

## Interpretation procedure — use without code execution

1. **Read state.** Record authoritative text `T`, clean baseline `B`, revision `R`, bounded undo stack `U`, redo stack `D`, expected history revision `H`, active file path `P`, expected on-disk digest `K`, transient UI selection, and any explicit host observations. If a required value is unavailable, return `UNDETERMINED` for the affected question.
2. **Receive input (BlackHole).** Capture `(action,payload)` exactly. Capturing is not authorization. Never transform missing values into defaults.
3. **Find exactly one command Gate.** Match the action in `LOGICAL-CONTRACT.json`. Unknown commands are rejected by `WH-COMMAND-GUARD`. A Gate links several Anchors but does not create a new type.
4. **Evaluate preconditions in order.** Validate the *exact* payload shape, types (notably Boolean is not integer), Unicode-codepoint offsets, required bindings, history freshness and any action-specific guard. If a precondition is false, return a rejection with no authorized document/history change. If a needed observation is missing, say `UNDETERMINED` rather than inventing permission or a host result.
5. **Resolve external effects only if explicitly observed.** Filesystem and clipboard operations cannot be performed mentally. For `open`, the input must include successful file read bytes or a failure. For saves, include a confirmed write/replace and conflict check. For clipboard read/write, include a callback result. Do not claim those effects occurred based on a generated prediction.
6. **Apply one authorized transition via the listed Neutral owners.** Compute changed text; increment `R` **only when text changes**. Dirty is always `T != B`. A changed undoable edit pushes `(before,after)` on the bounded undo stack and clears redo; unchanged text leaves history untouched. `new`/`open` reset history after successful baseline change. `save`/`save-as` change the clean baseline only after confirmed writes; do not erase history. Undo/redo preserve baseline.
7. **Return observable result.** For `read`/edits/files/undo, return snapshot; `find` returns match range or null; `select-all` returns Unicode-codepoint range; replace operations return snapshot plus replacement count. Do not derive UI appearance when the view contract does not specify it; describe snapshot/dirty indicator only where grounded.
8. **Report provenance and uncertainty.** Label output `PREDICTED_FROM_ANCHORS`, `REJECTED_BY_GATE`, or `UNDETERMINED`. A prediction is not an executed test, a host authorization, native `.anchor` execution or Baker acceptance.

## Example stimulus/response without program execution

```text
Known initial state:
 T="Hello"; B="Hello"; R=0; U=[]; D=[]; H=0
 input=("insert", {"offset":5,"text":" World"})

BH-EDITOR-INPUT receives (unchanged).
G-CMD-02 links BH-EDITOR-INPUT, WH-COMMAND-GUARD, N-DOCUMENT and N-EDIT-HISTORY.
WH-COMMAND-GUARD checks exact object shape, offset 0..5, current history binding.
N-DOCUMENT computes "Hello"[:5]+" World"+"Hello"[5:]=="Hello World".
Value differs => R=1. N-EDIT-HISTORY pushes ("Hello","Hello World") and sets H=1.
B remains "Hello", so dirty=True.

PREDICTED_FROM_ANCHORS:
 text="Hello World"; revision=1; dirty=True; undo_count=1; redo_count=0
No external effect. No Python application code was needed for this prediction.
```

## Interpretation edge cases that matter

| Scenario | Required prediction |
|---|---|
| Insert text identical to current document's resulting text | No new revision and no history entry |
| Undo after an edit | Restore former text, increment revision, preserve baseline, move undo entry to redo |
| New/Open when dirty and `discard=false` | Reject, preserve text, history, file association |
| Open with unreadable/non-UTF-8 file | Reject; no clean baseline installation |
| Save with no associated file | Reject; require Save As |
| Save on externally changed file | Reject, do not silently overwrite |
| Cut and clipboard write fails | Reject before editing document |
| Copy and clipboard write succeeds but callback changes state | Document edit rejected; clipboard effect may already have occurred |
| Replace All with two matches | At most **one** new document revision and one undo record |
| Find missing query | Return null match, no document/history mutation |
| Case-insensitive Unicode matching uncertain | Mark outcome `UNDETERMINED` if exact Python regex semantics are unavailable |

## Scope and stopping condition

The original Chase target is a single-document plain-text editor with New/Open/Save/Save As, editing, undo/redo, clipboard, selection, Find/Replace, shortcuts and unsaved-change protection. Its 17 internal commands are represented in the logical contract; GUI shortcut mapping is preserved by the existing Tk code and regression tests, not yet modeled as a complete portable event grammar. Therefore **this is not an unqualified universal logical executable**. It supports bounded predictions when inputs, state and host observations are fully declared.

The Chase can stop adding AnchorApplications when no distinct responsibility is missing. **Do not create Anchor #10 just to satisfy a round number.** If the Baker requests an additional feature with genuinely separate responsibility, re-evaluate the full design and add an Anchor only when justified. If scope is fully covered, proceed to review, KPP satisfaction when available, and explicit Baker acceptance.


## Fidelity 9 next-step economy / logical shell addendum

- AnchorApplication count stays at **nine**. No new canonical type, responsibility, runtime state owner, effect authority or Anchor is created.
- Detailed existing GateCondition clauses stay at **19**: seventeen verb clauses and two cross-cutting clauses. `GATE-ECONOMY.json` groups them under nine candidate independent Gate responsibilities, with exact clause ID traceability and many-to-many action participation. No new Gate is created.
- The **project optimization rule** jointly minimizes necessary Anchors and Gates while retaining measurable state, transition, host effects, failure and output truths. It does not override the immutable source-pinned `N-RULE-ECONOMY` singularity.
- `logical_engine.py` provides source-independent, deterministic interpretation of the command contract for testing/visualization. It is a test aid, NOT a new Anchor, KPP admission, LLM invocation, or native `.anchor` execution profile.
- `logical_shell.py` projects the interpreter state in a lightweight browser surface; all file/clipboard actions remain explicitly virtual except user-chosen browser file reads/download requests.
- A receiving LLM should be tested blindly against packets from `reasoning_prompt()`, without access to Python implementations or expected answers. Independent model accuracy is still **unverified**.

## NEW — v2 blind contract improvements from external-agent feedback

The externally reported 41 predictions (31 success / 10 rejected) have **not** been independently scored: the actual `responses.jsonl` content was not available with the supplied transcript. The aggregates match our reference key, but they are not accuracy evidence.

`blind_public/challenge.json` is now `notepad.blind-logic-challenge/2`, with:

- A **complete** nine-family/19-condition `gate_registry`, including build-time and UI clauses absent from the directly exercised runtime subset.
- An explicit `result_contract` naming allowed JSON result variants and allowed kinds per command; `DocumentSnapshot` is descriptive prose, not an output literal.
- An explicit trusted virtual file-session comparison observation for every trial, so Save conflict status never depends on a hidden hash calculation. No host success is assumed from this observation.
- Strict result-kind, result-field, count, and selection validation in the private evaluator.

All 41 stimuli, preexisting trial fields, and sealed expected answers remain identical to v1. We changed the public challenge fingerprint, not the behavioral target. See `AGENT-FEEDBACK-RECONCILIATION.md` and `CHALLENGE-COMPATIBILITY-LEDGER.json`. The public model-only ZIP must be distributed separately from this complete package.
