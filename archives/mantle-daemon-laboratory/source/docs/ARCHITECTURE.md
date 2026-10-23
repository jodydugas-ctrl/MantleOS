# Architecture and pass conditions

The constitution is durable but not experiential: identity, PRIMER, IMMUNE rules, SPECIAL
boot law, mission, authority, and developmental requirements live under `genome/`.
SELF is loaded as `PRIMER + IMMUNE + SPECIAL` before ordinary VCW interpretation.
Experiential entries live only in
the exploded `vcw/` PNG layers. `STACK.json` binds each band to a layer, driver, size, and
hash.

The minimum BODY is intentionally narrow:

- Senses accepts one structured event and routes it to Memory.
- Memory appends immutable, hashed entries to the events band.
- Nervous assembles a deterministic context snapshot.
- Immune verifies the stack and records faults.
- Limbs exposes a receipt-only output surface.
- Heart owns ordering and checkpoint decisions.

The Heartbeat order is frozen as:

```text
load -> pre-verify -> sense/circulate -> BODY mutation -> post-verify
      -> receipt -> guarded Git commit -> stop
```

The repository adapter is deliberately small: `head`, `status`, `commit`, and parent
guarding. The BODY does not call GitHub APIs. A future Actions adapter can implement the
same boundary without changing physiology.

The local Actions emulator exercises read-only, write-enabled, and write-loss modes against
the same Heart entry point. A missing checkpoint is reported as non-persistence; it is not
represented as a successful transition.

`daemon.github_actions.ActionsContext` maps repository, SHA, ref, and explicit checkpoint
permission into the same narrow seam. It does not treat a GitHub token's presence as
authority.

`tools/full_audit.py` is the local release gate: it verifies constitution, stack, receipts,
the unit suite, three crash-matrix repetitions, and an isolated 100-incarnation endurance
run by default.

## Accepted durable paths

`STACK.json`, `vcw/*.png`, `receipts/*.json`, and the constitutional `genome/` files may
be read by the runtime. A Heartbeat may change only the VCW stack and a new receipt.
PRIMER writes, path escapes, unverified candidates, and foreign executable tissue are
refused and become visible immune evidence.

The identity record pins the PRIMER SHA-256. A changed PRIMER cannot enter a normal
Heartbeat until an explicit constitutional update changes that pin.

VCW semantics are boot-declared by SPECIAL. The decoder never infers a Book/Dialect from
the filename, colors, layer number, or model confidence. Transported or foreign material
is candidate/OTHER until the Body verifies and admits it.

Developmental records identify organ source paths, runtime compatibility, hashes, and
proving tests. A registry record is candidate tissue until its hash and tests pass.

## MIND seam

`daemon.mind.Mind` is a proposal interface. `FakeMind` returns a deterministic proposal,
but BODY admission remains the only write path. The live provider phase requires an
explicit provider and secret-boundary decision; this specimen intentionally does not
choose one. `AlternateFakeMind` exists only to prove that provider-shaped cognition can be
replaced without changing identity or the canonical persistence path. `HttpJsonMind` is a
provider-neutral opt-in adapter: endpoint and credential are environment-only, and the
proposal is redacted before BODY admission or receipt persistence.
