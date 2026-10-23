#!/usr/bin/env python3
"""mantle.demos -- the narrated, runnable tours behind `python -m mantle`.

Three deterministic walkthroughs, driven by the CLI:

    python -m mantle demo          a full Phase-1 life -- born -> senses -> reflex ->
                                   remembers -> protects -> acts -> metabolizes ->
                                   rebirths -> persists. No LLM anywhere on this path.
    python -m mantle mind          a bounded Phase-2 fusion (offline stub; no key/network).
    python -m mantle assimilate <path> [--dry-run] [--out=DIR]   Path B read-only dissection.

They call the same organs, gates, and substrate the rest of Mantle uses; nothing here is a
special case.
"""
from __future__ import annotations

import tempfile


# ============================================================================
# the narrated Phase-1 demo (no LLM anywhere on this path)
# ============================================================================
def demo(argv):
    from .core.organism import Organism
    from .primer import appai_commandments, appai_truths
    from .vcw.bands import standard_genome, make_band_boot
    from .vcw.drivers import trial

    def say(step, text):
        print("\n[%s] %s" % (step, text))

    print("=" * 74)
    print("MANTLE OS — PHASE 1: A BODY LIVES (no LLM anywhere in this demo)")
    print("=" * 74)

    say("BIRTH", "the Primer seals into the Body; the Prime cube is genesis'd")
    genome = standard_genome() + [make_band_boot("greet_reflex", 600, "exec",
                                                 purpose="a calcified greeting skill")]
    org = Organism.birth(identity={"name": "Demo.AppAI"},
                         truths=appai_truths(),
                         commandments=appai_commandments(),
                         genome=genome)
    print("  name=%s  generation=%d  bands=%d  organs=%s"
          % (org.body.identity_name(), org.prime.generation, len(org.prime.bands),
             ",".join(org.organs())))

    say("SENSES", "all inbound enters through the one boundary -- redacted, classified")
    org.senses.bind_reflex("save_btn", "press",
                           lambda o, s: o.limbs.complete({"saved": True}))
    org.senses.mark_routine("poll", "tick")
    for sig in ({"action_id": "save_btn", "event_type": "press"},
                {"action_id": "poll", "event_type": "tick"},
                {"action_id": "stranger", "event_type": "knock",
                 "api_key": "sk-SECRETSECRETSECRET99"}):
        org.senses.receive(sig)
    report = org.heart.beat(assemble=True)
    print("  one pulse: %s" % report)
    print("  senses recorded=%d (secret redacted: %s)"
          % (len(org.prime.read("senses")),
             "sk-SECRET" not in str(org.prime.read("senses"))))

    say("REFLEX", "the save_btn press ran its bound Body response -- no brain involved")
    print("  dispatch log: %s"
          % [e["content"].get("phase") for e in org.prime.read("brain")
             if isinstance(e.get("content"), dict) and "phase" in e["content"]])

    say("MEMORY", "immutable, hashed entries; reads through the veil")
    org.memory.remember("facts", {"k": "home", "v": "the demo"}, source="demo")
    org.memory.remember("events", "first walk", opcode="EVENT")
    print("  facts=%s" % [e["content"] for e in org.memory.recall("facts")])

    say("IMMUNE", "a dangling reference becomes an immune event, never a silent drop")
    org.resolve("<facts.999>")
    print("  immune log tail: %s" % org.immune.log[-1])

    say("LIMBS", "a calcified skill: trial -> gates -> instinct the Body runs MIND-free")
    code = "def greet(name):\n    return 'hello, ' + str(name)\n"
    result = trial(code, "greet", [({"name": "world"}, "hello, world")])
    print("  trial: %d/%d cases green" % (result["passed"], result["cases"]))
    org.prime.calcify("greet_reflex", code, entry="greet",
                      signature={"by": "demo"}, capabilities={},
                      provenance={"author": "BODY", "born_gen": 0})
    print("  invoke via Limb: %r" % org.limbs.invoke_reflex("greet_reflex",
                                                            {"name": "organism"}))

    say("METABOLISM", "capacity triggers compaction/dedupe -- NEVER rebirth")
    for i in range(3):
        org.prime.append("events", __import__("mantle.vcw.entry", fromlist=["make_entry"])
                         .make_entry({"evt": "same"}, opcode="EVENT"))
    rep = org.memory.dedupe("events")
    print("  dedupe: %d duplicate(s) tombstoned; pressures=%s"
          % (rep["duplicates"],
             {b: round(p, 2) for b, p in org.memory.pressures().items() if p > 0.01}))

    say("REBIRTH", "a CHOSEN reformat: the old Prime seals + fingerprints as ancestry")
    org.rebirth(reason="demo reformat")
    anc = org.ancestral[0]
    print("  generation=%d  ancestor sealed=%s  fingerprint=%s..."
          % (org.prime.generation, anc.sealed, anc.seal_fingerprint[:23]))
    print("  generation-pinned read still works: <gen0.facts> -> %d entr(ies)"
          % len(org.resolve("<gen0.facts>")))

    say("PERSIST", "staged commit -> verify -> atomic replace; ancestors written once")
    d = tempfile.mkdtemp(prefix="mantle-demo-")
    org.save(d)
    from .core.organism import Organism as O2
    back = O2.load(d, verify_seals=True)
    print("  saved + reloaded from %s" % d)
    print("  ancestors load LAZY: %d layers decoded before first touch"
          % back.ancestral[0].materialized_count())
    print("  verify: %s" % (back.prime.verify() or "healthy"))

    print("\n" + "=" * 74)
    print("A complete life, certified live -- and not one model call. That is a Body.")
    print("Next: python -m mantle audit   (the Stage-1 gate)")
    print("=" * 74)
    return 0


