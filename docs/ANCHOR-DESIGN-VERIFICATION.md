# Anchor design qualification — 2 November 2026

Compact contracts use the existing canonical Anchor applications. Four responsibilities
describe Journal; no fixed count or new executable profile is imposed. The complete
Notepad behavior checklist is retained as a design example; XP parity is untested.

Windows CPython 3.14 synthetic before/after measurements used identical histories,
20 warm samples per case and 0 or 20 MiB content-addressed cold data. No model was
invoked. Baseline is the reviewed Journal implementation before design integration;
bootstrap metadata discovery reused the current helper. Concurrent verification load
and sequential case order limit small timing comparisons. Cold objects are synthetic
retained objects, not a claim of attachment UI qualification.

| Records | Cold MiB | Before median / p95 ms | Design median / p95 ms |
| --- | --- | --- | --- |
| 0 | 0 | 14.73 / 16.86 | 12.81 / 16.56 |
| 100 | 0 | 16.23 / 17.59 | 15.88 / 25.49 |
| 1000 | 0 | 15.03 / 16.92 | 16.11 / 17.09 |
| 0 | 20 | 17.11 / 18.34 | 16.78 / 19.49 |
| 100 | 20 | 16.34 / 17.80 | 15.72 / 19.29 |
| 1000 | 20 | 17.48 / 20.26 | 21.31 / 23.23 |

The design adds approximately 1.5 KiB to the frame and retains one proposal for an
ordinary reply. This change claims better responsibility guidance and verifiable
bindings; the timings do not establish faster model generation. Raw results retain
startup, commit, frame and export measurements. Repeat with
`python tools/benchmark_anchor_design.py --baseline-journal REVIEWED_PRIOR_JOURNAL.py --output NEW.json`.
That explicit baseline is executable Python, not an untrusted document to auto-run.

Both release-candidate full suites initially completed with one shared catalog metadata
failure (new ingredient absent from the expected stable-ID set). The ingredient and
assertion were updated together. Final KPP full rerun passed 400 tests with five
privilege-related skips; nine focused design tests also passed. MantleOS final
outcomes are recorded in the delivery report and commit-bound GitHub Actions. Original-checkout
suites passed 371 and 483 tests with five symlink-privilege skips each. These counts
are distinct from the newer remote-baseline candidates and their additional tests.

Journal regressions cover full PRIMER, custom founding setup, checked observations,
authority denial, replay, recall, interruptions, file-only bootstrap and carrier round
trips. New tests cover singularity tampering, ownership, guards, recipe coverage,
stale design preparations, exact replay and legacy explicit export upgrade. Transport
tests execute in isolated fresh Python receivers where specified by the upload suite.
Synthetic tests confer no Baker acceptance. Independent LLM providers, real browser
upload UI, XP appearance/behavior and other local Python/platform combinations remain
untested for this change. Historical Journal measurements retain their original scope.

Current-host observation: this chat LLM read a complete Synthetic Finch PRIMER and
the design frame, supplied an ordinary semantic reply, then requested body.status.
The action reached VERIFIED; its exact observation digest bound the committed reply.
Replay returned the same text. A saved-file-only bootstrap ran in fresh isolated
Python and projected both earlier turns; this LLM supplied the correct Spruce/Alder
recall reply and the carried runtime committed it. Model labels are host declarations,
not authenticated provider receipts. This is one chat context, not an independent
provider comparison or browser-upload UI experiment. Full packets remain private.

A real KPP workspace using journal-engram-design remained BUILDING with zero accepted
obligations; build-step projected the founding responsibilities and handoff retained
the design. Doctor, smoke, source parity, release inventory, fresh standalone export,
all five documented walkthroughs, offline builds and isolated installed CLI checks
passed. The first installed-environment and one carried-CLI attempt hit Windows TEMP
permissions; setting TEMP/TMP to the writable workspace allowed them to complete.
