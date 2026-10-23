"""mantle.organs -- the nine canonical organs (Mantle OS).

Heart, Genome, Nervous System, Senses, Immune System, Limbs, Memory, Brain, Reproduction. Every organ
carries an OrganContract (manifest, reflex surface, band permissions, audit obligations,
fail mode) and communicates only via the SignalBus and the cube -- never by reaching into
another organ. Nothing in this package imports mantle.mind: Phase-1 code cannot reach an
LLM even by accident.
"""
from .contract import Organ, OrganContract
from .heart import Heart
from .genome import Genome
from .nervous import Nervous
from .senses import Senses
from .immune import Immune
from .limbs import Limbs, DISPATCH_PHASES
from .memory import Memory, MEMORY_BANDS
from .brain import Brain
from .reproduction import Reproduction

__all__ = ["Organ", "OrganContract", "Heart", "Genome", "Nervous", "Senses", "Immune",
           "Limbs", "Memory", "Brain", "Reproduction", "DISPATCH_PHASES", "MEMORY_BANDS"]
