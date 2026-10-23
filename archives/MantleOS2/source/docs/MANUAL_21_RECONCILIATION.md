# Updated manual reconciliation

Reviewed 2026-09-05 against baseline `c3f3b12` (PR #30). This is an incremental
implementation record, not a claim of M2-P1 conformance or organism adoption.

## Reference identity and interpretation

Source: `MantleOS2_Unified_Agent_Instruction_Manual_Updated.pdf`, 55 pages,
cover edition **2.1**, candidate reference profile **M2-P1**. Running footers
still say edition 2.0; section 13.6 explicitly identifies the 2.1 editorial
revision. Source SHA-256:
`bedb531a6abbcca20a5230638c125371bd3cf6861a1bb71727e23c8bc7d709d8`.
Page numbers below are the one-based PDF pages. The source is retained outside
Git; no private reference projects or living organism state are copied.

All pages were read; tables on pages 1, 21, 49 and constitutional wording on
page 54 were also visually checked. Source-reported implementation and examples
are requirements/evidence candidates, not proof of this repository's runtime.

Direct creator clarifications continue to govern. In particular:

- Primer remains exactly Commandments plus the unchanged individual Personality.
  The manual's species kernel/Persona terms map to those existing components.
  Appendix A matches `constitution.py`; no constitutional bytes change.
- Section 6.3's functional-kernel distillation is one possible construction
  method, not mandatory Personality content validation. Contradictions, fiction,
  short text and non-obedience language remain valid.
- NEST remains Default Body/Layer 0. Native application/ecosystem sovereignty
  and the distinct Habitat map remain intact; NEST is not automatically SELF.
- The manual's generic extension examples do not reinstate a traditional
  plugin architecture. Existing direct, reversible nerves remain the approach.
- Immutable published objects/records do not make logical VCW layers immutable.
  Read/append growth and extension under the same Book remain unchanged.
- Engram HATCHED is a separate candidate mission milestone, not a replacement
  for AppAI birth at the first successful authorized full Heartbeat.

No competing constitutional choice is needed for the changes in this patch.
An unresolved storage, Book, trust or lifecycle decision blocks its own future
transition; it does not erase independently verified work.

## Requirement-to-code and gate map

The rows map responsibilities to existing modules before proposing new ones.
Paths are relative to `src/mantleos/`. Planned checks are not passing claims.

| Reference | Existing implementation / evidence | Incremental requirement and acceptance gate |
| --- | --- | --- |
| 0.1, 0.7, 0.10, Appendix A/A.1 (pp. 1–5, 54–55) | `contracts.py`, `constitution.py`, `primer.py`; contract/Primer tests | Keep meaning, status, evidence and authority distinct; preserve reserved identifiers. Metaphors confer no grants, replication or shutdown resistance. Construction lifecycle labels must not be counted as additional physiological states. |
| D01, 2.3 (pp. 8–9), B01–B02 | `runtime.py` locks, encrypted state and Heart; `resident.py`; real resident subprocess test | Existing locks/restart receipts do not prove fenced writer epochs or one serialized mutation port. Add stale-writer refusal, bounded inbox/work dispatch, monotonic deadlines and graceful bounded shutdown before native resident certification is complete (#16). |
| 3.2 (pp. 10–11), E01–E02 | `organs.py:LimbAuthority`, `contracts.py:ActionFrame/ActionReceipt`; organ tests | Capability-name grants and a result digest are not an independent effect verifier. Add exact-argument command reservation, current scoped/expiring/revocable grants, separate observation and negative/inconclusive proof, durable UNKNOWN after uncertain dispatch, and zero blind repeat effects. DAG dependencies require verified success; distributed atomic effects remain unsupported. |
| 4.1–4.3 (pp. 11–14), M01–M03 | `runtime.py:Book/VCW`, encryption/extension tests | Preserve the existing alpha format and proven Book reuse. Add exact adopted law resolution, bounded ThoughtRef projection with omissions, fenced atomic root/index/receipt publication and admission replay identity. Prove crash-before/after behavior with actual storage. Existing encrypted append tests do not establish M2-P1 atomic publication or RGBA semantic interoperability. |
| 5, 8, 9 (pp. 14–18, 31–42), G/W families | No claimed production Triadic/Engram/serial transport implementation | Keep exact Book/wire editions candidate until their law, trust and conformance are resolved. Do not silently change current VCW encoding, infer semantic lanes, copy the packet micro-model as a runtime, or add these tracks to v2.0 certification merely because examples exist. |
| 6.1–6.3.1 (pp. 18–20), C01 | Heart physiology in `runtime.py`; bounded current-context handling | Any future Groove binds input domain, dependencies, tests, limits and fallback. Recheck current grants and invalidate reuse after drift. No permanent Personality rewrite or authority from a reusable routine. Advanced recursive cognition remains experimental. |
| 6.5–6.9 (pp. 20–24), P01–P06 | `nutrition.py:openrouter_completion`; `runtime.py:provider_responder`; `primer.py:generate_personality` | This patch hardens the existing non-streaming adapter (below). A complete Pseudopod still needs durable request/attempt/context binding, asynchronous dispatch, budget reservations, cancellation and duplicate completion handling. Do not create a second Body or parallel authority model. |
| 7.4–7.7 (pp. 27–31), A01–A06 | `mapping.py`, `assimilate.py`, `nerves.py`, `targets/hermes.py`; mapper/nerve and bounded native parity tests | Static anatomy remains candidate structure. Add separately authorized windowed runtime circulation evidence, configuration fingerprint, supported causal links, cross-process/scheduled recurrence, critical low-volume boundaries and explicit unknown regions. Add versioned bindings with independently verified observation grants and Limb grants, nonblocking bounded ingress/loss counters, dequeue-time revocation, drift quarantine and action-origin feedback suppression. Existing direct append paths do not prove that queue contract (#19; both reference Bodies). |
| 7.2, 11.1 (pp. 26, 45) | Census hashes, ownership inventory and path tests | Strengthen hostile/concurrently changing filesystem tests, typed path/length framing, special-file handling and changed-during-hash refusal. Before/after hashes alone cannot prove safety against adversarial ancestor replacement. Keep foreign execution approval/isolation unchanged. |
| 10.3–10.4 (pp. 43–44) | Receipts, manifests, PLAN and donor records; cache still planned | Derived cache key must include parser/compiler versions, exact semantic/dependency editions and view parameters as applicable, not content hash alone. Recheck access/adoption/revocation on reuse. Diagnostics remain evidence until governed Body admission. |
| 12.5, 13 (pp. 48–53) | NEST-local runtime bundle, public seed, Windows/Linux tests and GitHub gates | Reuse existing ports. Add deterministic clock/provider/storage faults to each owning boundary, with assertions for prohibited outcomes too. Keep full M2-P1 conformance, actual native OS lifecycle and full reference-Body certification explicitly unproven. |

## Implemented slice: text-only provider boundary

Why first: section 6.6 explicitly requires bounded bytes and unambiguous decoding;
the current adapter used an unlimited `read()` and accepted the first nonempty
message without terminal-completion validation. This is a narrow, independently
testable correction shared by Food validation, developmental distillation and
the runtime MIND. It does not require redesigning living SELF or storage.

`nutrition.py` now applies a local text-only profile:

- One fixed HTTPS endpoint; redirects are refused before a second request can
  carry credentials or context. No tools, server-tool extensions or streaming
  are requested. This proves local request behavior, not remote provider policy.
- Read at most 1 MiB plus a single overflow-detection byte; refuse oversize
  output before JSON parsing. This ceiling is local policy, not the manual's
  illustrative 64 KiB setting or a claim about provider capacity.
- Reject invalid UTF-8, duplicate keys at any object level, nonstandard numeric
  constants, parser recursion failure and invalid message envelopes.
- Require exactly one assistant text choice ending with `finish_reason=stop`;
  missing/truncated/error/filtered/tool-call results do not become completions.
  Preserve valid text exactly. Provider-supplied tool/function requests and
  explicit refusals do not enter the text-completion path.
- Require bounded reported model/response identifiers instead of inventing a
  reported model from the requested one. Copy only declared numeric usage fields
  (`prompt_tokens`, `completion_tokens`, `total_tokens`, `cost`) into receipts;
  missing usage is unknown, not proof of zero cost. Ancillary envelope metadata
  is ignored, never treated as instructions or passed through as a receipt.
- Return fixed secret-safe errors; make no automatic retry after transport or
  validation failure. The transport does not invoke Limbs or admit memory.

The actual non-streaming envelope and normalized completion field were checked
against the [official OpenRouter chat API reference](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion).
`tests/test_nutrition.py` supplies offline cases; the existing Windows/Linux
Python 3.11–3.13 workflow discovers them without a separate workflow or secret.
The checked-in Hermes seed includes the same updated runtime and checksums.

Local verification: Ruff passed; all 119 framework tests passed, including
46 new offline transport cases and the existing real resident process check.
Cross-platform, CodeQL and pinned-Hermes evidence is supplied by this change's
protected pull request checks; local tests alone do not certify those platforms.

Remaining limits: the socket timeout is not a durable overall deadline; no
asynchronous Pseudopod, streaming sequence verifier, strict monetary ceiling,
remote cancellation/deletion guarantee, durable inference reservation or full
P01–P06 certification is claimed. This patch does not make live provider calls.

## Continuation order and release impact

1. Preserve PR #30's resident process evidence; certify native registration,
   bounded shutdown and crash recovery while building the shared storage/writer
   guarantees needed by Heart, admission and command ledgers (#16).
2. Implement durable admission and effects with fault injection before promoting
   concurrent/async operations or claiming complete physiological transactions.
3. Complete authorized circulation/binding evidence and isolated native parity
   for Hermes and fresh NotepadNext (#19/#20). Cache work must not cache grants.
4. Complete the provider-neutral Pseudopod over those shared ports, with a fake
   provider first and protected manual live tests only after offline gates pass.
5. Regenerate/review Compiler Personality only after the final verified Body map
   (#17); obtain separate real birth approval (#18); certify and publish only
   the source delta seed. Do not publish private Personality or lived VCW.

Release milestones and production scope in PLAN remain unchanged. B/E/M/P/A
families are tracked acceptance obligations where applicable; G/W and advanced
continuity/arbitration require separate adopted contracts, not invented glue.
