# SCAN v0.20 Blind Reconstruction Trial Contract

M6A turns a reconstruction-aware certification into a reproducible, source-blind engineering experiment. It does **not** execute the reconstructed application and it does not claim that static equivalence is universal behavioral equivalence.

## Two-package blindness boundary

A verified reconstruction certification is split into two independently sealed packages:

1. **Public challenge** — may be given to the reconstruction agent.
2. **Private evaluator** — must not be given to the reconstruction agent.

The public challenge contains:

- a sanitized reconstruction contract;
- source-free mechanically scored reconstruction signatures: human-visible surface text/type, required binding/effect closure, and MAPPED effect/capability terminals;
- reconstruction anchors and behavior contracts;
- the completeness-state vector without source locators or evidence excerpts;
- an agent brief;
- a source-isolation submission template;
- a deterministic challenge manifest.

It deliberately excludes:

- original specimen source bytes;
- `scan_index.sqlite`;
- `evidence_catalog.json` and `evidence_graph.json`;
- machine body maps containing source paths;
- source evidence excerpts;
- original local source paths;
- the private evaluator.

The private evaluator contains the exact mechanically derived reconstruction expectations, scoring internals, and lineage hashes. The public challenge receives only the source-free subset needed to make the test fair. Neither package contains original source bytes.

Create the split with:

```text
scan-body prepare-reconstruction-trial <reconstruction-cert-dir> \
  --challenge-out <public-dir> \
  --evaluator-out <private-dir> \
  [--challenge-bundle <public.zip>] \
  [--evaluator-bundle <private.zip>]
```

## Agent submission boundary

The reconstruction agent receives only the public challenge and writes its implementation into a separate candidate directory. The agent also completes the supplied `SUBMISSION_TEMPLATE.json` outside the candidate directory.

The submission records:

- challenge identity;
- agent name/version/provider;
- whether original source was accessed;
- whether the parent certification was accessed;
- whether the private evaluator was accessed;
- whether network/repository source lookup was used;
- the isolation enforcement level.

SCAN mechanically rejects a submission that admits any forbidden source access or refers to a different challenge.

The attestation cannot by itself prove that an external agent was sandboxed. `enforcement_level` therefore remains explicit. A future controlled harness may raise this from declaration to mechanically enforced filesystem/network isolation.

## Static reconstruction scoring

Score a candidate with:

```text
scan-body score-reconstruction-trial <package-root> <private-evaluator-dir> <candidate-dir> submission.json \
  --out <trial-dir> [--bundle <trial.zip>]
```

SCAN does not compare source code. It rescans the reconstructed candidate and compares mechanically recoverable reconstruction signatures:

- human-facing surface type and visible text where available;
- binding closure strength;
- effect-closure strength;
- MAPPED effect/capability/boundary terminal signatures.

The authoritative result is the per-anchor state and attribution. `fidelity_score` is only a convenience aggregate.

Mismatch attribution categories are:

- `RECONSTRUCTION_AGENT` — strong source evidence, adequate candidate scan, required signature missing;
- `SEMANTIC_IR` — a promoted reconstruction anchor lacks a mechanically scorable reconstruction signature;
- `SCANNER_CANDIDATE_COVERAGE` — the candidate scan is too incomplete to adjudicate the mismatch safely;
- `UNRESOLVED_SOURCE_UNCERTAINTY` — the original source evidence itself is partial, contradicted, or otherwise insufficient for a strong failure claim;
- `PASS` — mechanically scorable requirement recovered.

A weak original fact never becomes a strong reconstruction failure merely because an evaluator wants a binary score.

## Sealed trial artifact

The trial output preserves:

- a copy of the reconstructed candidate that was actually scored;
- the agent submission declaration;
- the candidate SCAN outputs;
- `scorecard.json`;
- `trial_receipt.json`;
- `TRIAL_MANIFEST.json` sealing the complete trial.

Verify later with:

```text
scan-body verify-reconstruction-trial <trial-dir>
```

Tampering with the candidate, scorecard, receipt, or scan output invalidates the trial manifest or candidate projection hashes.

## What M6A proves and does not prove

M6A proves that SCAN can conduct a reproducible **static, source-blind reconstruction trial** and separate four important failure domains: scanner coverage, semantic/reconstruction IR, reconstruction-agent implementation, and unresolved original evidence.

It does not yet complete PR7. Full M6/PR7 still requires a capable external coding agent that has never seen the source, plus behavior-level evaluation of the resulting surrogate. Runtime execution/stimulation remains a separately authorized mode under A1 and should be added as an isolated M6B evaluator rather than smuggled into ordinary static scanning.
