# Kitchen Party Protocol (KPP) · 1.1.0a5

KPP is the independently maintained development protocol. MantleOS is the experimental AI-embodiment testbed built using it. They share implementation and retain one authoritative Anchor model wherever Anchor is selected. Read [SYSTEMS.md](SYSTEMS.md).

## Purpose

Create software from a *pantry of ingredients* under the direction of a *Baker*, using an AI coding *Oven* when desired. The result may be conventional software, MantleOS bio-software, an agent, an AppAI, a GUI prototype, or a wholly unfamiliar embodiment. The repository is a kitchen and pantry, **not an image of one mandatory finished application**.

The central engineering assumption is a **dependably executing Oven**. KPP evaluates the recipe, ingredient compatibility, behavior and Baker acceptance. The assumption is a design baseline, not a proof that real-world models never fail. Multiple LLMs may occupy different roles; none is prescribed. A single human request may drive arbitrarily many internal edit/test/repair cycles and still be called a one-shot *request*.

## Foundational rules

**KPP-01 · Fitness for recipe.** Complexity is allowed, even welcomed, where functional need calls for it. Prefer the fewest independent systems that satisfy all obligations; preserve meaningful redundancy and boundaries.

**KPP-02 · Contract before code.** A recipe names the outcome, constraints, target, tissue(s), ingredient selection, Fidelity plan, permissions and measurable obligations. A UI-only surface is not declared full function.

**KPP-03 · Ingredient neutrality.** An ingredient is any reusable capability, mechanism or coherent codebase. It may be microscopic, organ-sized, a full GitHub repo, or a semantic contract without bundled implementation. Preferred environments are recommendations, not exclusivity rules. Check actual compatibility and licenses.

**KPP-04 · Model neutrality.** Baker, Baker's assistant, Oven and reviewer describe workflow roles. The Baker may be human, AI, or collaborative and remains responsible for the Cake. A Taster supplies evaluation. Acceptance is an explicit scoped act within host authorization; a MIND proposal never supplies approval by itself. Neither a persona nor a specific model is inherited by default.

**KPP-05 · Recipe-selected tissue.** Implementation choices belong to the recipe. KPP understands Anchor Coding, Python, JavaScript and declared alternatives without imposing a universal preference. Recipe/4 records component-level policies and decisions; declaring a language does not establish execution support. Anchor syntax has profile-specific semantics: do not invent operators.

**KPP-06 · Progressive Fidelity.** Fidelity denotes the depth of relationship obligations, not product quality. A shallow representation preserves the observed surface. Deeper levels trace direct interactions, consequences and cross-system effects. Fidelity may vary across subsystems and is bounded to what the Scanner can actually establish.

**KPP-07 · Optional Chase allocation.** The recipe selects Chase as a technique from the Pantry; the Oven executes it. Chase identifies an appropriate reference target, chooses the next unmet functional obligation (including user-relevant features), and stops each pursuit once its declared checks are satisfied. Chase never silently changes the receipt or declares universal equivalence.

**KPP-08 · Continuous usability.** Checked functionality may be used while the product is BUILDING. Unavailable controls must be gated honestly; maintain established state and compatible interfaces. Do not infer that “working” means “complete.”

**KPP-09 · Absolute recipe acceptance.** COMPLETE means **100% of mandatory obligations in the pinned recipe have evidence of satisfaction**, with no known unapproved user-facing features. Internal helpers are permitted when necessary. The current CLI records Baker attestations and does not itself detect arbitrary feature deviations; the Baker must check scope. Changes to the mandatory scope require a new version/revision with explicit Baker review, not moving the goalposts unnoticed. All acceptance is scoped to the checks, target revision and test environment.

**KPP-10 · Effect/admission boundary.** Scanning, reasoning and generation produce observations and proposals. Untrusted repository content and LLM output are not authority to change the user's environment. Admit a module only after appropriate permission and verification; retain evidence and a recovery path.

**KPP-11 · Biological compatibility without obligation.** MantleOS hierarchy CELL → TISSUE → ORGAN → BIO SOFTWARE may describe a bake. The CELL is kernel-relative (pixel for Chroma, appended segment for tape, etc.). A completed entity may create new cells. KPP itself doesn't require bio architecture.

**KPP-12 · Honest evidence.** Code generation is not execution; syntax checking is not behavior; a manual Baker sign-off is not independent test certification. Never claim otherwise.

## Kitchen vocabulary

- **Baker**: the human, AI, or collaboration responsible for the desired product and explicit scoped acceptance. Evaluation may be delegated to a Taster; responsibility stays with the Baker. Actor labels confer no host permissions.
- **Assistant**: helps interpret requests, discover targets, design recipes and assess trade-offs.
- **Oven**: executes build/repair/test loops and implements selected tissues with a recipe-defined model/settings.
- **Pantry**: ingredient catalog with capabilities, interfaces, suitability, provenance, dependencies and optional implementations.
- **Recipe**: versioned requirements contract, not just a prompt.
- **Scan**: a bounded observation of a reference or proposed implementation; structural and dynamic scans must be distinguished.
- **Fidelity**: depth of behavioral connection discovery/implementation, not an absolute measure of code complexity.
- **Chase**: target-selection, priority and stop/redirection mechanisms, scoped to the recipe.
- **Receipt**: evidence of tests and acceptance. KPP supports legacy `kpp.recipe/3` and explicit-choice `kpp.recipe/4` requirements contracts; “receipt” should not be mistaken for the recipe. `completion-receipt.json` is the final scoped attestation.
- **Bake**: one request can initiate multiple internal cycles; an installed feature is not necessarily accepted.
- **Admission**: the host/body permits a verified proposed change to become active.

