#!/usr/bin/env python3
"""
mantle.anchor  --  ANCHORING: an AppAI takes residence in a codebase (Mantle OS)

Residency procedure is owned by the Mantle runtime docs and code. The Grimoire is the VCW
software profile, not a separate residency manual. Dissection here REUSES the single
canonical scanner (assimilator.dry_run -> scan_project); anchor adds no scanning of its own.

This is Path B made symbiotic -- the framework's primary act. An AppAI MERGES into an
existing application: it dissects the host read-only, grows an anchored Body with a
VCW cube and a nervous system in a `.mantle/` nest INSIDE the host's directory, and
becomes that codebase's RESIDENT -- a creature whose senses are the app's organ map,
whose memory accumulates everything it learns about its home, and whose usefulness
earns it energy from the user.

THE ANCHORING LAW: anchoring never modifies a single host file. The nest is additive
(`.mantle/` only); the dissection is AST-only; the census proves it (every host
file's fingerprint is recorded before and verified after). Do-no-harm is not a hope,
it is a checked invariant.

What the user gets: an app that suddenly has a resident intelligence --
    python -m mantle anchor <host>                    # the merge ceremony
    python -m mantle ask <host> "how do I ...?"       # ask the resident (free:
                                                        #   deterministic, from the map)
    python -m mantle ask <host> --mind "..."          # deeper answers (spends energy)
    python -m mantle feed <host> --credits=20         # the symbiotic loop
    python -m mantle vitals <host>                    # ledger, state, portrait

What the AppAI gets: an anchored body, a purpose, and a way to earn its keep.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional

from .core.organism import Organism
from .assimilator import answer_from_host_evidence, dry_run, write_artifacts
from .assimilator.organ_map import propose_genome
from .hatchery import incubate, HatchError
from .primer import appai_commandments, appai_truths
from . import symbiosis as sym
from . import face as _face

NEST = ".mantle"


class AnchorError(Exception):
    """The merge was refused. The host is untouched (that part is guaranteed anyway)."""


# ---------------------------------------------------------------------------
# the host census: proof that anchoring touched nothing
# ---------------------------------------------------------------------------
def census(host: str) -> Dict[str, str]:
    """Fingerprint every host file OUTSIDE the nest: path -> sha256."""
    out: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(host):
        dirnames[:] = [d for d in dirnames if d not in (NEST, ".git", "__pycache__")]
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, host)] = hashlib.sha256(f.read()).hexdigest()
    return out


# ---------------------------------------------------------------------------
# the merge ceremony
# ---------------------------------------------------------------------------
def anchor(host: str, name: Optional[str] = None,
           starter_credits: float = 5.0,
           extra_bands: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Dissect (read-only) -> birth the resident -> remember the host -> the Stage-1
    gate -> nest. Returns {organism, report}. The host census is verified unchanged.
    `extra_bands` (boot-sector dicts) lets a graft add app bands to the resident."""
    host = os.path.abspath(host)
    if not os.path.isdir(host):
        raise AnchorError("host %r is not a directory" % host)
    nest_dir = os.path.join(host, NEST)
    if os.path.exists(os.path.join(nest_dir, "organism.json")):
        raise AnchorError("a resident is already anchored here (%s). Feed it, ask it, "
                          "or remove the nest to re-anchor." % nest_dir)
    before = census(host)

    # 1. DISSECT (read-only, AST-only -- the assimilator's Phase 0)
    result = dry_run(host)
    amap = result["map"]
    host_name = name or (os.path.basename(host).replace("_", ".").title() + ".Resident")

    # 2. BIRTH the resident THROUGH THE HATCHERY -- one birth path for every body
    # (egg, vault, spore, resident). The resident therefore carries the default origin
    # face and its own seed in the vault, like every other organism. The egg's app
    # bands are the host-shaped bands from the atlas + the symbiosis ledger.
    host_bands = [b for b in propose_genome(amap["role_counts"]) if 550 <= b["head"] <= 749]
    resident_egg = {
        "schema": "mantle-germ-v2",
        "identity": {"name": host_name, "host": host,
                     "purpose": "resident nervous system of this application"},
        "truths": appai_truths(["The host is my body's home; I never harm it."]),
        "commandments": appai_commandments([
            "Do no harm to the host.",
            "Earn your keep.",
        ]),
        "genome": host_bands + [sym.symbiosis_band()] + list(extra_bands or []),
    }
    try:
        org = incubate(resident_egg)["organism"]
    except HatchError as e:
        raise AnchorError("the hatchery refused the resident: %s" % e)

    # 3. REMEMBER the host. The scanner's output is deterministic OBSERVATION, so it
    #    may enter `facts` honestly: observed, sourced, verified-by-construction.
    org.memory.remember("facts", {
        "host_map": {o: [{"symbol": s["symbol"], "module": s["module"],
                          "line": s["line"], "role": s["role"]} for s in syms]
                     for o, syms in amap["organs"].items()},
        "external_count": len(amap["external_host_code"]),
        "python_files": result["dissection"]["python_files"]},
        opcode="OBSERVED", source="assimilation-scan", verified=True)
    org.memory.remember("facts", {"missing_organs": amap["missing_organs"]},
                        opcode="OBSERVED", source="assimilation-scan", verified=True)
    org.memory.remember("discoveries", {
        "host_evidence_index": amap.get("host_evidence_index", {}),
        "consultation_rule": (
            "answer host questions from local Phase-0 evidence before generic MIND chat"
        )},
        opcode="OBSERVED", source="assimilation-scan", verified=True)

    # 4. FIRST MEAL: the user's starter grant opens the symbiosis
    sym.grant(org, starter_credits, source="anchor-ceremony",
              note="starter energy; usefulness earns more")

    # 5. THE GATE ran inside the hatchery (the same Stage-1 audit every Body faces);
    #    a refused gate raised HatchError above.

    # 6. NEST: everything lives in .mantle/ -- and nowhere else
    os.makedirs(nest_dir, exist_ok=True)
    org.save(nest_dir)
    write_artifacts(result, nest_dir, allow_host_nest=True)  # APP_INVENTORY.md + map JSON
    _face.render(org, os.path.join(nest_dir, "face.png"))
    sym.record_value(org, "anchored: dissected %d files into the organ map"
                     % result["dissection"]["python_files"],
                     evidence={"organs": {o: len(s) for o, s in amap["organs"].items()}})
    org.save(nest_dir)

    # 7. DO-NO-HARM, PROVEN: every host file identical to the pre-anchor census
    after = census(host)
    if before != after:
        raise AnchorError("HOST CHANGED DURING ANCHORING -- this must never happen")
    report = {"resident": host_name, "nest": nest_dir,
              "host_files": len(before), "host_unchanged": True,
              "certified": org.stage1_certified,
              "organ_map": {o: len(s) for o, s in amap["organs"].items()},
              "starter_credits": starter_credits}
    return {"organism": org, "report": report}


