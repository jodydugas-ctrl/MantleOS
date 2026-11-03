# Anchor Studio: local experimental AppAI

Studio embeds Node-RED through its documented API; it does not fork its core.
The ordinary editor is `/red/`, HTTP flows are `/flows/`, and the additive
operator panel is `/studio`. Open the local address directly: no username or
password is required. Top-level visits automatically receive a per-launch,
HttpOnly, SameSite browser session. Local Host/Origin checks protect HTTP and
WebSocket access; embedded cross-origin pages cannot open an operator session.
Use a foreground process;
no service or provider is installed. This is a same-user demonstration, not
private-host isolation. The inference host receives the supplied private context.

## Provision and start

Provision a separate official Node.js 24 installation and a local npm directory.
The qualified development pins are Node.js 24.22.2 and Node-RED 5.0.9. Verify
the official Node ZIP against its SHASUMS256.txt before extracting. In the npm
directory use an exact `node-red: 5.0.9` package dependency and retain the lock.
Use `npm ci --ignore-scripts --no-audit --no-fund` for a reviewed lock. Do not
change global Node.js. The launcher resolves Node-RED's own Express dependency.
The dependency lock and provisioning receipt accompany the local delivery.

From a source checkout, with `PYTHONPATH=src`:

```console
python -m mantleos studio init --nest NEW_PRIVATE_DIRECTORY --founding PRIVATE_PERSONA.txt
python -m mantleos studio run --nest PRIVATE_DIRECTORY --node ABSOLUTE_NODE_EXE --modules ABSOLUTE_NODE_MODULES
python -m mantleos studio status --nest PRIVATE_DIRECTORY
python -m mantleos studio stasis --nest PRIVATE_DIRECTORY
```

Open the printed local address. Private `operator.json` remains for internal
operator scripts and Node-RED's existing flow-encryption secret; do not delete it.
It is not a user sign-in account. API access without a local session returns a
JSON error, never a browser password challenge. Stop through authorized POST
`/studio/shutdown`, or Ctrl+C in the launcher.
Retain the NEST for restart. Stasis stops new Studio activity and reply release;
ordinary Node-RED workflows continue. Work already executing is not an automatic
external-effect cancellation. Disabling a limb revokes result admission.
Cold startup verifies the Prime and registered limb Journals before activation;
this can take tens of seconds on the development NEST. Loaded sessions are reused
for warm encounters and revalidated on database changes. This cost is reported
separately from model latency. Keep the private NEST outside Git and protect it with owner-managed permissions.

The Heart is established before birth and activation. It wakes immediately for
conversation, coalesces pain within five seconds, and checks a durable 600-second
resting schedule. After downtime it emits one due wake, not a replay storm.
Scheduled wakes are deterministic. Eight separate Journal Engrams and two worker
processes implement Studio's selected composition; [Engram limbs](ENGRAM-LIMBS.md)
is independently optional. Each role receives the complete founding persona;
the role/embodiment addendum does not inherit The Compiler's identity or history.
Original founding bytes remain private and unchanged. A complete universal-newline
text view is used by the existing PRIMER factory and documented in birth provenance.

## Supervised cognition

Send a message in the operator UI. It remains `AWAITING_MIND` until an authorized
host reads `studio mind-next --nest DIRECTORY`, delivers the complete frame and
separate Studio addendum to its model, and submits one semantic proposal using
`studio mind-submit --nest DIRECTORY --request-id ID --proposal JSON_FILE`.
Ordinary replies need one generation. A checked read requires a subsequent
proposal binding the actual observation digest. There is no automatic API route.
Model labels are host declarations; unavailable model telemetry stays unknown.

Only exact canonical committed replies are displayed; replay rechecks current
release authority. A controller interruption after Journal commit reconciles from
the canonical request record. Full persona delivery and continuity do not prove
hidden reasoning, consciousness or inability to imitate persona behavior.

