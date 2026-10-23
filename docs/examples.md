# Working organisms

These examples share one runtime but represent distinct kinds of software.
An **AppAI** integrates MantleOS into a host application as its autonomic nervous
system. Its **SELF** is the entire integrated application and its **NEST** is the
whole installation directory. The `mantle/` directory contains its internal
system files; it is not the boundary of SELF. Other Bio-Agents and Bio-Software
do not become AppAI merely by having memory or activation cycles.

An **Engram** is separately identified, portable software with founding material
and experience. A representative inherits its parent's exact PRIMER bytes by
default, receives separate mission context, and builds its own experience. NEST
residency is a preference, especially strong for AppAI, not a relocation ban.

## Offline collection

From the repository, set `$env:PYTHONPATH = "src"` in PowerShell or
`export PYTHONPATH=src` in a POSIX shell. Use new output directories.

```console
python -m mantleos examples list
python -m mantleos examples demo --output .work/example-walkthrough
```

This builds a synthetic Engram, starts with blank memory, conducts a clearly
labeled scripted encounter through the actual hosted bridge, restores its new
experience from cartridge and PNG, builds interactive Notepad, and runs Observer
twice against a synthetic specimen. No network, model, or credentials are used.
Hermes qualification is separate because it needs the upstream host and its
optional test dependencies.

## Raven: fresh founding persona, blank experience

```console
python -m mantleos examples build raven --source PATH_TO_TRUSTED_RAVEN.vcw --output .work/raven
python -m mantleos examples run raven --directory .work/raven --message "Hello" --request-id first-contact
```

Construction reads verified founding material only. It assigns a new identity,
creates an empty experiential ledger and cold archive, and produces equivalent
`engram.vcw` and `engram.png` snapshots. The original carrier remains unchanged.
Omit `--source` to use the distributable synthetic persona. Personal founding
material and all generated output must remain outside Git.

The run command prepares a host handoff; it does not secretly call a model or
grant access to the current chat. A trusted host consumes the frame and supplies
typed proposals through the existing `bridge-advance` and `bridge-commit`
commands (`python -m mantleos --body PATH bridge-open --help` describes that
protocol). Scripted fixture replies are used only by tests and walkthroughs.

Current Chroma Body packages are also accepted as founding sources:

```console
python -m mantleos examples build raven --source PATH_TO_CURRENT.png --output .work/raven-image-rebirth
```

Both current carriers verify the Body and founding locks before copying PRIMER.
Fresh birth keeps no prior experience. Older image package `/1` is deliberately
unsupported; preserve old carriers externally. Hashes establish consistency,
not publisher authentication. New standalone apps and portable executable
thoughts are covered in [the authoring guide](thoughts.md).

## Anchor Notepad: interactive Bio-Software

```console
python -m mantleos examples build notepad --source PATH_TO_NOTEPAD.anchor --output .work/notepad
python -m mantleos examples run notepad --directory .work/notepad --port 8769
```

Open the printed loopback URL. Edit text, find/replace, and use the supported
Notepad menus. Ctrl+C stops the foreground server. Omit `--source` to use the
packaged example. The server exposes only the verified browser artifact.

Import checks the structural envelope, length/hash-bound payloads, and supported
`NOTEPAD_LLM/1.3` semantics independently of advisory launch prose. It regenerates
the browser/bridge/Python targets using this runtime. Older compiled targets
are not silently executed. The generic exact-target Anchor qualifier remains
stricter than this explicit import-and-rebuild operation.

Notepad's editing state is virtual browser state. Its current browser adapter
does not claim durable host-file export; follow its displayed capability status.
Use the deterministic notebook Body commands for ledger-backed editing.

## Workspace Observer: bounded Bio-Agent

```console
python -m mantleos examples build observer --output .work/observer
python -m mantleos examples run observer --directory .work/observer --source examples/notebook --request-id observation-1
```

Observer hashes a stable snapshot, runs the packaged static scanner, reports
changed paths and improvement opportunities, and appends an observation to its
own Body. It never imports or executes specimen code. The output must be outside
the specimen. Limits are 256 files, 2 MB per file, 8 MB total; scanner exclusions
and evidence limits apply. Run again with a new request ID to compare snapshots.
These are static findings, not behavioral certification or permission to edit.

## Hermes: genuine resident AppAI

Provision once, explicitly (network needed unless `--source` names a local pinned
checkout):

```console
python -m mantleos examples build hermes --output .work/hermes
python -m mantleos appai verify --nest .work/hermes
python -m mantleos appai birth --nest .work/hermes
python -m mantleos appai activate --nest .work/hermes
python -m mantleos appai run --nest .work/hermes --ticks 3 --interval 1
python -m mantleos appai stasis --nest .work/hermes
```

The pin is `nousresearch/hermes-agent` at
`63279301bcbdc185c1b07b98a9312eb0c862f26d`, selected by inspected MantleOS2.
Construction uses `git init/fetch/checkout` without configuring a remote. It
preserves the upstream license and records eight connections in six host files,
original hashes, owned files, and a reversible `mantle/host.patch`.

