# Sleep-time memory consolidation — KPP Pantry ingredient

**Status:** Experimental, narrow Python reference. **Not** a new organ, runtime service, scheduler, MIND, model trainer or birth certification.

## Why this exists

An AppAI's MIND can be in STASIS while its deterministic BODY remains operational. The Heart continues its fixed 600-second natural heartbeat; existing BODY work can sort, verify and index experiences between cognition encounters. This ingredient creates **rebuildable, derived retrieval views** at different update cadences, never rewriting the original Engram or claiming that an LLM has learned new facts.

Inspired by Google Research's [Nested Learning (2025)](https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning/) and [Sleep Framework (2026)](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/). Google's sleep work involves model-parameter learning, expert expansion and reinforcement learning. This ingredient **does not implement or reproduce those algorithms**; it applies only the broad multi-timescale scheduling metaphor to host-owned, nonparametric memory views.

## Host integration

1. Reuse the NEST's verified memory store, indexer, clock and read tools before adding code. No new organ is required if an existing Memory capability can perform the duty.
2. The Heart supplies a positive `beat_number` (not a new timer). The reference uses fast=every beat, medium=every sixth beat, slow=every 144th beat; these are **view cadences**, not Heart rhythm changes. With a 600-second pulse, these correspond to ten minutes, one hour and one day of continuous activation. These rates are adjustable via the function call; no wall-clock accuracy is assumed during host suspension.
3. The BODY reads an explicitly permitted, complete, verified bounded Engram prefix. Feed it to `project(records, beat_number=N, previous_head=PRIOR, expected_head=CURRENT)`. Obtain the optional expected head independently from the host when freshness matters.
4. The projection contains record hashes, sequence positions, and counts for a fixed set of public record types. Custom type names are counted as `other`. Every due tier refreshes even when the source head matches the previous head. The delta and the tier schedule are independent.
5. If the NEST needs durable projections, use an **existing checked host writer** to persist the derived view separately from canonical history, with source-head checks and recovery. The reference **does not publish** anything. Do not interpret a digest, model suggestion or Pantry label as authority.
6. In the next cycle supply the prior projection's `source_head`. The prior head must be an ancestor of the input, and the input must match the expected head when supplied. Replaying the same records, beat and options yields identical output.

## Body-only example

```python
from mantleos import engram
from mantleos.kpp.sleep_memory import project

# Host must authorize the source path; Engram read verifies the hash chain.
records = engram.read("NEST/ENGRAM.jsonl")
projection = project(records, beat_number=6)
assert projection["mind_calls"] == 0
# Host decides whether an approved derived view should be published.
```

## Boundaries and limitations

* MIND stasis does not imply BODY inactivity. No model, network, credentials or heartbeat scheduler are required by this ingredient.
* Memory content remains in the canonical append-only Engram. Derived indexes are not facts, new experience, or evidence of model learning.
* The reference accepts at most 512 complete records of at most 64 KiB each; larger NESTs need separately qualified incremental source adapters and paging. It checks record sequence and content hashes but does not authenticate an upstream recorder.
* The caller is responsible for NEST access scope, multiwriter coordination, trusted source reading, filesystem safety, any privacy controls, publication, and KPP/Baker acceptance.
* No semantic consolidation or model-weight modification is performed. Dreaming/self-improvement would require a separately selected and qualified ingredient; no automatic MIND effect authority is implied.
* Fail closed on stale history, malformed records or budget violations. Preserve source bytes and previous verified projections on any error.
* No need to reproduce a capability already verified in the NEST. This ingredient may serve as a contract/reference or be omitted when the existing host mechanism meets the same requirements.

## Proposed KPP acceptance scenarios

- No MIND transport installed: multiple due tier projections still execute and agree with source hashes.
- Tampered, out-of-order, stale, foreign or oversized Engram input is refused without changing source or prior derived views.
- Fast/medium/slow activity is triggered from the Heart's beat number; no second scheduler is created and the natural 600-second cadence is unchanged.
- Multiple identical retries yield byte-identical projections, and no failed attempt is reported as a completed effect.
- The original application still performs its declared functions when the MIND is disconnected; this ingredient by itself does not certify AppAI birth.

Run focused test: `PYTHONPATH=src python -m unittest tests.test_sleep_memory -v` (or `python -m unittest discover -s tests -p test_sleep_memory.py -v`).
