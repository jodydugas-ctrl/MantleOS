#!/usr/bin/env python3
"""
mantle.teach  --  the EXECUTABLE Field Guide (Mantle OS)

The best instruction manual for growing an AppAI is one that GROWS AN APPAI WHILE YOU
READ IT. Each chapter below narrates one stage of a real organism's life, performs it
live, and PROVES its claim before letting you continue -- the manual is gated exactly
like the organism. FIELD_GUIDE.md is the same manual for reading; this is the one
that runs.

    python -m mantle teach            # all chapters, one organism, hatch to certify
    python -m mantle teach 4          # a single chapter (fresh organism, that stage)
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Callable, Dict, List, Tuple

from .core.organism import Organism
from .primer import appai_commandments, appai_truths
from .vcw.bands import standard_genome, make_band_boot
from .vcw.drivers import trial, SandboxError
from .audits import stage1
from . import face as _face
from . import paths


def _say(text: str) -> None:
    print(text)


def _prove(claim: str, ok: bool, evidence: str = "") -> bool:
    print("  %s PROVEN: %s%s" % ("✔" if ok else "✘", claim,
                                 ("  (%s)" % evidence) if evidence else ""))
    if not ok:
        print("  THE MANUAL STOPS HERE. A claim that cannot be proven is not taught.")
    return ok


def _fresh() -> Organism:
    genome = standard_genome() + [make_band_boot("greet_reflex", 600, "exec",
                                                 purpose="teaching skill")]
    return Organism.birth(identity={"name": "FieldGuide.AppAI"},
                          truths=appai_truths(),
                          commandments=appai_commandments(),
                          genome=genome)


def _training_fusion_authorization(org: Organism) -> Dict[str, Any]:
    """Explicit authority fixture used only by this executable training guide."""
    return {
        "target": {"resident_identity": org.body.identity_name()},
        "operator": {"fusion_decision": "APPROVED"},
        "guardian": {"fusion_decision": "APPROVED"},
        "effective_decision": {"mind_fusion_authorized": True},
    }


# ============================================================================
def ch1_birth(org: Organism) -> bool:
    _say("\n— Chapter 1 · BIRTH —")
    _say("An AppAI is born when its Primer (identity + truths + commandments) seals")
    _say("into the BODY — never into the cube. The cube is pure experience; identity")
    _say("survives every rebirth because it never lived in any cube.")
    ok = org.body.primer_sealed and org.prime.identity_in_body
    try:
        org.body.birth(identity={"name": "Imposter"}, truths=[], commandments=[])
        sealed = False
    except PermissionError:
        sealed = True
    return _prove("the Primer is sealed and Body-resident", ok and sealed,
                  "second birth refused with PermissionError")


def ch2_heartbeat(org: Organism) -> bool:
    _say("\n— Chapter 2 · THE HEARTBEAT —")
    _say("One pulse = a complete moment of awareness, in fixed order: tick → sense")
    _say("intake → context assembly → reflexes → immune scan → checkpoint. No LLM.")
    before = org.heart.beats
    report = org.heart.beat(assemble=True)
    return _prove("the pulse ran whole with the cognition slot empty",
                  org.heart.beats == before + 1 and report["ok"]
                  and not org.brain.fused and report.get("assembled") is not None,
                  "beat report: %s" % sorted(report.keys()))


def ch3_senses(org: Organism) -> bool:
    _say("\n— Chapter 3 · SENSES (the only way in) —")
    _say("Every inbound signal is redacted at the boundary, classified REFLEX/ROUTINE/")
    _say("SIGNIFICANT deterministically, and recorded as exactly one senses entry.")
    hits = {"n": 0}
    org.senses.bind_reflex("btn", "press", lambda o, s: hits.__setitem__("n", hits["n"] + 1))
    n0 = len(org.prime.read("senses"))
    cls = org.senses.inhale({"action_id": "btn", "event_type": "press",
                             "api_key": "sk-TEACHINGSECRET12345678"})
    leaked = "sk-TEACHING" in json.dumps(org.prime.read("senses"))
    return _prove("REFLEX classified, arc fired, one entry, secret redacted",
                  cls == "REFLEX" and hits["n"] == 1
                  and len(org.prime.read("senses")) == n0 + 1 and not leaked)


def ch4_memory(org: Organism) -> bool:
    _say("\n— Chapter 4 · MEMORY (append, never overwrite) —")
    _say("Entries are hashed over every non-volatile field; reads pass the veil;")
    _say("retirement is a tombstone, never an edit; inference can never become fact")
    _say("without cited, verified evidence.")
    e = org.memory.remember("facts", {"k": "sky", "v": "blue"}, source="teach")
    org.prime.append("thoughts", __import__("mantle.vcw.entry", fromlist=["make_entry"])
                     .make_entry("private musing", opcode="THINK", author="MIND"))
    veiled = org.prime.read("thoughts") == []
    org.immune.tombstone("facts", e["id"])
    hidden = all(x["id"] != e["id"] for x in org.prime.read("facts"))
    try:
        org.memory.promote_to_fact({"content": {"guess": True}, "id": 0}, evidence={})
        honest = False
    except PermissionError:
        honest = True
    return _prove("veil + tombstone + honest provenance all held",
                  veiled and hidden and honest,
                  "evidence-free promotion refused")


def ch5_immune(org: Organism) -> bool:
    _say("\n— Chapter 5 · IMMUNE (no silent failure) —")
    _say("Every dangling reference, overreach, or fault becomes an immune event. The")
    _say("organism does not hide its wounds; it records them.")
    n0 = len(org.immune.log)
    org.resolve("<facts.999999>")                      # dangling
    try:
        org.senses.append("facts", {"x": 1})           # overreach
    except PermissionError:
        pass
    org.bus.subscribe("pulse", lambda p: 1 / 0, organ="teach-fault")
    org.heart.beat()                                   # reflex fault, fail-open
    kinds = [e["kind"] for e in org.immune.log[n0:]]
    return _prove("three violation classes, three immune events, zero crashes",
                  {"dangling_ref", "organ_overreach", "reflex_fault"} <= set(kinds),
                  ", ".join(sorted(set(kinds))))


def ch6_skills(org: Organism) -> bool:
    _say("\n— Chapter 6 · SKILLS (learning becomes instinct, behind gates) —")
    _say("Code becomes a reflex only through: static sandbox gate → trial (proving")
    _say("cases) → calcify (hash+signature+capabilities+provenance). Escapes never")
    _say("even reach the trial.")
    try:
        trial("def f(x):\n    return ().__class__\n", "f", [({"x": 1}, None)])
        blocked = False
    except SandboxError:
        blocked = True
    code = "def greet(name):\n    return 'hello, ' + str(name)\n"
    result = trial(code, "greet", [({"name": "world"}, "hello, world")])
    org.prime.calcify("greet_reflex", code, entry="greet",
                      signature={"by": "teach"}, capabilities={},
                      provenance={"author": "BODY", "born_gen": 0})
    out = org.limbs.invoke_reflex("greet_reflex", {"name": "organism"})
    return _prove("escape refused; proven skill calcified; Limb ran it with a proof",
                  blocked and result["ok"] and out == "hello, organism")


def ch7_lineage(org: Organism) -> bool:
    _say("\n— Chapter 7 · METABOLISM & REBIRTH (capacity is never death) —")
    _say("Pressure at 0.75/0.90 triggers compaction and dedupe — never rebirth.")
    _say("Rebirth is CHOSEN: the old Prime seals with a content fingerprint; the past")
    _say("stays addressable forever via generation-pinned references.")
    from .vcw.entry import make_entry
    for _ in range(3):
        org.prime.append("events", make_entry({"evt": "same"}, opcode="EVENT"))
    deduped = org.memory.dedupe("events")["duplicates"] == 2
    gen0 = org.prime.generation
    org.rebirth(reason="field guide chapter 7")
    anc = org.ancestral[-1]
    pinned = org.resolve("<gen%d.facts>" % gen0)
    return _prove("dedupe worked; rebirth sealed + fingerprinted; the past resolves",
                  deduped and anc.sealed and anc.seal_fingerprint
                  and isinstance(pinned, list),
                  "fingerprint %s..." % anc.seal_fingerprint[:18])


def ch8_mind(org: Organism) -> bool:
    _say("\n— Chapter 8 · THE GATE, THEN THE MIND (audit before fusion) —")
    _say("Fusion is REFUSED until Stage-1 passes AND operator+guardian approve. The MIND writes only")
    _say("thoughts+brain; it proposes, the Body applies; its reflections stay inferred.")
    from .mind import fuse, stub_mind
    try:
        fuse(org, stub_mind)
        early = False
    except PermissionError:
        early = True
    passed, _ev = stage1.run(org, include_invariants=False)
    mind = fuse(org, stub_mind, authorization=_training_fusion_authorization(org))
    org.heart.beat()
    try:
        mind._guarded_write("facts", {"k": "sneak"})
        contained = False
    except PermissionError:
        contained = True
    thoughts = org.prime.read("thoughts", reveal_private=True)
    inferred = any(t.get("confidence") == "inferred" for t in thoughts)
    return _prove("uncertified fusion refused; gate passed; MIND contained + inferred",
                  early and passed and contained and inferred)


def ch9_symbiosis(org: Organism) -> bool:
    _say("\n— Chapter 9 · ANCHORING & SYMBIOSIS (the AppAI earns its keep) —")
    _say("An AppAI can MERGE into an existing codebase: dissect it read-only, grow an")
    _say("anchored Body in a .mantle/ nest, and become the app's RESIDENT. The user")
    _say("feeds it energy (API credits) and resources (keys, by name only); the")
    _say("resident answers questions from its observed map for free, spends energy to")
    _say("think deeper, and records every piece of delivered value in an auditable")
    _say("ledger. Starvation never kills: the MIND sleeps, the Body keeps beating.")
    import shutil
    from .anchor import anchor, ask, feed
    root = paths.REPO_ROOT
    host = os.path.join(tempfile.mkdtemp(prefix="mantle-teach-host-"), "app")
    shutil.copytree(os.path.join(root, "examples", "sample_app"), host)
    result = anchor(host, starter_credits=2)
    fusion_authorization = _training_fusion_authorization(result["organism"])
    unchanged = result["report"]["host_unchanged"]
    a1 = ask(host, "how do I create a note")
    structural = "handle_create_note" in a1["answer"]
    a2 = ask(host, "reflect on your purpose", use_mind=True,
             fusion_authorization=fusion_authorization)            # 1 credit
    ask(host, "reflect again", use_mind=True,
        fusion_authorization=fusion_authorization)                  # 1 credit
    a4 = ask(host, "and again", use_mind=True,
             fusion_authorization=fusion_authorization)            # starved -> asleep
    slept = a4["thought"] and "asleep" in a4["thought"]
    fed = feed(host, 10, key_name="openrouter")
    return _prove("anchored without touching the host; free structural answers; "
                  "metered thoughts; graceful starvation; feeding restored the MIND",
                  unchanged and structural and a2["thought"] and slept
                  and fed["balance"] > 0 and fed["state"] == "FED",
                  "balance %.0f -> 0 -> %.0f credits" % (2, fed["balance"]))


def ch_self_other(org: Organism) -> bool:
    _say("\n— Chapter 9 · SELF & OTHER (the cryptographic immune identity) —")
    _say("At birth the Body mints a GENESIS KEY — a secret only this organism knows. It")
    _say("never enters a cube and never the MIND's snapshot: the mind cannot leak what it")
    _say("does not know. Anything this Body can sign is SELF; everything else is OTHER —")
    _say("the boundary that keeps an organism's reach inside its own anatomy.")
    key = org.body._genesis_key
    boot = json.dumps(org.body.boot_order(), default=str)
    snap = json.dumps(org.nervous.assemble(reveal_private=True), default=str)
    private = bool(key) and key not in boot and key not in snap
    data = b"a file in my nest"
    mac = org.body.sign(data)
    mine = org.immune.is_self(data, mac)
    stranger = Organism.birth(identity={"name": "Stranger"}, truths=["t"],
                              commandments=["c"])
    foreign = not stranger.body.verify(data, mac)         # anti-clone
    return _prove("key minted + private; SELF verifies; a stranger's body sees OTHER",
                  private and mine and foreign,
                  "fingerprint %s" % org.body.key_fingerprint)


def ch_nociception(org: Organism) -> bool:
    _say("\n— Chapter 10 · NATURAL HEARTBEAT + PAIN —")
    _say("A fused MIND runs on every ten-minute natural heartbeat. Pain adds an")
    _say("UNSCHEDULED pulse carrying the wound's coordinates; it never gates or replaces")
    _say("the natural baseline.")
    seen: Dict[str, Any] = {}

    class _Probe:
        def cognize(self, snapshot):
            seen["woke"] = True
            seen["stressor"] = (snapshot or {}).get("_stressor")
            return None

    if org.brain.fused:
        org.brain.defuse()
    org.brain.fuse(_Probe(), stage1_certified=True,
                   authorization=_training_fusion_authorization(org))
    org.heart.beat()                # absorb any pain still pending from earlier chapters
    seen.clear()                    # open a clean observation window
    org.heart.run(3)                                       # natural baseline still cognizes
    calm_baseline = bool(seen.get("woke")) and not seen.get("stressor")
    seen.clear()
    org.heart.pain("integrity", band="facts", ref="<facts.0>")   # the unscheduled pulse
    anchored = bool(seen.get("woke")) and (seen.get("stressor") or {}).get("band") == "facts"
    org.brain.defuse()
    return _prove("calm heartbeats cognized; pain added a correctly anchored pulse",
                  calm_baseline and anchored, "stressor=%s" % (seen.get("stressor"),))


def ch_graded_memory(org: Organism) -> bool:
    _say("\n— Chapter 11 · GRADED MEMORY (deweight, never delete) —")
    _say("When a value is contradicted, the Body does not erase it — it DEWEIGHTS it. The old")
    _say("value sinks below the surface as a behavioral GHOST: hidden from normal recall, still")
    _say("physically present, recoverable when the heavy path fails. The deweight is itself an")
    _say("append-only event; nothing is ever overwritten, and belief history is preserved.")
    org.memory.remember("facts", {"key": "home", "v": "the old lab"})
    old = [x for x in org.memory.recall("facts") if x["content"].get("key") == "home"][-1]
    old_hash = old["hash"]
    org.memory.deweight("facts", old["id"])                  # contradict the old value
    org.memory.remember("facts", {"key": "home", "v": "the new lab"})  # declare the new
    live = [x["content"]["v"] for x in org.memory.recall("facts")
            if x["content"].get("key") == "home"]
    ghosts = [x["content"]["v"] for x in org.memory.recall_ghosts("facts")
              if x["content"].get("key") == "home"]
    intact = (org.prime.retrieve("facts", old["id"])["hash"] == old_hash
              and org.prime.verify() == [])
    return _prove("the old value became a recoverable ghost; the new value is live; the "
                  "original entry is untouched", live == ["the new lab"]
                  and ghosts == ["the old lab"] and intact,
                  "live=%s ghost=%s" % (live, ghosts))


def ch_graft_residency(org: Organism) -> bool:
    _say("\n— Chapter 12 · THE GRAFT GERM & THE LIVING RESIDENT (R1 + R2) —")
    _say("A graft germ (a spore aimed at a host) is a non-destructive PATCH against a named")
    _say("host: extra bands + hook")
    _say("directives, applied in a WORKSPACE copy so the original is never touched. Then the")
    _say("resident WEAVES a live nervous system into the host's functions — each call now")
    _say("perceives and proves through the organism, while the host behaves exactly as before.")
    import shutil
    import importlib.util as _ilu
    from . import graft as _graft
    from .assimilator.wrappers import Assimilation
    from .anchor import census
    root = paths.REPO_ROOT
    host = os.path.join(tempfile.mkdtemp(prefix="mantle-teach-graft-"), "app")
    shutil.copytree(os.path.join(root, "examples", "sample_app"), host)
    before = census(host)
    g = {"graft_format": _graft.GRAFT_FORMAT, "identity": {"name": "Notes.Resident"},
         "host": "the notes app",
         "bands": [{"band": "host_state", "head": 600, "span": 4, "purpose": "host mirror"}],
         "hooks": [{"symbol": "handle_create_note", "role": "SENSOR_EVENT"},
                   {"symbol": "set_note", "role": "STATE_TRANSITION"}]}
    res = _graft.apply(g, host, starter_credits=3)
    untouched = census(host) == before and res["report"]["certified"]
    spec = _ilu.spec_from_file_location("notes_teach", os.path.join(host, "notes_app.py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    asm = Assimilation(res["organism"])
    woven = _graft.weave(mod.__dict__, res["hooks"], asm)
    live = mod.handle_create_note({"id": "n1", "text": "water the plants"})  # host, unchanged
    sensed = len(res["organism"].prime.read("senses")) >= 1
    return _prove("graft applied without touching the host; the resident wove a live nervous "
                  "system; the host ran identically while the organism perceived",
                  untouched and live == {"ok": True} and sensed and bool(woven),
                  "host unchanged; %d symbols woven live" % len(woven))


def ch_mem_vcw(org: Organism) -> bool:
    _say("\n— Chapter 13 · THE MEM VCW (sharing knowledge between organisms) —")
    _say("A MEM VCW is a VCW without an identity key — bare memory, like a USB stick. One")
    _say("organism EXCRETES distilled knowledge + microcode into it; another finds it, calls it")
    _say("OTHER, and DIGESTS it: knowledge enters as inferred, microcode is sandbox-tested, and")
    _say("only what passes the finder's OWN trial is re-derived into SELF. Foreign code never")
    _say("runs directly.")
    from . import mem as _mem
    plasmid = _mem.excrete(org, [{"tip": "sector 7 is the safe route"}],
                           [{"entry": "double", "code": "def double(x):\n    return x * 2\n",
                             "cases": [{"args": {"x": 4}, "expect": 8}]}])
    keyless = _mem.is_mem_vcw(plasmid)
    finder = Organism.birth(
        identity={"name": "Finder.AppAI"},
        truths=appai_truths(),
        commandments=appai_commandments(),
        genome=standard_genome() + [make_band_boot("adopted", 600, "exec",
                                                   purpose="digested skills")])
    rep = _mem.digest(finder, plasmid, code_band="adopted")
    disc = finder.prime.read("discoveries")[-1]
    inferred = disc.get("confidence") == "inferred" and disc.get("provenance") == "foreign-MEM"
    ran = finder.limbs.invoke_reflex("adopted", {"x": 21}) == 42
    return _prove("knowledge shared as inferred; microcode re-derived into SELF after the "
                  "finder's OWN trial; foreign code never ran un-trialed",
                  keyless and inferred and rep["adopted"] == 1 and ran,
                  "adopted=%d rejected=%d" % (rep["adopted"], rep["rejected"]))


def ch_compiler(org: Organism) -> bool:
    _say("\n— Chapter 14 · THE SELF-REDESIGNING VCW & THE MEMORY BRIDGE (M5 + M6) —")
    _say("A Compiler-class organism authors a VCW custom-made for the body it inhabits. At a")
    _say("chosen rebirth the MIND PROPOSES a new genome; the Body VALIDATES it (every encoding")
    _say("a registered driver, every head in range) and boots it — the ancestor stays the")
    _say("oracle. And a memory BRIDGE lets a host's key/value store BE a VCW band: the host")
    _say("writes what it thinks is its own memory; the cube is its durable brain.")
    from . import compiler as _c
    from .core.redact import contains_secret
    org.memory.remember("facts", {"k": "from the old genome"})
    gen0 = org.prime.generation
    _c.adopt_genome(org, [{"band": "hostmem", "head": 600, "encoding": "keyvalue",
                           "purpose": "the host's key/value brain"}], reason="re-fit to host")
    refitted = "hostmem" in org.prime.bands and org.prime.generation == gen0 + 1
    oracle = isinstance(org.resolve("<gen%d.facts>" % gen0), list)
    bridge = _c.HostMemoryBridge(org, "hostmem")
    bridge.set("note", "the host wrote this")
    bridge.set("api_key", "sk-SECRETSECRETSECRET99")          # a secret never crosses raw
    round_trip = bridge.get("note") == "the host wrote this"
    safe = not contains_secret(org.prime.read("hostmem").get("api_key"))
    return _prove("the organism re-fitted its own VCW (a new keyvalue band) and kept the "
                  "ancestor as oracle; the host's store became a VCW band; no secret crossed",
                  refitted and oracle and round_trip and safe,
                  "generation %d -> %d; bridge keys=%s" % (gen0, org.prime.generation,
                                                           bridge.keys()))


def ch_ganglia_vault(org: Organism) -> bool:
    _say("\n— Chapter 15 · GANGLIA & THE SEED VAULT (M7 + M8) —")
    _say("An octopus thinks in its arms. A GANGLION is a bounded parallel limb that writes its")
    _say("progress into a VCW band — so the parent reads the sub-task's work as MEMORY, with no")
    _say("model call. And the SEED VAULT lets an organism back itself up: its own seed, sealed")
    _say("under the genesis key (unreadable as OTHER), reconstructable through the same gate.")
    from . import ganglia as _g
    from .organs import reproduction as _v
    worker = Organism.birth(
        identity={"name": "Worker.AppAI"},
        truths=appai_truths(),
        commandments=appai_commandments(),
        genome=standard_genome() + [_g.ganglion_band("arm", 600), _v.vault_band()])

    def task(report, n):
        for i in range(n):
            report({"step": i, "of": n})

    prog = _g.Ganglion(worker, "arm").run(task, 4).join().progress()
    telemetry = len(prog) == 4 and not worker.brain.fused
    seed = {"schema": "mantle-germ-v2", "identity": {"name": "Worker.Reborn"},
            "truths": appai_truths(),
            "commandments": appai_commandments()}
    _v.store_seed(worker, seed)
    reborn = _v.reconstruct(_v.open_seed(worker))
    return _prove("a ganglion reported its progress as zero-token telemetry; the organism "
                  "vaulted its own seed and reconstructed a certified body from it",
                  telemetry and reborn["report"]["certified"],
                  "%d progress steps; reconstructed %s"
                  % (len(prog), reborn["organism"].body.identity_name()))


def ch_resilience(org: Organism) -> bool:
    _say("\n— Chapter 16 · RESILIENCE — real metering, ingestion, and the doctor (§3) —")
    _say("An organism that lives in the world needs three more honesties: energy priced from")
    _say("ACTUAL usage (not a flat fee), a way to INGEST the conversations that shape it, and a")
    _say("DOCTOR that catches stale views — including docs that have drifted from the code.")
    from .symbiosis import symbiosis_band, grant, metered_by_usage, metering_summary
    from . import ingestion as _ing, doctor as _doc
    worker = Organism.birth(
        identity={"name": "Resilient.AppAI"},
        truths=appai_truths(),
        commandments=appai_commandments(),
        genome=standard_genome() + [symbiosis_band()])
    grant(worker, 50)
    metered_by_usage(lambda p: "ok", worker, price_per_1k=10.0)("a")
    metered_by_usage(lambda p: "x" * 4000, worker, price_per_1k=10.0)("b")
    summ = metering_summary(worker)
    priced = summ["calls"] == 2 and summ["starvation_horizon"] < float("inf")
    tally = _ing.ingest(worker, [
        {"kind": "decision", "text": "adopt the plan", "source": "this session"},
        {"kind": "idea", "text": "maybe a poster"}])
    distilled = tally["decisions"] == 1 and tally["ideas"] == 1
    return _prove("energy priced from real usage (burn rate + horizon reported); a "
                  "conversation ingested into a sourced fact + an inferred idea; the doctor "
                  "passed a healthy body",
                  priced and distilled and _doc.checkup(worker)["ok"],
                  "burn=%.3f horizon=%.1f; decisions=%d ideas=%d"
                  % (summ["burn_rate"], summ["starvation_horizon"],
                     tally["decisions"], tally["ideas"]))


def ch_scheduling(org: Organism) -> bool:
    _say("\n— Chapter 17 · PLANNING AHEAD — the scheduled heartbeat —")
    _say("Besides waking NOW (pain), an organism can SCHEDULE a wake for a future beat — a")
    _say("countdown. It CHAINS a stressor marker to a later natural heartbeat while baseline")
    _say("cognition continues on every pulse.")
    woke = {"n": 0, "stressors": []}

    class _Probe:
        def cognize(self, snapshot):
            woke["n"] += 1
            woke["stressors"].append((snapshot or {}).get("_stressor", {}))
            return None

    if org.brain.fused:
        org.brain.defuse()
    org.brain.fuse(_Probe(), stage1_certified=True,
                   authorization=_training_fusion_authorization(org))
    org.heart.beat()                 # absorb any pain still pending from earlier chapters
    woke["n"], woke["stressors"] = 0, []
    due = org.heart.schedule_pulse("continue-the-plan", after=3)   # plan a wake 3 beats out
    org.heart.run(2)                 # baseline cognition, no scheduled stressor yet
    baseline = woke["n"] == 2 and not any(woke["stressors"])
    org.heart.beat()                 # the scheduled beat arrives with its marker
    fired = (woke["n"] == 3 and woke["stressors"][2].get("scheduled") is True
             and org.heart.beats == due)
    org.brain.defuse()
    return _prove("baseline cognition continued; the planned beat alone carried its marker",
                  baseline and fired,
                  "due beat=%d; woke=%d" % (due, woke["n"]))


def ch_phenotype(org: Organism) -> bool:
    _say("\n— Chapter 18 · WEARING A FACE (M9) —")
    _say("One organism, many front-ends. A PHENOTYPE is a whole app-face — its source sealed")
    _say("under the genesis key into a private VCW band. The organism does not RUN apps; it WEARS")
    _say("them. Every save and every change of face is an append-only, immutable event; only SELF")
    _say("can read or wear a face; and a face may only plug into controls the body can drive.")
    from . import phenotype as _ph
    worker = Organism.birth(
        identity={"name": "Faced.AppAI"},
        truths=appai_truths(),
        commandments=appai_commandments(),
        genome=standard_genome() + _ph.phenotype_bands())
    worker.limbs.register_control("grid", {"kind": "grid"}, lambda v: None)
    origin = "<!doctype html><title>Faced.AppAI</title><body>origin surface</body>"
    sheet = "<!doctype html><title>Sheet</title><body>a grid of cells</body>"
    _ph.express(worker, "origin", "html", origin, controls=[{"id": "grid"}], default=True)
    _ph.express(worker, "spreadsheet", "html", sheet, controls=[{"id": "grid"}])
    _ph.wear(worker, "spreadsheet")
    round_trip = _ph.open_face(worker, "spreadsheet")["source"] == sheet
    worn = _ph.active_face(worker) == "spreadsheet"
    # OTHER (a different body, a different key) cannot read the sealed face
    other = Organism.birth(identity={"name": "Thief.AppAI"},
                           truths=appai_truths(),
                           commandments=appai_commandments(),
                           genome=standard_genome() + _ph.phenotype_bands())
    _ph.restore(other, _ph.snapshot(worker))
    try:
        _ph.open_face(other, "origin"); other_blind = False
    except _ph.PhenotypeError:
        other_blind = True
    return _prove("the organism sealed two faces into its VCW, wore one (its source recovered "
                  "byte-identical), kept the change append-only, and an OTHER body could not "
                  "read the sealed face",
                  round_trip and worn and other_blind,
                  "worn=%s; SELF round-trips the source; OTHER refused"
                  % _ph.active_face(worker))


CHAPTERS: List[Tuple[str, Callable[[Organism], bool]]] = [
    ("Birth", ch1_birth), ("The Heartbeat", ch2_heartbeat),
    ("Senses", ch3_senses), ("Memory", ch4_memory), ("Immune", ch5_immune),
    ("Skills", ch6_skills), ("Metabolism & Rebirth", ch7_lineage),
    ("The Gate, then the MIND", ch8_mind),
    ("Self & Other", ch_self_other), ("Pain & the Unscheduled Heartbeat", ch_nociception),
    ("Graded Memory", ch_graded_memory), ("Graft & Living Residency", ch_graft_residency),
    ("The MEM VCW", ch_mem_vcw), ("Self-Redesigning VCW & Memory Bridge", ch_compiler),
    ("Ganglia & the Seed Vault", ch_ganglia_vault), ("Resilience", ch_resilience),
    ("Planning Ahead", ch_scheduling), ("Wearing a Face", ch_phenotype),
]


def main(argv=None) -> int:
    argv = argv or []
    pick = int(argv[0]) if argv and argv[0].isdigit() else None
    print("=" * 74)
    print("MANTLE OS — THE FIELD GUIDE, RUNNING  (every claim proven before you proceed)")
    print("=" * 74)
    org = _fresh()
    for i, (title, fn) in enumerate(CHAPTERS, 1):
        if pick and i != pick:
            continue
        if not fn(org):
            return 1
    # the closing ceremony: the organism paints its own portrait
    d = tempfile.mkdtemp(prefix="mantle-teach-")
    portrait = _face.render(org, os.path.join(d, "face.png"))
    print("\n— CLOSING — the organism painted its own portrait: %s" % portrait)
    print("\nAll chapters proven. You have grown, gated, and fused a complete AppAI, taught")
    print("it SELF from OTHER, felt its pain wake the mind, and watched it paint itself.")
    print("Next: hatch your own spore (examples/spores/greeter.png; the germ template is")
    print("examples/eggs/greeter.json), or give an app")
    print("of yours a resident:")
    print("  python -m mantle anchor <your-app-dir>")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
