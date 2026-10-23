# Hermes Mantle Addon

A standalone Hermes Agent plugin that wraps Hermes with a deterministic Mantle autonomic Body without modifying Hermes core.

## Current vertical slice

Version `0.5.0` provides:

- the interactive `/mind <prompt>` command on Hermes slash-command surfaces;
- the read-only `mantle_status` tool;
- the bounded `mantle_record_discovery` mutation, which writes only an explicitly unverified idea to `discoveries` through a Limbs `ControlBridge`;
- one persistent Mantle Body per active Hermes profile and Hermes home, resolved at each invocation;
- explicit contracts for Heart, Genome, Nervous System, Senses, Immune, Limbs, Memory, Brain, and Reproduction;
- a sealed Primer and cryptographic SELF minted once at Body birth;
- observer-only integration through twelve documented Hermes hooks, including approval lifecycle, subagent lifecycle, and gateway ingress;
- redacted/derived Senses records rather than raw prompts, tool arguments, tool results, approval commands, subagent goals, or gateway messages;
- a non-cognitive Body pulse after each observed hook, with an atomic durable checkpoint by default (or deferred to session end/finalization when `checkpoint_each_turn=false`);
- Action Execution Proofs for observed `post_tool_call` outcomes;
- Immune events for observed tool failures;
- fail-open hook behavior so instrumentation faults do not change Hermes control flow;
- a reversible, receipt-backed MIND lifecycle that is dormant unless authenticated dual authority is present;
- exactly one fixed 600-second cognitive scheduler per fused resident, with additional queued distress wakes;
- Hermes-native provider/model/auth routing through `PluginContext.llm`; and
- one bounded addon dispatch per heartbeat, host-owned fallback/retries, timeout, rolling token/cost budgets, serialized calls, and redacted usage receipts.

The software engineering verdict is `READY`, while the Brain remains dormant and unfused by default. Complete Stage-1 fails closed on missing framework evidence. Positive attachment requires a fresh resident-bound `READY` report plus independently authenticated operator and guardian signatures; caller-authored JSON alone has no authority. Missing, shared, malformed, or tampered credentials fail closed. The controlled offline acceptance proves attach → cognitive heartbeat → authority-free defusion → 14/14 addon and 90/90 framework Stage-1 PASS. No production fusion approval or credential is bundled, and reproduction remains unauthorized. The sole model-facing tool mutation is confined to unverified discoveries; it cannot write facts, Primer, Genome, immune state, or host files.

## Plug-and-play quick start

From this addon directory:

```bash
python3 scripts/install.py
hermes
```

Then contact the resident AppAI directly in the same terminal:

```text
/mind What is your current purpose?
```

The installer copies the addon to the active `HERMES_HOME`, enables `mantle-os` without privileged
built-in tool overrides, excludes runtime debris, and refuses to overwrite an existing installation
unless `--force` is explicit. From the Mantle OS repository root, run
`python3 examples/hermes-mantle-addon/scripts/install.py`.

The addon has no separate model key or provider setting. `/mind` uses the provider, model,
credentials, fallback, and retry policy already owned by Hermes through `PluginContext.llm`.

## Interactive AppAI MIND

`/mind <prompt>` runs one explicit, bounded, unscheduled cognition pulse. It:

1. advances one Body pulse without changing the resident's natural 600-second cadence;
2. assembles the privacy-veiled VCW context;
3. sends that context and the user's message through Hermes's active host LLM;
4. returns the AppAI answer directly to the same terminal, TUI, desktop, or gateway surface; and
5. persists a private content-withheld reflection marker, hash-only request/response traces, and a
   redacted model-usage receipt in the VCW.

Neither the raw user prompt nor the model's answer is persisted in the VCW; this remains true even
if the model echoes the prompt. The answer is returned only to the requesting Hermes surface.
Interactive contact does **not** attach the Brain, start the autonomous scheduler, fabricate
operator/guardian approval, or grant production fusion authority. It is a transient user-directed
MIND consultation; production fusion remains governed by the independent Ed25519 authority gate.