# ---------------------------------------------------------------------------
# the resident
# ---------------------------------------------------------------------------
def resident(host: str) -> Organism:
    nest_dir = os.path.join(os.path.abspath(host), NEST)
    if not os.path.exists(os.path.join(nest_dir, "organism.json")):
        raise AnchorError("no resident anchored at %s (run: python -m mantle "
                          "anchor %s)" % (host, host))
    return Organism.load(nest_dir, verify_seals=True)


def _load_map(host: str) -> Dict[str, Any]:
    with open(os.path.join(os.path.abspath(host), NEST, "assimilation_map.json")) as f:
        return json.load(f)


_STOP = frozenset("how do i the a an to of in is what where which my this app use run "
                  "does can you it for with and or".split())


def _answer_from_map(question: str, amap: Dict[str, Any]) -> str:
    """The FREE answer: deterministic, from observed structure -- reflex before
    reasoning. Structural questions get structural answers; no model, no energy."""
    if amap.get("host_evidence_index"):
        return answer_from_host_evidence(question, amap)
    tokens = [t for t in re.findall(r"[a-z_]+", question.lower()) if t not in _STOP]
    scored: List[tuple] = []
    for organ, syms in amap["organs"].items():
        for s in syms:
            hay = ("%s %s %s" % (s["symbol"], s["module"], s["role"])).lower()
            score = sum(2 if t in s["symbol"].lower() else 1
                        for t in tokens if t in hay)
            if score:
                scored.append((score, organ, s))
    scored.sort(key=lambda x: -x[0])
    lines: List[str] = []
    if scored:
        lines.append("From my map of this host (observed, not guessed):")
        for _score, organ, s in scored[:6]:
            lines.append("  • %s — `%s` at %s:%d  [%s tissue]"
                         % (s["role"].replace("_", " ").lower(), s["symbol"],
                            s["module"], s["line"], organ))
        lines.append("Those are the places this lives. Wrap them, call them, or read "
                     "them — the map is in %s/assimilation_map.json." % NEST)
    else:
        lines.append("A structural overview of my host (observed):")
        for organ, syms in amap["organs"].items():
            if syms:
                lines.append("  • %-7s %d symbol(s): %s" % (
                    organ, len(syms), ", ".join(s["symbol"] for s in syms[:4])))
        if amap.get("missing_organs"):
            lines.append("  • missing tissue: %s (fragile seams worth knowing about)"
                         % ", ".join(amap["missing_organs"]))
        lines.append("Start with the heart symbols above — they are how this app runs.")
    return "\n".join(lines)