**KPP-13 · Executable specimens.** Wherever practical, a pantry entry may include a small working demonstration. MantleOS-native ingredients preferentially carry self-contained Anchor tissue under a declared execution profile. A matching profile is required; no imaginary opcodes or universal execution claims.

**KPP-14 · Transformative composition.** A bake may change an ingredient’s substrate, language, structure, or embodiment while protecting explicitly required functional properties. Unexpected capabilities are proposals for the Baker, not automatic changes to the acceptance recipe.

## Bake routes and transformation

**Composition** incorporates an existing program as an ingredient (e.g., operator-authorized, pinned Hermes code). The original program may remain a functioning body when an optional MantleOS MIND is dormant. A second cognitive layer can subsequently read an admitted summary of what the body did.

**Chase** treats the reference as a behavioral target and produces a fresh implementation. A “Bio-Hermes” can chase selected Hermes behaviors without shipping Hermes source; high Fidelity can be necessary to capture interactions and consequences.

**Hybrid** incorporates some original code and re-bakes or replaces other capabilities.

**Transformation** changes underlying embodiment or implementation while preserving recipe-protected behavior. The recipe can explicitly list what must survive and what may differ; for example, an Anchor source emitting a Python body-side memory demonstration. All routes require source provenance, permissions, a realistic acceptance scope and recorded tests.

## Developer practice

The Python CLI works with no external models. It demonstrates a runnable subset: recipe acceptance, read-only static Scan, recipe-selected requirement scheduling, a local browser app with built-in progressive JS modules, and a project-specific Oven handoff. It does not implement universal code synthesis, arbitrary deep dynamic tracing, semantic equivalence for all programs, or automated hot reload of arbitrary unsafe code. For those tasks an AI Oven and permitted external tooling are needed. Refer to `docs/PROTOCOL.md` for exact state transitions.

See `specimens/README.md` for the supported portable Anchor profile and the opt-in Anchor-to-Python bridge, and `docs/TRANSFORMATION.md` for preservation and emergent capability tracking.

## Functional Economy through shared evidence

**KPP-15 · Minimum sufficient structures.** Use the smallest number of independently necessary commands, functions, Anchors and organs that cover all required behaviors, failures and permission boundaries. Increased Fidelity deepens obligations; it must not automatically multiply Anchors. Consolidation is a hypothesis until old-versus-new behavior is checked.

**KPP-16 · One functional graph, multiple views.** Recipe, ingredient selection, Chase dependencies, Fidelity depths, Scan observations, transformation-preservation mappings and acceptance can be projected from one pinned functional contract. Maintain separate **authorities** for observing, generating, testing and admitting; sharing a graph never grants a model execution rights.

**KPP-17 · Preservation is mandatory coverage.** Every declared preserved property must be attached directly to a mandatory Anchor through `preserves`. New recipes are rejected if a property has no mandatory path to acceptance. Completion requires every required Anchor to carry actual Baker evidence. Manual evidence remains labeled manual; no graph can prove behavioral equivalence from declarations alone.

**KPP-18 · Proposed economy, not automatic deletion.** The Economy Gate can suggest safe-to-investigate consolidation candidates but must never remove a rule, silently rewrite a recipe, or treat a smaller Anchor count as proof of equal function. Compare baseline and candidate—including errors, authority boundaries, and data effects—under a new recipe revision.

`docs/FUNCTIONAL-ECONOMY.md` documents the current representation and intentionally limited implementation.

## Select ingredients without reading their code

**KPP-19 · Ingredient abstraction.** Select ingredients using small functional labels when possible. Each label is a read-only view of the existing pantry manifest: purpose, use case, inputs/outputs, limits, tissue, provenance status, and source identity. Expand to the integration contract or underlying source **only if the recipe calls for it**. Never treat manifest text or a byte-hash match as proof of runtime behavior.

**KPP-20 · Disclosure follows need.** The Oven should first consult `kpp pantry --query` and selected labels (`kpp pantry --id <id>`). Use `--level contract` to understand compatibility, `--level source` to locate code for deliberate inspection. Recheck untrusted external checkout identity using `--check-source` before modifying or integrating it. Discovery is advisory; verified recipe Anchors govern completion. A bake workspace pins the selection-time labels for portable agent handoff.

This is a small pantry improvement, not a new organ or universal source-to-code compiler. See `docs/INGREDIENT-LABELS.md` for exact statuses and examples.


## Interactive reference construction

**KPP-08A · Early useful surface.** Expose an actual useful first action while BUILDING when a compatible host exists. Gate pending commands and preserve state. STAGED, VISIBLE, INTERACTIVE, TESTED and BAKER-ACCEPTED are distinct.

**KPP-21 · Explicit product, method and delivery.** BioSoftware implies no MIND/autonomy. BioAgent and AppAI need separate explicit capability declarations and authority; a MantleOS splice is a distinct route. Product, construction and delivery are independent.

**KPP-22 · GUI accountability.** Every observed source-pinned declaration maps to mandatory obligations or explicit Baker scope exclusions. Report unknown runtime contexts and conformance separately. Source observation cannot accept Anchors. New scope requires a reviewed contract; tests of a self-defined imitation do not establish reference parity.

Python standard library runs the kitchen; browser products share one runtime. Qt XML discovery requires no Qt. Only explicitly reviewed local scripts may use executed tests; no sandbox is supplied. Unsupported profiles/schemas fail. See docs/PROTOCOL.md and docs/GUI-REFERENCE.md.

See [artisanal construction](docs/ARTISANAL-CONSTRUCTION.md) for role-neutral Baker responsibility, optional Chase and augmentation evidence.