`UNBORN -> STASIS -> ACTIVE -> STASIS` is explicit. Activation resumes the same
identity and experience. Foreground ticks are bounded; no OS service or automatic
scheduler is installed. Hermes' own dependencies and provider setup remain its
own installation concerns; its pinned Python range is **3.11–3.13**, while the
lightweight MantleOS core targets 3.11–3.14.

When running Hermes normally, prefix a turn with `@appai` to include its PRIMER
and resident context through the existing host MIND handoff. Ordinary Hermes
turns retain native authority. AppAI tool actions require explicitly named
`appai activate --allow-tool TOOL_NAME` grants and Hermes' native authorization.
Unavailable authority denies an addressed AppAI action. Inactive or unavailable
Mantle tissue leaves ordinary host behavior independent. No provider is added.

`appai reverse --nest PATH` verifies ownership/drift, restores original host
files, and moves the system directory into a retained sibling archive, including
private experience. It refuses to overwrite source drift. It does not erase
memory. Transporting the internal Body does not transport the entire AppAI SELF.

## Resident parent, traveling representative

The operator selects one specimen and authorizes a standing policy:

```powershell
$nest = '.work/hermes'
python -m mantleos appai activate --nest $nest
$policy = python -m mantleos mission authorize --nest $nest --source examples/notebook --representatives .work/representatives --duration 300 --ttl 3600 --approve | ConvertFrom-Json
$cycle = python -m mantleos appai run --nest $nest --policy $policy.id --request-id mission-1 | ConvertFrom-Json
python -m mantleos mission inspect --nest $nest $cycle.mission.id
$review = python -m mantleos mission review --nest $nest $cycle.mission.id | ConvertFrom-Json
# Inspect $review.report before this operator admission:
python -m mantleos mission admit --nest $nest $cycle.mission.id --approve $review.sha256
python -m mantleos mission revoke --nest $nest --policy $policy.id
python -m mantleos appai stasis --nest $nest
```

The foreground AppAI creates and runs the representative within that policy;
subsequent authorized dispatches need no new policy approval. `mission dispatch`
and `mission run` also expose separate phases for inspection and transport.
There is one active representative, no recursive delegation, and a bounded local
worker timeout. The parent lock is released while the worker runs, so host work,
heartbeats, and revocation remain possible. Only the scanner executes.

SQLite persists policy, request IDs, creation intent, progress, and returned
evidence. A restarted call with the same ID cannot silently dispatch twice.
`mission recover` marks uncertain work interrupted or reconciles a completed
local birth; it never guesses an external outcome or starts another worker.
Recovery works while the parent is in stasis: a still-valid READY mission or
RETURNED result keeps its status. Resumption is required before execution or
admission. Stasis does not extend either deadline. Expired or revoked work is
retired; a target/policy mismatch is reported without changing the mission.
After inspection, use a new ID for a deliberately new mission. Revocation and
expiry block dispatch and admission; revocation does not claim cancellation on
an external host. A returned result occupies the active slot until admitted,
revoked, or recovered after expiry.

The child's `MISSION.json` carries purpose/context separately from PRIMER and
declares that it carries no authority. No parent ledger, credentials, filesystem
grants, or policy database are inherited. Use the normal `--body PATH save` and
`restore` ports for cartridge/PNG transport; destination execution needs local
authority. The parent admits a reviewed digest and provenance record, not the
child's entire ledger, and returned findings cannot grant tools.

The reproducible, synthetic relationship walkthrough is:

```console
python examples/hermes/walkthrough.py --nest .work/hermes --output .work/hermes-mission-demo
```

It verifies parent operation while the child is away, explicit scripted operator
admission after stasis/recovery/resumption, and two experienced-child carrier
restorations. It revokes its policy
and leaves Hermes in stasis afterward. It is the bounded local mission cycle,
not MantleOS2's unfinished asynchronous pseudopod machinery or a distributed swarm.

## Optional host qualification

Create a Python 3.12 venv and install `examples/hermes/requirements.txt`. Set
`HERMES_PYTHON` to its absolute executable path. Keep a pristine pinned checkout
and an integrated checkout, then run:

```console
python examples/hermes/qualify.py PRISTINE INTEGRATED --output .work/hermes-parity
```

On Windows, pass `--bash "C:/Program Files/Git/bin/bash.exe"`. The script invokes
Hermes' canonical `scripts/run_tests.sh` with its clean credential environment
and per-file isolation. The 12-file selection follows the historical donor's
scope; current results are recorded separately.

To exercise all eight actual connection points, copy
`examples/hermes/test_connections.py` to the disposable integrated host's
`tests/test_mantle_connections.py`, then run its canonical runner on that file.
It uses upstream fake agents, real host functions, a synthetic birth, and stub
tool execution. It makes no model call. This qualification is separate from
lightweight core CI; see [verification](verification.md) for executed results.
