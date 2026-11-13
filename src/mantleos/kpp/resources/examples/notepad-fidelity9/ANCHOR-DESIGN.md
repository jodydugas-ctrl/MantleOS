# Notepad — Fidelity 9 global Anchor recalculation

**Exactly one new Anchor:** `WH-BLUEPRINT-GATE` (**WhiteHole**, build-time). Total **9**. The previous eight runtime Anchor implementations remain **byte-identical** to the Fidelity 8 artifact because a runtime rebuild would introduce risk without removing an architectural conflict. The optimization is **separation of enforcement concerns**: the prior runtime guard keeps runtime command/effect authorization; the new WhiteHole checks the entire build blueprint and preservation records before a coding agent can present a candidate as locally ready.

This is a draft AnchorForge `anchorforge.organ-spec/1` and human-readable design. There is **no claim** of formal AnchorForge review, a formally satisfied `kpp.recipe/4`, or an executable native `.anchor` profile.

## Nine-Anchor recalculation

| # | Anchor | Type | Global review disposition |
|--:|---|---|---|
| 1 | `BH-EDITOR-INPUT` | BlackHole | Preserved input-as-data truth; source unchanged; build gate requires exact ID/class. |
| 2 | `N-DOCUMENT` | Neutral | Preserved sole text, revision and baseline owner; build gate pins declared state ownership and rejects protected duplicate writes. |
| 3 | `WH-COMMAND-GUARD` | WhiteHole | Preserved runtime command authorization; build gate now audits literal action allowlist, effect guard and display dispatch path. |
| 4 | `N-EDIT-HISTORY` | Neutral | Preserved undo/redo and document-revision ownership; build gate checks required fields/owner declarations. |
| 5 | `N-EDITOR-SURFACE` | Neutral | Preserved GUI projection and BH → WH route; build gate checks the source dispatch references. |
| 6 | `N-FILE-SESSION` | Neutral | Preserved guarded UTF-8 read/write/path ownership; build gate checks effect executor and selected raw file calls. |
| 7 | `N-CLIPBOARD-SELECTION` | Neutral | Preserved clipboard capability, Unicode selection and host effects; build gate checks declared executor and source boundaries. |
| 8 | `N-SEARCH-REPLACE` | Neutral | Preserved pure literal match semantics; build gate rejects source-level raw file/clipboard calls in this Anchor. |
| 9 | **`WH-BLUEPRINT-GATE`** | **WhiteHole** | **New.** Audit nine-Anchor candidate mapping and build obligations before readiness; no editor state or user-intent execution. |

## Two complementary WhiteHole boundaries

```text
RUNTIME (unchanged):
Tk UI / controller (N-EDITOR-SURFACE)
    -> BH-EDITOR-INPUT (capture intent verbatim)
    -> WH-COMMAND-GUARD (payload validation, action/capability authorization)
       -> N-DOCUMENT / N-EDIT-HISTORY / N-FILE-SESSION /
          N-CLIPBOARD-SELECTION / N-SEARCH-REPLACE
    -> authoritative snapshot projected by UI

BUILD TIME (new, outside user command path):
anchorforge-spec.json (draft) + blueprint-manifest.json
    + nine mapped Anchor source modules + all regression tests
       -> WH-BLUEPRINT-GATE (fail-closed consistency checks)
       -> full cumulative Python test execution with --verify
       -> evidence for a reviewed candidate; NEVER automatic Baker acceptance
```

## Optimized global architecture decisions

- **Distinct gates, no duplication of runtime semantics:** `WH-COMMAND-GUARD` remains the only runtime gate for user commands. `WH-BLUEPRINT-GATE` does not parse editor requests or hold document state. Building policy is not added to every editing operation.
- **No gratuitous rebuild:** Eight previous modules already have one authoritative document/history/file owner, bound clipboard/search operations and a guarded GUI. Rewriting them would not simplify the observed state graph. Existing design is therefore preserved; the optimization adds missing *build* verification without runtime coupling.
- **One canonical draft, one machine mapping:** `anchorforge-spec.json` owns responsibilities, flows, state, effects, obligations. `blueprint-manifest.json` maps this content to source classes and preservation IDs; it is not a second source of behavioral truth.
- **Additive evidence:** 181 inherited test identities and all 23 previous mandatory obligation IDs are preserved. Four new testable draft obligations cover role/state conformance, host effects/actions, obligation/test preservation and scoped acceptance.
- **Cumulative gate constraints:** unique Anchor roles/classes; no loss of count; exact source mapping; unique Neutral state owners; mapped protected field writers; effect requester/guard/executor/confirmation; runtime action allowlist; flow endpoints; mandatory obligation coverage and acyclic prerequisites; inherited test-method identity; and limited static host-call checks.

## State and effect ownership

13 previous declared state items remain owned by their prior Neutral Anchors. The new build-time WhiteHole owns **no runtime state**; its report is a transient value returned to a CLI caller. Four previously declared file/clipboard host effects retain `WH-COMMAND-GUARD`, their original requesters/executors and explicit confirmations. Running the offline test CLI executes Python processes in the development host, but is **not an editor runtime effect** and grants no app capability.

## Evidence, Chase and limits

Under a headless Linux Xvfb display, **213/213 tests passed**: all **181** prior tests unchanged plus **32** new tests for valid conformance, intentionally broken copied candidates, fail-closed CLI, and non-mutation of the audited sources. The new offline gate itself reports no violations for the shipped candidate.

**Chase:** original basic Notepad scope remains locally met. Fidelity 9 adds developer-blueprint preservation/hardening, locally met as scoped. Structural static checks cannot prove arbitrary runtime semantics or the integrity of a hostile coding agent that can edit the checker itself. Native AnchorForge review, KPP satisfaction and Baker acceptance remain **pending**.

## Fidelity 9 end-state Chase overlay (no new AnchorApplication)

The Baker clarified that minimizing AnchorApplication count while completely specifying the output is more important than continuing automatic `+1` rounds after the Chase target is covered. The original nine identities are preserved. See `CHASE-END-STATE-REVIEW.md` for the explicit stop assessment.

`LOGICAL-CONTRACT.json` adds **19 proposed GateCondition records** (one per runtime command plus one UI-projection Gate and one build-conformance Gate) referencing the existing nine applications; it does not redefine the canonical three Anchor types. `LOGICAL-INTERPRETATION.md` explains bounded stimulus-response prediction by a receiving LLM, and `LOGICAL-TRACE-CORPUS.json` provides 32 expected-behavior cases. This sidecar does not modify or certify `anchorforge.organ-spec/1`, and it does not create native `.anchor` execution semantics. Both the nine-Anchor count and the 27 draft obligations remain unchanged.

**End-state assessment:** original Notepad feature Chase locally covered; full KPP satisfaction and explicit Baker acceptance pending. Stop adding Anchors absent a distinct unmet responsibility.


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
