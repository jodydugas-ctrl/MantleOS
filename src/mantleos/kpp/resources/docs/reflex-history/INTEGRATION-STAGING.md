# Using the isolated patch with the MantleOS repository

This package is a **repository overlay**; extract at the existing MantleOS repository root. It adds only these paths:

- `experiments/reflex_book/`
- `examples/reflex_book/`
- `tests/reflex_book/`
- `docs/reflex/`

Or from the MantleOS repository root use the companion patch:

```bash
git switch -c experiment/reflex-0.1-m0-review
git apply --check /path/to/REFLEX_0_1_M0_review.patch
git apply /path/to/REFLEX_0_1_M0_review.patch
python -m unittest discover -s tests -v
python -m experiments.reflex_book.tools.record_test_receipt
# Run the existing repository's documented full regression commands separately.
git status --short
```

`git apply` **does not commit or install** anything; it stages additions to your working tree, for a reviewer to inspect. No code in this package changes MantleOS runtime behavior automatically. Only the project maintainer may decide to commit, open a draft PR, request review or merge. `M0-REVIEW.md` lists unresolved architecture decisions.

## M3 overlay note (24 October 2026)

The isolated admission APIs implement a **local SQLite simulation**, not a
MantleOS `tissue.py`/`evolution.py` update. Treat `registry.py` as design and
test evidence only. Maintainer and Baker decisions and new-construction review
must precede any integration into canonical Engram and transaction paths.
