# REFLEX toolkit release and continuation

KPP maintains the shared `mantleos` source. MantleOS receives an explicitly
reviewed clean KPP commit through its offline promotion workflow. Use a clean
checkout for development; preserve earlier workspaces and their private patches
before reconciling them. Never reset a workspace merely because its branch is old.

## Current release scope

KPP 1.1.0a5 and MantleOS 0.1.0a9 include the experimental REFLEX reference
toolkit, inactive Body attachments and the evaluation inspector. One synthetic
observation produces NORMAL at age 30 seconds and UNKNOWN at age 630 seconds
under a 180-second freshness limit. Program and observation values stay equal.
Only the supplied rule clock changes. See [REFLEX-BOOK.md](REFLEX-BOOK.md).

Inspection checks carried data without evaluation. Reproduction explicitly runs
the bounded reference evaluator. Neither grants operator authority, historical
authorship, formal language qualification or Baker acceptance. Native REFLEX Body
execution, production approval and wider native-reference qualification remain
future milestones. Optional browser/provider/cloud checks not executed for this
packaging change remain untested for this change.

The previously published baseline is KPP `5a48c0686c7aefbf077329e09d9e95fd4699d760`
and MantleOS `52db130c8b78042dbaf43cd6a3d9ef91f63b5301`: 424 matching shared
files, 368 KPP tests and 490 MantleOS tests. Observed hosted results are
[KPP's eight jobs](https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol/actions/runs/40339391887)
and [MantleOS's four jobs](https://github.com/jodydugas-ctrl/MantleOS/actions/runs/40343545891).
These are baseline observations, not test receipts for later commits. Current
commit-bound outcomes belong in the release's `EVIDENCE.json` and GitHub Actions
for the exact commit. Keep previous dated evidence unchanged.

## Beginner workflow from a release directory

The local review release includes a source ZIP, wheel, source distribution,
`CHECKSUMS.json`, standalone `VERIFY.py`, `EVIDENCE.json` and synthetic evidence.
It contains no private preservation snapshots or working Bodies. A complete
MantleOS source ZIP retains its already reviewed historical archive tree; its
wheel and source distribution exclude historical implementations.

First run `python VERIFY.py` beside `CHECKSUMS.json`. Compare the externally
supplied checksum of that manifest as well; a self-consistent altered manifest
is not authentication. Extract the source ZIP into a new directory if desired.
Python 3.11 through 3.14 is required. Create a new environment outside the source:

```console
python -m venv beginner-env
```

Use `beginner-env/Scripts/python.exe` on Windows or `beginner-env/bin/python`
on Linux in place of `PYTHON` below. Replace `WHEEL` with the included `.whl` path.
No network or runtime dependencies are required for installation:

```console
PYTHON -I -m pip install --no-index --no-deps WHEEL
PYTHON -I -m mantleos reflex-book demo --output new-reflex-demo
PYTHON -I -m mantleos reflex-book inspect new-reflex-demo/fresh.json --format text
PYTHON -I -m mantleos reflex-book compare new-reflex-demo/fresh.json new-reflex-demo/stale.json --format json
PYTHON -I -m mantleos reflex-book reproduce new-reflex-demo/fresh.json
PYTHON -I -m mantleos reflex-book reproduce new-reflex-demo/stale.json
```

Choose a new output directory each time. `REPRODUCED` confirms deterministic
agreement with the recorded claim. Retain both records and the comparison for
review. The specification and synthetic vectors are installed package resources.
The earlier `experiments.reflex_book` imports migrate to `mantleos.reflex_book`;
legacy `mantleos.reflex` imports and `python -m kpp reflex-book` remain delegates
to that same maintained implementation.

## Repeat the installed-wheel check

Build tools are development dependencies, separately provisioned and pinned in
the project. Run the documented complete verification, then build distributions:

```console
python -m build --no-isolation
python tools/check_reflex_install.py --wheel WHEEL --output NEW_EXTERNAL_DIRECTORY
```

Select exactly one built wheel. The check refuses an existing output directory
or a directory inside its source checkout. It creates an isolated environment,
installs that wheel with network disabled, verifies import location and packaged
resources, and exercises demo, evaluate, text/JSON inspect/compare and reproduce.
KPP additionally checks its doctor and compatibility CLI. Logs, synthetic records,
wheel digest, interpreter/platform and `report.json` remain in the external
directory. A failed check leaves diagnostic evidence and a FAIL report.

Minimal Python installations without `ensurepip` can supply a separately reviewed
offline pip wheel using `--pip-wheel FILE --pip-sha256 EXPECTED_DIGEST`. It seeds
only the new disposable environment after checking that independent digest and
member paths; it does not change the system Python or contact a package index.

Both hosted workflows run this check after building, on their declared matrices,
and retain the evidence. Configuration alone does not establish a successful run.
macOS, other Python versions, live models/providers and native application parity
remain untested unless separately recorded. Passing does not grant acceptance.

## Continue development

Read `AGENTS.md` and `CONTRIBUTING.md`. Edit shared source in KPP first. Protocol
documents and tools under `src/mantleos/kpp/resources` generate root views;
`tools/kpp_project` generates project scaffolding. Export to a new directory,
review the changes, refresh inventories and commit the clean KPP selection.
Promote it using MantleOS's `tools/kpp_upstream.py plan/apply --reviewed` workflow,
then verify the exact commit pin, shared bytes and standalone export. Do not
reapply an older local snapshot over these reviewed changes.

Release packages identify their exact source commits and artifact hashes in
`EVIDENCE.json` and `CHECKSUMS.json`. Local packaging does not publish to a package
registry, create a tag or issue formal product acceptance.
