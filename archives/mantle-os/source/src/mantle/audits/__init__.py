"""mantle.audits -- the gates (Mantle OS).

Stage 1 certifies the Zombie Body (deterministic, LLM-free). Stage 2 re-runs every
Stage-1 row after fusion and adds containment rows. The invariants prove every guard
red/green. Any hard-fail blocks progression. No invariant is ever weakened to pass.

NOTE: this package deliberately does NOT import its submodules eagerly. stage2 imports
the mind package (it audits a fusion), and Phase-1 code paths -- including the hatchery,
which runs the Stage-1 gate -- must be able to import `mantle.audits.stage1` without
ever loading an LLM transport. The no-phase1-llm-path invariant enforces this; it is
the invariant that caught the original eager import.
"""

__all__ = ["invariants", "stage1", "stage2"]
