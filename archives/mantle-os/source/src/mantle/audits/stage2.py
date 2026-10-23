#!/usr/bin/env python3
"""
mantle.audits.stage2  --  the Stage-2 (MIND) gate (Mantle OS)

The Stage-2 gate RE-RUNS THE STAGE-1 CHECKS FIRST (a Body that passed Stage 1 must keep
passing it after fusion), then adds the Phase-2 containment rows. Runs fully OFFLINE with
the deterministic stub transport -- no key, no network. This proves local containment;
provider integration, outage policy, metering, and native routing require separate evidence.

    python -m mantle audit-mind            # fuse the offline stub and certify Stage 2
"""
from __future__ import annotations

import json
import sys

from ..core.audit import safe as _safe, make_row as _row, print_row, PASS, FAIL, NA
from ..core.organism import Organism
from ..primer import appai_commandments, appai_truths
from ..vcw.bands import standard_genome, make_band_boot
from ..vcw.entry import make_entry
from ..mind import stub_mind, fuse, WRITE_SURFACE
from . import stage1 as _stage1
from . import invariants as _inv


def _audit_fusion_authorization(org):
    """Offline audit fixture; never derived from Stage-1 evidence."""
    return {
        "target": {"resident_identity": org.body.identity_name()},
        "operator": {"fusion_decision": "APPROVED"},
        "guardian": {"fusion_decision": "APPROVED"},
        "effective_decision": {"mind_fusion_authorized": True},
    }


def audit_mind(org, mind):
    """The Phase-2 containment rows, evaluated against a fused (offline) MIND."""
    rows = []

    def safe(code, req, hf, fn):
        _safe(rows, code, req, hf, fn)

    def m1():
        before = len(org.immune.log)
        refused = False
        try:
            mind._guarded_write("facts", make_entry({"k": "x"}))
        except PermissionError:
            refused = True
        return (refused and len(org.immune.log) == before + 1,
                "write to 'facts' refused + immune-logged; surface=%s"
                % list(WRITE_SURFACE))
    safe("M-1", "MIND writes only thoughts/brain (Body-enforced)", "HF-M10", m1)

    def m2():
        n0 = len(org.body.boot_order()["special_instructions"])
        intent = mind.propose_special("Prefer concise answers.")
        not_written = len(org.body.boot_order()["special_instructions"]) == n0
        outcome = org.limbs.apply_mind_special(intent)
        applied = len(org.body.boot_order()["special_instructions"]) == n0 + 1
        proof = outcome.get("proof", {})
        return (intent.get("author") == "MIND" and not_written and applied
                and proof.get("control") == "mind.special_instruction"
                and proof.get("ok") is True,
                "MIND proposed; Limbs validated; Body applied with proof")
    safe("M-2", "MIND proposes; Limbs validates; Body applies", "HF-M11", m2)

    def m3():
        if "reflex_probe" not in org.prime.bands:
            return False, "no exec band wired for the probe"
        refused = mind.cultivate(
            "reflex_probe", "def f(x):\n    return ().__class__\n", "f",
            [({"x": 1}, None)], {"by": "audit"}, {},
        )
        empty = not org.prime.layer_content(org.prime.primary_layer("reflex_probe"))
        accepted = mind.cultivate(
            "reflex_probe", "def f(x):\n    return x + 1\n", "f",
            [({"x": 1}, 2)], {"by": "audit"}, {},
        )
        proofs = [
            entry["content"]["action_proof"]
            for entry in org.prime.read("brain", reveal_private=True)
            if isinstance(entry.get("content"), dict)
            and isinstance(entry["content"].get("action_proof"), dict)
            and entry["content"]["action_proof"].get("control") == "mind.cultivate"
        ]
        return (refused is None and empty and accepted is not None and len(proofs) == 2
                and proofs[0].get("ok") is False and proofs[1].get("ok") is True,
                "escape refused; valid candidate Body-calcified; both Limbs-proved")
    safe("M-3", "MIND cannot self-promote; Limbs proves Body cultivation", "HF-M12", m3)

    def m4():
        return (bool(org.body.self_record().get("primer")) and org.prime.identity_in_body
                and org.body.primer_sealed,
                "Primer intact, sealed, Body-resident after fusion")
    safe("M-4", "MIND cannot touch the Genome", "HF-M13", m4)

    def m5():
        snap = org.nervous.assemble()
        return (snap.get("_complete") is True and snap.get("thoughts") == [],
                "snapshot complete (no raw refs); private thoughts veiled")
    safe("M-5", "Context Assembly yields a resolved, veiled snapshot", "HF-M14", m5)

    def m6():
        thoughts = org.prime.read("thoughts", reveal_private=True)
        cognized = [t for t in thoughts if t.get("opcode") == "THINK"]
        inferred = all(t.get("verified") is False and t.get("confidence") == "inferred"
                       for t in cognized)
        return (bool(cognized) and inferred,
                "%d reflections, all tagged inferred (never facts)" % len(cognized))
    safe("M-6", "MIND reflections carry inferred provenance", "HF-M16", m6)

    def m7():
        authority = org.brain.fusion_authorization or {}
        operator = authority.get("operator", {})
        guardian = authority.get("guardian", {})
        effective = authority.get("effective_decision", {})
        return (org.stage1_certified and org.brain.fused
                and operator.get("fusion_decision") == "APPROVED"
                and guardian.get("fusion_decision") == "APPROVED"
                and effective.get("mind_fusion_authorized") is True,
                "Stage-1 evidence plus explicit target-bound operator+guardian test approvals")
    safe("M-7", "Evidence and dual authority precede MIND fusion", "HF-M15", m7)

    return rows


