# Mantle bounded research charter

The research tissue is Body-owned and serial by default. It borrows the design shape of
baseline-first, fixed-budget experimentation, but it is independently implemented and
cannot adopt its own result.

Each trial has exactly one mutable logical candidate surface. The protocol, evaluator,
corpus, safety gates, baseline, and canonical source are immutable and hash-bound for the
trial. A candidate is materialized in an isolated workspace; the original host, current
organism, evaluator, and canonical Grimoire are never edited in place.

Every trial has fixed experiment-count, wall-clock, CPU, memory, output, filesystem, and
energy budgets. Initial profiles forbid network access. A trial must establish a baseline
before modification, and every attempted transition is appended to the Body-owned ledger.
Outcomes are `ELIGIBLE`, `DISCARDED`, `CRASHED`, `REFUSED`, or `INCONCLUSIVE`; eligibility
is not adoption.

Safety and correctness gates dominate score. Simplicity and resource cost are evaluation
dimensions after hard gates. Operator cancellation is immediate and receipted. The loop
stops on budget exhaustion, energy starvation, repeated crashes, no improvement, distress,
hash drift, strict-gate failure, or any forbidden action. There is no never-stop mode.

The MIND may inspect protocols, propose candidates, and request future work through a
capability port. It may not execute processes, write files, mutate evaluators or protocols,
append receipts, authorize, calcify, or adopt. The first implementation is one candidate
per Heart pulse; parallel trials are out of scope until separately authorized.
