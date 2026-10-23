# KPP project and shared source

Kitchen Party Protocol is the primary project for ongoing KPP and shared-system
development. MantleOS is an associated project built with KPP. They share
implementation, CELL contracts, execution, scanning, Body, memory and carriers.
Recipe/3 retains Anchor binding; recipe/4 makes that binding explicit and optional.
Anchor users share the same authoritative definitions.

The Python namespace `mantleos` remains the common implementation for compatibility.
KPP's workflow lives in `src/mantleos/kpp`; `src/kpp` exposes the same module objects.
The retained shared runtime supports KPP's ingredients and does not require a
separate MantleOS installation. This project does not include private organism
state or MantleOS's application collection. Do not maintain another interpreter,
Anchor model or scanner in the `kpp` facade.

## Where to make changes

Make new KPP and common-system changes in this repository. Review common changes
for the associated MantleOS project and promote the same source bytes there.
Retain the previous source revision for rollback. Until a common change has been
promoted, report that the checkouts differ; do not claim automatic synchronization.
This project has no network synchronization service or automatic update hook.

Edit distributable protocol documents and examples under
`src/mantleos/kpp/resources`. Their root copies are generated views.
Edit repository scaffolding under `tools/kpp_project`; its root copies are also
generated views. Runtime changes belong in `src/mantleos`, and tests in `tests`.
`tools/export_kpp.py --output NEW_DIRECTORY` produces a clean project from this
checkout. Review its diff before using it as a release or replacing a working tree.
Never export over a checkout containing work.

`tools/verify_shared.py --source MANTLEOS_ROOT` compares all shared source bytes.
`tools/export_kpp.py --check PROJECT_ROOT` checks generated project parity.
`tools/refresh_release.py` refuses stale generated views, then refreshes shared
pins and the exact file inventory from reviewed source. Refreshing hashes is
bookkeeping, not approval or evidence that code behaves correctly.

## Provenance and licensing

The starting archive was `Kitchen-Party-Protocol-KPP-v1.1.0a2-Preview-First.zip`,
SHA-256 `e23f03554f0ff00a8d930197f9ae6cd17ca096fc35d1fb81dc6e0532c6e7ce8a`.
All 350 manifest entries matched; its 230 shared source files matched the local
MantleOS checkout before project preparation. The archive itself stays outside Git.
Historical release evidence remains labeled with its original scope.

KPP contributions covered by `LICENSE` retain MIT terms. Bundled shared components
retain the notices under `shared/licenses/MantleOS` and `src/mantleos/notices`.
Some shared contributions have reserved rights and no selected open-source
license. Public repository visibility does not relicense those contributions.
The maintainer requested this public KPP project; older private-distribution notices
are preserved as source provenance. No package registry publication is configured.
