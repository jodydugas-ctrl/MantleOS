# Mantle OS — Security Contract and Threat Model

This is the repository's canonical security-claim table. It is subordinate to the
constitutional Grimoire and to the current implementation under `src/mantle/`; it does
not create a second doctrine. A conflict with either is a defect to resolve, never a
license to choose the stronger-sounding claim.

## 1. Protected assets

Mantle protects the deterministic Body, durable memory history, Body identity and
lineage, MIND-fusion authority, cultivated-skill execution, and the evidence emitted by
its certification gates.

## 2. Principals

- **Operator:** trusted authority holder. A hostile operator is out of scope.
- **Body code:** trusted in-process Python implementing the organs and substrate.
- **MIND:** the declared `prompt -> text` model callable. It receives text and returns
  text; it does not receive Python objects, tools, sockets, or file handles.
- **OTHER:** data or artifacts not proved SELF.
- **Cultivated skill:** Python proposed as data, trialed, and calcified by the Body.
- **Acquisition source:** a remote repository or other origin from which inert material
  is imported.

The Python `Mind` class is Body-side wrapper code, not the MIND principal. Calling
`mind.org` requires in-process Python execution and therefore demonstrates a public API
exposure, not a capability of the declared `prompt -> text` model.

## 3. Trust boundary

In-process Body/operator Python is trusted. Mantle does not claim to sandbox a malicious
Body, a hostile operator, the Python interpreter, or the standard library. Arbitrary
tool-calling, function-calling, or code-executing MINDs are out of scope unless placed
behind a real process or runtime isolation boundary.

Python naming conventions, private slots, AST filters, and restricted builtins are useful
hardening but are not a hard sandbox.

## 4. Verdicts

| Verdict | Meaning |
| --- | --- |
| `enforced` | The implementation prevents the named in-scope principal and a live proof demonstrates the refusal. |
| `detected` | The implementation may not prevent the event, but detects it and produces evidence. |
| `conventional` | Correctness depends on callers or deployment practice; prevention or detection is incomplete. |
| `out of scope` | The threat is explicitly outside this contract, with the reason stated. |

Code references prove that a check exists, not that prose and check are semantically
equivalent. Reviewers remain responsible for that mapping.

## 5. Guarantee table

