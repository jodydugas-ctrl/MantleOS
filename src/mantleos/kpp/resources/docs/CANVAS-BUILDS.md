# Preview-first app construction

MantleOS and standalone KPP use `mantleos.kpp.build` for the same construction
workflow. An Engram or agent should open an independently useful first slice in
the authorized Canvas while the recipe is **BUILDING**, then keep that instance
usable as Chase implements and checks the remaining Anchor requirements.
Final portable-document generation must not hold up the first useful preview.

## Host sequence

1. Pin a recipe with measurable Anchor obligations and a declared pursuit budget.
   Identify the smallest useful interaction. A progressive-web recipe pins its
   initial HTML, CSS, base behavior and JSON state adapter before workspace creation.
2. Create the workspace and open the first useful slice with the actual host's
   Canvas/app-preview tool. Check an interaction. The existing `ProgressiveBuild`
   API publishes shell and module revisions through a bound progressive bridge;
   KPP's loopback preview keeps its base app usable before extensions arrive.
3. Read `python -m mantleos kpp build-step --workspace DIR` (standalone:
   `python -m kpp build-step --workspace DIR`; carried Body:
   `python runtime.py kpp build-step --workspace DIR`). Implement and check its
   next ready obligation, preserve current inputs/drafts/selections/results, then
   read a fresh step. Dependency prerequisites are pursued before their dependents.
4. Keep Chase active until all mandatory obligations have current evidence and
   the required explicit Baker acceptance. A visible app, installed module or
   passing test does not confer acceptance. `kpp complete` remains a separate gate.
5. Package the complete `.anchor` with its exact program, receiver bridge and
   compiled targets. Receiving an already-built app still uses APP_LAUNCH_ONLY.
   Do not rebuild the bridge and Python target for every streamed source fragment.

The host must preserve its typed conversation/release protocol and checked-effect
authority. This sequence introduces no Anchor opcodes and no implicit delegation,
model provider, background scheduler or approval. If the host lacks an interactive
mount operation, report that result and provide the browser artifact explicitly.

## Bounded host driver

`mantleos.kpp.build.step(workspace)` returns a small packet derived from the
existing recipe, dependencies, current acceptance and preservation coverage.
It creates no second requirements registry. Decisions are `CONTINUE`, `BLOCKED`,
`READY_FOR_COMPLETION` and `COMPLETE`. Only current scoped acceptance can satisfy
the recipe. Optional work is excluded unless it is a prerequisite for required work.

```python
from mantleos.kpp.build import run

# These are caller-supplied, authorized host operations, not model proposals.
# open_preview(step) opens/checks the actual first surface and returns the host's
# OPENED/APPLIED receipt. refine(step) does scoped work/checks and returns
# CONTINUE, BLOCKED or AWAITING_REVIEW. It does not gain acceptance authority.
result = run(workspace, open_preview=open_preview, refine=refine, max_cycles=16)
```

The driver opens the preview before invoking refinement. It re-reads the graph
after every cycle, rejects recipe changes, and retains every unsatisfied obligation.
It reports pending review or exhausted budget with a resumable current step.
Exceptions propagate for host reconciliation; unknown effects are not replayed.
A failed or unavailable mount stops refinement. Serving a URL or creating a file
alone is not an OPENED/APPLIED host receipt. The driver never calls `accept` or
`complete` and cannot independently establish that a host's rendering claim is true.

## Loading and chat context

Public browser preparation and native app execution verify framing, section
digests, source pins and the exact program/HTML/Python/bridge relationship once
per operation. Verified sections are reused during that operation. No persistent
cache can conceal changes on the next launch. Portable payload bytes remain exact.

Chat requests carry the small construction contract, rather than an entire
Notepad app example in every ORIENT/RESPOND frame. An explicit caller can request
`anchor_apps.request_contract(text, include_example=True)` when an example is
needed. Native profile validation and the final self-contained artifact remain
required. Engram projections and KPP handoffs use the same source-defined build
rule. Newly built Bodies carry KPP preview assets/resources and expose
`python runtime.py kpp`, so their advertised build tools work without the development checkout.
Existing archived Engrams retain their original runtime snapshot; this source
change does not rewrite private identities or carriers.

## Executed checks and limits

The local browser check opens a working calculator before extension installation,
verifies addition and subtraction, installs an extension into the same mounted
instance, retains inputs/result, exercises the extension and rechecks the base
calculation. Unaccepted recipe obligations remain open. Shared regression tests
cover loop ordering, continued pursuit, dependency scheduling, review/budget stops,
scope drift, source/target tamper refusal and isolated carried-Body tooling.

`tools/benchmark_canvas.py` compares matched fresh local Python processes against
a saved baseline and checks exact app/HTML/preview output parity. Its timings
measure preparation, materialization and file delivery. They do not measure a
live LLM's generation speed or the chat service's Canvas mount latency. No claim
of universal receiving-model behavior follows from local execution. See the
release verification record for measured results and remaining platform limits.
