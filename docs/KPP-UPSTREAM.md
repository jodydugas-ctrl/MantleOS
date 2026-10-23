# Official KPP alignment

MantleOS is the primary product repository. The official Kitchen Party Protocol
project remains independently maintained at the URL recorded in
`upstream/kpp.lock.json`. This repository embeds one pinned selection from it.
There is one common `mantleos` runtime, Anchor model and interpreter. No updater
fetches, pulls, configures remotes or runs on a schedule.

The first selection is the reviewed local working snapshot based on commit
`6f4919cafb96e8f415434036a04762de69a6f5b8`, including uncommitted Save-organ,
scanner and reviewed module replacement integration. The local base commit is
provenance, not a claim that the selected bytes were published. Hashes establish
integrity, not authorship, trust or approval. Upstream notices are retained under
`upstream/kpp-notices/`; existing component notices and license terms still apply.

The lock assigns every selected file a source path, SHA-256 and ownership group:
the complete `src/mantleos/` shared implementation, upstream tests under
`tests/kpp/`, the `docs/kpp.md` view of canonical `SYSTEMS.md`, and upstream notices.
Product tools, the remaining tests and product documentation belong to MantleOS.
Shared changes must originate in KPP and arrive here with identical bytes. Review
new ownership additions and deletions as well as code changes.

From a locally supplied KPP checkout or a complete standalone source export:

```powershell
python tools/kpp_upstream.py check
python tools/kpp_upstream.py plan --source C:/local/KPP --output .work/kpp-proposal
# Read .work/kpp-proposal/REVIEW.md, plan.json and the exact payload/diffs.
python tools/kpp_upstream.py apply --source C:/local/KPP --plan .work/kpp-proposal --reviewed
python tools/kpp_upstream.py check
python tools/project_container.py check
```

Use new proposal directories. Supply the same current source for application;
`SHARED-SOURCE.json`, the full source tree, tests and notices are required. The
planner only reads data and Git metadata. It pins the candidate, upstream dirty
status, destination inventory and old lock. It does not execute candidate code.
Application rechecks these pins and refuses local edits or file ownership
conflicts. `--reviewed` explicitly authorizes running that candidate's Python
tests with the local user's privileges; it is not a security sandbox or Baker
acceptance. The CLI runs the complete combined unit suite and KPP doctor in a
separate candidate directory before publishing. Missing or failed validation
leaves current tracked source unchanged. Test callbacks in the unit tests are
synthetic fault probes, not qualification of an actual upstream update.

Only KPP-owned source, its generated view, lock, append-only update receipts and
the project inventory are published. Test-time modifications to the staged source
are refused. Source and destination are rechecked after validation. Atomic file
replacement, an exclusive writer lock, before/after backups and a pending journal
protect interrupted application. Publication spans multiple files: avoid using
the build while an update is pending. This is local recovery, not a distributed
transaction or protection against unrelated programs ignoring the writer lock.

```powershell
# After an interrupted update, inspect .work/kpp-updates, then:
python tools/kpp_upstream.py recover --reviewed
# Restore the last successfully applied update, retaining audit history:
python tools/kpp_upstream.py restore --reviewed
```

Recovery verifies retained source and current affected files before restoring.
It refuses conflicting external edits and tampered backups. Keep `.work/kpp-updates/`
until recovery or restoration is no longer required; it is local state excluded
from Git and handoff exports. Provenance events remain in `upstream/history/`.
No approvals or working organism state are imported or transferred. Source
updates require new runtime evidence and separate explicit Baker acceptance.

After a successful update, inspect the diff and receipts and create an ordinary
local commit if desired. `check` verifies embedded files against the lock offline;
it cannot discover online releases. The future hosted CI invokes alignment and
inventory checks; it contains no scheduled updater.

## Recipe/4 local revision

The updated local working snapshot includes explicit language choices and optional
Anchor binding. Its local base is provenance, not a published upstream claim.
Reviewed KPP scaffolding is promoted alongside shared source; runtime ownership
remains the explicit file map in the lock. The prior handoff remains available.

The r3 input is the reviewed local working snapshot with optional construction
techniques and augmentation tests. It is not a published upstream revision.

## Consolidated repository pin

The selected clean KPP review commit is recorded in the upstream lock. Publication status remains explicit; a local commit is not a published revision. CI compares shared bytes with a checkout of the declared commit using `tools/verify_kpp_pin.py`. Future shared changes still originate in KPP and require reviewed promotion.
