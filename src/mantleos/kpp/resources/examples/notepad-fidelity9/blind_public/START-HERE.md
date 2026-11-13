# Notepad Anchor Code — Model-independent blind interpretation challenge

This is the **model-facing** packet only. The sealed expected results, reference
Python implementation, scenario labels and scoring machinery are intentionally absent.
This benchmark targets frontier models but does not depend on a model, SDK,
provider, chain-of-thought disclosure, Python runtime, or hosted API.

For **each** item in `challenge.json.trials`, use only its declared initial state,
stimulus, canonical Anchor types, the linked Gate condition and shared semantics.
Compute the **updated** state and user-visible result. Submit one standalone JSON
object per line to the evaluator as `responses.jsonl`; 41 lines, any order.

Required JSON keys exactly: `trial_id`, `outcome`, `result`, `state`,
`gate_families`, `reason`. The full state has 10 keys documented by the
`expected_response_schema`. Copy the initial state's virtual file values unless
an approved virtual effect changes them; do not invent real file/clipboard writes.
For a missing host observation or irreducible ambiguity, use `UNDETERMINED` and
explain why rather than fabricating a success. For rejected commands, use
`REJECTED_BY_GATE`, null result and preserve all state that should remain stable.
For successes use `PREDICTED_FROM_ANCHORS` and the clause-specific result object.

The explicit `result_contract` provides the exact allowed JSON result variants
and maps the 17 supported actions to those variants. `gate_registry` enumerates all
9 families and all 19 condition clauses. The build-time family is offline only,
not an additional runtime dispatch requirement. Each trial includes a pre-command
`file_session_observation.disk_comparison` from the trusted virtual host: MATCH,
MISMATCH, MISSING, NO_ASSOCIATION, or UNKNOWN. On Save, MISMATCH rejects, MISSING
may allow a new virtual write, and UNKNOWN requires UNDETERMINED if equality
is required. Do not calculate, invent, or assume a hidden expected SHA-256.
The observation is a precondition, not proof that a later write succeeded.

This is a **virtual host** exercise. Initial `virtual_files` values use either
`{"text":"..."}` for valid UTF-8 content or `{"bytes_hex":"fffe"}` for
invalid UTF-8. Do not compute SHA-256; it is intentionally excluded from the
required response. The provided prestate and contract still control the rules.
Document positions use Unicode code points, with half-open ranges.

Do not inspect any reference program, evaluator key or answered corpus. Do not
execute Python. All cases are independent snapshots, not a sequential API session.
The expectation is a falsifiable structured result, not disclosure of hidden model
reasoning. An operator should keep token/latency/retry/provenance logs separately.
