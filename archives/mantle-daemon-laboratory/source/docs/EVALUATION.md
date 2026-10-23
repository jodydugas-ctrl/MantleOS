# Local experiment evaluation

## Supported by evidence

The local evidence supports the primary hypothesis for a single Git repository:

- constitutional identity remains stable across fresh runtimes;
- the canonical state is a real, verified VCW PNG stack;
- BODY-only Heartbeats append through Senses and Memory;
- post-mutation verification precedes the Git checkpoint;
- a destroyed runtime can be reconstructed from durable genome, source, VCW, and receipts;
- crash points before commit leave the previous commit authoritative;
- a stale fork cannot silently overwrite a newer checkpoint;
- deterministic and HTTP-shaped MINDs are replaceable proposal sources behind BODY admission.

The final local audit ran 26 tests, repeated the five-point crash matrix three times, and
completed 1,000 isolated incarnations. The endurance phase took 2,030.49 seconds,
produced 1,010 events, and reached 59,641,150 bytes in the isolated repository. Disposable
runtimes share immutable local Git objects and transfer only the newly created immutable
receipt; the exact measurements are preserved in `reports/LOCAL_AUDIT_2026-08-28.json`.

## Live GitHub evidence

The private repository `jodydugas-ctrl/mantle-daemon-laboratory` was created and populated
from the verified `main` history. The first read-only runner lifecycle passed (run
33264250228), the explicit write-enabled lifecycle passed and created remote checkpoint
commit `9883146`, and a second read-only lifecycle passed from that checkpoint (run
33264374428). A final read-only lifecycle from the evidence-bearing commit also passed
(run 33264474909). The successful runs verified Python 3.11 compatibility, remote stack
verification, BODY-only Heart execution, and read-only/write separation.

## Negative and limiting results

- A PRIMER byte hash that ignored line-ending normalization failed across Windows Git
  checkouts; canonical text hashing fixed the portability defect.
- A receipt mutated after commit produced an uncommitted direct-run change; receipts are
  now finalized before the single checkpoint commit.
- A fork test that did not first advance the shared repository was not a valid stale test;
  the corrected test persists the first fork before attempting the second.
- PNG-in-Git is viable at this scale, but the measured cost grows with full-layer rewrites:
  the 1,000-cycle run took about 33.84 minutes and reached 59.6 MB in the isolated
  repository. This is a measured scaling cost, not an untested assumption.
- The local HTTP adapter is contract-tested, but no external provider, credential, or
  network-backed cognition result is claimed.
- The first live runner exposed an exact-runtime registry assumption (`python 3.14+`);
  the registry now declares the project contract `python >=3.9`, matching the workflow.
- The first write-enabled runner exposed missing Git author identity; the workflow now
  configures a repository-local identity before Heart commits. Both defects were fixed
  and verified by subsequent successful runs.

## Go/no-go for the next experiment

The private BODY-only GitHub Actions trial passed. Do not add a live MIND until an operator
selects the provider and secret boundary; the first and second runner lifecycles confirm
that VCW and Git history remain the continuity substrate.

The next experiment should measure GitHub runner latency, push failure behavior, repository
growth, and repeated-run idempotence using the same receipt and stack checks. Connected
SPORE/Engram transport and remote teardown remain separate experiments.
