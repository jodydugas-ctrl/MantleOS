# Anchor Journal Engram — qualification, 2 November 2026

The implementation and KPP ingredient are experimental. Raven's full founding PRIMER
is retained. Ordinary encounters use one host-supplied semantic packet; checked read
actions require an observed result before the reply. Python handles storage/transport,
with existing Anchor conversational messages, register and qualified program semantics.

## Local turn performance

Each case has 20 baseline samples and 20 final journal samples. Baseline uses the
existing two-stage hosted bridge and embedded archive path. The final candidate was
rechecked separately against that recorded baseline after compacting its frame.
These are scripted local measurements; model generation is excluded. Concurrent
verification creates disk contention, so absolute timings are environment-specific.

| Prior records | Cold data | Cartridge median | Journal median | Reduction |
| --- | --- | --- | --- | --- |
| 0 | 0 MiB | 6.581 s | 15.3 ms | 99.77% |
| 0 | 20 MiB | 6.840 s | 15.0 ms | 99.78% |
| 100 | 0 MiB | 6.459 s | 17.3 ms | 99.73% |
| 100 | 20 MiB | 7.561 s | 20.2 ms | 99.73% |
| 1000 | 0 MiB | 10.175 s | 33.3 ms | 99.67% |
| 1000 | 20 MiB | 10.349 s | 30.4 ms | 99.71% |

Cold opening still verifies executable snapshot, founding material and history; it
is slower than a warm turn. Use the foreground stdio session to retain verified data.
The original benchmark JSON records cold startup, commit, frame sizes, p95, samples,
and export costs. SQLite's internal I/O byte count was not instrumented; reported
frame bytes are language-context bytes, not a claim about total filesystem traffic.

## Actual host bridge qualification

This chat assistant supplied semantic packets to isolated copies of both original
Raven bridges and the new journal. Checked commits, exact replay, a name correction,
later recall, authority refusal and VERIFIED body.status were exercised. The new
journal retained full PRIMER and used one packet for ordinary replies. Model labels
are host-declared attribution. No external model API was configured or called by the
bridges. Private reasoning and unique persona fidelity are not certified by these tests.
Model-generation and host-scheduling latency could not be independently measured
in this chat; the measurements establish local overhead reduction and fewer required
language stages, not a quantified end-to-end model-speed improvement.

The original single cartridge committed locally but its Windows vault hook returned
Bad file descriptor and left a lock file blocking its next verification. The lock
was removed only in the isolated test copy to continue. Its legacy SAVE also failed
with WinError 5 in this sandbox. Those failures are retained as failures. The original
PNG's own save codec rebuilt 23 tape records with a new active manifest. Originals
remain unchanged. Existing legacy /1 readers were not reintroduced into the public API.

## Compatibility and verification

Journal save/reopen, native lifecycle save/restore, current cartridge/PNG export and
round trips passed. Both old carrier exports recovered an exact 20 MiB cold object.
The fresh Raven artifact has blank experience; qualification conversations are separate.
KPP's ingredient, recipe/4 contract, runnable synthetic specimen and existing-profile
Anchor teaching ingredient remain separate from manual Baker acceptance.

The full MantleOS run exercised 468 tests: 461 passed, 6 skipped and one localhost
preview test failed inside the restricted network sandbox. Its complete 11-test
module passed on the native host (10 passed, 1 skipped). KPP's first full run found
a duplicate specimen catalog count, corrected by exposing the journal's actual
bundled-module source and independent runnable example. The clean KPP run passed 357 tests (352 passed, 5 skipped); all 14 final
journal-focused tests passed. Fresh standalone export, byte-identical shared source,
release inventory, doctor, smoke and the documented offline walkthroughs passed. Symlink/platform skips and untested models remain explicit.

Other models, other operating systems and direct-API timing are untested. Host
permissions govern effects and publication. No service, cloud sync or remote
publication was configured. Evidence supplies no automatic Baker acceptance.

A final single matched checked-action sample at 1,020 prior records took 11.95 s
versus 50.2 ms without cold data, and 13.01 s versus 58.1 ms with 20 MiB cold data
(existing cartridge versus journal). These are single samples, not latency distributions,
and exclude model generation. The installed KPP wheel passed doctor and journal
import from outside both source checkouts. Both project wheels and source distributions
were built offline using the existing pinned build tools.
