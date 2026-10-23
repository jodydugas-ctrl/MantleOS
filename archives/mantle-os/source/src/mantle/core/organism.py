#!/usr/bin/env python3
"""
mantle.core.organism  --  the Organism: Body + Prime cube + ancestors + nine organs (Mantle OS)

    Organism = BODY        (the Primer + lineage index -- identity, outside every cube)
             + PRIME cube  (one, hot, takes all experiential writes)
             + ANCESTRAL   (sealed, fingerprinted, lazy-loaded, read-only)
             + the nine organs, meshed on one deterministic SignalBus

How an AppAI lives, in this one class's vocabulary:
  born      Organism.birth() -- the Primer seals into the Body; the Prime cube is genesis'd
  senses    organism.senses.inhale()/receive() -- the only inbound boundary
  remembers organism.memory.remember() -- immutable hashed entries, veiled reads
  reacts    reflex arcs + bus reflexes -- deterministic, no LLM
  protects  organism.immune -- every violation becomes an immune event; staged saves
  acts      organism.limbs -- dispatch lifecycle, ControlBridge, proofs
  learns    discoveries (inferred) -> facts only with cited evidence
  calcifies trial -> gates -> Cube.calcify -> limbs.invoke_reflex (instinct, no MIND)
  rebirths  organism.rebirth() -- CHOSEN reformat; ancestors sealed + fingerprinted
  thinks    Phase 2 only: a bounded MIND fused into organism.brain (extension, never
            replacement -- and never imported by anything in this package)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .body import Body
from .events import SignalBus
from . import refs as _refs
from .persist import atomic_write_json, ensure_owner_directory, harden_owner_file
from ..vcw.cube import Cube
from ..vcw.bands import standard_genome
from ..organs.heart import Heart
from ..organs.genome import Genome
from ..organs.nervous import Nervous
from ..organs.senses import Senses
from ..organs.immune import Immune
from ..organs.limbs import Limbs
from ..organs.memory import Memory
from ..organs.brain import Brain
from ..organs.reproduction import Reproduction

ORGAN_ORDER = ("heart", "genome", "nervous", "senses", "immune", "limbs", "memory",
               "brain", "reproduction")


class Organism:
    def __init__(self, body: Body, prime: Cube) -> None:
        self.body = body
        self.prime = prime
        self.ancestral: List[Cube] = []
        self.stage1_certified = False           # set by the Stage-1 gate; required for fusion

        # --- the mesh: one bus, nine organs, no hidden coupling ------------------
        self.bus = SignalBus()
        self.immune = Immune(self)
        self.bus.set_immune_sink(self.immune.event)      # reflex faults -> immune events
        self.heart = Heart(self)
        self.genome = Genome(self)
        self.nervous = Nervous(self)
        self.senses = Senses(self)
        self.limbs = Limbs(self)
        self.memory = Memory(self)
        self.brain = Brain(self)
        self.reproduction = Reproduction(self)
        self.prime.pressure_hook = self.memory.on_pressure   # capacity -> metabolism record
        # lineage continuity (the Reproduction organ's runtime duty): the sealed seed
        # and sealed origin spore are carried across every rebirth, fail-open via the bus
        self.bus.subscribe("rebirth", lambda p: self.reproduction.on_rebirth(p),
                           organ="reproduction")
        # nociception wiring (M1): the Heart wakes the MIND only on a reason -- a
        # SIGNIFICANT signal (Senses) or distress (Immune). No reason -> the MIND sleeps.
        self.bus.subscribe("significant", lambda p: self.heart.on_significant(p),
                           organ="heart")
        self.bus.subscribe("distress", lambda p: self.heart.on_distress(p), organ="heart")
        self._sync_lineage()

    # ---- birth ----------------------------------------------------------------
    @classmethod
    def birth(cls, identity: Dict[str, Any], truths: List[str], commandments: List[str],
              genome: Optional[List[Dict[str, Any]]] = None) -> "Organism":
        body = Body()
        body.birth(identity, truths, commandments)
        prime = Cube.genesis(genome or standard_genome(), generation=0)
        return cls(body, prime)

    # ---- the organ mesh, inspectable -------------------------------------------
    def organs(self) -> Dict[str, Any]:
        return {name: getattr(self, name) for name in ORGAN_ORDER}

    def manifests(self) -> Dict[str, Dict[str, Any]]:
        return {name: organ.manifest() for name, organ in self.organs().items()}

    # ---- lineage bookkeeping ------------------------------------------------------
    def _sync_lineage(self) -> None:
        self.body.prime_generation = self.prime.generation
        self.body.lineage_index[self.prime.generation] = {
            "role": "prime", "location": "prime", "seal_fingerprint": None}
        for c in self.ancestral:
            self.body.lineage_index[c.generation] = {
                "role": "ancestral", "location": "gen%03d" % c.generation,
                "seal_fingerprint": c.seal_fingerprint}

    def cube_for_generation(self, gen: int) -> Optional[Cube]:
        if gen == self.prime.generation:
            return self.prime
        for c in self.ancestral:
            if c.generation == gen:
                return c
        return None

    # ---- boundaries (delegations that keep old call-sites honest) ----------------
    def sense(self, signal: Any, opcode: str = "SENSE") -> str:
        """Back-compat inbound boundary: everything still enters through Senses."""
        if not isinstance(signal, dict):
            signal = {"value": signal}
        return self.senses.inhale(signal)

    def immune_event(self, kind: str, detail: Any) -> None:
        self.immune.event(kind, detail)

    @property
    def immune_log(self) -> List[Dict[str, Any]]:
        return self.immune.log

    def resolve(self, ref: str) -> Any:
        return _refs.resolve(self, ref)

    # ---- rebirth = CHOSEN reformat (never capacity-forced) -------------------------
    def rebirth(self, new_genome: Optional[List[Dict[str, Any]]] = None,
                reason: str = "reformat") -> "Organism":
        """Distill Prime -> seal + fingerprint it as ancestral -> new Prime with a
        (possibly new) genome. The Body keeps the Primer; nothing identity-bearing is
        copied between cubes. Rebirth is always a choice; capacity triggers metabolism,
        not this."""
        distillation = {"from_generation": self.prime.generation, "reason": reason,
                        "fact_count": len(self.prime.read("facts"))}
        fingerprint = self.prime.seal()                       # freeze + fingerprint
        self.ancestral.append(self.prime)
        new_gen = self.prime.generation + 1
        self.prime = Cube.genesis(new_genome or standard_genome(), generation=new_gen)
        self.prime.pressure_hook = self.memory.on_pressure
        self.genome.record_inheritance(
            dict(distillation, seal_fingerprint=fingerprint),
            source_ref="<gen%d.facts>" % distillation["from_generation"])
        self._sync_lineage()
        self.bus.emit("rebirth", {"generation": new_gen, "reason": reason})
        return self

    # ---- the SELF seal (M2): a signature over the identity-bearing artifacts ---------
    def _self_seal_payload(self) -> bytes:
        """The bytes the Body signs to mark a nest as SELF: the Primer + the Prime cube's
        content fingerprint. Only this Body's genesis key produces a verifying mac, so a
        cloned or forged nest fails the check (anti-clone)."""
        payload = {"primer": self.body.self_record()["primer"],
                   "prime_fingerprint": self.prime.fingerprint()}
        return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          default=str).encode("utf-8")

    # ---- persistence (hot Prime; cold, write-once ancestors) ------------------------
    def save(self, directory: str) -> None:
        ensure_owner_directory(directory)
        prime_path = os.path.join(directory, "gen%03d.vcw" % self.prime.generation)
        self.prime.save(prime_path)
        harden_owner_file(prime_path)
        for c in self.ancestral:
            target = os.path.join(directory, "gen%03d.vcw" % c.generation)
            if c.sealed and os.path.exists(target):
                harden_owner_file(target)
                continue                          # sealed = immutable = written once
            c.save(target)
            harden_owner_file(target)
        atomic_write_json(os.path.join(directory, "body.json"), self.body.to_dict())
        atomic_write_json(
            os.path.join(directory, "organism.json"),
            {"prime_generation": self.prime.generation,
             "ancestral_generations": [c.generation for c in self.ancestral],
             "stage1_certified": self.stage1_certified},
        )
        atomic_write_json(
            os.path.join(directory, "resident_protocol.json"),
            {"schema": "mantle-resident-protocol-declaration-v1",
             "protocol": "mantle-resident-v2"},
        )
        # the SELF seal: sign the nest as this Body's own (M2). Skipped only for a
        # legacy Body with no genesis key.
        if self.body.has_key:
            seal = {"fingerprint": self.body.key_fingerprint,
                    "mac": self.body.sign(self._self_seal_payload())}
            atomic_write_json(os.path.join(directory, "self_seal.json"), seal)

    @classmethod
    def load(cls, directory: str, verify_seals: bool = False) -> "Organism":
        with open(os.path.join(directory, "organism.json")) as f:
            org_meta = json.load(f)
        with open(os.path.join(directory, "body.json")) as f:
            body = Body.from_dict(json.load(f))
        prime = Cube.load(os.path.join(directory,
                                       "gen%03d.vcw" % org_meta["prime_generation"]))
        o = cls(body, prime)
        # A saved value is historical evidence only. Certification is deliberately
        # process-local and must be reproduced against the loaded bytes before fusion.
        # Never restore a bare boolean as a fresh capability.
        o.stage1_certified = False
        # ancestors load LAZY (the cold tier): no layer decodes until referenced
        o.ancestral = [Cube.load(os.path.join(directory, "gen%03d.vcw" % g), lazy=True)
                       for g in org_meta["ancestral_generations"]]
        if verify_seals:
            # the SELF check (M2): a key whose fingerprint no longer matches is a tampered
            # or orphaned identity -- fail LOUDLY (an immune event AND a raise), never
            # silently boot a body that cannot prove it is itself.
            if o.body.has_key and not o.body.key_fingerprint_consistent():
                o.immune_event("autoimmune_risk",
                               {"problem": "genesis key fingerprint mismatch"})
                raise PermissionError("autoimmune_risk: the genesis key does not match its "
                                      "recorded fingerprint; refusing to boot a tampered SELF")
            seal_path = os.path.join(directory, "self_seal.json")
            if o.body.has_key and os.path.exists(seal_path):
                with open(seal_path) as f:
                    seal = json.load(f)
                if not o.body.verify(o._self_seal_payload(), seal.get("mac", "")):
                    # the nest does not verify as THIS Body's own (clone / forgery / a
                    # substituted key+fingerprint pair) -- record it, do not trust silently.
                    o.immune_event("autoimmune_risk",
                                   {"problem": "self-seal does not verify under this key"})
            for c in o.ancestral:
                for problem in c.verify_seal():
                    o.immune_event("ancestor_tamper",
                                   {"generation": c.generation, "problem": problem})
        o._sync_lineage()
        return o
