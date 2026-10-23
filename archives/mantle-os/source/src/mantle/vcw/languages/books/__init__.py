#!/usr/bin/env python3
"""mantle.vcw.languages.books

Concrete forged Books. Each subpackage is an immutable language artifact:

  reason_evidence       OPERATIONAL Tome — reason-evidence@0.10/mantle-standard
                        (FROZEN; delegates to frozen Grimoire v0.10)

CANDIDATE lineages (per their Tome documents) are not yet declared here:
user_language, computational_thought, agent_instruction. They enter the
registry only after their codecs, corpora and measurements pass the freeze
gate (Forge v0.2 §23, §31-§32).
"""
from __future__ import annotations

from . import reason_evidence as reason_evidence  # registers on import
