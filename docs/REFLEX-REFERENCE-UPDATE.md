# REFLEX reference toolkit repository update

This records the earlier reference-inspector integration snapshot. For the
current release, read [RELEASE-HANDOFF.md](RELEASE-HANDOFF.md); the current KPP
selection is recorded in `upstream/kpp.lock.json`. The commit below retains its
historical scope.

The bundled toolkit and evaluation inspector are integrated with the current
published KPP source. The clean reviewed KPP commit is `5a48c0686c7aefbf077329e09d9e95fd4699d760`.
MantleOS carries the same source through the documented offline promotion workflow.

The integration preserves published Engram construction/carriers, reviewed
synthetic samples, Pantry repository locators, historical receipts and the explicit
REFLEX approval field validation. `mantleos.reflex` imports alias the maintained
`mantleos.reflex_book` modules; old `kpp reflex-book` and native carrier commands
remain supported. There is one evaluator, one compiler and one approval validator.

Run `python -m mantleos reflex-book demo --output .work/new-reflex-demo` and follow
[REFLEX-BOOK.md](REFLEX-BOOK.md) for inspect, compare and explicit reproduce.
The same synthetic observation is NORMAL at 30 seconds and UNKNOWN at 630 seconds
under its 180-second freshness guard. Inspection performs no evaluation or admission.
Reproduction compares deterministic traces and cannot prove historical execution,
authorship or approval. Native Body execution and formal qualification remain deferred.

The earlier local review archive describes its own tested source snapshot. This
repository integration adds compatibility with the already merged work and preserves
the published approval-validation fix. Its final source and CI checks are recorded
in Git history and the GitHub workflow runs; historical receipts are not current
certification. No private Body, credential or imported source archive is added.

Existing working checkouts were preserved; integration was prepared in isolated
checkouts from each repository's current main branch. Only reviewed source and
its generated inventories are part of the update.