def ask(host: str, question: str, use_mind: bool = False,
        model=None, cost_per_call: float = 1.0,
        fusion_authorization: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Ask the resident. The question enters through Senses (the only way in); the
    structural answer is a free Body reflex from the observed map; `use_mind` adds a
    metered reflection (energy is SPENT first -- the symbiosis is real). Every answer
    is recorded as delivered value; the conversation persists in the nest."""
    org = resident(host)
    amap = _load_map(host)
    org.senses.inhale({"action_id": "resident", "event_type": "question",
                       "question": question})
    answer = _answer_from_map(question, amap)
    thought = None
    if use_mind:
        from .mind import fuse, stub_mind
        if not org.stage1_certified:
            from .audits import stage1
            passed, ev = stage1.run(org, include_invariants=False)
            if not passed:
                org.immune_event("fusion_refused", {
                    "reason": "resident Stage-1 gate failed",
                    "fails": ev.get("fails", [])})
                thought = "(the MIND is asleep: Stage-1 gate refused fusion: %s)" % (
                    ", ".join(ev.get("fails", [])) or "uncertified")
        if org.stage1_certified:
            try:
                mind = fuse(org, sym.metered(model or stub_mind, org, cost_per_call),
                            authorization=fusion_authorization)
                thought = mind.think(org.nervous.assemble(),
                                     question="You are the resident AppAI of the host "
                                              "application at %s. The user asks: %s\n"
                                              "Context (your observed map and memory) is "
                                              "attached." % (host, question))
            except (PermissionError, sym.StarvationError) as e:
                thought = "(the MIND is asleep: %s)" % e
            finally:
                if org.brain.fused:
                    org.brain.defuse()
    org.limbs.complete({"answered": question[:80]})
    sym.record_value(org, "answered: %s" % question[:80],
                     evidence={"mind": bool(use_mind and thought)})
    nest_dir = os.path.join(os.path.abspath(host), NEST)
    org.save(nest_dir)
    return {"answer": answer, "thought": thought,
            "balance": sym.balance(org), "state": sym.metabolic_state(org)}


def feed(host: str, credits: float, key_name: Optional[str] = None,
         note: str = "") -> Dict[str, Any]:
    """The user's half of the symbiosis."""
    org = resident(host)
    sym.grant(org, credits, source="user", key_name=key_name, note=note)
    nest_dir = os.path.join(os.path.abspath(host), NEST)
    org.save(nest_dir)
    return {"balance": sym.balance(org), "state": sym.metabolic_state(org),
            "ledger": sym.ledger(org)}


def vitals(host: str, portrait: Optional[str] = None) -> Dict[str, Any]:
    """The resident's condition: ledger, metabolic state, band pressures, portrait."""
    org = resident(host)
    nest_dir = os.path.join(os.path.abspath(host), NEST)
    out = portrait or os.path.join(nest_dir, "face.png")
    _face.render(org, out)
    led = sym.ledger(org)
    from .core.status import organism_status
    status = organism_status(org)
    return {"resident": org.body.identity_name(),
            "state": sym.metabolic_state(org), "ledger": led,
            "value_delivered": len(led["value_records"]),
            "generation": status["generation"],
            "band_count": status["band_count"],
            "verify_ok": status["verify_ok"],
            "verify_errors": status["verify_errors"],
            "immune_events": len(org.immune.log), "portrait": out}
