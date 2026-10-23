# Files.AppAI And Spore v2 Problem Log

This ledger records problems observed during the local Grimoire v0.9 carrier refactor
and Files.AppAI birth. All fixes are local; no online resource was changed.

| Problem | Cause | Fix | Prevention evidence |
| --- | --- | --- | --- |
| Files instincts initially could not hatch | Instinct code was assigned to `log-json` bands instead of `exec` bands | Moved `files_area` and `files_verify_command` to dedicated `exec` bands 676 and 677 | Germ proving cases pass 4/4 and 3/3 at every hatch |
| Physical Alpha conflicted with Grimoire force | SPORE-PNG v1 wrote Hamming SECDED masks into Alpha | Replaced v1 with framed Grimoire QUOTE statements; HEAD uses A=QUOTE, continuations use A=0, and G=0x7f carries parity | `test_v09_tables_and_quoted_byte_alpha_policy`; static legacy-ECC absence test |
| Grimoire tables drifted from the canonical file | Runtime names used older evidence/force vocabulary and zero-XOR substitution affected B/A | Aligned EVIDENCE and FORCE to v0.9; only zero R parity becomes `0xFE`; parity B/A remain raw XOR | `test_parity_substitutes_only_zero_r`; Grimoire invariant |
| Statement parity alone did not cover coordinated rewrites | A data byte and its parity pixel can be changed together | Manifest now carries SHA-256 over every raw payload RGBA lane plus frame index and byte length | Parity-preserving rewrite test must fail with `full-lane fingerprint mismatch` |
| Pillow conversion could accept a transformed image | The old read path used `convert("RGBA")` | Canonical reader now always uses the strict PNG parser and requires non-interlaced 8-bit RGBA; the embryo refuses non-RGBA input | `test_strict_parser_refuses_non_rgba_png` |
| Spore hatch saved incomplete birth evidence | `hatch_from_spore` saved before adding the source receipt and never wrote `hatch_report.json` or `face.png` | Added one `_persist_hatch` path used by germ and spore births, after all receipts are attached | Hatch test asserts report/portrait existence and reloads exactly one source receipt |
| Shared Grimoire import caused a circular import | The VCW atlas eagerly measured a half-initialized `spore` module | Delayed the shared profile import until spore constants are defined | Clean-process CLI create/read/verify and `mantle prove` import path |
| Oversized append raised instead of returning FULL | `_fits` built an over-capacity package before returning a Boolean | Added an early capacity check and contained package-build `ValueError` as `False` | Purity gate asserts FULL, unchanged memory, and no child spore |
| Legacy PNG fixtures no longer represented current law | Existing v1 binaries retained repair Alpha | Added scripts that delete and recreate every spore from germ/state inputs | `make_spores.py`, `make_example.py`, and `files_appai/build.py`; generated receipts report `spore-png-v2` |
| Initial long audit exceeded its execution window | The old stress loop repeatedly regenerated a 2000x2000 image more times than needed for the invariant | Kept the same round-trip/delta assertions with fewer redundant iterations and added early oversized-payload refusal | Purity gate passes all 53 rows; focused pytest covers corruption paths |

## Prevention Rules

1. Maintain germs and phenotype source, never a PNG carrier by hand.
2. Delete and regenerate generated spores after any carrier or embedded-tool change.
3. Treat PARITY as statement integrity and the package fingerprint as transport integrity;
   neither substitutes for the other.
4. Parse physical bytes as raw RGBA. Do not composite, premultiply, resample, color-manage,
   or infer byte order from the host.
5. Keep evidence and force labels unchanged from the canonical Grimoire table.
6. A certification claim requires carrier verification, hatch proving cases, Stage 1,
   persisted receipt checks, and the browser phenotype gate.
