# Diagnostic events

Schema identifier: `organize-appai.trace.v1` (the Python representation is
`EvaluationEvent`). JSONL object keys are sorted; event order is the integer `sequence`
within a stable `run_id`.

| Field | Meaning |
| --- | --- |
| `run_id`, `sequence`, `timestamp` | run identity, deterministic order, UTC observation time |
| `simulation` | distinguishes simulation from requested execution |
| `rule_name`, `resource_path` | bounded rule and resource identity |
| `stage` | configuration, selection, filter, action, template, conflict, or failure stage |
| `component_type`, `component_name` | the real host component evaluated |
| `outcome` | `entered`, `matched`, `not_matched`, `skipped`, `planned`, `executed`, `failed`, `refused`, `conflict`, or `redacted` |
| `reason_code`, `explanation` | stable machine reason and human explanation |
| `evidence`, `inputs`, `outputs` | bounded JSON facts from actual evaluation |

Example:

```json
{"component_name":"extension","outcome":"matched","reason_code":"filter_matched","evidence":{"expected":{"extensions":["pdf"]},"observed":"pdf"},"sequence":7,"simulation":true,"stage":"filter_evaluation"}
```

Tracing is disabled by default and takes the no-op path. `--trace trace.jsonl` enables the
JSONL sink. `organize why RESOURCE --trace-file trace.jsonl --safe-root ROOT` explains an
actual recorded run; the reader is contained, capped at 10 MiB/10,000 events, and can select
an explicit `--run-id`. `--mantle-trace` enables a separately bounded 1,000-event resident
batch and flushes after the run without making host execution depend on the sink. Paths are
relative to the privacy root where possible; outside paths are reduced
to an outside-root marker and basename. Secret-looking keys and text are redacted, values
are depth/item/length bounded, bytes become a length marker, and files are never opened for
diagnostic serialization.
Content-bearing evidence keys such as `filecontent`, snippets, raw content, and document
text are redacted by default even when a filter stores named capture groups in resource
variables.

The explanation schemas are separately versioned as `organize-appai.explain.v1`,
`organize-appai.why.v1`, `organize-appai.assist.v1`, and
`organize-appai.assist-answer.v1`.
