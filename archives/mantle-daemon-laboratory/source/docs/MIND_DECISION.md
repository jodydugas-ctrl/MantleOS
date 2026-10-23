# Live MIND decision gate

The laboratory keeps the MIND disabled by default. Before steps 100-105 or 161-164 can
run, an operator must choose exactly one provider, define its endpoint/contract, inject one
runtime-only secret, and approve the target repository/network boundary.

The selected provider must implement the `Mind.propose(context) -> proposal` contract. The
BODY will sanitize the proposal, validate its opcode, admit it through normal Memory paths,
and record provider ID, proposal hash, and admission result. Provider wording is never an
authority grant and provider session state is never continuity state.

Required preflight evidence:

- endpoint is explicit and reachable only when the live test is intentionally run;
- secret is present only in the process environment/secret store;
- no secret value appears in VCW, receipts, Git history, or logs;
- one accepted and one rejected proposal are observed;
- the provider process/session is destroyed before a fresh incarnation resumes.

