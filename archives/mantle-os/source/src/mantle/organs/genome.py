#!/usr/bin/env python3
"""
mantle.organs.genome  --  the Genome organ: identity, inheritance & lineage (Mantle OS)

The Genome is held in the BODY, not the cube. There are two distinct genomes: the *agent
genome* (Primer + commandments + defining data -- this organ) lives in the Body; the
*cube genome* (the booted band/layer/profile layout) is the cube boot sector. The cube is
pure experiential memory; identity survives every rebirth because it never lived in any
cube.

Reflexes: boot-order (assemble Primer + Special + Immunization for a model), seal-primer
(reject any post-birth Primer write -- enforced by the Body store itself), inherit (on
rebirth, record the distillation + the sealed ancestor's fingerprint in the lineage index).
"""
from __future__ import annotations

from typing import Any, Dict

from .contract import Organ, OrganContract

CONTRACT = OrganContract(
    "genome", "identity, inheritance & lineage -- who this creature is (Body-resident)",
    reads=[],
    writes=["discoveries"],   # the inheritance record on rebirth
    reflexes=[
        {"name": "boot-order", "trigger": "model boot / context assembly",
         "effect": "assemble Primer + Special Instructions + Immunization"},
        {"name": "seal-primer", "trigger": "any post-birth Primer write",
         "effect": "refused (PermissionError) -- the Primer is immutable"},
        {"name": "inherit", "trigger": "rebirth",
         "effect": "distill the outgoing Prime; record inheritance + seal fingerprint"},
    ],
    phase1="active",
    phase2_extension="the MIND proposes Special Instructions; the Body applies them",
    audit=[
        "Primer immutable & Body-resident (never in the cube)",
        "boot order = Primer + Special Instructions + Immunization",
        "the MIND has no write path to the Genome",
        "rebirth is chosen, never capacity-forced, and retains sealed ancestry",
    ],
)


class Genome(Organ):
    contract = CONTRACT

    @property
    def body(self):
        return self.org.body

    def boot_order(self) -> Dict[str, Any]:
        return self.body.boot_order()

    def boot_text(self) -> str:
        return self.body.boot_text()

    def identity_name(self) -> str:
        return self.body.identity_name()

    def self_record(self) -> Dict[str, Any]:
        return self.body.self_record()

    def record_inheritance(self, distillation: Dict[str, Any], source_ref: str) -> Any:
        """Write the rebirth inheritance record into the NEW Prime's discoveries band."""
        from ..vcw.entry import make_entry
        return self.append("discoveries", make_entry(
            {"inheritance": distillation}, opcode="INHERIT", author="BODY",
            source=source_ref))
