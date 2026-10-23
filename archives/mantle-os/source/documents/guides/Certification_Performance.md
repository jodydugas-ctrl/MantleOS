# Certification performance measurements

Mantle's certification benchmark measures cost; it does not certify an organism and it cannot
grant authority. Every record is labeled `NON-AUTHORITATIVE PERFORMANCE EVIDENCE`.

Run a quick invariant measurement from a clean checkout:

```bash
python tools/benchmark_certification.py --suite invariants --repeat 5 --warmup 1 --require-clean
```

Measure the Grimoire bundle and its named invariant wrappers:

```bash
python tools/benchmark_certification.py --suite grimoire --repeat 9 --warmup 1
```

Measure the complete strict command when enough time is available:

```bash
python tools/benchmark_certification.py --suite strict --repeat 3 --warmup 1 --timeout 1200
```

Results append to `.artifacts/efficiency/benchmarks.jsonl` by default. Each record includes the
commit, tracked-tree digest, dirty status, interpreter, platform, raw samples, median, median
absolute deviation, minimum, and maximum. Use `--output` to select another local artifact path.

The tool is serial, read-only except for its result file, standard-library-only, and
non-networked. A timeout or unexpected command result is recorded as a failure. Profiled times
are useful for attribution but must not be compared directly with unprofiled acceptance times.
Always finish optimization work with the governing command:

```bash
python -m mantle check --strict
```
