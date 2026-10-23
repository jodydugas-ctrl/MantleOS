"""mantle.core -- the organism's spine (Mantle OS).

The Body store, the SignalBus, the unified reference resolver, the secret boundary, and
the Organism that meshes the nine organs. No LLM, no network, no vendor code -- ever.
"""
from .body import Body
from .events import SignalBus
from .redact import redact, redact_str, contains_secret, MASK
from .organism import Organism, ORGAN_ORDER
from . import refs

__all__ = ["Body", "SignalBus", "redact", "redact_str", "contains_secret", "MASK",
           "Organism", "ORGAN_ORDER", "refs"]
