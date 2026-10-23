#!/usr/bin/env python3
"""
mantle.mem  --  the MEM VCW: a keyless knowledge plasmid (Mantle OS · M4)

A MEM VCW is a VCW *without an identity key* -- bare memory, like a USB stick. It carries
DATA and MICROCODE-as-data only: no Body, no genesis key, no lineage, no memory tree. It is
the mechanism by which organisms share knowledge (the bacterial plasmid / phagocytosis
model). Because it has no key, a MEM VCW is ALWAYS *other* to any body that finds it.

Two operations:

  excrete(org, knowledge, microcode)
      an organism writes a MEM VCW of distilled knowledge (+ optional microcode carried as
      inert data -- never a live exec layer). The result is a portable cube file.

  digest(org, mem, code_band=None)
      a body that finds an OTHER MEM VCW does NOT use its code directly. It:
        1. reviews the knowledge into `discoveries` as INFERRED (provenance `foreign-MEM`) --
           never into `facts`;
        2. smoke-tests each microcode in the SANDBOX (`trial`): an escape is refused and
           immune-logged, never adopted;
        3. only AFTER its own trial passes may it RE-DERIVE the microcode into SELF -- it
           calcifies the skill under the BODY's own authorship (the organism vouches for it),
           never running the foreign artifact as-is.

Nothing foreign executes outside the sandbox; nothing foreign becomes a fact; nothing
foreign calcifies without the organism's own proof.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .vcw.cube import Cube
from .vcw.bands import make_band_boot
from .vcw.entry import make_entry
from .vcw.drivers import trial, SandboxError

MEM_DATA = "mem_data"       # distilled knowledge (log-json)
MEM_CODE = "mem_code"       # microcode carried as DATA: {entry, code, cases} (log-json)


def mem_genome() -> List[Dict[str, Any]]:
    """The minimal genome of a MEM VCW: two data bands, nothing identity-bearing."""
    return [make_band_boot(MEM_DATA, 600, "log-json", span=8,
                           purpose="shared knowledge (a plasmid, not an organism)"),
            make_band_boot(MEM_CODE, 610, "log-json", span=4,
                           purpose="shared microcode, carried as inert data")]


def is_mem_vcw(cube: Any) -> bool:
    """A MEM VCW is a bare Cube with the mem bands and NO identity key (it is not an
    organism; no Body ever signs it, so it is always OTHER)."""
    return (isinstance(cube, Cube) and MEM_DATA in cube.bands
            and not getattr(cube, "genesis_key", None))


def excrete(org: Any, knowledge: List[Dict[str, Any]],
            microcode: Optional[List[Dict[str, Any]]] = None) -> Cube:
    """Write a MEM VCW of distilled knowledge (+ optional microcode-as-data). Keyless and
    lineage-free by construction -- it is data, not a self."""
    mem = Cube.genesis(mem_genome(), generation=0)
    for k in knowledge:
        mem.append(MEM_DATA, make_entry(k, opcode="MEM", author="BODY",
                                        source="excretion"))
    for code in (microcode or []):
        mem.append(MEM_CODE, make_entry(
            {"entry": code["entry"], "code": code["code"], "cases": code.get("cases", []),
             "capabilities": code.get("capabilities", {})},
            opcode="MICROCODE", author="BODY", source="excretion"))
    return mem


def digest(org: Any, mem: Cube, code_band: Optional[str] = None) -> Dict[str, Any]:
    """Phagocytose an OTHER MEM VCW: review knowledge as inferred, sandbox-test microcode,
    and re-derive only the microcode that passes the organism's OWN trial into SELF. Returns
    a report. Foreign code never runs outside the sandbox and never calcifies un-trialed."""
    report = {"knowledge_reviewed": 0, "microcode_trialed": 0,
              "adopted": 0, "rejected": 0, "other": is_mem_vcw(mem)}

    # 1. knowledge -> discoveries, INFERRED, foreign provenance (never facts)
    for e in mem.read(MEM_DATA):
        org.memory.remember("discoveries", e["content"], opcode="DIGESTED",
                            source="foreign-MEM", verified=False,
                            confidence="inferred", provenance="foreign-MEM")
        report["knowledge_reviewed"] += 1

    # 2/3. microcode -> sandbox trial; re-derive into SELF only on the body's own proof
    for e in mem.read(MEM_CODE):
        c = e["content"]
        cases = [(cs.get("args", {}), cs.get("expect")) for cs in c.get("cases", [])]
        try:
            res = trial(c["code"], c["entry"], cases)          # the sandbox smoke-test
        except SandboxError:
            org.immune_event("foreign_code_rejected",
                             {"entry": c.get("entry"), "reason": "sandbox-escape"})
            report["rejected"] += 1
            continue
        if not res.get("ok"):
            org.immune_event("foreign_code_rejected",
                             {"entry": c.get("entry"), "reason": "trial-failed"})
            report["rejected"] += 1
            continue
        report["microcode_trialed"] += 1
        if code_band and code_band in org.prime.bands:
            # RE-DERIVE into SELF: the organism adopts it under its OWN authorship after its
            # own trial -- the foreign origin is recorded, but the body vouches for the code.
            org.prime.calcify(code_band, c["code"], entry=c["entry"],
                              signature={"by": "digest"},
                              capabilities=c.get("capabilities", {}),
                              provenance={"author": "BODY", "born_gen": 0,
                                          "origin": "foreign-MEM", "adopted": True})
            report["adopted"] += 1
    return report
