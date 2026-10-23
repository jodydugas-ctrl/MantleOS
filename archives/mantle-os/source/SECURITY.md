# Security Policy

## Supported versions

Security fixes are provided for the current maintained line.

| Version | Supported |
|---|---|
| 2.0.0rc1 candidate | Yes |
| 1.x | Upgrade required |

## Reporting a vulnerability

Please use GitHub's private **Security advisories → Report a vulnerability** flow for this
repository. Do not publish credentials, resident identity keys, approval keys, raw prompts, or
proof-of-concept payloads in a public issue.

Include:

- the affected version and platform;
- the smallest reproducible sequence;
- expected and actual behavior;
- whether the issue crosses a Body, persistence, authority, host, or reproduction boundary; and
- any temporary mitigation you verified.

## Security boundaries

The canonical, implementation-scoped guarantee table is
[`THREAT_MODEL.md`](THREAT_MODEL.md). It grades each claim as enforced, detected,
conventional, or out of scope and distinguishes the declared `prompt -> text` MIND from
trusted in-process Body/operator Python.

- Stage-1, Stage-2, containment, and `READY` are technical evidence, not production fusion
  authority.
- Production MIND fusion requires fresh resident-bound evidence plus distinct authenticated
  operator and guardian approvals.
- External hatch and graft activation requires a fresh, one-shot authorization bound to
  the artifact, lifecycle action, and exact resolved target. Inspection and migration do
  not activate an artifact.
- SELF-vault reconstruction remains a Body-owned recovery path and must still pass its
  integrity, provenance, instinct, Stage-1, and atomic-persistence gates.
- MIND fusion is a separate authority boundary and continues to require distinct,
  resident-bound operator and guardian approvals.
- Authority credentials and provider credentials are deployment secrets and must never be
  committed.
- The Hermes addon is fail-open toward host operation but fail-closed toward fusion authority.

The project will acknowledge a complete private report when maintainers are available, assess
severity, and coordinate disclosure after a fix or mitigation exists. No fixed response-time SLA
is promised.