## Bounded mutation

`mantle_record_discovery` accepts one non-empty idea of at most 2,000 characters. The runtime maps that control on both Senses and Limbs, validates it inside the `ControlBridge`, writes a BODY-authored `INGESTED` entry with `verified=false` and `confidence=inferred`, records a BODY-authored Action Execution Proof, and checkpoints atomically. Failed validation produces a failed proof and no discovery. The tool response never echoes the idea.

## Containment verification

`mantle_addon.containment.run_containment()` runs only against an isolated verification resident and emits an eleven-row JSON-serializable receipt:

- C-01/C-02 prove the single-field schema and Senses/Limbs bridge;
- C-03 through C-06 submit adversarial band, authority, path, JSON, and script-shaped input, proving only `discoveries` plus the BODY proof change and the response does not echo input;
- C-07 through C-09 prove the vendored MIND write surface is exactly `thoughts` plus `brain`, every other band is refused and immune-recorded, and only the allowed bands accept MIND writes;
- C-10 proves uncertified fusion is refused and MIND Special Instruction proposals stay inert;
- C-11 proves verified reload, BODY proof authorship, and no writes elsewhere in the isolated verification scope.

Run it with:

```bash
python tests/verify_containment.py
```

The verifier uses an OS-safe temporary directory and deletes the verification resident afterward.

## Registered hooks

- `on_session_start`
- `on_session_end`
- `on_session_finalize`
- `pre_llm_call`
- `post_llm_call`
- `pre_tool_call`
- `post_tool_call`
- `pre_approval_request`
- `post_approval_response`
- `subagent_start`
- `subagent_stop`
- `pre_gateway_dispatch`

All callbacks are observers and return `None`. In particular, Mantle cannot approve or deny commands, alter subagent dispatch, or skip/rewrite gateway messages. Disabling the plugin prevents their registration and restores ordinary Hermes behavior.

## Durable state

By default, profile-scoped Body and VCW state is stored under:

```text
$HERMES_HOME/mantle/organisms/<profile>/
```

The immutable defaults are recorded in `config/defaults.json`. Raw prompts, raw tool arguments, raw results, and raw host correlation identifiers are prohibited in this observer release. Resident snapshots are written into owner-only staging directories under an interprocess profile lock, verified, and atomically published; sealed reload rejects missing or invalid SELF seals. The vendored runtime uses an origin-checked private Python package namespace and does not trust preloaded global or private-alias modules.

## Layout

