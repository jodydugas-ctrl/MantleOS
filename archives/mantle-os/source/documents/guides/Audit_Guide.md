# Mantle OS — Audit Guide

Everything is provable, so prove it. Three harnesses, all pure stdlib, all offline:

```bash
python -m mantle audit         # Stage 1: the Zombie Body gate (deterministic, LLM-free)
python -m mantle prove         # the security invariant suite (red/green)
python -m mantle audit-mind    # Stage 2: MIND containment + FULL Stage-1 regression
```

Exit code 0 = gate passed. ANY failing row or red invariant blocks (exit 1). The gates
fold the invariants in; `--fast` skips them for a quick row-only run; `--json` appends a
machine-readable evidence record.

The closed-world `python -m mantle check --strict` orchestrator executes the complete invariant
suite once. Stage 1 and Stage 2 still produce separate row verdicts, while a current-run nonce
and tracked-source digest bind the complete, ordered invariant receipt between them. Missing,
red, reordered, replayed, or stale evidence blocks certification. Standalone `audit` and
`audit-mind` remain complete by default; the internal `--rows-only` mode explicitly reports that
it is not a standalone certification.

## Stage 1 — the Zombie Body gate (`src/mantle/audits/stage1.py`)

Substrate rows: cube verify healthy (B-01) · Primer present (B-02/HF-B02) · canonical
band map (B-03) · identity in the Body, never the cube (B-45/HF-B45) · entry hashes
intact (B-13) · the veil (B-14) · dangling ref → immune (B-12/HF-B24) · sealed ancestors
refuse writes (B-46) AND their fingerprints verify (B-46b) · metabolism present + every
band purposed (B-W).

Mesh rows (the RUNNING nine-organ Body): heartbeat with no LLM — proven by beating with
the cognition slot empty (B-04/HF-B08) · dual-flush (B-05/HF-B33) · the fixed pulse order
(B-06) · the deterministic Senses classifier, one entry per signal, REFLEX never touches
the brain band (B-16/HF-B09) · Human Surface Map coverage (B-25) + ControlBridge proofs
(B-26/HF-B44) · dispatch authorship immutable (B-29/HF-B29) · all nine organs present
with enforced contracts, Brain dormant (B-60) · the SignalBus fail-open (B-61/HF-B32) ·
organ overreach refused (B-62) · capacity pressure measurable and wired (B-63).

A pass sets `organism.stage1_certified = True` as technical evidence. Fusion still requires
separate target-bound `APPROVED` decisions from both operator and guardian.

## Tamper proofs (the harness must CATCH violations)

```bash
python -m mantle audit --break-hash      # a tampered entry        -> MUST exit 1
python -m mantle audit --break-primer    # the Primer in the cube  -> MUST exit 1
python -m mantle audit --break-seal      # a rewritten ancestor    -> MUST exit 1
```
CI runs all three and fails if any of them PASSES. A gate that cannot catch a violation
is not a gate.

## Stage 2 — the MIND gate (`src/mantle/audits/stage2.py`)

Runs offline with the deterministic stub transport (no key, no network); because the
model is a pluggable callable, the same audit certifies any provider. Rows: the bounded
write surface (M-1/HF-M10) · propose/apply split (M-2) · no self-promotion (M-3/HF-M12) ·
Genome untouched (M-4) · assembly resolved + veiled (M-5/HF-M14) · reflections carry
inferred provenance (M-6/HF-M16) · audit-before-fusion held (M-7/HF-M15). Then the ENTIRE
Stage-1 row set re-runs against the fused organism: Stage 2 may never break Stage 1.

## The invariants (`src/mantle/audits/invariants.py`)

Red/green guards (`mantle prove` prints the live count), each proving a hard-fail fires
(and, where relevant, that the
permitted path still works). Highlights beyond the v2 set: **no-Phase-1-LLM-path** proven
in a clean subprocess that lives a full Phase-1 life and then inspects `sys.modules`,
plus an AST import scan of every Phase-1 source · **capacity → metabolism, never
rebirth** · **seal-tamper detection** · **lazy-load equivalence** · **calcify requires
hash/signature/capability/provenance** · **fusion requires Stage-1 + dual authority** · **self-inquiry
never becomes a fact** (and evidence-free promotion is refused while cited promotion
works) · **organ overreach refused** · **staged save rejects a corrupt cube**.

## The one rule

**Never weaken an invariant to make a test pass.** If a test fails, either the code
broke a guarantee (fix the code) or the test asserts the wrong guarantee (fix the test —
and say so in the commit message). Both happen; record which in the commit.
