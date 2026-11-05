# Owner-reviewed editor source

This is an incremental part of the full Community Chase, not a complete editor
backend or a change to its acceptance scope. Node-RED remains the Body.

Within the existing Community design, `BH-COMMAND` receives the explicitly
reviewed profile, `N-HOST` owns the loaded presentation snapshot, and
`WH-CONTRACT` checks source/path/size boundaries before admission. The same
canonical Anchor applications describe those responsibilities; this JavaScript
loader is host integration, not a new executable Anchor profile. Asset admission
does not satisfy the separate workflow, effects or acceptance obligations.

The optional `examples/anchor-studio/editor-assets.cjs` loader accepts a locally
provisioned `n8n-editor-ui` **2.46.4** package. It does not install dependencies,
run package scripts, start an n8n server, configure a provider, or grant effects.
The version is the existing pinned Chase reference, not a claim about the latest
upstream release. Assets are not bundled in either GitHub project.

After reviewing the source and its applicable license, use the project-local
Node executable with the following commands. Choose an unused profile file:

```console
node examples/anchor-studio/editor-assets.cjs pin --package LOCAL_PACKAGE --profile NEW.json --revision 261663556d98c9502663f6618edd8edd537e5688 --reviewed
node examples/anchor-studio/editor-assets.cjs check --package LOCAL_PACKAGE --profile NEW.json
node --test examples/anchor-studio/editor-assets.test.cjs
```

`studio.editor-source/1` binds package identity, declared upstream revision,
every file below `dist`, and the exact `package.json`, `LICENSE.md`, and
`LICENSE_EE.md` bytes. The revision is owner-supplied provenance; this utility
does not establish that an npm package was reproducibly built from that commit.
Hashes establish integrity, not authentication, license permission, user
identity, execution support, or Baker acceptance. Profiles contain no local
paths, credentials, resident identity, or private memory.

On load, the loader validates the complete profile, rejects changed/missing or
extra files, links, special files, ambiguous case-only names and unsafe paths,
then retains a private snapshot of the verified bytes. The default limits are
2,048 files, 10 MiB per file, 64 MiB in total, and a 1 MiB profile. Directory
traversal is also bounded. A newly opened session rechecks the complete source;
an already loaded snapshot remains unchanged if disk contents or caller-owned
objects subsequently change. These checks are a cooperating owner-local
boundary, not protection against an administrator or a compromised Node process.

`loadSnapshot` exposes copied asset bytes and original license notices. Its
`index()` prepares the known root-path placeholders, inserts fixed same-origin
`rest` endpoint metadata and generates a fresh nonce. JavaScript and CSS
root-path placeholders are expanded in memory. The installed package is never
rewritten. A host must apply its own navigation, origin, authorization, HTTP
content-type, error and effect boundaries before serving these bytes. Importing
this module or pinning a profile never activates an editor. The default launcher
continues to open the existing Studio; the optional host below requires a
separate reviewed selection. Ordinary Node-RED remains available at `/red/`.

The synthetic tests cover deterministic admission, required review, immutable
snapshots, notices, same-length changes, missing/extra source, profile changes,
path attacks, junction/symlink rejection, limits, and read-only checks in fresh
receiving processes. The fixtures contain synthetic notices and establish no
upstream licensing or full n8n behavioral claim. Real browser editing, backend
execution, expressions, triggers, credentials, settings and current-candidate
cumulative verification still require their separate recipe evidence.

## Optional resident editor host

The foreground Studio launcher can serve the selected editor over its existing
Node-RED Body. It consumes the existing `studio_workflows` storage worker and
the same resident controller. It starts no n8n backend, secondary resident,
HTTP courier to another NEST, provider route, or automatic fallback.

