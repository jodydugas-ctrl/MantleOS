#!/usr/bin/env python3
"""
mantle.reproduction  --  the TWO ways an AppAI makes another AppAI (Mantle OS)

Doctrine of record: documents/REPRODUCTION.md.

There is ONE travelling artifact -- the SPORE, a single PNG carrying the germ (the
complete build data) and build instructions -- and two methods of reproduction. This
module is the single seam that says so; every call delegates to the canonical,
already-audited module. "How does an organism reproduce?" has a two-word answer --
SEED or GRAFT -- and both answers are spores.

  SEED  --  INDEPENDENT reproduction. A spore whose germ declares a WHOLE new AppAI.
            Hatching it is always a BIRTH through the one hatchery door
            (mantle.hatchery.hatch) and faces the same Stage-1 gate every Body faces --
            a tampered seed cannot smuggle an uncertified Body into the world. A bare
            v1 spore (no germ) still hatches: its identity + task distill into a
            minimal germ. Internal tissue of the same act: the VAULT (the organism's
            own sealed germ inside its VCW, for self-reconstruction) and the
            cache-ghost (mantle.ghost, a spore living in an LLM prompt cache).

  GRAFT --  DEPENDENT reproduction: a spore AIMED AT A HOST. The germ inside is a
            non-destructive patch set against a NAMED host, applied in a workspace
            copy; the original is census-proven byte-identical (mantle.graft). The
            same act includes anchoring (mantle.anchor -- dissect the host read-only,
            grow an additive `.mantle/` nest, become the codebase's resident) and is
            sustained by symbiosis (mantle.symbiosis, the metered energy economy).
            Assimilation closes the loop: `mantle assimilate <host> --spore=out.png`
            scans an app and EMITS its spore.

A seed answers to no host, a graft lives in one. Two methods, one artifact, both gated
by the full invariant suite, no standing law weakened.
"""
from __future__ import annotations

from typing import Any, Dict, Union

SEED_FORMS = ("spore",)              # the one artifact ("egg"/"vault" route to its tissue)
GRAFT_FORMS = ("anchor", "graft")

#: The consolidation map -- the one-artifact story. Used by the docs,
#: `python -m mantle reproduce`, and the Field Guide so the story stays single-sourced.
METHODS: Dict[str, Dict[str, Any]] = {
    "seed": {
        "kind": "independent",
        "biology": "spores -- dormant, self-contained, grows with no host",
        "forms": {
            "spore": "mantle.spore + mantle.hatchery  -- ONE PNG carrying the germ (the whole "
                     "build document); `mantle hatch <spore.png>` births it (cache-ghost optional)",
            "vault": "reproduction organ tissue  -- the organism's own sealed germ, inside its "
                     "VCW, for self-reconstruction (RESURGERE is a birthright)",
        },
        "law": "hatching a seed is a BIRTH: it faces the same Stage-1 gate every Body faces",
    },
    "graft": {
        "kind": "dependent",
        "biology": "a spore aimed at a host -- propagate by living inside what you do not own",
        "forms": {
            "anchor":    "mantle.anchor  -- take residence in a host codebase (additive nest)",
            "symbiosis": "mantle.symbiosis  -- the metered energy economy that sustains residency",
            "graft":     "mantle.graft  -- a graft-germ spore: a non-destructive patch against "
                         "a named host",
        },
        "law": "a graft never modifies a host file; the census proves do-no-harm byte-for-byte",
    },
}


class ReproductionError(Exception):
    """An unknown reproductive form, or a form given the wrong kind of seed/host."""


def describe() -> Dict[str, Any]:
    """Return the two-method consolidation map (for docs, the CLI, and `teach`)."""
    return METHODS


# ---------------------------------------------------------------------------
# SEED -- independent reproduction
# ---------------------------------------------------------------------------

def seed(form: str = "spore", **kwargs) -> Dict[str, Any]:
    """Reproduce INDEPENDENTLY. kwargs pass through to the canonical module unchanged.

        seed("spore", germ={...}, path="buddy.png")          # pack a germ spore
        seed("spore", name="Buddy", task="answer one question", path="buddy.png")
        seed("spore", path="examples/spores/greeter.png", hatch=True, out_dir="nest/")
        seed("vault", seed=<germ dict sealed in an organism>) # internal tissue

    Every path ends in a certified Body (or a verifiable dormant spore). This routes to
    the canonical module; it never re-implements the birth.
    """
    if form == "spore":
        from . import spore as _spore
        if kwargs.pop("hatch", False):
            from .hatchery import hatch as _hatch
            return {"method": "seed", "form": "spore", "result": _hatch(**kwargs)}
        germ = kwargs.pop("germ", None)
        path = (_spore.pack_germ(germ, **kwargs) if germ is not None
                else _spore.create_spore(**kwargs))
        return {"method": "seed", "form": "spore", "path": path,
                "verify": _spore.verify_spore(path)["ok"]}
    if form == "egg":                       # historical name for a germ hatch
        from .hatchery import hatch as _hatch
        return {"method": "seed", "form": "spore", "result": _hatch(**kwargs)}
    if form == "vault":
        from .organs.reproduction import reconstruct
        return {"method": "seed", "form": "vault", "result": reconstruct(**kwargs)}
    raise ReproductionError(
        f"unknown seed form {form!r}; expected one of {SEED_FORMS} "
        "(the historical 'egg' and 'vault' names still route)")


# ---------------------------------------------------------------------------
# GRAFT -- dependent reproduction (residency in a host)
# ---------------------------------------------------------------------------

def graft(form: str = "anchor", **kwargs) -> Dict[str, Any]:
    """Reproduce DEPENDENTLY, inside a host. `form` selects the residency style.

        graft("anchor", host="path/to/app", starter_credits=5)
        graft("graft",  spec="examples/eggs/notes_graft.json", host="examples/sample_app")

    External graft artifacts require a target-bound authorization and explicit
    workspace. A pre-loaded dict is Body-internal data and requires ``internal=True``.
    """
    if form == "anchor":
        from .anchor import anchor
        return {"method": "graft", "form": "anchor", "result": anchor(**kwargs)}
    if form == "graft":
        from . import graft as _graft
        spec: Union[str, Dict[str, Any]] = kwargs.pop("spec")
        if isinstance(spec, str):
            return {"method": "graft", "form": "graft",
                    "result": _graft.apply_artifact(spec, **kwargs)}
        if not kwargs.pop("internal", False):
            raise ReproductionError(
                "pre-loaded graft dictionaries are Body-internal; pass internal=True explicitly"
            )
        return {"method": "graft", "form": "graft", "result": _graft.apply(spec, **kwargs)}
    raise ReproductionError(
        f"unknown graft form {form!r}; expected one of {GRAFT_FORMS}")
