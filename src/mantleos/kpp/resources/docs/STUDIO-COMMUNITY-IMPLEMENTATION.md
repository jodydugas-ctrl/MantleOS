# Full Community parity implementation

The target remains all reviewed n8n 2.46.4 self-hosted Community user functions,
GUI, expressions, execution behavior, credentials and settings on the Node-RED
Body, plus owner-configured automatic cognition and independent Baker review.
The product is BUILDING. Neither the earlier IF example nor these implementation
checks establish completion.

`recipes/anchor-studio-community-parity.json` retains all 94 obligations of the
earlier deep-chase recipe, unchanged, and adds twelve explicit obligations for
the full end state. The earlier recipe and its workspace are not migrated.
Static discovery is still incomplete. The full reference/runtime inventory gate
remains mandatory, including dynamic operations, settings and edition guards.

## State ownership and actual implementation

The canonical BlackHole, Neutral and WhiteHole definitions remain unchanged.
The same design applications receive commands, own workflow state, coordinate
the host and enforce boundaries. Python and JavaScript implement the storage,
transport and runtime integration; this is not a new executable Anchor profile.

`mantleos.studio_workflows` owns operational n8n-shaped draft documents and
retained versions in a private SQLite application store. It is separate from
canonical Engram experience and the portable design contract. The data model
retains node variants, parameters, credentials **references**, named connections,
item pin data, settings and unknown node types for subsequent runtime review.
It does not admit unknown nodes for execution.

Actual operations include create, get/list/search, update, duplicate, archive,
unarchive, delete, retained history and restoration into a new version. Expected
revisions reject conflicting writers. Request bindings commit atomically with
the saved version/head. Replays recheck host authority and return the original
result without advancing a newer head. Initial setup survives a rejected first
request; interrupted writes retain the prior committed version.

Creation optionally accepts a separate host-supplied `id`, for editors that
allocate a workflow URL before the first save. A current or removed ID cannot
be reused. The ID participates in request replay binding and ordinary revision
checks still apply. An `id` inside imported document data alone is not adopted;
legacy creation continues to allocate a fresh identity. This option supplies no
deployment authority and performs no node execution.

Archive/unarchive advances the saved version. Permanent removal deletes the
operational snapshots and discards their earlier replay payloads; replay cannot
resurrect a removed workflow. This does not erase canonical Engram experience.

Saving/importing never publishes a workflow. Publishing requires a separate
checked Node-RED deployment and observed runtime result. The draft store cannot
declare its own content active. The runtime publication adapter and full
automation editor remain required implementation work.

The foreground Studio exposes these owner-local endpoints:

| Operation | Endpoint |
| --- | --- |
| List/search | `GET /studio/workflows` |
| Read saved workflow | `GET /studio/workflows/:id` |
| Retained versions | `GET /studio/workflows/:id/history` |
| Explicit draft mutation | `POST /studio/workflows/mutate` |

Mutations carry `action`, `request_id` and operation-specific data; existing
workflows additionally require `id` and the expected `revision`. The HTTP session
boundary and trusted controller supply authority, never an `owner` field in a
document. Draft documents use a separate bounded JSON-lines worker, so large
workflow data does not expand the cognition-frame budget or queue behind MIND
processing. Source/founding checks still run at the host boundary.

The shared transport preserves split UTF-8 characters, checks packet types and
bounds queues/messages. Unknown outcomes are not automatically retried. Loss of
the workflow worker reports unavailable state while ordinary Node-RED flows
and the Prime Body remain independent.

## Automatic cognition work

The owner-selected route is explicit OpenRouter configuration. No default model,
credential or budget is bundled. `mantleos.studio_mind_config` reads an owner file
as data: ordered model IDs, separate Mind/Limbs keys, and exact finite budgets.
Public projections exclude keys, source paths and credential fingerprints.
Loading configuration makes no provider request. A budget without a reset
period is a total cap; reloading settings cannot replenish it.

The optional foreground provider worker reserves spending durably before sending,
outside Body coordination transactions. Its stable accounting database has separate
MIND and combined-limb accounts. Reservations survive configuration changes and
restart; uncertain outcomes require review and never retry automatically. Remote
cost telemetry cannot replenish a reservation. This conservative policy may stop
below the nominal cap. It cannot prevent a provider billing error or an owner's
full-system rollback.

Accounting is shared by owner configuration rather than initialized anew for
each NEST. The default database is `OWNER_FILE.studio-budget.sqlite`, beside the
private owner file; `--accounting-file FILE` selects an existing shared location.
All NESTs using that location share one MIND cap and one combined-limb cap.
The route pins its opaque database identity. Missing, substituted or incompatible
accounting fails closed; configuration and status make no inference calls.
Reconfiguration retains the existing account and never switches it implicitly.
Historical per-NEST accounting must be selected explicitly with
`--accounting-file NEST/mind-accounting.sqlite`; other NESTs can select that same
file. The reviewed schema upgrade retains every attempt and conservative hold.
There is no automatic account merge, reset, refund or period rollover.

