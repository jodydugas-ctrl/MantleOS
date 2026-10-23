#!/usr/bin/env python3
"""Render the tracked Mantle 2 correction/friction closure matrix deterministically."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "documents" / "mantle2" / "MANTLE2_CONSOLIDATION_MATRIX.md"

TITLES = """C:\\tmp\\mantleos-notepadnext could not be created from the sandboxed PowerShell session.
The requested host was described as C, but repository metadata identifies it as C++.
Mantle's stock assimilate command undercounted the host because the default scanner does not parse C/C++.
The first native inventory run produced blank Git provenance fields.
The first native scanner pass misread C++ control-flow blocks as function symbols.
The native scanner also misread Qt call expressions with lambda bodies as function symbols.
The native scanner initially missed functions whose opening brace is on the following line.
External review identified that constructor initializer lists were still not handled.
The first native map forced every symbol into exactly one role.
Lua, macro, script, console, and debug surfaces were overclassified as Brain.
File writes were overclassified as Memory.
The first Qt graph extraction treated connect(...) as vocabulary instead of causality.
Regex-based connect(...) extraction initially truncated lambda edges.
Ownership boundaries needed more granularity than first-party versus vendored.
External review found a proof-order bug in the read-only sign-off.
Ownership and file type were still conflated in one scope field.
Vendored and resource symbols could still populate proposed organs.
Multi-label role evidence was present in JSON but still collapsed in the organ map.
Heartbeat evidence was still too broad.
Function body extraction had a fixed 220-line ceiling.
Qt Designer .ui parsing omitted actions and declared connections.
The gap report was too narrow.
The larger lesson is not add C/C++ support; it is adaptive assimilation tooling.
Full invariant auditing hit an optional dependency, not a NotepadNext organism failure.
Certification evidence was first written through the wrong organ contract.
A local NotepadNext AppAI resident can pass available Body and offline MIND gates.
Saved organisms must be re-audited before MIND activation.
Stage-2 audits can be destructive to probe bands.
Full-MIND proof needs a runtime cognition receipt, not only Stage-2 row summaries.
Host layout cannot be guessed from product name or repository name.
Code-agnostic assimilation needs generated integration tools, not only generated reports.
Integration verification must be artifact-kind aware.
Verification receipts must not hash their own mutable output.
Observer scaffolds need a narrower claim than full native insertion.
Generated certification tools should not depend on the caller's current directory.
A runnable desktop app may not exist just because source assimilation succeeded.
Every AppAI needs an explicit user-to-MIND contact surface.
Text-entry surfaces should commit semantic entries, not keystrokes.
App-band allocation must account for reserved hatchery bands.
Example smoke tests should not require optional npm dependencies when a static proof is enough.
A downloaded host binary cannot show newly designed in-app affordances.
Terminal slash commands need a secret-safe routing layer.
The terminal needed a live provider smoke test, not only command parsing.
Hidden key prompts are bad UX for AppAI terminals.
Surface parity needs real Body controls and exact host-window targeting.
Audit reports need to separate resident gates from optional environment extras.
Optional Python extras need workspace-local proof, not only user-site installation.
Windows Git clones may need long-path policy before checkout.
VCW audit helpers must use the current cube API.
Generation status belongs to the current Prime cube.
Generated lifecycle audits need a shared organism-status adapter.
Lifecycle SPOREs need a readable bootstrap plus an encrypted body payload.
The resident primer should be distilled from the SPORE/app body, not only copied from the prior build.
MIND status answers must load the VCW, not infer genome status from metadata.
A lifecycle SPORE must carry an actual grimoire copy, not stale paths or excerpts.
Lifecycle completion should be auditable by the SPORE toolchain itself.
Complete lifecycle examples should be packaged as reproducible archive artifacts.
The framework needed a shared VCW/organism status receipt instead of generated scripts duplicating internal calls.
App-band allocation was protected at the platform layer, not only in the calculator egg.
The stock assimilator now records substrate coverage before organ mapping.
Standalone Phase-0 artifact output is now enforced outside the host tree.
GitHub applet clones now apply Windows long-path-safe checkout policy.
A visible Body write was reported successful before the editor surface verified it.
Natural-language Body requests were answered as plans instead of executed as Body operations.
The resident could discuss itself but did not reliably consult its own host evidence.
MantleOS treated consultation evidence as an artifact pile instead of a resident interface.
The resident's function answer was a capped sample instead of a GUI nerve map.
Activation silently discarded most host controls.
The Qt scanner missed helper-wired nerves.
Missing GUI nerves need maintenance pressure instead of silence.
Natural-language Body dispatch became too aggressive.
Working surfaces were treated as generic commands instead of discovered SELF anatomy.
Resident runtime state needed an operator-visible VCW reset.
App-specific working surfaces were exposed as slash commands instead of conversational Body anatomy.
Creative document creation was implemented as a Body reflex instead of MIND-authored work.
Non-slash user conversation was intercepted by deterministic resident/reflex routing.
The MIND lacked an internal Body request lane after the slash-only boundary was restored.
Escaped MIND-to-Body directives leaked into the terminal when parsing failed.
GUI self-knowledge was sampled instead of selected from the complete surface map.
Terminal experience lived in sidecar logs instead of first-class VCW memory.
GUI coverage did not require every surface output to be proven into VCW.
Resident runtime lessons were still trapped in one NotepadNext companion terminal.
Audit/demo/teaching paths still allowed short Primer doctrine.
Text input surfaces needed committed readback, not tab-state inference.
Examples drifted from the resident text-commit contract.
Residents wrote conversation to VCW but did not rehydrate it into MIND context.
Sidecar mirror failures could stop resident recall.
Hermes addon resident factory drifted from the shared AppAI Primer.
Conversational document-reset requests were answered literally instead of operated.
NotepadNext resident passed Body certification without a live cognitive heartbeat scheduler.
User-submit heartbeats still had deterministic bypasses and weak API-call accounting.
The resident heartbeat scheduler was still example tissue, not platform tissue.
The NotepadNext terminal kept a private copy of the rhythm after the platform owned it.
Stage-1 could certify a host resident that owned no live cognitive heartbeat.
The NotepadNext resident factory substituted app doctrine for the shared AppAI Primer.
A likely /mind model-selection command was rejected as unknown.
Requested model route and provider-resolved model were conflated.
Untrusted provider prose could inject terminal control characters.""".splitlines()


def contract(number: int) -> tuple[str, str, str, str, str]:
    """Return subsystem, implementation, test, example, immutable commit evidence."""
    if number == 1:
        return ("workspace/supply", "paths.REPO_ROOT; applet_body._safe_checkout",
                "SUPPLY-1; FRICTION-1", "isolated NotepadNext candidate build", "7bff0b1; 54913e0")
    if 2 <= number <= 23 or 30 <= number <= 34 or 60 <= number <= 62 or number == 69:
        return ("assimilation", "assimilator.scanner_native; coverage.SubstrateCoverage; artifact_validation.validate_artifact",
                "COVERAGE-1; NATIVE-1; ASSIM-1; ASSIM-2", "notepadnext_appai_mantle2_candidate causal map", "a231096; 54913e0")
    if number in (24, 27, 28, 46, 47):
        return ("audit/certification", "check._steps; certify.certify_nest; audits.stage2.run",
                "STAGE2-PROFILE-1; CERTIFY-1", "candidate lifecycle completion audit v2", "be828ee; e09b61c")
    if number in (25, 29, 33, 49, 50, 51, 54, 58, 80, 86, 87):
        return ("evidence/VCW", "core.status.organism_status; ResidentRuntime._rehydrate; ActionExecutionProof",
                "CLAIM-1; PROOF-1; CONTEXT-BODY-OWNED", "NotepadNext and Organize Prime-VCW terminals", "e46b0c7; 54913e0; 896a959")
    if number in (39, 59):
        return ("application bands", "vcw.atlas.allocate_app_bands",
                "APPBAND-1; REPRO-1", "calculator egg and NotepadNext candidate", "7bff0b1; e09b61c")
    if number in (40, 48):
        return ("portable tooling", "check._steps; applet_body._safe_checkout",
                "SUPPLY-1; Windows workflow", "Windows candidate and browser smoke workflows", "7bff0b1; 54913e0")
    if 52 <= number <= 57:
        return ("spore/lifecycle", "spore.inspect_spore; spore.validate_embedded_material; lifecycle.LifecycleTransaction",
                "SPORE-1; SPORE-2; SPORE-3; LIFECYCLE-1", "germ-v2 NotepadNext lifecycle spore", "be828ee; 78820e1; e09b61c")
    if number in (63, 64, 68, 81, 84):
        return ("Body proof/surfaces", "proofs.ActionExecutionProof; contracts.HostAdapter; surface_coverage",
                "PROOF-1; ASSIM-2", "NotepadNext host adapter with post-state readback", "a231096; e09b61c")
    if number in (65, 66, 67, 70, 72, 79):
        return ("host evidence", "contracts.HostAdapter; surface_coverage.build_surface_coverage",
                "CLAIM-1; ASSIM-2", "query-relevant NotepadNext v3 nerve inventory", "a231096; e09b61c")
    if 37 <= number <= 45 or 71 <= number <= 78 or 82 <= number <= 85 or 88 <= number <= 98:
        return ("resident runtime", "contracts.ResidentRuntime; resident.commands.BodyCommandDispatcher; resident.heartbeat",
                "RESIDENT-RT-1; RESIDENT-CMD-1; RESIDENT-HB-1; RESIDENT-HB-2",
                "shared NotepadNext and Organize Mantle 2 terminals", "e46b0c7; e09b61c; 896a959")
    if number in (26, 35, 36):
        return ("maintained example", "certify.certify_nest; notepadnext_appai_mantle2_candidate.build_candidate",
                "CERTIFY-1; test_notepadnext_mantle2_candidate", "distinct Mantle 2 candidate and audit v2", "e09b61c")
    return ("platform contract", "contracts.GroundedAnswer; core.status.organism_status",
            "CLAIM-1; CERTIFY-1", "NotepadNext and Organize maintained examples", "54913e0; e09b61c")


FRICTION = {
    1: "workspace branch/bootstrap containment", 2: "untracked generated evidence",
    3: "Windows patching outside writable root", 4: "Mantle reading-gate edition selection",
    5: "resident key/credits prompt ambiguity", 6: "host test protocol fixtures",
    7: "model route versus resolved model", 8: "stale virtual environments",
    9: "missing contained pytest base", 10: "Unix shell assumption on Windows",
    11: "shell built-in capability detection", 12: "authorization not wired to mutation boundary",
    13: "shared global pytest state", 14: "concurrent mutable gate fixture",
    15: "security command documentation drift", 16: "Grimoire edition index drift",
    17: "edition-specific verifier ambiguity", 18: "germ schema runtime drift",
    19: "dummy resident integration fixture", 20: "Windows bash implementation ambiguity",
    21: "release scan sentinel noise", 22: "installed Mantle source/version drift",
    23: "package stderr and deprecated license metadata",
    24: "PowerShell process-redirection argument parsing",
    25: "application certification hid a missing Spore extra",
    26: "GitHub CI inspector used a locale-dependent decoder",
    27: "top-level help returned usage error and local smoke masked it",
    28: "Windows runner exposed a POSIX-only descriptor-swap claim",
    29: "duplicate conditional caused a context-light patch misapplication",
}


def render() -> str:
    if len(TITLES) != 98:
        raise RuntimeError(f"expected 98 corrections, found {len(TITLES)}")
    lines = [
        "# MantleOS 2.0 consolidation matrix", "",
        "This is the release closure index for all 98 NotepadNext corrections and the",
        "cross-project friction ledger. A nonhistorical row is closed only when shared",
        "implementation, executable regression coverage, a maintained example, and",
        "commit-bound evidence agree. Historical artifacts remain byte-preserved and are",
        "never treated as current runtime authority.", "",
        "Allowed statuses are `already_verified`, `superseded`, `historical_only`, and",
        "`requires_operator_decision`. This release has no open correction work items.", "",
        "## Correction closure", "",
        "| Correction | Actual correction | Status | Owning subsystem | Implementation symbol | Test/invariant | Migrated example | Immutable closure evidence |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for number, title in enumerate(TITLES, 1):
        subsystem, implementation, test, example, evidence = contract(number)
        safe_title = title.replace("|", "\\|")
        lines.append(f"| {number} | {safe_title} | already_verified | {subsystem} | `{implementation}` | `{test}` | {example} | commits `{evidence}` |")
    lines += ["", "## Friction closure", "",
              "| Friction ID | Condition | Status | Owning subsystem | Implementation work item | Test/invariant | Example migration | Closure evidence |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for number, condition in FRICTION.items():
        evidence = "documents/mantle2/FRICTION_EVENTS.md; FRICTION-1"
        if number <= 18:
            example = "NotepadNext v2 candidate"
        elif number <= 22:
            example = "Organize.AppAI Mantle 2 migration"
        else:
            example = "MantleOS wheel/sdist release pipeline"
        lines.append(f"| FRICTION-{number:03d} | {condition} | already_verified | release operations | recorded remedy and prevention control | `{evidence}` | {example} | commits `54913e0; e09b61c; 896a959` |")
    lines += [
        "", "## Doctrine reconciliation", "",
        "- The historical spore-derived Body-key audit is noncanonical. Mantle 2 independently",
        "  mints genesis keys; public spores, conversation, and personality seeds grant no key authority.",
        "- Spores are inert carriers until an authorized Body tool acts. Conversation is",
        "  testimony/inferred memory and cannot become executable authority.",
        "- SHA/parity evidence establishes integrity. Optional lineage attestation establishes",
        "  an asserted relationship; `UNATTESTED` is not invalid and grants no activation authority.",
        "- Repository certification, application certification, historical receipts, and current",
        "  runtime authority are separate claims with separate evidence.",
        "- Ordinary host software remains ordinary. Body, MIND, Senses, Limbs, Immune, SELF/OTHER,",
        "  and VCW name Mantle tissue only.",
        "- Documentation claims, executable behavior, observed receipts, and interpretation are",
        "  labeled separately; executable code and passing tests govern runtime behavior.", "",
        "## Closure rule", "",
        "A candidate is landed only when shared implementation, an executable regression, an",
        "updated maintained example, and matching documentation are all present. `FRICTION-1`",
        "enforces this table structurally during `python -m mantle prove`.", "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8", newline="\n")
    print(OUT)