`editor-catalog.cjs` admits a separately reviewed, data-only catalog paired to
the exact editor digest. Its fixed inventory is `nodes.json`, `credentials.json`,
`node-versions.json`, `public-settings.json`, and `PROVENANCE.json`. The catalog
contains descriptions, not executable node implementations or stored credentials.
Provenance binds the four data files and pinned upstream revision; reference
owner/project identities must not be imported. Public settings require host
placeholders and disabled telemetry. Limits are 24 MiB per file and 32 MiB in
total. `pinCatalog` creates the reviewed profile; `loadCatalog` rechecks its
complete contents and retains an immutable snapshot. The installation verifier
binds both source profiles into `studio.editor-installation/1`.

After provisioning and reviewing these local inputs, stop Studio in stasis and
select them explicitly. Existing installations whose controller source changed
also require the existing reviewed source rebind and provider-route review;
retain their accounting database and exposure. Do not copy a route to reset a
budget or bypass recovery of uncertain requests.

```console
python -m mantleos studio editor-configure --nest PRIVATE_NEST --node NODE_EXE --package-root LOCAL_PACKAGE --editor-profile EDITOR_PROFILE --catalog-root LOCAL_CATALOG --catalog-profile CATALOG_PROFILE --reviewed
python -m mantleos studio editor-status --nest PRIVATE_NEST
python -m mantleos studio run --nest PRIVATE_NEST --node NODE_EXE --modules NODE_MODULES
```

The selected editor opens at `/`; `/studio` retains the design/KPP workspace.
No username/password prompt is introduced. Local navigation establishes the
existing same-owner, loopback session; origin and websocket checks still apply.
After a restart, `/?studio_connect=1` refreshes that session in another tab
without navigating away from an existing draft. Browser preservation of an
unsaved draft across that reconnect remains a separate qualification case.

Fresh local presentation records describe the owner/project to the editor;
they are not an AppAI identity, credential store, or authority grant. The AppAI
panel uses the resident's verified persona metadata, status, conversation and
committed-result operations. It receives no PRIMER, private frames, provider
keys, approval operations, or intermediate model tokens. Result retrieval and
replay invoke the Body's current release checks. A displayed commit digest
establishes continuity within this trusted host, not independent authentication.

The host supports bounded workflow draft create/list/read/update over the
canonical storage interface. Each update requires its loaded version and uses
the full storage revision for compare-and-swap. The n8n display checksum is a
separate compatibility projection and cannot establish complete state integrity.
Unknown operations, including general workflow execution and credential-secret
management, return explicit errors. They remain mandatory unfinished Community
obligations. No simulated execution or empty credential inventory supplies
success. Installation and these tests grant no Baker acceptance.

Configuration is held in the existing controller database. Selection requires
the controller to be stopped, stasis, no outstanding cognition and owner review.
The launcher rechecks both snapshots on startup; warm requests reuse them.
Controller source and selected configuration bind pending cognition, including
observation-bound second frames. Changed bindings invalidate pending work.
Withdraw the presentation after stopping in stasis with:

```console
python -m mantleos studio editor-disable --nest PRIVATE_NEST --reviewed
```

Withdrawal records an event and retains memories, source, workflows and native
Node-RED flows. It is not an automatic rollback of uncertain effects.

The optional `test_studio_host.py` uses a real owner-provisioned Node-RED runtime
and a synthetic resident. It exercises normal embedding, selected presentation,
full synthetic PRIMER delivery, supervised fixture commit/replay, fresh-process
reload, stasis and withdrawal. A real deployed Node-RED HTTP flow must keep
working throughout. `STUDIO_MODULES` and Node on `PATH` opt into this test;
otherwise it explicitly skips. This is native runtime and protocol evidence,
not a real browser or live-LLM qualification of the new host. Separate socket
tests check the shared authenticated dispatcher and preservation of host sockets.

## Reviewed manual execution

Add `--manual-execution` to the reviewed `studio editor-configure` command to
select the pure manual Node-RED profile. The selected configuration pins this
grant alongside the editor source. Studio checks the configuration and active
Body before admitting and dispatching each run. Reconfigure in stasis with the
flag omitted to withdraw the execution grant.

