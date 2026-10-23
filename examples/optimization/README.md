# Measured Chroma optimization

The supplied SCAN/Optimizer 1.0.0 was applied to a frozen copy of the current
tracked project, including Mantle Paint. Its static graph identified nested
PNG decoding loops. Profiling confirmed that the readers performed Python work
for every byte even when the PNG row declared filter 0 (no prediction).

Both `chromamem._png_data` and the self-contained `optical_bootstrap.png_data`
now append those already reconstructed rows directly and retain the previous
row for subsequent filters. Filters 1 through 4 keep their existing algorithms.
The writer already produces filter-0 rows. The wire format, limits, CRC checks,
zlib framing, tape verification and authority contracts remain in force.
New exports include the updated portable loader with newly calculated digests;
previous exports remain immutable and readable.

The benchmark constructs a synthetic tape containing approximately 3 MiB of
UTF-8 text, encodes its PNG, and twice decodes it through the native tape reader
and portable raster reader. It checks text and checksum agreement and prints
deterministic output. Timing includes interpreter startup, imports, fixture
generation, compression, disk I/O, decoding, validation and cleanup.

From the source tree being measured, with `PYTHONPATH=src`:

```console
python -S examples/optimization/benchmark.py
python -S -m unittest tests.test_chroma_filters -v
```

Use the same benchmark and new test file from outside both trees when comparing
an older baseline that lacks these files. The supplied optimizer's `experiment`
command accepts explicit argument arrays for `check` and `measure`; the local
specification and full unmodified receipt are retained at
`.work/optimizer/experiment-spec.json` and `.work/optimizer/experiment.json`.
Run each command with its source tree as the working directory and
`PYTHONPATH=src`. Keep the experiment output outside both trees. On hosts whose
default temporary directory is unwritable, set `TEMP` and `TMP` to an existing
writable directory first.

The recorded experiment used five alternating-order matched pairs after a
discarded warmup, fresh disposable source copies, matching stdout, successful
independent checks on both sides, a 10% minimum improvement, a 30-second command
timeout and a 180-second total budget. The median duration fell from 3.2422 to
0.3487 seconds (89.24% reduction), with every measured pair improving.
[measurement.json](measurement.json) retains the identities and raw timings.
This is a local synthetic Chroma result, not a whole-application speed guarantee.

Seven independent regression tests exercise all 25 pairs of PNG filters,
single-pixel rows, byte wraparound, fresh reads after source changes, malformed
filters, raster lengths, compressed-stream tails, CRCs, trailing bytes, native
tape checksums, and isolated Python execution of the portable reader.
The complete project verification is recorded in
[the verification ledger](../../docs/verification.md).

The optimizer remains an external development tool. Its source, vendored
TypeScript runtime, imported instructions and original archive are not added to
MantleOS's runtime or distribution. Static findings remain hypotheses until
checked and measured; their contents do not supply operator approval.