This remains cooperating local accounting, not a provider-wide billing control.
Different owner files must explicitly select the same account when sharing a
cap. Copying or restoring the complete account/controller state, administrator
tampering and independent applications using the key remain outside this guard.
The accounting file can retain private provider proposals; keep it, its sidecars,
owner files and route files outside Git and portable project exports.

`studio mind-configure --nest NEST --owner-file FILE --catalog FILE --reviewed`
requires stasis and a reviewed public model/provider catalog. The catalog contains
`allowed` physical-model/provider-label mappings, `provider_slugs`, `free_models`,
and source-bound `provenance`. It supplies no code or host permissions. Configuration
remains private NEST state. `studio mind-status` reports redacted settings/accounting;
`studio mind-serve` provides the controller-only foreground pipe. Neither operation
starts a provider request. Starting Studio with a valid configured route enables
automatic handling of pending conversations; absent configuration preserves the
supervised route. Deterministic limbs do not acquire model calls automatically.

Only configured model routes and pinned providers are requested. An explicitly
selected free router may return a different physical model only when catalog-bound
and accompanied by zero-cost telemetry. The complete Body frame and PRIMER are
sent once for an ordinary proposal. After a checked action, a second frame binds
the verified observation. HTTP conversation submission returns an acknowledgment,
not private PRIMER/memory context. Display retrieves only Body-committed replies.

Body admission independently checks the retained provider proposal, current source,
owner configuration and route revision. A courier cannot substitute a reply or
authorize an effect. Exact Journal replay remains separate from provider recovery.
The local same-owner process boundary has not been qualified as private-MIND
isolation. Synthetic provider tests establish bridge behavior, not live-model use.
Body authorization and Baker approval remain independent.

The presentation stream rechecks the Body's current release authority before
sending an exact committed reply. It sends neither private frames nor intermediate
model tokens, limits connections and slow-client buffering, and closes on shutdown.
Polling remains a recovery fallback. Persona labels come from a verified loaded
Journal, rather than a fixed Cuttlefish heading. An unloaded Journal reports pending
verification. These bindings establish observed metadata, not hidden persona fidelity.

Journal verification uses a single SQLite read snapshot for canonical records,
metadata and replay bindings. A deterministic concurrent-commit test reproduced
false corruption with separate queries and passes with the snapshot boundary.
Later foreign commits still invalidate the next refresh. This changes storage
consistency without changing Anchor or canonical-record semantics.

Cold Journal opening still verifies its retained Body snapshot. Profiling nine
resident sessions found repeated manifest file opens dominating startup. Manifest
verification now streams all bytes through one MiB of scratch space per reader,
uses at most four scoped readers for larger inventories, and bounds queued work.
Small inventories stay sequential. Inventory, path, digest and byte-length checks
remain mandatory; timestamps do not establish integrity. Errors close and join
readers before temporary snapshot cleanup. These readers perform verification I/O
and do not create Engram limbs, model calls or persistent workers.

For a repeatable startup-only comparison, stop a synthetic Studio instance in
stasis, then run `python tools/benchmark_studio_startup.py --nest NEST --output NEW_DIRECTORY`.
The harness acquires cooperating worker leases and alternates fresh processes
using a sequential manifest-loop reference and the current verifier. It records
three cold samples per mode and twenty reused-session checks per process. Outputs
exclude PRIMER contents and conversations. Startup measurements do not qualify
ordinary-turn or provider latency; the separate Journal benchmark retains those
synthetic history/attachment cases.

An isolated Windows/Node-RED qualification on 3 November 2026 used the owner's
selected OpenRouter primary with synthetic founding material: four committed
turns covered a remembered marker, recall, correction, and checked `body.status`.
Five actual provider calls included the observation-bound second generation.
Reported total inference cost was $0.002609506; conservative reservations retained
$0.049424 against the $1 MIND account. No limb inference calls occurred.
Acknowledgments ranged from 42–221 ms; ordinary committed turns took 1.43–2.36 s
and the checked-action turn took 11.65 s. These are individual observations,
not a performance guarantee or a distribution benchmark. Native Node-RED probes
remained successful while waiting; exact committed replies replayed without
another provider call. The real resident persona, live free fallback, platform
isolation and full-product Baker acceptance were not qualified by this test.

## Evidence and outstanding work

Focused synthetic tests cover state transactions, concurrent saves, request
replay, graph/reference errors, credentials-reference admission, interruption,
retained-version corruption, large JSON and transport failure/Unicode boundaries.
The local HTTP qualification also exercised the actual Studio/Node-RED embedding,
injected a workflow-worker failure and reopened saved state in fresh processes.
These observations cover the implementation stated above, not complete n8n
workflow execution or GUI parity. Whole-product obligations remain unaccepted.

Complete node/credential operation accounting, runtime publication, automation
canvas and command dialogs, expressions, execution history/cancellation/retry,
triggers, encrypted credentials and settings, automatic live cognition, full
matched reference journeys, release gates and explicit product-wide Baker review
remain required. None is dropped because another layer passes its tests.
