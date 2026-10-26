# M3 reproducible offline review commands

From the root of this overlay in an isolated Python 3.11+ environment:

```bash
python -m unittest discover -s tests -v
python -m experiments.reflex_book.tools.demo_m3
python -m experiments.reflex_book.cli verify examples/reflex_book/m3_location_candidate.rfx
python -m experiments.reflex_book.cli candidate \
  examples/reflex_book/m3_location_candidate.rfx \
  --evidence docs/reflex/TEST-RECEIPT.json \
  --baselines examples/reflex_book/m3_baseline_versions.json \
  --proposed-by synthetic_model \
  --evidence-ref synthetic:m0-test-receipt \
  --output .work/m3_candidate.json
```

The candidate command *only* constructs a digest-bound manifest and always reports `authorized=false` and `installed=false`. The demonstration `demo_m3` uses an intentionally published dummy key, a temporary SQLite file, and synthetic observations. It shows installation/activation/one execution/disable **inside the test registry only**, then deletes the temporary registry. Its output carries `production_body_authorized=false`.

No CLI subcommand mints trusted operator approvals or performs real BODY installation. In a future implementation, trusted issuer keys must be provisioned exclusively through a separately reviewed host mechanism and must never be embedded in REFLEX rules or media carriers.
