# Limitations

- `assist --config "Why ..."` uses a bounded top-level sample (20 resources, 200 evidence
  facts); it does not recursively inventory a tree. Use `organize why <resource>
  --trace-file <trace>` for the exact action/conflict/template outcome of a prior run.
- The offline intent translator covers common PDF invoice, age quarantine, screenshot
  rename, duplicate-report, and report-only patterns. It states assumptions instead of
  inventing unsupported extraction fields.
- The included `.pdf`, `.docx`, and `.png` fixtures are content-free extension placeholders;
  content-extraction behavior is covered by upstream tests rather than the demo.
- The optional `MantleCallableProvider` accepts a callable already bounded/configured by an
  operator. This project adds no vendor client and no competing key or secret store.
- The desktop resident terminal intentionally does not persist OpenRouter keys. Re-enter
  `/key` for each new session or use an external operator-managed secret boundary.
- A saved Mantle resident does not persist a fused MIND object. Fusion requires fresh
  process-local Stage-1 evidence and explicit operator plus guardian authorization.
- Normal upstream execution is not restricted to the AppAI workspace. The strict path guard
  applies to AppAI diagnosis, proposals, tests, and demo operations.
- Windows upstream baseline retains two platform-assumption failures: Unix `touch` in the
  shell-action test and treating the `dir` shell built-in as an executable.