The current profile accepts one Manual Trigger and strict IF 2.4 nodes on
connected, acyclic main-port graphs with a single input per node. It accepts
literal conditions and direct `$json.field` paths in left operands. The worker
limits graphs to 64 nodes and 256 KiB, runs at most two child runtimes at once,
and bounds each child to 30 seconds. The profile has no credential, external
effect, arbitrary script, pinned data, published trigger or general expression
capability. Unqualified node options or graph shapes return an explicit error
before dispatch.

The native editor runs the committed saved revision. Studio binds each
execution to that graph and records node inputs through their source links,
outputs, and terminal state. The initiating editor receives a completion
notification after the result commits, and the native Executions view reads
the retained snapshot. Shutdown closes execution intake and waits for
admitted work to finish recording.

The editor's Stop request targets the current run. Studio records cancellation
after the owned child exits in response to Stop, or when it confirms that no
child was started. If the run finishes first, its existing result wins. A
repeated Stop reads the committed cancellation without creating another run.
The Windows browser qualification observed a canceled run and a separate
successful run of the same saved revision. Crash recovery and retention of
partial node output from canceled runs remain open.

The Windows qualification used the normal launcher and a synthetic workflow.
Changing a numeric IF operand from 42 to 60 through the editor moved the item
from false to true, matching the reference. Both runs reopened with their
original saved revisions. This qualifies those journeys within the manual
profile. Full execution and expression parity and Baker acceptance remain
separate gates.

## Initialization and connection contracts

The selected editor initializes a separate owner-local descriptor index through
the reviewed configuration operation. `EditorInventory` retains versioned
credential descriptors, tags and favorites. Credential descriptors accept only
ID, name and type; secret-data and claimed-authority fields are rejected. Registered
metadata survives reopening and updates require the current revision. Browser
routes can read this index but cannot register metadata, secrets or grants.
An absent or damaged index fails explicitly instead of reporting an invented
empty inventory. A newly initialized index genuinely has no entries.

The usable-credential projection remains empty because this runtime has no
qualified workflow credential-use grants. Registering a descriptor does not
make it usable; the MIND's separately configured provider keys are not read or
copied into this index. Full credential management and use remain unfinished obligations.
The index is application metadata, not Engram experience, a secret vault or a
second requirements/acceptance database. It stays outside saved Studio projects.

The pinned Community project setting is a structured quota,
`enterprise.projects.team.limit = 0`; flattening it into a Boolean breaks the
frontend project store. The host preserves that type. Its Community usage view
reports no published triggers or evaluations, matching the runtime's current
limits; it grants no upstream license activation or enterprise functionality.

`/healthz` checks the real Body controller and workflow-storage worker, including
their existing source checks. It returns HTTP 503 when they are unavailable or
the storage schema is invalid. Stasis still reports reachable services; ordinary
Node-RED automation continues. This is connectivity and storage readiness, not
complete historical verification or Baker acceptance. The editor's separate
backend-health and websocket indicators must both be checked.

The websocket adapter admits the pinned client's `heartbeat`, `workflowOpened`
and `workflowClosed` notification shapes. Presence neither acquires a write lock
nor admits an effect. Other messages, including forged authority attached to a
presence notification, remain rejected. Closing a valid presence notification
previously caused repeated reconnects; a missing JSON health endpoint separately
caused an Offline indicator even when the socket was open. Tests preserve these
distinct consequences rather than setting a frontend indicator directly.

Real browser qualification of the isolated synthetic host exercised the native
Add new item → New workflow → Add first step → Trigger manually path, followed
by Ctrl+S and a backend check of the saved graph. The live resident on the
preceding source candidate separately completed one ordinary OpenRouter turn
with its full PRIMER and exact committed release. That live observation does not
qualify later source revisions, hidden reasoning, general workflow execution or
complete Community parity. A new-draft console exception was also observed on
the real pinned n8n reference; the upstream assets were not rewritten to hide it.
