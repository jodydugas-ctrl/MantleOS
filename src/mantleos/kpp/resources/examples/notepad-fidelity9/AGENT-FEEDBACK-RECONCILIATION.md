# Fidelity 9 — External-agent feedback reconciliation and blind-packet repair

**Date:** 2026-11-13. **Status:** Benchmark contract revised; actual external-model answers have **NOT** been independently scored. No additions to the **nine AnchorApplications**, **nineteen detailed GateConditions**, or **nine proposed Gate families**. No changes to the nine existing Anchor Python implementation modules, app semantics, or 41 benchmark expected outcomes.

## Source and evidence boundary

The user supplied a transcript of another agent examining `Notepad-Anchor-Model-Only-Challenge(1).zip`. It reports: 41 trials answered, 31 predicted successes, 10 rejections; structural review passed; it raised two contract issues. The raw `responses.jsonl` bytes were **not accessible** to this working environment, despite its filename appearing in the pasted log. Therefore **no model score, field match, per-trial correctness, token count, or latency can be independently claimed**. A 31/10 class distribution merely matches the reference aggregate counts; incorrect per-trial assignments could still share those totals.

## What was reproduced locally

| Feedback | Independent inspection | Decision / adjustment |
| --- | --- | --- |
| 41 answers: 31 successes and 10 rejects | The private reference key has precisely 31 `PREDICTED_FROM_ANCHORS` and 10 `REJECTED_BY_GATE` outcomes | **Not a measured model score.** Preserve as an unverified external report pending the actual JSONL |
| Successful `result.kind` forms unspecified | Per-action clause used `DocumentSnapshot` and generic response schema said {kind, selection?, count?}, while evaluator expected literal lowercase JSON variants | **Confirmed.** Add `result_contract.result_kinds` for `snapshot`, `selection`, `match`, `none`, `replace`, with exact fields and `allowed_result_kinds_by_action` for 17 supported commands. Strictly parse success result structure |
| Save's expected disk digest absent | Blind public state omitted private reference `expected_digest`; one Save follows an Open and requires a match check | **Confirmed.** Provide `file_session_observation.disk_comparison` as a trusted pre-command virtual-host observation, with five explicit statuses. This is input evidence, not a positive effect result, and requires no SHA-256 arithmetic from an LLM |
| 9 family / 19 clause taxonomy not separately exposed | Public had only eight family IDs and 17 runtime clause IDs represented directly by the scenarios | **Confirmed.** Provide `gate_registry` with all nine families and all nineteen detailed conditions; explicitly distinguish offline `G-BUILD-01` and projection `G-UI-01` from 17 command clauses |
| Other sample outcomes (Unicode edits, undo, no-op replacement, clipboard-failure cut) | The reference key contains these behavior classes, but the purported agent output was unavailable | Keep as reported illustrations, **not verified external successes** |

## What changed in the model-facing packet

- Public schema: `notepad.blind-logic-challenge/1` -> `/2`; private key schema `/1` -> `/2` to prevent accidental mixing. The response schema stays `/1`: the six top-level response keys and ten state fields are unchanged.
- New top-level `result_contract` and `gate_registry`, including a complete 17-action output-kind map and an exact Gate inventory. These are **descriptions of the existing system**, not additional Anchors, runtime gates or unreviewed host capabilities.
- New top-level `file_session_observation_contract` and a per-trial `file_session_observation` with `active_path`, `disk_comparison`, and `observation_source`. Statuses: `NO_ASSOCIATION`, `MATCH`, `MISMATCH`, `MISSING`, `UNKNOWN`. The packet never asks the model to calculate or fabricate a hidden digest.
- `blind_trial.load_responses` now rejects unknown success-result kinds, extra/missing result keys, malformed selection ranges, and invalid counts instead of silently accepting structurally ambiguous JSON.
- Existing 41 user actions and their **exact expected states, results, reasons, and Gate families are unchanged**, verified by direct structural/key comparison. No new Gate condition or Anchor was added to address these feedback points.

## Mechanical evidence

- Prior challenge SHA-256 (canonical JSON): `e53d5991080c03584ff00f15f42f9894e0a41b37d392a1da176f37871c3ddd8b`.
- Revised challenge SHA-256 (canonical JSON): `dbef9137e256902ec89f5ccc9924f53fd245dbc8523b0a22373692b40a0a1c06`.
- Original and revised expected answers compared: **41/41 byte-equivalent Python objects** (including classifications, state outputs, trial IDs, and source scenario tags). Original trial payloads and preconditions retained; the per-trial new observation is additive.
- Reference-control scorer: **41/41** exact trial matches, **574/574** field checks. Deliberately modified answer: **40/41**, **573/574** field checks.
- Local full `unittest` suite: **254/254** passed under Xvfb, zero skips. Blueprint verifier: **254/254**, zero skips. (Previous checkpoint: 248/248; six tests added to `test_blind_trial.py`.)
- Nine Anchor implementation module bytes matched the previous package, verified by SHA-256. Local checks are not independent formal certification or Baker acceptance.

## How to finish the actual external-model test

Obtain the **real** `responses.jsonl` file produced in the other session. Keep it read-only and record its SHA-256, exact model name/configuration, instructions, challenge version originally seen, retries, time/tokens and access controls. Then score against the **matching** public/private pair:

```sh
python blind_trial.py score \
  --challenge blind_public/challenge.json \
  --key blind_private/private-key.json \
  --responses /path/to/actual-responses.jsonl \
  --report /new/evaluator-report.json
```

The v1 responses can also be scored against this v2 key **if they retain the same six-key response schema**, because the 41 trial IDs and expected answers were preserved. Report that as a retrospective comparison; it is not equivalent to a model taking the *revised* challenge because the additional observations were unavailable to the original model. For original-protocol evaluation, use the retained v1 challenge and v1 key from the preceding package.

## Important model / host distinction

Logical `PREDICTED_FROM_ANCHORS` only establishes what should occur **given the declared virtual-host observations**. It cannot prove a real filesystem write, clipboard update, display mount, or Baker acceptance. This format targets frontier LLMs, is model-provider-independent, and makes no claim that lower-capability models are a required or verified runtime.

**Architectural decision:** Keep nine Anchors and nineteen detailed Gates. Strengthen existing contract semantics and evidence exposure rather than creating extra Gate identities to repair ambiguity. Formal KPP Satisfaction and explicit Baker approval remain outstanding.