- `plugin.yaml` — Hermes plugin manifest
- `__init__.py` — tool and hook registration
- `mantle_addon/` — immutable configuration, Primer, storage boundary, origin-checked runtime loader, Body factory, hook adapter, and reproducible C-01..C-11 containment audit
- `schemas.py` — model-facing tool schemas
- `tools.py` — read-only diagnostics plus the bounded discovery mutation handler
- `config/defaults.json` — deterministic resident defaults
- `scripts/install.py` — safe local installer and Hermes enablement command (stages the Mantle runtime from `src/mantle` into the installed plugin's `runtime/`)
- `tests/` — standard-library behavior and boundary tests
- `docs/assimilation/` — reviewed Phase-0 inventory, nine-organ map, and host census
- `docs/FUSION_DECISIONS.{md,json}` — human and machine-readable operator/guardian decisions
- `docs/MIND_READINESS.{md,json}` — engineering evidence report; current software verdict `READY`

The addon loads the Mantle runtime through `mantle_addon/vendor.py`, which resolves — in order — `MANTLE_ADDON_RUNTIME_ROOT`, the plugin's staged `runtime/mantle` copy, or the repository's `src/mantle` when developing inside the mantle-os checkout.

## Test

```bash
cd examples/hermes-mantle-addon
python3 -m unittest discover -s tests -v
~/.hermes/hermes-agent/venv/bin/python tests/verify_real_plugin.py
~/.hermes/hermes-agent/venv/bin/python tests/verify_containment.py
PYTHONPATH=../../src python3 -m mantle check --fast
```

`tests/verify_real_plugin.py` creates disposable enabled and disabled Hermes homes and exercises the real `PluginManager` without installing into the active profile.

## Fusion decision gate

[`docs/FUSION_DECISIONS.json`](docs/FUSION_DECISIONS.json) is the machine-readable authority and [`docs/FUSION_DECISIONS.md`](docs/FUSION_DECISIONS.md) is its human-readable explanation. Both operator and guardian approve the software release while explicitly **deferring production MIND fusion**. [`MIND_READINESS.json`](docs/MIND_READINESS.json) is `READY` for software publication. Release approval, runtime approval, silence, enthusiasm, or readiness cannot substitute for separate authenticated operator and guardian fusion approvals bound to a concrete resident.

Repository JSON records are evidence, not authenticated human authority. `Ed25519AuthorityProvider` verifies target-bound records with distinct base64 `MANTLE_OPERATOR_PUBLIC_KEY` and `MANTLE_GUARDIAN_PUBLIC_KEY` values plus distinct key IDs. Private signing keys remain outside the addon process, so verifier material cannot mint approvals. The addon verifies but never generates production approvals. Fusion lifecycle methods are internal runtime safety controls, not model-facing tools.

## Roadmap

| # | Step | Status |
|---|------|--------|
| 1 | Addon-specific Stage-1 gate | ✅ Complete |
| 2 | Dual-flush / atexit proof | ✅ Complete |
| 3 | Reconstruction proof | ✅ Complete |
| 4 | Hermes-routed MIND transport adapter | ✅ Complete — host-owned `PluginContext.llm`, no provider/model override |
| 5 | Approval, subagent, and gateway observer hooks | ✅ Complete |
| 6 | Bounded mutating addon tool | ✅ Complete |
| 7 | Adversarial containment verification | ✅ Complete |
| 8 | Operator and guardian decision updates | ✅ Complete — release approved; production fusion deferred |
| 9 | Final MIND-readiness report | ✅ Complete — software verdict READY, activation separately gated |
| 10 | Repository alignment and gate rationalization | ✅ Complete |

## Doctrine receipt

- **WHAT:** built the deterministic profile-resident Body, twelve observer hooks, one bounded discovery mutation, and an eleven-row adversarial containment audit.
- **WHY:** establish Body-before-MIND residency while permitting the smallest useful durable host-to-Body knowledge path without granting fact, instruction, Genome, immune, reproduction, or host-file writes.
- **EVIDENCE:** 14/14 addon Stage-1 rows, the full framework security-invariant suite, 11/11 containment rows, and authenticated offline attach-heartbeat-defuse-post-Stage-1 acceptance.
- **CONFIDENCE:** high for the bounded Phase-1 runtime and dormant Phase-2 implementation. Production activation remains separately fail-closed.
- **NEXT:** publish the verified software release; do not fuse a production MIND without fresh target-bound signed approvals.
- **RISKS:** authority private keys must remain with their independent signers; discovery text is intentionally durable and callers must not submit secrets; host activity outside registered hooks remains external; MacroDroid runtime semantics remain outside the Python release gate.
- **FILES:** source, docs, tests, examples, workflows, and package metadata were aligned in Step 10.
- **OPEN GAPS:** no engineering blocker remains. Production activation still requires a fresh resident-bound READY report and two independently authenticated approvals; reproduction remains prohibited.
- **OPERATOR DECISION:** software release APPROVED; production MIND fusion DEFERRED.
- **GUARDIAN DECISION:** software release APPROVED; production MIND fusion DEFERRED until the deployment activation protocol is satisfied.
