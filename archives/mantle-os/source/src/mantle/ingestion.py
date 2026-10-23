#!/usr/bin/env python3
"""
mantle.ingestion  --  the organism remembers its own becoming (Mantle OS · §3)

Conversations (design sessions, operator instructions, these very build notes) should not
live only in a chat log -- they should enter the organism the same way everything else
does: through SENSES, distilled deterministically, with honest provenance.

  a DECISION   -> a `facts` entry, SOURCED (the operator decided it; the citation is the
                  conversation). It is observed, not inferred.
  an IDEA      -> a `discoveries` entry, INFERRED (verified=False, confidence="inferred").
                  An idea is a maybe, and it stays a maybe until evidence promotes it.
  the COVENANT -> operator INTENT recorded as a Special Instruction (the Body applies it),
                  so it is carried in every future MIND framing rather than lost in chat.

Everything is redacted at the Senses boundary; nothing inferred is ever laundered into a
fact.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .core.redact import redact

DECISION, IDEA = "decision", "idea"


def ingest(org: Any, lines: List[Dict[str, Any]]) -> Dict[str, int]:
    """Ingest a conversation. Each line is {text, kind?, source?}. Returns a tally."""
    tally = {"sensed": 0, "decisions": 0, "ideas": 0}
    for line in lines:
        text = redact(line.get("text", ""))
        org.senses.inhale({"action_id": "ingest", "event_type": "conversation",
                           "text": text})                  # the only way in
        tally["sensed"] += 1
        if str(line.get("kind", IDEA)).lower() == DECISION:
            org.memory.remember("facts", {"decision": text}, opcode="INGESTED",
                                source=line.get("source", "conversation"), verified=True)
            tally["decisions"] += 1
        else:
            org.memory.remember("discoveries", {"idea": text}, opcode="INGESTED",
                                source="conversation", verified=False,
                                confidence="inferred")
            tally["ideas"] += 1
    return tally


def record_covenant(org: Any, intent: str) -> Dict[str, Any]:
    """Record operator intent as a Special Instruction -- the covenant the MIND is framed by.
    The MIND guides; the Body applies (it is the Body that writes this)."""
    return org.body.apply_special(redact(intent), source="operator-covenant")
