# Security model

`organize` is intentionally powerful. Delete/trash, shell, inline Python, executable
invocation, recursive traversal, network paths, archive mutation, environment expansion,
templates, symlinks, overwrite policies, and cross-filesystem moves are high risk.

The prototype applies these controls:

- `why` and `assist` require an explicit `--safe-root`, unless a parent directory contains
  a matching `WORKSPACE.txt` marker.
- containment resolves existing parents and symlinks and compares canonical paths; `..`,
  absolute escape, another volume, and junction/symlink escape are refused.
- `assist` uses a closed action allowlist (`echo`, `copy`, `move`, `rename`), refuses Python
  filters, recursion, home/environment expansion, parent traversal, unsafe template values,
  symlink/hardlink actions, and destructive conflict policies. It never executes and always
  saves a new proposal.
- provider output is untrusted JSON, must satisfy a closed Pydantic schema, must parse with
  the real `Config` class, and then passes the same action/path policy. Rejection falls back
  to a conservative deterministic proposal.
- diagnosis invokes real filters but only plans actions. Dangerous action plans produce a
  structured refusal. Prior-trace diagnosis accepts only a contained, bounded JSONL file.
- trace serialization does not read file contents, enumerate environment variables, or log
  credentials. Bounded path/template evidence may still reveal filenames, so traces should
  be handled as operational records.
- the resident terminal accepts `/key` only without an inline payload, then uses a hidden
  prompt. The raw OpenRouter key remains in session memory only and is cleared by `/offline`
  or process exit. It is never persisted or supplied to the local energy ledger.
- real MIND calls require separate explicit operator and guardian approvals bound to the
  current resident. A key alone does not authorize fusion.
- a self-consistent `WORKSPACE.txt` routes the inherited rotating application log to
  `<workspace>/logs/organize`; outside a marked workspace, upstream platform logging is
  retained for compatibility.
- the walker skips both symlinks and Windows junctions. The AppAI guard additionally rejects
  a configured root or selected path that resolves through a link outside the approved root.

The normal upstream `run` command remains powerful for compatibility. Organize.AppAI does
not claim to sandbox a configuration the operator explicitly executes. Review `explain`,
run `sim`, inspect traces, and authorize execution separately.