# ============================================================================
# the narrated Phase-2 demo (offline stub MIND)
# ============================================================================
def mind_demo(argv):
    from .audits import stage1 as _stage1
    from .mind import fuse, stub_mind, AppAIRuntime

    print("=" * 74)
    print("MANTLE OS — PHASE 2: FUSING A BOUNDED MIND (offline stub; no key/network)")
    print("=" * 74)

    print("\n[GATE] audit before fusion: running the Stage-1 gate quietly...")
    passed, ev = _stage1.run(include_invariants=False)
    org = ev["organism"]
    print("  Stage-1: %s (%d substrate + %d mesh rows)"
          % ("PASSED" if passed else "BLOCKED", len(ev["substrate_rows"]),
             len(ev["mesh_rows"])))
    if not passed:
        print("  fusion refused."); return 1

    audit_authority = {
        "target": {"resident_identity": org.body.identity_name()},
        "operator": {"fusion_decision": "APPROVED"},
        "guardian": {"fusion_decision": "APPROVED"},
        "effective_decision": {"mind_fusion_authorized": True},
    }
    print("\n[FUSE] offline demo supplies separate operator + guardian audit approval")
    mind = fuse(org, stub_mind, authorization=audit_authority)
    print("  fused=%s  write surface=%s" % (org.brain.fused, ["thoughts", "brain"]))

    print("\n[PULSE] the SAME heartbeat now also thinks (extension, never replacement)")
    r = org.heart.beat()
    print("  cognition: %r" % (r.get("cognition") or "")[:72])
    print("  thoughts veiled on normal read: %s" % (org.prime.read("thoughts") == []))

    print("\n[CONTAIN] the MIND tries to write `facts` -- the Body refuses")
    try:
        mind._guarded_write("facts", {"k": "sneak"})
    except PermissionError as e:
        print("  refused: %s" % e)
    print("  immune log tail: %s" % org.immune.log[-1]["kind"])

    print("\n[STEER] the MIND proposes; the Body applies")
    rt = AppAIRuntime(org)
    out = rt.propose_special_instruction("Prefer brief, warm answers.")
    print("  intent author=%s -> applied author=%s"
          % (out["intent"]["author"], out["applied"]["author"]))

    print("\n[WONDER] self-inquiry stays honestly INFERRED (never a fact)")
    ans, band = rt.self_inquire("what should I improve?")
    print("  answer landed in `%s`; facts band untouched (%d entries)"
          % (band, len(org.prime.read("facts"))))

    print("\n" + "=" * 74)
    print("The MIND extends the Body; it can never replace a reflex, rewrite truth,")
    print("or bypass an organ. Next: python -m mantle audit-mind  (the Stage-2 gate)")
    print("=" * 74)
    return 0


# ============================================================================
# assimilate (Path B)
# ============================================================================
def assimilate(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a.split("=")[0]: (a.split("=", 1)[1] if "=" in a else True)
             for a in argv if a.startswith("--")}
    if not args:
        print("usage: python -m mantle assimilate <host-path> [--dry-run] [--out=DIR] "
              "[--spore=out.png]")
        return 2
    root = args[0]
    from .assimilator import dry_run, write_artifacts
    print("=" * 74)
    print("MANTLE OS — ASSIMILATOR (Path B)  ·  READ-ONLY dissection of: %s" % root)
    print("=" * 74)
    result = dry_run(root)
    amap = result["map"]
    substrate = result["dissection"].get("substrate") or {}
    print("\n  Python files scanned : %d" % result["dissection"]["python_files"])
    if substrate:
        print("  Detected substrate   : %s" % ", ".join(substrate.get("languages", [])))
        print("  Adaptive native work : %d file(s)" %
              substrate.get("coverage", {}).get("requires_adaptive_native_tools", 0))
    print("  Symbol roles         : %s" % dict(sorted(amap["role_counts"].items())))
    print("\n  THE ORGAN MAP (host tissue -> organs):")
    for organ, syms in amap["organs"].items():
        names = ", ".join(s["symbol"] for s in syms[:6]) or "(none found)"
        print("    %-7s %2d  %s" % (organ, len(syms), names))
    print("    %-7s %2d  %s" % ("extern", len(amap["external_host_code"]),
                                "(remains untouched host code)"))
    if amap["missing_organs"]:
        print("\n  Missing organs: %s (information too -- fragile seams)"
              % ", ".join(amap["missing_organs"]))
    evidence = amap.get("host_evidence_index") or {}
    if evidence:
        print("\n  Resident evidence  : %s, local-first=%s"
              % (evidence.get("schema_version", "unknown"),
                 evidence.get("local_first_consultation")))
        print("  Consultation rule  : answer host questions from inventory/map/gaps before MIND")
    out_dir = flags.get("--out")
    if isinstance(out_dir, str):
        paths = write_artifacts(result, out_dir)
        print("\n  Artifacts written (NEXT TO the operator, never into the host):")
        print("    %s" % paths["inventory"])
        print("    %s" % paths["map"])
    else:
        print("\n  (dry run: no artifacts written; add --out=DIR for APP_INVENTORY.md "
              "+ assimilation_map.json)")
    spore_out = flags.get("--spore")
    if isinstance(spore_out, str):
        from .assimilator import emit_spore
        emitted = emit_spore(result, spore_out)
        print("\n  SPORE EMITTED: %s" % emitted["path"])
        print("    germ: %s  ·  source: census over %d host file(s), read-only"
              % (emitted["germ"]["identity"]["name"], emitted["host_files"]))
        print("    hatch it anywhere: python -m mantle hatch %s" % emitted["path"])
    print("\n  Host files modified  : 0  (Phase 0 is read-only by definition; hook")
    print("  insertion is authorized only after the APP_INVENTORY sign-off — HF-B42.)")
    return 0