<!-- MANTLE-GUARANTEES:START -->
| ID | Property | Principal / threat | Verdict | Live proof | Notes |
| --- | --- | --- | --- | --- | --- |
| `TM-HISTORY-REWRITE` | Existing memory rewritten out of band | corruption or trusted in-process code | `detected` | `HF-B29`, `HF-B46b` | Entry hashes and ancestor fingerprints reveal alteration. Detection is not prevention. |
| `TM-INSERTION-PROVENANCE` | A newly inserted valid row proves its authorized writer | trusted in-process code | `out of scope` | — | Hashes cover content but do not attest which organ called append. |
| `TM-MIND-BAND-SCOPE` | Declared MIND writes outside `thoughts` / `brain` | `prompt -> text` MIND | `enforced` | `HF-M10` | Body-side `guarded_write` refuses and immune-logs forbidden bands. |
| `TM-WRAPPER-RAW-HANDLE` | Body-side MIND wrappers expose a raw organism handle | in-process caller | `enforced` | `MIND-PORT-1` | Public wrappers expose capability ports, not raw Body handles. The trusted ports retain private `_org` references: this is defense in depth, not a Python sandbox. |
| `TM-GENOME-MUTATION` | Identity or Primer changes after birth | declared MIND / ordinary callers | `enforced` | `HF-B07`, `HF-B45`, `HF-B02` | Identity stays in the Body; the Primer seals at birth. |
| `TM-ANCESTOR-SEAL` | A sealed ancestral generation is changed | corruption or trusted in-process code | `detected` | `HF-B46`, `HF-B46b` | Normal writes are refused; out-of-band mutation is detected by the seal fingerprint. |
| `TM-AST-KNOWN-REFUSALS` | Known imports, dunder traversal, and named escape primitives enter a cultivated skill | proposed Python skill | `enforced` | `HF-B51`, `HF-M12` | This is a finite syntactic refusal claim, not a complete Python sandbox. |
| `TM-PYTHON-HARD-SANDBOX` | Arbitrary hostile Python cannot escape | hostile skill | `out of scope` | — | The prepared WASM seam is not implemented; the Python runner is not a hard sandbox. |
| `TM-SKILL-INTEGRITY` | Code hash, capability, provenance, or calcification gates are bypassed | cultivated skill | `enforced` | `HF-B47`, `HF-B48`, `HF-B50`, `HF-B52` | These gates run before the selected runner. |
| `TM-SKILL-WALLCLOCK` | Skill exceeds its wall-clock budget | cultivated Python skill | `enforced` | `BUGFIX-1`, `EXEC-LIMIT-1` | The Python child process tree is terminated on timeout. |
| `TM-SKILL-MEMORY-OUTPUT` | Skill exhausts memory or returns unbounded output | cultivated Python skill | `enforced` | `EXEC-LIMIT-1` | POSIX address-space limits or a Windows Job Object bound memory; JSON request, result, and response sizes are capped. |
| `TM-FOREIGN-EXECUTION` | Foreign Python runs on the non-isolating runner | public invoke caller | `enforced` | `HF-B50`, `EXEC-TRUST-1` | Public grants carry resource capabilities only; unknown/reserved keys are refused. Trial authority is a private Body ceremony. |
| `TM-FOREIGN-ACQUISITION` | Remote material is pinned and reproducible | GitHub acquisition source | `enforced` | `SUPPLY-1` | `applet-clone` requires explicit network consent and an exact 40-hex commit; checkout is detached with hooks/submodules disabled and commit/tree hashes receipted. |
| `TM-SECRET-BOUNDARY` | Secrets enter ordinary memory/log surfaces | input and failure paths | `enforced` | `HF-B20`, `APPLET-5` | Senses and Immune redact before append. |
| `TM-CONTEXT-VEIL` | Private thoughts enter the model context | declared MIND | `enforced` | `HF-M14` | Nervous assembly resolves references and applies the veil. |
| `TM-CONTEXT-LEDGER` | Rolling context leaks, mutates its prefix, consumes uncommitted sources, crosses its budget, includes itself, or resumes corrupt state | declared MIND, provider failure, or storage corruption | `enforced` | `CONTEXT-BODY-OWNED`, `CONTEXT-NO-SELF-INCLUSION`, `CONTEXT-CANONICAL-BYTES`, `CONTEXT-CURSOR-COMMIT-AFTER-SUCCESS`, `CONTEXT-PREFIX-IMMUTABLE`, `CONTEXT-ROLLOVER-BEFORE-HARD-LIMIT`, `CONTEXT-PRIVATE-VEIL`, `CONTEXT-REQUEST-HASH-EXACT`, `CONTEXT-CORRUPTION-DETECTED` | The private Body-authored ledger uses canonical full-hash chains, commit-last cursors, deterministic rollover, exact request hashes, and recovery generations. Provider cache hits remain outside Mantle's control. |
| `TM-FUSION-AUTHORITY` | MIND fuses without current Stage-1 evidence and dual approval | caller | `enforced` | `HF-M15` | Approval is target-bound and distinct from technical readiness. |
| `TM-MIND-SELF-PROMOTION` | MIND promotes inference to fact or calcifies itself directly | declared MIND | `enforced` | `HF-M12`, `HF-M16` | Limbs and Body own promotion/calcification. |
| `TM-CONSOLIDATION-AUTHORITY` | Retrospective cognition rewrites history, promotes inference to fact, invents source coordinates, or advances its cursor after refusal/failure | declared `prompt -> text` MIND / provider failure | `enforced` | `CONSOLIDATION-1` .. `CONSOLIDATION-4` | MIND output remains inferred; Limbs validates Body-selected references and mutations; original records remain immutable; fact promotion remains external-evidence-only; the receipt commits the cursor last; the MIND write surface remains unchanged. |
| `TM-PHASE1-MODEL-FREE` | Phase-1 behavior depends on a model | Body implementation | `enforced` | `HF-B08` | Static and clean-interpreter proofs keep certified Phase 1 model-free. |
| `TM-REFERENCE-CERT` | Repository reference-organism regression is detected | framework change | `detected` | `HF-B08`, `DOCTOR-1`, `STAGE2-PROFILE-1` | Stage 2 aggregates base, reborn, and resident fixtures: every row must PASS somewhere, no profile may FAIL, and all-N/A remains a blocking gap. Repository gates still do not certify arbitrary dependent applications. |
| `TM-APPLICATION-CERT` | A dependent application's own nest is certified | user application | `enforced` | `CERTIFY-1` | `mantle certify <path>` loads the actual nest, runs applicable Stage-1 rows plus repository invariants, fingerprints target artifacts and the invariant registry, and emits a Body-signed deterministic receipt. |
| `TM-GRIMOIRE-EDITION` | Grimoire editions, procedure metadata, or verifier agreement drift | VCW profile data and decoder | `enforced` | `GRIMOIRE-V010-01` .. `GRIMOIRE-V010-14` | Edition selection is explicit; v0.9 remains frozen; zero-HEAD procedures remain non-governing without container metadata; parity is not transport integrity; the independent verifier must agree with runtime BOOK semantics. |
| `TM-GRIMOIRE-SEMANTIC` | Semantic-memory encoding invents evidence/force or atom addresses, loses the raw run, or weakens the entry-stream guarantees | VCW profile data and decoder | `enforced` | `GRIMOIRE-ENC-01` .. `GRIMOIRE-ENC-14` | The one-step driver encodes at append; evidence/force come only from the default tables; record-kind atoms are canonical section-6 rows verified against the edition; raw runs are hex, hash-covered, and parity-checked; ids, veil, immune marks, graded memory, metabolism, and evidence-distinct dedupe hold on semantic bands; Stage-1 stays model-free; adoption is operator-receipted new-tissue-only. |
| `TM-RESEARCH-BOUNDARY` | Bounded research candidate escapes workspace, mutates evaluator, forges score, or self-adopts | Research Ganglion, Candidate Chamber, immutable evaluator, Body-owned ledger | `conventional` | `RESEARCH-1` | Candidate containment, traversal refusal, original-source integrity, inert proposals, and Body-owned evidence are executable. This is a bounded workflow, not hostile-process isolation. |
| `TM-REMOTE-RESIDENCY` | A GitHub NEST can't become SELF, the Heart, or Phase-1 authority; private visibility and local determinism are preserved | remote residency | `enforced` | `GHNEST-1`, `GHNEST-2`, `GHNEST-12`, `GHNEST-15`, `GHNEST-16` | Private-by-default, numeric-ID binding, backward-compatible local target, byte-equivalent local-to-GitHub-to-local round trip, and visibility-flip refusal keep GitHub as OTHER evidence carried locally. |
| `TM-REMOTE-INTEGRITY` | Tampered remote manifest, sealed Body, or stale authority is never trusted | remote materialization | `enforced` | `GHNEST-5`, `GHNEST-19` | Tamper fails envelope authentication; stale certification is evidence, never current runtime authority. |
| `TM-REMOTE-SECRET` | The Body or a provider key never travels in plaintext; the envelope-opening capability is never MIND-exposed | outbound publish | `enforced` | `GHNEST-3`, `GHNEST-10` | Plaintext Body paths and secret-shaped payloads are refused; the Body travels only inside an authenticated sealed envelope. |
| `TM-REMOTE-CAS` | State-branch head moves only by exact-revision non-force compare-and-swap, fully proved end to end | publication | `enforced` | `GHNEST-4`, `GHNEST-6`, `GHNEST-7` | Exact-head materialization; a stale expected-parent CAS refuses without force; outbound intent and completion are transaction-bound-proved. |
| `TM-REMOTE-EVENTS` | Inbound GitHub events enter Senses exactly once; failures route to Immune; schedule drift is repaired | event intake | `enforced` | `GHNEST-8`, `GHNEST-9`, `GHNEST-14`, `GHNEST-18` | HMAC-verified webhooks are shaped once as OTHER; wrong repo/install and bad-HMAC deliveries are rejected; missed pulses are recovered rather than stacked. |
| `TM-REMOTE-ISOLATION` | Phase-1 interpreter stays network-free; artifacts/caches are never canonical; workflows are SHA-pinned with minimum permissions | isolation | `enforced` | `GHNEST-11`, `GHNEST-13`, `GHNEST-17` | Canonical state is the fingerprinted NEST; no nest module imports a network client at module scope; workflow templates declare permissions and SHA-pin actions. |
<!-- MANTLE-GUARANTEES:END -->

