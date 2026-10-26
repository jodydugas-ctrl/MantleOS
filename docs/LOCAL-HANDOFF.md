## Current repository and release

The maintained repository is https://github.com/jodydugas-ctrl/MantleOS. It has
ordinary Git history and an explicitly pinned KPP selection, checked by hosted
CI. For the current release, exact-commit evidence, installed-wheel verification
and beginner workflow, read [RELEASE-HANDOFF.md](RELEASE-HANDOFF.md). Preserve
existing local edits and use a clean checkout for new work.

## Optional offline container

The remaining instructions describe the disposable snapshot produced by
`tools/project_container.py package`, not the maintained GitHub repository.
In that container, `MantleOS/` has one initial commit on `main` and no remote;
`MantleOS.bundle` holds that same snapshot. There is no Docker environment.
Keep the existing license terms and notices.

Use the included repository directly, or recreate it offline in a new directory:

```console
git init -b main MantleOS-restored
git -C MantleOS-restored bundle unbundle ../MantleOS.bundle
# Use the initial commit printed at the top of HANDOFF.md:
git -C MantleOS-restored reset --hard COMMIT_FROM_HANDOFF
git -C MantleOS-restored fsck --full --strict
git -C MantleOS-restored status --short
git -C MantleOS-restored remote -v
```

Local object import and checkout recreate the bundle without configuring a remote
or contacting GitHub. Replace COMMIT_FROM_HANDOFF with the recorded commit. Match `git rev-parse HEAD` to the handoff
commit. `CHECKSUMS.json` lists SHA-256 for every delivered file except itself,
including the repository metadata, source, bundle and these instructions. The ZIP
has a separate `.sha256` file. These checks detect corruption, not authorship.

From the source root, Python 3.11 through 3.14 works without runtime dependencies:

```powershell
$env:PYTHONPATH = 'src'
python -m mantleos --help
python -m mantleos kpp doctor
python tools/kpp_upstream.py check
python tools/project_container.py check
python -m unittest discover -s tests -v
python -m mantleos demo --output .work/new-demo
```

See CONTRIBUTING.md for all walkthroughs and distribution verification. To install
offline, first supply the pinned build requirements locally, then use
`python -m pip install --no-index --no-build-isolation --no-deps .`.
Runtime demonstrations use synthetic data; new output directories avoid replacing
local organisms. The Save-organ browser probe requires locally installed Node,
Playwright and Chromium and explicit review to execute preview JavaScript:

```console
python src/mantleos/kpp/resources/tools/check_organ_save.py --output .work/new-save-demo --execute --reviewed
```

It checks actual download bytes and reviewed replacement/restoration. The
workspace stays BUILDING with acceptance NOT_GRANTED. Browser download initiation
does not prove a disk write; runtime capability declarations are not a sandbox.

## Rebuild the local container

`PROJECT-FILES.json` is the explicit, hash-pinned source inventory. Exports refuse
missing, modified or newly added distributable files until reviewed. The allowlist
excludes private Engrams, credentials, carriers, working state, old kits, existing
archives, caches and previous Git metadata. Keep private material outside approved
source trees; the inventory is not an arbitrary secret-content detector.

```console
python tools/project_container.py check
# Only after reviewing intentional source changes:
python tools/project_container.py refresh
python tools/project_container.py export --output .work/new-source-export
python tools/project_container.py package --output dist/new-handoff --zip dist/new-handoff.zip
python tools/project_container.py verify-container dist/new-handoff
```

The package command creates a fresh sanitized history, neutral local snapshot
author, exact byte attributes and a bundle. It does not preserve old Git objects,
hooks or user configuration. `* -text` prevents checkout newline conversion from
breaking KPP pins. The archive index describes old systems; no snapshots are
included. Historical verification receipts remain labeled historical; current
handoff execution is recorded separately in docs/local-handoff-verification.json.
Future hosted CI is supplied as configuration and has not been executed here.

## Later GitHub upload, performed separately by the owner

These are instructions only; no online repository was created or contacted for
this handoff. When ready, review licenses/privacy, create an empty GitHub repository
under the chosen account, then replace the placeholder below with its actual URL:

```console
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

MantleOS is the product repository. Keep official KPP independent and use the
offline review workflow in docs/KPP-UPSTREAM.md to promote its shared changes.

## Revised experimental testbed

This revision includes recipe/4 language choices and optional Anchor binding,
while recipe/3 keeps its existing behavior. New results are in
`docs/recipe-v4-verification.json`; the original handoff receipts are historical.

Current r3 execution results are in docs/log-adoption-verification.json; prior
recipe/4 and handoff receipts remain historical. Future hosted CI is unexecuted.

## Consolidated GitHub project

See `docs/CONSOLIDATION.md` for the r3 baseline, full historical repository handoffs, runtime-only distribution scope, exact KPP pin and publication/deletion gates. The original handoff commands and unexecuted-hosted-CI statements above describe the imported container. They are historical following owner-approved publication on 2026-10-23. The new repository retains reviewed initial commit `50c7c1544eacf2cc57bc51b1f9195860e324113e`; current hosted evidence is available in [GitHub Actions](https://github.com/jodydugas-ctrl/MantleOS/actions). Fresh remote clones restored all four public bundles and verified every archived source blob and retained ref.
