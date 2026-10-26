# Contributing

Current release scope, installed-wheel verification and commit-bound evidence:
[docs/RELEASE-HANDOFF.md](docs/RELEASE-HANDOFF.md). Earlier dated verification
records retain their original scope.

Work locally on a focused branch. Keep the deterministic Body useful without a
MIND. Reuse an existing capability or codec before adding a new mechanism.

Set `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH = "src"`) and run:

```console
python -m unittest discover -s tests -v
python -m mantleos demo --output .work/review-demo
python -m mantleos examples demo --output .work/review-examples
python examples/thoughts/walkthrough.py --output .work/review-thoughts
python examples/kpp/walkthrough.py --output .work/review-kpp
python examples/discovery/walkthrough.py --output .work/review-discovery
python -m build --no-isolation
```

Build tools are pinned in `requirements-dev.txt`. Runtime and tests use the
standard library. Use a fresh demo directory. Tests use synthetic fixtures in
temporary directories and make no network or model calls. Size optimization
must preserve supported skills and generated self-contained artifacts; there
is no arbitrary ZIP size ceiling. Remove obsolete adapters and duplication first.

For host connection changes, also run the separately provisioned Hermes native
parity selection and actual connection tests in [the example guide](docs/examples.md).
Do not substitute synthetic-host fixtures for that evidence.

Every integration should name its inherited source, observable contract,
focused verification, and remaining limits. Update the capability ledger when
those facts change. A historical receipt describes its original artifact only.

Do not edit pinned Anchor semantics casually. A justified implementation change
requires a reviewed source-pin update and regression tests. Keep generated
packages and private organism state out of commits. Review `git diff --cached`
before committing; use small checkpoints. Remote setup and publication are
separate owner actions.

When the owner later creates a private GitHub repository, review its available
secret scanning, push protection, dependency alerts, and branch protections;
these are hosting settings and have not been enabled locally. Repository layout
and contribution guidance follow [GitHub's repository recommendations](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories).
Large carriers remain external rather than becoming Git history.

Anchor singularities are source constants. Change attributes rather than creating
a new meaning for an existing Anchor. Recipe/3 and explicitly bound recipe/4 obligations use the same model; unbound recipe/4 obligations are generic requirements.
CELL means the smallest unit produced by its declared kernel.

The Paint example has optional Node-based raster tests and a visible browser
fixture; see [its guide](examples/paint/README.md). Python core verification does
not require Node. Changes to Paint must retain its UTF-8 Anchor/receiver round
trip and keep tested browser behavior separate from native XP parity.

Recipe/4 implementation choices and optional Anchor binding are documented in
`docs/LANGUAGE-CHOICES.md`. Run `python tools/kpp_upstream.py check` and
`python tools/project_container.py check` before release. Current revision
results for that earlier revision remain in `docs/log-adoption-verification.json`.
Use the release handoff and the workflow run for the exact current commit for
subsequent results; hosted CI has now been exercised.
