# Rolling Context and Provider Cache Guide

Mantle's default MIND context policy remains `snapshot`: each cognition round receives the
same deterministic, privacy-veiled snapshot framing that existed before rolling context.
`rolling-prefix` is an explicit Phase-2 opt-in for applications that benefit from a
byte-stable prompt prefix and provider prefix caching.

The rolling ledger is not a second memory system. Experiential VCW bands remain
authoritative. The ledger is a Body-owned transport projection that answers: exactly what
model-visible bytes were prepared, in what order, for which model, lane, task, and context
generation?

## Lifecycle

One request follows a strict order:

1. Nervous assembles a resolved, veiled snapshot.
2. The Body reads the active context generation and committed source cursors.
3. Newly eligible VCW entries become a deterministic, redacted delta.
4. The existing prefix, delta, and active intent are rendered as canonical bytes.
5. The token counter checks the candidate against the rollover budget.
6. The Body records `CONTEXT.REQUEST`, then the transport sends the exact bytes.
7. On success, the Body appends the delta, intent, response, usage receipt, and a final
   `CONTEXT.COMMIT`.
8. Only that final commit advances source cursors.

A timeout records `CONTEXT.FAILURE`; it does not commit the delta or advance a cursor.
Retrying against unchanged source state recreates the same model-visible bytes.

## Install the optional band

Rolling mode requires a private `log-json` app band. It is never added silently to an
existing cube:

```python
from mantle.mind import install_context_band

install_context_band(organism, authorized=True)
```

The experimental allocator selects a free app-band range without crossing framework atlas
reservations. The migration is an explicit Body action and is immune-recorded. New
organisms may instead include `context_band_boot(existing_genome)` in their birth genome.
The context band is excluded from ordinary Nervous snapshots and from its own projection.
The MIND write surface remains only `thoughts` and `brain`.

## Enable rolling mode

```python
from mantle.mind import (
    RollingContextConfig,
    RollingPrefixContextStrategy,
    fuse,
)

strategy = RollingPrefixContextStrategy(
    organism,
    RollingContextConfig(
        context_window_tokens=128_000,
        reserved_output_tokens=4_096,
        safety_margin_tokens=2_048,
        rollover_threshold=0.90,
        persistence_mode="durable-exact",
        lane="interactive",
        task="primary",
        provider_cache="auto",
    ),
)

mind = fuse(
    organism,
    model=model,
    authorization=authorization,
    context_strategy=strategy,
)
```

The transport contract is still `model(prompt) -> text`. A transport may additionally
implement `complete(ModelRequest) -> ModelResponse`; `Mind` uses it when present and falls
back to the callable contract otherwise.

## Canonical prefix

Model-visible records use sorted, compact UTF-8 JSON with NaN refused. Each record is
framed with a version, byte length, and full SHA-256:

```text
MANTLE-CONTEXT-ENTRY/1
length:<decimal byte length>
sha256:<full SHA-256>

<canonical JSON bytes>
```

Changing dictionary insertion order cannot change these bytes. Timestamps, retry counts,
cumulative usage, cache status, and mutable last-updated fields stay in non-visible
receipts. After a successful round, the committed delta, intent, and redacted assistant
response join the stable prefix for the next round.

## Context records

The private ledger uses `mantle-context-v1` records:

- `OPEN` freezes the model, provider, renderer, tokenizer, policy, persistence mode, lane,
  task, budget, and starting cursors for one generation.
- `REQUEST` stores hashes, estimates, and cursors before/after. It deliberately does not
  store a copy of the prompt: in `durable-exact` the exact sent bytes are reproduced by
  re-rendering the generation's committed visible chain, so a per-round copy would
  duplicate the whole prefix every round and grow the ledger quadratically.
- `DELTA`, `INTENT`, and `RESPONSE` become model-visible only after a matching `COMMIT`.
  Outside `durable-exact` the exact content stays in process memory and the ledger keeps a
  `DELTA_RECEIPT` / `INTENT_RECEIPT` / `RESPONSE_RECEIPT` instead. A delta receipt still
  records the consumed source-id range so cursor verification stays enforceable without
  storing the projected content.
- `RECEIPT` records observed provider usage and cache facts.
- `FAILURE` records an unsuccessful boundary crossing without cursor movement.
- `ROLLOVER` closes a generation; `CHECKPOINT` opens a bounded deterministic state in the
  next one.

Every record has a full canonical record hash, previous-record link, generation-local
sequence, and full chain hash. Verification catches altered content, removed/reordered
records, duplicate source inclusion, backward cursors, and cursors advanced beyond
committed source entries.

## Persistence and privacy

| Mode | Exact context location | Restart-safe |
| --- | --- | --- |
| `durable-exact` | Private context band | Yes |
| `session-exact` | Protected process memory; VCW stores receipts/hashes | No |
| `receipt-only` | Process memory for continuity; VCW stores receipts/hashes | No |

Restart-safe prefix continuity necessarily retains the exact redacted projected context
and responses. Hashes alone cannot reconstruct prior bytes. Session and receipt-only modes
therefore reject `resume_after_restart=True` and open a new generation after restart.
Host-level encryption remains a deployment responsibility.

Secrets are redacted before canonical rendering. Private thoughts, raw brain traces,
immune internals, unresolved references, tombstoned/quarantined records, provider
credentials, hidden directives, and the context ledger itself are excluded by default.

## Token budget and rollover

The conservative built-in counter estimates:

```text
ceil(UTF-8 byte length / 3.0)
```

Hosts may inject an exact tokenizer with `CallableTokenCounter`. The hard input budget is
the context window minus the output reserve and safety margin. Rollover begins at the
configured fraction of that budget, before the hard limit.

Rollover also occurs when model, provider, renderer, tokenizer, persistence policy, or
context-window assumptions change. The Body closes the old generation and writes a
deterministic checkpoint containing redacted identity/constitution data plus a bounded
recent projection from each eligible source band. If checkpoint plus active intent still
cannot fit, Mantle raises `ContextBudgetExceeded` and emits an immune event; it never
silently truncates the active request.

## Prefix cache versus response cache

Prefix caching reuses computation for an identical beginning of a new request. Response
caching reuses a whole prior answer. They are separate policies:

```python
RollingContextConfig(
    context_window_tokens=128_000,
    provider_cache="auto",  # disabled | auto | required | response-cache
)
```

`auto` uses transport capabilities when available. `required` raises
`ContextCapabilityUnavailable` before preparing anything when the transport does not report
prefix-cache support. A cache miss is an ordinary observed result, not a failure. Cache hits remain provider-controlled and are never promised by Mantle.

Provider receipts are reconciled with the local estimate. `RECEIPT` records prompt and
completion tokens, cached/write tokens when reported, generation ID, exact request hash,
stable-prefix hash, dynamic-suffix hash, and estimation error.

## Lanes and recovery

`ContextKey(body_fingerprint, lane, task)` isolates independent histories such as
`interactive`, `planning`, `coding`, and `maintenance`. Each key has its own generations,
cursors, hashes, receipts, and cache locality.

If the active generation is corrupt, Mantle emits `context_corruption`, refuses to resume
it, preserves its records for inspection, and opens a recovery generation from
authoritative VCW state. The invariant suite deliberately tampers with stored bytes,
cursors, and sequences to prove those failures are detected.