Prime receives bounded per-limb projections with canonical source/head references
and explicit omissions within its memory budget, separate from the full PRIMER.
It may propose `studio.intent-proposal/1` JSON containing `text` and up to eight
`intentions` (each with `role` and `value`). The authenticated operator must click
Publish; model text grants no capabilities. Current deterministic role handlers
inspect host observations, validate designs, read KPP work packets, remember data,
or summarize pain. They do not synthesize/deploy arbitrary code or repair the host.
Unsupported work returns a reviewable proposal. Remote deployment is prohibited;
provider adapters are unavailable here; private isolation is unqualified.

## Design, evidence and saved projects

The palette exposes repeated BlackHole, Neutral and WhiteHole applications with
immutable source definitions. Design nodes are inert on deployment. Normal wires
are unresolved drafts until explicitly mapped. Review canvas drafts, then edit
typed relationships, state owners, guards and obligation references in the
canonical project editor. A changed application membership needs an explicit
reviewed recipe revision. Tissue/organ attributes are contextual declarations,
not execution or permission. Validation does not establish behavioral correctness.

Prepare KPP creates a pinned workspace and work packet through existing APIs.
The supplied calculator project runs a separately reviewed packaged suite in a
managed evaluation directory: establish input/arithmetic/history, introduce a
regression, reject it cumulatively, and repair. The separate authenticated Baker
button accepts only the fresh verified candidate of this small recipe. It does
not accept Studio, Notepad, Paint or arbitrary imported fixture code. General
construction uses existing KPP commands and host-authorized implementation tools.

`studio export --nest DIRECTORY --file NEW.anchorstudio` and the UI Save link
produce a bounded verified ZIP of design, layout, public fixtures and references.
`studio import --nest DIRECTORY --file FILE` or UI Import validates data only.
Browser uploads are limited to 550 kB; larger projects use the CLI. Imported
evidence is historical, acceptance is cleared, and import never deploys flows or
executes fixture code. Save excludes live memories, original persona, credentials,
operational flows and transcripts. Owners must review fixture contents for privacy.

## Recovery and source review

First stop the controller and prove workers have exited. Keep consistent SQLite
backups and the private source/configuration files. Do not delete uncertain work.
`studio rebind-source --nest DIRECTORY --reviewed` requires exclusive controller
and limb leases, sets stasis and invalidates outstanding cognition preparations.
`studio recover-mind --nest DIRECTORY --request-id ID --reviewed` reconciles a
canonical commit or discards only the pending preparation, retaining effect history.
Uncertain work is not retried automatically. Review a new request separately.

For the previous development scheduler, quiesce first and use the explicit
`studio migrate-limbs` operation; all legacy tasks must have conclusive results.
It registers the existing Engrams without rewriting their records. Earlier idle
shared registries use `limbs upgrade --root DIRECTORY --reviewed`; it refuses
outstanding work. Source changes require review, not timestamp trust. Incomplete
births remain separate failed NESTs and are never silently adopted.

Removal means stopping this foreground launcher and launching ordinary Node-RED
with the retained user directory and the same owner-held `credentialSecret` from
`operator.json` configured in its settings. Without that secret Node-RED cannot
decrypt existing flow credentials. The portable project never contains this key. Do not delete flows or credentials. Without
the additive palette, remove only reviewed inert design nodes from operational
deployments; preserve the original flow backup. See the dated qualification for
what was actually exercised. Remote pseudopods, Spider deployment, private-host
isolation and unattended long-duration experiments are outside this delivery.

Repeat synthetic qualification and 20 warm measurements with
`python tools/studio_specimen.py --output NEW_DIRECTORY`. Repeat optional real
browser checks with `tools/studio_browser_probe.py --nest PRIVATE_DIRECTORY
--chromium BROWSER_EXE --output NEW_DIRECTORY --reviewed`. Playwright is a
separately provisioned developer tool. Add `--accept-demo` only for deliberate
synthetic calculator acceptance; it never accepts Studio itself.

For a warm attached host, use `tools/studio_host.py --nest DIRECTORY next` and
`tools/studio_host.py --nest DIRECTORY submit --request-id ID --proposal FILE`.
Submission reuses the authenticated loopback controller and its verified sessions,
avoiding a fresh Journal open for every CLI invocation. There is no provider API
or automatic fallback. The direct `studio mind-submit` CLI remains available
when a host deliberately uses its own foreground session.
