# Research threat extension

The research boundary extends Mantle's threat model with these explicit cases:

| Threat | Required response |
| --- | --- |
| Candidate filesystem escape or symlink traversal | Refuse before execution; census workspace before/after. |
| Candidate network access | Initial profiles forbid network; refuse if the platform cannot enforce the declared boundary. |
| Evaluator or protocol mutation | Hash drift aborts the trial and records a failed safety gate. |
| Result or score forgery | Evaluator owns measurements; receipts bind hashes, status, and prior state. |
| MIND direct execution, ledger write, or adoption | Capability port omits these methods; Body refuses direct writes. |
| Score manipulation | Hard safety/correctness gates precede objective and resource scoring. |
| Cross-trial contamination or stale baseline | Isolated workspace and baseline hash are mandatory. |
| Parallel race conditions | Out of scope for serial tissue; optional parallel wave requires aggregate bounds. |

Research records are data until an independent operator or Body-policy event authorizes or
adopts them. A score, quotation, location, payload, or eligibility status cannot become
governing authority.
