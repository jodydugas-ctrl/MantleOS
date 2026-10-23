#!/usr/bin/env python3
"""
mantle.mind.containment  --  the bounded MIND write surface (Mantle OS)

The single choke point for every MIND write. The MIND may write ONLY:

    thoughts   private reflection (veiled)
    brain      brain lifecycle records: dispatch INTENTION/DELEGATED + model traces

Any other band is refused by the Body and recorded as an immune event -- the breach never
executes. The MIND can only ever EXTEND the Body, never break it. Durable truth (`facts`),
the Genome, the immune band, and every other band stay forever out of reach.
"""
from __future__ import annotations

from typing import Any, Dict

# The ONLY bands a fused MIND may write. Everything else is the Body's, permanently.
WRITE_SURFACE = ("thoughts", "brain")


def guarded_write(organism: Any, band: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    """Refuse-and-record any MIND write outside the surface; append otherwise."""
    if band not in WRITE_SURFACE:
        organism.immune_event("mind_write_refused",
                              {"band": band, "allowed": list(WRITE_SURFACE)})
        raise PermissionError("the MIND may write only %s, not %r"
                              % (list(WRITE_SURFACE), band))
    return organism.prime.append(band, entry)