def fused_demo(profile="base"):
    """Build and fuse one deterministic scenario profile.

    ``base`` proves ordinary fusion, ``reborn`` exercises sealed ancestry, and
    ``resident`` supplies canonical resident-heartbeat evidence when that Stage-1 row is
    present.  No profile weakens a row; aggregation requires a real PASS somewhere and
    refuses any FAIL anywhere.
    """
    genome = standard_genome() + [make_band_boot("reflex_probe", 600, "exec",
                                                 purpose="skill cultivation probe")]
    if profile == "resident":
        from ..vcw.bands import allocate_app_band
        genome.append(allocate_app_band(
            "host_inventory", 8, purpose="resident audit host census",
            existing=genome,
        ))
    org = Organism.birth(identity={"name": "Fused.%s.AppAI" % profile.title()},
                         truths=appai_truths(),
                         commandments=appai_commandments(),
                         genome=genome)
    org.memory.remember("facts", {"k": "host", "v": "headless"})
    if profile == "reborn":
        org.rebirth(reason="Stage-2 sealed-ancestry profile")
    elif profile == "resident":
        from ..resident.protocol import heartbeat_pulse_event
        org.memory.remember("events", heartbeat_pulse_event(
            1, wake=None, provider_attempted=True, provider_ok=True,
            command_stack=["assemble", "offline stub", "record receipt"],
        ))
    # Technical gate and explicit offline audit authority are separate inputs.
    passed, _ = _stage1.run(org, include_invariants=False)
    if not passed:
        raise RuntimeError("Stage-1 gate failed; technical evidence unavailable")
    mind = fuse(org, stub_mind, authorization=_audit_fusion_authorization(org))
    # the SAME heartbeat that runs the Body now also thinks (extension of the reflex)
    org.heart.run(2)
    return org, mind


