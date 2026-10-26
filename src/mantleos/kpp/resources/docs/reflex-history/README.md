# REFLEX/0.1 experiment — review handoff

This is a **candidate M0 semantic freeze and hardened M1/M2 offline prototype**, not an approved MantleOS Book. The implementation is isolated in `experiments/reflex_book`; synthetic examples and tests live in their matching folders.

Read [`M0-REVIEW.md`](M0-REVIEW.md) for decisions and gates, and [`../../experiments/reflex_book/SPEC.md`](../../experiments/reflex_book/SPEC.md) for precise semantics. The independent reproducibility receipt is in `TEST-RECEIPT.json`. `PR-REVIEW-CHECKLIST.md` describes how to stage it in a dedicated GitHub branch without editing runtime or pinned KPP files.

From a checkout with this overlay present:

```bash
python -m unittest discover -s tests -v
python -m experiments.reflex_book.cli validate examples/reflex_book/location_rule.json
python -m experiments.reflex_book.cli compile examples/reflex_book/location_rule.json --output .work/location.rfx
python -m experiments.reflex_book.cli verify .work/location.rfx
python -m experiments.reflex_book.cli run .work/location.rfx --input examples/reflex_book/location_normal.json
python -m experiments.reflex_book.cli run .work/location.rfx --input examples/reflex_book/location_anomaly.json
python -m experiments.reflex_book.cli run .work/location.rfx --input examples/reflex_book/location_stale.json
python -m experiments.reflex_book.tools.record_test_receipt
```

All results are reports only; `REQUEST_REVIEW` is **not a host effect**. This uses no model, no network, no patient data or real sensors. This prototype does not install or authorize itself. `golden_hashes.json` pins the baseline canonical and binary bytes.

## M3 candidate admission review (24 October 2026)

See [M3-REVIEW.md](M3-REVIEW.md) and [M3-QUICKSTART.md](M3-QUICKSTART.md).
This new overlay adds `experiments/reflex_book/evidence.py`, a separate
operator HMAC receipt validator, and a transactional isolated SQLite registry.
The included `demo_m3.py` is explicitly synthetic, using a public dummy key.
Neither it nor `cli candidate` installs a REFLEX program into MantleOS.
**M3 acceptance/Baker approval has not occurred.**

## M4 experimental carrier transport (24 October 2026)

See [`M4-REVIEW.md`](M4-REVIEW.md) and [`TEST-RECEIPT-M4.json`](TEST-RECEIPT-M4.json).
`carrier-pack`, `carrier-verify` and `carrier-unpack` add strict raw and ZIP
REFLEX-only transports. Their success means **integrity-verified data only**, not
MantleOS Cartridge adoption, execution, authority or Baker approval. The M4
native-carrier approval gate is still open.
