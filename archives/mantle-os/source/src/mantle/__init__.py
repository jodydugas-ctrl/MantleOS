"""Mantle OS -- the Homeostatic AppAI Framework.

Grow software like a living organism, then give it a mind. An AppAI is built Body first:
nine contracted organs mesh on one deterministic SignalBus around a durable picture-memory
(the VCW cube), with an immune system and a heartbeat -- all certified with no LLM attached.
Only then may a bounded MIND be fused, and it may only ever extend what already lives.

An AppAI travels as a single SPORE -- one PNG carrying its germ (the complete build data)
and build instructions any coding agent can read. It can take residence in a host codebase,
share knowledge, redesign its own VCW, and reconstruct itself -- every capability gated by
the runnable audits and their tamper proofs.

    python -m mantle teach                       # the Field Guide, running
    python -m mantle hatch examples/spores/greeter.png --out=nest/ --auth=hatch-auth.json
"""
__version__ = "2.0.0rc1"

# The public API is exposed lazily (PEP 562): importing `mantle` is near-free; each name pulls
# in its submodule only on first access. `from mantle import Organism` and `mantle.Organism`
# both still work -- they just defer the core/vcw/hatchery import chains (and the heavy audit
# suite those drag in) until something is actually used.
_LAZY = {
    "ClaimStatus": ("mantle.contracts", "ClaimStatus"),
    "EvidenceRef": ("mantle.contracts", "EvidenceRef"),
    "GroundedClaim": ("mantle.contracts", "GroundedClaim"),
    "GroundedAnswer": ("mantle.contracts", "GroundedAnswer"),
    "ResidentTurnResult": ("mantle.contracts", "ResidentTurnResult"),
    "ResidentRuntime": ("mantle.contracts", "ResidentRuntime"),
    "HostAdapter": ("mantle.contracts", "HostAdapter"),
    "CertificationStatus": ("mantle.contracts", "CertificationStatus"),
    "TaskClass": ("mantle.governance", "TaskClass"),
    "EnergyPolicy": ("mantle.governance", "EnergyPolicy"),
    "SpendAuthorization": ("mantle.governance", "SpendAuthorization"),
    "ProviderState": ("mantle.governance", "ProviderState"),
    "EnergyState": ("mantle.governance", "EnergyState"),
    "ResourceOfferInbox": ("mantle.resources", "ResourceOfferInbox"),
    "FaceAttestation": ("mantle.phenotype", "FaceAttestation"),
    "AncestorEvidence": ("mantle.ancestry", "AncestorEvidence"),
    "LineageAttestation": ("mantle.lifecycle", "LineageAttestation"),
    "SporeInspection": ("mantle.lifecycle", "SporeInspection"),
    "ActionExecutionProof": ("mantle.proofs", "ActionExecutionProof"),
    "MutationClass": ("mantle.proofs", "MutationClass"),
    "Organism": ("mantle.core", "Organism"),
    "Body": ("mantle.core", "Body"),
    "SignalBus": ("mantle.core", "SignalBus"),
    "Cube": ("mantle.vcw", "Cube"),
    "standard_genome": ("mantle.vcw", "standard_genome"),
    "make_band_boot": ("mantle.vcw", "make_band_boot"),
    "make_entry": ("mantle.vcw", "make_entry"),
    "entry_hash": ("mantle.vcw", "entry_hash"),
    "code_hash": ("mantle.vcw", "code_hash"),
    "trial": ("mantle.vcw", "trial"),
    "CapacityError": ("mantle.vcw", "CapacityError"),
    "OVERFLOW_THRESHOLD": ("mantle.vcw", "OVERFLOW_THRESHOLD"),
    "EMERGENCY_THRESHOLD": ("mantle.vcw", "EMERGENCY_THRESHOLD"),
    "GERM_FORMAT": ("mantle.hatchery", "GERM_FORMAT"),
    "EGG_FORMAT": ("mantle.hatchery", "EGG_FORMAT"),
    "EggError": ("mantle.hatchery", "EggError"),
    "validate_germ": ("mantle.hatchery", "validate_germ"),
    "load_germ": ("mantle.hatchery", "load_germ"),
    "incubate": ("mantle.hatchery", "incubate"),
    "hatch": ("mantle.hatchery", "hatch"),
    "HatchError": ("mantle.hatchery", "HatchError"),
    # SEED reproduction -- the ONE artifact: the SPORE (one PNG that is a whole agent,
    # optionally carrying the germ -- the complete build data -- for a full AppAI)
    "create_spore": ("mantle.spore", "create_spore"),
    "pack_germ": ("mantle.spore", "pack_germ"),
    "read_spore": ("mantle.spore", "read_spore"),
    "verify_spore": ("mantle.spore", "verify_spore"),
    "inspect_spore_typed": ("mantle.spore", "inspect_spore_typed"),
}

__all__ = list(_LAZY) + ["__version__"]


def __getattr__(name):
    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError("module %r has no attribute %r" % (__name__, name))
    import importlib
    value = getattr(importlib.import_module(spec[0]), spec[1])
    globals()[name] = value  # cache so the lazy lookup happens at most once
    return value


def __dir__():
    return sorted(list(globals()) + list(_LAZY))