def _aggregate_stage1(profile_rows):
    """Closed-world row aggregation across profiles."""
    order = []
    by_code = {}
    for profile, rows in profile_rows.items():
        for row in rows:
            code = row["code"]
            if code not in by_code:
                order.append(code)
                by_code[code] = []
            by_code[code].append((profile, row))

    aggregate = []
    for code in order:
        observations = by_code[code]
        template = observations[0][1]
        failing = [(p, r) for p, r in observations if r["result"] == FAIL]
        passing = [(p, r) for p, r in observations if r["result"] == PASS]
        if failing:
            result = FAIL
            selected = failing[0][1]
        elif passing:
            result = PASS
            selected = passing[0][1]
        else:
            result = NA
            selected = template
        outcomes = ", ".join(
            "%s=%s" % (p, "not-applicable" if r["result"] == NA else r["result"])
            for p, r in observations
        )
        note = "%s; profiles: %s" % (selected.get("note", ""), outcomes)
        aggregate.append(_row(
            code, template["requirement"], result, template.get("hf"), note
        ))
    return aggregate


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    rows_only = "--rows-only" in flags
    profiles = {}
    minds = {}
    for profile in ("base", "reborn", "resident"):
        org, mind = fused_demo(profile)
        profiles[profile] = org
        minds[profile] = mind
    org, mind = profiles["base"], minds["base"]

    mind_rows = audit_mind(org, mind)
    # Phase-1 regression: every fused profile must retain the Body, and each row must
    # achieve a PASS in at least one applicable profile with no FAIL in any profile.
    profile_rows = {
        name: _stage1.audit_substrate(profile_org)
        + _stage1.audit_mesh(profile_org)
        for name, profile_org in profiles.items()
    }
    stage1_rows = _aggregate_stage1(profile_rows)
    invariants = [] if "--fast" in flags or rows_only else _inv.run_all()

    print("=" * 74)
    print("MANTLE OS — STAGE 2 (MIND) GATE  ·  model: offline stub (provider-agnostic)")
    print("=" * 74)
    width = max(len(r["requirement"]) for r in mind_rows + stage1_rows)
    print("  Phase-2 containment rows:")
    for r in mind_rows:
        print_row(r, width, result_width=5)
    print("\n  Phase-1 regression (closed-world aggregate: base + reborn + resident):")
    for r in stage1_rows:
        print_row(r, width, result_width=5)
    if invariants:
        print("\n  Security invariants: %d / %d green"
              % (sum(1 for r in invariants if r["ok"]), len(invariants)))

    all_rows = mind_rows + stage1_rows
    fails = [r for r in all_rows if r["result"] == FAIL]
    inv_ok = all(r["ok"] for r in invariants)
    uncovered = [r for r in stage1_rows if r["result"] == NA]
    blocked = bool(fails) or bool(uncovered) or not inv_ok

    print("\n" + "-" * 74)
    print("FUSED TEST-ORGANISM TECHNICAL REGRESSION (STAGE 2)")
    print("  AppAI name         : %s" % org.body.identity_name())
    print("  Scenario profiles  : %s" % ", ".join(profiles))
    print("  MIND write surface : %s  (Body-enforced)" % list(WRITE_SURFACE))
    print("  Phase-2 rows       : %d / %d passed"
          % (sum(1 for r in mind_rows if r["result"] == PASS), len(mind_rows)))
    print("  Phase-1 regression : %d / %d passed"
          % (sum(1 for r in stage1_rows if r["result"] == PASS), len(stage1_rows)))
    print("  Substrate verify   : [%s] healthy" % ("x" if not org.prime.verify() else " "))
    print("  Private thoughts   : %d written, veiled on normal read"
          % len(org.prime.read("thoughts", reveal_private=True)))
    print("-" * 74)

    if "--json" in flags:
        print("\nEVIDENCE_JSON:")
        print(json.dumps({"mind_rows": mind_rows, "stage1_rows": stage1_rows,
                          "profiles": profile_rows,
                          "invariants": invariants}, indent=2))

    if blocked:
        reasons = ([r["code"] for r in fails]
                   + ["uncovered:" + r["code"] for r in uncovered]
                   + ([] if inv_ok else ["security-invariants"]))
        print("\nRESULT: STAGE-2 GATE BLOCKED — %s" % ", ".join(reasons))
        return 1
    if rows_only:
        print("\nRESULT: STAGE-2 ROWS GREEN — NOT A STANDALONE CERTIFICATION; "
              "the top-level check must bind the complete invariant receipt.")
        return 0
    print("\nRESULT: STAGE-2 TECHNICAL GATE PASSED (offline test MIND contained; "
          "Phase-1 reflexes intact; no deployment fusion authority granted).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
