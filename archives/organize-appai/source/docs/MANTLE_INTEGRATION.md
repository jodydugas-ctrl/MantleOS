# MantleOS integration

The `.mantle/` nest is anchored to the product working copy and intentionally ignored by
Git because it contains Body-private identity material. `MantleBridge` discovers a pinned
MantleOS source tree through `MANTLEOS_SRC` or the isolated workspace layout and degrades
cleanly when neither a resident nor MantleOS is available.

The bridge uses canonical public interfaces:

- user questions enter through `org.senses.inhale`;
- configuration maps and diagnostic traces enter bounded append-only memory;
- execution failures also become `org.immune_event` records;
- model interpretations go to `discoveries` as `inferred` and `verified=False`;
- rule drafts go to `discoveries` as `proposed` and `verified=False`;
- approved simulations may be labelled `verified`, while actual action receipts are
  labelled `executed`.

`run` and `sim` remain resident-independent. When the operator explicitly supplies
`--mantle-trace`, a maximum of 1,000 sanitized events is buffered and appended after the
host run. Sink failure is reported but cannot change the host operation's result.

The labels `observed`, `verified`, `inferred`, `proposed`, `refused`, and `executed` are
preserved in stored content. The bridge never uses `promote_to_fact`; external cited
evidence is required by MantleOS for that operation.

Loading a saved organism deliberately resets runtime Stage-1 capability. Therefore
`mantle-status` reports both persisted certification evidence and the process-local runtime
state. A saved boolean is not treated as fresh fusion authority. No MIND is fused by
default, and deterministic `explain`, `why`, and proposal generation remain operational.
Optional answers are stored as `inferred` only after their typed citations are checked
against the bounded evidence supplied to the provider.

## Interactive resident terminal

`python -m organize.mantle_appai.terminal --product-root <product>` provides the canonical
three-lane boundary: slash-prefixed maintenance commands, ordinary resident conversation,
and Mantle's bounded MIND path. `/key` must be typed alone; the credential is collected by
a non-echoing prompt, remains in process memory, and is never written into the nest, logs,
Git, command line, or proposal state. The default transport is Mantle's official
OpenRouter-compatible adapter with model `openrouter/free`; explicit `/model auto`
selects `openrouter/auto`.

Slash commands are deterministic Body calls, not MIND prompts. Each accepted, refused, or
cancelled command is sensed in redacted form and appended to resident memory. Successful
configuration changes use `BODY_CONFIGURATION_CHANGED`, list only the changed public
fields, and emit `body_configuration_changed` on the Mantle bus so the next assembled MIND
context can observe that the Body changed. No credential value or unrestricted state is
included.

MIND fusion remains gated by fresh Stage-1 evidence plus explicit, target-bound operator
and guardian decisions. `/credits` feeds Mantle's local symbiosis ledger; it does not buy or
modify funds in the user's OpenRouter account. Provider/network failures fall back to the
deterministic host-map answer.

The Grimoire selected for this integration reading gate was `grimoire-v0.10`, selected from
the repository edition index. It informs the resident's VCW profile; it is not a procedure
runtime and does not redefine ordinary host modules as organs.