## 6. Residual risks

- The Python runner is a subprocess with wall-clock control, not a hard sandbox.
- Memory, wall-clock, JSON request/result, and child-response bounds are enforced by
  `EXEC-LIMIT-1`; platform facilities still differ (POSIX rlimits versus a Windows Job
  Object), and neither turns arbitrary Python into a hard sandbox.
- Static Python filtering is finite and can erode as the language changes.
- Remote GitHub applet acquisition requires an exact commit and records commit/tree
  hashes. Non-GitHub acquisition adapters must provide equivalent pinning before admission.
- Repository certification does not certify an arbitrary application; `mantle certify
  <nest>` is the separate target-bound application gate, and a historical receipt is not
  current runtime authority.
- A raw in-process caller can reach internal Python state; this is inside the trust
  boundary even when public façades remove convenient handles.
- Windows fallback persistence refuses traversal plus pre-existing root, artifact, and
  nested symlinks, but Python exposes no descriptor-relative rename there. A privileged
  actor concurrently replacing a validated parent during the final rename is outside the
  trusted-operator boundary; POSIX runs retain the live descriptor-swap proof.
- `durable-exact` rolling continuity retains exact redacted projected context and responses;
  confidentiality at rest depends on host storage encryption and access control.
- A provider may ignore, evict, partition, or misreport its cache. Mantle records observed
  cache facts but does not claim that a stable prefix guarantees a hit.

## 7. Proof surfaces

- `python -m mantle audit` — deterministic Stage-1 reference gate.
- `python -m mantle prove` — live invariant registry.
- `python -m mantle audit-mind` — Stage-2 containment/regression fixtures.
- `python -m mantle check --strict` — full closed-world repository certification; any
  skipped or not-applicable required gate fails closed.
- `python -m mantle doctor <nest>` — deployment and documentation-coherence checks.

Technical evidence never grants operator authority for fusion, mutation, network access,
reproduction, or publication.
